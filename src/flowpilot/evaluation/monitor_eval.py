"""Score a monitor run against the ground truth.

This is the only place that reads the injected scenarios; the monitor package never imports it.
Attribution rules are reported as-is. One refinement was made after the first run: retention
alerts were first credited to S1 whenever they reached past its start, which credited S1 with a
week-1 retention alert whose first detection came from cohorts before the iOS release (E3 window).
S1 is now credited only for activation alerts, or retention alerts that start after the release.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from flowpilot.monitor.detect import Alert, MonitorRun

S1_START = date(2026, 10, 26)
S2_START = date(2026, 9, 7)
S5_START, S5_END = date(2026, 11, 3), date(2026, 11, 6)
E3_START, E3_END = date(2026, 9, 28), date(2026, 10, 26)


class Attributed(BaseModel):
    alert: Alert
    explained_by: str | None  # scenario or experiment id; None = unexplained (false alarm)


class MonitorEvaluation(BaseModel):
    tests_performed: int
    decline_alerts: int
    improvement_notices: int
    detected: dict[str, date | None]  # scenario -> first detection day
    unexplained_declines: list[Attributed]
    attributed: list[Attributed]


def _overlaps(a: Alert, start: date, end: date) -> bool:
    return a.first_period_start < end and start < a.last_period_end


def attribute(a: Alert) -> str | None:
    seg = a.segment
    if a.kind == "tracking_gap" and a.direction == "decline":
        if seg.get("platform") == "android" and _overlaps(a, S5_START, S5_END):
            return "S5"
        return None
    if a.kind != "rate":
        if a.metric == "active_users" and a.data_quality_suspect:
            return "S5"
        return None
    if a.metric == "activation_rate" and a.last_period_end > S1_START:
        return "S1"
    if (a.metric.endswith("retention") and seg.get("acquisition_channel") == "paid_social"
            and a.last_period_end > S2_START):
        return "S2"
    if a.metric.endswith("retention") and _overlaps(a, E3_START, E3_END):
        return "E3"  # the treatment half of E3 lowers retention in these cohorts
    if a.metric.endswith("retention") and a.first_period_start >= S1_START:
        return "S1"  # knock-on: fewer activated users retain less
    return None


def evaluate(run: MonitorRun) -> MonitorEvaluation:
    declines = [a for a in run.alerts if a.direction == "decline"]
    attributed = [Attributed(alert=a, explained_by=attribute(a)) for a in declines]
    detected: dict[str, date | None] = {"S1": None, "S2": None, "S5": None}
    for item in attributed:
        sid = item.explained_by
        if sid in detected:
            day = item.alert.first_detected_on
            current = detected[sid]
            detected[sid] = day if current is None else min(current, day)
    return MonitorEvaluation(
        tests_performed=run.tests_performed,
        decline_alerts=len(declines),
        improvement_notices=len(run.alerts) - len(declines),
        detected=detected,
        unexplained_declines=[x for x in attributed if x.explained_by is None],
        attributed=attributed,
    )
