"""The four dataset experiments, scored against their ground-truth verdicts (D19, D23)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from flowpilot.experiments.analysis import ExperimentAnalysis, analyze
from flowpilot.metrics.engine import MetricEngine
from flowpilot.warehouse.connection import connect_read_only


@pytest.fixture(scope="module")
def engine(full_world: Path) -> Iterator[MetricEngine]:
    con = connect_read_only(full_world)
    yield MetricEngine(con)
    con.close()


@pytest.fixture(scope="module")
def results(engine: MetricEngine) -> dict[str, ExperimentAnalysis]:
    return {x: analyze(engine, x) for x in ("E1", "E2", "E3", "E4")}


@pytest.mark.parametrize(("experiment", "verdict"), [
    ("E1", "ship"), ("E2", "no_meaningful_effect"), ("E3", "dont_ship"), ("E4", "invalid"),
])
def test_verdict_matches_ground_truth(
    results: dict[str, ExperimentAnalysis], experiment: str, verdict: str
) -> None:
    assert results[experiment].verdict == verdict, results[experiment].rationale


def test_e3_is_stopped_by_its_guardrail_not_its_primary(
    results: dict[str, ExperimentAnalysis],
) -> None:
    e3 = results["E3"]
    breached = [g.metric for g in e3.guardrails if g.breached]
    assert breached == ["week2_retention"]


def test_e4_srm_blocks_interpretation(results: dict[str, ExperimentAnalysis]) -> None:
    srm = results["E4"].integrity[0]
    assert not srm.passed and srm.p_value < 1e-6


def test_interim_look_gives_no_verdict(engine: MetricEngine) -> None:
    # Regression: an early look crashed when a guardrail had no mature cohort yet.
    early = analyze(engine, "E1", as_of=date(2026, 9, 28))
    assert early.verdict == "not_decision_grade"
    assert not early.decision_grade
    assert early.primary is not None  # activation is already measurable for the first week
    assert any(g.comparison is None for g in early.guardrails)  # trial-to-paid is not


def test_experiment_and_dashboard_use_the_same_definition(
    engine: MetricEngine, results: dict[str, ExperimentAnalysis],
) -> None:
    # E1 assigns every new workspace in its window, so both arms together are the cohort.
    e1 = results["E1"]
    assert e1.primary is not None
    pooled = (e1.primary.control.rate * e1.primary.control.units
              + e1.primary.treatment.rate * e1.primary.treatment.units)
    window = engine.query("activation_rate", date(2026, 9, 14), date(2026, 10, 12))
    assert round(pooled) == sum(r.numerator for r in window.rows)
