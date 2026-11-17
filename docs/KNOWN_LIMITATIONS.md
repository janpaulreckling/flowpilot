# Known Limitations

Honest list of what FlowPilot does not do well yet. Each entry says where it shows up.

## Data
- **All data is synthetic.** Effects are injected by a documented generator ([DATA_SCENARIOS.md](DATA_SCENARIOS.md)); realism is limited to what the generator models (no holidays, no marketing campaigns beyond the scenarios, no bots).
- **Scenario sizes vary with the seed.** The default seed shows S1 overall at −2.8 pp against an expected −3.5 pp, and S2 at −6.3 pp against an expected −8 pp (calibration log in DATA_SCENARIOS.md).

## Monitoring
- **Count monitor lags growth and seasonality.** The same-weekday median of the last four weeks produces many improvement notices (58 in the back-test) when the user base grows or the summer dip ends. Decision D27 keeps the parameters frozen; notices are shown collapsed. ([MONITORING.md](MONITORING.md))
- **Detection is only as fast as the metric's window.** Activation needs 7 days after the last signup of a cohort week, week-4 retention 34 days; S1 could not be detected before day 14 after the release.
- **One false decline alert** in the back-test (week-1 retention, paid social, cohort of Jul 20, z 3.5 at the segment threshold).
- **Experiments move aggregate metrics.** E3's treatment half lowers retention enough to raise three alerts; the monitor does not yet know which cohorts are in running experiments.
