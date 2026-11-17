"""Store investigations with every tool call and its evidence."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from flowpilot.investigation.evidence import Evidence, EvidenceLog
from flowpilot.investigation.report import InvestigationReport, ValidationIssue


class InvestigationRecord(BaseModel):
    investigation_id: str
    alert_id: str
    mode: str
    model: str | None = None
    cost_usd: float | None = None
    status: str  # running | completed | failed
    failure_reason: str | None
    report: InvestigationReport | None
    evidence: list[Evidence]
    started_at: str
    finished_at: str


class AlreadyRunning(Exception):
    """Another investigation of the same alert is still running."""


STALE_AFTER = timedelta(minutes=15)


def start(con: sqlite3.Connection, alert_id: str, mode: str) -> str:
    """Reserve an investigation id before any (possibly paid) work starts."""
    now = datetime.now(UTC)
    with con:
        con.execute("BEGIN IMMEDIATE")  # serialize the check-and-insert across threads
        row = con.execute(
            "SELECT investigation_id FROM investigations WHERE alert_id = ? AND status = "
            "'running' AND started_at > ?",
            [alert_id, (now - STALE_AFTER).isoformat(timespec="seconds")]).fetchone()
        if row:
            raise AlreadyRunning(row[0])
        inv_id = f"INV-{uuid.uuid4().hex[:10]}"
        con.execute(
            "INSERT INTO investigations (investigation_id, alert_id, mode, status, started_at) "
            "VALUES (?, ?, ?, 'running', ?)",
            (inv_id, alert_id, mode, now.isoformat(timespec="seconds")))
    return inv_id


def finish(con: sqlite3.Connection, inv_id: str, report: InvestigationReport,
           log: EvidenceLog, issues: list[ValidationIssue],
           model: str | None = None, input_tokens: int | None = None,
           output_tokens: int | None = None, cost_usd: float | None = None,
           failure: str | None = None) -> None:
    finished = datetime.now(UTC).isoformat(timespec="seconds")
    status = "failed" if issues or failure else "completed"
    reason = failure or "; ".join(f"{i.problem} in: {i.claim[:80]}" for i in issues) or None
    with con:
        con.execute(
            """UPDATE investigations SET status = ?, failure_reason = ?, report_json = ?,
               model = ?, input_tokens = ?, output_tokens = ?, cost_usd = ?, finished_at = ?
               WHERE investigation_id = ?""",
            (status, reason, report.model_dump_json(), model, input_tokens, output_tokens,
             cost_usd, finished, inv_id))
        for ev in log.items:
            call_id = f"{inv_id}:{ev.evidence_id}"
            con.execute(
                """INSERT INTO tool_calls (tool_call_id, investigation_id, step, tool_name,
                   input_json, output_json, output_sha256, error, duration_ms, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (call_id, inv_id, ev.step, ev.tool, json.dumps(ev.input),
                 ev.output.model_dump_json() if ev.output else None, ev.output_sha256,
                 ev.error, ev.duration_ms, finished))
            if ev.output:
                con.execute("INSERT INTO evidence VALUES (?, ?, ?, ?)",
                            (call_id, call_id, ev.output.summary, json.dumps(ev.output.facts)))
        con.execute("UPDATE alerts SET status = 'investigating', updated_at = ? "
                    "WHERE alert_id = ? AND status = 'open'", (finished, report.alert_id))


def abort(con: sqlite3.Connection, inv_id: str, reason: str) -> None:
    with con:
        con.execute("UPDATE investigations SET status = 'failed', failure_reason = ?, "
                    "finished_at = ? WHERE investigation_id = ?",
                    (reason, datetime.now(UTC).isoformat(timespec="seconds"), inv_id))


def load(con: sqlite3.Connection, investigation_id: str) -> InvestigationRecord | None:
    row = con.execute(
        """SELECT investigation_id, alert_id, mode, status, failure_reason, report_json,
                  started_at, finished_at, model, cost_usd
           FROM investigations WHERE investigation_id = ?""",
        [investigation_id]).fetchone()
    if row is None:
        return None
    calls = con.execute(
        """SELECT step, tool_name, input_json, output_json, output_sha256, error, duration_ms,
                  tool_call_id FROM tool_calls WHERE investigation_id = ? ORDER BY step""",
        [investigation_id]).fetchall()
    evidence = [Evidence(
        evidence_id=call_id.split(":", 1)[1], step=step, tool=tool, input=json.loads(inp),
        output=json.loads(out) if out else None, error=err, output_sha256=sha,
        duration_ms=ms) for step, tool, inp, out, sha, err, ms, call_id in calls]
    return InvestigationRecord(
        investigation_id=row[0], alert_id=row[1], mode=row[2], status=row[3],
        failure_reason=row[4],
        report=InvestigationReport.model_validate_json(row[5]) if row[5] else None,
        evidence=evidence, started_at=row[6], finished_at=row[7] or "", model=row[8],
        cost_usd=row[9])


def for_alert(con: sqlite3.Connection, alert_id: str) -> list[str]:
    return [r[0] for r in con.execute(
        "SELECT investigation_id FROM investigations WHERE alert_id = ? ORDER BY started_at",
        [alert_id]).fetchall()]
