"""Run the frozen C37 prospective native exact confirmation once."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_native_confirmation import (
    NativeConfirmationConfig,
    run,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=1200.0)
    args = parser.parse_args()

    def progress(stage: str, current: int, total: int, identity: str) -> None:
        interval = 54 if stage == "single_performance" else 24
        if current == total or current % interval == 0:
            print(f"c37 {stage} {current}/{total} {identity}", flush=True)

    result = run(
        NativeConfirmationConfig(
            run_id=args.run_id, max_seconds=args.max_seconds,
        ),
        args.output,
        ROOT / "docs/recognition/c37_native_exact_confirmation/freeze_v3.json",
        ROOT / "docs/recognition/c37_native_exact_confirmation_dataset.json",
        ROOT / "docs/recognition/c37_native_exact_confirmation_dataset_verification.json",
        ROOT,
        progress=progress,
    )
    print(json.dumps({
        "status": result["status"],
        "single_root_speedup": result["single_root"]["native_speedup_over_python_r2"],
        "multi_root_speedup": result["multi_root"]["union_speedup_over_separate"],
        "all_predeclared_gates_passed": result["decision"]["all_predeclared_gates_passed"],
        "production_promotion": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
