#!/usr/bin/env python3
"""Preview or explicitly run finite CRSE dataset/train/evaluate phases, offline."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_name] = "1"
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.motif_experiment import MotifConfig, run_motif_experiment


def _integers(value):
    try:
        return tuple(int(v) for v in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--phase", choices=("run", "dataset", "train", "evaluate"), default="run")
    parser.add_argument("--input", type=Path, help="dataset or trained artifact directory for separate phases")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--data-seed", type=int, default=20260829)
    parser.add_argument("--training-seeds", type=_integers, default=(20260829, 20260830))
    parser.add_argument("--parent-counts", type=_integers, default=(64, 16, 16, 8))
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    parser.add_argument("--disable-learned", action="store_true")
    args = parser.parse_args(argv)
    config = MotifConfig(args.data_seed, args.training_seeds, args.parent_counts, args.epochs,
                         args.batch_size, args.hidden, args.rounds, args.max_seconds,
                         learned_enabled=not args.disable_learned)
    try:
        config.validate()
        if not args.run:
            print(json.dumps({"mode": "plan_only", "writes": False,
                              "manifest": config.manifest(args.output or Path("docs/recognition/runs/CHOOSE-NEW-RUN"), args.phase)}, indent=2))
            return 0
        if args.output is None:
            raise ValueError("--run requires a new --output directory")
        result = run_motif_experiment(config, args.output, phase=args.phase, input_dir=args.input)
        print(f"Status: {result['status']}; mismatches: {result['semantic_mismatches']}")
        print(f"Report: {args.output.resolve() / 'report.md'}")
        return 0 if result["status"] == "complete" else 2
    except (ValueError, OSError) as exc:
        print(f"CRSE learning refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
