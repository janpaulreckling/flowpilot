"""Metric layer: compiles registry definitions into parameterized SQL over the analytics store.

Rules enforced here (docs/METRICS.md):
- one definition per metric, read from registry.yaml;
- dimension names are checked against the registry, filter values are bound as parameters;
- every row says whether its period is complete (fully inside the requested range and mature),
  so callers never compare incomplete with complete periods;
- a period without any units has value None, never 0.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import cache
from importlib import resources
from typing import Any, Literal

import duckdb
import yaml
from pydantic import BaseModel, Field

Grain = Literal["day", "week"]
Kind = Literal[
    "cohort_rate", "cohort_count", "trial_conversion", "active_users", "stickiness",
    "feature_adoption", "event_volume", "session_volume",
]
CORE_EVENTS = ("task_created", "task_completed", "comment_added", "timeline_viewed",
               "integration_used")


class MetricError(ValueError):
    """Invalid metric request (unknown metric, dimension or grain)."""


class MetricDefinition(BaseModel):
    name: str
    label: str
    description: str
    kind: Kind
    unit: str
    numerator: str | None = None
    retention_week: int | None = None
    lag_days: int = 0
    dimensions: list[str] = Field(default_factory=list)
    event: str | None = None
    platforms: list[str] | None = None

    @property
    def is_rate(self) -> bool:
        return self.kind in ("cohort_rate", "trial_conversion", "stickiness", "feature_adoption")

    @property
    def grains(self) -> tuple[Grain, ...]:
        if self.kind in ("stickiness", "feature_adoption"):
            return ("week",)
        return ("day", "week")


class MetricRow(BaseModel):
    period: date
    segment: str | None
    numerator: int
    denominator: int | None
    value: float | None
    complete: bool


class MetricResult(BaseModel):
    metric: str
    label: str
    unit: str
    is_rate: bool
    grain: Grain
    filters: dict[str, list[str]]
    group_by: str | None
    data_end_exclusive: date
    rows: list[MetricRow]


class FunnelStep(BaseModel):
    step: str
    segment: str | None
    users: int
    rate_from_start: float | None
    rate_from_previous: float | None


class FunnelResult(BaseModel):
    window_days: int
    complete: bool
    steps: list[FunnelStep]


@cache
def load_registry() -> tuple[dict[str, MetricDefinition], tuple[str, ...]]:
    raw: dict[str, Any] = yaml.safe_load(
        resources.files("flowpilot.metrics").joinpath("registry.yaml").read_text()
    )
    cohort_dims = tuple(raw["cohort_dimensions"])
    metrics: dict[str, MetricDefinition] = {}
    for name, spec in raw["metrics"].items():
        d = MetricDefinition(name=name, **spec)
        if d.kind in ("cohort_rate", "cohort_count", "trial_conversion"):
            d.dimensions = list(cohort_dims)
        if d.kind == "cohort_rate" and (d.numerator is None) == (d.retention_week is None):
            raise MetricError(f"{name}: cohort_rate needs exactly one of numerator/retention_week")
        metrics[name] = d
    return metrics, cohort_dims


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


class MetricEngine:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self.con = con
        self.metrics, _ = load_registry()
        row = con.execute(
            "SELECT value FROM dataset_info WHERE key = 'period_end_exclusive'"
        ).fetchone()
        if row is None:
            raise MetricError("dataset_info.period_end_exclusive missing")
        self.data_end = date.fromisoformat(str(row[0]))

    # ---- public API ---------------------------------------------------------------------
    def definition(self, metric: str) -> MetricDefinition:
        try:
            return self.metrics[metric]
        except KeyError:
            raise MetricError(f"unknown metric {metric!r}") from None

    def query(
        self,
        metric: str,
        start: date,
        end: date,
        grain: Grain = "week",
        filters: dict[str, list[str]] | None = None,
        group_by: str | None = None,
    ) -> MetricResult:
        d = self.definition(metric)
        filters = filters or {}
        if grain not in d.grains:
            raise MetricError(f"{metric} supports grains {d.grains}, not {grain!r}")
        if start >= end:
            raise MetricError("start must be before end")
        for dim in [*filters, *([group_by] if group_by else [])]:
            if dim not in d.dimensions:
                raise MetricError(f"{metric} cannot be filtered or grouped by {dim!r}; "
                                  f"allowed: {d.dimensions}")
        for dim, values in filters.items():
            if not values or not all(isinstance(v, str) for v in values):
                raise MetricError(f"filter {dim!r} needs a non-empty list of strings")

        sql, params = self._sql(d, start, end, grain, filters, group_by)
        raw = self.con.execute(sql, params).fetchall()
        rows = [self._row(d, grain, start, end, r) for r in raw]
        if group_by is None:
            rows = self._fill_periods(d, grain, start, end, rows)
        return MetricResult(
            metric=metric, label=d.label, unit=d.unit, is_rate=d.is_rate, grain=grain,
            filters=filters, group_by=group_by, data_end_exclusive=self.data_end, rows=rows,
        )

    def funnel(
        self, start: date, end: date, filters: dict[str, list[str]] | None = None,
        group_by: str | None = None,
    ) -> FunnelResult:
        """Onboarding funnel of signups in [start, end), each step within 7 days of signup."""
        filters = filters or {}
        _, cohort_dims = load_registry()
        for dim in [*filters, *([group_by] if group_by else [])]:
            if dim not in cohort_dims:
                raise MetricError(f"funnel cannot be filtered or grouped by {dim!r}")
        where, params = self._filters(filters, [start, end])
        seg = group_by or "NULL"
        sql = f"""
            SELECT {seg} AS segment,
                   count(*) AS signups,
                   count(*) FILTER (WHERE project_at < signup_at + INTERVAL 7 DAY) AS project,
                   count(*) FILTER (WHERE project_at < signup_at + INTERVAL 7 DAY
                                    AND invite_at < signup_at + INTERVAL 7 DAY) AS invite,
                   count(*) FILTER (WHERE project_at < signup_at + INTERVAL 7 DAY
                                    AND invite_at < signup_at + INTERVAL 7 DAY
                                    AND first_teammate_at < signup_at + INTERVAL 7 DAY) AS joined
            FROM owner_cohort
            WHERE signup_date >= ? AND signup_date < ? {where}
            GROUP BY 1 ORDER BY 1 NULLS FIRST"""
        names = ("Signed up", "Project created", "Invite sent", "Teammate joined")
        steps: list[FunnelStep] = []
        for r in self.con.execute(sql, params).fetchall():
            counts = [int(x) for x in r[1:]]
            for i, (name, n) in enumerate(zip(names, counts, strict=True)):
                steps.append(FunnelStep(
                    step=name, segment=None if r[0] is None else str(r[0]), users=n,
                    rate_from_start=n / counts[0] if counts[0] else None,
                    rate_from_previous=(n / counts[i - 1] if i and counts[i - 1] else None),
                ))
        last_signup = end - timedelta(days=1)
        complete = last_signup + timedelta(days=7) < self.data_end
        return FunnelResult(window_days=7, complete=complete, steps=steps)

    def experiment_outcomes(
        self, metric: str, experiment_id: str
    ) -> list[tuple[str, int, int, date]]:
        """Per assigned workspace: (variant, outcome sum, users, signup date).

        Owner-level metrics contribute one user per workspace. Uses the same definitions as
        `query`, so experiment results and dashboards cannot disagree on a metric.
        """
        d = self.definition(metric)
        if d.kind == "trial_conversion":
            hit, join = "t.next_plan = 'team'", "JOIN trial_outcomes t USING (workspace_id)"
        elif d.kind == "cohort_rate":
            hit, join = self._cohort_hit(d), ""
        else:
            raise MetricError(f"{metric} is not a per-signup metric")
        rows = self.con.execute(f"""
            SELECT a.variant, CAST(coalesce({hit}, false) AS INTEGER), 1, o.signup_date
            FROM experiment_assignments a
            JOIN owner_cohort o USING (workspace_id) {join}
            WHERE a.experiment_id = ?
            ORDER BY a.workspace_id""", [experiment_id]).fetchall()
        return [(str(v), int(y), int(n), sd) for v, y, n, sd in rows]

    @staticmethod
    def _cohort_hit(d: MetricDefinition) -> str:
        if d.retention_week is not None:
            lo, hi = 7 * d.retention_week, 7 * d.retention_week + 6
            return (f"EXISTS (SELECT 1 FROM user_active_days a WHERE a.user_id = o.user_id "
                    f"AND a.day BETWEEN o.signup_date + {lo} AND o.signup_date + {hi})")
        return f"coalesce(({d.numerator}), false)"

    # ---- SQL ----------------------------------------------------------------------------
    @staticmethod
    def _filters(filters: dict[str, list[str]], params: list[Any]) -> tuple[str, list[Any]]:
        clauses = []
        for dim, values in sorted(filters.items()):
            clauses.append(f"AND {dim} IN ({', '.join('?' for _ in values)})")
            params.extend(values)
        return " ".join(clauses), params

    def _sql(
        self, d: MetricDefinition, start: date, end: date, grain: Grain,
        filters: dict[str, list[str]], group_by: str | None,
    ) -> tuple[str, list[Any]]:
        seg = group_by or "NULL"

        def period(col: str) -> str:
            return f"CAST(date_trunc('week', {col}) AS DATE)" if grain == "week" else col

        if d.kind in ("cohort_rate", "cohort_count"):
            hit = "1" if d.kind == "cohort_count" else self._cohort_hit(d)
            where, params = self._filters(filters, [start, end])
            return f"""
                SELECT {period('signup_date')} AS period, {seg} AS segment,
                       sum(CAST({hit} AS INTEGER)) AS num, count(*) AS den
                FROM owner_cohort o
                WHERE signup_date >= ? AND signup_date < ? {where}
                GROUP BY 1, 2 ORDER BY 1, 2""", params

        if d.kind == "trial_conversion":
            where, params = self._filters(filters, [start, end])
            return f"""
                SELECT {period('o.signup_date')} AS period, {seg} AS segment,
                       count(*) FILTER (WHERE t.next_plan = 'team') AS num, count(*) AS den
                FROM owner_cohort o JOIN trial_outcomes t USING (workspace_id)
                WHERE o.signup_date >= ? AND o.signup_date < ? {where}
                GROUP BY 1, 2 ORDER BY 1, 2""", params

        if d.kind == "active_users":
            where, params = self._filters(filters, [start, end])
            return f"""
                SELECT {period('day')} AS period, {seg} AS segment,
                       count(DISTINCT user_id) AS num, NULL AS den
                FROM user_active_days WHERE day >= ? AND day < ? {where}
                GROUP BY 1, 2 ORDER BY 1, 2""", params

        if d.kind == "stickiness":
            where, params = self._filters(filters, [start, end])
            return f"""
                WITH daily AS (
                    SELECT day, {seg} AS segment, count(DISTINCT user_id) AS dau
                    FROM user_active_days WHERE day >= ? AND day < ? {where} GROUP BY 1, 2),
                weekly AS (
                    SELECT CAST(date_trunc('week', day) AS DATE) AS period, {seg} AS segment,
                           count(DISTINCT user_id) AS wau
                    FROM user_active_days WHERE day >= ? AND day < ? {where} GROUP BY 1, 2)
                SELECT w.period, w.segment, coalesce(sum(daily.dau), 0) AS num, 7 * w.wau AS den
                FROM weekly w LEFT JOIN daily
                  ON CAST(date_trunc('week', daily.day) AS DATE) = w.period
                 AND daily.segment IS NOT DISTINCT FROM w.segment
                GROUP BY w.period, w.segment, w.wau ORDER BY 1, 2""", params + params

        if d.kind == "feature_adoption":
            assert d.event is not None and d.platforms is not None
            plats = ", ".join("?" for _ in d.platforms)
            params = [start, end, *d.platforms, d.event, *d.platforms, start, end]
            return f"""
                WITH active AS (
                    SELECT DISTINCT CAST(date_trunc('week', day) AS DATE) AS period, user_id
                    FROM user_active_days
                    WHERE day >= ? AND day < ? AND platform IN ({plats})),
                used AS (
                    SELECT DISTINCT CAST(date_trunc('week', occurred_at) AS DATE) AS period,
                           user_id
                    FROM events WHERE event_name = ? AND platform IN ({plats})
                      AND CAST(occurred_at AS DATE) >= ? AND CAST(occurred_at AS DATE) < ?)
                SELECT a.period, NULL AS segment, count(u.user_id) AS num, count(*) AS den
                FROM active a LEFT JOIN used u USING (period, user_id)
                GROUP BY 1 ORDER BY 1""", params

        table = "daily_event_counts" if d.kind == "event_volume" else "daily_sessions"
        where, params = self._filters(filters, [start, end])
        return f"""
            SELECT {period('day')} AS period, {seg} AS segment, sum(n) AS num, NULL AS den
            FROM {table} WHERE day >= ? AND day < ? {where}
            GROUP BY 1, 2 ORDER BY 1, 2""", params

    # ---- rows ---------------------------------------------------------------------------
    def _complete(self, d: MetricDefinition, grain: Grain, p: date, start: date, end: date) -> bool:
        last = p + timedelta(days=6 if grain == "week" else 0)
        full = p >= start and last < end
        lag = d.lag_days if d.kind in ("cohort_rate", "cohort_count", "trial_conversion") else 0
        return full and last + timedelta(days=lag) < self.data_end

    def _row(self, d: MetricDefinition, grain: Grain, start: date, end: date,
             r: tuple[Any, ...]) -> MetricRow:
        p, seg, num, den = r
        num = int(num or 0)
        den = None if den is None else int(den)
        value = (num / den if den else None) if d.is_rate else float(num)
        return MetricRow(period=p, segment=None if seg is None else str(seg), numerator=num,
                         denominator=den, value=value,
                         complete=self._complete(d, grain, p, start, end))

    def _fill_periods(self, d: MetricDefinition, grain: Grain, start: date, end: date,
                      rows: list[MetricRow]) -> list[MetricRow]:
        """Add periods without any units: value None for rates, 0 for counts (a full day of
        data with no events is a real zero; a rate over nobody is undefined)."""
        have = {r.period for r in rows}
        p = _week_start(start) if grain == "week" else start
        step = timedelta(days=7 if grain == "week" else 1)
        out = list(rows)
        last_day = min(end, self.data_end)
        while p < last_day:
            if p not in have:
                out.append(MetricRow(
                    period=p, segment=None, numerator=0,
                    denominator=0 if d.is_rate else None,
                    value=None if d.is_rate else 0.0,
                    complete=self._complete(d, grain, p, start, end),
                ))
            p += step
        return sorted(out, key=lambda r: r.period)
