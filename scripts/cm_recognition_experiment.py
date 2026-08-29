#!/usr/bin/env python3
"""Local CRSE experiment. No VM, launcher, network, remote effects, or installs."""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

# Process-local thread request, before NumPy/BLAS imports. Not OS containment.
for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_name] = "1"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.corpus import FAMILIES
from cmbench.recognition.experiment import Config, run_experiment, write_artifacts
from cmbench.recognition.portfolio import BACKENDS


def _integers(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="perform local measurements and fit the small router")
    parser.add_argument("--output", type=Path, help="new output directory; existing directories are refused")
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--train-per-family", type=int, default=12)
    parser.add_argument("--validation-per-family", type=int, default=4)
    parser.add_argument("--test-per-family", type=int, default=4)
    parser.add_argument("--sizes", type=_integers, default=(6, 8, 10))
    parser.add_argument("--query-counts", type=_integers, default=(1, 8, 64))
    parser.add_argument("--held-out-family", choices=FAMILIES, default="mux")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    parser.add_argument("--feature-ablation", action="store_true")
    parser.add_argument("--disable-learned", action="store_true")
    args = parser.parse_args(argv)
    config = Config(
        seed=args.seed, train_per_family=args.train_per_family,
        validation_per_family=args.validation_per_family, test_per_family=args.test_per_family,
        sizes=args.sizes, query_counts=args.query_counts, held_out_family=args.held_out_family,
        rounds=args.rounds, max_seconds=args.max_seconds,
        feature_ablation=args.feature_ablation, learned_enabled=not args.disable_learned,
    )
    try:
        config.validate()
        if not args.run:
            print(json.dumps({"mode": "plan_only", "config": asdict(config),
                              "backends": BACKENDS, "windows_native_work": "deferred",
                              "network": False, "writes": False}, indent=2))
            return 0
        if args.output is None:
            raise ValueError("--run requires --output pointing to a new directory")
        # No overwrite, cleanup, subprocess, credential lookup, or cloud effect.
        args.output.mkdir(parents=True, exist_ok=False)
        with (args.output / "run_spec.json").open("x", encoding="utf-8") as handle:
            json.dump({"schema": "crse-run-spec/v1", "status": "planned", "config": asdict(config),
                       "output": str(args.output.resolve()), "training_steps": "one bounded tree fit per schema",
                       "batch_size": "all training formulas", "threads": 1,
                       "memory_estimate_bytes": 64 * 1024 * 1024,
                       "memory_estimate_is_hard_limit": False,
                       "thread_environment": {name: os.environ.get(name) for name in
                           ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}}, handle, indent=2)
        result = run_experiment(config, progress=lambda message: print(message, flush=True))
        write_artifacts(args.output, result)
        print(f"Status: {result['status']}; mismatches: {result['semantic_mismatches']}")
        print(f"Report: {args.output.resolve() / 'report.md'}")
        return 0 if result["status"] == "complete" else 2
    except (ValueError, OSError) as exc:
        print(f"CRSE experiment refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
