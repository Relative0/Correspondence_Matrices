"""Run the bounded C14 task-guard and shadow-mode confirmation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.task_guard_experiment import (
    DEFAULT_INPUT, TaskGuardConfig, run_task_guard_experiment,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--repetitions", type=int, default=9)
    parser.add_argument("--cache-capacity", type=int, default=1024)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--max-seconds", type=int, default=120)
    args = parser.parse_args(argv)
    result = run_task_guard_experiment(
        TaskGuardConfig(args.repetitions, args.cache_capacity,
                        args.threads, args.max_seconds),
        args.output, input_path=args.input)
    print(json.dumps({
        "status": result["status"], "criteria": result["criteria"],
        "measurement_rows": result["measurement_rows"],
        "split_summary": result["split_summary"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
