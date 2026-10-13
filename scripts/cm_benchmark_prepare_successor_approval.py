"""Prepare the exact, non-authorizing RunPod successor launch request."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cm_benchmark_runpod_successor_controller import (  # noqa: E402
    BASE,
    CAMPAIGN,
    CORRECTED_REPLAY,
    CORE_PLAN,
    MANIFEST,
    PHASE_COST_CAP,
    PHASE_HOURS,
    PRELAUNCH,
    PRIOR_RECONCILIATION,
    READINESS,
    REQUEST,
    bound_hashes,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    if REQUEST.exists():
        raise RuntimeError("successor approval request already exists")
    manifest = load(MANIFEST)
    readiness = load(READINESS)
    plan = load(CORE_PLAN)
    reconciliation = load(PRIOR_RECONCILIATION)
    replay = load(CORRECTED_REPLAY)
    selected = readiness.get("selected_proposal") or {}
    if (
        digest(MANIFEST)
        != "580b08ec86385ebca01ed3e763def78e4c68c1c98d216a21b07a307f4061fcee"
        or manifest.get("campaign_id") != CAMPAIGN
        or manifest.get("authorization_granted") is not False
        or len(manifest.get("bundles", [])) != 1
        or len(manifest.get("controls", [])) != 2
        or plan.get("campaign_id") != CAMPAIGN
        or len(plan.get("cells", [])) != 108
        or readiness.get("campaign_id") != CAMPAIGN
        or readiness.get("transport", {}).get("resource_writes") != 0
        or readiness.get("inventory", {}).get("v1", {}).get("pod_count") != 0
        or readiness.get("inventory", {}).get("v2", {}).get("pod_count") != 0
        or selected.get("id") != "cpu3g"
        or selected.get("availability") not in {"LOW", "MEDIUM", "HIGH"}
        or selected.get("requested_vcpu") != 16
        or float(selected.get("ram_gb", 0)) < 64
        or float(selected.get("secure_usd_per_hour", 99)) > 0.64
        or reconciliation.get("inventories", {}).get("v1_pod_count") != 0
        or reconciliation.get("inventories", {}).get("v2_pod_count") != 0
        or replay.get("status") != "passed"
        or replay.get("summary", {}).get("core_screen", {}).get("cells") != 108
        or replay.get("summary", {}).get("core_screen", {}).get("correctness_mismatches")
        or replay.get("summary", {}).get("core_screen", {}).get("status_counts", {}).get("worker_error", 0)
        or replay.get("summary", {}).get("core_screen", {}).get("status_counts", {}).get("error", 0)
    ):
        raise RuntimeError("successor approval preconditions are not frozen and clean")

    manifest_sha = digest(MANIFEST)
    runner = next(row for row in manifest["controls"] if row["id"] == "runner")
    plan_control = next(row for row in manifest["controls"] if row["id"] == "plan")
    approval = (
        "I authorize exactly one RunPod Pod for successor campaign "
        "cm-mega-successor-20260914-009 using the exact hashes in this request. "
        "The Pod must be a Secure CPU Pod using cpu3g with 16 vCPU and at least "
        "64 GB RAM, with at most one concurrent Pod and no replacement, automatic "
        "replacement, or further creation attempt if creation fails. This successor "
        "phase is limited to two Pod-hours and $1.35 in RunPod charges, stopping on "
        "whichever cap binds first, and the combined original and successor campaigns "
        "remain below 16 total Pod-hours and $50 cumulative RunPod charges. I authorize "
        "upload only of the single frozen successor shard listed in upload-manifest "
        f"file SHA-256 {manifest_sha}, plus transmission only of the hash-bound 108-cell "
        "successor runner and plan in this request; execution of the paired exact-count "
        "and closed-biology screen; bounded result retrieval; and deletion and "
        "reconciliation of the campaign-owned Pod. No production change, commit, push, "
        "publication, unrelated-resource mutation, credential upload, or other upload "
        "is authorized."
    )
    rate = float(selected["secure_usd_per_hour"])
    projected = rate * PHASE_HOURS + 30 * 0.1 * (PHASE_HOURS / 720)
    prior = reconciliation["totals"]
    document = {
        "schema": "cm-benchmark-runpod-successor-approval-request/v1",
        "created_utc": now(),
        "campaign_id": CAMPAIGN,
        "status": "exact_approval_pending",
        "authorization_granted": False,
        "approval_text_to_repeat": approval,
        "bound_sha256": bound_hashes(),
        "live_quote": {
            "readiness_file_sha256": digest(READINESS),
            "checked_utc": readiness["checked_utc"],
            "cpu_flavor": "cpu3g",
            "availability": selected["availability"],
            "available_data_centers": selected["available_data_centers"],
            "vcpu": 16,
            "ram_gb": selected["ram_gb"],
            "secure_usd_per_hour": rate,
            "projected_two_hour_compute_and_prorated_container_disk_usd": projected,
            "phase_charge_cap_usd": PHASE_COST_CAP,
            "catalog_snapshot_only_not_placement_guarantee": True,
        },
        "upload": {
            "manifest_file_sha256": manifest_sha,
            "bundles": manifest["bundles"],
            "controls": [runner, plan_control],
            "other_uploads_permitted": False,
        },
        "screen": {
            "plan_file_sha256": digest(CORE_PLAN),
            "plan_internal_sha256": plan["plan_sha256"],
            "cases": len(plan["cases"]),
            "cells": len(plan["cells"]),
            "repetitions": plan["repetitions"],
            "per_cell_seconds": plan["cell_seconds"],
            "stop_admission_seconds": plan["campaign_seconds"],
            "lanes": ["biology_fixed_points", "exact_count"],
        },
        "local_linux_replay": {
            "replay_file_sha256": digest(CORRECTED_REPLAY),
            "status_counts": replay["summary"]["core_screen"]["status_counts"],
            "correctness_mismatches": replay["summary"]["core_screen"]["correctness_mismatches"],
            "evidence_zip_sha256": replay["evidence_zip_sha256"],
        },
        "prior_campaign": {
            "campaign_id": "cm-mega-prelaunch-20260914-008",
            "pods_created": prior["pods_created"],
            "estimated_pod_hours": prior["estimated_total_pod_hours"],
            "estimated_compute_cost_usd": prior["estimated_compute_cost_usd"],
            "all_owned_pods_absent": True,
        },
        "maximum_total_pods": 1,
        "maximum_concurrent_pods": 1,
        "maximum_phase_pod_hours": PHASE_HOURS,
        "maximum_phase_runpod_charges_usd": PHASE_COST_CAP,
        "maximum_combined_pod_hours": 16,
        "maximum_combined_runpod_charges_usd": 50,
        "maximum_result_archive_bytes": 256 << 20,
        "automatic_replacement": False,
        "further_creation_after_failure": False,
        "production_changes": False,
        "commit": False,
        "push": False,
        "publication": False,
        "credential_upload": False,
        "unrelated_resource_mutation": False,
    }
    REQUEST.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (PRELAUNCH / "APPROVAL_REQUEST.md").write_text(
        "# Focused successor RunPod approval request\n\n"
        "Status: exact approval pending.\n\n> "
        + approval
        + "\n\nRequest SHA-256: `"
        + digest(REQUEST)
        + "`\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "authorization_granted": False,
                "request_sha256": digest(REQUEST),
                "upload_manifest_sha256": manifest_sha,
                "bundle_sha256": manifest["bundles"][0]["sha256"],
                "runner_sha256": runner["sha256"],
                "plan_sha256": plan_control["sha256"],
                "projected_two_hour_usd": projected,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
