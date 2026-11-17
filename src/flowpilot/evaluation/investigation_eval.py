"""Score investigation reports against the ground truth (docs/AGENT.md, DATA_SCENARIOS.md).

Criteria per scenario are fixed here; every decline alert is scored and reported, including
the ones the investigator gets wrong.
"""

from __future__ import annotations

from pydantic import BaseModel

from flowpilot.evaluation.monitor_eval import attribute
from flowpilot.investigation.report import InvestigationReport
from flowpilot.monitor.detect import Alert


class Score(BaseModel):
    alert_id: str
    scenario: str | None
    checks: dict[str, bool]

    @property
    def passed(self) -> bool:
        return all(self.checks.values())


def _text(report: InvestigationReport) -> str:
    return " ".join(c.text for c in report.claims()) + " " + report.title


def _status(report: InvestigationReport, name: str) -> str | None:
    return next((h.status for h in report.hypotheses if h.name == name), None)


def score(alert: Alert, report: InvestigationReport) -> Score:
    scenario = attribute(alert) if alert.direction == "decline" else None
    t = _text(report)
    checks: dict[str, bool]
    if scenario == "S1":
        checks = {
            "localized to iOS": "concentrated in signup platform iOS" in t,
            "version 4.12 named": "version 4.12" in t,
            "invite step named": "'invite sent'" in t,
            "release found": "4.12 was released" in t,
            "calendar ruled out": _status(report, "Calendar or seasonality") == "ruled_out",
            "mix not blamed": _status(report, "Acquisition-channel mix") != "supported",
            "fix and verify": report.recommendation.kind == "fix_and_verify",
        }
    elif scenario == "S2":
        checks = {
            "localized to paid social": "acquisition channel paid social" in t,
            "retention, not onboarding": "not an onboarding problem" in t,
            "conclusion supported": report.conclusion_supported,
        }
    elif scenario == "S5":
        checks = {
            "no behavioral conclusion": not report.conclusion_supported,
            "fix tracking": report.recommendation.kind == "fix_tracking",
            "version 7.3 named": "version 7.3" in t,
        }
    elif scenario == "E3":
        checks = {
            "experiment named": _status(report, "Running experiment") == "supported",
            "not blamed on a segment": not any(
                "concentrated in" in f.claim.text for f in report.findings),
        }
    else:  # unexplained alert: the honest answer is "no reliable conclusion"
        checks = {"no conclusion claimed": not report.conclusion_supported}
    return Score(alert_id=alert.alert_id, scenario=scenario, checks=checks)
