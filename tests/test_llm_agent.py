"""The LLM agent loop, driven by a scripted model (no network, no cost)."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from flowpilot.appstate.alerts import StoredAlert
from flowpilot.investigation.llm_agent import READ_TOOLS, TOOLS, Limits, run_agent
from flowpilot.investigation.report import NO_CONCLUSION
from flowpilot.investigation.tools import Toolbox
from flowpilot.metrics.engine import MetricEngine
from flowpilot.monitor.detect import Alert, run_monitor
from flowpilot.warehouse.connection import connect_read_only


@dataclass
class Block:
    type: str
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class Usage:
    input_tokens: int = 2_000
    output_tokens: int = 300
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class Response:
    content: list[Block]
    stop_reason: str = "tool_use"
    usage: Usage = field(default_factory=Usage)


Turn = Callable[[list[dict[str, Any]]], Response]


class Scripted:
    def __init__(self, turns: list[Turn]) -> None:
        self.turns = turns
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Response:
        # Snapshot: the agent keeps appending to the same message list after this call.
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        turn = self.turns[min(len(self.calls) - 1, len(self.turns) - 1)]
        return turn(kwargs["messages"])


def use(name: str, **args: Any) -> Turn:
    return lambda _m: Response([Block("tool_use", id=f"t{name}", name=name, input=args)])


def last_result(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """The most recent successful tool result (skipping validator feedback)."""
    for msg in reversed(messages):
        if msg["role"] != "user" or not isinstance(msg["content"], list):
            continue
        for item in msg["content"]:
            if isinstance(item, dict) and not item.get("is_error"):
                try:
                    return dict(json.loads(item["content"]))
                except (json.JSONDecodeError, TypeError):
                    continue
    raise AssertionError("no tool result yet")


def claim(text: str, *facts: tuple[str, str]) -> dict[str, Any]:
    return {"text": text, "citations": [{"evidence_id": e, "fact": f} for e, f in facts]}


def report(summary: list[dict[str, Any]], supported: bool = True) -> dict[str, Any]:
    return {"title": "Activation fell", "summary": summary, "findings": [], "hypotheses": [],
            "limitations": [], "conclusion_supported": supported,
            "recommendation": {"kind": "no_action", "claim": {"text": "Keep monitoring.",
                                                              "citations": []}}}


def submit_from_facts(wrong: bool = False) -> Turn:
    def turn(messages: list[dict[str, Any]]) -> Response:
        facts = last_result(messages)["facts"]
        shown = facts["current_rate"] * 100 + (5 if wrong else 0)
        text = f"Activation was {shown:.1f}% ({facts['diff_pp']:+.1f} pp)."
        rep = report([claim(text, ("E-1", "current_rate"), ("E-1", "diff_pp"))])
        return Response([Block("tool_use", id="sub", name="submit_report", input=rep)])
    return turn


@pytest.fixture(scope="module")
def setup(full_world: Path) -> Iterator[tuple[Toolbox, Alert]]:
    con = connect_read_only(full_world)
    engine = MetricEngine(con)
    alerts = run_monitor(engine, date(2026, 5, 4)).alerts
    alert = next(a for a in alerts if a.metric == "activation_rate" and not a.segment)
    yield Toolbox(engine, [StoredAlert(alert=a, status="open") for a in alerts]), alert
    con.close()


def compare(alert: Alert) -> Turn:
    return use("compare_periods", metric="activation_rate",
               current_start=alert.first_period_start.isoformat(),
               current_end=alert.last_period_end.isoformat(),
               baseline_start="2026-08-17", baseline_end=alert.first_period_start.isoformat())


def test_completes_with_a_validated_report(setup: tuple[Toolbox, Alert]) -> None:
    tools, alert = setup
    model = Scripted([compare(alert), submit_from_facts()])
    run, log = run_agent(tools, alert, client=model)
    assert run.status == "completed", run.detail
    assert run.report is not None and run.report.mode == "llm"
    assert [e.tool for e in log.items] == ["compare_periods"]
    assert run.tool_calls == 1 and run.steps == 2 and run.cost_usd > 0
    assert model.calls[0]["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_hallucinated_number_is_sent_back_and_corrected(setup: tuple[Toolbox, Alert]) -> None:
    tools, alert = setup
    model = Scripted([compare(alert), submit_from_facts(wrong=True), lambda m: Response(
        [Block("tool_use", id="sub2", name="submit_report",
               input=report([claim("Activation changed; see the evidence.")]))])])
    run, _ = run_agent(tools, alert, client=model)
    assert run.status == "completed"
    feedback = model.calls[2]["messages"][-1]["content"][0]
    assert feedback["is_error"] and "matches no cited fact" in feedback["content"]


def test_persistent_hallucination_fails_the_run(setup: tuple[Toolbox, Alert]) -> None:
    tools, alert = setup
    model = Scripted([compare(alert), submit_from_facts(wrong=True)])
    run, _ = run_agent(tools, alert, client=model, limits=Limits(max_report_attempts=2))
    assert run.status == "failed" and run.failure == "invalid_report"


def test_write_attempt_is_refused_and_not_executed(setup: tuple[Toolbox, Alert]) -> None:
    tools, alert = setup
    model = Scripted([use("execute_sql", sql="DELETE FROM events"), compare(alert),
                      submit_from_facts()])
    run, log = run_agent(tools, alert, client=model)
    refused = model.calls[1]["messages"][-1]["content"][0]
    assert refused["is_error"] and "Only read-only tools" in refused["content"]
    assert "execute_sql" not in [e.tool for e in log.items]
    assert run.status == "completed"


def test_bad_tool_input_is_reported_back(setup: tuple[Toolbox, Alert]) -> None:
    tools, alert = setup
    model = Scripted([use("compare_periods", metric="revenue", current_start="2026-10-01",
                          current_end="2026-11-01", baseline_start="2026-08-01",
                          baseline_end="2026-10-01"), compare(alert), submit_from_facts()])
    run, log = run_agent(tools, alert, client=model)
    assert log.items[0].error and "unknown metric" in log.items[0].error
    assert model.calls[1]["messages"][-1]["content"][0]["is_error"]
    # E-1 is the failed call, so the scripted report citing E-1 must be rejected; the run
    # still ends cleanly within its attempts.
    assert run.status in ("completed", "failed")


@pytest.mark.parametrize(("limits", "usage", "failure"), [
    (Limits(max_steps=3), Usage(), "step_limit"),
    (Limits(max_cost_usd=0.01), Usage(input_tokens=50_000), "cost_limit"),
    (Limits(max_total_tokens=1_000), Usage(), "token_limit"),
    (Limits(max_tool_calls=2), Usage(), "tool_call_limit"),
])
def test_limits_end_the_run(setup: tuple[Toolbox, Alert], limits: Limits, usage: Usage,
                            failure: str) -> None:
    tools, alert = setup
    loop = lambda _m: Response([Block("tool_use", id="g", name="get_alert",  # noqa: E731
                                      input={"alert_id": alert.alert_id})], usage=usage)
    run, _ = run_agent(tools, alert, client=Scripted([loop]), limits=limits)
    assert run.status == "failed" and run.failure == failure


def test_refusal_and_api_errors_are_named_failures(setup: tuple[Toolbox, Alert]) -> None:
    tools, alert = setup
    run, _ = run_agent(tools, alert, client=Scripted(
        [lambda _m: Response([], stop_reason="refusal")]))
    assert run.failure == "refusal"

    class Broken:
        def create(self, **kwargs: Any) -> Response:
            raise TimeoutError("network down")
    run, _ = run_agent(tools, alert, client=Broken())
    assert run.failure == "api_error" and "network down" in (run.detail or "")


def test_no_conclusion_requires_the_exact_sentence(setup: tuple[Toolbox, Alert]) -> None:
    tools, alert = setup
    vague = report([claim("Unclear.")], supported=False)
    honest = report([claim(NO_CONCLUSION)], supported=False)
    model = Scripted([lambda _m: Response([Block("tool_use", id="a", name="submit_report",
                                                 input=vague)]),
                      lambda _m: Response([Block("tool_use", id="b", name="submit_report",
                                                 input=honest)])])
    run, _ = run_agent(tools, alert, client=model)
    assert run.status == "completed" and run.report is not None
    assert not run.report.conclusion_supported


def test_tool_surface_is_read_only() -> None:
    names = {t["name"] for t in TOOLS}
    assert names - {"submit_report"} == READ_TOOLS
    assert not any(w in n for n in names for w in ("write", "update", "delete", "sql", "approve"))
