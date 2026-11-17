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
