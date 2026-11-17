# Investigator Evaluation — Protocol

**Committed before any evaluation run.** It compares the rule-based investigator with the LLM agent on the same alerts, with the same tools, the same evidence validator and the same scoring.

## Why new seeds

The rule-based investigator was revised (method v2) after its results on the default seed (20261116) were known. Scoring it there would favor it. Both investigators are therefore scored on **three new seeds, 101, 202 and 303**, which nobody looked at before this protocol was committed. The scenario definitions and dates are the same as in [DATA_SCENARIOS.md](DATA_SCENARIOS.md); only the random draws differ.

## Cases

For each seed:
1. Generate the full dataset.
2. Run the monitor (parameters as in [MONITORING.md](MONITORING.md), v2).
3. Take **every decline alert**: no selection, no exclusions. Each alert is labeled by `flowpilot.evaluation.monitor_eval.attribute` (S1, S2, S5, E3, partial or unexplained).

## Scoring

`flowpilot.evaluation.investigation_eval.score`, unchanged from the commit that introduced this protocol. Per alert, a report passes when all scenario checks pass:

| Scenario | The report must… |
|---|---|
| S1 (activation) | localize to iOS and name version 4.12, the "invite sent" step and the release; rule out calendar; not blame the channel mix; recommend fix and verify |
| S2 | localize to paid social; state "retention, not onboarding"; support a conclusion |
| S5 | draw no behavioral conclusion; recommend fixing tracking; name version 7.3 |
| E3 | name the experiment as a supported explanation; not blame a segment |
| S1 knock-on (retention) | localize to iOS |
| Unexplained | not claim a conclusion |

In addition, every report must pass the evidence validator, or it does not count as completed.

## Measured per investigator

- Pass rate overall and per scenario.
- Completed vs. failed runs, with the failure type for the LLM: step, tool-call, token, cost or time limit, refusal, API error, invalid report.
- For the LLM: report submissions, claims rejected by the validator, and tool errors.
- Runtime per investigation; for the LLM also tokens and US$ per investigation, at list prices.

## LLM settings

- Model and effort are reported with the results.
- Limits as in [AGENT.md](AGENT.md): 16 turns, 30 tool calls, 400k tokens, US$1.50 and 300 s per run.
- A total budget is set before the run; the run stops when it is reached, and that is reported.
- No prompt or tool change is allowed between the first LLM run and the report. If one is made, the whole evaluation is re-run and both versions are reported.

## Results

### Rule-based investigator (seeds 101, 202, 303; `eval/rule_based.json`)

**9 of 16 decline alerts pass**, against 6 of 7 on the default seed it was revised on. The gap is the expected effect of revising rules on one dataset.

| Scenario | Passed |
|---|---|
| S1 iOS activation regression (including partial and knock-on alerts) | 2 of 8 |
| S2 paid-social retention | 3 of 3 |
| S5 Android tracking gap | 3 of 3 |
| E3 experiment effect (partial) | 1 of 2 |

Why S1 alerts failed (one alert can fail several checks):
- **"Calendar ruled out" (4 alerts):** the rule needs every other segment to move by less than 1 pp. On new random draws the other segments often moved a little more, so the hypothesis stayed "inconclusive". The threshold is too strict for normal noise.
- **Localization (2 alerts), funnel step and fix recommendation (2 alerts each):** the segment and step tests did not reach their significance thresholds, so the report did not name iOS 4.12 or the step. The likely cause, not yet verified case by case, is alert windows that mix pre- and post-release weeks.
- **E3 (1 alert):** the experiment's expected contribution stayed below the 25% bar, so it was listed as minor.

These rules are **not** changed in response, because that would repeat the overfitting this evaluation is designed to expose. They are listed in [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) and the roadmap.

### LLM agent

Not run yet: real runs need an API key and a spend limit. The agent will be scored on the same 16 alerts with the same scorer.
