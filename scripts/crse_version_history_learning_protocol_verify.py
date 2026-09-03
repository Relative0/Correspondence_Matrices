"""Independently verify a version-history learning-protocol artifact."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.version_history_learning_protocol import (
    ARTIFACT_SCHEMA,
    VERIFICATION_SCHEMA,
    benchmark_analytical_controls,
    build_assessment,
    build_source_blind_rows,
    canonical_bytes,
    file_sha256,
    load_verified_benchmark_artifact,
    load_verified_query_ladder_result,
    render_report,
    validate_assessment,
)
from scripts.cm_version_history_learning_protocol import write_new


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    if not artifact.is_relative_to(ROOT) or not artifact.is_dir():
        raise ValueError("artifact must be an in-project directory")
    manifest_path = artifact / "manifest.json"
    assessment_path = artifact / "assessment.json"
    report_path = artifact / "report.md"
    manifest = read_json(manifest_path)
    assessment = read_json(assessment_path)
    if (
        manifest.get("schema") != ARTIFACT_SCHEMA
        or set(manifest)
        != {
            "schema", "source_checkpoint", "sources", "benchmark_input",
            "query_ladder_input", "artifacts",
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
        if (
            not path.is_relative_to(ROOT)
            or not path.is_file()
            or file_sha256(path) != expected
        ):
            raise ValueError(f"source hash mismatch: {name}")

    validate_assessment(assessment)
    benchmark_artifact = ROOT / assessment["benchmark_input"]["artifact_path"]
    bundle = load_verified_benchmark_artifact(benchmark_artifact)
    expected_benchmark_hashes = {
        "assessment_sha256": bundle["hashes"]["assessment"],
        "manifest_sha256": bundle["hashes"]["manifest"],
        "independent_verification_sha256": bundle["hashes"][
            "independent_verification"
        ],
    }
    if manifest["benchmark_input"] != expected_benchmark_hashes:
        raise ValueError("benchmark input hash mismatch")
    query_ladder = load_verified_query_ladder_result(
        ROOT / assessment["query_ladder_input"]["analysis_path"]
    )
    if manifest["query_ladder_input"] != query_ladder["hashes"]:
        raise ValueError("query-ladder input hash mismatch")
    replay = build_assessment(
        bundle,
        query_ladder,
        assessment["analytical_controls"]["timing"],
        source_bindings=manifest["sources"],
        source_checkpoint=manifest["source_checkpoint"],
    )
    if canonical_bytes(replay) != canonical_bytes(assessment):
        raise ValueError("assessment replay mismatch")
    if report_path.read_text(encoding="utf-8") != render_report(replay):
        raise ValueError("report replay mismatch")

    # A fresh short run verifies the timing code remains executable.  Its values
    # are intentionally not compared with the recorded cross-host diagnostic.
    _, timing_cases = build_source_blind_rows(bundle)
    fresh_timing = benchmark_analytical_controls(
        timing_cases,
        budget_ns_per_case=assessment["economics"][
            "maximum_total_overhead_ns_per_case_preserving_1_10"
        ],
        batches=5,
        repetitions=100,
    )
    verification = {
        "schema": VERIFICATION_SCHEMA,
        "status": "verified_protocol_no_training",
        "assessment_sha256": file_sha256(assessment_path),
        "manifest_sha256": file_sha256(manifest_path),
        "benchmark_artifact_reauthenticated": True,
        "query_ladder_result_reauthenticated": True,
        "assessment_replay_byte_identical": True,
        "report_replay_byte_identical": True,
        "fresh_timing_smoke_completed": True,
        "fresh_timing_exact_backend_executions": fresh_timing[
            "exact_backend_executions"
        ],
        "training_performed": False,
        "selector_fitted": False,
        "prospective_data_consumed": False,
        "benchmark_executed": False,
        "advice_enabled": False,
        "production_write": False,
        "production_promotion": False,
    }
    write_new(artifact / "independent_verification.json", verification)
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
