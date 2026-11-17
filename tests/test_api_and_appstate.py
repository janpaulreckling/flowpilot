from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from flowpilot.api.app import app
from flowpilot.appstate.db import connect
from tests.conftest import World


def test_health() -> None:
    assert TestClient(app).get("/api/health").json()["status"] == "ok"


def test_dataset_reports_synthetic_data(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLOWPILOT_DATA_DIR", str(world.db_path.parent))
    body = TestClient(app).get("/api/dataset").json()
    assert body["synthetic"] is True
    assert body["row_counts"]["events"] == world.counts["events"]
    assert body["period_start"] == "2026-05-04"


def test_dataset_without_store_is_503(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLOWPILOT_DATA_DIR", str(tmp_path))
    assert TestClient(app).get("/api/dataset").status_code == 503


def test_decision_requires_a_note(tmp_path: Path) -> None:
    con = connect(tmp_path / "app.sqlite")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO decisions VALUES ('d1', 'proposal', 'p1', 'approved', '  ', 'pm', 'now')"
        )
