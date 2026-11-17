"""Write generator output to Parquet and load it into the DuckDB analytics store."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from flowpilot.generator.simulate import SimulationResult

TABLE_ORDER = (
    "workspaces", "users", "subscriptions", "sessions", "events", "releases",
    "experiments", "experiment_assignments", "experiment_exposures",
)


def write_raw(result: SimulationResult, raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        pq.write_table(table, raw_dir / f"{name}.parquet")
    (raw_dir / "ground_truth.json").write_text(json.dumps(result.ground_truth, indent=2) + "\n")


def build_database(raw_dir: Path, db_path: Path) -> dict[str, int]:
    """(Re)create the analytics store from Parquet files. Returns row counts per table."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = db_path.with_suffix(".building")
    tmp.unlink(missing_ok=True)
    schema = resources.files("flowpilot.warehouse").joinpath("schema.sql").read_text()
    counts: dict[str, int] = {}
    with duckdb.connect(str(tmp)) as con:
        con.execute("SET TimeZone = 'UTC'")
        con.execute(schema)
        for name in TABLE_ORDER:
            path = raw_dir / f"{name}.parquet"
            con.execute(f"INSERT INTO {name} SELECT * FROM read_parquet(?)", [str(path)])
            row = con.execute(f"SELECT count(*) FROM {name}").fetchone()
            counts[name] = int(row[0]) if row else 0
        derived = resources.files("flowpilot.warehouse").joinpath("derived.sql").read_text()
        con.execute(derived)
        truth = json.loads((raw_dir / "ground_truth.json").read_text())
        info = {
            "synthetic": "true",
            "seed": str(truth["seed"]),
            "scale": str(truth["scale"]),
            "period_start": truth["period"]["start"],
            "period_end_exclusive": truth["period"]["end_exclusive"],
        }
        con.executemany("INSERT INTO dataset_info VALUES (?, ?)", list(info.items()))
    tmp.replace(db_path)
    return counts
