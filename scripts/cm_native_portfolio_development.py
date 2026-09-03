"""Run the cache-isolated native versus bigint development comparison."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_native_portfolio_experiment import (
    NativePortfolioConfig,
    run,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--dataset", type=Path,
        default=ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json",
    )
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    args = parser.parse_args()

    def progress(stage: str, current: int, total: int, case_id: str) -> None:
        if current == total or current % max(1, total // 20) == 0:
            print(f"{stage}: {current}/{total} ({case_id})", flush=True)

    result = run(
        NativePortfolioConfig(
            run_id=args.run_id,
            max_seconds=args.max_seconds,
        ),
        args.output,
        args.dataset,
        args.library,
        ROOT,
        progress=progress,
    )
    summary = result["summary"]
    print(
        f"best={summary['best_fixed_method']} "
        f"native_vs_best_non_native={summary['native_speedup_over_best_non_native']:.6f} "
        f"oracle_headroom={summary['oracle_speedup_over_best_fixed']:.6f} "
        f"prospective={result['decision']['prospective_confirmation_allowed']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
