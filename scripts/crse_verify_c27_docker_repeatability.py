"""Independently verify three same-host C27 Linux Docker repetitions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c27_linux_confirmation"
MANIFEST = HERE / "c27_linux_upload_manifest.json"
AGGREGATE = HERE / "C27_DOCKER_LINUX_REPEATABILITY_20260901.json"
OUTPUT = HERE / "C27_DOCKER_LINUX_REPEATABILITY_VERIFICATION_20260901.json"
RUN_NAME = "c27-support-aware-fresh-linux-20260831-001"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def surface(result: dict) -> dict:
    summary = result["summary"]
    return {
        "gate": summary["support_aware_confirmation_gate"],
        "break_even_query_count": summary["support_aware_break_even_query_count"],
        "by_query_count": {
            count: {
                "aggregate": values["methods"]["support_aware_c27_advice_on"][
                    "aggregate_speedup_over_direct_screened"],
                "minimum_width": values["methods"]["support_aware_c27_advice_on"][
                    "minimum_width_speedup_over_direct_screened"],
            }
            for count, values in summary["by_query_count"].items()
        },
    }


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 Docker repeatability verification")
    manifest = load(MANIFEST)
    aggregate = load(AGGREGATE)
    surfaces = []
    evidence = []
    for index in (1, 2, 3):
        directory = HERE / f"c27-docker-linux-portability-{index:03d}"
        execution = load(directory / "EXECUTION.json")
        run = directory / "results" / RUN_NAME
        result = load(run / "results.json")
        verification = load(run / "independent_verification.json")
        current_surface = surface(result)
        if (
            execution.get("status") != "pass"
            or execution.get("network_during_workload") is not False
            or execution.get("manifest_sha256") != sha256(MANIFEST)
            or result.get("status") != "complete"
            or result.get("measurement_batches") != 720
            or result.get("timed_queries") != 7560
            or result.get("memory_measurement_batches") != 24
            or result.get("semantic_or_artifact_mismatches") != 0
            or verification.get("status") != "verified"
            or verification.get("measurement_batches_checked") != 720
            or verification.get("timed_query_records_checked") != 7560
            or verification.get("summary_recomputed") is not True
            or verification.get("semantic_or_artifact_mismatches") != 0
            or current_surface.get("gate") is not True
            or current_surface.get("break_even_query_count") != 8
            or aggregate["repetitions"][index - 1]["timing"] != current_surface
        ):
            raise ValueError(f"C27 Docker repetition {index} mismatch")
        surfaces.append(current_surface)
        evidence.append({
            "repetition": index,
            "execution_sha256": sha256(directory / "EXECUTION.json"),
            "results_sha256": sha256(run / "results.json"),
            "independent_verification_sha256": sha256(
                run / "independent_verification.json"),
        })
    if (
        aggregate.get("status") != "complete"
        or aggregate.get("manifest_sha256") != sha256(MANIFEST)
        or aggregate.get("repetition_count") != 3
        or aggregate.get("timing_gate_passes") != 3
        or aggregate.get("break_even_query_counts") != [8, 8, 8]
        or aggregate.get("all_exact") is not True
        or aggregate.get("semantic_or_artifact_mismatches") != 0
        or aggregate.get("network_during_workload") is not False
        or aggregate.get("second_machine_replication") is not False
        or aggregate.get("production_promotion") is not False
    ):
        raise ValueError("C27 Docker repeatability aggregate mismatch")
    ranges = {}
    for count in ("1", "2", "4", "8", "16", "32"):
        aggregate_values = [item["by_query_count"][count]["aggregate"] for item in surfaces]
        width_values = [item["by_query_count"][count]["minimum_width"] for item in surfaces]
        ranges[count] = {
            "aggregate_min": min(aggregate_values),
            "aggregate_median": statistics.median(aggregate_values),
            "aggregate_max": max(aggregate_values),
            "minimum_width_min": min(width_values),
            "minimum_width_median": statistics.median(width_values),
            "minimum_width_max": max(width_values),
        }
    record = {
        "schema": "crse-c27-docker-linux-repeatability-verification/v1",
        "status": "verified",
        "scientific_scope": "three same-host Linux Docker timings; not second-machine",
        "manifest_sha256": sha256(MANIFEST),
        "aggregate_sha256": sha256(AGGREGATE),
        "evidence": evidence,
        "repetition_count": 3,
        "timing_gate_passes": 3,
        "break_even_query_counts": [8, 8, 8],
        "timing_ranges": ranges,
        "q8_aggregate_min": ranges["8"]["aggregate_min"],
        "q8_minimum_width_min": ranges["8"]["minimum_width_min"],
        "measurement_batches_total": 2160,
        "timed_queries_total": 22680,
        "memory_batches_total": 72,
        "semantic_or_artifact_mismatches": 0,
        "all_independent_verifications_passed": True,
        "network_during_workload": False,
        "second_machine_replication": False,
        "production_promotion": False,
        "training": False,
        "production_write": False,
    }
    OUTPUT.write_bytes(json.dumps(
        record, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "status": "verified", "timing_gate_passes": 3,
        "break_even_query_counts": [8, 8, 8],
        "q8_aggregate_min": record["q8_aggregate_min"],
        "q8_minimum_width_min": record["q8_minimum_width_min"],
        "timed_queries_total": record["timed_queries_total"],
        "semantic_or_artifact_mismatches": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
