"""Run the bounded per-variable equivariant cut experiment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.natural_variable_cut_experiment import (
    DEFAULT_C4_RUN,
    DEFAULT_SCOUT,
    NaturalVariableCutConfig,
    run_natural_variable_cut_experiment,
)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scout", type=Path, default=DEFAULT_SCOUT)
    parser.add_argument("--base-c4", type=Path, default=DEFAULT_C4_RUN)
    args = parser.parse_args(argv)
    result = run_natural_variable_cut_experiment(
        NaturalVariableCutConfig(), args.output, args.scout, args.base_c4
    )
    print(json.dumps({"status": result["status"], "criteria": result["criteria"],
        "wall_seconds": result["wall_seconds"], "row_count": result["row_count"]}))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
