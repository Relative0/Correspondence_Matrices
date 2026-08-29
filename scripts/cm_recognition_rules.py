"""Run the bounded CRSE proved-rule reuse experiment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.rule_experiment import RuleExperimentConfig, run_rule_experiment


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_rule_experiment(RuleExperimentConfig(), args.output)
    print(json.dumps({"status": result["status"], "wall_seconds": result["wall_seconds"],
                      "rows": result["row_count"],
                      "semantic_mismatches": result["semantic_mismatches"],
                      "break_even_applications": result["summaries"]["estimated_break_even_applications"]}))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
