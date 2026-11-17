# FlowPilot

> **Work in progress.** FlowPilot watches a product's key metrics, flags changes that are unlikely to be noise, investigates them with evidence, evaluates experiments with defensible statistics, and hands a product manager a recommendation to approve or reject.

All data is **synthetic**: a simulated team task-management SaaS called *Tasklane*, with documented, injected scenarios (see [docs/DATA_SCENARIOS.md](docs/DATA_SCENARIOS.md)).

## Status

In place: reproducible data generator, DuckDB analytics store, metric layer with an independent reference test, anomaly monitor with a measured back-test, API, design prototype, tests and CI. Experiments, investigations and the full UI follow. Plans and decisions live in [docs/](docs/).

## Quickstart

```bash
uv sync
make data    # simulate ~6M events, build data/flowpilot.duckdb, run the anomaly monitor
make check   # ruff, mypy, pytest
make serve   # API on http://localhost:8000 (e.g. /api/alerts, /api/metrics/activation_rate?start=2026-09-07&end=2026-11-16)
make ui      # UI on http://localhost:5173 (design prototype: Decision Center + one investigation)
```
