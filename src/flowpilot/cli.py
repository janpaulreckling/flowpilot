"""Command-line entry point: `flowpilot generate|serve`."""

from __future__ import annotations

import argparse
import time

from flowpilot.generator.config import WorldConfig
from flowpilot.generator.simulate import simulate
from flowpilot.settings import get_paths
from flowpilot.warehouse.build import build_database, write_raw


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="flowpilot")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="simulate the synthetic dataset and build the store")
    gen.add_argument("--seed", type=int, default=WorldConfig().seed)
    gen.add_argument("--scale", type=float, default=1.0)
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
    elif args.command == "serve":
        import uvicorn

        uvicorn.run("flowpilot.api.app:app", port=args.port, reload=False)


if __name__ == "__main__":
    main()
