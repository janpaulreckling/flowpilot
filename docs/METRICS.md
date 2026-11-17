# Metric Catalog (Phase 5 — draft for approval)

Status: **draft**. Every page, the monitor and the investigation tools read metrics only through this catalog (D13). All times are UTC; weeks start Monday. A cohort only counts once its full measurement window has passed (maturity rule), so incomplete periods are never compared with complete ones.

| Metric | Unit of analysis | Numerator | Denominator | Window / maturity |
|---|---|---|---|---|
| `signups` | workspace | new workspaces (self-serve signups) | – | per day/week |
| `activation_rate` | signup (workspace owner) | owners who created a project **and** whose workspace gained a joined teammate | owners in the signup cohort | within 7 days of signup; cohort mature 7 days after its last signup |
| funnel steps | signup | project created → invite sent → teammate joined | previous step | 7 days |
| `active_users` (DAU / WAU / MAU) | user | users with at least one **active event** **[decision]** | – | calendar day / ISO week / 28 days |
| `stickiness` | user | DAU averaged over the week | WAU of that week | complete weeks only |
| `weekN_retention` (N = 1, 2, 4) | signup (owner) | owners active in retention week N **[decision]** | owners in the signup cohort | cohort mature after day 7N+6 |
| `feature_adoption` | user | users with the feature event | active users on the platforms where the feature exists | per week |
| `trial_to_paid` | workspace | workspaces whose first plan after the trial is Team | workspaces whose 14-day trial has ended | mature at trial end |

Changes are always reported as **percentage points** for rates and **percent** for relative change, never mixed. Missing data is never treated as zero; a metric with an incomplete or flagged period returns that flag with the value.

## Open definitions

**Active event.** Option A: any session counts. Option B (recommended): only core actions count (task created, task completed, comment added, timeline viewed, integration used), so app opens without doing anything are not "active".

**Retention week N.** Option A (recommended): active on at least one day in days 7N to 7N+6 after signup (bracketed). Option B: active on or after day 7N (unbounded, always higher, hides churn timing).
