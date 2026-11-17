"""FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from flowpilot import __version__
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


app = FastAPI(title="FlowPilot API", version=__version__)


@app.get("/api/health")
def health() -> Health:
    return Health(status="ok", version=__version__)


@app.get("/api/dataset")
def dataset() -> DatasetInfo:
    try:
        con = connect_read_only(get_paths().analytics_db)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    with con:
        info = dict(con.execute("SELECT key, value FROM dataset_info").fetchall())
        tables = ("workspaces", "users", "sessions", "events", "experiments")
        counts = {}
        for t in tables:
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
