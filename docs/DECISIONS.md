# Decision Log

Approved decisions for FlowPilot. Each entry records the choice, the rejected alternatives and why. Decisions are only changed with explicit product-owner approval.

## D1 — Monitored product: team task-management SaaS (2026-11-17, approved)

FlowPilot monitors a fictional B2B task-management SaaS for small teams (web + mobile, freemium with a paid team plan).

- **Why:** everyone understands the product in one sentence; activation, an onboarding regression on mobile and a free-to-paid funnel arise naturally; team invites give a collaboration/virality dimension.
- **Rejected:** appointment-booking SaaS (weaker team dimension); invoicing SaaS (too close to the two finance portfolio projects).

## D2 — Scope until mid-December 2026: core MVP, chat later (2026-11-17, approved)

MVP = metric layer, anomaly monitoring, AI investigation, experiment evaluation and a decision center as one connected workflow. The conversational "AI analyst chat" moves to the roadmap.

- **Why:** about four weeks of build time; a complete workflow beats many half-finished pages.
- **Rejected:** full scope including chat (high risk of unfinished parts); analytics without an agent (loses the main differentiator).

## D3 — Stack: FastAPI + DuckDB + React/TypeScript/Tailwind (2026-11-17, approved)

Python backend (FastAPI, Pydantic, SciPy/Statsmodels), DuckDB as the analytical store with a single SQL metric layer, React + TypeScript + Tailwind frontend.

- **Why:** credible SaaS UI that is visibly different from the Streamlit app in cash-reconciliation-engine; Python keeps the statistics libraries.
- **Rejected:** Python-only UI (Streamlit/Dash; looks like the sibling project); Next.js full-stack TypeScript (weaker statistics ecosystem).

## D4 — Agent: custom lightweight loop on the Claude API (2026-11-17, approved)

Own orchestration loop using Claude tool use, typed read-only analytical tools, step/token/cost/time limits, evidence IDs for every claim, a thin provider interface, and a clearly labeled deterministic (non-LLM) fallback when no API key is set.

- **Why:** fully explainable in an interview; few dependencies; matches the "real APIs" principle of the portfolio.
- **Rejected:** LangGraph (more dependencies, less transparent control flow); LiteLLM provider abstraction (extra layer without MVP value).
- **Needs:** an Anthropic API key from the product owner for real runs.

## D5 — Demo and hosting: static live demo + full app locally (2026-11-17, approved)

Public static demo (GitHub Pages or Vercel) built from a data snapshot; investigations shown there are real, recorded agent runs and labeled as such. The full application runs locally with one command.

- **Why:** free, no API-key abuse risk, recruiters can click it without setup.
- **Rejected:** hosted live backend (running cost, key protection, rate limiting); local only (recruiters rarely run it).
- **Note:** publishing/deploying still requires separate approval.

## D6 — Product blueprint approved (2026-11-17, approved)

[PRODUCT_BLUEPRINT.md](PRODUCT_BLUEPRINT.md) is the agreed scope: personas, jobs to be done, the seven-step demo journey, MoSCoW prioritization, success criteria and out-of-scope list.

## D7 — Monitored product name: Tasklane (2026-11-17, approved)

- **Rejected:** Crewboard.

## D8 — Central demo story: mobile onboarding regression (2026-11-17, approved)

Activation drops after iOS release 4.12 at the "invite teammate" step; the agent must localize it and rule out seasonality and channel mix.

- **Why:** easy to follow in five minutes, exercises segment and funnel analysis, leads naturally to an experiment proposal.
- **Rejected:** retention drop in one acquisition cohort as the main story (kept as a secondary injected scenario).

## D9 — Review workflow: checkpoint review after each committed step (2026-11-17, approved)

Every completed step is committed separately and reviewed independently (read-only: diff, architecture, tests, consistency with the approved decisions). Fix requests are applied only after product-owner approval.

## D10 — Positioning: lead with analyst judgment, the agent is the method (2026-11-17, approved)

README and demo lead with analyst judgment: metric definitions, hypotheses checked and ruled out, the experiment verdict and the decision memo. The AI agent is presented openly as the method that does the legwork, with every claim verifiable against its evidence. FlowPilot is not framed as a hand-written-SQL showcase.

## D11 — Experiment statistics: fixed-horizon frequentist (2026-11-17, approved)

Workspace-level randomization with cluster-robust analysis, SRM check first, 95% confidence intervals, verdict only at the pre-registered sample size, Holm correction for guardrails, practical significance via the MDE. Details in [TECHNICAL_BLUEPRINT.md](TECHNICAL_BLUEPRINT.md) §6.

- **Rejected:** sequential (always-valid) tests (harder to explain and validate); Bayesian analysis (prior choice is easy to attack).

## D12 — Anomaly detection: transparent baseline (2026-11-17, approved)

Trailing-baseline bands plus a practical threshold and a minimum sample, followed by a segment/mix decomposition. Details in §5.

- **Rejected:** STL decomposition (less explainable, shaky on six months of data); Prophet/ML (heavy dependency, black box).

## D13 — Metric layer: own YAML registry compiled to SQL (2026-11-17, approved)

- **Rejected:** dbt plus registry (more moving parts; dbt is already shown in cash-reconciliation-engine).

