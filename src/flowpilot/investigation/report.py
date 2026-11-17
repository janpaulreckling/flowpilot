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
_NUMBER = re.compile(r"(?<![\w.\-\u2212])([+\-\u2212]?\d(?:[\d,]*\d)?(?:\.\d+)?)\s*(pp|%)?")
# A version number is a name, but only in context ("iOS 4.12", "version 7.3", "v2.1");
# a bare decimal such as "7.9" or "0.018" is always a measurement and must be cited.
_VERSION = re.compile(
    r"\b(?:version|v|ios|android|release)\s*(\d+\.\d+(?:\.\d+)?)\b", re.IGNORECASE)


_DIRECTION = re.compile(
    r"\b(rose|increased|grew|climbed|improved|fell|dropped|declined|decreased|shrank)\s+by\s*$",
    re.IGNORECASE)
_UP = {"rose", "increased", "grew", "climbed", "improved"}


def _numbers(text: str) -> list[tuple[float, str | None, str, str | None]]:
    """(value, unit, raw text, direction word) for every measurement in the text."""
    version_spans = [m.span(1) for m in _VERSION.finditer(text)]
    out = []
    for m in _NUMBER.finditer(text):
        raw, unit = m.group(1), m.group(2)
        if unit is None and any(a <= m.start(1) < b for a, b in version_spans):
            continue
        value = float(raw.replace(",", "").replace("\u2212", "-"))
        d = _DIRECTION.search(text[max(0, m.start(1) - 24):m.start(1)])
        out.append((value, unit, raw, d.group(1).lower() if d else None))
    return out


def _decimals(raw: str) -> int:
    return len(raw.split(".")[1]) if "." in raw else 0


def _matches(shown: float, unit: str | None, raw: str, fact: float) -> bool:
    """Does the displayed number equal the fact, rounded the way it is displayed?

    Rates are stored as fractions, so "34.4%" or "-2.8 pp" also match fact x 100. A number
    written with an explicit sign must have the fact's sign; an unsigned one is compared by
    size (its direction is checked separately).
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
    """Bind every number in a claim to exactly one cited fact, in order of appearance.

    - each citation must point at a recorded fact;
    - the claim must cite as many facts as it shows numbers, in the same order, and each
      number must equal its fact as displayed (so swapped values fail);
    - "rose by" / "fell by" must agree with the sign of the fact;
    - calendar dates are skipped, and quoted text only when it is a known category name.
    """
    issues: list[ValidationIssue] = []
    for claim in report.claims():
        facts: list[float] = []
        broken = False
        for c in claim.citations:
            ev = log.get(c.evidence_id)
            if ev is None or ev.output is None:
                issues.append(ValidationIssue(claim=claim.text,
                                              problem=f"unknown evidence {c.evidence_id}"))
                broken = True
                continue
            if c.fact not in ev.output.facts:
                issues.append(ValidationIssue(claim=claim.text,
                                              problem=f"{c.evidence_id} has no fact {c.fact!r}"))
                broken = True
                continue
            facts.append(ev.output.facts[c.fact])
        numbers = _numbers(_strip_dates(claim.text))
        if broken:
            continue
        if len(numbers) != len(facts):
            issues.append(ValidationIssue(
                claim=claim.text,
                problem=f"shows {len(numbers)} numbers but cites {len(facts)} facts; cite each "
                        "number exactly once, in order of appearance"))
            numbers = numbers[:len(facts)]
        for (value, unit, raw, direction), fact in zip(numbers, facts, strict=False):
            if not _matches(value, unit, raw, fact):
                issues.append(ValidationIssue(
                    claim=claim.text,
                    problem=f"number {raw}{unit or ''} does not match its cited fact ({fact:g})"))
            elif direction and fact != 0 and (direction in _UP) != (fact > 0):
                issues.append(ValidationIssue(
                    claim=claim.text,
                    problem=f"'{direction} by {raw}' contradicts the sign of its fact ({fact:g})"))
    return issues


_MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|"
           "December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec")
_DATE = re.compile(rf"\b(?:{_MONTHS})\.?\s+\d{{1,2}}(?:,\s*\d{{4}})?\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b")
_QUOTED = re.compile(r"'([^']*)'")
# Category names that may appear in quotes; any other quoted text is checked like prose.
QUOTED_NAMES = {"1-10", "11-50", "51-200", "project created", "invite sent", "teammate joined"}


# A year after "in", "since", ... ("In 2026, activation fell") names a period.
_YEAR = re.compile(r"\b(in|since|during|until|through|of)\s+(?:19|20)\d{2}\b(?!\s*(?:%|pp|\.\d))",
                   re.IGNORECASE)


def _strip_dates(text: str) -> str:
    """Remove calendar dates and years (they name periods) and quoted category names."""
    text = _YEAR.sub(lambda m: m.group(1), _DATE.sub("", text))
    return _QUOTED.sub(lambda m: "" if m.group(1) in QUOTED_NAMES else m.group(1), text)
