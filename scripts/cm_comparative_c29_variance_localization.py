"""Run the C29 q8 counterbalanced variance localization diagnostic."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_variance_localization import C29Config, run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blocks", type=int, default=16)
    parser.add_argument("--max-seconds", type=float, default=600.0)
    args = parser.parse_args()
    result = run(
        C29Config(args.output.name, blocks=args.blocks, max_seconds=args.max_seconds),
        args.output,
        ROOT / "docs/recognition/c27_yosys_fresh_gf2_dataset.json",
        ROOT / "docs/recognition/c27_yosys_fresh_gf2_dataset_verification.json",
        ROOT / "docs/recognition/c27_support_aware_policy.json",
        ROOT / "docs/recognition/c22_source_portfolio_policy.json",
        ROOT / "docs/recognition/runs/c19-logikbench-cheap-work-policy-windows-20260831-001/policy.json",
        ROOT / "docs/recognition/runs/c28-cross-machine-profitability-adjudication-20260901-001/input_manifest.json",
        ROOT,
    )
    summary = result["summary"]
    print(
        f"C29 status={result['status']} batches={summary['measurement_batches']} "
        f"queries={summary['timed_queries']} "
        f"total={summary['aggregate_ratio_of_median_total_speedup']:.4f}x "
        f"query={summary['aggregate_ratio_of_median_query_speedup']:.4f}x"
    )
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
