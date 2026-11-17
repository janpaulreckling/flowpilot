"""The metric layer against an independent reference implementation and its own rules.

The reference below recomputes metrics in plain Python from the raw Parquet files. It shares no
code and no SQL with the metric layer, so a definition error in one shows up as a mismatch.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from datetime import date, datetime, timedelta

import duckdb
import pyarrow.parquet as pq
import pytest

from flowpilot.metrics.engine import MetricEngine, MetricError, MetricResult
from tests.conftest import World

START, END = date(2026, 5, 4), date(2026, 11, 16)
CORE = {"task_created", "task_completed", "comment_added", "timeline_viewed", "integration_used"}


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


class Reference:
    def __init__(self, world: World) -> None:
        def rows(name: str) -> list[dict[str, object]]:
            data: list[dict[str, object]] = pq.read_table(
                world.raw_dir / f"{name}.parquet").to_pylist()
            return data

        self.users = rows("users")
        self.owners = [u for u in self.users if u["role"] == "owner"]
        events = rows("events")
        self.first: dict[tuple[int, str], datetime] = {}
        self.active: dict[int, set[date]] = defaultdict(set)
        self.active_by_day: dict[date, set[int]] = defaultdict(set)
        self.timeline_web: dict[date, set[int]] = defaultdict(set)
        self.active_web_week: dict[date, set[int]] = defaultdict(set)
        for e in events:
            uid, name, ts = e["user_id"], e["event_name"], e["occurred_at"]
            assert isinstance(uid, int) and isinstance(name, str) and isinstance(ts, datetime)
            key = (uid, name)
            if key not in self.first or ts < self.first[key]:
                self.first[key] = ts
            if name in CORE:
                self.active[uid].add(ts.date())
                self.active_by_day[ts.date()].add(uid)
                if e["platform"] == "web":
                    self.active_web_week[monday(ts.date())].add(uid)
            if name == "timeline_viewed" and e["platform"] == "web":
                self.timeline_web[monday(ts.date())].add(uid)
        self.first_member: dict[int, datetime] = {}
        for u in self.users:
            if u["role"] == "member":
                ws, ts = u["workspace_id"], u["signup_at"]
                assert isinstance(ws, int) and isinstance(ts, datetime)
                if ws not in self.first_member or ts < self.first_member[ws]:
                    self.first_member[ws] = ts
        subs = rows("subscriptions")
        trial_end = {s["workspace_id"]: s["ended_at"] for s in subs if s["plan"] == "team_trial"}
        self.converted = {
            s["workspace_id"] for s in subs
            if s["plan"] == "team" and s["started_at"] == trial_end.get(s["workspace_id"])
        }

    def weekly(self, hit: object) -> dict[date, tuple[int, int]]:
        out: dict[date, list[int]] = defaultdict(lambda: [0, 0])
        for o in self.owners:
            ts = o["signup_at"]
            assert isinstance(ts, datetime)
            w = out[monday(ts.date())]
            w[1] += 1
            w[0] += int(hit(o))  # type: ignore[operator]
        return {k: (v[0], v[1]) for k, v in out.items()}

    def activated(self, o: dict[str, object]) -> bool:
        ts, uid, ws = o["signup_at"], o["user_id"], o["workspace_id"]
        assert isinstance(ts, datetime) and isinstance(uid, int) and isinstance(ws, int)
        limit = ts + timedelta(days=7)
        project = self.first.get((uid, "project_created"))
        member = self.first_member.get(ws)
        return project is not None and project < limit and member is not None and member < limit

    def retained(self, week: int) -> object:
        def hit(o: dict[str, object]) -> bool:
            ts, uid = o["signup_at"], o["user_id"]
            assert isinstance(ts, datetime) and isinstance(uid, int)
            d0 = ts.date()
            days = self.active.get(uid, set())
            return any(d0 + timedelta(days=7 * week + i) in days for i in range(7))
        return hit


@pytest.fixture(scope="module")
def ref(world: World) -> Reference:
    return Reference(world)


@pytest.fixture()
def engine(con: duckdb.DuckDBPyConnection) -> Iterator[MetricEngine]:
    yield MetricEngine(con)


def complete_rows(result: MetricResult) -> dict[date, tuple[int, int | None]]:
    return {r.period: (r.numerator, r.denominator) for r in result.rows if r.complete}


def test_activation_matches_reference(engine: MetricEngine, ref: Reference) -> None:
    got = complete_rows(engine.query("activation_rate", START, END))
    want = ref.weekly(ref.activated)
    assert got and all(got[w] == want[w] for w in got)


@pytest.mark.parametrize("week", [1, 2, 4])
def test_retention_matches_reference(engine: MetricEngine, ref: Reference, week: int) -> None:
    got = complete_rows(engine.query(f"week{week}_retention", START, END))
    want = ref.weekly(ref.retained(week))
    assert got and all(got[w] == want[w] for w in got)


def test_trial_to_paid_matches_reference(engine: MetricEngine, ref: Reference) -> None:
    got = complete_rows(engine.query("trial_to_paid", START, END))
    want = ref.weekly(lambda o: o["workspace_id"] in ref.converted)
    assert got and all(got[w] == want[w] for w in got)


def test_daily_active_users_match_reference(engine: MetricEngine, ref: Reference) -> None:
    result = engine.query("active_users", START, END, grain="day")
    for r in result.rows:
        assert r.numerator == len(ref.active_by_day.get(r.period, set())), r.period


def test_timeline_adoption_matches_reference(engine: MetricEngine, ref: Reference) -> None:
    result = engine.query("timeline_adoption", START, END)
    for r in result.rows:
        assert r.numerator == len(ref.timeline_web.get(r.period, set()))
        assert r.denominator == len(ref.active_web_week.get(r.period, set()))


def test_segments_add_up_to_the_total(engine: MetricEngine) -> None:
    total = engine.query("activation_rate", START, END)
    split = engine.query("activation_rate", START, END, group_by="signup_platform")
    for t in total.rows:
        parts = [r for r in split.rows if r.period == t.period]
        assert sum(p.numerator for p in parts) == t.numerator
        assert sum(p.denominator or 0 for p in parts) == t.denominator


def test_funnel_last_step_equals_activation(engine: MetricEngine) -> None:
    a, b = date(2026, 9, 7), date(2026, 10, 5)
    funnel = engine.funnel(a, b)
    activation = engine.query("activation_rate", a, b)
    assert funnel.complete
    assert funnel.steps[-1].users == sum(r.numerator for r in activation.rows)
    assert funnel.steps[0].users == sum(r.denominator or 0 for r in activation.rows)


def test_immature_cohorts_are_flagged(engine: MetricEngine) -> None:
    rows = engine.query("week4_retention", START, END).rows
    last_complete = max(r.period for r in rows if r.complete)
    # Week-4 needs days 28-34 after the latest signup of the cohort week.
    assert last_complete + timedelta(days=6 + 34) < END
    assert any(not r.complete for r in rows if r.period > last_complete)


def test_partial_period_at_range_edge_is_not_complete(engine: MetricEngine) -> None:
    rows = engine.query("signups", date(2026, 6, 3), date(2026, 7, 1)).rows
    assert not rows[0].complete  # the week of Jun 1 is cut at Jun 3


def test_empty_segment_is_undefined_not_zero(engine: MetricEngine) -> None:
    rows = engine.query("activation_rate", date(2026, 6, 1), date(2026, 6, 29),
                        filters={"signup_app_version": ["4.12"]}).rows
    assert rows and all(r.value is None and r.denominator == 0 for r in rows)


def test_rejects_unknown_metric_dimension_and_grain(engine: MetricEngine) -> None:
    with pytest.raises(MetricError):
        engine.query("revenue", START, END)
    with pytest.raises(MetricError):
        engine.query("activation_rate", START, END, group_by="user_id; DROP TABLE users")
    with pytest.raises(MetricError):
        engine.query("stickiness", START, END, grain="day")


def test_filter_values_are_data_not_sql(engine: MetricEngine) -> None:
    rows = engine.query("signups", START, END,
                        filters={"acquisition_channel": ["x' OR '1'='1"]}).rows
    assert all(r.numerator == 0 for r in rows)
