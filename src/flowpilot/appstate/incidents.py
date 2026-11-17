"""Group related decline alerts into incidents for the Decision Center (D33, F20).

One injected problem often raises several alerts (overall, a platform, a channel). An incident
is a set of decline alerts on the same metric whose cohort windows overlap; its lead is the
alert with the strongest single detection. Product-metric incidents are ordered by that
strength; data-quality incidents are listed after them, because they block conclusions rather
than describe a product change.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from flowpilot.appstate.alerts import StoredAlert


class Incident(BaseModel):
    incident_id: str
    kind: Literal["metric", "data_quality"]
    metric: str
    lead: StoredAlert
    related: list[StoredAlert]
    severity: float  # |z| of the lead's strongest detection
    status: str  # the lead alert's status: investigations and decisions run on the lead


def build(alerts: list[StoredAlert]) -> list[Incident]:
    declines = [a for a in alerts if a.alert.direction == "decline" and a.status != "closed"]
    groups: dict[tuple[str, str], list[list[StoredAlert]]] = {}
    for a in sorted(declines, key=lambda x: x.alert.first_period_start):
        key = (a.alert.metric, "data_quality" if a.alert.kind == "tracking_gap" else "metric")
        buckets = groups.setdefault(key, [])
        last = buckets[-1] if buckets else None
        if last and a.alert.first_period_start < max(x.alert.last_period_end for x in last):
            last.append(a)
        else:
            buckets.append([a])
    incidents: list[Incident] = []
    for (metric, kind), buckets in groups.items():
        for members in buckets:
            lead = max(members, key=lambda x: abs(x.alert.peak_z or x.alert.max_abs_z))
            incidents.append(Incident(
                incident_id=f"I-{lead.alert.alert_id.removeprefix('A-')}",
                kind=kind,  # type: ignore[arg-type]
                metric=metric, lead=lead,
                related=[m for m in members if m is not lead],
                severity=abs(lead.alert.peak_z or lead.alert.max_abs_z), status=lead.status))
    incidents.sort(key=lambda i: (i.kind == "data_quality", -i.severity))
    return incidents
