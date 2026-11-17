# Known Limitations

Honest list of what FlowPilot does not do well yet. Each entry says where it shows up.

## Data
- **All data is synthetic.** Effects are injected by a documented generator ([DATA_SCENARIOS.md](DATA_SCENARIOS.md)); realism is limited to what the generator models (no holidays, no marketing campaigns beyond the scenarios, no bots).
- **Scenario sizes vary with the seed.** The default seed shows S1 overall at −2.8 pp against an expected −3.5 pp, and S2 at −6.3 pp against an expected −8 pp (calibration log in DATA_SCENARIOS.md).

## Monitoring
- **Count monitor lags growth and seasonality.** The same-weekday median of the last four weeks produces many improvement notices (58 in the back-test) when the user base grows or the summer dip ends. Decision D27 keeps the parameters frozen; notices are shown collapsed. ([MONITORING.md](MONITORING.md))
- **Detection is only as fast as the metric's window.** Activation needs 7 days after the last signup of a cohort week, week-4 retention 34 days; S1 could not be detected before day 14 after the release.
- **One false decline alert** in the back-test (week-1 retention, paid social, cohort of Jul 20, z 3.5 at the segment threshold). The segment threshold is a heuristic, not a multiple-comparison correction; each run reports how many chance crossings to expect (0.9 in the back-test).
- **Experiments move aggregate metrics.** E3's treatment half lowers retention enough to raise three alerts; the monitor does not yet know which cohorts are in running experiments.

## Experiments
- **Fixed horizon only (D11).** No sequential or always-valid inference; interim looks are shown but never produce a verdict.
- **No variance reduction** (e.g. CUPED with pre-period behavior); new signups have no pre-period, so its value here would be limited.
- **Dataset experiments use owner-level metrics.** The delta-method path for several users per workspace is validated by simulation, but none of E1–E4 uses a user-level metric yet.
- **Planner MDE is an approximation** (variance evaluated at the baseline rate).
- **E3's primary effect is not detectable at this sample size:** the true +1.5 pp lift in trial-to-paid comes out at +0.8 pp with a CI spanning zero; the guardrail decides that experiment.

## Investigations
- **The rule-based investigator does not generalize as well as the default seed suggests.** On three new seeds it passes 9 of 16 alerts (2 of 8 for the iOS regression), against 6 of 7 on the seed its v2 rules were revised on. The main cause is a strict "calendar ruled out" rule (every other segment must move by less than 1 pp) and significance thresholds that mixed pre/post-release windows miss ([EVALUATION.md](EVALUATION.md)).
- **Mixed causes are hard to score.** When two causes overlap (E3's treatment and the knock-on of S1 on iOS), the investigator reports both, but the fixed scoring rule counts it as a failure (1 of 7 in v2, METHOD_V2.md). In v1 the concentration rule also blamed the largest segment for evenly spread effects; v2 replaced it with a significance test.
- **The rule-based investigator follows one fixed playbook.** It does not try dimensions beyond platform, channel and company size, and its recommendations are templates.
- **The LLM agent has not been run against a real model yet** (D30). It is built and tested with a scripted model; quality and cost per run are unmeasured.
- **A tracking gap and a functional break look alike** in event data (events missing, sessions normal). The investigator says so and recommends checking the feature before fixing the tracking.
- **Data-quality issues are not attached to metric rows.** Retention or activity for an affected platform and period is returned unflagged; the monitor and the investigations carry the warning.

## Experiments (v2)
- Guardrails use a fixed 1 pp non-inferiority margin for every metric; a product team would set it per metric before the test.
