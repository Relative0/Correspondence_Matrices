"""Run the bounded E1/R07 ROBDD order study."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.bdd_order_experiment import (
    BddOrderConfig, run_bdd_order_experiment,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260830)
    parser.add_argument("--train-per-family", type=int, default=3)
    parser.add_argument("--validation-per-family", type=int, default=1)
    parser.add_argument("--test-per-family", type=int, default=1)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--best-of-k", type=int, default=4)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--max-seconds", type=int, default=120)
    args = parser.parse_args()
    config = BddOrderConfig(
        seed=args.seed, train_per_family=args.train_per_family,
        validation_per_family=args.validation_per_family,
        test_per_family=args.test_per_family, repetitions=args.repetitions,
        best_of_k=args.best_of_k, threads=args.threads,
        max_seconds=args.max_seconds)
    try:
        result = run_bdd_order_experiment(config, args.output)
    except Exception as exc:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "INCOMPLETE.json").write_text(json.dumps({
            "schema": "crse-bdd-order-incomplete/v1", "status": "incomplete",
            "error_type": type(exc).__name__, "error": str(exc),
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise
    print(json.dumps({
        "status": result["status"], "criteria": result["criteria"],
        "wall_seconds": result["wall_seconds"],
        "training_measurement_rows": result["training_measurement_rows"],
        "evaluation_measurement_rows": result["evaluation_measurement_rows"],
        "task_probe_rows": result["task_probe_rows"],
        "cost_tree_regret": result["cost_tree_regret"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
