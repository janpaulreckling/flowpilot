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

## Count metrics (daily)

Monitored: active users (overall and per platform), event volume per (event, platform), sessions per platform.

- **Baseline:** the same weekday in the previous 4 weeks. Expected = median; robust scale = max(1.4826 × MAD, 5% of the median).
- **Alert** when |obs − median| / scale ≥ 4.0 and the relative change is at least 15%.
- **Tracking-gap rule:** an event-volume alert for (event, platform) on a day when sessions on that platform are within ±10% of their expected value is labeled **possible tracking gap**. Behavioral conclusions for that segment and day are then marked unreliable.

## Evaluation

The monitor is back-tested over the whole data period. Reported: which injected scenarios were detected, how fast, and the number of alerts in weeks and days outside every scenario window (false-alarm count). These numbers are measured, not targets.
