# Design Blueprint (Phase 3 — draft for approval)

Status: **draft**. Builds on D1–D15 in [DECISIONS.md](DECISIONS.md), especially D10 (lead with analyst judgment).

## 1. Navigation

Left sidebar, workflow first:

| Area | Purpose |
|---|---|
| **Decision Center** | Inbox of open items: new alerts, investigations waiting for review, proposals waiting for a decision; plus decision history |
| **Overview** | Product health: KPI tiles with definitions on hover, trend charts, filters |
| **Funnels & Retention** | Onboarding funnel by step and segment; weekly signup cohorts |
| **Experiments** | List with status and verdict; detail page with SRM, effect + CI, guardrails, planner |
| **Investigations** | All investigation reports, with the evidence trail |
| **Metrics** | Catalog of metric definitions (numerator, denominator, window, maturity rule) |
| **About the data** | Synthetic-data disclosure, injected scenarios (hidden behind a reveal so the demo is not spoiled), data-quality report |

A persistent banner states that all data is synthetic. In the static demo, write actions are labeled "demo, not saved".

## 2. Core interaction patterns

- **Every number explains itself:** hovering a KPI shows its definition and denominator; changes are always shown as both percentage points and percent where that applies.
- **Evidence drill-down:** each claim in an investigation has a small evidence marker; clicking it opens a side panel with the tool call, its inputs and the exact result rows.
- **Confidence is visible:** findings carry a label (supported / suggestive / not supported) and the hypotheses that were ruled out are listed, not hidden.
- **Human decisions are explicit:** approve / reject / request more evidence, each with a required note; the decision is logged with a timestamp.
- **States:** every view has designed loading, empty ("no open alerts this week") and error states.

## 3. Investigation workflow (screens)

Alert card → alert detail (metric, size of change, band, affected cohort weeks, automatic segment decomposition) → "Investigate" (agent or rule-based, labeled) → live step list while it runs (tool calls appear as they finish) → report (summary, findings with evidence, ruled-out hypotheses, limitations, recommended next action) → review (accept/reject per finding) → proposal (fix + verification or experiment draft with the sample-size plan) → decision.

## 4. Experiment workflow (screens)

Experiment list (status, days run vs. planned, verdict chip) → detail: pre-registration (hypothesis, primary metric, guardrails, MDE) → integrity (SRM, exposure checks) → result (effect with CI against the MDE band, guardrails table with Holm-adjusted results) → verdict with plain-English rationale → decision.

## 5. Visual direction — options **[decision]**

| | A. Analyst memo | B. Ops console | C. Clean SaaS |
|---|---|---|---|
| Feel | Calm, editorial; investigations read like a decision memo with footnoted evidence | Dark, dense, monospace numbers, many panels | White cards, one accent color, rounded corners |
| Type | Inter for UI, a serif for report headings, tabular numerals | Inter + JetBrains Mono | Inter |
| Strength | Matches D10 (analyst judgment first); distinctive; reports are pleasant to read | Looks "technical" and powerful | Familiar, safe |
| Weakness | Needs care so dashboards don't feel too sparse | Hard to read for long reports; looks like many monitoring tools | Easily looks like a template |

Both light and dark mode will be supported in any direction.

## 6. UI building blocks **[decision]**

Proposal: Tailwind + shadcn/ui (Radix-based components copied into the repo, fully restyleable, accessible) and Recharts for charts. Alternatives: Tremor (dashboard kit, faster but recognizable look), MUI (heavy, strong default look).

## 7. Next step after approval

Build one prototype screen (Decision Center plus one investigation report) with real components and the chosen direction, show it, collect feedback, then scale across the app.
