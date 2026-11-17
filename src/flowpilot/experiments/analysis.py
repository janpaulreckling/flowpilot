"""Experiment analysis following the committed rules in docs/EXPERIMENTS.md."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Literal

import numpy as np
from pydantic import BaseModel

from flowpilot.experiments.stats import (
    Comparison,
    compare,
    detectable_effect,
    holm,
    ratio_estimate,
    srm_p_value,
    two_proportion_p,
)
from flowpilot.metrics.engine import MetricEngine

SRM_ALPHA = 0.001
EXPOSURE_ALPHA = 0.001
GUARDRAIL_ALPHA = 0.05

Verdict = Literal["ship", "dont_ship", "no_meaningful_effect", "keep_testing", "invalid",
                  "not_decision_grade"]


class IntegrityCheck(BaseModel):
    name: str
    control: float
    treatment: float
    p_value: float
    passed: bool
    detail: str


class GuardrailResult(BaseModel):
    metric: str
    comparison: Comparison | None  # None while no cohort is mature for this metric yet
    holm_p_harm: float | None
    breached: bool


class ExperimentAnalysis(BaseModel):
    experiment_id: str
    name: str
    hypothesis: str
    randomization_unit: str
    primary_metric: str
    mde_abs: float
    planned_units_per_arm: int
    started: date
    ended: date
    as_of: date
    decision_grade: bool
    integrity: list[IntegrityCheck]
    primary: Comparison | None
    guardrails: list[GuardrailResult]
    achieved_mde: float | None
    verdict: Verdict
    rationale: list[str]


def compare_arms(engine: MetricEngine, metric: str, experiment_id: str,
          mature_by: date) -> tuple[Comparison | None, bool]:
    """Compare arms on units whose metric window has closed by `mature_by`."""
    lag = engine.definition(metric).lag_days
    rows = engine.experiment_outcomes(metric, experiment_id)
    usable = [r for r in rows if r[3] + timedelta(days=lag) < mature_by]
    all_mature = len(usable) == len(rows)
    arms = {}
    for variant in ("control", "treatment"):
        y = np.array([r[1] for r in usable if r[0] == variant], dtype=np.float64)
        n = np.array([r[2] for r in usable if r[0] == variant], dtype=np.float64)
        if y.size < 2:
            return None, False  # nothing measurable yet for this metric
        arms[variant] = ratio_estimate(y, n)
    return compare(metric, arms["control"], arms["treatment"]), all_mature


def analyze(
    engine: MetricEngine, experiment_id: str, as_of: date | None = None
) -> ExperimentAnalysis:
    as_of = min(as_of or engine.data_end, engine.data_end)
    con = engine.con
    row = con.execute(
        """SELECT name, hypothesis, randomization_unit, primary_metric, guardrail_metrics,
                  mde_abs, planned_units_per_arm, CAST(started_at AS DATE), CAST(ended_at AS DATE)
           FROM experiments WHERE experiment_id = ?""", [experiment_id]).fetchone()
    if row is None:
        raise ValueError(f"unknown experiment {experiment_id!r}")
    name, hypothesis, unit, primary_metric, guardrails_json, mde, planned, started, ended = row
    guardrail_metrics: list[str] = json.loads(guardrails_json)
    rationale: list[str] = []

    # Assignment counts use only units assigned before `as_of` (no look into the future).
    counts = dict(con.execute(
        """SELECT variant, count(*) FROM experiment_assignments
           WHERE experiment_id = ? AND CAST(assigned_at AS DATE) < ? GROUP BY 1""",
        [experiment_id, as_of]).fetchall())
    exposed = dict(con.execute(
        """SELECT a.variant, count(x.workspace_id) FROM experiment_assignments a
           LEFT JOIN experiment_exposures x USING (experiment_id, workspace_id)
           WHERE a.experiment_id = ? AND CAST(a.assigned_at AS DATE) < ? GROUP BY 1""",
        [experiment_id, as_of]).fetchall())
    n_c, n_t = int(counts.get("control", 0)), int(counts.get("treatment", 0))
    srm_p = srm_p_value(n_c, n_t)
    e_c, e_t = int(exposed.get("control", 0)), int(exposed.get("treatment", 0))
    exp_p = two_proportion_p(e_c, n_c, e_t, n_t) if n_c and n_t else 1.0
    integrity = [
        IntegrityCheck(name="Sample ratio", control=n_c, treatment=n_t, p_value=srm_p,
                       passed=srm_p >= SRM_ALPHA,
                       detail=f"planned 50/50, observed {n_t / max(n_c + n_t, 1):.1%} treatment"),
        IntegrityCheck(name="Exposure logging", control=e_c / max(n_c, 1),
                       treatment=e_t / max(n_t, 1), p_value=exp_p, passed=exp_p >= EXPOSURE_ALPHA,
                       detail="share of assigned workspaces with an exposure record"),
    ]

    primary, primary_mature = compare_arms(engine, primary_metric, experiment_id, as_of)
    guard_cmp = [(m, *compare_arms(engine, m, experiment_id, as_of)) for m in guardrail_metrics]
    measurable = [c for _, c, _ in guard_cmp if c is not None]
    adjusted = iter(holm([c.p_harm for c in measurable]))
    guardrails = []
    for metric, c, _ in guard_cmp:
        p = next(adjusted) if c is not None else None
        guardrails.append(GuardrailResult(metric=metric, comparison=c, holm_p_harm=p,
                                          breached=p is not None and p < GUARDRAIL_ALPHA))
    all_mature = primary_mature and all(m for _, _, m in guard_cmp)
    decision_grade = as_of >= ended and all_mature and primary is not None
    smallest_arm = min(primary.control.units, primary.treatment.units) if primary else 0
    achieved = (detectable_effect(primary.control.rate, smallest_arm)
                if primary and smallest_arm else None)

    verdict: Verdict
    if not decision_grade:
        verdict = "not_decision_grade"
        rationale.append("Interim look: the experiment has not ended or its cohorts are not "
                         "mature yet. Results are shown, but no decision is made (no peeking).")
    elif not integrity[0].passed:
        verdict = "invalid"
        rationale.append(f"Sample ratio mismatch: {integrity[0].detail} (p = {srm_p:.1e}). "
                         "The assignment is broken, so no effect is interpreted.")
    elif not integrity[1].passed:
        verdict = "invalid"
        rationale.append("Exposure logging differs between arms; the comparison is unreliable.")
    elif smallest_arm < planned:
        verdict = "keep_testing"
        rationale.append(f"Only {smallest_arm:,} units in the smaller arm, planned {planned:,}.")
    elif any(g.breached for g in guardrails):
        verdict = "dont_ship"
        for g in guardrails:
            if g.breached and g.comparison is not None and g.holm_p_harm is not None:
                rationale.append(
                    f"Guardrail {g.metric} breached: {g.comparison.diff * 100:+.1f} pp "
                    f"(Holm-adjusted p = {g.holm_p_harm:.3f}).")
    elif primary is None:  # unreachable: decision_grade requires a primary result
        verdict = "not_decision_grade"
    elif primary.ci95[0] > 0:
        verdict = "ship"
        rationale.append(f"{primary_metric} improved by {primary.diff * 100:+.1f} pp; the 95% CI "
                         f"[{primary.ci95[0] * 100:+.1f}, {primary.ci95[1] * 100:+.1f}] pp "
                         "excludes zero, and no guardrail was breached.")
    elif primary.ci95[1] < 0:
        verdict = "dont_ship"
        rationale.append(f"{primary_metric} got worse: 95% CI entirely below zero.")
    elif -mde < primary.ci90[0] and primary.ci90[1] < mde:
        verdict = "no_meaningful_effect"
        rationale.append(f"The 90% CI [{primary.ci90[0] * 100:+.1f}, {primary.ci90[1] * 100:+.1f}]"
                         f" pp lies inside ±{mde * 100:.1f} pp (the MDE): any effect is too small"
                         " to matter (equivalence, TOST at 5%).")
    else:
        verdict = "keep_testing"
        rationale.append("The interval is too wide to tell a meaningful effect from none.")

    return ExperimentAnalysis(
        experiment_id=experiment_id, name=name, hypothesis=hypothesis, randomization_unit=unit,
        primary_metric=primary_metric, mde_abs=mde, planned_units_per_arm=planned,
        started=started, ended=ended, as_of=as_of, decision_grade=decision_grade,
        integrity=integrity, primary=primary, guardrails=guardrails, achieved_mde=achieved,
        verdict=verdict, rationale=rationale,
    )
