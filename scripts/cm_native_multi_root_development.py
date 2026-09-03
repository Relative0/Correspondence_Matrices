"""Run the development-only native multi-root benchmark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_multi_root_experiment import MultiRootConfig, run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    args = parser.parse_args()

    def progress(stage: str, current: int, total: int, workload_id: str) -> None:
        if current == total or current % 24 == 0:
            print(f"native-multi-root {stage} {current}/{total} {workload_id}", flush=True)

    result = run(
        MultiRootConfig(run_id=args.run_id, max_seconds=args.max_seconds),
        args.output, args.library, ROOT, progress=progress)
    print(json.dumps({
        "status": result["status"],
        "union_speedup": result["summary"]["union_speedup_over_separate"],
        "union_ten_percent_gate": result["summary"]["union_ten_percent_gate"],
        "production_promotion": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
