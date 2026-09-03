"""Prepare the source-bound query-ladder and isolated-memory follow-up freeze."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.architecture_query_ladder_freeze import build_followup_freeze


DEFAULT_OUTPUT = (
    ROOT / "docs/recognition/architecture_query_ladder_followup_freeze_20260903"
)
PARENT_FREEZE = "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json"
PARENT_ANALYSIS = "docs/recognition/architecture_comparison_execution_retry_20260903/ANALYSIS.json"
ORACLES = "docs/recognition/architecture_comparison_execution_retry_20260903/ORACLES.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-checkpoint", required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise SystemExit("follow-up freeze output must be a new in-project directory")
    freeze = build_followup_freeze(
        project_root=ROOT,
        source_checkpoint=args.source_checkpoint,
        parent_freeze_path=PARENT_FREEZE,
        parent_analysis_path=PARENT_ANALYSIS,
        oracles_path=ORACLES,
    )
    output.mkdir(parents=True)
    with (output / "FREEZE.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(freeze, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({
        "status": freeze["status"],
        "freeze_sha256": freeze["freeze_sha256"],
        "planned_cells": freeze["schedule"]["planned_cells"],
        "query_counts": freeze["schedule"]["query_counts"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
