"""Read-only access to the analytics store.

Everything except the build step uses this connection, so the API and the investigation agent
cannot modify source data or metric results.
"""

from __future__ import annotations

from pathlib import Path

import duckdb


def connect_read_only(db_path: Path) -> duckdb.DuckDBPyConnection:
    if not db_path.exists():
        raise FileNotFoundError(f"Analytics store not found at {db_path}; run `flowpilot build`.")
    con = duckdb.connect(str(db_path), read_only=True)
    con.execute("SET TimeZone = 'UTC'")
    return con
