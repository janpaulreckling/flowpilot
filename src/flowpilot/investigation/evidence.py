"""Recorded tool calls. Every number in a report must point at a fact recorded here."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field


class ToolOutput(BaseModel):
    """What a tool returns: structured data plus named numeric facts that claims can cite."""

    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    facts: dict[str, float] = Field(default_factory=dict)


class Evidence(BaseModel):
    evidence_id: str
    step: int
    tool: str
    input: dict[str, Any]
    output: ToolOutput | None
    error: str | None
    output_sha256: str | None
    duration_ms: int


class EvidenceLog:
    def __init__(self) -> None:
        self.items: list[Evidence] = []

    def record(self, tool: str, args: dict[str, Any],
               fn: Callable[..., ToolOutput]) -> Evidence:
        start = time.perf_counter()
        output: ToolOutput | None = None
        error: str | None = None
        try:
            output = fn(**args)
        except Exception as exc:  # noqa: BLE001 - a failing tool becomes a recorded error
            error = f"{type(exc).__name__}: {exc}"
        payload = output.model_dump_json() if output else None
        ev = Evidence(
            evidence_id=f"E-{len(self.items) + 1}",
            step=len(self.items) + 1,
            tool=tool,
            input=json.loads(json.dumps(args, default=str)),
            output=output,
            error=error,
            output_sha256=hashlib.sha256(payload.encode()).hexdigest() if payload else None,
            duration_ms=int((time.perf_counter() - start) * 1000),
        )
        self.items.append(ev)
        return ev

    def get(self, evidence_id: str) -> Evidence | None:
        return next((e for e in self.items if e.evidence_id == evidence_id), None)
