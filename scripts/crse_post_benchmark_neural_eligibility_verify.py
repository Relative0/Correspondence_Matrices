"""Independently replay a post-benchmark neural eligibility artifact."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.post_benchmark_neural_gate import (
    ARTIFACT_SCHEMA,
    VERIFICATION_SCHEMA,
    build_assessment,
    canonical_bytes,
    file_sha256,
    load_default_inputs,
    read_json,
    render_report,
    validate_assessment,
)
from scripts.cm_post_benchmark_neural_eligibility import evidence_git_identity, write_new


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    if not artifact.is_relative_to(ROOT):
        raise ValueError("artifact escaped project")
    manifest_path = artifact / "manifest.json"
    assessment_path = artifact / "assessment.json"
    report_path = artifact / "report.md"
    manifest = read_json(manifest_path)
    assessment = read_json(assessment_path)
    if (
        manifest.get("schema") != ARTIFACT_SCHEMA
        or set(manifest)
        != {
            "schema", "evidence_checkpoint", "evidence_tree", "evidence",
            "sources", "artifacts",
        }
        or set(manifest.get("artifacts", {})) != {"assessment.json", "report.md"}
    ):
        raise ValueError("artifact manifest shape")
    for name, expected in manifest["artifacts"].items():
        path = artifact / name
        if not path.is_file() or file_sha256(path) != expected:
            raise ValueError(f"artifact hash mismatch: {name}")
    for name, expected in manifest["sources"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or file_sha256(path) != expected:
            raise ValueError(f"source hash mismatch: {name}")
    validate_assessment(assessment)
    inputs = load_default_inputs()
    if manifest["evidence"] != inputs["hashes"]:
        raise ValueError("evidence hash mismatch")
    checkpoint, tree = evidence_git_identity()
    if (
        checkpoint != manifest["evidence_checkpoint"]
        or tree != manifest["evidence_tree"]
    ):
        raise ValueError("evidence Git identity mismatch")
    replay = build_assessment(
        inputs,
        evidence_checkpoint=checkpoint,
        evidence_tree=tree,
        source_bindings=manifest["sources"],
    )
    if canonical_bytes(replay) != canonical_bytes(assessment):
        raise ValueError("assessment replay mismatch")
    if report_path.read_text(encoding="utf-8") != render_report(replay):
        raise ValueError("report replay mismatch")
    verification = {
        "schema": VERIFICATION_SCHEMA,
        "status": "verified_no_training",
        "assessment_sha256": file_sha256(assessment_path),
        "manifest_sha256": file_sha256(manifest_path),
        "evidence_checkpoint": checkpoint,
        "surface_count": len(replay["surfaces"]),
        "gross_gate_candidates": replay["gross_gate_candidates"],
        "charged_gate_candidates": replay["charged_gate_candidates"],
        "replay_byte_identical": True,
        "training_performed": False,
        "selector_fitted": False,
        "prospective_data_consumed": False,
        "production_write": False,
        "production_promotion": False,
    }
    write_new(artifact / "independent_verification.json", verification)
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
