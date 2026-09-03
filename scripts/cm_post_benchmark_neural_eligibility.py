"""Create the development-only post-benchmark neural eligibility artifact."""
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

from cmbench.recognition.post_benchmark_neural_gate import (
    ANALYSIS_SCRIPT_PATH,
    ARTIFACT_SCHEMA,
    build_assessment,
    file_sha256,
    load_default_inputs,
    render_report,
)


SOURCE_PATHS = (
    ROOT / "cmbench/recognition/post_benchmark_neural_gate.py",
    ROOT / "scripts/cm_post_benchmark_neural_eligibility.py",
    ROOT / "scripts/crse_post_benchmark_neural_eligibility_verify.py",
)


def write_new(path: Path, value: Any, *, json_value: bool = True) -> None:
    mode = "x"
    with path.open(mode, encoding="utf-8", newline="\n") as handle:
        if json_value:
            json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
        else:
            handle.write(str(value))


def evidence_git_identity() -> tuple[str, str]:
    relative = str(ANALYSIS_SCRIPT_PATH.relative_to(ROOT)).replace("\\", "/")
    checkpoint = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", relative],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "show", "-s", "--format=%T", checkpoint],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()
    return checkpoint, tree


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError("output must be a new in-project directory")
    if any(not path.is_file() for path in SOURCE_PATHS):
        raise ValueError("assessment source closure is incomplete")
    source_bindings = {
        str(path.relative_to(ROOT)).replace("\\", "/"): file_sha256(path)
        for path in SOURCE_PATHS
    }
    checkpoint, tree = evidence_git_identity()
    inputs = load_default_inputs()
    assessment = build_assessment(
        inputs,
        evidence_checkpoint=checkpoint,
        evidence_tree=tree,
        source_bindings=source_bindings,
    )
    output.mkdir(parents=True, exist_ok=False)
    assessment_path = output / "assessment.json"
    report_path = output / "report.md"
    write_new(assessment_path, assessment)
    write_new(report_path, render_report(assessment), json_value=False)
    manifest = {
        "schema": ARTIFACT_SCHEMA,
        "evidence_checkpoint": checkpoint,
        "evidence_tree": tree,
        "evidence": assessment["evidence_bindings"],
        "sources": source_bindings,
        "artifacts": {
            "assessment.json": file_sha256(assessment_path),
            "report.md": file_sha256(report_path),
        },
    }
    write_new(output / "manifest.json", manifest)
    print(json.dumps({
        "status": assessment["status"],
        "gross_gate_candidates": assessment["gross_gate_candidates"],
        "charged_gate_candidates": assessment["charged_gate_candidates"],
        "training_allowed": assessment["decision"]["training_allowed"],
        "assessment_sha256": manifest["artifacts"]["assessment.json"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
