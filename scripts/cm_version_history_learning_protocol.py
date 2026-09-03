"""Create the development-only version-history learning-protocol artifact."""
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

from cmbench.recognition.version_history_learning_protocol import (
    ARTIFACT_SCHEMA,
    DEFAULT_BENCHMARK_ARTIFACT,
    DEFAULT_QUERY_LADDER_ANALYSIS,
    benchmark_analytical_controls,
    build_assessment,
    build_source_blind_rows,
    file_sha256,
    load_verified_benchmark_artifact,
    load_verified_query_ladder_result,
    render_report,
)


SOURCE_PATHS = (
    ROOT / "cmbench/recognition/version_history_learning_protocol.py",
    ROOT / "scripts/cm_version_history_learning_protocol.py",
    ROOT / "scripts/crse_version_history_learning_protocol_verify.py",
)


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
    parser.add_argument(
        "--benchmark-artifact", type=Path, default=DEFAULT_BENCHMARK_ARTIFACT
    )
    parser.add_argument(
        "--query-ladder-analysis", type=Path, default=DEFAULT_QUERY_LADDER_ANALYSIS
    )
    parser.add_argument("--timing-batches", type=int, default=21)
    parser.add_argument("--timing-repetitions", type=int, default=2_000)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError("output must be a new in-project directory")
    if any(not path.is_file() for path in SOURCE_PATHS):
        raise ValueError("protocol source closure is incomplete")

    bundle = load_verified_benchmark_artifact(args.benchmark_artifact)
    query_ladder = load_verified_query_ladder_result(args.query_ladder_analysis)
    _, timing_cases = build_source_blind_rows(bundle)
    surface = bundle["assessment"]["surfaces"][
        "lane_d_version_history_resident_engine"
    ]
    timing = benchmark_analytical_controls(
        timing_cases,
        budget_ns_per_case=surface[
            "maximum_overhead_ns_per_case_preserving_1_10x"
        ],
        batches=args.timing_batches,
        repetitions=args.timing_repetitions,
    )
    sources = {
        str(path.relative_to(ROOT)).replace("\\", "/"): file_sha256(path)
        for path in SOURCE_PATHS
    }
    checkpoint = source_checkpoint()
    assessment = build_assessment(
        bundle,
        query_ladder,
        timing,
        source_bindings=sources,
        source_checkpoint=checkpoint,
    )

    output.mkdir(parents=True, exist_ok=False)
    assessment_path = output / "assessment.json"
    report_path = output / "report.md"
    write_new(assessment_path, assessment)
    write_new(report_path, render_report(assessment), json_value=False)
    manifest = {
        "schema": ARTIFACT_SCHEMA,
        "source_checkpoint": checkpoint,
        "sources": sources,
        "benchmark_input": {
            "assessment_sha256": bundle["hashes"]["assessment"],
            "manifest_sha256": bundle["hashes"]["manifest"],
            "independent_verification_sha256": bundle["hashes"][
                "independent_verification"
            ],
        },
        "query_ladder_input": dict(sorted(query_ladder["hashes"].items())),
        "artifacts": {
            "assessment.json": file_sha256(assessment_path),
            "report.md": file_sha256(report_path),
        },
    }
    write_new(output / "manifest.json", manifest)
    print(json.dumps({
        "status": assessment["status"],
        "cases": assessment["dataset"]["cases"],
        "training_allowed": assessment["decision"]["training_allowed"],
        "advice_enabled": assessment["decision"]["advice_enabled"],
        "assessment_sha256": manifest["artifacts"]["assessment.json"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
