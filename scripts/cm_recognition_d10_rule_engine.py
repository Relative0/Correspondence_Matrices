from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.d10_rule_experiment import D10Config, run_d10_experiment


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frozen CRSE D10 rule-engine study")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", default="d10-rule-engine-windows-20260830-001")
    parser.add_argument("--rounds", type=int, default=7)
    parser.add_argument("--max-seconds", type=float, default=300.0)
    args = parser.parse_args()
    result = run_d10_experiment(D10Config(args.run_id, 20260830, args.rounds,
                                          args.max_seconds), args.output)
    print(f"D10 status={result['status']} gate={result['summary']['local_promotion_gate']} "
          f"mismatches={result['semantic_mismatches']}")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
