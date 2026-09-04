"""Create a new source-blind q64 learning-evidence freeze artifact."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition import query_ladder_learning_freeze as protocol


def write_new(path: Path, value: Any, *, json_value: bool = True) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        if json_value:
            json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
        else:
            handle.write(str(value))


def source_checkpoint() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError("output must be a new in-project directory")

    freeze = protocol.build_freeze(
        project_root=ROOT,
        source_checkpoint=source_checkpoint(),
    )
    output.mkdir(parents=True, exist_ok=False)
    freeze_path = output / "FREEZE.json"
    report_path = output / "REPORT.md"
    write_new(freeze_path, freeze)
    write_new(report_path, protocol.render_report(freeze), json_value=False)
    manifest = {
        "schema": protocol.MANIFEST_SCHEMA,
        "status": "source_blind_freeze_no_labels",
        "source_checkpoint": freeze["source_checkpoint"],
        "source_closure_sha256": freeze["source_closure_sha256"],
        "artifacts": {
            "FREEZE.json": protocol.file_sha256(freeze_path),
            "REPORT.md": protocol.file_sha256(report_path),
        },
        "exact_backend_executions": 0,
        "timing_rows_produced": 0,
        "labels_produced": 0,
        "models_trained": 0,
        "prospective_cases_consumed": 0,
    }
    write_new(output / "MANIFEST.json", manifest)
    print(json.dumps({
        "status": freeze["status"],
        "cases": freeze["cohort"]["case_count"],
        "split_counts": freeze["cohort"]["source_group_counts_by_split"],
        "freeze_sha256": manifest["artifacts"]["FREEZE.json"],
        "labels_produced": 0,
        "models_trained": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
