"""Register independently verified C9-C12 exact-dispatcher results."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/adaptive-exact-dispatcher-robust-20260830-002"
VERIFY = DOCS / "verification/adaptive-exact-dispatcher-robust-20260830-002.json"
RUNPOD_VERIFY = DOCS / "c12_linux_confirmation/RUNPOD_C12_LINUX_ATTEMPT_FINAL_VERIFICATION_20260830.json"
RUNPOD_RETRY_VERIFY = DOCS / "c12_linux_confirmation/RUNPOD_C12_LINUX_RETRY_FINAL_VERIFICATION_20260830.json"
PACKAGE_V2_VALIDATION = DOCS / "c12_linux_confirmation/C12_PACKAGE_V2_LOCAL_VALIDATION_20260830.json"
RUNPOD_PACKAGE_V2_VERIFY = DOCS / "c12_linux_confirmation/RUNPOD_C12_LINUX_PACKAGE_V2_FINAL_VERIFICATION_20260830.json"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C12_ADAPTIVE_EXACT_DISPATCHER_2026_08_30.md"
MACHINE = "learning_milestone_c12_adaptive_dispatcher_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


UPDATES = {
    "R01": ("The frozen robust dispatcher remained exact. C12 measured 0.968x/0.925x locally and 0.988x/0.969x on Linux; the second-machine 5% gate passed, but profitability remains platform-sensitive.",
            "Develop a near-zero-overhead tail sentinel or task-level tail-latency gate, then freeze before another source holdout."),
    "R03": ("Exact source partitions remained stable through set, packed, bitset, restart, and in-place representation changes on fresh Yosys-derived functions.",
            "Extend exact representation conversion to repeated subgraphs only where the task contract benefits from compact partitions."),
    "R06": ("Two new balanced 40-case source sets preserved exact independent-component partitions with zero overlap against prior source cases.",
            "Add a genuinely new raw source family before making broader decomposition-transfer claims."),
    "R16": ("In-place conversion removed duplicate DAG-prefix work. The Linux replay passed the 5% C12 no-regret gate, while the original Windows B split remained outside it.",
            "Move the tail sentinel into the base set kernel and separately time diagnostic instrumentation."),
    "R17": ("The frozen policies remained exact and leakage-safe. Linux passed the second-machine promotion gate, but cross-machine profitability variation still requires guarded enablement.",
            "Calibrate task-level abstention using only pre-execution workload requirements and development data."),
    "R18": ("Fixed set, cached packed, direct bitset, guarded restart, and one-pass paths exposed catastrophic-tail savings, sparse overhead, and measurable platform sensitivity.",
            "Retain sparse no-switch cases and dense tail cases in every future dispatcher confirmation."),
}


def main():
    summary, verification, runpod = load(RUN / "summary.json"), load(VERIFY), load(RUNPOD_VERIFY)
    runpod_retry, package_v2 = load(RUNPOD_RETRY_VERIFY), load(PACKAGE_V2_VALIDATION)
    runpod_v2 = load(RUNPOD_PACKAGE_V2_VERIFY)
    if (summary.get("status") != "complete" or summary.get("semantic_mismatches") != 0
            or summary.get("criteria", {}).get("exact") is not True
            or summary.get("criteria", {}).get("production_promotion") is not False
            or verification.get("status") != "pass" or verification.get("semantic_rows_replayed") != 940
            or verification.get("timing_samples_checked") != 14100
            or verification.get("semantic_mismatches") != 0
            or runpod.get("status") != "safe_failure_reconciled"
            or runpod.get("complete") is not True
            or runpod.get("scientific_confirmation_complete") is not False
            or runpod.get("owned_pod_absent_verified") is not True
            or runpod.get("uploaded_source_files") != 0
            or runpod_retry.get("status") != "safe_workload_failure_reconciled"
            or runpod_retry.get("complete") is not True
            or runpod_retry.get("scientific_confirmation_complete") is not False
            or runpod_retry.get("owned_pod_absent_verified") is not True
            or runpod_retry.get("uploaded_source_files") != 14
            or package_v2.get("status") != "pass" or package_v2.get("initial_file_count") != 16
            or package_v2.get("measurement_rows") != 2560
            or package_v2.get("semantic_mismatches") != 0
            or runpod_v2.get("status") != "pass" or runpod_v2.get("complete") is not True
            or runpod_v2.get("scientific_confirmation_complete") is not True
            or runpod_v2.get("second_machine_promotion") is not True
            or runpod_v2.get("create_requests_this_authorization") != 1
            or runpod_v2.get("automatic_replacement_queued") is not False
            or runpod_v2.get("uploaded_source_files") != 16
            or runpod_v2.get("measurement_rows") != 2560
            or runpod_v2.get("semantic_mismatches") != 0
            or runpod_v2.get("owned_pod_absent_verified") is not True
            or runpod_v2.get("final_inventories") != {"v1": [], "v2": []}):
        raise SystemExit("refusing C12 registration: evidence is incomplete")
    machine = {"schema": "crse-learning-milestone-c12-adaptive-dispatcher-summary/v1",
        "date": "2026-08-30", "status": "complete", "production_promotion": False,
        "report": REPORT, "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "verification": {"path": str(VERIFY.relative_to(ROOT)).replace("\\", "/"), **verification},
        "policy": summary["policy"], "c12_audit": summary["c12_audit"],
        "split_summary": summary["split_summary"], "criteria": summary["criteria"],
        "semantic_mismatches": 0,
        "prior_runs": ["docs/recognition/runs/exact-representation-dispatcher-20260830-002",
                       "docs/recognition/runs/staged-exact-dispatcher-20260830-001",
                       "docs/recognition/runs/adaptive-exact-dispatcher-20260830-001"],
        "runpod": {"status": "second_machine_confirmation_complete",
            "pod_created": True, "upload_performed": True,
            "scientific_confirmation_complete": True,
            "second_machine_promotion": True,
            "criteria": runpod_v2["criteria"],
            "split_summary": runpod_v2["split_summary"],
            "attempts": [{"verification": str(RUNPOD_VERIFY.relative_to(ROOT)).replace("\\", "/"),
                          "uploaded_files": 0, "cost_usd": runpod["estimated_compute_cost_usd"]},
                         {"verification": str(RUNPOD_RETRY_VERIFY.relative_to(ROOT)).replace("\\", "/"),
                          "uploaded_files": 14, "cost_usd": runpod_retry["estimated_compute_cost_usd"]},
                         {"verification": str(RUNPOD_PACKAGE_V2_VERIFY.relative_to(ROOT)).replace("\\", "/"),
                          "uploaded_files": 16, "cost_usd": runpod_v2["estimated_compute_cost_usd"]}],
            "owned_pod_absent_verified": True,
            "combined_cost_usd": runpod_v2["combined_c12_cloud_cost_usd"],
            "corrected_manifest": "docs/recognition/c12_linux_confirmation/c12_linux_upload_manifest_v2.json",
            "corrected_package_local_validation": str(PACKAGE_V2_VALIDATION.relative_to(ROOT)).replace("\\", "/"),
            "corrected_controller": "docs/recognition/c12_linux_confirmation/runpod_c12_linux_controller_v6.py",
            "authorization_record_present": True},
        "interpretation": "The Linux second-machine gate passed with exact results and less than 5% regret on both C12 splits. The original Windows B split remained outside the band, so use guarded opt-in or task-level enablement rather than an unconditional default."}
    (DOCS / MACHINE).write_bytes(json.dumps(machine, indent=2, sort_keys=True,
        allow_nan=False).encode("utf-8") + b"\n")

    data = load(REGISTER)
    if ([track["id"] for track in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing update: register no longer has R01-R18 and eight applications")
    by_id = {track["id"]: track for track in data["tracks"]}
    for track_id, (reason, next_experiment) in UPDATES.items():
        track = by_id[track_id]
        track["status"] = "measured"
        track["status_reason"] = reason
        track["next_experiment"] = next_experiment
        result = {"report": REPORT, "machine_summary": MACHINE, "scope": reason}
        existing = [row for row in track["results"] if row.get("report") == REPORT]
        if len(existing) > 1:
            raise SystemExit(f"duplicate C12 registration for {track_id}")
        if existing:
            existing[0].update(result)
        else:
            track["results"].append(result)
    hardware = next(item for item in data["applications"] if item["name"] == "Hardware verification/design")
    result = {"report": REPORT, "machine_summary": MACHINE,
        "scope": "Exact adaptive source-ANF routing controlled dense tails and passed the Linux second-machine 5% gate; the Windows/Linux difference keeps production enablement guarded."}
    existing = [row for row in hardware["results"] if row.get("report") == REPORT]
    if len(existing) > 1:
        raise SystemExit("duplicate C12 hardware registration")
    if existing:
        existing[0].update(result)
    else:
        hardware["results"].append(result)
    data["milestones"]["C"] = (
        "C12 robust one-pass exact dispatcher complete; exact and tail-safe, Linux second-machine gate passed, cross-machine profitability remains sensitive and unconditional promotion stays disabled"
    )
    data["updated"] = "2026-08-30"
    REGISTER.write_bytes(json.dumps(data, indent=2, ensure_ascii=False,
        allow_nan=False).encode("utf-8") + b"\n")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
        "updated_tracks": sorted(UPDATES), "semantic_mismatches": 0,
        "production_promotion": False, "second_machine_promotion": True,
        "runpod_pod_created": True, "runpod_uploaded_files": 16,
        "runpod_owned_pod_absent": True,
        "corrected_package_local_validation": "pass"}, sort_keys=True))


if __name__ == "__main__":
    main()
