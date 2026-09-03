"""Run the bounded local C34 natural task-matched headroom experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_natural_headroom_experiment import C34Config, run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "docs/recognition/c34_natural_headroom_dataset.json",
    )
    parser.add_argument(
        "--dataset-verification",
        type=Path,
        default=ROOT / "docs/recognition/c34_natural_headroom_dataset_verification.json",
    )
    parser.add_argument("--max-seconds", type=float, default=900.0)
    args = parser.parse_args()
    last = 0.0

    def progress(stage: str, current: int, total: int, case_id: str) -> None:
        nonlocal last
        now = time.monotonic()
        if current == total or now - last >= 20:
            print(json.dumps({
                "stage": stage,
                "current": current,
                "total": total,
                "case_id": case_id,
            }, sort_keys=True), flush=True)
            last = now

    result = run(
        C34Config(run_id=args.run_id, max_seconds=args.max_seconds),
        args.output,
        args.dataset,
        args.dataset_verification,
        ROOT,
        progress=progress,
    )
    print(json.dumps({
        "status": result["status"],
        "wall_seconds": result["wall_seconds"],
        "truth_best_fixed": result["summary"]["complete_relation"]["best_fixed_method"],
        "decomposition_best_fixed": result["summary"]["gf2_decomposition"]["best_fixed_method"],
        "mismatches": result["semantic_or_artifact_mismatches"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
