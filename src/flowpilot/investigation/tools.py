"""Read-only analytical tools for investigations (docs/AGENT.md).

Tools read through the metric layer, the experiment engine and the stored alerts. They never
write, and they never return user-generated text (workspace or project names).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from flowpilot.appstate.alerts import StoredAlert
from flowpilot.experiments.analysis import analyze, compare_arms
from flowpilot.investigation.evidence import ToolOutput
from flowpilot.metrics.engine import MetricEngine, MetricError

MIN_SEGMENT = 30  # units per period below which a segment is too small to lead


def _d(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


def _filters(raw: dict[str, list[str]] | None) -> dict[str, list[str]]:
    return {k: list(v) for k, v in (raw or {}).items()}


class Toolbox:
    def __init__(self, engine: MetricEngine, alerts: list[StoredAlert]) -> None:
        self.engine = engine
        self.alerts = {a.alert.alert_id: a.alert for a in alerts}

    # ---- helpers ------------------------------------------------------------------------
    def _pooled(self, metric: str, start: date, end: date,
                filters: dict[str, list[str]], group_by: str | None = None
                ) -> dict[str | None, tuple[int, int, int]]:
        """(numerator, denominator, complete periods) per segment over complete periods."""
        res = self.engine.query(metric, start, end, "week", filters, group_by)
        out: dict[str | None, list[int]] = {}
        for r in res.rows:
            if not r.complete or r.denominator is None:
                continue
            acc = out.setdefault(r.segment, [0, 0, 0])
            acc[0] += r.numerator
            acc[1] += r.denominator
            acc[2] += 1
        return {k: (v[0], v[1], v[2]) for k, v in out.items()}

    # ---- tools --------------------------------------------------------------------------
    def get_alert(self, alert_id: str) -> ToolOutput:
        a = self.alerts.get(alert_id)
        if a is None:
            raise KeyError(f"no alert {alert_id}")
        facts = {"observed": a.observed, "expected": a.expected, "z": a.max_abs_z,
                 "detections": float(a.detections)}
        if a.kind == "rate":
            facts["diff_pp"] = (a.observed - a.expected) * 100
        elif a.expected:
            facts["rel_change_pct"] = (a.observed - a.expected) / a.expected * 100
        seg = ", ".join(f"{k}={v}" for k, v in a.segment.items()) or "all signups"
        return ToolOutput(
            summary=f"{a.alert_id}: {a.metric} {a.direction} ({seg}), "
                    f"{a.first_period_start} to {a.last_period_end}",
            data=a.model_dump(mode="json"), facts=facts)

    def get_metric_definition(self, metric: str) -> ToolOutput:
        d = self.engine.definition(metric)
        return ToolOutput(summary=f"{d.label}: {d.description}",
                          data=d.model_dump(mode="json"), facts={"lag_days": float(d.lag_days)})

    def compare_periods(self, metric: str, current_start: str | date, current_end: str | date,
                        baseline_start: str | date, baseline_end: str | date,
                        filters: dict[str, list[str]] | None = None) -> ToolOutput:
        d = self.engine.definition(metric)
        if not d.is_rate:
            raise MetricError(f"{metric} is not a rate metric")
        f = _filters(filters)
        cur = self._pooled(metric, _d(current_start), _d(current_end), f).get(None)
        base = self._pooled(metric, _d(baseline_start), _d(baseline_end), f).get(None)
        if not cur or not base or not cur[1] or not base[1]:
            raise MetricError("no complete periods with data in one of the windows")
        c, b = cur[0] / cur[1], base[0] / base[1]
        return ToolOutput(
            summary=f"{d.label}: {c:.1%} now vs {b:.1%} before",
            data={"metric": metric, "filters": f},
            facts={"current_rate": c, "baseline_rate": b, "diff_pp": (c - b) * 100,
                   "rel_change_pct": (c - b) / b * 100 if b else 0.0,
                   "current_n": float(cur[1]), "baseline_n": float(base[1]),
                   "current_weeks": float(cur[2]), "baseline_weeks": float(base[2])})

    def segment_breakdown(self, metric: str, dimension: str, current_start: str | date,
                          current_end: str | date, baseline_start: str | date,
                          baseline_end: str | date,
                          filters: dict[str, list[str]] | None = None) -> ToolOutput:
        """Change per segment plus mix/rate decomposition.

        total = sum s_c r_c - sum s_b r_b = sum (s_c - s_b) r_b  [mix]  + sum s_c (r_c - r_b) [rate]
        """
        f = _filters(filters)
        cur = self._pooled(metric, _d(current_start), _d(current_end), f, dimension)
        base = self._pooled(metric, _d(baseline_start), _d(baseline_end), f, dimension)
        n_c = sum(v[1] for v in cur.values())
        n_b = sum(v[1] for v in base.values())
        if not n_c or not n_b:
            raise MetricError("no complete periods with data in one of the windows")
        segs: list[dict[str, Any]] = []
        facts: dict[str, float] = {}
        mix = rate = 0.0
        for seg in sorted({*cur, *base}, key=str):
            cn, cd, _ = cur.get(seg, (0, 0, 0))
            bn, bd, _ = base.get(seg, (0, 0, 0))
            s_c, s_b = cd / n_c, bd / n_b
            r_c = cn / cd if cd else None
            r_b = bn / bd if bd else None
            entry: dict[str, Any] = {"segment": seg, "current_n": cd, "baseline_n": bd,
                                     "current_rate": r_c, "baseline_rate": r_b,
                                     "share_current": s_c, "share_baseline": s_b}
            if r_c is not None:
                facts[f"{seg}.current_rate"] = r_c
                facts[f"{seg}.current_n"] = float(cd)
            if r_b is not None:
                mix += (s_c - s_b) * r_b
            if r_c is not None and r_b is not None:
                contrib = s_c * (r_c - r_b)
                rate += contrib
                entry |= {"diff_pp": (r_c - r_b) * 100, "rate_contribution_pp": contrib * 100,
                          "eligible": cd >= MIN_SEGMENT and bd >= MIN_SEGMENT}
                facts |= {f"{seg}.current_rate": r_c, f"{seg}.baseline_rate": r_b,
                          f"{seg}.diff_pp": (r_c - r_b) * 100, f"{seg}.current_n": float(cd)}
            facts[f"{seg}.share_change_pp"] = (s_c - s_b) * 100
            segs.append(entry)
        total = mix + rate
        eligible = [s for s in segs if s.get("eligible")]
        lead = max(eligible, key=lambda s: s["rate_contribution_pp"] * (-1 if total < 0 else 1),
                   default=None)
        others_diff = None
        if lead is not None:
            rest_c = [(cur[s][0], cur[s][1]) for s in cur if s != lead["segment"]]
            rest_b = [(base[s][0], base[s][1]) for s in base if s != lead["segment"]]
            rc = sum(x for x, _ in rest_c) / max(sum(y for _, y in rest_c), 1)
            rb = sum(x for x, _ in rest_b) / max(sum(y for _, y in rest_b), 1)
            others_diff = (rc - rb) * 100
            facts |= {"lead_share": lead["rate_contribution_pp"] / (total * 100) if total else 0.0,
                      "lead_diff_pp": lead["diff_pp"], "others_diff_pp": others_diff}
        facts |= {"total_diff_pp": total * 100, "mix_effect_pp": mix * 100,
                  "rate_effect_pp": rate * 100,
                  "mix_share": mix / total if total else 0.0}
        return ToolOutput(
            summary=f"{metric} by {dimension}: lead segment "
                    f"{lead['segment'] if lead else 'none'}",
            data={"metric": metric, "dimension": dimension, "filters": f, "segments": segs,
                  "lead_segment": lead["segment"] if lead else None},
            facts=facts)

    def funnel(self, current_start: str | date, current_end: str | date,
               segment: dict[str, list[str]]) -> ToolOutput:
        """Onboarding funnel of one segment vs everyone else, in the same period."""
        s, e = _d(current_start), _d(current_end)
        seg = self.engine.funnel(s, e, _filters(segment))
        everyone = self.engine.funnel(s, e)
        steps = ["Signed up", "Project created", "Invite sent", "Teammate joined"]
        n_seg = {x.step: x.users for x in seg.steps}
        n_all = {x.step: x.users for x in everyone.steps}
        n_rest = {k: n_all[k] - n_seg.get(k, 0) for k in steps}
        facts: dict[str, float] = {"segment_signups": float(n_seg.get(steps[0], 0)),
                                   "rest_signups": float(n_rest[steps[0]])}
        rows = []
        for prev, step in zip(steps, steps[1:], strict=False):
            rs = n_seg[step] / n_seg[prev] if n_seg.get(prev) else None
            rr = n_rest[step] / n_rest[prev] if n_rest[prev] else None
            key = step.lower().replace(" ", "_")
            if rs is not None and rr is not None:
                facts |= {f"{key}.segment_rate": rs, f"{key}.rest_rate": rr,
                          f"{key}.gap_pp": (rs - rr) * 100}
            rows.append({"step": step, "segment_rate": rs, "rest_rate": rr})
        return ToolOutput(summary=f"funnel for {segment} vs everyone else",
                          data={"segment": segment, "complete": seg.complete, "steps": rows},
                          facts=facts)

    def retention_cohorts(self, start: str | date, end: str | date,
                          filters: dict[str, list[str]] | None = None) -> ToolOutput:
        facts: dict[str, float] = {}
        rows: dict[str, dict[str, float | None]] = {}
        for week in (1, 2, 4):
            res = self.engine.query(f"week{week}_retention", _d(start), _d(end), "week",
                                    _filters(filters))
            for r in res.rows:
                if r.complete and r.value is not None:
                    rows.setdefault(r.period.isoformat(), {})[f"w{week}"] = r.value
                    facts[f"{r.period.isoformat()}.w{week}"] = r.value
        return ToolOutput(summary="week-1/2/4 retention by signup week",
                          data={"cohorts": rows}, facts=facts)

    def feature_adoption(self, feature: str, start: str | date, end: str | date) -> ToolOutput:
        metric = {"timeline_view": "timeline_adoption", "integrations": "integration_usage"}.get(
            feature, feature)
        res = self.engine.query(metric, _d(start), _d(end), "week")
        d = self.engine.definition(metric)
        facts = {f"{r.period.isoformat()}.adoption": r.value for r in res.rows
                 if r.complete and r.value is not None}
        return ToolOutput(summary=f"{d.label} on {d.platforms}",
                          data={"metric": metric, "platforms": d.platforms,
                                "weeks": [r.model_dump(mode="json") for r in res.rows]},
                          facts=facts)

    def get_releases(self, platform: str) -> ToolOutput:
        rows = self.engine.con.execute(
            "SELECT version, CAST(released_at AS DATE) FROM releases WHERE platform = ? "
            "ORDER BY released_at", [platform]).fetchall()
        last_day = self.engine.data_end - timedelta(days=1)
        return ToolOutput(
            summary=f"{len(rows)} {platform} releases",
            data={"releases": [{"version": v, "released_on": d.isoformat()} for v, d in rows]},
            facts={f"{v}.days_before_data_end": float((last_day - d).days) for v, d in rows})

    def experiment_result(self, experiment_id: str | None = None, metric: str | None = None,
                          start: str | date | None = None,
                          end: str | date | None = None) -> ToolOutput:
        """One experiment's analysis, or experiments overlapping a period with their effect
        on `metric` (treatment minus control)."""
        con = self.engine.con
        if experiment_id:
            a = analyze(self.engine, experiment_id)
            facts = {}
            if a.primary:
                facts = {"primary_diff_pp": a.primary.diff * 100,
                         "primary_p": a.primary.p_two_sided}
            return ToolOutput(summary=f"{experiment_id}: {a.verdict}",
                              data=a.model_dump(mode="json"), facts=facts)
        if not (metric and start and end):
            raise ValueError("give experiment_id, or metric with start and end")
        rows = con.execute(
            """SELECT experiment_id FROM experiments
               WHERE CAST(started_at AS DATE) < ? AND CAST(ended_at AS DATE) > ?
               ORDER BY started_at""", [_d(end), _d(start)]).fetchall()
        found: list[dict[str, Any]] = []
        overlap_facts: dict[str, float] = {}
        for (xid,) in rows:
            cmp, _ = compare_arms(self.engine, metric, xid, self.engine.data_end)
            if cmp is None:
                continue
            found.append({"experiment_id": xid, "diff_pp": cmp.diff * 100,
                          "p_harm": cmp.p_harm, "p_two_sided": cmp.p_two_sided})
            overlap_facts |= {f"{xid}.diff_pp": cmp.diff * 100, f"{xid}.p_harm": cmp.p_harm}
        return ToolOutput(summary=f"{len(found)} experiments overlap the period",
                          data={"metric": metric, "experiments": found}, facts=overlap_facts)

    def data_quality_report(self, start: str | date, end: str | date,
                            platform: str | None = None) -> ToolOutput:
        s, e = _d(start), _d(end)
        gaps = [a for a in self.alerts.values()
                if a.kind == "tracking_gap" and a.direction == "decline"
                and a.first_period_start < e and s < a.last_period_end
                and (platform is None or a.segment.get("platform") == platform)]
        facts: dict[str, float] = {"tracking_gaps": float(len(gaps))}
        details = []
        for g in gaps:
            plat, event = g.segment["platform"], g.segment.get("event_name", "")
            gs, ge = g.first_period_start, g.last_period_end
            ref_s, ref_e = gs - timedelta(days=7), ge - timedelta(days=7)
            ev = self.engine.query("event_volume", gs, ge, "day",
                                   {"platform": [plat], "event_name": [event]},
                                   group_by="app_version")
            ev_ref = self.engine.query("event_volume", ref_s, ref_e, "day",
                                       {"platform": [plat], "event_name": [event]},
                                       group_by="app_version")
            ses_v = self.engine.query("session_volume", gs, ge, "day", {"platform": [plat]},
                                      group_by="app_version")
            ses_v_ref = self.engine.query("session_volume", ref_s, ref_e, "day",
                                          {"platform": [plat]}, group_by="app_version")
            ses = sum(r.numerator for r in ses_v.rows)
            ses_ref = sum(r.numerator for r in ses_v_ref.rows)
            # [events now, events week before, sessions now, sessions week before] per version.
            # Users move between versions after a release, so raw counts per version mislead;
            # events per session compare like with like.
            by_version: dict[str, list[int]] = {}
            for rows, i in ((ev.rows, 0), (ev_ref.rows, 1), (ses_v.rows, 2), (ses_v_ref.rows, 3)):
                for r in rows:
                    by_version.setdefault(r.segment or "", [0, 0, 0, 0])[i] += r.numerator
            events_now = sum(v[0] for v in by_version.values())
            events_ref = sum(v[1] for v in by_version.values())
            key = f"{g.alert_id}"
            facts |= {
                f"{key}.events_change_pct": (events_now - events_ref) / events_ref * 100
                if events_ref else 0.0,
                f"{key}.sessions_change_pct": (ses - ses_ref) / ses_ref * 100 if ses_ref else 0.0,
                f"{key}.days": float((ge - gs).days),
            }
            for version, (now, ref, s_now, s_ref) in by_version.items():
                if ref and s_now and s_ref:
                    per_now, per_ref = now / s_now, ref / s_ref
                    facts[f"{key}.{version}.per_session_change_pct"] = (
                        (per_now - per_ref) / per_ref * 100)
            details.append({"alert_id": g.alert_id, "platform": plat, "event": event,
                            "start": gs.isoformat(), "end": ge.isoformat(),
                            "by_version": {k: {"events": v[0], "events_week_before": v[1],
                                               "sessions": v[2], "sessions_week_before": v[3]}
                                           for k, v in by_version.items()}})
        return ToolOutput(summary=f"{len(gaps)} tracking gaps in the period",
                          data={"gaps": details}, facts=facts)

    def query_metric(self, metric: str, start: str | date, end: str | date,
                     grain: str = "week", filters: dict[str, list[str]] | None = None,
                     group_by: str | None = None) -> ToolOutput:
        res = self.engine.query(metric, _d(start), _d(end), grain,  # type: ignore[arg-type]
                                _filters(filters), group_by)
        facts: dict[str, float] = {}
        for r in res.rows:
            if r.complete and r.value is not None:
                facts[f"{r.period.isoformat()}.{r.segment or 'all'}.value"] = r.value
                if r.denominator is not None:
                    facts[f"{r.period.isoformat()}.{r.segment or 'all'}.n"] = float(r.denominator)
        return ToolOutput(summary=f"{res.label} by {group_by or 'period'}",
                          data=res.model_dump(mode="json"), facts=facts)
