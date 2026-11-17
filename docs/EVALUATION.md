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

Filled in by `scripts/evaluate_investigators.py`, in a later commit than this protocol.
