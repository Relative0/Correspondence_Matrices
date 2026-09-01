"""Independently verify the successful single-pod C16 v2 Linux attempt."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics


HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "runpod-c16-linux-v2-execute-001"
STUDY = RUN_DIR / "evidence/run-output/c16-linux-confirmation"
MANIFEST = HERE / "c16_linux_upload_manifest_v2.json"
AUTHORIZATION = HERE / "RUNPOD_C16_PACKAGE_V2_EXACT_PAYLOAD_AUTHORIZED_2026_08_31.json"
VALIDATION = HERE / "C16_PACKAGE_V2_LOCAL_VALIDATION_20260831.json"
PRIOR = HERE / "RUNPOD_C16_LINUX_FINAL_VERIFICATION_20260831.json"
OUTPUT = HERE / "RUNPOD_C16_PACKAGE_V2_FINAL_VERIFICATION_20260831.json"
METHODS = {
    "explicit_cm_exhaustive",
    "explicit_cm_screened",
    "packed_source_anf_screened",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def p95(values):
    return statistics.quantiles(values, n=20, method="inclusive")[18]


def main() -> None:
    run = load(RUN_DIR / "RUN.json")
    watchdog = load(RUN_DIR / "WATCHDOG-RESULT.json")
    resources = load(RUN_DIR / "POD-RESOURCE-CHECK.json")
    freeze = load(RUN_DIR / "TRANSPORT-FREEZE.json")
    remote_validation = load(RUN_DIR / "evidence/run-output/REMOTE-VALIDATION.json")
    runtime = load(RUN_DIR / "evidence/run-output/RUNTIME.json")
    dependencies = load(RUN_DIR / "evidence/run-output/DEPENDENCIES.json")
    command = load(RUN_DIR / "evidence/run-output/yosys-c7-linux-confirmation.json")
    summary = load(STUDY / "summary.json")
    rows = [json.loads(line) for line in (STUDY / "measurements.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()]
    dataset = load(HERE / "c16_dataset.json")
    manifest = load(MANIFEST)
    authorization = load(AUTHORIZATION)
    local_validation = load(VALIDATION)
    prior = load(PRIOR)

    cases = {row["case_id"]: row for row in dataset["cases"]}
    expected_keys = {
        (repetition, method, case_id)
        for repetition in range(3)
        for method in METHODS
        for case_id in cases
    }
    observed_keys = {
        (row.get("repetition"), row.get("method"), row.get("case_id")) for row in rows
    }
    if len(observed_keys) != len(rows):
        raise SystemExit("C16 v2 retrieved measurements contain duplicate keys")

    functional = {row["case_id"]: row for row in summary.get("functional_rows", [])}
    if set(functional) != set(cases):
        raise SystemExit("C16 v2 functional rows do not match the frozen dataset")
    for case_id, case in cases.items():
        case_rows = [row for row in rows if row.get("case_id") == case_id]
        if (
            len(case_rows) != 9
            or {row.get("split") for row in case_rows} != {case["split"]}
            or {row.get("n_vars") for row in case_rows} != {case["n_vars"]}
            or len({row.get("output_sha256") for row in case_rows}) != 1
            or len({row.get("best_artifact_sha256") for row in case_rows}) != 1
            or next(iter({row.get("best_artifact_sha256") for row in case_rows}))
            != functional[case_id].get("best_artifact_sha256")
            or functional[case_id].get("exact_best_identity_match") is not True
            or functional[case_id].get("exact_reconstruction") is not True
        ):
            raise SystemExit(f"C16 v2 case replay invariant failed: {case_id}")

    by_case_method = {}
    for row in rows:
        by_case_method.setdefault((row["case_id"], row["method"]), []).append(row)
    case_ids = sorted(cases)
    medians = {
        key: {
            field: statistics.median(row[field] for row in values)
            for field in ("representation_ns", "analysis_ns", "total_ns")
        }
        for key, values in by_case_method.items()
    }
    totals = {
        method: {
            field: sum(medians[(case_id, method)][field] for case_id in case_ids)
            for field in ("representation_ns", "analysis_ns", "total_ns")
        }
        for method in METHODS
    }
    exhaustive, screened = "explicit_cm_exhaustive", "explicit_cm_screened"
    recomputed_speedup = {
        "screened_analysis_over_exhaustive":
            totals[exhaustive]["analysis_ns"] / totals[screened]["analysis_ns"],
        "screened_whole_path_over_exhaustive":
            totals[exhaustive]["total_ns"] / totals[screened]["total_ns"],
        "screened_whole_path_p95":
            p95([medians[(case_id, exhaustive)]["total_ns"] for case_id in case_ids])
            / p95([medians[(case_id, screened)]["total_ns"] for case_id in case_ids]),
        "packed_source_anf_over_explicit_cm_screened":
            totals[screened]["total_ns"] / totals["packed_source_anf_screened"]["total_ns"],
    }
    speedup_matches = all(
        math.isclose(summary["speedup"][key], value, rel_tol=1e-15, abs_tol=0.0)
        for key, value in recomputed_speedup.items()
    )
    totals_match = all(
        summary["median_case_sum_ns"][method][field] == int(value)
        for method, fields in totals.items()
        for field, value in fields.items()
    )
    expected_criteria = {
        "exact": True,
        "screened_analysis_speedup_at_least_1_50x": True,
        "whole_path_speedup_at_least_1_25x": True,
        "whole_path_p95_speedup_at_least_1_20x": True,
    }

    if (
        run.get("status") != "complete"
        or run.get("creation_attempted") is not True
        or run.get("creation_uncertain") is not False
        or run.get("pod_created") is not True
        or run.get("uploaded_source_files") != 18
        or run.get("automatic_replacement_queued") is not False
        or len(run.get("payload_attempts", [])) != 1
        or run["payload_attempts"][0].get("status") != "accepted"
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or run.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
        or len(run.get("cleanup", {}).get("attempts", [])) != 1
        or run["cleanup"]["attempts"][0].get("http_status") != 204
        or watchdog
        != {
            "errors": [],
            "finished_utc": watchdog.get("finished_utc"),
            "status": "controller_cleanup_verified",
        }
        or run.get("actual_resources", {}).get("rate_usd_per_hour") != 0.06
        or run.get("actual_resources", {}).get("ram_gb") != 4.0
        or run.get("actual_resources", {}).get("vcpu_count") != 2
        or run.get("actual_resources", {}).get("container_disk_gb") != 12
        or run.get("actual_resources", {}).get("pod_volume_gb") != 0
        or run.get("actual_resources", {}).get("ports") != ["8080/http"]
        or run.get("actual_resources", {}).get("cloud_evidence") != ["SECURE"]
        or resources.get("network_volume_present") is not False
        or freeze.get("source_files") != 18
        or freeze.get("source_bytes") != 423735
        or freeze.get("manifest_sha256") != sha(MANIFEST)
        or freeze.get("authorization_sha256") != sha(AUTHORIZATION)
        or freeze.get("credentials_recorded_or_uploaded") is not False
        or manifest.get("file_count") != 18
        or manifest.get("bytes") != 423735
        or authorization.get("authorized") is not True
        or authorization.get("one_create") is not True
        or authorization.get("no_replacement") is not True
        or authorization.get("controller_total_ceiling_usd") != 0.05
        or authorization.get("local_validation_pythonpath_injected") is not False
        or local_validation.get("status") != "pass"
        or local_validation.get("pythonpath_injected") is not False
        or command.get("returncode") != 0
        or command.get("stderr_tail") not in (None, "")
        or remote_validation.get("status") != "complete"
        or remote_validation.get("error") is not None
        or dependencies.get("numpy") != "2.3.2"
        or runtime.get("source_files") != 18
        or runtime.get("runpod_pod_id") != run.get("pod_id")
        or summary.get("schema") != "crse-c16-gf2-screened-tail-linux-confirmation/v1"
        or summary.get("status") != "complete"
        or summary.get("semantic_mismatches") != 0
        or summary.get("measurement_rows") != 360
        or summary.get("criteria") != expected_criteria
        or summary.get("second_machine_gate") is not True
        or summary.get("production_promotion") is not False
        or observed_keys != expected_keys
        or any(
            row.get("semantic_mismatches") != 0
            or row.get("artifact_mismatches") != 0
            or any(
                type(row.get(field)) is not int or row[field] <= 0
                for field in ("representation_ns", "analysis_ns", "total_ns")
            )
            or row["total_ns"] != row["representation_ns"] + row["analysis_ns"]
            for row in rows
        )
        or not speedup_matches
        or not totals_match
        or not (RUN_DIR / "evidence.zip").is_file()
        or not 0 <= run.get("estimated_compute_cost_usd", -1) <= 0.05
    ):
        raise SystemExit("C16 v2 RunPod attempt did not satisfy final verification invariants")

    result = {
        "schema": "crse-runpod-c16-package-v2-final-verification/v1",
        "status": "pass",
        "complete": True,
        "scientific_confirmation_complete": True,
        "second_machine_gate": True,
        "criteria": expected_criteria,
        "cases": 40,
        "repetitions": 3,
        "methods": 3,
        "measurement_rows": 360,
        "semantic_mismatches": 0,
        "artifact_mismatches": 0,
        "speedup": recomputed_speedup,
        "median_case_sum_ns": {
            method: {field: int(value) for field, value in fields.items()}
            for method, fields in totals.items()
        },
        "create_requests_this_authorization": 1,
        "automatic_replacement_queued": False,
        "pod_created": True,
        "pod_id": run["pod_id"],
        "uploaded_source_files": 18,
        "uploaded_source_bytes": 423735,
        "owned_pod_absent_verified": True,
        "final_inventories": {"v1": [], "v2": []},
        "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "combined_c16_cloud_cost_usd": (
            prior["estimated_compute_cost_usd"] + run["estimated_compute_cost_usd"]
        ),
        "elapsed_since_create_s": run["elapsed_since_create_s"],
        "run_sha256": sha(RUN_DIR / "RUN.json"),
        "watchdog_sha256": sha(RUN_DIR / "WATCHDOG-RESULT.json"),
        "transport_freeze_sha256": sha(RUN_DIR / "TRANSPORT-FREEZE.json"),
        "evidence_zip_sha256": sha(RUN_DIR / "evidence.zip"),
        "measurements_sha256": sha(STUDY / "measurements.jsonl"),
        "summary_sha256": sha(STUDY / "summary.json"),
        "manifest_sha256": sha(MANIFEST),
        "authorization_sha256": sha(AUTHORIZATION),
    }
    OUTPUT.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
