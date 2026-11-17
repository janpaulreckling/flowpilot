"""File locations, overridable with environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    data_dir: Path

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def analytics_db(self) -> Path:
        return self.data_dir / "flowpilot.duckdb"

    @property
    def app_db(self) -> Path:
        return self.data_dir / "appstate.sqlite"


def get_paths() -> Paths:
    return Paths(data_dir=Path(os.environ.get("FLOWPILOT_DATA_DIR", "data")).resolve())
