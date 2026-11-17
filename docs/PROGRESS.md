# Progress

## 2026-11-17 — Phases 0–3 (planning) done
- Phase 0 discovery: baseline decisions D1–D5.
- Phase 1 product blueprint approved ([PRODUCT_BLUEPRINT.md](PRODUCT_BLUEPRINT.md)); D7 name Tasklane, D8 demo story, D9 checkpoint review, D10 positioning.
- Phase 2 technical blueprint approved ([TECHNICAL_BLUEPRINT.md](TECHNICAL_BLUEPRINT.md), D15); D11 experiment statistics, D12 anomaly detection, D13 metric layer; D14 LLM model choice deferred to Phase 7.
- Phase 3 design blueprint approved ([DESIGN_BLUEPRINT.md](DESIGN_BLUEPRINT.md)); D16 analyst-memo look, D17 Decision Center as landing page, D18 shadcn/ui + Recharts.
- Repository is local only (not published). No code yet; no tests run yet.

## 2026-11-17 — Phase 4 foundation (backend)
- Python project (uv, Python 3.12), ruff + mypy strict + pytest, GitHub Actions CI.
- Synthetic data generator (vectorized, seeded; about 7 s for the full world) writing Parquet + `ground_truth.json`.
- DuckDB analytics store with schema constraints (duplicate keys fail the build); read-only connection for everything else.
- SQLite workflow-state schema (alerts, investigations, tool calls, evidence, proposals, decisions; a decision requires a note).
- FastAPI skeleton: `/api/health`, `/api/dataset`.
- Tests: 34 passing locally (determinism, 19 consistency invariants, scenario checks, read-only and constraint enforcement, API, app state). CI not yet run on GitHub (repo unpublished).

## 2026-11-17 — Scenario checks and design prototype
- Tolerance-band tests per scenario on the full default dataset (`tests/test_scenarios.py`); S2 recalibrated across seeds; D23 recorded.
- Frontend skeleton: Vite + React + TypeScript + Tailwind + shadcn/ui + Recharts, analyst-memo theme (light/dark), app shell with navigation and live dataset footer from `/api/dataset`.
- Prototype screens (D22): Decision Center and the investigation report for alert A-0142 with evidence side panel, chart with direct labels and table view, decision form requiring a note. Sample content is labeled in the UI.
- Verified: frontend typecheck, lint, 6 Vitest tests, production build; checked in a browser at desktop and phone width, light and dark, no console errors. Backend: 44 pytest tests.

## 2026-11-17 — Phase 5 analytics engine (core)
- Derived tables in the build step (`owner_cohort`, `user_active_days`, `trial_outcomes`, daily volumes).
- Metric layer: YAML registry (13 metrics) compiled to parameterized SQL; completeness flags, undefined (not zero) empty periods, dimension whitelist; onboarding funnel.
- Independent pure-Python reference implementation from the raw Parquet files; mutation checks confirmed the tests catch a wrong activation window and a wrong retention window.
- Anomaly monitor per `docs/MONITORING.md` (parameters committed before the first run); evaluation in a separate module that alone reads the ground truth. Measured: S1, S2, S5 detected; 1 false decline alert; 58 improvement notices (see MONITORING.md).
- Gates: ruff, mypy strict, 62 pytest tests.

## Next
- Scenario catalog frozen (D19, [DATA_SCENARIOS.md](DATA_SCENARIOS.md)); data volume about 2,500 new workspaces per week (D20).
- Product-owner feedback on the design prototype.
- Phase 5 remainder: API endpoints for metrics, funnel and alerts; alerts persisted to app state.
