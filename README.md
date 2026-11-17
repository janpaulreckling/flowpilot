# FlowPilot

> **Work in progress.** FlowPilot watches a product's key metrics, flags changes that are unlikely to be noise, investigates them with evidence, evaluates experiments with defensible statistics, and hands a product manager a recommendation to approve or reject.

All data is **synthetic**: a simulated team task-management SaaS called *Tasklane*, with documented, injected scenarios (see [docs/DATA_SCENARIOS.md](docs/DATA_SCENARIOS.md)).

## Status

Foundation in place: reproducible data generator, DuckDB analytics store, API skeleton, tests and CI. Metrics, monitoring, experiments, investigations and the UI follow. Plans and decisions live in [docs/](docs/).

## Quickstart

```bash
uv sync
make data    # simulate ~6M events and build data/flowpilot.duckdb (about 10 s)
make check   # ruff, mypy, pytest
make serve   # API on http://localhost:8000/api/dataset
make ui      # UI on http://localhost:5173 (design prototype: Decision Center + one investigation)
```
