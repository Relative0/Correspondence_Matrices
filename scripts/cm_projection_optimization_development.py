"""Run the development-only exact projection optimization benchmark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_projection_optimization_experiment import (
    ProjectionOptimizationConfig,
    run,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    args = parser.parse_args()

    def progress(stage: str, current: int, total: int, case_id: str) -> None:
        interval = 25 if stage == "performance" else 15
        if current == total or current % interval == 0:
            print(f"projection-optimization {stage} {current}/{total} {case_id}",
                  flush=True)

    result = run(
        ProjectionOptimizationConfig(
            run_id=args.run_id,
            max_seconds=args.max_seconds,
        ),
        args.output,
        ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json",
        ROOT,
        progress=progress,
    )
    print(json.dumps({
        "status": result["status"],
        "best_projection": result["summary"]["best_projection_method"],
        "projection_reaches_r2": result["summary"]["projection_reaches_r2"],
        "production_promotion": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
