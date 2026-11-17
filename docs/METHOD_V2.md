# Method v2 — Changes After an Independent Review

An independent review (statistics, architecture and security, interview lens) found weaknesses in rules that had been fixed before their first run (MONITORING.md, EXPERIMENTS.md, AGENT.md). Changing a pre-registered rule after seeing results can turn into tuning, so this file does three things:

1. It lists every rule change and its reason **before** v2 is run (this commit).
2. It keeps the v1 results, which stay in the other documents, labeled v1.
3. It reports v2 results next to v1, including anything that gets worse.

## Rule changes

| # | Area | v1 rule | v2 rule | Reason (review finding) |
|---|---|---|---|---|
| M1 | Monitor standard error | SE² = s²ₓ/k + p̄(1−p̄)(1/n_obs + 1/n_base) | SE² = s²ₓ(1/k + 1/8) + p̄(1−p̄)(1/n_obs + 1/n_base) | The extra-binomial variance of the 8-week baseline mean was left out, so SE was too small by about 10%. |
| M2 | Segment scan wording | The z = 3.5 segment threshold "accounts for the number of segment tests". | z = 3.5 is a heuristic, not a correction. Each run reports how many null crossings to expect from its number of tests. | About 1,400 segment tests would need z of about 4.1 under Bonferroni. |
| M3 | Investigator: localization | Lead segment = largest share of the rate effect (≥ 60%) and \|Δ_lead\| ≥ 2\|Δ_rest\|. | Lead segment = largest z of (Δ_segment − Δ_rest) in the alert's direction. Localized if that z ≥ 3 and \|Δ_lead\| ≥ 2\|Δ_rest\|. | The share of contribution mostly measured segment size (the root cause of the two E3 failures). |
| M4 | Investigator: funnel step | Segment vs. everyone else, current period only. | Difference-in-differences of step conversion: (segment − rest), current vs. baseline. A version segment uses its platform as the baseline segment. A step is named if its DiD ≤ −5 pp and the other steps stay within ±2 pp. | A segment that was always weaker at a step would have been blamed. |
| M5 | Investigator: version drill-down | Lowest-rate version with n ≥ 100, if it carries ≥ 80% of the lead change. | The same, plus its rate must differ from the platform baseline with z ≥ 3. | Picking the minimum of noisy versions without a test. |
| M6 | Investigator: competing experiment | Any overlapping experiment with a significant effect on the metric counts as "supported". | Expected contribution = (treatment units in the window ÷ all units in the window) × ITT difference. "Supported" only if it is at least 25% of the observed change with the same sign; otherwise listed as minor. | E3 was "supported" for an alert it could explain only by about 0.3 of 5.1 pp. |
| M7 | Investigator: tracking gap | "Tracking gap, not a behavior change"; real drop ruled out. | "Tracking gap or functional break". Event data alone cannot tell them apart, so the recommendation is to check that the feature works (QA, error logs) before fixing tracking. Still no behavioral conclusion. | A release that breaks task creation looks the same in event data. |
| M8 | Experiments: guardrails | Breached only if harm is significant (Holm, one-sided). | Also tested for non-inferiority with a 1 pp margin (Holm). If a guardrail cannot be shown to lose less than 1 pp, the verdict is "keep testing". | An underpowered guardrail always passed. |
| M9 | Evaluation (scoring only) | S1 credited for any activation decline after Oct 26; E3 credited for any overlapping retention alert. | Full credit only when the alert's segment is the scenario's segment (S1: all signups or iOS) or the scenario's expected contribution is at least 50% of the observed change; otherwise **partial**. Reported as full / partial / unexplained. | "1 false alarm" was a lower bound. |

Documentation fixes that come with v2: METRICS.md no longer promises a 28-day MAU or a data-quality flag on metric rows (neither exists). Tracking gaps are reported by the monitor and the investigations instead.

## Results

Filled in after the v2 run (next commit), next to v1.
