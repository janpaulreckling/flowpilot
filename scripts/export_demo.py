"""Export the static demo: every GET the UI makes, answered by the real API, saved as JSON.

Runs the rule-based investigation for each open incident first (recorded runs, D5), on a copy
of the workflow state, so the local app state is untouched. The file names follow
`snapshotName()` in frontend/src/lib/api.ts, and the query strings follow the way the pages
build them; the end-to-end test fails on any request the snapshot does not cover.

Usage: uv run python scripts/export_demo.py [output dir]
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "frontend" / "public" / "demo-data"


def snapshot_name(path: str) -> str:
    name = re.sub(r"^/api/", "", path)
    name = re.sub(r"[/?&]", "__", name)
    return re.sub(r"[^\w=.-]", "_", name) + ".json"


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def q(params: list[tuple[str, str]]) -> str:
    return urlencode(params)  # same encoding as URLSearchParams for these values


def main() -> None:
    data_dir = Path(os.environ.get("FLOWPILOT_DATA_DIR", ROOT / "data")).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(data_dir / "flowpilot.duckdb", work / "flowpilot.duckdb")
        shutil.copytree(data_dir / "raw", work / "raw")
        if (data_dir / "appstate.sqlite").exists():
            shutil.copy(data_dir / "appstate.sqlite", work / "appstate.sqlite")
        os.environ["FLOWPILOT_DATA_DIR"] = str(work)
        os.environ.pop("ANTHROPIC_API_KEY", None)  # the demo never shows a live AI button
        from flowpilot.api.app import app

        client = TestClient(app, headers={"X-FlowPilot": "1"})
        incidents = client.get("/api/incidents").json()
        if not incidents:
            sys.exit("no incidents: run `make data` first")
        for inc in incidents:
            lead = inc["lead"]["alert"]["alert_id"]
            if not client.get(f"/api/alerts/{lead}/investigations").json():
                client.post(f"/api/alerts/{lead}/investigate").raise_for_status()

        paths = ["/api/dataset", "/api/capabilities", "/api/alerts", "/api/incidents",
                 "/api/decisions", "/api/experiments", "/api/metrics", "/api/ground-truth"]
        dataset = client.get("/api/dataset").json()
        end = date.fromisoformat(dataset["period_end_exclusive"])

        for e in client.get("/api/experiments").json():
            paths.append(f"/api/experiments/{e['experiment_id']}")

        for stored in client.get("/api/alerts").json():
            a = stored["alert"]
            paths.append(f"/api/alerts/{a['alert_id']}/investigations")
            for inv in client.get(f"/api/alerts/{a['alert_id']}/investigations").json():
                paths.append(f"/api/investigations/{inv}")
            if a["kind"] == "rate":  # AlertPage trend
                s = (date.fromisoformat(a["first_period_start"]) - timedelta(days=70))
                t = date.fromisoformat(a["last_period_end"]) + timedelta(days=14)
                base = [("start", s.isoformat()), ("end", t.isoformat())]
                paths.append(f"/api/metrics/{a['metric']}?{q(base)}")
                for dim, value in a["segment"].items():
                    seg = [*base, ("filter", f"{dim}:{value}")]
                    paths.append(f"/api/metrics/{a['metric']}?{q(seg)}")

        for weeks in (8, 16, 28):  # Overview
            s = monday(end - timedelta(days=7 * weeks))
            base = [("start", s.isoformat()), ("end", end.isoformat())]
            for platform in ("all", "web", "ios", "android"):
                for m in ("activation_rate", "week1_retention", "trial_to_paid", "active_users"):
                    extra = [] if platform == "all" else [(
                        "filter", f"{'platform' if m == 'active_users' else 'signup_platform'}:"
                                  f"{platform}")]
                    paths.append(f"/api/metrics/{m}?{q([*base, *extra])}")
            for m, dim in (("activation_rate", "signup_platform"),
                           ("week1_retention", "signup_platform"), ("active_users", "platform")):
                paths.append(f"/api/metrics/{m}?{q([*base, ('group_by', dim)])}")

        f_end = monday(end - timedelta(days=7))  # Funnels & Retention
        f_start = f_end - timedelta(days=28)
        funnel = [("start", f_start.isoformat()), ("end", f_end.isoformat()),
                  ("group_by", "signup_platform")]
        paths.append(f"/api/funnel?{q(funnel)}")
        c_start = f_end - timedelta(days=84)
        for w in (1, 2, 4):
            cohorts = [("start", c_start.isoformat()), ("end", end.isoformat())]
            paths.append(f"/api/metrics/week{w}_retention?{q(cohorts)}")

        if OUT.exists():
            shutil.rmtree(OUT)
        OUT.mkdir(parents=True)
        for path in dict.fromkeys(paths):
            r = client.get(path)
            r.raise_for_status()
            (OUT / snapshot_name(path)).write_text(json.dumps(r.json(), separators=(",", ":")))
        print(f"wrote {len(list(OUT.iterdir()))} snapshot files to {OUT}")


if __name__ == "__main__":
    main()
