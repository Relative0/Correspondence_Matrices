"""Run the validation-frozen staged exact dispatcher experiment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.staged_dispatcher_experiment import (
    DEFAULT_C6_RUN, DEFAULT_C7_RUN, StagedDispatcherConfig, run_staged_dispatcher_experiment,
)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--c6", type=Path, default=DEFAULT_C6_RUN)
    parser.add_argument("--c7", type=Path, default=DEFAULT_C7_RUN)
    parser.add_argument("--repetitions", type=int, default=9)
    parser.add_argument("--cache-capacity", type=int, default=1024)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--max-seconds", type=int, default=120)
    args = parser.parse_args(argv)
    result = run_staged_dispatcher_experiment(StagedDispatcherConfig(
        repetitions=args.repetitions, cache_capacity=args.cache_capacity,
        threads=args.threads, max_seconds=args.max_seconds), args.output,
        c6=args.c6, c7=args.c7)
    print(json.dumps({"status": result["status"], "wall_seconds": result["wall_seconds"],
        "policy": result["policy"], "criteria": result["criteria"]}, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
