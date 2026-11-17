# Product Blueprint (Phase 1)

Status: **approved 2026-11-17** (D6–D8). Builds on decisions D1–D5 in [DECISIONS.md](DECISIONS.md).

## 1. Vision

**FlowPilot turns product telemetry into reviewed product decisions.** It watches a product's key metrics, flags changes that are unlikely to be noise, has an AI analyst investigate them with controlled tools, evaluates experiments with defensible statistics, and hands a product manager a recommendation with the evidence attached. The human decides; FlowPilot never approves anything on its own.

The loop: **detect → investigate → test → decide → record.**

## 2. The monitored product (synthetic)

**Tasklane** (fictional): task management for small teams of 3–50 people.

| Aspect | Proposal |
|---|---|
| Platforms | Web, iOS, Android |
| Plans | Free (up to 3 members) and Team (paid per seat, monthly); 14-day Team trial on signup |
| Acquisition channels | Organic search, paid search, paid social, referral/invite, partner marketplace |
| Unit of analysis | User (most metrics) and workspace (paid conversion, team metrics); kept explicit per metric |
| Activation (proposal) | A new user creates a project **and** at least one invited teammate joins, within 7 days of signup |
| Data | Fully synthetic, seeded and reproducible; ~6 months of history; every injected scenario documented with its ground truth |

All data is clearly labeled synthetic in the app and the README.

## 3. Personas

| Persona | Situation | What they need from FlowPilot |
|---|---|---|
| **Growth / onboarding PM** | Owns activation and the onboarding funnel; gets asked "why did activation drop?" every week | To know quickly whether a move is real, where it is concentrated, and what to do next |
| **Head of Product** | Runs the weekly product review; approves launches | A short list of issues that matter, each with a recommendation and the evidence, plus experiment verdicts they can trust |
| **Product / data analyst** | Fields ad-hoc questions; guards metric definitions | Fewer repetitive investigations, one source of metric truth, and an agent whose every claim can be checked |

## 4. Jobs to be done

1. *When a key metric moves*, I want to know whether it is beyond normal fluctuation and which segment drives it, so I can act before the weekly review instead of after it.
2. *When an anomaly is confirmed*, I want a first investigation with the evidence attached, so my analyst starts from hypotheses instead of a blank query editor.
3. *When an experiment ends*, I want a verdict that checks sample ratio mismatch, guardrails and practical significance, so we don't ship a false win.
4. *When I approve or reject a recommendation*, I want the decision and its evidence recorded, so we can later see what we decided and why.

## 5. Core user journey (the five-minute demo)

1. **Alert.** The monitor flags a drop in activation in the week after mobile release 4.12 (an injected, documented scenario).
2. **Triage.** The PM opens the alert in the Decision Center: metric, size of the change in percentage points and percent, the confidence band, affected period.
3. **Investigation.** The agent breaks the change down by platform, app version, channel and plan, inspects the onboarding funnel, and finds that the drop is concentrated in iOS users on 4.12 at the "invite teammate" step. Competing explanations (seasonality, channel-mix shift) are checked and ruled out or left open. Every statement links to the tool call that produced it.
4. **Review.** The PM reviews the evidence, accepts or rejects each finding, and adds a note.
5. **Proposal.** FlowPilot drafts a follow-up: fix + verification, or an experiment with a sample-size plan (minimum detectable effect, runtime estimate).
6. **Experiment verdict.** The PM opens a completed experiment from the dataset (e.g. a new onboarding checklist) and sees the result: effect with confidence interval, guardrails, SRM check, and a ship / don't ship / keep testing recommendation.
7. **Decision.** The PM approves or rejects; the decision is logged with its evidence.

*Honesty note:* experiments in the demo are pre-simulated in the synthetic dataset. A proposed experiment can be planned in the app, but its results only exist if the dataset contains them; the UI says so.

## 6. Feature prioritization (MVP per D2)

**Must have**
- Metric layer: one definition per metric (numerator, denominator, unit, time zone, completeness rule), used by every page, the monitor and the agent
- Overview dashboard with filters (date, platform, channel, plan)
- Funnels and retention cohorts
- Anomaly monitor (deterministic statistics) with automatic segment breakdown
- AI investigation with evidence tracking, limits, failure states, and a labeled non-LLM fallback
- Experiment evaluation: SRM check, effect + confidence interval, guardrails, practical vs. statistical significance, verdict
- Sample-size / MDE planner
- Decision Center: alerts → investigations → proposals → human decisions, with history
- Synthetic data generator with a ground-truth manifest
- Static public demo snapshot; tests and CI; README

**Should have**
- Feature adoption page
- Draft an experiment directly from an investigation
- Agent evaluation harness: score investigations against the known ground truth and publish the measured result
- Adversarial tests (prompt injection in event properties, malformed agent output, write attempts)

**Could have (roadmap)**
- Conversational analyst chat (reuses the same tools)
- Scheduled monitoring runs and Slack/email notifications

**Won't have in the MVP**
- Login, multiple tenants, roles
- A real event-ingestion SDK or connection to real analytics tools
- Any agent write access to data, metric definitions or experiment results
- Causal claims from observational data (only experiments support causal statements)
- A hosted live backend (D5)

## 7. Success criteria

These are targets to measure, not results. The README will report the measured values.

| Area | Criterion |
|---|---|
| Detection | Every injected anomaly is flagged; false alarms on scenario-free periods are counted and reported |
| Investigation | For each scenario the agent names the injected segment, **or** states that the data does not support a conclusion (the data-quality scenario must end that way) |
| Evidence | Every numeric claim in an investigation references a tool result; a validator rejects claims that don't match |
| Experiments | Positive, null and guardrail-regression experiments get the right verdict; the SRM scenario is flagged and blocks a verdict |
| Metric correctness | SQL metrics match an independent reference implementation on fixtures |
| Reproducibility | One command rebuilds data, runs the analysis and starts the app; CI green |

## 8. Out of scope

Real customer data, real business impact claims, production deployment claims, accuracy numbers that were not measured, and any modification of the sibling portfolio projects.
