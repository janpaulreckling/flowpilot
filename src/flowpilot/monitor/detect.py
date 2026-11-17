"""Deterministic anomaly monitor (D12). Method and thresholds: docs/MONITORING.md.

The parameters below were fixed before the monitor was first run against the data. The monitor
reads metrics only through the metric layer and never reads the ground truth.
"""

from __future__ import annotations

import hashlib
import math
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel

from flowpilot.metrics.engine import MetricEngine

# ---- fixed parameters (docs/MONITORING.md, 2026-11-17) ----------------------------------
RATE_METRICS: dict[str, float] = {  # metric -> practical threshold (absolute)
    "activation_rate": 0.02,
    "week1_retention": 0.03,
    "week4_retention": 0.03,
    "trial_to_paid": 0.015,
}
SEGMENT_DIMENSIONS = ("signup_platform", "acquisition_channel", "company_size")
BASELINE_WEEKS = 8
WINDOWS = (1, 4)
Z_OVERALL, Z_SEGMENT = 3.0, 3.5
MIN_N = {1: 300, 4: 1000}

COUNT_BASELINE_WEEKS = 4
COUNT_Z, COUNT_MIN_REL = 4.0, 0.15
SCALE_FLOOR = 0.05
GAP_SESSION_TOLERANCE = 0.10
CORE_EVENTS = ("task_created", "task_completed", "comment_added", "timeline_viewed",
               "integration_used")
PLATFORMS = ("web", "ios", "android")

Direction = Literal["decline", "improvement"]


class Detection(BaseModel):
    """One threshold crossing for one period."""

    metric: str
    kind: Literal["rate", "count", "tracking_gap"]
    window: str  # "1w", "4w" or "day"
    period_start: date
    period_end: date  # exclusive
    segment: dict[str, str]
    observed: float
    expected: float
    z: float
    n: int | None
    direction: Direction


class Alert(BaseModel):
    """Consecutive detections of the same metric, segment and direction, merged."""

    alert_id: str
    metric: str
    kind: Literal["rate", "count", "tracking_gap"]
    segment: dict[str, str]
    direction: Direction
    severity: Literal["alert", "notice"]
    first_period_start: date
    last_period_end: date
    first_detected_on: date  # the day the first detection could have been made
    observed: float  # at first detection
    expected: float
    max_abs_z: float
    windows: list[str]
    detections: int
    data_quality_suspect: bool = False
    # The strongest single detection: the window that actually triggered the alert.
    peak_window: str = ""
    peak_period_start: date | None = None
    peak_period_end: date | None = None
    peak_observed: float = 0.0
    peak_expected: float = 0.0
    peak_z: float = 0.0


class MonitorRun(BaseModel):
    tests_performed: int
    alerts: list[Alert]
    rate_tests_overall: int = 0
    rate_tests_segment: int = 0

    @property
    def expected_null_crossings(self) -> float:
        """Statistical-threshold crossings expected by chance alone (two-sided, before the
        practical and size filters): about 0.0027 per overall test, 0.00047 per segment test."""
        return self.rate_tests_overall * 0.0027 + self.rate_tests_segment * 0.000465


@dataclass
class _Week:
    start: date
    num: int
    den: int


