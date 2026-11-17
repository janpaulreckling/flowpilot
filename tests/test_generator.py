"""The synthetic world must be reproducible and internally consistent."""

from __future__ import annotations

import duckdb
import pytest

from flowpilot.generator.config import WorldConfig
from flowpilot.generator.simulate import INJECTION_STRINGS, planned_units_per_arm, simulate
from tests.conftest import World


def scalar(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    row = con.execute(sql).fetchone()
    assert row is not None
    return int(row[0])


def test_same_seed_gives_identical_tables() -> None:
    a = simulate(WorldConfig(scale=0.02, seed=7)).tables
    b = simulate(WorldConfig(scale=0.02, seed=7)).tables
    assert a.keys() == b.keys()
    for name in a:
        assert a[name].equals(b[name]), name


def test_different_seed_gives_different_data() -> None:
    a = simulate(WorldConfig(scale=0.02, seed=7)).tables["events"]
    b = simulate(WorldConfig(scale=0.02, seed=8)).tables["events"]
    assert not a.equals(b)


@pytest.mark.parametrize(
    ("description", "sql"),
    [
        ("event before the user's signup",
         "SELECT count(*) FROM events e JOIN users u USING (user_id) "
         "WHERE e.occurred_at < u.signup_at"),
        ("event outside its session",
         "SELECT count(*) FROM events e JOIN sessions s USING (session_id) "
         "WHERE e.occurred_at < s.started_at OR e.occurred_at > s.ended_at"),
        ("event user differs from session user",
         "SELECT count(*) FROM events e JOIN sessions s USING (session_id) "
         "WHERE e.user_id <> s.user_id"),
        ("event after the end of the period",
         "SELECT count(*) FROM events WHERE occurred_at >= "
         "(SELECT value FROM dataset_info WHERE key = 'period_end_exclusive')::TIMESTAMPTZ"),
        ("session before the user's signup",
         "SELECT count(*) FROM sessions s JOIN users u USING (user_id) "
         "WHERE s.started_at < u.signup_at"),
        ("workspace without exactly one owner",
         "SELECT count(*) FROM (SELECT workspace_id FROM users GROUP BY 1 "
         "HAVING count(*) FILTER (WHERE role = 'owner') <> 1)"),
        ("owner is not the recorded founder",
         "SELECT count(*) FROM users u JOIN workspaces w USING (workspace_id) "
         "WHERE u.role = 'owner' AND u.user_id <> w.founder_user_id"),
        ("member joined before the founder sent an invite",
         "SELECT count(*) FROM users m JOIN workspaces w USING (workspace_id) "
         "WHERE m.role = 'member' AND NOT EXISTS (SELECT 1 FROM events e WHERE "
         "e.user_id = w.founder_user_id AND e.event_name = 'invite_sent' "
         "AND e.occurred_at <= m.signup_at)"),
        ("invite sent before the founder's first project",
         "SELECT count(*) FROM events i WHERE i.event_name = 'invite_sent' AND NOT EXISTS "
         "(SELECT 1 FROM events p WHERE p.user_id = i.user_id "
         "AND p.event_name = 'project_created' AND p.occurred_at <= i.occurred_at)"),
        ("mobile session on a version not yet released",
         "SELECT count(*) FROM sessions s JOIN releases r "
         "ON r.platform = s.platform AND r.version = s.app_version "
         "WHERE s.started_at < r.released_at"),
        ("mobile session on an unknown version",
         "SELECT count(*) FROM sessions s WHERE s.platform <> 'web' AND NOT EXISTS "
         "(SELECT 1 FROM releases r WHERE r.platform = s.platform AND r.version = s.app_version)"),
        ("web session with an app version",
         "SELECT count(*) FROM sessions WHERE platform = 'web' AND app_version <> 'web'"),
        ("overlapping subscriptions",
         "SELECT count(*) FROM subscriptions a JOIN subscriptions b USING (workspace_id) "
         "WHERE a.started_at < b.started_at "
         "AND coalesce(a.ended_at, 'infinity'::TIMESTAMPTZ) > b.started_at"),
        ("first subscription is not a trial starting at signup",
         "SELECT count(*) FROM workspaces w WHERE NOT EXISTS (SELECT 1 FROM subscriptions s "
         "WHERE s.workspace_id = w.workspace_id AND s.plan = 'team_trial' "
         "AND s.started_at = w.created_at)"),
        ("assignment outside the experiment window",
         "SELECT count(*) FROM experiment_assignments a JOIN experiments x USING (experiment_id) "
         "WHERE a.assigned_at < x.started_at OR a.assigned_at >= x.ended_at"),
        ("assignment does not match workspace creation",
         "SELECT count(*) FROM experiment_assignments a JOIN workspaces w USING (workspace_id) "
         "WHERE a.assigned_at <> w.created_at"),
        ("exposure without assignment",
         "SELECT count(*) FROM experiment_exposures x LEFT JOIN experiment_assignments a "
         "USING (experiment_id, workspace_id) WHERE a.workspace_id IS NULL"),
        ("exposure before assignment",
         "SELECT count(*) FROM experiment_exposures x JOIN experiment_assignments a "
         "USING (experiment_id, workspace_id) WHERE x.exposed_at < a.assigned_at"),
        ("timeline view outside web or before launch",
         "SELECT count(*) FROM events WHERE event_name = 'timeline_viewed' "
         "AND (platform <> 'web' OR occurred_at < '2026-08-17'::TIMESTAMPTZ)"),
    ],
)
def test_consistency(con: duckdb.DuckDBPyConnection, description: str, sql: str) -> None:
    assert scalar(con, sql) == 0, description


def test_ground_truth_lists_every_scenario(world: World) -> None:
    truth = world.result.ground_truth
    assert [s["id"] for s in truth["scenarios"]] == ["S1", "S1b", "S2", "S3", "S4", "S5"]
    assert [e["id"] for e in truth["experiments"]] == ["E1", "E2", "E3", "E4"]
    assert "Synthetic" in truth["disclaimer"]


def test_s5_tracking_gap_has_no_task_created_but_sessions_continue(
    con: duckdb.DuckDBPyConnection, world: World
) -> None:
    window = ("platform = 'android' AND app_version = '7.3' AND occurred_at >= '2026-11-03' "
              "AND occurred_at < '2026-11-06'")
    assert scalar(con, f"SELECT count(*) FROM events WHERE event_name = 'task_created' "
                       f"AND {window}") == 0
    assert scalar(con, f"SELECT count(*) FROM events WHERE {window}") > 0
    assert world.result.ground_truth["realized"]["s5_dropped_events"] > 0


def test_e4_assignment_log_misses_safari_treatment(
    con: duckdb.DuckDBPyConnection, world: World
) -> None:
    missing = scalar(con, (
        "SELECT count(*) FROM experiment_assignments a JOIN users u "
        "ON u.workspace_id = a.workspace_id AND u.role = 'owner' "
        "WHERE a.experiment_id = 'E4' AND a.variant = 'treatment' AND u.browser = 'safari'"))
    assert missing == 0
    assert world.result.ground_truth["realized"]["e4_dropped_assignments"] > 0


def test_injection_strings_are_present_as_data(
    con: duckdb.DuckDBPyConnection, world: World
) -> None:
    realized = world.result.ground_truth["realized"]
    in_names = scalar(con, "SELECT count(*) FROM workspaces WHERE name IN (" +
                      ", ".join(f"'{s}'" for s in INJECTION_STRINGS) + ")")
    assert in_names == realized["injected_workspace_names"]
    in_projects = scalar(con, "SELECT count(*) FROM events WHERE event_name = 'project_created' "
                         "AND (" + " OR ".join(f"properties LIKE '%{s[:20]}%'"
                                              for s in INJECTION_STRINGS) + ")")
    assert in_projects == realized["injected_project_names"]


def test_planned_sample_size_matches_textbook_formula() -> None:
    # 0.38 -> 0.41, alpha 0.05 two-sided, power 0.8: about 4,150 per arm.
    assert 4_100 <= planned_units_per_arm(0.38, 0.03) <= 4_200
