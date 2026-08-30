"""Run the bounded CRSE natural profitability-policy experiment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.natural_profitability_policy_experiment import (
    NaturalProfitabilityConfig, run_natural_profitability_policy_experiment,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases-per-circuit", type=int, default=2)
    parser.add_argument("--training-rounds", type=int, default=2)
    parser.add_argument("--evaluation-rounds", type=int, default=3)
    args = parser.parse_args(argv)
    config = NaturalProfitabilityConfig(cases_per_circuit=args.cases_per_circuit,
        training_rounds=args.training_rounds, evaluation_rounds=args.evaluation_rounds)
    summary = run_natural_profitability_policy_experiment(config, args.output)
    print(json.dumps({"status": summary["status"], "wall_seconds": summary["wall_seconds"],
        "case_counts": summary["case_counts"], "semantic_mismatches": summary["semantic_mismatches"],
        "evaluation": summary["summaries"]["evaluation"]}))
    return 0 if summary["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
