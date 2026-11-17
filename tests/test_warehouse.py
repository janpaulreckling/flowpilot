"""The analytics store enforces its schema and is read-only for everything but the build."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from flowpilot.warehouse.build import build_database
from flowpilot.warehouse.connection import connect_read_only
from tests.conftest import World


def test_row_counts_match_generator_output(world: World) -> None:
    for name, table in world.result.tables.items():
        assert world.counts[name] == table.num_rows, name


def test_read_only_connection_rejects_writes(con: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(duckdb.Error):
        con.execute("DELETE FROM events")
    with pytest.raises(duckdb.Error):
        con.execute("CREATE TABLE sneaky AS SELECT 1")


def test_missing_store_gives_clear_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="flowpilot build"):
        connect_read_only(tmp_path / "nope.duckdb")


def test_build_fails_on_duplicate_events(world: World, tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    for f in world.raw_dir.iterdir():
        (raw / f.name).write_bytes(f.read_bytes())
    events = pq.read_table(raw / "events.parquet")
    pq.write_table(pa.concat_tables([events, events.slice(0, 1)]), raw / "events.parquet")
    with pytest.raises(duckdb.ConstraintException):
        build_database(raw, tmp_path / "broken.duckdb")
    assert not (tmp_path / "broken.duckdb").exists()
