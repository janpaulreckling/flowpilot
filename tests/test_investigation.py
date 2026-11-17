"""Rule-based investigations on the default dataset, the evidence validator, and safety."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from flowpilot.appstate.alerts import StoredAlert
from flowpilot.evaluation.investigation_eval import Score, score
from flowpilot.investigation.evidence import EvidenceLog, ToolOutput
from flowpilot.investigation.report import (
    NO_CONCLUSION,
    Citation,
    Claim,
    InvestigationReport,
    Recommendation,
    validate,
)
from flowpilot.investigation.rule_based import investigate
from flowpilot.investigation.tools import Toolbox
from flowpilot.metrics.engine import MetricEngine
from flowpilot.monitor.detect import run_monitor
from flowpilot.warehouse.connection import connect_read_only


@pytest.fixture(scope="module")
def tools(full_world: Path) -> Iterator[Toolbox]:
    con = connect_read_only(full_world)
    engine = MetricEngine(con)
    run = run_monitor(engine, date(2026, 5, 4))
    yield Toolbox(engine, [StoredAlert(alert=a, status="open") for a in run.alerts])
    con.close()


@pytest.fixture(scope="module")
def scorecard(tools: Toolbox) -> list[tuple[Score, InvestigationReport, EvidenceLog]]:
    out = []
    for alert in tools.alerts.values():
        if alert.direction != "decline":
            continue
        report, log = investigate(tools, alert)
        out.append((score(alert, report), report, log))
    return out


def test_every_report_passes_the_evidence_validator(
    scorecard: list[tuple[Score, InvestigationReport, EvidenceLog]],
) -> None:
    for s, report, log in scorecard:
        assert validate(report, log) == [], s.alert_id
        assert not [e for e in log.items if e.error], s.alert_id


@pytest.mark.parametrize("scenario", ["S1", "S2", "S5"])
def test_injected_scenarios_are_explained(
    scorecard: list[tuple[Score, InvestigationReport, EvidenceLog]], scenario: str
) -> None:
    scores = [s for s, _, _ in scorecard if s.scenario == scenario]
    assert scores
    for s in scores:
        assert s.passed, (s.alert_id, s.checks)


def test_unexplained_alert_gets_no_conclusion(
    scorecard: list[tuple[Score, InvestigationReport, EvidenceLog]],
) -> None:
    unexplained = [(s, r) for s, r, _ in scorecard if s.scenario is None]
    assert unexplained
    for s, report in unexplained:
        assert s.passed, s.alert_id
        assert any(c.text == NO_CONCLUSION for c in report.summary)


# ---- validator ----------------------------------------------------------------------------
def _log_with(facts: dict[str, float]) -> EvidenceLog:
    log = EvidenceLog()
    log.record("stub", {}, lambda: ToolOutput(summary="stub", facts=facts))
    return log


def _report(claim: Claim) -> InvestigationReport:
    return InvestigationReport(
        alert_id="A-1", mode="llm", title="t", summary=[claim], findings=[], hypotheses=[],
        limitations=[], recommendation=Recommendation(kind="no_action", claim=Claim(text="ok")),
        conclusion_supported=True)


def test_validator_accepts_correctly_cited_numbers() -> None:
    log = _log_with({"rate": 0.344, "diff_pp": -2.79, "n": 5369})
    claim = Claim(text="Activation was 34.4% (−2.8 pp) for 5,369 signups on iOS 4.12 in "
                       "week-2 since October 26.",
                  citations=[Citation(evidence_id="E-1", fact=f) for f in ("rate", "diff_pp", "n")])
    assert validate(_report(claim), log) == []


@pytest.mark.parametrize("text", [
    "Activation was 31.0% for these signups.",       # hallucinated number
    "Activation changed by +2.8 pp.",                # wrong sign
    "Activation was 34.4% for 9,999 signups.",       # one invented count
    # Regression (review finding): bare decimals and 20xx integers were skipped as
    # "versions" and "years", so these passed without evidence.
    "The z-score was 7.9 for iOS.",
    "Events per session fell from 4.1 to 2.3 on Android 7.3.",
    "p = 0.018 for the guardrail.",
    "We saw 2031 new signups that week.",
])
def test_validator_rejects_numbers_without_matching_evidence(text: str) -> None:
    log = _log_with({"rate": 0.344, "diff_pp": -2.79})
    claim = Claim(text=text, citations=[Citation(evidence_id="E-1", fact="rate"),
                                        Citation(evidence_id="E-1", fact="diff_pp")])
    assert validate(_report(claim), log)


def test_validator_rejects_unknown_evidence_and_facts() -> None:
    log = _log_with({"rate": 0.344})
    claim = Claim(text="Activation was 34.4%.",
                  citations=[Citation(evidence_id="E-9", fact="rate"),
                             Citation(evidence_id="E-1", fact="made_up")])
    problems = [i.problem for i in validate(_report(claim), log)]
    assert any("unknown evidence" in p for p in problems)
    assert any("no fact" in p for p in problems)


# ---- safety -------------------------------------------------------------------------------
def test_tools_cannot_write(tools: Toolbox) -> None:
    import duckdb

    with pytest.raises(duckdb.Error):
        tools.engine.con.execute("DELETE FROM experiments")


def test_tool_outputs_never_contain_user_generated_text(
    scorecard: list[tuple[Score, InvestigationReport, EvidenceLog]],
) -> None:
    from flowpilot.generator.simulate import INJECTION_STRINGS

    for _, _, log in scorecard:
        for ev in log.items:
            dumped = ev.model_dump_json()
            assert not any(s[:25] in dumped for s in INJECTION_STRINGS)
