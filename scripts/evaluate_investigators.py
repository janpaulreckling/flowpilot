"""Score the rule-based investigator and (optionally) the LLM agent on new seeds.

Protocol: docs/EVALUATION.md (committed before any run). Writes a JSON file with every case
and a markdown summary.

Usage:
  uv run python scripts/evaluate_investigators.py --out eval/rule_based.json
  ANTHROPIC_API_KEY=... uv run python scripts/evaluate_investigators.py --llm \\
      --budget-usd 15 --out eval/llm.json
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from flowpilot.appstate.alerts import StoredAlert
from flowpilot.evaluation.investigation_eval import score
from flowpilot.evaluation.monitor_eval import attribute
from flowpilot.generator.config import WorldConfig
from flowpilot.generator.simulate import simulate
from flowpilot.investigation.llm_agent import run_agent
from flowpilot.investigation.report import validate
from flowpilot.investigation.rule_based import investigate
from flowpilot.investigation.tools import Toolbox
from flowpilot.metrics.engine import MetricEngine
from flowpilot.monitor.detect import run_monitor
from flowpilot.warehouse.build import build_database, write_raw
from flowpilot.warehouse.connection import connect_read_only

SEEDS = (101, 202, 303)  # docs/EVALUATION.md: never looked at before the protocol


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="also run the LLM agent (costs money)")
    ap.add_argument("--budget-usd", type=float, default=0.0, help="stop LLM runs above this")
    ap.add_argument("--model", default=None)
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.llm and args.budget_usd <= 0:
        ap.error("--llm needs a positive --budget-usd")

    cases: list[dict[str, Any]] = []
    spent = 0.0
    budget_hit = False
    for seed in SEEDS:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_raw(simulate(WorldConfig(seed=seed)), root / "raw")
            build_database(root / "raw", root / "db.duckdb")
            with connect_read_only(root / "db.duckdb") as con:
                engine = MetricEngine(con)
                run = run_monitor(engine, engine.data_start)
                tools = Toolbox(engine, [StoredAlert(alert=a, status="open") for a in run.alerts])
                for alert in run.alerts:
                    if alert.direction != "decline":
                        continue
                    case: dict[str, Any] = {
                        "seed": seed, "alert_id": alert.alert_id, "metric": alert.metric,
                        "segment": alert.segment, "scenario": attribute(alert)}
                    t0 = time.perf_counter()
                    report, log = investigate(tools, alert)
                    s = score(alert, report)
                    case["rule_based"] = {
                        "passed": s.passed,
                        "failed_checks": [k for k, v in s.checks.items() if not v],
                        "validator_issues": len(validate(report, log)),
                        "seconds": round(time.perf_counter() - t0, 3)}
                    if args.llm:
                        if spent >= args.budget_usd:
                            budget_hit = True
                            case["llm"] = {"skipped": "budget reached"}
                        else:
                            r, llm_log = run_agent(tools, alert, model=args.model,
                                                   effort=args.effort)
                            spent += r.cost_usd
                            entry: dict[str, Any] = {
                                "status": r.status, "failure": r.failure, "model": r.model,
                                "steps": r.steps, "tool_calls": r.tool_calls,
                                "report_attempts": r.report_attempts,
                                "rejected_claims": r.rejected_claims,
                                "tool_errors": r.tool_errors, "input_tokens": r.input_tokens,
                                "output_tokens": r.output_tokens, "cost_usd": r.cost_usd,
                                "seconds": r.duration_s}
                            if r.report is not None:
                                ls = score(alert, r.report)
                                entry |= {"passed": ls.passed,
                                          "failed_checks": [k for k, v in ls.checks.items()
                                                            if not v],
                                          "title": r.report.title}
                            else:
                                entry["passed"] = False
                            case["llm"] = entry
                    cases.append(case)
                    print(json.dumps({k: case[k] for k in ("seed", "alert_id", "scenario")}
                                     | {"rule": case["rule_based"]["passed"],
                                        "llm": case.get("llm", {}).get("passed")}), flush=True)

    summary = summarize(cases, args.llm, spent, budget_hit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"protocol": "docs/EVALUATION.md", "seeds": SEEDS,
                                    "date": date.today().isoformat(), "summary": summary,
                                    "cases": cases}, indent=2))
    print(json.dumps(summary, indent=2))


def summarize(cases: list[dict[str, Any]], llm: bool, spent: float,
              budget_hit: bool) -> dict[str, Any]:
    def rate(key: str) -> dict[str, Any]:
        done = [c for c in cases if key in c and "passed" in c[key]]
        by: dict[str, list[int]] = {}
        for c in done:
            base = (c["scenario"] or "unexplained").split(" ")[0]
            by.setdefault(base, [0, 0])
            by[base][0] += int(c[key]["passed"])
            by[base][1] += 1
        return {"passed": sum(int(c[key]["passed"]) for c in done), "cases": len(done),
                "by_scenario": {k: f"{v[0]}/{v[1]}" for k, v in sorted(by.items())}}

    out: dict[str, Any] = {"cases": len(cases), "rule_based": rate("rule_based")}
    if llm:
        runs = [c["llm"] for c in cases if "status" in c.get("llm", {})]
        out["llm"] = rate("llm") | {
            "failures": dict(Counter(r["failure"] for r in runs if r["failure"])),
            "rejected_claims": sum(r["rejected_claims"] for r in runs),
            "tool_errors": sum(r["tool_errors"] for r in runs),
            "mean_cost_usd": round(spent / len(runs), 3) if runs else None,
            "total_cost_usd": round(spent, 2),
            "mean_seconds": round(sum(r["seconds"] for r in runs) / len(runs), 1) if runs
            else None,
            "budget_reached": budget_hit}
    return out


if __name__ == "__main__":
    main()
