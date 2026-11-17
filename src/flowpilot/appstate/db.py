"""Workflow state in SQLite, kept separate from the read-only analytics store.

Alerts, investigations, the evidence behind every claim, proposals and human decisions live here.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    alert_id      TEXT PRIMARY KEY,
    metric        TEXT NOT NULL,
    period_start  TEXT NOT NULL,
    period_end    TEXT NOT NULL,
    segment       TEXT,
    observed      REAL NOT NULL,
    expected      REAL NOT NULL,
    lower_bound   REAL NOT NULL,
    upper_bound   REAL NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('open', 'investigating', 'reviewed', 'closed')),
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investigations (
    investigation_id TEXT PRIMARY KEY,
    alert_id         TEXT REFERENCES alerts(alert_id),
    mode             TEXT NOT NULL CHECK (mode IN ('llm', 'rule_based')),
    status           TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    failure_reason   TEXT,
    report_json      TEXT,
    model            TEXT,
    input_tokens     INTEGER,
    output_tokens    INTEGER,
    cost_usd         REAL,
    started_at       TEXT NOT NULL,
    finished_at      TEXT
);

CREATE TABLE IF NOT EXISTS tool_calls (
    tool_call_id     TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id),
    step             INTEGER NOT NULL,
    tool_name        TEXT NOT NULL,
    input_json       TEXT NOT NULL,
    output_json      TEXT,
    output_sha256    TEXT,
    error            TEXT,
    duration_ms      INTEGER NOT NULL,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id  TEXT PRIMARY KEY,
    tool_call_id TEXT NOT NULL REFERENCES tool_calls(tool_call_id),
    label        TEXT NOT NULL,
    value_json   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proposals (
    proposal_id      TEXT PRIMARY KEY,
    investigation_id TEXT REFERENCES investigations(investigation_id),
    kind             TEXT NOT NULL CHECK (kind IN ('fix_and_verify', 'experiment', 'no_action')),
    body_json        TEXT NOT NULL,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id  TEXT PRIMARY KEY,
    subject_type TEXT NOT NULL CHECK (subject_type IN ('finding', 'proposal', 'experiment')),
    subject_id   TEXT NOT NULL,
    outcome      TEXT NOT NULL CHECK (outcome IN ('approved', 'rejected', 'more_evidence')),
    note         TEXT NOT NULL CHECK (length(trim(note)) > 0),
    decided_by   TEXT NOT NULL,
    decided_at   TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    return con
