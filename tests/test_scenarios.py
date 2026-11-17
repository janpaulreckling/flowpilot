"""Tolerance-band checks: the generated default dataset shows each documented scenario.

Ranges are about the expected effect plus or minus roughly three standard errors at full scale.
They check the generator against docs/DATA_SCENARIOS.md; they are not tuned to any later
analysis. The full world is generated once per test session (about 10 seconds).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest

# One row per founder: activation funnel within 7 days and weekly retention flags.
FOUNDERS = """
WITH founders AS (
    SELECT u.user_id, u.workspace_id, u.signup_at, u.signup_platform AS platform,
           u.signup_app_version AS version, u.acquisition_channel AS channel, w.company_size,
           EXISTS (SELECT 1 FROM events e WHERE e.user_id = u.user_id
                   AND e.event_name = 'project_created'
                   AND e.occurred_at < u.signup_at + INTERVAL 7 DAY) AS project,
           EXISTS (SELECT 1 FROM events e WHERE e.user_id = u.user_id
                   AND e.event_name = 'invite_sent'
                   AND e.occurred_at < u.signup_at + INTERVAL 7 DAY) AS invite,
           EXISTS (SELECT 1 FROM users m WHERE m.workspace_id = u.workspace_id
                   AND m.role = 'member' AND m.signup_at < u.signup_at + INTERVAL 7 DAY) AS joined,
           EXISTS (SELECT 1 FROM events e WHERE e.user_id = u.user_id
                   AND e.event_name = 'integration_connected') AS connected
    FROM users u JOIN workspaces w USING (workspace_id)
    WHERE u.role = 'owner'
),
active_days AS (
    SELECT DISTINCT s.user_id,
           CAST(floor(epoch(s.started_at - u.signup_at) / 86400) AS INTEGER) AS d
    FROM sessions s JOIN users u USING (user_id)
),
retention AS (
    SELECT user_id,
           max(CASE WHEN d BETWEEN 7 AND 13 THEN 1 ELSE 0 END) AS w1,
           max(CASE WHEN d BETWEEN 14 AND 20 THEN 1 ELSE 0 END) AS w2,
           max(CASE WHEN d BETWEEN 28 AND 34 THEN 1 ELSE 0 END) AS w4
    FROM active_days GROUP BY 1
),
f AS (
    SELECT founders.*, (project AND joined)::INTEGER AS activated,
           coalesce(w1, 0) AS w1, coalesce(w2, 0) AS w2, coalesce(w4, 0) AS w4
    FROM founders LEFT JOIN retention USING (user_id)
)
"""


@pytest.fixture(scope="module")
def full(full_world: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    # In-memory session with the store attached read-only, so the founder view can be
    # materialized once for all checks without write access to the store.
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    con.execute(f"ATTACH '{full_world}' AS store (READ_ONLY)")
    con.execute("USE store")
    con.execute(f"CREATE TABLE memory.main.f AS {FOUNDERS} SELECT * FROM f")
    yield con
    con.close()


def value(con: duckdb.DuckDBPyConnection, sql: str) -> float:
    row = con.execute(sql).fetchone()
    assert row is not None and row[0] is not None
    return float(row[0])


def diff(con: duckdb.DuckDBPyConnection, col: str, where_a: str, where_b: str) -> float:
    """mean(col | a) - mean(col | b) over founders."""
    return value(con, f"SELECT avg({col}) FILTER (WHERE {where_a}) - "
                      f"avg({col}) FILTER (WHERE {where_b}) FROM memory.main.f")


# Pre-window after E1 ended (Oct 11), so E1's treatment does not inflate the baseline.
PRE_S1 = "signup_at >= '2026-10-12' AND signup_at < '2026-10-26'"
POST_S1 = "signup_at >= '2026-10-26' AND signup_at < '2026-11-09'"  # 7-day window complete


def test_s1_ios_412_activation_drop_at_invite_step(full: duckdb.DuckDBPyConnection) -> None:
    ios_post = f"{POST_S1} AND platform = 'ios' AND version = '4.12'"
    ios_pre = f"{PRE_S1} AND platform = 'ios'"
    assert -0.17 <= diff(full, "activated", ios_post, ios_pre) <= -0.07
    # The break is at the invite step, not at project creation.
    assert -0.03 <= diff(full, "project::INTEGER", ios_post, ios_pre) <= 0.03
    invite_drop = value(full, (
        "SELECT avg(invite::INTEGER) FILTER (WHERE project AND " + ios_post + ") - "
        "avg(invite::INTEGER) FILTER (WHERE project AND " + ios_pre + ") FROM memory.main.f"))
    assert -0.30 <= invite_drop <= -0.15
    # Other platforms are unaffected.
    assert abs(diff(full, "activated", f"{POST_S1} AND platform <> 'ios'",
                    f"{PRE_S1} AND platform <> 'ios'")) <= 0.03


def test_s1_overall_activation_drop(full: duckdb.DuckDBPyConnection) -> None:
    # Documented as roughly 3-4 pp; the expected value is about 3.5 pp, the band allows noise.
    assert -0.05 <= diff(full, "activated", POST_S1, PRE_S1) <= -0.015


def test_s1b_mix_shift_is_real_but_explains_little(full: duckdb.DuckDBPyConnection) -> None:
    share_change = diff(full, "(channel = 'paid_search')::INTEGER", POST_S1, PRE_S1)
    assert 0.03 <= share_change <= 0.07
    # Activation change implied by the channel mix alone, holding pre-period rates fixed.
    mix_effect = value(full, f"""
        WITH s AS (
            SELECT channel,
                   count(*) FILTER (WHERE {POST_S1}) AS n_post,
                   count(*) FILTER (WHERE {PRE_S1}) AS n_pre,
                   avg(activated) FILTER (WHERE {PRE_S1}) AS rate_pre
            FROM memory.main.f GROUP BY channel
        )
        SELECT sum((n_post / (SELECT sum(n_post) FROM s) - n_pre / (SELECT sum(n_pre) FROM s))
                   * rate_pre)
        FROM s""")
    assert abs(mix_effect) <= 0.006


def test_s2_paid_social_week4_retention_drop(full: duckdb.DuckDBPyConnection) -> None:
    pre = "signup_at >= '2026-07-27' AND signup_at < '2026-09-07'"
    post = "signup_at >= '2026-09-07' AND signup_at < '2026-10-12'"  # week 4 observed
    ps = "channel = 'paid_social'"
    assert -0.12 <= diff(full, "w4", f"{post} AND {ps}", f"{pre} AND {ps}") <= -0.04
    assert abs(diff(full, "w4", f"{post} AND NOT {ps}", f"{pre} AND NOT {ps}")) <= 0.025
    # Activation is unchanged: this is a retention problem, not an onboarding problem.
    assert abs(diff(full, "activated", f"{post} AND {ps}", f"{pre} AND {ps}")) <= 0.04


def test_s3_timeline_adopted_on_web_only(full: duckdb.DuckDBPyConnection) -> None:
    web_share = value(full, """
        SELECT count(DISTINCT e.user_id) FILTER (WHERE e.event_name = 'timeline_viewed')
               / count(DISTINCT e.user_id)
        FROM events e WHERE e.platform = 'web' AND e.occurred_at >= '2026-09-14'""")
    assert web_share >= 0.10
    mobile = value(full, "SELECT count(*) FROM events WHERE event_name = 'timeline_viewed' "
                         "AND platform <> 'web'")
    assert mobile == 0


def test_s4_integration_correlation_is_confounded_by_company_size(
    full: duckdb.DuckDBPyConnection,
) -> None:
    cohort = "signup_at < '2026-10-01'"
    naive = diff(full, "w4", f"{cohort} AND connected", f"{cohort} AND NOT connected")
    assert naive >= 0.05  # the misleading raw correlation exists
    stratified = value(full, f"""
        WITH by_size AS (
            SELECT company_size,
                   avg(w4) FILTER (WHERE connected) - avg(w4) FILTER (WHERE NOT connected) AS d,
                   count(*) FILTER (WHERE connected) AS n
            FROM memory.main.f WHERE {cohort} GROUP BY 1
        )
        SELECT sum(d * n) / sum(n) FROM by_size""")
    assert abs(stratified) <= 0.02


def assignment_diff(con: duckdb.DuckDBPyConnection, experiment: str, col: str) -> float:
    return value(con, f"""
        SELECT avg({col}) FILTER (WHERE a.variant = 'treatment')
             - avg({col}) FILTER (WHERE a.variant = 'control')
        FROM experiment_assignments a JOIN memory.main.f f USING (workspace_id)
        WHERE a.experiment_id = '{experiment}'""")


def test_e1_checklist_raises_activation(full: duckdb.DuckDBPyConnection) -> None:
    assert 0.01 <= assignment_diff(full, "E1", "activated") <= 0.055


def test_e2_due_dates_have_no_effect(full: duckdb.DuckDBPyConnection) -> None:
    assert abs(assignment_diff(full, "E2", "w1")) <= 0.025


def test_e3_upgrade_prompt_hurts_week2_retention(full: duckdb.DuckDBPyConnection) -> None:
    assert -0.06 <= assignment_diff(full, "E3", "w2") <= -0.005
    conversion = value(full, """
        SELECT avg(paid) FILTER (WHERE variant = 'treatment')
             - avg(paid) FILTER (WHERE variant = 'control')
        FROM (SELECT a.variant, EXISTS (SELECT 1 FROM subscriptions s
                     WHERE s.workspace_id = a.workspace_id AND s.plan = 'team')::INTEGER AS paid
              FROM experiment_assignments a WHERE a.experiment_id = 'E3')""")
    # True uplift +1.5 pp (SE about 0.6 pp): the lower bound catches a lost uplift.
    assert 0.005 <= conversion <= 0.035


def test_e4_sample_ratio_mismatch(full: duckdb.DuckDBPyConnection) -> None:
    share = value(full, "SELECT avg((variant = 'treatment')::INTEGER) "
                        "FROM experiment_assignments WHERE experiment_id = 'E4'")
    assert 0.44 <= share <= 0.48
