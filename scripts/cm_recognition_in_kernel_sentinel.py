"""Run the bounded C13 in-kernel tail-sentinel confirmation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.in_kernel_sentinel_experiment import (
    DEFAULT_INPUT, InKernelSentinelConfig, run_in_kernel_sentinel_experiment,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--repetitions", type=int, default=15)
    parser.add_argument("--cache-capacity", type=int, default=1024)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--max-seconds", type=int, default=120)
    args = parser.parse_args(argv)
    result = run_in_kernel_sentinel_experiment(
        InKernelSentinelConfig(
            repetitions=args.repetitions,
            cache_capacity=args.cache_capacity,
            threads=args.threads,
            max_seconds=args.max_seconds,
        ),
        args.output,
        input_path=args.input,
    )
    print(json.dumps({
        "status": result["status"], "criteria": result["criteria"],
        "measurement_rows": result["measurement_rows"],
        "split_summary": result["split_summary"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
