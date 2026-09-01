from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.gf2_work_policy_experiment import C19Config, run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run C19 cheap exact GF(2) work-policy study")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--max-seconds", type=float, default=600.0)
    args = parser.parse_args()
    result = run(
        C19Config("c19-logikbench-cheap-work-policy-windows-20260831-001",
                  rounds=args.rounds, max_seconds=args.max_seconds),
        args.output, ROOT / "docs/recognition/c19_logikbench_small_cone_dataset.json",
        ROOT / "docs/recognition/runs/c17-gf2-task-dispatcher-windows-20260831-001/policy.json",
        ROOT)
    selected = result["confirmation"]["methods"]["c19_selected"]
    print(f"C19 status={result['status']} candidate={result['policy']['selected_candidate']} "
          f"gate={result['confirmation']['gate']} "
          f"speedup={selected['aggregate_speedup_over_exhaustive']:.4f}x "
          f"minimum={selected['minimum_case_speedup_over_exhaustive']:.4f}x")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
