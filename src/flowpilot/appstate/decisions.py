"""Human decisions: the only writes a user makes, each with a required note."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DecisionIn(BaseModel):
    subject_type: Literal["finding", "proposal", "experiment"]
    subject_id: str = Field(min_length=1, max_length=64)
    outcome: Literal["approved", "rejected", "more_evidence"]
    note: str = Field(max_length=2000)
    decided_by: str = Field(default="Product manager", min_length=1, max_length=80)

    @field_validator("note")
    @classmethod
    def note_required(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("a note is required so the decision can be understood later")
        return v.strip()


class Decision(DecisionIn):
    decision_id: str
    decided_at: str


def record(con: sqlite3.Connection, d: DecisionIn, alert_id: str | None = None) -> Decision:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    dec = Decision(**d.model_dump(), decision_id=f"D-{uuid.uuid4().hex[:8]}", decided_at=now)
    with con:
        con.execute("INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (dec.decision_id, dec.subject_type, dec.subject_id, dec.outcome, dec.note,
                     dec.decided_by, dec.decided_at))
        if alert_id and d.outcome != "more_evidence":
            con.execute("UPDATE alerts SET status = 'reviewed', updated_at = ? WHERE alert_id = ?",
                        (now, alert_id))
    return dec


def list_decisions(con: sqlite3.Connection) -> list[Decision]:
    rows = con.execute(
        """SELECT decision_id, subject_type, subject_id, outcome, note, decided_by, decided_at
           FROM decisions ORDER BY decided_at DESC""").fetchall()
    return [Decision(decision_id=r[0], subject_type=r[1], subject_id=r[2], outcome=r[3],
                     note=r[4], decided_by=r[5], decided_at=r[6]) for r in rows]
