from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.gf2_decomposition_experiment import GF2Config, run_gf2_experiment


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frozen CRSE C15 exact CM/GF(2) study")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", default="c15-exact-cm-gf2-windows-20260830-001")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--max-partitions", type=int, default=64)
    parser.add_argument("--max-seconds", type=float, default=600.0)
    args = parser.parse_args()
    result = run_gf2_experiment(GF2Config(args.run_id, 20260830, args.rounds,
        args.max_partitions, args.max_seconds), args.output)
    print(f"C15 status={result['status']} functional={result['summary']['functional_gate']} "
          f"timing_gate={result['summary']['second_machine_timing_gate']} "
          f"mismatches={result['semantic_mismatches']}")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
