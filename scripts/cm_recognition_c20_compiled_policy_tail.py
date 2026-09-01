from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.gf2_compiled_policy_tail_experiment import C20Config, run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run C20 compiled C19 policy on the VTR slow tail")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=9)
    parser.add_argument("--max-seconds", type=float, default=300.0)
    args = parser.parse_args()
    result = run(
        C20Config(args.output.name, rounds=args.rounds, max_seconds=args.max_seconds),
        args.output,
        ROOT / "docs/recognition/c18_independent_cone_dataset.json",
        ROOT / "docs/recognition/runs/c19-logikbench-cheap-work-policy-windows-20260831-001/policy.json",
        ROOT,
    )
    compiled = result["summary"]["methods"]["compiled_c19"]
    print(
        f"C20 status={result['status']} gate={result['summary']['research_gate']} "
        f"speedup={compiled['aggregate_speedup_over_exhaustive']:.4f}x "
        f"minimum={compiled['minimum_case_speedup_over_exhaustive']:.4f}x"
    )
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
