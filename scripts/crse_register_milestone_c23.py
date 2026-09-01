"""Register the verified local C23 fresh-source GF(2) table."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c23-yosys-fresh-gf2-table-windows-20260831-002"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C23_FRESH_YOSYS_GF2_TABLE_2026_08_31.md"
MACHINE = "learning_milestone_c23_fresh_yosys_gf2_table_results.json"
FAILED_ATTEMPT = (
    DOCS / "c23_linux_confirmation/RUNPOD_C23_FAILED_ATTEMPT_VERIFICATION_20260831.json")
LINUX_FINAL = (
    DOCS / "c23_linux_confirmation/RUNPOD_C23_RETRY_002C_FINAL_VERIFICATION_20260831.json")
CROSS_MACHINE = DOCS / "c23_linux_confirmation/C23_LOCAL_LINUX_COMPARISON_20260831.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def upsert(container: dict, scope: str) -> None:
    value = {"report": REPORT, "machine_summary": MACHINE, "scope": scope}
    rows = [row for row in container["results"] if row.get("report") == REPORT]
    if len(rows) > 1:
        raise SystemExit("duplicate C23 registration")
    if rows:
        rows[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    dataset_verification = load(DOCS / "c23_yosys_fresh_gf2_dataset_v2_verification.json")
    manifest = load(DOCS / "c23_linux_confirmation/c23_linux_upload_manifest.json")
    package_validation = load(
        DOCS / "c23_linux_confirmation/C23_PACKAGE_LOCAL_VALIDATION_20260831.json")
    failed_attempt = load(FAILED_ATTEMPT) if FAILED_ATTEMPT.exists() else None
    linux_final = load(LINUX_FINAL) if LINUX_FINAL.exists() else None
    cross_machine = load(CROSS_MACHINE) if CROSS_MACHINE.exists() else None
    summary = result["summary"]
    packed = summary["methods"]["source_packed_anf"]
    screened = summary["methods"]["cm_screened"]
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("measurement_rows") != 1680
        or result.get("memory_measurement_rows") != 56
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("claims", {}).get("unchanged_c21_methods") is not True
        or result.get("claims", {}).get("fresh_confirmation") is not True
        or result.get("claims", {}).get("production_promotion") is not False
        or summary.get("exactness_gate") is not True
        or summary.get("best_fixed_method") != "source_packed_anf"
        or verification.get("status") != "verified"
        or verification.get("functional_cases_replayed") != 48
        or verification.get("measurement_rows_checked") != 1680
        or verification.get("summary_recomputed") is not True
        or dataset_verification.get("status") != "verified"
        or dataset_verification.get("cases_replayed") != 48
        or dataset_verification.get("prior_truth_overlaps") != 0
        or dataset_verification.get("out_of_task_support_cases") != 0
        or manifest.get("file_count") != 52
        or manifest.get("bytes") != 903745
        or package_validation.get("status") != "pass"
        or package_validation.get("initial_file_count") != 52
        or (failed_attempt is not None and (
            failed_attempt.get("status") != "pass"
            or failed_attempt.get("scientific_replication_complete") is not False
            or failed_attempt.get("creation_http_status") != 500
            or failed_attempt.get("pod_created") is not False
            or failed_attempt.get("files_uploaded") != 0
            or failed_attempt.get("owned_pod_absent_verified") is not True
            or failed_attempt.get("final_inventories") != {"v1": [], "v2": []}
        ))
        or ((linux_final is None) != (cross_machine is None))
        or (linux_final is not None and (
            linux_final.get("status") != "pass"
            or linux_final.get("scientific_confirmation_complete") is not True
            or linux_final.get("measurement_rows") != 1680
            or linux_final.get("memory_rows") != 56
            or linux_final.get("semantic_or_artifact_mismatches") != 0
            or linux_final.get("owned_pod_absent_verified") is not True
            or linux_final.get("final_inventories") != {"v1": [], "v2": []}
            or linux_final.get("automatic_replacement_queued") is not False
            or not 0 <= linux_final.get("estimated_compute_cost_usd", -1) <= 0.05
            or cross_machine.get("status") != "verified"
            or cross_machine.get("corpus_or_methods_changed") is not False
            or cross_machine.get("semantic_or_artifact_mismatches") != 0
            or cross_machine.get("conclusions", {}).get("exact_transfer") is not True
            or cross_machine.get("conclusions", {}).get("production_promotion") is not False
        ))
    ):
        raise SystemExit("refusing C23 registration: evidence incomplete")

    linux_replication = {
        "status": "pending_exact_external_upload_approval",
        "manifest": "docs/recognition/c23_linux_confirmation/c23_linux_upload_manifest.json",
        "file_count": 52,
        "source_bytes": 903745,
        "local_package_validation": "pass",
        "pod_created": False,
        "files_uploaded": 0,
    }
    machine_status = "fresh_same_machine_exact_table_verified_linux_replication_pending"
    linux_interpretation = "The unchanged Linux package is locally validated but not uploaded."
    if failed_attempt is not None:
        linux_replication.update({
            "status": "attempt_1_create_http_500_horizon_reconciled",
            "create_requests": 1,
            "creation_http_status": 500,
            "automatic_replacement_queued": False,
            "estimated_compute_cost_usd": None,
            "owned_pod_absent_verified": True,
            "final_inventories": {"v1": [], "v2": []},
            "scientific_replication_complete": False,
            "retry_requires_new_exact_authorization": True,
            "failure_verification": str(FAILED_ATTEMPT.relative_to(ROOT)).replace("\\", "/"),
        })
        machine_status = "fresh_same_machine_exact_table_verified_linux_create_failed_reconciled"
        linux_interpretation = (
            "The first exact Linux create request returned HTTP 500 before a pod or upload; the "
            "watchdog reconciled empty inventories, and another create needs new exact authorization."
        )
    if linux_final is not None:
        linux_replication.update({
            "status": "retry_002c_scientifically_verified",
            "create_requests": 1,
            "pod_created": True,
            "files_uploaded": 52,
            "scientific_replication_complete": True,
            "automatic_replacement_queued": False,
            "estimated_compute_cost_usd": linux_final["estimated_compute_cost_usd"],
            "owned_pod_absent_verified": True,
            "final_inventories": {"v1": [], "v2": []},
            "controller_status": linux_final["controller_status"],
            "controller_gate_adjudication": linux_final["controller_gate_adjudication"],
            "final_verification": str(LINUX_FINAL.relative_to(ROOT)).replace("\\", "/"),
            "cross_machine_comparison": str(CROSS_MACHINE.relative_to(ROOT)).replace("\\", "/"),
            "linux_best_fixed_method": linux_final["summary"]["best_fixed_method"],
            "linux_oracle_headroom_over_best_fixed":
                linux_final["summary"]["oracle_headroom_over_best_fixed"],
            "retry_requires_new_exact_authorization": False,
        })
        machine_status = "fresh_and_second_machine_exact_table_verified"
        linux_interpretation = (
            "The unchanged Linux retry completed exactly and was independently adjudicated after "
            "the controller incorrectly required vendored dd in installed-package metadata. "
            "Compiled screened CM led on Linux, and all owned resources were removed."
        )

    machine = {
        "schema": "crse-learning-milestone-c23-fresh-yosys-gf2-table-summary/v1",
        "date": "2026-08-31",
        "status": machine_status,
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "dataset": result["dataset"],
        "methods": list(summary["methods"]),
        "measurement_rows": result["measurement_rows"],
        "memory_measurement_rows": result["memory_measurement_rows"],
        "summary": summary,
        "verification": {
            "path": str((RUN / "independent_verification.json").relative_to(ROOT)).replace(
                "\\", "/"),
            **verification,
        },
        "dataset_verification": {
            "path": "docs/recognition/c23_yosys_fresh_gf2_dataset_v2_verification.json",
            **dataset_verification,
        },
        "linux_replication": linux_replication,
        "semantic_or_artifact_mismatches": 0,
        "fresh_confirmation": True,
        "production_promotion": False,
        "interpretation": (
            f"On 48 fresh Yosys-family functions, all unchanged C21 methods delivered the same "
            f"exhaustive-best artifact. Packed source ANF led at "
            f"{packed['aggregate_speedup_over_exhaustive']:.3f}x over exhaustive and "
            f"{packed['aggregate_speedup_over_screened']:.3f}x over screened; screened CM reached "
            f"{screened['aggregate_speedup_over_exhaustive']:.3f}x over exhaustive. The timing "
            f"oracle has only {summary['oracle_headroom_over_best_fixed']:.3f}x headroom before "
            f"router cost. {linux_interpretation}"
        ),
    }
    write(DOCS / MACHINE, machine)

    data = load(REGISTER)
    if (
        [row["id"] for row in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
        or len(data.get("applications", [])) != 8
    ):
        raise SystemExit("refusing C23 update: 18-track or 8-application shape changed")
    tracks = {row["id"]: row for row in data["tracks"]}
    scope = (
        "C23 transferred the unchanged seven-method exact GF(2) table to 48 previously unused "
        "Yosys generator-family functions. Packed source ANF led at 3.306x over exhaustive, "
        "screened CM reached 3.286x, all artifacts matched, and oracle routing headroom was 1.047x."
    )
    if linux_final is not None:
        scope = (
            "C23 exactly transferred the unchanged seven-method GF(2) table across Windows and "
            "Linux. Screened CM reached 3.286x and 3.337x over exhaustive; the narrow winner changed "
            "from packed source ANF to compiled screened CM, and Linux oracle headroom was 1.005x."
        )
    for track_id in ("R01", "R06", "R07", "R11", "R13", "R16", "R17", "R18"):
        upsert(tracks[track_id], scope)
        tracks[track_id]["status"] = "measured"
        tracks[track_id]["status_reason"] = scope
    tracks["R01"]["next_experiment"] = (
        "Measure the C22 exact dispatcher boundary end to end on the sealed C23 cases."
    )
    tracks["R06"]["next_experiment"] = (
        "Treat the close packed/compiled ordering as machine-specific and require controls on each target."
    )
    tracks["R07"]["next_experiment"] = (
        "Keep fresh BDD as a negative control; evaluate resident BDD only for repeated-query contracts."
    )
    tracks["R11"]["next_experiment"] = (
        "Exercise packed source ANF through the C22 advice-off, fallback, and shadow boundary."
    )
    tracks["R13"]["next_experiment"] = (
        "Do not train another router unless independent data shows materially more than 1.047x oracle headroom."
    )
    tracks["R16"]["next_experiment"] = (
        "Charge C22 dispatch, refusal, fallback, shadow execution, exact replay, and wrapper costs on C23."
    )
    tracks["R17"]["next_experiment"] = (
        "Add unsupported support widths and malformed source metadata as exact C22 refusal controls."
    )
    tracks["R18"]["next_experiment"] = (
        "Retain exhaustive, screened, compiled-screened, fresh BDD, and abstaining proposal controls."
    )
    hardware = next(
        item for item in data["applications"] if item["name"] == "Hardware verification/design")
    upsert(hardware, scope)
    data["milestones"]["F"] = (
        "C23 verifies fresh and second-machine transfer of the unchanged exact GF(2) table: screened "
        "CM is stably above 3.28x exhaustive, close fixed-arm ranking is machine-specific, and "
        "production remains disabled"
    )
    data["updated"] = "2026-08-31"
    write(REGISTER, data)
    print(json.dumps({
        "tracks": len(data["tracks"]),
        "applications": len(data["applications"]),
        "updated_tracks": ["R01", "R06", "R07", "R11", "R13", "R16", "R17", "R18"],
        "milestone": "C23/F3",
        "fresh_confirmation": True,
        "linux_replication": linux_replication["status"],
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
