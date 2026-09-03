"""Run the frozen local C36 wider-natural repeated-query experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_wide_repeated_query_experiment import C36Config, run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    args = parser.parse_args()
    def progress(stage: str, current: int, total: int, case_id: str) -> None:
        if current == total or current % 12 == 0:
            print(f"C36 {stage} {current}/{total} {case_id}", flush=True)
    result = run(C36Config(run_id=args.run_id, max_seconds=args.max_seconds), args.output,
                 ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json",
                 ROOT / "docs/recognition/c36_wide_repeated_query_dataset_verification.json",
                 ROOT, progress=progress)
    final = result["summary"]["checkpoints"]["64"]
    print(json.dumps({"status": result["status"], "measurement_rows": result["measurement_rows"],
                      "best_at_64": final["best_fixed_method"],
                      "cm_vs_cse_at_64": final["cm_speedup_over_flattened_cse"],
                      "cm_promotion_gate": result["summary"]["cm_promotion_gate"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
