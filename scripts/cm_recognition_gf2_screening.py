from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.gf2_screening_experiment import (
    GF2ScreeningConfig,
    run_gf2_screening_experiment,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CRSE C16 exact-screened GF(2) tail study")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", default="c16-gf2-screened-tail-windows-20260830-001")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--max-partitions", type=int, default=64)
    parser.add_argument("--materialize-budget", type=int, default=4)
    parser.add_argument("--max-seconds", type=float, default=420.0)
    args = parser.parse_args()
    config = GF2ScreeningConfig(
        args.run_id, 20260830, args.rounds, args.max_partitions,
        args.materialize_budget, args.max_seconds
    )
    result = run_gf2_screening_experiment(config, args.output)
    print(f"C16 status={result['status']} functional={result['summary']['functional_gate']} "
          f"local_timing={result['summary']['local_timing_gate']} "
          f"speedup={result['summary']['speedup']['screened_whole_path_over_exhaustive']:.4f}x")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
