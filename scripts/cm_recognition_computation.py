"""Run the bounded CRSE Milestone D task-computation experiment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.computation_experiment import ComputationConfig, run_computation_experiment


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_computation_experiment(ComputationConfig(), args.output)
    print(json.dumps({"status": result["status"], "wall_seconds": result["wall_seconds"],
                      "training_rows": result["row_counts"]["training"],
                      "evaluation_rows": result["row_counts"]["evaluation"],
                      "semantic_mismatches": result["semantic_mismatches"],
                      "failed_rows": result["failed_rows"]}))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
