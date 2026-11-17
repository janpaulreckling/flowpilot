from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from flowpilot.api.app import app
from flowpilot.cli import main
from tests.conftest import World

WRITE = {"X-FlowPilot": "1"}


@pytest.fixture()
def client(world: World, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FLOWPILOT_DATA_DIR", str(world.db_path.parent))
    return TestClient(app, headers=WRITE)


def test_metric_catalog_lists_definitions(client: TestClient) -> None:
    names = {m["name"] for m in client.get("/api/metrics").json()}
    assert {"activation_rate", "week4_retention", "trial_to_paid", "active_users"} <= names


def test_metric_query_with_filter_and_group(client: TestClient) -> None:
    r = client.get("/api/metrics/activation_rate", params={
        "start": "2026-09-07", "end": "2026-10-05", "group_by": "signup_platform",
        "filter": ["acquisition_channel:organic_search", "acquisition_channel:referral"]})
    assert r.status_code == 200
    body = r.json()
    assert body["filters"] == {"acquisition_channel": ["organic_search", "referral"]}
    assert {row["segment"] for row in body["rows"]} <= {"web", "ios", "android"}


@pytest.mark.parametrize("params", [
    {"start": "2026-09-07", "end": "2026-10-05", "group_by": "password"},
    {"start": "2026-09-07", "end": "2026-10-05", "filter": ["no-colon"]},
    {"start": "2026-10-05", "end": "2026-09-07"},
])
def test_bad_requests_are_400(client: TestClient, params: dict[str, str | list[str]]) -> None:
    assert client.get("/api/metrics/activation_rate", params=params).status_code == 400


def test_funnel_endpoint(client: TestClient) -> None:
    body = client.get("/api/funnel", params={"start": "2026-09-07", "end": "2026-10-05"}).json()
    assert [s["step"] for s in body["steps"]] == [
        "Signed up", "Project created", "Invite sent", "Teammate joined"]


def test_monitor_alerts_are_stored_and_keep_their_status(
    world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "flowpilot.duckdb").write_bytes(world.db_path.read_bytes())
    monkeypatch.setenv("FLOWPILOT_DATA_DIR", str(data))
    main(["monitor"])
    client = TestClient(app, headers=WRITE)
    first = client.get("/api/alerts").json()
    assert first, "the small world should still produce some alerts or notices"
    assert all(a["status"] == "open" for a in first)
    if first:
        con = sqlite3.connect(data / "appstate.sqlite")
        con.execute("UPDATE alerts SET status = 'reviewed' WHERE alert_id = ?",
                    (first[0]["alert"]["alert_id"],))
        con.commit()
        con.close()
        main(["monitor"])  # re-running must not reset a human review status
        again = {a["alert"]["alert_id"]: a["status"] for a in client.get("/api/alerts").json()}
        assert again[first[0]["alert"]["alert_id"]] == "reviewed"


def test_experiment_endpoints(client: TestClient) -> None:
    listed = client.get("/api/experiments").json()
    assert [e["experiment_id"] for e in listed] == ["E2", "E1", "E3", "E4"]
    detail = client.get("/api/experiments/E4").json()
    assert detail["integrity"][0]["name"] == "Sample ratio"
    assert client.get("/api/experiments/E9").status_code == 404


def test_planner(client: TestClient) -> None:
    body = client.get("/api/planner", params={"baseline": 0.38, "mde_abs": 0.03,
                                              "weekly_units": 2500}).json()
    assert 4_100 <= body["units_per_arm"] <= 4_200
    assert 3.0 < body["weeks_needed"] < 3.5
    assert client.get("/api/planner", params={"baseline": 0.99, "mde_abs": 0.03}).status_code == 400


def test_investigation_is_run_stored_and_reloaded(
    world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "flowpilot.duckdb").write_bytes(world.db_path.read_bytes())
    monkeypatch.setenv("FLOWPILOT_DATA_DIR", str(data))
    main(["monitor"])
    client = TestClient(app, headers=WRITE)
    alert_id = client.get("/api/alerts").json()[0]["alert"]["alert_id"]
    record = client.post(f"/api/alerts/{alert_id}/investigate").json()
    assert record["report"]["mode"] == "rule_based"
    assert record["evidence"] and record["evidence"][0]["evidence_id"] == "E-1"
    assert record["status"] in ("completed", "failed")
    again = client.get(f"/api/investigations/{record['investigation_id']}").json()
    assert again["report"] == record["report"]
    assert client.get(f"/api/alerts/{alert_id}/investigations").json() == [
        record["investigation_id"]]
    status = {a["alert"]["alert_id"]: a["status"] for a in client.get("/api/alerts").json()}
    assert status[alert_id] == "investigating"
    assert client.post("/api/alerts/A-9999/investigate").status_code == 404


def test_llm_mode_is_refused_without_a_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assert client.get("/api/capabilities").json() == {"llm_enabled": False, "model": None}
    r = client.post("/api/alerts/A-0001/investigate", params={"mode": "llm"})
    assert r.status_code == 409 and "Rule-based" in r.json()["detail"]


def test_decisions_require_a_note_and_an_existing_subject(
    world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "flowpilot.duckdb").write_bytes(world.db_path.read_bytes())
    monkeypatch.setenv("FLOWPILOT_DATA_DIR", str(data))
    main(["monitor"])
    client = TestClient(app, headers=WRITE)
    alert_id = client.get("/api/alerts").json()[0]["alert"]["alert_id"]
    inv = client.post(f"/api/alerts/{alert_id}/investigate").json()["investigation_id"]
    base = {"subject_type": "proposal", "subject_id": inv, "outcome": "approved"}
    assert client.post("/api/decisions", json={**base, "note": "   "}).status_code == 422
    assert client.post("/api/decisions", json={**base, "subject_id": "INV-x",
                                               "note": "ok"}).status_code == 404
    assert client.post("/api/decisions", json={"subject_type": "experiment",
                                               "subject_id": "E9", "outcome": "approved",
                                               "note": "ok"}).status_code == 404
    made = client.post("/api/decisions", json={**base, "note": "Ship the fix in 4.13."})
    assert made.status_code == 201
    assert client.get("/api/decisions").json()[0]["note"] == "Ship the fix in 4.13."
    status = {a["alert"]["alert_id"]: a["status"] for a in client.get("/api/alerts").json()}
    assert status[alert_id] == "reviewed"


def test_writes_need_the_header_and_a_local_origin(
    world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "flowpilot.duckdb").write_bytes(world.db_path.read_bytes())
    monkeypatch.setenv("FLOWPILOT_DATA_DIR", str(data))
    main(["monitor"])
    alert_id = TestClient(app).get("/api/alerts").json()[0]["alert"]["alert_id"]
    bare = TestClient(app)
    assert bare.post(f"/api/alerts/{alert_id}/investigate").status_code == 403
    foreign = TestClient(app, headers={**WRITE, "Origin": "https://evil.example"})
    assert foreign.post(f"/api/alerts/{alert_id}/investigate").status_code == 403
    local = TestClient(app, headers={**WRITE, "Origin": "http://localhost:5173"})
    assert local.post(f"/api/alerts/{alert_id}/investigate").status_code == 200


def test_second_run_while_one_is_running_is_refused(
    world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from flowpilot.appstate import db as appdb
    from flowpilot.appstate import investigations as inv_store

    data = tmp_path / "data"
    data.mkdir()
    (data / "flowpilot.duckdb").write_bytes(world.db_path.read_bytes())
    monkeypatch.setenv("FLOWPILOT_DATA_DIR", str(data))
    main(["monitor"])
    client = TestClient(app, headers=WRITE)
    alert_id = client.get("/api/alerts").json()[0]["alert"]["alert_id"]
    con = appdb.connect(data / "appstate.sqlite")
    running = inv_store.start(con, alert_id, "rule_based")
    con.close()
    r = client.post(f"/api/alerts/{alert_id}/investigate")
    assert r.status_code == 409 and running in r.json()["detail"]


@pytest.mark.parametrize("params", [
    {"start": "0001-01-02", "end": "2100-01-01", "grain": "day"},
    {"start": "2025-01-01", "end": "9999-12-31"},
])
def test_huge_ranges_are_clamped_to_the_data(client: TestClient,
                                             params: dict[str, str]) -> None:
    r = client.get("/api/metrics/signups", params=params)
    assert r.status_code == 200 and len(r.content) < 200_000
    assert client.get("/api/funnel", params={"start": "2025-01-01",
                                             "end": "9999-12-31"}).status_code == 200
    assert client.get("/api/metrics/signups", params={"start": "1990-01-01",
                                                      "end": "1991-01-01"}).status_code == 400
