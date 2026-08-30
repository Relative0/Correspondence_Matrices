"""Run exact cache measurements on audited natural feature-model revisions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.natural_revision_experiment import (
    NaturalRevisionConfig, run_natural_revision_experiment,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--case-limit", type=int, default=0)
    args = parser.parse_args(argv)
    result = run_natural_revision_experiment(
        NaturalRevisionConfig(rounds=args.rounds, case_limit=args.case_limit), args.output)
    summary = result.get("summaries", {})
    print(json.dumps({"status": result["status"], "wall_seconds": result["wall_seconds"],
        "rows": result["row_count"], "semantic_mismatches": result["semantic_mismatches"],
        "cache_speedup_over_fresh_cm": summary.get("exact_cache_speedup_over_fresh_cm"),
        "cache_speedup_over_direct_cnf": summary.get("exact_cache_speedup_over_direct_cnf")}))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
