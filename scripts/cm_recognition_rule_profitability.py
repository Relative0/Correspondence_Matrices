"""Run the bounded CRSE proved-rule profitability experiment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.profitability_rule_experiment import (
    ProfitabilityRuleConfig, run_profitability_rule_experiment,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cone-count", type=int, default=32)
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args(argv)
    config = ProfitabilityRuleConfig(cone_count=args.cone_count, rounds=args.rounds)
    result = run_profitability_rule_experiment(config, args.output)
    summary = result.get("summaries", {})
    print(json.dumps({"status": result["status"], "wall_seconds": result["wall_seconds"],
        "rows": result["row_count"], "semantic_mismatches": result["semantic_mismatches"],
        "gated_speedup_over_no_rewrite": summary.get("gated_sequence_speedup_over_no_rewrite"),
        "gated_speedup_over_fresh_pack": summary.get("gated_sequence_speedup_over_fresh_pack")}))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
