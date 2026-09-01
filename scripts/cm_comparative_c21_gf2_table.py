from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_table_experiment import C21Config, run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the C21 task-matched exact GF(2) method table")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    args = parser.parse_args()
    result = run(
        C21Config(args.output.name, rounds=args.rounds, max_seconds=args.max_seconds),
        args.output,
        ROOT / "docs/recognition/c21_decomposition_table_dataset.json",
        ROOT / "docs/recognition/runs/c19-logikbench-cheap-work-policy-windows-20260831-001/policy.json",
        ROOT,
    )
    summary = result["summary"]
    print(
        f"C21 status={result['status']} best={summary['best_fixed_method']} "
        f"headroom={summary['oracle_headroom_over_best_fixed']:.4f}x "
        f"rows={result['measurement_rows']}"
    )
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
