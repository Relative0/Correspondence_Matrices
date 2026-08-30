"""Run the bounded CRSE variable-size decomposition experiment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.variable_decomposition_experiment import (
    VariableDecompositionConfig, run_variable_decomposition_experiment,
)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_variable_decomposition_experiment(VariableDecompositionConfig(), args.output)
    print(json.dumps({"status": result["status"], "wall_seconds": result["wall_seconds"],
                      "row_count": result["row_count"], "criteria": result["criteria"]}))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
