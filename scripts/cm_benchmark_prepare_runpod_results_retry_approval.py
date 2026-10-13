"""Prepare a non-authorizing request to retry creation of the fourth results Pod."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
OUT = BASE / "results-retry-approval-request-001"
REQUEST = OUT / "RUNPOD_RESULTS_RETRY_APPROVAL_REQUEST.json"
FAILED_CREATE = BASE / "runpod-results-001/RUN.json"
READINESS = BASE / "account-readiness-004/ACCOUNT_READINESS.json"
RECONCILIATION = BASE / "campaign-reconciliation-002/RUNPOD_RECONCILIATION.json"
FILES = {
    "upload_manifest": BASE / "prelaunch-008/UPLOAD_MANIFEST.json",
    "final_reconciliation": RECONCILIATION,
    "first_results_authorization": BASE / "results-authorization-001/RUNPOD_RESULTS_AUTHORIZATION.json",
    "failed_create_record": FAILED_CREATE,
    "post_failure_readiness": READINESS,
    "bootstrap": ROOT / "scripts/cm_benchmark_runpod_bootstrap_v2.py",
    "results_remote_worker": ROOT / "scripts/cm_benchmark_runpod_remote_v4.py",
    "core_screen_runner": ROOT / "scripts/cm_benchmark_core_screen.py",
    "core_screen_plan": BASE / "core-screen-freeze-001/PLAN.json",
    "results_controller": ROOT / "scripts/cm_benchmark_runpod_results_controller_v2.py",
}
MANIFEST_SHA256 = "f12864a3d072062526ea298aaa1c14ec8a6cb972314de7e9762bf21ba1277e72"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main():
    failed = load(FAILED_CREATE)
    readiness = load(READINESS)
    reconciliation = load(RECONCILIATION)
    manifest = load(FILES["upload_manifest"])
    selected = readiness.get("selected_proposal") or {}
    if (OUT.exists() or digest(FILES["upload_manifest"]) != MANIFEST_SHA256
            or len(manifest.get("bundles", [])) != 11
            or failed.get("status") != "failed" or failed.get("creation_http_status") != 500
            or failed.get("pod_created") is not False or failed.get("uploaded_shards") != 0
            or failed.get("cleanup", {}).get("owned_pod_absent") is not True
            or readiness.get("transport", {}).get("resource_writes") != 0
            or readiness.get("inventory", {}).get("v1", {}).get("pod_count") != 0
            or readiness.get("inventory", {}).get("v2", {}).get("pod_count") != 0
            or selected.get("id") != "cpu3g" or selected.get("requested_vcpu") != 16
            or float(selected.get("ram_gb", 0)) < 64
            or float(selected.get("secure_usd_per_hour", 99)) > .64
            or reconciliation.get("totals", {}).get("pods_created") != 3):
        raise RuntimeError("results retry preconditions are not exact and clean")
    approval = (
        "I authorize exactly one retry of the RunPod creation request for the still-uncreated fourth and final results "
        "Pod for campaign cm-mega-prelaunch-20260914-008 using the exact hashes in this request. The first results-Pod "
        "creation request returned HTTP 500, created no Pod, uploaded no controls or shards, incurred no estimated Pod "
        "charge, and was followed by a delayed zero-Pod inventory check. This retry does not authorize a replacement "
        "Pod, a fifth Pod, more than four total campaign Pods, or any further creation attempt if this retry fails. The "
        "successor transport may send only the same hash-bound core-screen runner and frozen plan through token-gated, "
        "SHA-256-checked control endpoints after creation, and may upload only the same exact 11 frozen shards with "
        "upload-manifest file SHA-256 f12864a3d072062526ea298aaa1c14ec8a6cb972314de7e9762bf21ba1277e72. "
        "All prior limits remain: one concurrent Pod; Secure cpu3g, 16 vCPU and at least 64 GB RAM; two hours and $1.35 "
        "additional charges for this phase; 16 total Pod-hours and $50 cumulative RunPod charges; bounded 192-cell "
        "execution and result retrieval; owned-Pod deletion and reconciliation; and no production change, commit, push, "
        "publication, unrelated-resource mutation, credential upload, automatic replacement, or other upload."
    )
    document = {
        "schema": "cm-benchmark-runpod-results-retry-approval-request/v1",
        "created_utc": now(),
        "campaign_id": "cm-mega-prelaunch-20260914-008",
        "status": "exact_approval_pending",
        "authorization_granted": False,
        "approval_text_to_repeat": approval,
        "reason": "RunPod returned HTTP 500 before creating a Pod; the oversized create payload was reduced by moving the already-approved control files to authenticated uploads",
        "transport_correction": {
            "failed_create_payload_bytes": 84313,
            "successor_create_payload_bytes": 15618,
            "failed_create_command_chars": 81273,
            "successor_create_command_chars": 12245,
            "control_files": ["core-screen runner", "frozen plan"],
            "control_authentication": "ephemeral bearer token",
            "control_identity": "declared length and SHA-256",
        },
        "bound_sha256": {name: digest(path) for name, path in FILES.items()},
        "live_quote": {
            "checked_utc": readiness["checked_utc"],
            "availability": selected["availability"],
            "cpu_flavor": "cpu3g",
            "vcpu": 16,
            "ram_gb": selected["ram_gb"],
            "secure_usd_per_hour": selected["secure_usd_per_hour"],
        },
        "maximum_creation_retries_after_http_500": 1,
        "maximum_additional_pods": 1,
        "maximum_total_campaign_pods": 4,
        "maximum_concurrent_pods": 1,
        "maximum_phase_pod_hours": 2,
        "maximum_phase_runpod_charges_usd": 1.35,
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
        "# Results-Pod creation retry approval\n\nStatus: exact approval pending.\n\n> " + approval
        + "\n\nRequest SHA-256: `" + digest(REQUEST) + "`\n", encoding="utf-8")
    print(json.dumps({"authorization_granted": False, "request_sha256": digest(REQUEST),
                      "manifest_sha256": digest(FILES["upload_manifest"])}, sort_keys=True))


if __name__ == "__main__":
    main()