def _rate_detections(engine: MetricEngine, start: date
                     ) -> tuple[list[Detection], int, int]:
    detections: list[Detection] = []
    tests = 0
    seg_tests = 0
    for metric, practical in RATE_METRICS.items():
        series: dict[tuple[tuple[str, str], ...], list[_Week]] = {}
        overall = engine.query(metric, start, engine.data_end)
        series[()] = [_Week(r.period, r.numerator, r.denominator or 0)
                      for r in overall.rows if r.complete]
        for dim in SEGMENT_DIMENSIONS:
            res = engine.query(metric, start, engine.data_end, group_by=dim)
            by_value: dict[str, list[_Week]] = {}
            for r in res.rows:
                if r.complete and r.segment is not None:
                    by_value.setdefault(r.segment, []).append(
                        _Week(r.period, r.numerator, r.denominator or 0))
            for value, weeks in by_value.items():
                series[((dim, value),)] = weeks
        for seg, weeks in series.items():
            z_thr = Z_OVERALL if not seg else Z_SEGMENT
            for k in WINDOWS:
                for t in range(BASELINE_WEEKS + k - 1, len(weeks)):
                    window = weeks[t - k + 1 : t + 1]
                    base = weeks[t - k - BASELINE_WEEKS + 1 : t - k + 1]
                    if len(base) < BASELINE_WEEKS or any(w.den == 0 for w in base):
                        continue
                    n_obs = sum(w.den for w in window)
                    n_base = sum(w.den for w in base)
                    if n_obs < MIN_N[k]:
                        continue
                    tests += 1
                    seg_tests += bool(seg)
                    obs = sum(w.num for w in window) / n_obs
                    p = sum(w.num for w in base) / n_base
                    rates = [w.num / w.den for w in base]
                    binom = statistics.fmean(p * (1 - p) / w.den for w in base)
                    s2x = max(0.0, statistics.variance(rates) - binom)
                    # v2 (M1): the baseline mean also carries extra-binomial variance.
                    se = math.sqrt(s2x * (1 / k + 1 / BASELINE_WEEKS)
                                   + p * (1 - p) * (1 / n_obs + 1 / n_base))
                    if se == 0:
                        continue
                    z = (obs - p) / se
                    if abs(z) >= z_thr and abs(obs - p) >= practical:
                        last = window[-1].start
                        detections.append(Detection(
                            metric=metric, kind="rate", window=f"{k}w",
                            period_start=window[0].start,
                            period_end=last + timedelta(days=7),
                            segment=dict(seg), observed=obs, expected=p, z=z, n=n_obs,
                            direction="decline" if obs < p else "improvement",
                        ))
    return detections, tests, seg_tests


def _daily(engine: MetricEngine, metric: str, start: date,
           filters: dict[str, list[str]]) -> dict[date, float]:
    res = engine.query(metric, start, engine.data_end, grain="day", filters=filters)
    return {r.period: float(r.value or 0.0) for r in res.rows if r.complete}


def _robust(series: dict[date, float], d: date) -> tuple[float, float] | None:
    prior = [series.get(d - timedelta(days=7 * i)) for i in range(1, COUNT_BASELINE_WEEKS + 1)]
    if any(v is None for v in prior):
        return None
    vals = [float(v) for v in prior if v is not None]
    med = statistics.median(vals)
    mad = statistics.median(abs(v - med) for v in vals)
    return med, max(1.4826 * mad, SCALE_FLOOR * med)


def _count_detections(engine: MetricEngine, start: date) -> tuple[list[Detection], int]:
    detections: list[Detection] = []
    tests = 0
    series: list[tuple[str, dict[str, str], dict[date, float]]] = [
        ("active_users", {}, _daily(engine, "active_users", start, {}))
    ]
    sessions: dict[str, dict[date, float]] = {}
    for plat in PLATFORMS:
        series.append(("active_users", {"platform": plat},
                       _daily(engine, "active_users", start, {"platform": [plat]})))
        sessions[plat] = _daily(engine, "session_volume", start, {"platform": [plat]})
        series.append(("session_volume", {"platform": plat}, sessions[plat]))
        for ev in CORE_EVENTS:
            s = _daily(engine, "event_volume", start,
                       {"platform": [plat], "event_name": [ev]})
            if sum(s.values()) > 0:
                series.append(("event_volume", {"platform": plat, "event_name": ev}, s))
    for metric, seg, values in series:
        for d in sorted(values):
            base = _robust(values, d)
            if base is None or base[0] == 0:
                continue  # no baseline, or expected zero: relative change undefined
            tests += 1
            med, scale = base
            obs = values[d]
            z = (obs - med) / scale
            rel = (obs - med) / med if med else 0.0
            if abs(z) >= COUNT_Z and abs(rel) >= COUNT_MIN_REL:
                kind: Literal["count", "tracking_gap"] = "count"
                if metric == "event_volume":
                    sess = _robust(sessions[seg["platform"]], d)
                    s_obs = sessions[seg["platform"]].get(d)
                    if sess and s_obs is not None and sess[0] and \
                            abs(s_obs - sess[0]) / sess[0] <= GAP_SESSION_TOLERANCE:
                        kind = "tracking_gap"
                detections.append(Detection(
                    metric=metric, kind=kind, window="day", period_start=d,
                    period_end=d + timedelta(days=1), segment=seg, observed=obs, expected=med,
                    z=z, n=None, direction="decline" if obs < med else "improvement",
                ))
    return detections, tests


