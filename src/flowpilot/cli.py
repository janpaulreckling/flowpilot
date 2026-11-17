"""Command-line entry point: `flowpilot generate|monitor|serve`."""

from __future__ import annotations

import argparse
import time
from datetime import date

from flowpilot.appstate import db as appdb
from flowpilot.appstate.alerts import save_run
from flowpilot.generator.config import WorldConfig
from flowpilot.generator.simulate import simulate
from flowpilot.metrics.engine import MetricEngine
from flowpilot.monitor.detect import run_monitor
from flowpilot.settings import get_paths
from flowpilot.warehouse.build import build_database, write_raw
from flowpilot.warehouse.connection import connect_read_only


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="flowpilot")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="simulate the synthetic dataset and build the store")
    gen.add_argument("--seed", type=int, default=WorldConfig().seed)
    gen.add_argument("--scale", type=float, default=1.0)
    sub.add_parser("monitor", help="run the anomaly monitor and store its alerts")
    serve = sub.add_parser("serve", help="run the API")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    paths = get_paths()
    if args.command == "generate":
        t0 = time.perf_counter()
        result = simulate(WorldConfig(seed=args.seed, scale=args.scale))
        write_raw(result, paths.raw_dir)
        counts = build_database(paths.raw_dir, paths.analytics_db)
        for name, n in counts.items():
            print(f"{name:24s} {n:>10,d}")
        print(f"built {paths.analytics_db} in {time.perf_counter() - t0:.1f}s")
        if paths.app_db.exists():
            paths.app_db.unlink()
            print(f"reset workflow state {paths.app_db} (it described the previous dataset)")
    elif args.command == "monitor":
        with connect_read_only(paths.analytics_db) as con:
            engine = MetricEngine(con)
            run = run_monitor(engine, date.fromisoformat(
                str(con.execute("SELECT value FROM dataset_info WHERE key = 'period_start'")
                    .fetchone()[0])))  # type: ignore[index]
        app = appdb.connect(paths.app_db)
        n = save_run(app, run)
        app.close()
        declines = sum(a.direction == "decline" for a in run.alerts)
        print(f"{run.tests_performed:,d} tests, {declines} alerts, {n - declines} notices")
    elif args.command == "serve":
        import uvicorn

        uvicorn.run("flowpilot.api.app:app", host="127.0.0.1", port=args.port, reload=False)


if __name__ == "__main__":
    main()
