"""Run the bounded exact natural source-ANF hybrid experiment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.natural_decomposition_experiment import DEFAULT_SCOUT
from cmbench.recognition.natural_source_anf_experiment import (
    DEFAULT_C5_RUN,
    NaturalSourceAnfConfig,
    run_natural_source_anf_experiment,
)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scout", type=Path, default=DEFAULT_SCOUT)
    parser.add_argument("--base", type=Path, default=DEFAULT_C5_RUN)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--cache-capacity", type=int, default=1024)
    parser.add_argument("--validation-gate-quantile", type=float, default=.90)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--max-seconds", type=int, default=120)
    args = parser.parse_args(argv)
    config = NaturalSourceAnfConfig(
        repetitions=args.repetitions,
        cache_capacity=args.cache_capacity,
        validation_gate_quantile=args.validation_gate_quantile,
        threads=args.threads,
        max_seconds=args.max_seconds,
    )
    result = run_natural_source_anf_experiment(
        config, args.output, scout=args.scout, base=args.base
    )
    print(json.dumps({"status": result["status"], "wall_seconds": result["wall_seconds"],
        "dataset_rows": result["dataset_rows"], "product_pair_budget":
        result.get("gate_selection", {}).get("product_pair_budget"), "criteria": result["criteria"]},
        indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
