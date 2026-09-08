"""Freeze or evaluate the development-only H6 representation estimator."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.h6_representation_estimator_candidate import (
    evaluate_to_path,
    freeze_to_path,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    freeze_parser = subparsers.add_parser("freeze")
    freeze_parser.add_argument("--project-root", required=True)
    freeze_parser.add_argument("--output", required=True)
    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--project-root", required=True)
    evaluate_parser.add_argument("--freeze", required=True)
    evaluate_parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "freeze":
        result = freeze_to_path(args.project_root, args.output)
    else:
        result = evaluate_to_path(args.project_root, args.freeze, args.output)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
