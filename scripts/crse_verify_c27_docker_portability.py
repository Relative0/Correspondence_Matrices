"""Independently verify and compare the same-host C27 Linux Docker run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
HERE = DOCS / "c27_linux_confirmation"
MANIFEST = HERE / "c27_linux_upload_manifest.json"
DOCKER = HERE / "c27-docker-linux-portability-001"
EXECUTION = DOCKER / "EXECUTION.json"
RUN = DOCKER / "results/c27-support-aware-fresh-linux-20260831-001"
WINDOWS = DOCS / "runs/c27-support-aware-fresh-windows-20260831-001/results.json"
ISOLATED = HERE / "C27_PACKAGE_LOCAL_VALIDATION_20260831.json"
OUTPUT = HERE / "C27_DOCKER_LINUX_PORTABILITY_VERIFICATION_20260901.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timing_surface(result: dict) -> dict:
    summary = result["summary"]
    return {
        "gate": summary["support_aware_confirmation_gate"],
        "break_even_query_count": summary["support_aware_break_even_query_count"],
        "by_query_count": {
            query_count: {
                "aggregate_speedup_over_direct_screened": values["methods"][
                    "support_aware_c27_advice_on"][
                        "aggregate_speedup_over_direct_screened"],
                "minimum_width_speedup_over_direct_screened": values["methods"][
                    "support_aware_c27_advice_on"][
                        "minimum_width_speedup_over_direct_screened"],
            }
            for query_count, values in summary["by_query_count"].items()
        },
    }


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 Docker portability verification")
    manifest = load(MANIFEST)
    execution = load(EXECUTION)
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    windows = load(WINDOWS)
    isolated = load(ISOLATED)
    output_files = [path for path in (DOCKER / "results").rglob("*") if path.is_file()]
    output_bytes = sum(path.stat().st_size for path in output_files)
    if (
        execution.get("status") != "pass"
        or execution.get("scientific_scope")
        != "same-host Linux OS/container portability; not second-machine"
        or execution.get("manifest_sha256") != sha256(MANIFEST)
        or execution.get("source_files") != 63
        or execution.get("source_bytes") != 1078671
        or execution.get("frozen_sources_unchanged_after_run") is not True
        or execution.get("network_during_workload") is not False
        or execution.get("container_root_read_only") is not True
        or execution.get("vcpu_limit") != 2
        or execution.get("memory_limit_gb") != 4
        or execution.get("runtime") != {
            "python": "3.13.15", "numpy": "2.3.2",
            "system": "Linux", "machine": "x86_64"}
        or any(row.get("returncode") != 0 for row in execution.get("commands", []))
        or result.get("status") != "complete"
        or result.get("measurement_batches") != 720
        or result.get("timed_queries") != 7560
        or result.get("memory_measurement_batches") != 24
        or result.get("fallback_controls") != 48
        or result.get("selected_path_controls") != 48
        or result.get("refusal_controls") != 10
        or result.get("semantic_or_artifact_mismatches") != 0
        or verification.get("status") != "verified"
        or verification.get("measurement_batches_checked") != 720
        or verification.get("timed_query_records_checked") != 7560
        or verification.get("summary_recomputed") is not True
        or verification.get("semantic_or_artifact_mismatches") != 0
        or execution.get("results_sha256") != sha256(RUN / "results.json")
        or execution.get("independent_verification_sha256")
        != sha256(RUN / "independent_verification.json")
        or output_bytes != execution.get("result_bytes")
        or output_bytes > manifest.get("result_cap_bytes")
    ):
        raise ValueError("C27 Docker portability evidence mismatch")
    for row in manifest["files"]:
        frozen = DOCKER / "frozen" / row["target"]
        if frozen.stat().st_size != row["bytes"] or sha256(frozen) != row["sha256"]:
            raise ValueError(f"C27 Docker frozen source mismatch: {row['target']}")
    docker_surface = timing_surface(result)
    windows_surface = timing_surface(windows)
    if (
        docker_surface["gate"] is not True
        or docker_surface["break_even_query_count"] != 8
        or windows_surface["gate"] is not True
        or windows_surface["break_even_query_count"] != 8
        or isolated.get("support_aware_confirmation_gate") is not False
    ):
        raise ValueError("C27 Docker timing comparison mismatch")
    comparison = {
        query_count: {
            "windows": windows_surface["by_query_count"][query_count],
            "docker_linux": docker_surface["by_query_count"][query_count],
        }
        for query_count in sorted(
            docker_surface["by_query_count"], key=lambda value: int(value))
    }
    record = {
        "schema": "crse-c27-docker-linux-portability-verification/v1",
        "status": "verified",
        "scientific_scope": execution["scientific_scope"],
        "second_machine_replication": False,
        "second_machine_replication_pending": True,
        "manifest_sha256": sha256(MANIFEST),
        "execution_sha256": sha256(EXECUTION),
        "results_sha256": sha256(RUN / "results.json"),
        "independent_verification_sha256": sha256(
            RUN / "independent_verification.json"),
        "runtime": execution["runtime"],
        "network_during_workload": False,
        "measurement_batches": 720,
        "timed_queries": 7560,
        "memory_batches": 24,
        "semantic_or_artifact_mismatches": 0,
        "independent_verification": "verified",
        "windows_primary": windows_surface,
        "windows_isolated_timing_gate": isolated["support_aware_confirmation_gate"],
        "docker_linux": docker_surface,
        "timing_comparison": comparison,
        "timing_gate_passes_across_three_same_host_runs": 2,
        "timing_sensitive": True,
        "production_promotion": False,
        "result_files": len(output_files),
        "result_bytes": output_bytes,
        "credentials_included": False,
        "training": False,
        "production_write": False,
    }
    OUTPUT.write_bytes(json.dumps(
        record, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "status": "verified",
        "docker_gate": docker_surface["gate"],
        "docker_break_even": docker_surface["break_even_query_count"],
        "windows_primary_gate": windows_surface["gate"],
        "windows_isolated_gate": isolated["support_aware_confirmation_gate"],
        "timing_gate_passes_across_three_same_host_runs": 2,
        "semantic_or_artifact_mismatches": 0,
        "second_machine_replication": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
