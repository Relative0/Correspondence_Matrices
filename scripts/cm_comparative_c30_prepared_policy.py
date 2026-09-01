"""Run C30 prepared-policy context on the unchanged C29 counterbalanced q8 schedule."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_prepared_policy_experiment import C30Config, run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blocks", type=int, default=16)
    parser.add_argument("--max-seconds", type=float, default=600.0)
    args = parser.parse_args()
    result = run(
        C30Config(args.output.name, blocks=args.blocks, max_seconds=args.max_seconds),
        args.output,
        ROOT / "docs/recognition/c27_yosys_fresh_gf2_dataset.json",
        ROOT / "docs/recognition/c27_yosys_fresh_gf2_dataset_verification.json",
        ROOT / "docs/recognition/c27_support_aware_policy.json",
        ROOT / "docs/recognition/c22_source_portfolio_policy.json",
        ROOT / "docs/recognition/runs/c19-logikbench-cheap-work-policy-windows-20260831-001/policy.json",
        ROOT / "docs/recognition/runs/c29-variance-localization-windows-20260901-002",
        ROOT,
    )
    summary = result["summary"]
    print(
        f"C30 status={result['status']} gate={summary['prepared_no_regret_gate']} "
        f"batches={summary['measurement_batches']} queries={summary['timed_queries']} "
        f"total={summary['aggregate_ratio_of_median_charged_total_speedup']:.4f}x "
        f"minimum_width={summary['minimum_width_ratio_of_median_charged_total_speedup']:.4f}x"
    )
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
