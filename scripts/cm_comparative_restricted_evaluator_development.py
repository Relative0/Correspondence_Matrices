"""Run the development-only R0/R1/R2 restricted-evaluator experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_restricted_evaluator_experiment import (
    RestrictedEvaluatorConfig,
    run,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    args = parser.parse_args()

    def progress(stage: str, current: int, total: int, case_id: str) -> None:
        interval = 18 if stage == "performance" else 12
        if current == total or current % interval == 0:
            print(f"restricted-evaluator {stage} {current}/{total} {case_id}", flush=True)

    result = run(
        RestrictedEvaluatorConfig(
            run_id=args.run_id,
            max_seconds=args.max_seconds,
        ),
        args.output,
        ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json",
        ROOT / "docs/recognition/c36_wide_repeated_query_dataset_verification.json",
        ROOT,
        progress=progress,
    )
    final = result["summary"]["checkpoints"]["64"]
    print(json.dumps({
        "status": result["status"],
        "best_fixed_at_q64": final["best_fixed_method"],
        "r1_speedup_over_r0_at_q64": final["r1_speedup_over_r0"],
        "r2_speedup_over_r0_at_q64": final["r2_speedup_over_r0"],
        "production_promotion": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
