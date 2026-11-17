"""Investigation report schema and the evidence validator (docs/AGENT.md)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from flowpilot.investigation.evidence import EvidenceLog

NO_CONCLUSION = "The available data does not support a reliable conclusion."

Confidence = Literal["supported", "suggestive", "not_supported"]
HypothesisStatus = Literal["supported", "ruled_out", "inconclusive"]


class Citation(BaseModel):
    evidence_id: str
    fact: str


class Claim(BaseModel):
    """A sentence plus the facts its numbers come from."""

    text: str
    citations: list[Citation] = Field(default_factory=list)


class Finding(BaseModel):
    claim: Claim
    confidence: Confidence


class Hypothesis(BaseModel):
    name: str
    status: HypothesisStatus
    claim: Claim


class Recommendation(BaseModel):
    kind: Literal["fix_and_verify", "experiment", "fix_tracking", "investigate_segment",
                  "no_action"]
    claim: Claim


class InvestigationReport(BaseModel):
    alert_id: str
    mode: Literal["rule_based", "llm"]
    title: str
    summary: list[Claim]
    findings: list[Finding]
    hypotheses: list[Hypothesis]
    limitations: list[str]
    recommendation: Recommendation
    conclusion_supported: bool

    def claims(self) -> list[Claim]:
        return [*self.summary, *(f.claim for f in self.findings),
                *(h.claim for h in self.hypotheses), self.recommendation.claim]


class ValidationIssue(BaseModel):
    claim: str
    problem: str


# Numbers as shown in claims: "−2.8 pp", "+3.4 pp", "34.4%", "1,573", "4.12" (versions are
# excluded below). Unicode minus and ASCII hyphen are both accepted.
_NUMBER = re.compile(r"(?<![\w.\-\u2212])([+\-\u2212]?\d[\d,]*(?:\.\d+)?)\s*(pp|%)?")
_VERSION = re.compile(r"\b\d+\.\d+(?:\.\d+)?\b")


def _numbers(text: str) -> list[tuple[float, str | None, str]]:
    versions = {m.group(0) for m in _VERSION.finditer(text)}
    out = []
    for m in _NUMBER.finditer(text):
        raw, unit = m.group(1), m.group(2)
        if unit is None and raw.lstrip("+-−") in versions:
            continue  # app versions such as 4.12 are names, not measurements
        if unit is None and re.fullmatch(r"20\d\d", raw):
            continue  # years in dates
        value = float(raw.replace(",", "").replace("−", "-"))
        out.append((value, unit, raw))
    return out


def _decimals(raw: str) -> int:
    return len(raw.split(".")[1]) if "." in raw else 0


def _matches(shown: float, unit: str | None, raw: str, fact: float) -> bool:
    """Does the displayed number equal the fact, rounded the way it is displayed?

    Rates are stored as fractions, so "34.4%" or "-2.8 pp" also match fact x 100. A number
    written with an explicit sign must have the fact's sign; an unsigned one ("fell by 2.8 pp")
    is compared by size.
    """
    signed = raw[0] in "+-\u2212"
    tol = 0.5 * 10 ** (-_decimals(raw)) + 1e-9
    candidates = [fact, fact * 100] if unit in ("%", "pp") else [fact]
    for c in candidates:
        if signed and abs(shown - c) <= tol:
            return True
        if not signed and abs(abs(shown) - abs(c)) <= tol:
            return True
    return False


def validate(report: InvestigationReport, log: EvidenceLog) -> list[ValidationIssue]:
    """Every cited fact must exist, and every number in a claim must equal a cited fact.

    Calendar dates ("October 26") name periods and are skipped; every other number, including
    counts such as "8 weeks", must match a cited fact.
    """
    issues: list[ValidationIssue] = []
    for claim in report.claims():
        facts: list[float] = []
        for c in claim.citations:
            ev = log.get(c.evidence_id)
            if ev is None or ev.output is None:
                issues.append(ValidationIssue(claim=claim.text,
                                              problem=f"unknown evidence {c.evidence_id}"))
                continue
            if c.fact not in ev.output.facts:
                issues.append(ValidationIssue(claim=claim.text,
                                              problem=f"{c.evidence_id} has no fact {c.fact!r}"))
                continue
            facts.append(ev.output.facts[c.fact])
        for value, unit, raw in _numbers(_strip_dates(claim.text)):
            if not any(_matches(value, unit, raw, f) for f in facts):
                issues.append(ValidationIssue(
                    claim=claim.text, problem=f"number {raw}{unit or ''} matches no cited fact"))
    return issues


_MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|"
           "December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec")
_DATE = re.compile(rf"\b(?:{_MONTHS})\.?\s+\d{{1,2}}(?:,\s*\d{{4}})?\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b")


_QUOTED = re.compile(r"'[^']*'")


def _strip_dates(text: str) -> str:
    """Calendar dates name periods and quoted terms name categories (a step, a company size
    such as '1-10'); neither is a measurement."""
    return _QUOTED.sub("", _DATE.sub("", text))
