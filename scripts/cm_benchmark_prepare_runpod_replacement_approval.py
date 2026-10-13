"""Create the exact non-authorizing request for one primary replacement Pod."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
OUT = BASE / "replacement-approval-request-001"
REQUEST = OUT / "RUNPOD_PRIMARY_REPLACEMENT_APPROVAL_REQUEST.json"
README = OUT / "APPROVAL_REQUEST.md"
FILES = {
    "original_authorization": BASE / "authorization-001/RUNPOD_AUTHORIZATION.json",
    "upload_manifest": BASE / "prelaunch-008/UPLOAD_MANIFEST.json",
    "prior_run": BASE / "runpod-primary-001/RUN.json",
    "controller": ROOT / "scripts/cm_benchmark_runpod_controller.py",
    "bootstrap": ROOT / "scripts/cm_benchmark_runpod_bootstrap.py",
    "remote_worker": ROOT / "scripts/cm_benchmark_runpod_remote.py",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    prior = json.loads(FILES["prior_run"].read_text(encoding="utf-8"))
    if (prior.get("status") != "failed" or prior.get("uploaded_shards") != 0
            or prior.get("cleanup", {}).get("owned_pod_absent") is not True):
        raise RuntimeError("prior attempt is not a safely reconciled zero-upload failure")
    text = (
        "I authorize one replacement primary RunPod Pod for campaign "
        "cm-mega-prelaunch-20260914-008 using the hardened controller identified in this request. "
        "This is the second and final Pod permitted by the existing campaign authorization; no further "
        "replacement is authorized. All original upload, resource, 16 total Pod-hour, $50 cumulative-charge, "
        "one-concurrent-Pod, ownership, retrieval, cleanup, credential, and excluded-effect limits remain unchanged."
    )
    document = {
        "schema": "cm-benchmark-runpod-primary-replacement-approval-request/v1",
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "exact_approval_pending",
        "authorization_granted": False,
        "approval_text_to_repeat": text,
        "reason": "first primary Pod encountered transient proxy HTTP 404 before any shard upload",
        "prior_attempt": {"uploaded_shards": 0, "owned_pod_absent": True,
                          "estimated_compute_cost_usd": prior.get("estimated_compute_cost_usd")},
        "hardening": {"two_consecutive_health_checks": True, "same_pod_shard_404_retries": 6,
                      "digest_mismatch_retry": False},
        "bound_sha256": {name: digest(path) for name, path in FILES.items()},
        "maximum_additional_pods": 1,
        "maximum_total_campaign_pods": 2,
        "automatic_or_further_replacement": False,
        "original_limits_unchanged": True,
    }
    OUT.mkdir(parents=True, exist_ok=False)
    REQUEST.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    README.write_text("# Primary replacement approval request\n\nStatus: exact approval pending.\n\n> " + text +
                      "\n\nRequest SHA-256: `" + digest(REQUEST) + "`\n", encoding="utf-8")
    print(json.dumps({"authorization_granted": False, "request_sha256": digest(REQUEST)}, sort_keys=True))


if __name__ == "__main__":
    main()
