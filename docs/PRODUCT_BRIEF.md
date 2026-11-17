# Product Brief

**FlowPilot turns product telemetry into reviewed product decisions.** It watches a product's key metrics and flags changes that are unlikely to be noise. It then investigates them with controlled, read-only tools and evaluates experiments with defensible statistics. A product manager gets a recommendation with the evidence attached. The human decides; FlowPilot never approves anything on its own.

The loop: **detect → investigate → test → decide → record.**

## The monitored product (synthetic)

**Tasklane** is a fictional task-management product for teams of 3 to 50 people. All of its data is simulated ([DATA_SCENARIOS.md](DATA_SCENARIOS.md)).

| Aspect | |
|---|---|
| Platforms | Web, iOS, Android |
| Plans | 14-day Team trial on signup, then the paid Team plan or Free |
| Acquisition channels | Organic search, paid search, paid social, referral, partner marketplace |
| Activation | A new workspace's owner creates a project **and** an invited teammate joins, both within 7 days of signup ([METRICS.md](METRICS.md)) |
| History | 28 weeks, about 71,000 workspaces, 163,000 users, 6.2 million events |

## Personas

| Persona | Situation | What they need |
|---|---|---|
| **Growth / onboarding PM** | Owns activation and the onboarding funnel; gets asked "why did activation drop?" every week | To know quickly whether a change is real, where it is concentrated, and what to do next |
| **Head of Product** | Runs the weekly product review and approves launches | A short list of issues that matter, each with a recommendation and its evidence, plus experiment verdicts they can trust |
| **Product / data analyst** | Fields ad-hoc questions and guards metric definitions | Fewer repetitive investigations, one source of metric truth, and investigations whose every number can be checked |

## Jobs to be done

1. **When a key metric moves,** I want to know whether it is beyond normal fluctuation and which segment drives it, so I can act before the weekly review instead of after it.
2. **When an anomaly is confirmed,** I want a first investigation with the evidence attached, so the analyst starts from hypotheses instead of a blank query editor.
3. **When an experiment ends,** I want a verdict that checks the sample ratio, guardrails and practical relevance, so we don't ship a false win.
4. **When I approve or reject a recommendation,** I want the decision, my note and the evidence recorded, so we can later see what we decided and why.

## The demo journey

1. **Incident.** The Decision Center opens on the strongest open incident: activation fell after iOS release 4.12. The card shows the window that triggered the alert and the related alerts folded into it.
2. **Investigation.** The report locates the drop:
   - iOS, then version 4.12, then the "invite sent" step, measured against the gap before the release;
   - seasonality and the channel mix are ruled out;
   - the recommendation is fix and verify;
   - every number is footnoted to the tool call that produced it.
3. **Decision.** The PM approves, rejects or asks for more evidence, with a required note.
4. **Experiments.** Four completed experiments show the verdicts a careful analyst would give:
   - ship;
   - no meaningful effect;
   - don't ship because a guardrail was breached;
   - invalid because of a sample ratio mismatch.
5. **Data quality.** An Android tracking gap is reported as "tracking gap or functional break", with no behavioral conclusion.
6. **Ground truth.** "About the data" reveals the injected scenarios, so every claim in the demo can be checked.

The experiments are simulated in the dataset. The sample-size planner is available in the API (`/api/planner`) to plan a follow-up test.

## Success criteria

Each criterion is measured against the synthetic ground truth. The results are in the [README](../README.md) and [METHOD_V2.md](METHOD_V2.md).

| Area | Criterion |
|---|---|
| Detection | Every monitorable injected scenario is flagged; false alarms are counted and reported |
| Investigation | Each scenario is localized correctly, or the report states that the data does not support a conclusion |
| Evidence | Every number in a report matches a recorded tool result, which the validator enforces |
| Experiments | The right verdict for each experiment; a sample ratio mismatch blocks any verdict |
| Metric correctness | SQL metrics match an independent reference implementation |
| Reproducibility | One command rebuilds the data; CI runs all tests and the demo journey |

## Out of scope

- Login, multiple tenants and roles.
- A real event-ingestion SDK.
- Any write access for the investigation tools or the agent.
- Causal claims from observational data.
- A hosted backend.
- Claims about real customers or real business impact.
