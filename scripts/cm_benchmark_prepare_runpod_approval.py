"""Create the exact, non-authorizing RunPod approval request for the CM campaign."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRELAUNCH = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign/prelaunch-008"
READINESS = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign/account-readiness-002/RUNPOD_ACCOUNT_READINESS.json"
OUT_DIR = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign/approval-request-001"
REQUEST = OUT_DIR / "RUNPOD_PAID_LAUNCH_APPROVAL_REQUEST.json"
README = OUT_DIR / "APPROVAL_REQUEST.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_request() -> dict[str, Any]:
    manifest = load(PRELAUNCH / "UPLOAD_MANIFEST.json")
    readiness = load(READINESS)
    selected = readiness.get("selected_proposal") or {}
    if manifest.get("upload_authorized") is not False:
        raise ValueError("frozen manifest must remain non-authorizing")
    if not readiness.get("readiness", {}).get("account_checks_pass"):
        raise ValueError("account readiness must pass for the selected quote")
    if not selected or selected.get("eligible") is not True:
        raise ValueError("a qualifying account-visible CPU offer is required")
    manifest_file_sha = sha256(PRELAUNCH / "UPLOAD_MANIFEST.json")
    approval_text = (
        "I authorize upload of only the 11 frozen shards in the CM benchmark upload manifest "
        f"with file SHA-256 {manifest_file_sha}, and the paid RunPod campaign "
        f"{manifest['campaign_id']}: Secure CPU Pods using cpu3g, 16 vCPU and at least 64 GB RAM, "
        "at most one concurrent Pod and at most two serial campaign-owned Pods, no automatic "
        "replacement, no more than 16 total Pod-hours and $50 total RunPod charges, stopping on "
        "whichever cap binds first. I authorize only benchmark upload, execution, bounded result "
        "retrieval, and deletion/reconciliation of Pods created for this campaign; no production "
        "changes, commit, push, publication, unrelated-resource mutation, or credential upload."
    )
    return {
        "schema": "cm-benchmark-runpod-paid-launch-approval-request/v1",
        "campaign_id": manifest["campaign_id"],
        "created_utc": utc_now(),
        "status": "exact_approval_pending",
        "authorization_granted": False,
        "approval_text_to_repeat": approval_text,
        "requested_effect": (
            "Upload the exact frozen shards, create and supervise the bounded two-stage serial "
            "RunPod campaign, retrieve bounded results, and terminate/reconcile only owned Pods."
        ),
        "frozen_artifacts": {
            "upload_manifest": {"path": str((PRELAUNCH / "UPLOAD_MANIFEST.json").relative_to(ROOT)),
                                "file_sha256": manifest_file_sha,
                                "canonical_manifest_sha256": manifest["manifest_sha256"]},
            "arm_manifest_sha256": sha256(PRELAUNCH / "ARM_MANIFEST.json"),
            "schedule_ledger_sha256": sha256(PRELAUNCH / "SCHEDULE_LEDGER.json"),
            "environment_lock_sha256": sha256(PRELAUNCH / "ENVIRONMENT_LOCK.json"),
            "local_verification_sha256": sha256(PRELAUNCH / "LOCAL_VERIFICATION.json"),
            "linux_smoke_sha256": sha256(ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign/linux-smoke-002/LINUX_SMOKE.json"),
            "account_readiness_sha256": sha256(READINESS),
        },
        "upload": {
            "authorized": False,
            "bundle_count": len(manifest["bundles"]),
            "compressed_bytes": sum(row["bytes"] for row in manifest["bundles"]),
            "expanded_bytes": sum(row["expanded_bytes"] for row in manifest["bundles"]),
            "bundles": [{"path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"]}
                        for row in manifest["bundles"]],
            "credential_files_excluded": True,
        },
        "resource_request": {
            "cloud_type": "SECURE",
            "compute_type": "CPU",
            "cpu_flavor": selected["id"],
            "vcpu_count": selected["requested_vcpu"],
            "minimum_usable_ram_gb": selected["ram_gb"],
            "maximum_rate_usd_per_hour": 0.64,
            "live_rate_usd_per_hour": selected["secure_usd_per_hour"],
            "container_disk_gb": 30,
            "pod_volume_gb": 0,
            "network_volume": False,
            "maximum_concurrent_pods": 1,
            "maximum_total_pods": 2,
            "automatic_replacement": False,
            "name_prefix": manifest["campaign_id"] + "-",
        },
        "envelope": {
            "maximum_total_pod_hours": 16,
            "maximum_total_runpod_charges_usd": 50,
            "stop_on_first_binding_cap": True,
            "quoted_compute_usd": selected["compute_usd"],
            "quoted_storage_usd": selected["storage_usd_prorated"],
            "quoted_total_usd": selected["quoted_total_usd"],
            "stages_max_hours": {
                "environment_and_probe": 2,
                "broad_screen": 4,
                "confirmation_and_large_widths": 6,
                "second_host_replication": 3,
                "retrieval_and_cleanup_reserve": 1,
            },
        },
        "runtime_safeguards": {
            "source_input_limit_mib": 16,
            "normal_cell": {"memory_gib": 4, "seconds": 60, "output_mib": 64},
            "admitted_large_cell": {"memory_gib": 48, "seconds": 300, "output_mib": 512},
            "absolute_exploratory_cell_seconds": 900,
            "aggregate_retrieval_limit_gib": 8,
            "checkpoint_each_completed_cell": True,
            "stop_admission_before_hard_boundary": True,
        },
        "ownership_and_cleanup": {
            "record_created_pod_ids_immediately": True,
            "mutate_or_delete_only_recorded_campaign_owned_ids": True,
            "release_primary_before_second_host": True,
            "verify_local_result_hashes_before_ephemeral_termination": True,
            "reconcile_v1_and_v2_inventories": True,
            "touch_unrelated_resources": False,
        },
        "network": {"setup_and_transfer_only": True, "workload_network": False},
        "credential_handling": {
            "local_reference_names": ["RUNPOD_API_KEY", "RP_TOKEN"],
            "record_values": False,
            "upload_values": False,
        },
        "excluded_effects": {
            "production_changes": False,
            "deployment": False,
            "publication": False,
            "commit": False,
            "push": False,
        },
    }


def write_new(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=False)
    document = build_request()
    write_new(REQUEST, json.dumps(document, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
    md = (
        "# RunPod paid-launch approval request\n\n"
        "Status: exact approval pending. This file does not grant authorization.\n\n"
        "## Exact approval text\n\n"
        f"> {document['approval_text_to_repeat']}\n\n"
        f"Request JSON SHA-256: `{sha256(REQUEST)}`\n\n"
        "No upload, resource creation, paid execution, or external write was performed while preparing this request.\n"
    )
    write_new(README, md.encode("utf-8"))
    print(json.dumps({
        "authorization_granted": False,
        "request": str(REQUEST.relative_to(ROOT)),
        "request_sha256": sha256(REQUEST),
        "manifest_file_sha256": document["frozen_artifacts"]["upload_manifest"]["file_sha256"],
        "bundle_count": document["upload"]["bundle_count"],
        "quoted_total_usd": document["envelope"]["quoted_total_usd"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
