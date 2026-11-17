# Metric Catalog

Status: **approved 2026-11-17** (D25, D26). Every page, the monitor and the investigation tools read metrics only through this catalog (D13). All times are UTC; weeks start Monday. A cohort only counts once its full measurement window has passed (maturity rule), so incomplete periods are never compared with complete ones.

| Metric | Unit of analysis | Numerator | Denominator | Window / maturity |
|---|---|---|---|---|
| `signups` | workspace | new workspaces (self-serve signups) | – | per day/week |
| `activation_rate` | signup (workspace owner) | owners who created a project **and** whose workspace gained a joined teammate | owners in the signup cohort | within 7 days of signup; cohort mature 7 days after its last signup |
| funnel steps | signup | project created → invite sent → teammate joined | previous step | 7 days |
| `active_users` (DAU / WAU) | user | users with at least one **active event** | – | calendar day / ISO week |
| `stickiness` | user | DAU averaged over the week | WAU of that week | complete weeks only |
| `weekN_retention` (N = 1, 2, 4) | signup (owner) | owners active in retention week N | owners in the signup cohort | cohort mature after day 7N+6 |
| `feature_adoption` | user | users with the feature event | active users on the platforms where the feature exists | per week |
| `trial_to_paid` | workspace | workspaces whose first plan after the trial is Team | workspaces whose 14-day trial has ended | mature at trial end |

Changes are always reported as **percentage points** for rates and **percent** for relative change, never mixed. Missing data is never treated as zero; a period that is incomplete is returned with `complete = false`. Tracking gaps are reported by the monitor and the investigations; they are not attached to metric rows (see KNOWN_LIMITATIONS.md).

## Definitions decided

**Active event (D25).** Only core actions count: task created, task completed, comment added, timeline viewed, integration used. Opening the app without doing anything is not activity. Consequence: a tracking gap in a core event (S5) shows up as an activity dip and must be recognized as a data-quality issue, not a behavior change.

**Retention week N (D26).** Active on at least one day in days 7N to 7N+6 after signup (bracketed), so the curve shows when users drop off.
