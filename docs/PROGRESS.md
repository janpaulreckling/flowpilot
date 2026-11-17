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
- API: `/api/metrics`, `/api/metrics/{metric}` (filters, group_by, grain), `/api/funnel`, `/api/alerts`; `flowpilot monitor` stores alerts in the workflow state and never overwrites a human review status; `make data` runs generate + monitor. 69 pytest tests.

## 2026-11-17 — Phase 6 experimentation engine
- Decision rules committed before analysis (`docs/EXPERIMENTS.md`); D28 Phase 5 approved.
- Statistics core: delta-method ratio estimates, CIs, SRM chi-square, exposure balance, Holm, TOST equivalence, planner and achieved MDE.
- Analysis with the committed check order; experiment outcomes reuse the metric layer's definitions (tested against the dashboard numbers).
- Measured: E1 ship, E2 no meaningful effect, E3 don't ship (guardrail), E4 invalid (SRM) — all match ground truth. A/A simulations pass; a crash in interim looks was found and fixed with a regression test.
- API: `/api/experiments`, `/api/experiments/{id}?as_of=`, `/api/planner`. 85 pytest tests.

## 2026-11-17 — Phase 7 part 1: tools, evidence, rule-based investigator
- Rules committed before the first run (`docs/AGENT.md`); D29 Phase 6 approved.
- 11 read-only tools with recorded evidence (input, output, SHA-256, duration) and named facts; report schema; evidence validator that rejects any number not matching a cited fact.
- Rule-based investigator per the committed playbook; investigations stored with all tool calls; API `POST /api/alerts/{id}/investigate`, `GET /api/investigations/{id}`.
- Measured: 7 of 9 decline alerts investigated correctly (S1 ×3, S2, S5, false alarm, one E3); 2 E3 alerts fail on segment attribution (documented).
- 98 pytest tests.

## 2026-11-17 — Phase 7 part 2: LLM agent loop (D30)
- Bounded tool-use loop on the Claude Messages API with `submit_report` + evidence validator feedback, limits with named failure states, refusal fallback, cached system prompt.
- API: `POST /api/alerts/{id}/investigate?mode=llm` (409 without a key), `GET /api/capabilities`.
- Tested with a scripted model; no real-model run yet (needs the product owner's API key). 111 pytest tests.

## Next
- Scenario catalog frozen (D19, [DATA_SCENARIOS.md](DATA_SCENARIOS.md)); data volume about 2,500 new workspaces per week (D20).
- Product-owner feedback on the design prototype.
- Product-owner approval of Phase 7; real LLM runs when an API key exists.
- Phase 8: full frontend on the real API.
