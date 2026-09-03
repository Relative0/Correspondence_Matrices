"""Run the development-only native fused-slot benchmark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_native_slot_experiment import NativeSlotConfig, run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    args = parser.parse_args()

    def progress(stage: str, current: int, total: int, case_id: str) -> None:
        interval = 18 if stage == "performance" else 12
        if current == total or current % interval == 0:
            print(f"native-fused-slots {stage} {current}/{total} {case_id}", flush=True)

    result = run(
        NativeSlotConfig(run_id=args.run_id, max_seconds=args.max_seconds),
        args.output,
        ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json",
        args.library,
        ROOT,
        progress=progress,
    )
    print(json.dumps({
        "status": result["status"],
        "best_method": result["summary"]["best_method"],
        "native_speedup_over_python_r2": result["summary"]["native_speedup_over_python_r2"],
        "native_ten_percent_gate": result["summary"]["native_ten_percent_gate"],
        "production_promotion": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
