# Anomaly Monitor — Method and Fixed Parameters

Implements D12 (transparent baseline). **These parameters were fixed on 2026-11-17, before the monitor was run against the data for the first time.** The monitor never reads the ground truth; tests use the ground truth only to score it afterwards. If a parameter changes later, the change and its reason are recorded here.

## Rate metrics (weekly signup cohorts)

Monitored: `activation_rate`, `week1_retention`, `week4_retention`, `trial_to_paid`. Only mature cohorts are evaluated.

For each mature week *t* and each window *k* ∈ {1 week, 4 weeks pooled} ending at *t*:

- **Baseline:** the 8 mature weeks immediately before the window. Expected rate p̄ = pooled baseline rate (sum of numerators / sum of denominators).
- **Week-to-week variation:** s² = sample variance of the 8 weekly baseline rates; the extra-binomial part is s²ₓ = max(0, s² − mean of p̄(1−p̄)/nᵢ).
- **Standard error:** SE = √( s²ₓ / k + p̄(1−p̄)/n_obs + p̄(1−p̄)/n_base ).
- **Alert** when all three hold:
  1. statistical: |z| = |obs − p̄| / SE ≥ 3.0 for the overall metric, ≥ 3.5 for a segment;
  2. practical: |obs − p̄| ≥ 2 pp (activation), 3 pp (retention), 1.5 pp (trial to paid);
  3. size: n_obs ≥ 300 for one week, ≥ 1,000 for four weeks.
- **Segments scanned:** each single value of `signup_platform`, `acquisition_channel`, `company_size`. The stricter z threshold accounts for the number of segment tests; the run reports how many tests it made.
- Declines are alerts; improvements are reported as notices.

- **Experiments inside the baseline:** cohorts in a running experiment are not excluded from baselines or windows. A treatment effect therefore moves the aggregate (E3 raised three retention alerts); this is listed in KNOWN_LIMITATIONS.md.

## Count metrics (daily)

Monitored: active users (overall and per platform), event volume per (event, platform), sessions per platform.

- **Baseline:** the same weekday in the previous 4 weeks. Expected = median; robust scale = max(1.4826 × MAD, 5% of the median).
- **Alert** when |obs − median| / scale ≥ 4.0 and the relative change is at least 15%.
- Days whose expected value is zero (e.g. a feature before its launch) are skipped: a relative change is undefined there. *(Clarification added during the first run, which crashed on division by zero; no threshold changed.)*
- **Tracking-gap rule:** an event-volume alert for (event, platform) on a day when sessions on that platform are within ±10% of their expected value is labeled **possible tracking gap**. Behavioral conclusions for that segment and day are then marked unreliable.

## Evaluation

The monitor is back-tested over the whole data period. Reported: which injected scenarios were detected, how fast, and the number of alerts in weeks and days outside every scenario window (false-alarm count). These numbers are measured, not targets.

## Measured results (default dataset, seed 20261116)

Back-test over May 4 – Nov 15, 2026: **4,624 tests**, **9 decline alerts**, **58 improvement notices**. Reproduce with `uv run pytest tests/test_monitor.py`; scoring rules in `src/flowpilot/evaluation/monitor_eval.py`.

| Scenario | Detected | First possible detection | Note |
|---|---|---|---|
| S1 iOS 4.12 activation regression (starts Oct 26) | yes: iOS segment (z 7.2), overall, paid search | Nov 9 | 14 days: one full cohort week plus the 7-day activation window must pass |
| S2 paid-social week-4 retention (cohorts from Sep 7) | yes, 4-week window | Nov 1 | week-4 retention needs 34 days after signup |
| S5 Android tracking gap (Nov 3–5) | yes, labeled **tracking gap** | Nov 4 | sessions were normal, so it was not read as a behavior change |
| S3, S4 | not monitored | – | design / interpretation scenarios for the investigation step |

Decline alerts not caused by an injected anomaly scenario:

- **3 × E3**: the treatment half of the E3 experiment really lowers retention in its cohorts, so these are true signals, not noise.
- **1 unexplained (false alarm)**: week-1 retention of paid-social signups, cohort week of Jul 20 (z 3.5, at the segment threshold).

Improvement notices: 58, almost all from the count monitor (47 event volume, 8 active users, 3 sessions), concentrated in September (32) and July–August (22). Cause: the user base grows and the summer dip ends on Sep 1; a same-weekday median of the last four weeks lags both. No count series raised a false **decline** alert. The parameters above were not changed after this run.
