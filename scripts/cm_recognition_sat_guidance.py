"""Run or independently verify the bounded E2/R10 SAT-guidance study."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.sat_guidance_experiment import (
    SatGuidanceConfig, run_sat_guidance_experiment, verify_sat_guidance_run,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--seed", type=int, default=20260830)
    parser.add_argument("--train-per-family", type=int, default=3)
    parser.add_argument("--validation-per-family", type=int, default=1)
    parser.add_argument("--test-per-family", type=int, default=1)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--max-seconds", type=int, default=180)
    args = parser.parse_args()
    if args.verify:
        result = verify_sat_guidance_run(args.output)
    else:
        config = SatGuidanceConfig(
            seed=args.seed, train_per_family=args.train_per_family,
            validation_per_family=args.validation_per_family,
            test_per_family=args.test_per_family,
            repetitions=args.repetitions, threads=args.threads,
            max_seconds=args.max_seconds)
        try:
            result = run_sat_guidance_experiment(config, args.output)
        except Exception as exc:
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / "INCOMPLETE.json").write_text(json.dumps({
                "schema": "crse-sat-guidance-incomplete/v1", "status": "incomplete",
                "error_type": type(exc).__name__, "error": str(exc),
            }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            raise
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
