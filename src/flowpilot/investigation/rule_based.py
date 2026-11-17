"""Rule-based investigator (no LLM). Implements the committed playbook in docs/AGENT.md.

It uses the same tools and produces the same report shape as the LLM agent, so the app stays
useful without an API key. Every number in its text is formatted from a recorded fact and cites
it, so the evidence validator can check the report like any other.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from flowpilot.investigation.evidence import Evidence, EvidenceLog
from flowpilot.investigation.report import (
    NO_CONCLUSION,
    Citation,
    Claim,
    Finding,
    Hypothesis,
    InvestigationReport,
    Recommendation,
)
from flowpilot.investigation.tools import Toolbox
from flowpilot.monitor.detect import Alert

BASELINE_WEEKS = 8
DIMENSIONS = ("signup_platform", "acquisition_channel", "company_size")
LEAD_Z = 3.0  # v2 (M3): segment change vs rest change
LOCALIZED_RATIO = 2.0
VERSION_Z = 3.0  # v2 (M5)
EXPERIMENT_SHARE = 0.25  # v2 (M6): share of the observed change an experiment must explain
STEP_DROP_PP = 5.0
OTHER_STEPS_PP = 2.0
ACTIVATION_STABLE_PP = 2.0
CALENDAR_OTHERS_PP = 1.0
MIX_RULED_OUT, MIX_SUPPORTED = 0.25, 0.5
VERSION_MIN_N = 100
VERSION_SHARE = 0.8
EVENTS_FOR_METRIC = {
    "activation_rate": {"project_created", "invite_sent"},
    "week1_retention": {"task_created", "task_completed", "comment_added", "timeline_viewed",
                        "integration_used"},
}
EVENTS_FOR_METRIC["week2_retention"] = EVENTS_FOR_METRIC["week1_retention"]
EVENTS_FOR_METRIC["week4_retention"] = EVENTS_FOR_METRIC["week1_retention"]

MINUS = "−"
NAMES = {"ios": "iOS", "android": "Android", "web": "web", "paid_social": "paid social",
         "paid_search": "paid search", "organic_search": "organic search",
         "referral": "referral", "partner": "partner", "signup_platform": "signup platform",
         "acquisition_channel": "acquisition channel", "company_size": "company size"}
STEP_NAMES = {"project_created": "project created", "invite_sent": "invite sent",
              "teammate_joined": "teammate joined"}


def name(x: str) -> str:
    """Readable label; category values containing digits are quoted so they read as names."""
    label = NAMES.get(x, x)
    return f"'{label}'" if any(ch.isdigit() for ch in label) else label


def pp(v: float) -> str:
    s = f"{abs(v):.1f}"
    return f"{MINUS if v < 0 and float(s) else '+'}{s} pp"


def rate(v: float) -> str:
    return f"{v * 100:.1f}%"


def rel(v: float) -> str:
    s = f"{abs(v):.0f}"
    return f"{MINUS if v < 0 and float(s) else '+'}{s}%"


def day(d: date) -> str:
    return d.strftime("%B %-d")


def cite(ev: Evidence, *facts: str) -> list[Citation]:
    return [Citation(evidence_id=ev.evidence_id, fact=f) for f in facts]


def fact(ev: Evidence | None, key: str) -> float | None:
    if ev is None or ev.output is None:
        return None
    return ev.output.facts.get(key)


class _Run:
    def __init__(self, tools: Toolbox) -> None:
        self.tools = tools
        self.log = EvidenceLog()

    def call(self, tool: str, **args: Any) -> Evidence:
        return self.log.record(tool, args, getattr(self.tools, tool))


def investigate(tools: Toolbox, alert: Alert) -> tuple[InvestigationReport, EvidenceLog]:
    run = _Run(tools)
    if alert.kind == "tracking_gap":
        return _tracking_gap(run, alert), run.log
    if alert.kind == "rate":
        return _rate(run, alert), run.log
    return _count(run, alert), run.log


# ---- rate alerts --------------------------------------------------------------------------
def _rate(run: _Run, alert: Alert) -> InvestigationReport:
    m = alert.metric
    cur_s, cur_e = alert.first_period_start, alert.last_period_end
    base_s, base_e = cur_s - timedelta(days=7 * BASELINE_WEEKS), cur_s
    period = {"current_start": cur_s, "current_end": cur_e,
              "baseline_start": base_s, "baseline_end": base_e}
    run.call("get_alert", alert_id=alert.alert_id)
    ev_def = run.call("get_metric_definition", metric=m)
    label = ev_def.output.data["label"] if ev_def.output else m
    ev_cmp = run.call("compare_periods", metric=m, **period)
    if ev_cmp.output is None:
        return _failed(alert, label, f"compare_periods failed: {ev_cmp.error}")
    diff = fact(ev_cmp, "diff_pp") or 0.0
    down = diff < 0
    summary = [Claim(
        text=f"{label} was {rate(fact(ev_cmp, 'current_rate') or 0)} for signups from "
             f"{day(cur_s)} to {day(cur_e - timedelta(days=1))}, against "
             f"{rate(fact(ev_cmp, 'baseline_rate') or 0)} in the "
             f"{fact(ev_cmp, 'baseline_weeks'):.0f} weeks before: {pp(diff)} "
             f"({rel(fact(ev_cmp, 'rel_change_pct') or 0)}).",
        citations=cite(ev_cmp, "current_rate", "baseline_rate", "baseline_weeks", "diff_pp",
                       "rel_change_pct"))]
    findings: list[Finding] = []
    hypotheses: list[Hypothesis] = []
    limitations = ["This is an observational analysis: it locates the change but does not "
                   "prove its cause."]

    # Data quality first: a tracking gap on an event the metric depends on limits everything.
    ev_dq = run.call("data_quality_report", start=cur_s, end=cur_e)
    relevant_gaps = [g for g in (ev_dq.output.data["gaps"] if ev_dq.output else [])
                     if g["event"] in EVENTS_FOR_METRIC.get(m, set())]

    # Where is the change? One breakdown per dimension; the most concentrated one leads.
    breakdowns = {dim: run.call("segment_breakdown", metric=m, dimension=dim, **period)
                  for dim in DIMENSIONS}
    scored = [(fact(ev, "lead_z") or 0.0, dim, ev) for dim, ev in breakdowns.items()
              if ev.output and ev.output.data.get("lead_segment") is not None]
    localized = False
    lead_dim = lead_seg = version = step = None
    lead_ev: Evidence | None = None
    if scored:
        lead_z, lead_dim, lead_ev = max(scored, key=lambda x: x[0])
        lead_seg = str(lead_ev.output.data["lead_segment"]) if lead_ev.output else None
        lead_diff = fact(lead_ev, "lead_diff_pp") or 0.0
        others = fact(lead_ev, "others_diff_pp") or 0.0
        localized = (lead_z >= LEAD_Z and
                     abs(lead_diff) >= LOCALIZED_RATIO * abs(others) and
                     (lead_diff < 0) == down)
        if localized and lead_seg is not None:
            findings.append(Finding(confidence="supported", claim=Claim(
                text=f"The change is concentrated in {name(lead_dim)} {name(lead_seg)}: "
                     f"{pp(lead_diff)} there, against {pp(others)} for all other signups.",
                citations=cite(lead_ev, "lead_diff_pp", "others_diff_pp"))))

    # Drill down: app version and release for a platform lead.
    seg_filter: dict[str, list[str]] = {}
    if localized and lead_dim and lead_seg and lead_ev:
        seg_filter = {lead_dim: [lead_seg]}
    if localized and lead_dim == "signup_platform" and lead_seg and lead_ev:
        ev_ver = run.call("segment_breakdown", metric=m, dimension="signup_app_version",
                          filters={"signup_platform": [lead_seg]}, **period)
        platform_base = fact(lead_ev, f"{lead_seg}.baseline_rate")
        candidates = [s for s in (ev_ver.output.data["segments"] if ev_ver.output else [])
                      if s["current_rate"] is not None and s["current_n"] >= VERSION_MIN_N]
        if candidates and platform_base is not None:
            worst = min(candidates, key=lambda s: s["current_rate"] * (1 if down else -1))
            v_diff = (worst["current_rate"] - platform_base) * 100
            lead_diff = fact(lead_ev, "lead_diff_pp") or 0.0
            carries = v_diff <= VERSION_SHARE * lead_diff if down else (
                v_diff >= VERSION_SHARE * lead_diff)
            r_v, n_v = worst["current_rate"], worst["current_n"]
            n_pb = fact(lead_ev, f"{lead_seg}.baseline_n") or 0.0
            v_se = (r_v * (1 - r_v) / n_v + platform_base * (1 - platform_base)
                    / max(n_pb, 1.0)) ** 0.5
            v_z = (v_diff / 100) / v_se * (-1 if down else 1) if v_se else 0.0
            if carries and v_z >= VERSION_Z:
                version = str(worst["segment"])
                ev_rel = run.call("get_releases", platform=lead_seg)
                released = next((r["released_on"] for r in (ev_rel.output.data["releases"]
                                 if ev_rel.output else []) if r["version"] == version), None)
                seg_filter = {"signup_platform": [lead_seg], "signup_app_version": [version]}
                findings.append(Finding(confidence="supported", claim=Claim(
                    text=f"Within {name(lead_seg)}, signups on version {version} activated at "
                         f"{rate(worst['current_rate'])}, against "
                         f"{rate(platform_base)} for {name(lead_seg)} before.",
                    citations=[*cite(ev_ver, f"{version}.current_rate"),
                               *cite(lead_ev, f"{lead_seg}.baseline_rate")]))
                    if m == "activation_rate" else Finding(confidence="supported", claim=Claim(
                        text=f"Within {name(lead_seg)}, the change sits in version {version}.")))
                if released and cur_s <= date.fromisoformat(released) < cur_e:
                    findings.append(Finding(confidence="supported", claim=Claim(
                        text=f"{name(lead_seg)} {version} was released on "
                             f"{day(date.fromisoformat(released))}, inside the affected "
                             "period.")))
                else:
                    version = None

    # Funnel step for activation alerts.
    if localized and m == "activation_rate" and seg_filter:
        # v2 (M4): difference in differences against the baseline period; a new version is
        # compared with its platform before the release.
        ev_f = run.call("funnel", current_start=cur_s, current_end=cur_e, segment=seg_filter,
                        baseline_start=base_s, baseline_end=base_e,
                        baseline_segment={lead_dim: [lead_seg]} if lead_dim and lead_seg
                        else None)
        gaps = {k: fact(ev_f, f"{k}.did_pp") for k in STEP_NAMES}
        known = {k: v for k, v in gaps.items() if v is not None}
        if known:
            pick = min if down else max
            step = pick(known, key=lambda k: known[k])
            other = [k for k in known if k != step]
            clear = all(abs(known[k]) < OTHER_STEPS_PP for k in other)
            if abs(known[step]) >= STEP_DROP_PP and clear:
                who = name(lead_seg or "") + (f" {version}" if version else "")
                findings.append(Finding(confidence="supported", claim=Claim(
                    text=f"In the onboarding funnel, {who} signups reach '{STEP_NAMES[step]}' at "
                         f"{rate(fact(ev_f, f'{step}.segment_rate') or 0)}, against "
                         f"{rate(fact(ev_f, f'{step}.rest_rate') or 0)} for everyone else. "
                         f"Compared with the gap before, that step lost {pp(known[step])}; the "
                         "other steps moved by "
                         + " and ".join(pp(known[k]) for k in other) + ".",
                    citations=cite(ev_f, f"{step}.segment_rate", f"{step}.rest_rate",
                                   *(f"{k}.did_pp" for k in [step, *other])))))
            else:
                step = None

    # Retention alerts: is it onboarding or what happens after?
    if localized and m.endswith("retention") and seg_filter:
        # Compare on the lead segment itself: a new app version has no baseline period.
        ev_act = run.call("compare_periods", metric="activation_rate",
                          filters={lead_dim: [lead_seg]} if lead_dim and lead_seg
                          else seg_filter, **period)
        act_diff = fact(ev_act, "diff_pp")
        if act_diff is not None and abs(act_diff) < ACTIVATION_STABLE_PP:
            findings.append(Finding(confidence="supported", claim=Claim(
                text=f"Activation of the same signups changed by only {pp(act_diff)}, so this "
                     "is a retention problem, not an onboarding problem.",
                citations=cite(ev_act, "diff_pp"))))

    # Competing explanation: experiments running on these cohorts.
    ev_x = run.call("experiment_result", metric=m, start=cur_s, end=cur_e)
    significant = [x for x in (ev_x.output.data["experiments"] if ev_x.output else [])
                   if (x["p_harm"] < 0.05 if down else
                       x["p_two_sided"] < 0.05 and x["diff_pp"] > 0)]
    # v2 (M6): an experiment explains the change only if it can account for enough of it.
    harmful = [x for x in significant
               if (x["expected_contribution_pp"] < 0) == down
               and abs(x["expected_contribution_pp"]) >= EXPERIMENT_SHARE * abs(diff)]
    minor = [x for x in significant if x not in harmful]

    # ---- hypotheses ---------------------------------------------------------------------
    others_diff = fact(lead_ev, "others_diff_pp") if lead_ev else None
    if (localized and others_diff is not None and abs(others_diff) < CALENDAR_OTHERS_PP
            and lead_ev):
        hypotheses.append(Hypothesis(name="Calendar or seasonality", status="ruled_out",
                                     claim=Claim(
            text=f"A calendar effect would move all signups; outside {name(lead_seg or '')} "
                 f"the change was {pp(others_diff)}.",
            citations=cite(lead_ev, "others_diff_pp"))))
    else:
        hypotheses.append(Hypothesis(name="Calendar or seasonality", status="inconclusive",
                                     claim=Claim(text="The change is not confined to one "
                                                      "segment, so a calendar effect cannot be "
                                                      "excluded.")))
    ev_mix = breakdowns["acquisition_channel"]
    mix_share = fact(ev_mix, "mix_share")
    if mix_share is not None:
        status = ("ruled_out" if abs(mix_share) < MIX_RULED_OUT else
                  "supported" if mix_share > MIX_SUPPORTED else "inconclusive")
        hypotheses.append(Hypothesis(name="Acquisition-channel mix", status=status,  # type: ignore[arg-type]
                                     claim=Claim(
            text=f"Shifts in the acquisition-channel mix account for "
                 f"{pp(fact(ev_mix, 'mix_effect_pp') or 0)} of the "
                 f"{pp(fact(ev_mix, 'total_diff_pp') or 0)} change.",
            citations=cite(ev_mix, "mix_effect_pp", "total_diff_pp"))))
    if relevant_gaps:
        hypotheses.append(Hypothesis(name="Data quality", status="supported", claim=Claim(
            text=f"A tracking gap on {relevant_gaps[0]['event']} ({relevant_gaps[0]['platform']})"
                 " overlaps the period.")))
        limitations.append("A tracking gap on an event this metric depends on overlaps the "
                           "period; affected cohorts are unreliable.")
    else:
        hypotheses.append(Hypothesis(name="Data quality", status="ruled_out", claim=Claim(
            text="No tracking gap on an event this metric depends on overlaps the period.")))
    if harmful or minor:
        x = (harmful or minor)[0]
        xid = x["experiment_id"]
        hypotheses.append(Hypothesis(
            name="Running experiment", status="supported" if harmful else "inconclusive",
            claim=Claim(
                text=f"Experiment {xid} overlaps these cohorts; its treatment changed "
                     f"{label.lower()} by {pp(x['diff_pp'])}, which accounts for about "
                     f"{pp(x['expected_contribution_pp'])} of the {pp(diff)} change.",
                citations=[*cite(ev_x, f"{xid}.diff_pp", f"{xid}.expected_contribution_pp"),
                           *cite(ev_cmp, "diff_pp")])))
    else:
        hypotheses.append(Hypothesis(name="Running experiment", status="ruled_out", claim=Claim(
            text=f"No experiment overlapping these cohorts changed {label.lower()} "
                 "significantly.")))

    # ---- conclusion and recommendation ---------------------------------------------------
    mix_supported = mix_share is not None and mix_share > MIX_SUPPORTED
    blocked = bool(relevant_gaps) and not localized
    supported = (localized or mix_supported or bool(harmful)) and not blocked
    direction = "fell" if down else "rose"
    if localized and version and step:
        title = (f"{label} {direction}; the change sits in {name(lead_seg or '')} {version} "
                 f"signups at the '{STEP_NAMES[step]}' step")
        rec = Recommendation(kind="fix_and_verify", claim=Claim(
            text=f"Fix the '{STEP_NAMES[step]}' step in {name(lead_seg or '')} {version} and "
                 "confirm that activation of signups on the fixed version returns to the "
                 "earlier level. No experiment is needed: this is a regression fix, verified by "
                 "comparing cohorts."))
    elif localized:
        title = f"{label} {direction}; the change is concentrated in {name(lead_seg or '')} signups"
        rec = Recommendation(kind="investigate_segment", claim=Claim(
            text=f"Review what changed for {name(lead_seg or '')} signups in this period "
                 "(targeting, landing pages, release notes). If a product change is proposed, "
                 "test it with a planned experiment."))
    elif harmful:
        title = f"{label} {direction}; a running experiment explains the change"
        rec = Recommendation(kind="no_action", claim=Claim(
            text=f"Decide on experiment {harmful[0]['experiment_id']} in its review; its "
                 "treatment is the likely cause."))
    else:
        title = f"{label} {direction}; no single segment explains the change"
        rec = Recommendation(kind="no_action", claim=Claim(
            text="Keep monitoring; neither a segment nor the channel mix explains the change."))
    if not supported:
        summary.append(Claim(text=NO_CONCLUSION))
    return InvestigationReport(
        alert_id=alert.alert_id, mode="rule_based", title=title, summary=summary,
        findings=findings, hypotheses=hypotheses, limitations=limitations,
        recommendation=rec, conclusion_supported=supported)


# ---- tracking gaps ------------------------------------------------------------------------
def _tracking_gap(run: _Run, alert: Alert) -> InvestigationReport:
    plat = alert.segment.get("platform", "")
    event = alert.segment.get("event_name", "")
    s, e = alert.first_period_start, alert.last_period_end
    run.call("get_alert", alert_id=alert.alert_id)
    ev = run.call("data_quality_report", start=s, end=e, platform=plat)
    key = alert.alert_id
    findings: list[Finding] = []
    ev_change = fact(ev, f"{key}.events_change_pct")
    ses_change = fact(ev, f"{key}.sessions_change_pct")
    if ev_change is None or ses_change is None:
        return _failed(alert, event, "data_quality_report returned no figures for this alert")
    summary = [Claim(
        text=f"{event} events from {name(plat)} changed by {rel(ev_change)} from {day(s)} to "
             f"{day(e - timedelta(days=1))}, compared with the same days a week earlier, while "
             f"{name(plat)} sessions changed by {rel(ses_change)}.",
        citations=cite(ev, f"{key}.events_change_pct", f"{key}.sessions_change_pct")),
        Claim(text=NO_CONCLUSION)]
    prefix, suffix = f"{key}.", ".per_session_change_pct"
    versions = {k[len(prefix):-len(suffix)]: v
                for k, v in (ev.output.facts.items() if ev.output else [])
                if k.startswith(prefix) and k.endswith(suffix) and k != f"{key}{suffix}"}
    if versions:
        worst = min(versions, key=lambda v: versions[v])
        others = [v for v in versions if v != worst]
        text = (f"Per session, {event} events changed by {rel(versions[worst])} on app version "
                f"{worst}" + (", against " + " and ".join(rel(versions[v]) for v in others)
                              + " on other versions" if others else "") + ".")
        findings.append(Finding(confidence="supported", claim=Claim(
            text=text, citations=cite(ev, *(f"{key}.{v}.per_session_change_pct"
                                            for v in [worst, *others])))))
    findings.append(Finding(confidence="supported", claim=Claim(
        text=f"Sessions continued normally ({rel(ses_change)}), so users kept using the app; "
             "either the events were not recorded or this action failed for them.",
        citations=cite(ev, f"{key}.sessions_change_pct"))))
    hypotheses = [
        Hypothesis(name="Real drop in usage", status="ruled_out", claim=Claim(
            text=f"{name(plat)} sessions changed by {rel(ses_change)}, which a real drop in "
                 "usage would not leave intact.",
            citations=cite(ev, f"{key}.sessions_change_pct"))),
        Hypothesis(name="Tracking gap or functional break", status="supported", claim=Claim(
            text=f"{event} events are missing while sessions continue. Event data alone cannot "
                 f"tell a tracking bug from a release in which {event} itself fails.")),
    ]
    return InvestigationReport(
        alert_id=alert.alert_id, mode="rule_based",
        title=f"{event} events from {name(plat)} are missing: "
              "a tracking gap or a functional break, not a drop in usage",
        summary=summary, findings=findings, hypotheses=hypotheses,
        limitations=[f"Activity and retention metrics for {name(plat)} on these days are "
                     "unreliable until the gap is fixed or excluded."],
        recommendation=Recommendation(kind="fix_tracking", claim=Claim(
            text=f"First check that {event} works in the affected {name(plat)} version (QA, "
                 "error logs); then fix the tracking and exclude these days from behavioral "
                 "comparisons.")),
        conclusion_supported=False)


# ---- other count alerts -------------------------------------------------------------------
def _count(run: _Run, alert: Alert) -> InvestigationReport:
    plat = alert.segment.get("platform")
    run.call("get_alert", alert_id=alert.alert_id)
    ev = run.call("data_quality_report", start=alert.first_period_start,
                  end=alert.last_period_end, platform=plat)
    gaps = fact(ev, "tracking_gaps") or 0
    hyp = Hypothesis(
        name="Data quality", status="supported" if gaps else "ruled_out",
        claim=Claim(text="A tracking gap overlaps this change." if gaps else
                    "No tracking gap overlaps this change."))
    return InvestigationReport(
        alert_id=alert.alert_id, mode="rule_based",
        title=f"{alert.metric} changed; " + ("a tracking gap overlaps" if gaps else
                                             "no explanation found"),
        summary=[Claim(text=NO_CONCLUSION)], findings=[], hypotheses=[hyp],
        limitations=["The rule-based investigator only checks data quality for count alerts."],
        recommendation=Recommendation(kind="fix_tracking" if gaps else "no_action", claim=Claim(
            text="Fix the tracking gap first." if gaps else "Keep monitoring.")),
        conclusion_supported=False)


def _failed(alert: Alert, label: str, reason: str) -> InvestigationReport:
    return InvestigationReport(
        alert_id=alert.alert_id, mode="rule_based", title=f"{label}: investigation incomplete",
        summary=[Claim(text=NO_CONCLUSION)], findings=[], hypotheses=[],
        limitations=[reason], recommendation=Recommendation(
            kind="no_action", claim=Claim(text="Re-run the investigation after fixing the error.")),
        conclusion_supported=False)