## D14 — LLM model choice deferred to Phase 7 (2026-11-17, approved)

The model stays a configuration value. Until Phase 7 no API key is needed; the rule-based investigator carries the workflow. The model is chosen in Phase 7 from measured cost and quality per run. Agent runs are billed through Anthropic API credits, with a per-run cost cap in code and a spend limit on the account.

- **Options on the table:** Claude Opus 5.5 with a cost cap; Sonnet 5.5 for development and Opus 5.5 for recorded demo runs.

## D15 — Technical blueprint approved (2026-11-17, approved)

[TECHNICAL_BLUEPRINT.md](TECHNICAL_BLUEPRINT.md) is the agreed architecture: read-only DuckDB analytics store plus SQLite workflow state, YAML metric registry, typed read-only agent tools with evidence validation and a rule-based fallback, the testing strategy, local run plus static demo, and the cut line.

## D16 — Visual direction: analyst memo (2026-11-17, approved)

Calm, editorial look: Inter for UI, a serif for report headings, tabular numerals, generous whitespace; investigations read like a decision memo with footnoted evidence. Light and dark mode.

- **Rejected:** ops console (dense dark panels; hard to read long reports, looks like many monitoring tools); clean SaaS cards (looks like a template).

## D17 — Landing page: Decision Center (2026-11-17, approved)

The app opens on the inbox of open alerts, investigations and pending decisions, so the detect → investigate → decide workflow is the first thing a visitor sees.

- **Rejected:** overview dashboard first (makes FlowPilot look like one more dashboard).

## D18 — UI building blocks: shadcn/ui + Recharts (2026-11-17, approved)

- **Rejected:** Tremor (recognizable default look); MUI (heavy, strong Material look).

## D19 — Synthetic scenario catalog approved and frozen (2026-11-17, approved)

[DATA_SCENARIOS.md](DATA_SCENARIOS.md): baseline world, scenarios S1–S5 (plus the S1b decoy), experiments E1–E4 and the adversarial content. Ground truth is fixed before the monitor and agent exist and is never tuned afterwards.

## D20 — Data volume: about 2,500 new workspaces per week (2026-11-17, approved)

At about 1,200 new workspaces per week the 4-week experiments would be underpowered (E1 would reach significance only about 55% of the time), so the verdict would depend on luck. Volume is raised; effects and periods stay as approved. Also corrects an inconsistency in the first draft (it implied about 9,000 workspaces).

- **Rejected:** longer experiments (changes the approved periods, more overlap); larger effects (unrealistic for an onboarding test); choosing a seed that happens to give the "right" answer (manipulation).

## D21 — S4 signal: integration connected at setup (2026-11-17, approved)

Amends the frozen catalog D19 with product-owner approval; the calibration log in [DATA_SCENARIOS.md](DATA_SCENARIOS.md) records it.

The misleading-correlation scenario uses an integration connected during setup (share depends only on company size) instead of "ever used". The first design also produced a within-size gap through survivorship bias (only active users can use a feature), which contradicted the documented ground truth. The survivorship trap of an "ever used" definition is kept as a documented lesson.

- **Rejected:** keep "ever used" and widen the ground-truth statement.

## D22 — Build order: visual prototype before the analytics engine (2026-11-17, approved)

Frontend skeleton plus the Decision Center and one investigation report in the analyst-memo look, so design feedback comes early. Content that is not built yet is labeled "Prototype – sample content" in the UI.

- **Rejected:** analytics engine first (real numbers in the prototype, but later design feedback).

## D23 — Experiments E1–E3 are not rolled out in the data period (2026-11-17, approved)

Amends the frozen catalog D19 with product-owner approval: after each experiment ends, new workspaces get the control experience; the ship / don't-ship decisions are pending at the end of the data period, which is the state the Decision Center demo starts from. This matches the generator (effects apply only to treatment workspaces inside the experiment window).

## D24 — Design prototype approved (2026-11-17, approved)

The analyst-memo look and the structure of the Decision Center and the investigation report are the template for all further pages. Next: Phase 5 (analytics engine), after which real numbers replace the sample content.

## D25 — "Active" means a core action (2026-11-17, approved)

Task created, task completed, comment added, timeline viewed or integration used. Opening the app alone does not count.

- **Rejected:** any session counts (robust to tracking gaps, but counts empty app opens as activity).

## D26 — Retention week N is bracketed (2026-11-17, approved)

Active on at least one day in days 7N to 7N+6 after signup.

- **Rejected:** unbounded ("week N or later"; always higher and hides when users drop off).

## D27 — Monitor parameters stay frozen; improvement notices are shown, not hidden (2026-11-17, approved)

The back-test produced 58 improvement notices from the count monitor (growth and the end of the summer dip). Parameters stay as committed before the first run. The Decision Center leads with decline alerts and lists improvement notices collapsed below them; the limitation is documented.

- **Rejected:** a trend-corrected v2 tuned after seeing the results (risk of fitting this dataset); dropping improvement notices for counts (would hide real positive jumps such as a feature launch).

## D28 — Phase 5 approved (2026-11-17, approved)

Metric layer, monitor and API as built; next is the experimentation engine (Phase 6).
