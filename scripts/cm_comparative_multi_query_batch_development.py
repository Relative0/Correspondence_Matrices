"""Run the exposed-data exact multi-query batching development experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_multi_query_batch_experiment import (
    MultiQueryBatchConfig,
    run,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    args = parser.parse_args()

    def progress(stage: str, current: int, total: int, case_id: str) -> None:
        interval = 72 if stage == "performance" else 16
        if current == total or current % interval == 0:
            print(f"multi-query-batch {stage} {current}/{total} {case_id}", flush=True)

    result = run(
        MultiQueryBatchConfig(run_id=args.run_id, max_seconds=args.max_seconds),
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
        "best_batch_at_q64": final["best_batch_method"],
        "batch_speedup_at_q64": final["best_batch_speedup_over_best_nonbatch"],
        "batch_gate": result["summary"]["decision"]["batch_continuation_gate_passed"],
        "production_promotion": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
