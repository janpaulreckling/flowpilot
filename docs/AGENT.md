# Investigations — Tools, Evidence and the Rule-Based Investigator

Implements the technical blueprint §7. **The investigator's rules below were committed on 2026-11-17 before it was run against any alert.** Neither the tools nor the investigator read the ground truth; only `flowpilot.evaluation` does, to score reports afterwards.

## Tools (typed, read-only)

Every tool reads through the metric layer, the experiment engine or the stored alerts, on a read-only connection. Each call is recorded with its input, output, duration and a SHA-256 of the output, and gets an evidence id (`E-1`, `E-2`, …). Each output carries named **facts** (for example `current_rate`, `diff_pp`) that claims cite.

| Tool | Answers |
|---|---|
| `get_alert` | what was flagged, for which segment and period |
| `get_metric_definition` | numerator, denominator, window of a metric |
| `compare_periods` | a metric in the current vs. the baseline period (complete cohorts only) |
| `segment_breakdown` | the change per segment of one dimension, with a mix-vs-rate decomposition |
| `funnel` | onboarding steps for a segment vs. everyone else, current vs. baseline |
| `retention_cohorts` | week-1/2/4 retention per cohort week |
| `feature_adoption` | adoption of a feature by week on its platforms |
| `get_releases` | app releases of a platform |
| `experiment_result` | analysis of one experiment, or the experiments overlapping a period |
| `data_quality_report` | event volume vs. sessions per platform, and tracking-gap alerts |
| `query_metric` | any registry metric with filters and grouping (fallback) |

User-generated text (workspace and project names) never appears in tool outputs. Where text from the data must be shown, it is wrapped and marked as data.

## Report

A report has a title, a summary, findings (each with a confidence: supported / suggestive / not supported), hypotheses (supported / ruled out / inconclusive), limitations, a recommended next action, and `conclusion_supported`. When that is false the report says: **"The available data does not support a reliable conclusion."**

Every number in a claim must cite a fact of a recorded tool call. The **evidence validator** extracts each number from the claim text and checks it against the cited facts (rounded as displayed). A claim with an unmatched number is rejected; a report with a rejected claim is not shown as completed.

## Rule-based investigator (no LLM)

Runs the same tools in a fixed order and produces the same report shape, labeled "Rule-based analysis (no LLM)".

**Rate alerts** (activation, retention, trial to paid). Current period = the alert's weeks; baseline = the 8 complete weeks before.
1. `get_alert`, `get_metric_definition`, `compare_periods` (overall).
2. `data_quality_report` for the current period. A tracking gap on an event the metric depends on → limitation; if the gap covers the whole current period → `conclusion_supported = false`.
3. `segment_breakdown` for `signup_platform`, `acquisition_channel`, `company_size`. The **concentration** of a dimension = the largest single segment's share of the total rate effect. The dimension with the highest concentration is the lead.
4. If the lead segment explains ≥ 60% of the change and its own change is at least twice the change of all other segments combined → **finding: localized** (supported). Then: drill down by `signup_app_version` inside a platform lead; `get_releases` for that platform; a release inside the current period whose version carries the change → supporting finding.
5. Activation alerts: `funnel` for the lead segment vs. everyone else → the step with the largest drop in step conversion is reported (supported if its drop is ≥ 5 pp and other steps moved < 2 pp).
6. Retention alerts: `compare_periods` of activation for the lead segment → unchanged activation (|Δ| < 2 pp) means "retention problem, not onboarding" (supported).
7. `experiment_result` for experiments whose cohorts overlap the current period: an experiment with a breached guardrail or a significant primary effect on the alerted metric is listed as a competing explanation.

Hypotheses always checked:
- **Calendar / seasonality** — ruled out if the change is localized (step 4) and segments outside it moved < 1 pp; otherwise inconclusive.
- **Acquisition mix** — ruled out if the mix effect is < 25% of the change; supported if > 50%; otherwise inconclusive.
- **Data quality** — supported if step 2 found a relevant tracking gap.
- **Running experiment** — supported or inconclusive per step 7.

**Tracking-gap alerts.** `data_quality_report` for the platform and days → events missing while sessions are normal → finding (supported) that the drop is a tracking issue; `conclusion_supported = false` for behavioral metrics in that window; recommendation: fix tracking and re-check affected metrics.

**Recommendation.** Localized regression with a release → fix and verify (compare cohorts on the fixed version; no experiment needed). Localized change without a release → investigate the segment (experiment plan with the planner if a product change is proposed). Data-quality issue → fix tracking. Nothing localized and mix not decisive → no conclusion; keep monitoring.
