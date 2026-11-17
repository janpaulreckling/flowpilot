# Design Decisions

The trade-offs that shaped FlowPilot, each with the alternatives that were rejected. Numbers are stable ids referenced from code comments and other docs.

## Product and data

**D1 · The monitored product is a team task-management SaaS ("Tasklane").** Everyone understands it in one sentence, and it naturally has an activation moment, a mobile onboarding funnel, a free-to-paid motion and a team dimension. *Rejected:* appointment booking (weak team dimension), invoicing (too close to finance).

**D8 · The headline story is a mobile onboarding regression.** Activation drops after iOS release 4.12 at the "invite teammate" step. It exercises segment, funnel and release analysis and must be told apart from seasonality and a channel-mix shift. *Rejected as the lead:* a retention drop in one acquisition cohort (kept as scenario S2).

**D19 · Synthetic scenarios are frozen before analysis code exists.** The ground truth ([DATA_SCENARIOS.md](DATA_SCENARIOS.md)) was fixed before the monitor and the investigator were written. Two later amendments are recorded with their reasons: **D21** (the misleading-correlation scenario uses "integration connected at setup", because "ever used" adds survivorship bias) and **D23** (experiments are not rolled out inside the data period).

**D20 · The data volume follows from statistical power, not from a convenient seed.** At about 1,200 new workspaces per week the 4-week experiments would reach significance only about half the time. The volume was raised to about 2,500 per week. *Rejected:* longer experiments, larger effects, or picking a seed that gives the "right" answer.

## Metrics

**D13 · One metric registry, compiled to SQL.** Every page, the monitor and the investigation tools read metrics from one YAML registry ([METRICS.md](METRICS.md)), so there cannot be two activation numbers. *Rejected:* dbt plus a registry (more moving parts, no runtime filtering).

**D25 · "Active" means a core action, not an app open.** Opening the app without doing anything is not activity. As a consequence, a tracking gap shows up as an activity dip, and the monitor must recognize it as a data problem.

**D26 · Retention week N is bracketed.** A user counts as retained in week N only if active on days 7N to 7N+6. *Rejected:* "week N or later", which is always higher and hides when users drop off.

## Monitoring and experiments

**D12 · Anomaly detection uses a transparent baseline.** It compares against a trailing 8-week baseline and alerts only when three conditions hold together: a statistical signal, a practical threshold and a minimum size. A segment decomposition follows ([MONITORING.md](MONITORING.md)). *Rejected:* STL (shaky on 6 months of data), Prophet/ML (black box, heavy dependency).

**D27 · Monitor parameters stay frozen after the first run.** The back-test produced 58 improvement notices from a monitor that lags growth. They are shown, collapsed, instead of tuning a v2 to this dataset.

**D11 · Experiments use fixed-horizon frequentist analysis with explicit guards** ([EXPERIMENTS.md](EXPERIMENTS.md)):
- workspace randomization with intent-to-treat;
- delta-method variance;
- the SRM check before any effect is read;
- Holm-corrected guardrails;
- TOST for "no meaningful effect";
- no verdict before the planned horizon.

*Rejected:* sequential tests (harder to explain and validate), Bayesian analysis (priors are easy to attack).

**D33 · Method v2 after a structured method review.** The review found real weaknesses, among them a too-small monitor standard error, a localization rule that measured segment size, and a too-generous evaluation. The rules were changed in a separate commit before re-running, and v1 and v2 results are reported side by side ([METHOD_V2.md](METHOD_V2.md)).

## Investigations and AI

**D4 · The agent is a hand-written tool-use loop on the Claude API, with a rule-based fallback.** It can call typed, read-only tools only, with no free SQL. Every number in a report must match a recorded tool result, which an evidence validator checks. Steps, tokens, cost and time are capped, and each cap has a named failure state. *Rejected:* LangGraph (more dependencies, less transparent control flow), a provider abstraction layer (no value yet).

**D14 / D30 · The LLM agent is built but not yet evaluated against a real model.** The loop is tested end to end with a scripted model: hallucination feedback, a refused write attempt, limits, refusals and API errors. Real runs, with measured quality and cost, need an API key and are listed in the roadmap. Until then the app labels the AI mode as not enabled, and investigations run rule-based ([AGENT.md](AGENT.md)).

## Architecture and delivery

**D3 · FastAPI + DuckDB + React/TypeScript.**
- Python keeps the statistics libraries.
- DuckDB gives fast single-file analytics.
- React gives a real product UI.

The analytics store is opened **read-only** by everything except the build step. Human decisions live in a separate SQLite store, so neither the API nor the agent can change source data. *Rejected:* Streamlit/Dash (looks like a notebook), full-stack TypeScript (weaker statistics ecosystem).

**D16 / D17 · The UI reads like an analyst memo and opens on the Decision Center.**
- Investigations read like a decision memo with footnoted evidence.
- The landing page is an inbox of incidents, investigations and pending experiment decisions, not a dashboard.
- Related alerts are grouped into incidents ordered by strength.

*Rejected:* an ops-console look (hard to read long reports), a dashboard-first landing page.

**D5 · The live demo is a static snapshot.** The public demo is built from JSON exported from the real API, and its investigations are recorded runs. *Rejected:* a hosted backend (running cost, API-key exposure).
