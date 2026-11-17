"""Persist monitor alerts in the workflow state, keeping each alert's review status."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from pydantic import BaseModel

from flowpilot.monitor.detect import Alert, MonitorRun


class StoredAlert(BaseModel):
    alert: Alert
    status: str


def save_run(con: sqlite3.Connection, run: MonitorRun) -> int:
    """Insert new alerts and refresh existing ones; the review status is never overwritten."""
    now = datetime.now(UTC).isoformat(timespec="seconds")
    with con:
        for a in run.alerts:
            con.execute(
                """INSERT INTO alerts (alert_id, body_json, detected_on, status, updated_at)
                   VALUES (?, ?, ?, 'open', ?)
                   ON CONFLICT (alert_id) DO UPDATE SET
                       body_json = excluded.body_json,
                       detected_on = excluded.detected_on,
                       updated_at = excluded.updated_at""",
                (a.alert_id, a.model_dump_json(), a.first_detected_on.isoformat(), now),
            )
    return len(run.alerts)


def list_alerts(con: sqlite3.Connection) -> list[StoredAlert]:
    rows = con.execute(
        "SELECT body_json, status FROM alerts ORDER BY detected_on DESC, alert_id DESC"
    ).fetchall()
    return [StoredAlert(alert=Alert.model_validate_json(body), status=status)
            for body, status in rows]
