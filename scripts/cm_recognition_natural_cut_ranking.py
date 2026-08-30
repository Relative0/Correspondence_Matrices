"""Run the bounded direct-cut and matched-pair ranking experiment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.natural_cut_experiment import (
    DEFAULT_SCOUT,
    NaturalCutConfig,
    run_natural_cut_experiment,
)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scout", type=Path, default=DEFAULT_SCOUT)
    args = parser.parse_args(argv)
    result = run_natural_cut_experiment(NaturalCutConfig(), args.output, args.scout)
    print(json.dumps({
        "status": result["status"],
        "criteria": result["criteria"],
        "wall_seconds": result["wall_seconds"],
        "row_count": result["row_count"],
    }))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
