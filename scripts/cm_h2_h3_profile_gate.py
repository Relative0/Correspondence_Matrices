"""CLI for the frozen local H2/H3 profile-first gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cmbench.comparative.h2_h3_profile_gate import (
    freeze_to_path,
    run_profile,
    summary_to_path,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("freeze", "run", "summarize"))
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--freeze")
    parser.add_argument("--raw")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    if args.command == "freeze":
        result = freeze_to_path(root, args.output)
    elif args.command == "run":
        if not args.freeze:
            parser.error("run requires --freeze")
        freeze = json.loads(Path(args.freeze).read_text(encoding="utf-8"))
        result = run_profile(root, freeze, args.output)
    else:
        if not args.freeze or not args.raw:
            parser.error("summarize requires --freeze and --raw")
        result = summary_to_path(args.raw, args.freeze, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

