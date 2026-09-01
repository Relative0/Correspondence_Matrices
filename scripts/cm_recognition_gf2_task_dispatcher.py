from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.gf2_task_dispatcher_experiment import (
    GF2DispatcherConfig,
    run_gf2_dispatcher_experiment,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the CRSE C17 exact GF(2) dispatcher study")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "docs/recognition/c16_linux_confirmation/c16_dataset.json")
    parser.add_argument("--run-id", default="c17-gf2-task-dispatcher-windows-20260831-001")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--max-seconds", type=float, default=420.0)
    args = parser.parse_args()
    result = run_gf2_dispatcher_experiment(
        GF2DispatcherConfig(args.run_id, rounds=args.rounds, max_seconds=args.max_seconds),
        args.output, args.dataset, ROOT,
    )
    speed = result["summary"]["speedup"]
    print(f"C17 status={result['status']} exact={result['summary']['exactness_gate']} "
          f"research_gate={result['summary']['local_research_gate']} "
          f"speedup={speed['c17_over_direct_exhaustive']:.4f}x")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
