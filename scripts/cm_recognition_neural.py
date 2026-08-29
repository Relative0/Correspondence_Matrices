"""Run the approved bounded CRSE PyTorch representation experiment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.neural_experiment import NeuralConfig, run_neural_experiment


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_neural_experiment(NeuralConfig(), args.output)
    print(json.dumps({"status": result["status"], "wall_seconds": result["wall_seconds"],
                      "classification_rows": result["row_counts"]["classification"],
                      "retrieval_rows": result["row_counts"]["retrieval"],
                      "semantic_mismatches": result["accepted_semantic_mismatches"]}))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
