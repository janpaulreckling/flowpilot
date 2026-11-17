"""Back-test of the anomaly monitor on the default dataset, scored against the ground truth.

Recall of the injected scenarios is asserted. The false-alarm count is measured and reported
in docs/MONITORING.md; it is deliberately not asserted against a number chosen after the fact.
"""

from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

import pytest

from flowpilot.evaluation.monitor_eval import MonitorEvaluation, evaluate
from flowpilot.metrics.engine import MetricEngine
from flowpilot.monitor import detect
from flowpilot.monitor.detect import run_monitor
from flowpilot.warehouse.connection import connect_read_only


@pytest.fixture(scope="module")
def evaluation(full_world: Path) -> MonitorEvaluation:
    with connect_read_only(full_world) as con:
        return evaluate(run_monitor(MetricEngine(con), date(2026, 5, 4)))


def test_detects_every_monitorable_scenario(evaluation: MonitorEvaluation) -> None:
    assert evaluation.detected["S1"] is not None
    assert evaluation.detected["S2"] is not None
    assert evaluation.detected["S5"] is not None


def test_s1_found_before_the_end_of_the_data(evaluation: MonitorEvaluation) -> None:
    first = evaluation.detected["S1"]
    assert first is not None and first <= date(2026, 11, 16)
    ios = [a.alert for a in evaluation.attributed
           if a.explained_by == "S1" and a.alert.segment.get("signup_platform") == "ios"]
    assert ios, "the iOS segment must be among the S1 alerts"


def test_s5_is_classified_as_tracking_gap(evaluation: MonitorEvaluation) -> None:
    gaps = [a.alert for a in evaluation.attributed if a.explained_by == "S5"]
    assert any(a.kind == "tracking_gap" and a.segment.get("event_name") == "task_created"
               for a in gaps)


def test_monitor_never_reads_ground_truth() -> None:
    tree = ast.parse(Path(detect.__file__).read_text())
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    imported |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any(m and ("evaluation" in m or "generator" in m) for m in imported)
    assert "ground_truth" not in Path(detect.__file__).read_text()
