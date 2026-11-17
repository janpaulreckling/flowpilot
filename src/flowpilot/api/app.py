"""FastAPI application. Every analytics endpoint goes through the metric layer."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Annotated, Literal

import duckdb
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel

from flowpilot import __version__
from flowpilot.appstate import db as appdb
from flowpilot.appstate import investigations as inv_store
from flowpilot.appstate.alerts import StoredAlert, list_alerts
from flowpilot.experiments.analysis import ExperimentAnalysis, analyze
from flowpilot.experiments.stats import detectable_effect, units_per_arm
from flowpilot.investigation.llm_agent import DEFAULT_MODEL, llm_enabled, run_agent
from flowpilot.investigation.report import (
    NO_CONCLUSION,
    Claim,
    InvestigationReport,
    Recommendation,
    validate,
)
from flowpilot.investigation.rule_based import investigate
from flowpilot.investigation.tools import Toolbox
from flowpilot.metrics.engine import (
    FunnelResult,
    Grain,
    MetricEngine,
    MetricError,
    MetricResult,
    load_registry,
)
from flowpilot.settings import get_paths
from flowpilot.warehouse.connection import connect_read_only


class Health(BaseModel):
    status: str
    version: str


class DatasetInfo(BaseModel):
    synthetic: bool
    seed: int
    scale: float
    period_start: str
    period_end_exclusive: str
    row_counts: dict[str, int]


class MetricInfo(BaseModel):
    name: str
    label: str
    description: str
    unit: str
    is_rate: bool
    grains: list[str]
    dimensions: list[str]


app = FastAPI(title="FlowPilot API", version=__version__)


def analytics() -> Iterator[duckdb.DuckDBPyConnection]:
    try:
        con = connect_read_only(get_paths().analytics_db)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        yield con
    finally:
        con.close()


Analytics = Annotated[duckdb.DuckDBPyConnection, Depends(analytics)]


def parse_filters(raw: list[str]) -> dict[str, list[str]]:
    """`dimension:value` pairs; repeating a dimension ORs its values."""
    out: dict[str, list[str]] = {}
    for item in raw:
        dim, sep, value = item.partition(":")
        if not sep or not dim or not value:
            raise HTTPException(
                status_code=400, detail=f"filter must be dimension:value, got {item!r}")
        out.setdefault(dim, []).append(value)
    return out


@app.get("/api/health")
def health() -> Health:
    return Health(status="ok", version=__version__)


@app.get("/api/dataset")
def dataset(con: Analytics) -> DatasetInfo:
    info = dict(con.execute("SELECT key, value FROM dataset_info").fetchall())
    counts = {}
    for t in ("workspaces", "users", "sessions", "events", "experiments"):
        row = con.execute(f"SELECT count(*) FROM {t}").fetchone()
        counts[t] = int(row[0]) if row else 0
    return DatasetInfo(
        synthetic=info["synthetic"] == "true",
        seed=int(info["seed"]),
        scale=float(info["scale"]),
        period_start=info["period_start"],
        period_end_exclusive=info["period_end_exclusive"],
        row_counts=counts,
    )


@app.get("/api/metrics")
def metrics() -> list[MetricInfo]:
    defs, _ = load_registry()
    return [MetricInfo(name=d.name, label=d.label, description=d.description, unit=d.unit,
                       is_rate=d.is_rate, grains=list(d.grains), dimensions=d.dimensions)
            for d in defs.values()]


@app.get("/api/metrics/{metric}")
def metric(
    con: Analytics,
    metric: str,
    start: date,
    end: date,
    grain: Grain = "week",
    group_by: str | None = None,
    filter: Annotated[list[str], Query()] = [],  # noqa: B006 - FastAPI query list default
) -> MetricResult:
    try:
        return MetricEngine(con).query(metric, start, end, grain, parse_filters(filter), group_by)
    except MetricError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/funnel")
def funnel(
    con: Analytics,
    start: date,
    end: date,
    group_by: str | None = None,
    filter: Annotated[list[str], Query()] = [],  # noqa: B006
) -> FunnelResult:
    try:
        return MetricEngine(con).funnel(start, end, parse_filters(filter), group_by)
    except MetricError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/alerts")
def alerts() -> list[StoredAlert]:
    con = appdb.connect(get_paths().app_db)
    try:
        return list_alerts(con)
    finally:
        con.close()


class ExperimentSummary(BaseModel):
    experiment_id: str
    name: str
    primary_metric: str
    verdict: str
    diff: float | None
    started: date
    ended: date


class PlannerResult(BaseModel):
    baseline: float
    mde_abs: float
    units_per_arm: int
    weekly_units: int | None
    weeks_needed: float | None
    mde_after_weeks: dict[int, float] | None


@app.get("/api/experiments")
def experiments(con: Analytics) -> list[ExperimentSummary]:
    engine = MetricEngine(con)
    ids = [r[0] for r in con.execute(
        "SELECT experiment_id FROM experiments ORDER BY started_at").fetchall()]
    out = []
    for x in ids:
        a = analyze(engine, x)
        out.append(ExperimentSummary(
            experiment_id=x, name=a.name, primary_metric=a.primary_metric, verdict=a.verdict,
            diff=a.primary.diff if a.primary else None, started=a.started, ended=a.ended))
    return out


@app.get("/api/experiments/{experiment_id}")
def experiment(
    con: Analytics, experiment_id: str, as_of: date | None = None
) -> ExperimentAnalysis:
    try:
        return analyze(MetricEngine(con), experiment_id, as_of)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/planner")
def planner(
    baseline: Annotated[float, Query(gt=0, lt=1)],
    mde_abs: Annotated[float, Query(gt=0, lt=1)],
    weekly_units: Annotated[int | None, Query(gt=0)] = None,
) -> PlannerResult:
    """Units per arm for a 50/50 test (alpha 0.05, power 0.8) and the runtime it implies."""
    if baseline + mde_abs >= 1:
        raise HTTPException(status_code=400, detail="baseline + mde_abs must stay below 1")
    n = units_per_arm(baseline, mde_abs)
    per_arm_week = weekly_units / 2 if weekly_units else None
    return PlannerResult(
        baseline=baseline, mde_abs=mde_abs, units_per_arm=n, weekly_units=weekly_units,
        weeks_needed=n / per_arm_week if per_arm_week else None,
        mde_after_weeks={w: detectable_effect(baseline, int(per_arm_week * w))
                         for w in (1, 2, 4, 8)} if per_arm_week else None,
    )


class Capabilities(BaseModel):
    llm_enabled: bool
    model: str | None


@app.get("/api/capabilities")
def capabilities() -> Capabilities:
    enabled = llm_enabled()
    return Capabilities(llm_enabled=enabled,
                        model=os.environ.get("FLOWPILOT_MODEL", DEFAULT_MODEL) if enabled else None)


@app.post("/api/alerts/{alert_id}/investigate")
def run_investigation(
    con: Analytics, alert_id: str, mode: Literal["rule_based", "llm"] = "rule_based",
) -> inv_store.InvestigationRecord:
    """Investigate an alert, rule-based (no LLM) or with the LLM agent, and store the result."""
    if mode == "llm" and not llm_enabled():
        raise HTTPException(status_code=409, detail="LLM mode is not enabled: set "
                            "ANTHROPIC_API_KEY. Rule-based investigations work without it.")
    app_con = appdb.connect(get_paths().app_db)
    try:
        stored = list_alerts(app_con)
        tools = Toolbox(MetricEngine(con), stored)
        alert = tools.alerts.get(alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail=f"no alert {alert_id}")
        started = datetime.now(UTC).isoformat(timespec="seconds")
        if mode == "rule_based":
            report, log = investigate(tools, alert)
            inv_id = inv_store.save(app_con, report, log, validate(report, log), started)
        else:
            run, log = run_agent(tools, alert)
            report = run.report or InvestigationReport(
                alert_id=alert_id, mode="llm", title="LLM investigation failed",
                summary=[Claim(text=NO_CONCLUSION)], findings=[], hypotheses=[],
                limitations=[f"Run ended: {run.failure} {run.detail or ''}".strip()],
                recommendation=Recommendation(kind="no_action", claim=Claim(
                    text="Use the rule-based investigation, or retry later.")),
                conclusion_supported=False)
            issues = validate(report, log) if run.report else []
            inv_id = inv_store.save(app_con, report, log, issues, started, model=run.model,
                                    input_tokens=run.input_tokens,
                                    output_tokens=run.output_tokens, cost_usd=run.cost_usd,
                                    failure=None if run.status == "completed" else
                                    f"{run.failure}: {run.detail or ''}")
        record = inv_store.load(app_con, inv_id)
        assert record is not None
        return record
    finally:
        app_con.close()


@app.get("/api/alerts/{alert_id}/investigations")
def alert_investigations(alert_id: str) -> list[str]:
    app_con = appdb.connect(get_paths().app_db)
    try:
        return inv_store.for_alert(app_con, alert_id)
    finally:
        app_con.close()


@app.get("/api/investigations/{investigation_id}")
def get_investigation(investigation_id: str) -> inv_store.InvestigationRecord:
    app_con = appdb.connect(get_paths().app_db)
    try:
        record = inv_store.load(app_con, investigation_id)
    finally:
        app_con.close()
    if record is None:
        raise HTTPException(status_code=404, detail=f"no investigation {investigation_id}")
    return record