def _merge(detections: list[Detection], engine: MetricEngine) -> list[Alert]:
    """Merge detections of the same metric/segment/direction whose periods touch."""
    groups: dict[tuple[str, str, tuple[tuple[str, str], ...], str], list[Detection]] = {}
    for det in detections:
        key = (det.metric, det.kind, tuple(sorted(det.segment.items())), det.direction)
        groups.setdefault(key, []).append(det)
    alerts: list[Alert] = []
    for (metric, kind, seg, direction), dets in groups.items():
        dets.sort(key=lambda x: (x.period_end, x.period_start))
        episodes: list[list[Detection]] = []
        for det in dets:
            gap = timedelta(days=1 if det.window == "day" else 7)
            if episodes and det.period_start <= episodes[-1][-1].period_end + gap:
                episodes[-1].append(det)
            else:
                episodes.append([det])
        lag = engine.definition(metric).lag_days if kind == "rate" else 0
        for episode in episodes:
            first = min(episode, key=lambda x: x.period_end)
            peak = max(episode, key=lambda x: abs(x.z))
            alerts.append(Alert(
                alert_id="", metric=metric, kind=first.kind, segment=dict(seg),
                direction=first.direction,
                severity="alert" if direction == "decline" else "notice",
                first_period_start=min(x.period_start for x in episode),
                last_period_end=max(x.period_end for x in episode),
                first_detected_on=first.period_end + timedelta(days=lag),
                observed=first.observed, expected=first.expected,
                max_abs_z=max(abs(x.z) for x in episode),
                windows=sorted({x.window for x in episode}), detections=len(episode),
                peak_window=peak.window, peak_period_start=peak.period_start,
                peak_period_end=peak.period_end, peak_observed=peak.observed,
                peak_expected=peak.expected, peak_z=peak.z,
            ))
    alerts.sort(key=lambda a: (a.first_detected_on, a.metric, str(a.segment)))
    for a in alerts:
        # Stable across re-runs: derived from what the alert is about, not its position.
        ident = (f"{a.metric}|{a.kind}|{sorted(a.segment.items())}|{a.direction}|"
                 f"{a.first_period_start.isoformat()}")
        a.alert_id = "A-" + hashlib.sha1(ident.encode()).hexdigest()[:6]
    return alerts


def run_monitor(engine: MetricEngine, start: date) -> MonitorRun:
    rate, n_rate, n_seg = _rate_detections(engine, start)
    count, n_count = _count_detections(engine, start)
    alerts = _merge(rate + count, engine)
    gaps = [(a.segment.get("platform"), a.first_period_start, a.last_period_end)
            for a in alerts if a.kind == "tracking_gap"]
    for a in alerts:
        if a.kind == "count" and a.metric == "active_users":
            plat = a.segment.get("platform")
            a.data_quality_suspect = any(
                (plat is None or plat == gp)
                and a.first_period_start < ge and gs < a.last_period_end
                for gp, gs, ge in gaps)
    return MonitorRun(tests_performed=n_rate + n_count, alerts=alerts,
                      rate_tests_overall=n_rate - n_seg, rate_tests_segment=n_seg)
