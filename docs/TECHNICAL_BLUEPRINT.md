# Technical Blueprint (Phase 2 — draft for approval)

Status: **draft**; §4–§6 approved as D11–D13, model choice open. Builds on D1–D13 in [DECISIONS.md](DECISIONS.md). Items marked **[decision]** need product-owner approval.

## 1. Architecture at a glance

```
 generator (Python, seeded)          ground_truth.json (injected scenarios)
        │ Parquet
        ▼
 DuckDB analytics store  ── build step: staging → core tables (SQL files)
        │ read-only connection
        ▼
 Metric layer (one registry of metric definitions → parameterized SQL)
        │                    │                        │
        ▼                    ▼                        ▼
 Analytics service     Anomaly monitor         Investigation agent
 (KPIs, funnels,       (deterministic,         (tool loop on the Claude API,
  cohorts, segments)    writes alerts)          or rule-based fallback)
        │                    │                        │
        └───────────── FastAPI (JSON API) ────────────┘
                             │            ▲
                             │            └── App state (SQLite): alerts, investigations,
                             ▼                evidence, proposals, decisions
              React + TypeScript + Tailwind (Vite)
                             │
              snapshot export → static demo (GitHub Pages)
```

**Two stores on purpose.** The analytics store (DuckDB) is opened read-only by everything except the build step, so neither the API nor the agent can change source data or metric results. Workflow state (alerts, investigations, human decisions) lives in a separate SQLite file.

## 2. Components

| Component | Responsibility | Why this choice | Simpler alternative considered |
|---|---|---|---|
| Synthetic data generator | Simulates Tasklane users, workspaces, sessions, events, plans, experiments; injects documented scenarios | Full control of ground truth; reproducible with a fixed seed | Static CSV fixtures (no realistic behavior, no scenarios) |
| DuckDB | Columnar analytics on a few million events, single file, no server | Fast, SQL, zero ops, same engine locally and in CI | Postgres (needs a server, slower for scans) |
| Metric layer **[decision]** | One definition per metric; every page, the monitor and the agent call it | Prevents "two activation numbers" | Ad-hoc SQL per page (the problem we want to avoid) |
| Analytics service | KPIs, funnels, retention cohorts, segment breakdowns, feature adoption | Thin Python over the metric layer | — |
| Anomaly monitor **[decision]** | Daily/weekly checks, writes alerts with evidence | Deterministic, testable against ground truth | LLM-based detection (not reproducible) |
| Experiment engine **[decision]** | SRM, effect estimates, CIs, guardrails, verdicts, sample-size planner | SciPy/Statsmodels, independently testable | — |
| Investigation agent **[decision: model]** | Plans and runs typed read-only tools, records evidence, returns a structured report | Custom loop on the Claude Messages API (D4) | Framework (rejected in D4) |
| Rule-based investigator | Fixed playbook (decompose by segment, funnel step, mix vs. rate) when no API key | App stays useful offline; clearly labeled | — |
| FastAPI | JSON API, Pydantic schemas shared with the agent tools | Typed, auto OpenAPI docs | Flask (less typing) |
| React frontend | Decision Center, dashboards, experiment pages | D3 | — |
| Snapshot export | Calls every read endpoint the UI uses and writes JSON for the static demo | One frontend codebase serves live and demo mode | Separate demo site (drift) |

## 3. Data model (analytics store)

| Table | Grain | Key columns |
|---|---|---|
| `workspaces` | one per team | workspace_id, created_at, plan, seats, acquisition_channel |
| `users` | one per user | user_id, workspace_id, signup_at (UTC), signup_platform, country, is_inviter |
| `subscriptions` | one per plan period | workspace_id, plan, started_at, ended_at, trial flag |
| `sessions` | one per session | session_id, user_id, platform, app_version, started_at, ended_at |
| `events` | one per event | event_id, user_id, session_id, event_name, occurred_at, properties (JSON) |
| `releases` | one per app release | platform, version, released_at |
| `experiments` | one per experiment | experiment_id, hypothesis, unit, primary metric, guardrails, MDE, planned sample, start/end |
| `experiment_assignments` | one per unit | experiment_id, unit_id, variant, assigned_at |
| `experiment_exposures` | one per first exposure | experiment_id, unit_id, exposed_at |

Event properties may contain user-generated text (task titles); that is where prompt-injection test cases live.

**App state (SQLite):** `alerts`, `investigations`, `tool_calls` (input, output, hash, duration), `evidence` (id → tool call + extracted value), `findings`, `proposals`, `decisions` (who, when, approve/reject, note).

## 4. Metric layer **[decision]**

Each metric is a YAML entry: name, description, entity (user or workspace), numerator, denominator, window (e.g. 7 days after signup), time zone (UTC), maturity rule (a signup cohort only counts once its 7-day window is complete), allowed dimensions. A small Python compiler turns `query(metric, period, grain, filters, group_by)` into parameterized SQL. Tests compare results with an independent pandas reference on fixtures.

Initial metrics: signups, activation rate, signup→activation funnel steps, DAU/WAU/MAU and stickiness, week-1/week-4 retention, feature adoption, trial→paid conversion (workspace level), churn.

## 5. Anomaly detection **[decision]**

