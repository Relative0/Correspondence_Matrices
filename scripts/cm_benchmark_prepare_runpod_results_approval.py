"""Prepare the exact, non-authorizing request for one bounded results Pod."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
OUT = BASE / "results-approval-request-001"
REQUEST = OUT / "RUNPOD_RESULTS_APPROVAL_REQUEST.json"
READINESS = BASE / "account-readiness-003/ACCOUNT_READINESS.json"
RECONCILIATION = BASE / "campaign-reconciliation-002/RUNPOD_RECONCILIATION.json"
FILES = {
    "upload_manifest": BASE / "prelaunch-008/UPLOAD_MANIFEST.json",
    "final_reconciliation": RECONCILIATION,
    "bootstrap": ROOT / "scripts/cm_benchmark_runpod_bootstrap.py",
    "results_remote_worker": ROOT / "scripts/cm_benchmark_runpod_remote_v3.py",
    "core_screen_runner": ROOT / "scripts/cm_benchmark_core_screen.py",
    "core_screen_plan": BASE / "core-screen-freeze-001/PLAN.json",
    "results_controller": ROOT / "scripts/cm_benchmark_runpod_results_controller.py",
}
MANIFEST_SHA256 = "f12864a3d072062526ea298aaa1c14ec8a6cb972314de7e9762bf21ba1277e72"
PHASE_HOURS = 2.0
PHASE_COST_CAP = 1.35


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main():
    readiness = load(READINESS)
    reconciliation = load(RECONCILIATION)
    manifest = load(FILES["upload_manifest"])
    plan = load(FILES["core_screen_plan"])
    selected = readiness.get("selected_proposal") or {}
    if (OUT.exists() or digest(FILES["upload_manifest"]) != MANIFEST_SHA256
            or len(manifest.get("bundles", [])) != 11
            or readiness.get("operation") != "credentialed_read_only_preflight"
            or readiness.get("transport", {}).get("resource_writes") != 0
            or readiness.get("inventory", {}).get("v1", {}).get("pod_count") != 0
            or readiness.get("inventory", {}).get("v2", {}).get("pod_count") != 0
            or selected.get("id") != "cpu3g" or selected.get("requested_vcpu") != 16
            or float(selected.get("ram_gb", 0)) < 64
            or float(selected.get("secure_usd_per_hour", 99)) > .64
            or reconciliation.get("totals", {}).get("pods_created") != 3
            or reconciliation.get("authorization_exhausted") is not True
            or reconciliation.get("further_create_authorized") is not False
            or plan.get("campaign_id") != "cm-mega-prelaunch-20260914-008"
            or len(plan.get("cells", [])) != 192):
        raise RuntimeError("results approval preconditions are not frozen and clean")

    approval = (
        "I authorize one additional and final RunPod results Pod for campaign "
        "cm-mega-prelaunch-20260914-008 using the exact hashes in this request. This explicitly expands the "
        "campaign maximum from three to four total serial Pods, overriding only the earlier three-Pod/no-further-Pod "
        "limit, while keeping one concurrent Pod, the original 16 total Pod-hour and $50 cumulative-charge ceilings, "
        "Secure CPU Pods using cpu3g with 16 vCPU and at least 64 GB RAM, and all ownership, credential, retrieval, "
        "cleanup, and excluded-effect limits unchanged. This Pod is limited to two hours and $1.35 in additional "
        "RunPod charges, stopping on whichever cap binds first. I authorize upload of only the same exact 11 frozen "
        "shards with upload-manifest file SHA-256 f12864a3d072062526ea298aaa1c14ec8a6cb972314de7e9762bf21ba1277e72, "
        "plus transmission of only the hash-bound core-screen runner and frozen plan in this request; execution of "
        "the bounded 192-cell counting, biology, and affine results screen; bounded result retrieval; and deletion and "
        "reconciliation of the campaign-owned Pod. No automatic replacement, fifth Pod, production change, commit, "
        "push, publication, unrelated-resource mutation, credential upload, or other upload is authorized."
    )
    rate = float(selected["secure_usd_per_hour"])
    phase_quote = rate * PHASE_HOURS + 30 * .1 * (PHASE_HOURS / 720)
    prior_hours = float(reconciliation["totals"]["estimated_total_pod_hours"])
    prior_cost = float(reconciliation["totals"]["estimated_compute_cost_usd"])
    document = {
        "schema": "cm-benchmark-runpod-results-approval-request/v1",
        "created_utc": now(),
        "campaign_id": "cm-mega-prelaunch-20260914-008",
        "status": "exact_approval_pending",
        "authorization_granted": False,
        "approval_text_to_repeat": approval,
        "bound_sha256": {name: digest(path) for name, path in FILES.items()},
        "live_quote": {
            "readiness_file_sha256": digest(READINESS),
            "checked_utc": readiness["checked_utc"],
            "cpu_flavor": "cpu3g",
            "availability": selected["availability"],
            "vcpu": 16,
            "ram_gb": selected["ram_gb"],
            "secure_usd_per_hour": rate,
            "projected_two_hour_compute_and_prorated_container_disk_usd": phase_quote,
            "phase_charge_cap_usd": PHASE_COST_CAP,
            "catalog_snapshot_only_not_placement_guarantee": True,
        },
        "screen": {
            "plan_file_sha256": digest(FILES["core_screen_plan"]),
            "plan_internal_sha256": plan["plan_sha256"],
            "cases": len(plan["cases"]),
            "cells": len(plan["cells"]),
            "repetitions": plan["repetitions"],
            "per_cell_seconds": plan["cell_seconds"],
            "stop_admission_seconds": plan["campaign_seconds"],
        },
        "prior_campaign": {
            "pods_created": 3,
            "estimated_pod_hours": prior_hours,
            "estimated_compute_cost_usd": prior_cost,
            "all_owned_pods_absent": True,
        },
        "maximum_additional_pods": 1,
        "maximum_total_campaign_pods": 4,
        "maximum_concurrent_pods": 1,
        "maximum_phase_pod_hours": PHASE_HOURS,
        "maximum_phase_runpod_charges_usd": PHASE_COST_CAP,
        "maximum_total_pod_hours": 16,
        "maximum_total_runpod_charges_usd": 50,
        "maximum_result_archive_bytes": 256 << 20,
        "further_replacement": False,
        "production_changes": False,
        "commit": False,
        "push": False,
        "publication": False,
        "credential_upload": False,
    }
    OUT.mkdir(parents=True, exist_ok=False)
    REQUEST.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "APPROVAL_REQUEST.md").write_text(
        "# Bounded results Pod approval request\n\nStatus: exact approval pending.\n\n> " + approval
        + "\n\nRequest SHA-256: `" + digest(REQUEST) + "`\n", encoding="utf-8")
    print(json.dumps({
        "authorization_granted": False,
        "request_sha256": digest(REQUEST),
        "manifest_sha256": digest(FILES["upload_manifest"]),
        "plan_sha256": digest(FILES["core_screen_plan"]),
        "phase_quote_usd": phase_quote,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
