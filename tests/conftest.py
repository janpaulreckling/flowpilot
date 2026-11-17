from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pytest

from flowpilot.generator.config import WorldConfig
from flowpilot.generator.simulate import SimulationResult, simulate
from flowpilot.warehouse.build import build_database, write_raw
from flowpilot.warehouse.connection import connect_read_only

SMALL = WorldConfig(scale=0.05)


@dataclass
class World:
    result: SimulationResult
    raw_dir: Path
    db_path: Path
    counts: dict[str, int]


@pytest.fixture(scope="session")
def world(tmp_path_factory: pytest.TempPathFactory) -> World:
    root = tmp_path_factory.mktemp("world")
    result = simulate(SMALL)
    write_raw(result, root / "raw")
    counts = build_database(root / "raw", root / "flowpilot.duckdb")
    return World(result, root / "raw", root / "flowpilot.duckdb", counts)


@pytest.fixture()
def con(world: World) -> Iterator[duckdb.DuckDBPyConnection]:
    c = connect_read_only(world.db_path)
    yield c
    c.close()


@pytest.fixture(scope="session")
def full_world(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The default full-scale dataset (about 10 s to build), shared by slow tests."""
    root = tmp_path_factory.mktemp("full")
    write_raw(simulate(WorldConfig()), root / "raw")
    build_database(root / "raw", root / "db.duckdb")
    return root / "db.duckdb"
