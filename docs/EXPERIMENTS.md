# Experiment Analysis — Method and Decision Rules

Implements D11 (fixed-horizon frequentist). **Written and committed on 2026-11-17 before any experiment in the dataset was analyzed with this engine.** The rules are textbook choices, listed with their reason; a later change must be recorded here with its reason.

## Population and unit

- **Randomization unit: workspace.** Teammates share projects and tasks, so randomizing users would let treated and control users influence each other.
- **Analysis population: every assigned workspace (intent to treat).** Exposure logs are used only for integrity checks, never to drop units, because dropping unexposed units can bias the comparison.
- **Unit of analysis matches the unit of randomization.** Metrics are computed per workspace as a ratio *Σ outcomes / Σ users*. For owner-level metrics (activation, retention of the signup, trial to paid) each workspace contributes one user and the method reduces to the usual two-proportion comparison. For user-level metrics (several users per workspace) the variance uses the **delta method for ratio metrics**, which accounts for users of the same workspace being correlated; a naive per-user standard error would be too small.

## Order of checks

1. **Decision-grade?** The experiment's planned end has passed and every assigned cohort is mature for the metric. Otherwise results are shown as *interim, not decision-grade* and no verdict is given (no peeking).
2. **Sample ratio mismatch (SRM).** Chi-square goodness-of-fit of assignment counts against the planned 50/50 split. p < 0.001 → **invalid**; no effect is interpreted. The strict level is standard because SRM checks run on every experiment and a false SRM is costly.
3. **Exposure balance.** Share of assigned units with an exposure log per arm; a difference with p < 0.001 (two-proportion test) → **invalid**.
4. **Sample size.** Fewer units per arm than planned → **keep testing** (underpowered), with the achieved minimum detectable effect reported.
5. **Guardrails** (one-sided harm question, **Holm** correction across the experiment's guardrails at α = 0.05). A guardrail is **breached** when its Holm-adjusted p-value for harm is below 0.05. Breach → **don't ship**, whatever the primary metric says.
6. **Primary metric** (one per experiment, no correction needed):
   - **ship** — the 95% CI of the difference lies entirely above 0;
   - **don't ship** — the 95% CI lies entirely below 0;
   - **no meaningful effect** — equivalence by TOST at α = 0.05: the **90%** CI lies entirely inside (−MDE, +MDE). The 90% interval is what TOST requires for a 5% error rate; MDE is the pre-registered minimum effect worth acting on;
   - **keep testing** — none of the above (the data cannot tell a meaningful effect from none).

Reported for every metric: control and treatment rates, absolute difference in **percentage points** with CI, relative difference in **percent**, p-value, and units per arm. Statistical significance and practical relevance are shown side by side, never merged.

## Planning

Units per arm for a two-sided test of two proportions at α = 0.05 and 80% power; runtime = units needed ÷ recent weekly eligible signups per arm. The planner also inverts the formula to show the MDE a given sample can detect.

## Validation

- A/A simulations: the 95% CI covers the true difference in about 95% of runs, for owner-level and for clustered user-level data; the naive per-user interval is shown to under-cover on clustered data.
- SRM check flags a 52.5/47.5 split at 10,000 units and stays quiet on fair splits.
- The four dataset experiments are scored against their ground truth verdicts (E1 ship, E2 no meaningful effect, E3 don't ship, E4 invalid). Results are reported as measured, including any mismatch.

## Measured results (default dataset, seed 20261116)

Reproduce with `uv run pytest tests/test_experiments.py tests/test_experiment_stats.py`.

| Experiment | Primary metric | Difference (95% CI) | Guardrails | Verdict | Ground truth |
|---|---|---|---|---|---|
| E1 Onboarding checklist | activation | +3.4 pp [+1.6, +5.2] | week-1 retention +1.0 pp, trial to paid +1.3 pp: ok | **ship** | ship |
| E2 Smart due-date suggestions | week-1 retention | +0.8 pp [−1.2, +2.8]; 90% CI [−0.9, +2.4] inside ±3 pp | activation ok | **no meaningful effect** | no meaningful effect |
| E3 Aggressive upgrade prompt | trial to paid | +0.8 pp [−0.3, +1.9] | **week-2 retention −2.2 pp, Holm p = 0.018: breached** | **don't ship** | don't ship (guardrail) |
| E4 Pricing page redesign | trial to paid | not interpreted | – | **invalid** (46.7% treatment, SRM p = 1.3e-11) | invalid (SRM) |

Simulation checks: owner-level A/A coverage of the 95% CI within 93.5–96.5% over 2,000 runs; clustered user-level A/A coverage also within that band with the delta method, while the naive per-user interval covers less than 85%; SRM check flags fewer than 0.4% of fair 10,000-unit splits.

Found by the tests: an interim analysis early in an experiment crashed when a guardrail had no mature cohort yet. Fixed: such guardrails are reported as "not measurable yet" and the analysis stays not decision-grade (regression test `test_interim_look_gives_no_verdict`).
