"""Prepare a non-authorizing request for one corrected environment recovery Pod."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
CORRECTION = BASE / "dependency-correction-001"
OUT = BASE / "recovery-approval-request-001"
REQUEST = OUT / "RUNPOD_ENVIRONMENT_RECOVERY_APPROVAL_REQUEST.json"
WHEEL = CORRECTION / "python_sat-1.8.dev21-cp313-cp313-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl"
FILES = {
    "upload_manifest": BASE / "prelaunch-008/UPLOAD_MANIFEST.json",
    "original_authorization": BASE / "authorization-001/RUNPOD_AUTHORIZATION.json",
    "replacement_authorization": BASE / "replacement-authorization-001/RUNPOD_PRIMARY_REPLACEMENT_AUTHORIZATION.json",
    "attempt_001": BASE / "runpod-primary-001/RUN.json",
    "attempt_002": BASE / "runpod-primary-002/RUN.json",
    "reconciliation": BASE / "campaign-reconciliation-001/RUNPOD_RECONCILIATION.json",
    "controller": ROOT / "scripts/cm_benchmark_runpod_controller.py",
    "bootstrap": ROOT / "scripts/cm_benchmark_runpod_bootstrap.py",
    "corrected_remote_worker": ROOT / "scripts/cm_benchmark_runpod_remote.py",
    "admitted_linux_wheel": WHEEL,
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    correction = {
        "schema": "cm-benchmark-linux-dependency-correction/v1",
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "failed_pin": "python-sat==1.8.dev20",
        "failure": "no matching PyPI distribution for Linux CPython 3.13",
        "successor_pin": "python-sat==1.8.dev21",
        "wheel": {"filename": WHEEL.name, "bytes": WHEEL.stat().st_size, "sha256": digest(WHEEL),
                  "platform": "manylinux_2_24_x86_64.manylinux_2_28_x86_64", "abi": "cp313",
                  "source": "official PyPI release file"},
        "remote_download": {"exact_size_and_sha256_required_before_install": True},
        "benchmark_measurements_seen_before_correction": 0,
        "outcome_responsive_method_change": False,
        "cloud_launch_authorized": False,
    }
    (CORRECTION / "DEPENDENCY_CORRECTION.json").write_text(json.dumps(correction, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    approval = (
        "I authorize one additional and final RunPod environment-recovery Pod for campaign "
        "cm-mega-prelaunch-20260914-008 using the corrected Python-SAT pin and the exact hashes in this request. "
        "This expands the campaign maximum from two to three total serial Pods but keeps one concurrent Pod, the "
        "original 16 total Pod-hour and $50 cumulative-charge ceilings, the exact 11-shard upload scope, and all "
        "ownership, retrieval, cleanup, credential, and excluded-effect limits unchanged. No replacement after this Pod is authorized."
    )
    document = {
        "schema": "cm-benchmark-runpod-environment-recovery-approval-request/v1",
        "created_utc": correction["created_utc"], "status": "exact_approval_pending",
        "authorization_granted": False, "approval_text_to_repeat": approval,
        "reason": "second Pod stopped before measurements because the frozen Linux dependency pin was unavailable",
        "correction": correction,
        "bound_sha256": {name: digest(path) for name, path in FILES.items()},
        "maximum_additional_pods": 1, "maximum_total_campaign_pods": 3,
        "maximum_concurrent_pods": 1, "maximum_total_pod_hours": 16,
        "maximum_total_runpod_charges_usd": 50, "further_replacement": False,
    }
    OUT.mkdir(parents=True, exist_ok=False)
    REQUEST.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "APPROVAL_REQUEST.md").write_text(
        "# Environment-recovery Pod approval request\n\nStatus: exact approval pending.\n\n> " + approval +
        "\n\nRequest SHA-256: `" + digest(REQUEST) + "`\n", encoding="utf-8")
    print(json.dumps({"authorization_granted": False, "request_sha256": digest(REQUEST),
                      "wheel_sha256": digest(WHEEL)}, sort_keys=True))


if __name__ == "__main__":
    main()
