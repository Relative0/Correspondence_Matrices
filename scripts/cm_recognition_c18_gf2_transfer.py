from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.gf2_independent_transfer_experiment import C18TransferConfig, run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run C18 independent exact GF(2) transfer")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    args = parser.parse_args()
    result = run(
        C18TransferConfig("c18-independent-gf2-transfer-windows-20260831-001",
                          rounds=args.rounds, max_seconds=args.max_seconds),
        args.output, ROOT / "docs/recognition/c18_independent_cone_dataset.json",
        ROOT / "docs/recognition/runs/c17-gf2-task-dispatcher-windows-20260831-001/policy.json",
        ROOT)
    print(f"C18 status={result['status']} exact={result['summary']['exactness_gate']} "
          f"speedup={result['summary']['speedup']['c17_over_direct_exhaustive']:.4f}x")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
