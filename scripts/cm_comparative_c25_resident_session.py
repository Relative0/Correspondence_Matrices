from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_resident_session_experiment import C25Config, run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the C25 resident C22 session evaluation")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--max-seconds", type=float, default=1200.0)
    args = parser.parse_args()
    result = run(
        C25Config(args.output.name, rounds=args.rounds, max_seconds=args.max_seconds),
        args.output,
        ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset_v2.json",
        ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset_v2_verification.json",
        ROOT / "docs/recognition/c22_source_portfolio_policy.json",
        ROOT / "docs/recognition/runs/c19-logikbench-cheap-work-policy-windows-20260831-001/policy.json",
        ROOT,
    )
    summary = result["summary"]
    print(
        f"C25 status={result['status']} gate={summary['resident_promotion_gate']} "
        f"break_even={summary['advice_on_break_even_query_count']} "
        f"batches={result['measurement_batches']} queries={result['timed_queries']}"
    )
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
