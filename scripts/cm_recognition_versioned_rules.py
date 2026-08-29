"""Run the bounded CRSE versioned proved-rule cache experiment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.versioned_rule_experiment import (
    VersionedRuleConfig, run_versioned_rule_experiment,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_versioned_rule_experiment(VersionedRuleConfig(), args.output)
    print(json.dumps({"status": result["status"], "wall_seconds": result["wall_seconds"],
                      "rows": result["row_count"],
                      "semantic_mismatches": result["semantic_mismatches"],
                      "cache_speedup": result.get("summaries", {}).get(
                          "cached_sequence_speedup_over_fresh_pack")}))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
