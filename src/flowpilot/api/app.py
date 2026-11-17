"""FastAPI application. Every analytics endpoint goes through the metric layer."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Annotated

import duckdb
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel

from flowpilot import __version__
from flowpilot.appstate import db as appdb
from flowpilot.appstate.alerts import StoredAlert, list_alerts
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