Proposal: transparent baseline monitoring.
- Rate metrics (e.g. activation) are checked per mature weekly signup cohort against a trailing 8-week baseline. An alert needs **both** a statistical signal (observed rate outside a band built from the baseline's week-to-week variation plus binomial noise) **and** a practical threshold (e.g. ≥ 2 percentage points), plus a minimum cohort size.
- Count metrics (DAU, signups) are compared with the same weekday of prior weeks (weekly seasonality) using a robust z-score (median/MAD).
- On alert, an automatic decomposition splits the change into segment contributions and separates a **mix effect** (more users from a weaker segment) from a **rate effect** (a segment got worse).
- Measured on the synthetic data: detection of every injected scenario, and the false-alarm count on scenario-free weeks.

## 6. Experiment methodology **[decision]**

Proposal: fixed-horizon frequentist analysis with explicit guards.
- **Randomization unit = workspace** (teammates share the product, so user-level randomization would leak). User-level metrics are then analyzed with cluster-robust standard errors (delta method), so the unit of analysis matches the unit of randomization.
- Pre-registered primary metric, guardrails, MDE and planned sample size; the planner computes runtime.
- **SRM check** (chi-square on assignment counts) runs first; a failed SRM blocks the verdict.
- Effect = absolute and relative difference with 95% CI; proportions via a two-proportion z-test (cluster-adjusted), continuous metrics via Welch's t-test.
- **Peeking:** results before the planned sample are shown as "not decision-grade"; the verdict only unlocks at the planned horizon.
- **Multiple comparisons:** one primary metric; guardrails corrected with Holm.
- **Verdict** combines CI vs. MDE (practical significance) and guardrails: ship / don't ship / keep testing / invalid (SRM or data quality).
- Missing data is reported, never filled with zeros.

## 7. Investigation agent

- **Loop:** Claude Messages API with tool use, written by hand (D4). Limits: max steps, max tokens per run, wall-clock timeout, max retries per tool, cost cap in USD; every limit produces an explicit failure state.
- **Tools (typed, read-only):** `get_metric_definition`, `query_metric`, `compare_periods`, `segment_breakdown`, `funnel`, `retention_cohorts`, `feature_adoption`, `experiment_result`, `get_alert`, `get_releases`, `data_quality_report`. No free-form SQL in the MVP.
- **Evidence:** every tool result gets an evidence ID. The final report is structured (Pydantic): findings, each with claims, each claim with evidence IDs, a confidence level, the hypotheses considered and rejected, limitations and a recommended next action. A validator checks every numeric claim against the referenced evidence and flags or rejects mismatches.
- **Safety:** tool outputs that carry user text are wrapped and marked as data; the agent cannot write, approve or redefine anything. Decisions are human-only.
- **Fallback:** without an API key, the rule-based investigator runs the same tools in a fixed order and produces the same report shape, labeled "Rule-based analysis (no LLM)".
- **Evaluation:** a harness runs the agent on every injected scenario and scores it against ground truth; the measured result goes into the README.

## 8. Testing strategy

| Layer | Tooling | Examples |
|---|---|---|
| Unit / metric | pytest | each metric vs. pandas reference; denominators; incomplete-period exclusion; time zones |
| Statistics | pytest + simulation | CI coverage ≈ 95% over many simulated A/A tests; SRM catches skewed splits; known effects recovered |
| Data quality | pytest | duplicate events, missing events, out-of-order timestamps, tiny cohorts |
| Ground truth | pytest | monitor finds every injected scenario; agent/rule investigator localizes it |
| Agent contract | pytest with a scripted fake model client | malformed output, tool errors, step/cost limits, prompt injection in event properties, write attempts |
| API | pytest + FastAPI TestClient | schemas, errors, read-only guarantees |
| Frontend | Vitest + Testing Library | components, empty/loading/error states |
| End-to-end | Playwright | the seven-step demo journey on the snapshot build |
| Gates / CI | ruff, mypy, eslint, tsc; GitHub Actions | all of the above on every push |

Real-model runs are not part of CI (cost, nondeterminism); they run on demand and are recorded.

## 9. Running and deployment

- **Local:** `uv` for Python, `npm` for the frontend; `make demo` builds data, runs the monitor, starts API and UI. Docker only if it earns its keep later.
- **Static demo (D5):** `make snapshot` exports JSON; the frontend is built in demo mode and published to GitHub Pages (publishing requires separate approval). Write actions in demo mode are clearly marked as not persisted.
- **Secrets:** `ANTHROPIC_API_KEY` from the environment only; `.env.example` documents it.

## 10. Complexity budget

The riskiest parts are the agent's evidence validator, the cluster-robust experiment statistics and the frontend breadth. The plan keeps each one testable on its own and lets the app work end-to-end with the rule-based investigator before the LLM path is added.

## 11. Cut line if the schedule slips

Must-haves are built in this order; if time runs short, items drop from the bottom up and move to the roadmap, never silently:

1. Synthetic data + ground truth, metric layer, anomaly monitor (the foundation everything else needs)
2. Rule-based investigation with evidence tracking, Decision Center with human decisions
3. Experiment evaluation (SRM, CI, guardrails, verdict)
4. LLM investigation agent with the evidence validator
5. Static demo snapshot, README, CI
6. *First to drop:* sample-size planner as its own page (falls back to a planner section on the experiment page)
7. *Second to drop:* filters beyond date and platform on the overview dashboard
8. *Third to drop:* retention-cohort page (cohorts stay available as an agent tool)

Should-haves (feature adoption page, experiment drafting from an investigation, agent evaluation harness, extended adversarial tests) are only started once 1–5 are done. The agent evaluation harness is the first Should-have to pull in, because it produces the measured agent results the README needs.
