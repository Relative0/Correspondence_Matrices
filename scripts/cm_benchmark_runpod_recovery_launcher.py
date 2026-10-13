"""One-time launcher enforcing the exact environment-recovery authorization."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
REQUEST = BASE / "recovery-approval-request-001/RUNPOD_ENVIRONMENT_RECOVERY_APPROVAL_REQUEST.json"
AUTHORIZATION = BASE / "recovery-authorization-001/RUNPOD_ENVIRONMENT_RECOVERY_AUTHORIZATION.json"
OUT = BASE / "runpod-primary-003"
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
    "admitted_linux_wheel": BASE / "dependency-correction-001/python_sat-1.8.dev21-cp313-cp313-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    request = load(REQUEST)
    authorization = load(AUTHORIZATION)
    attempt_001 = load(FILES["attempt_001"])
    attempt_002 = load(FILES["attempt_002"])
    reconciliation = load(FILES["reconciliation"])
    current = {name: digest(path) for name, path in FILES.items()}
    inventories = reconciliation.get("inventories", {})
    if (
        OUT.exists()
        or authorization.get("authorized") is not True
        or authorization.get("request_sha256") != digest(REQUEST)
        or authorization.get("exact_authorized_text") != request.get("approval_text_to_repeat")
        or authorization.get("bound_sha256") != current
        or request.get("bound_sha256") != current
        or authorization.get("maximum_additional_pods") != 1
        or authorization.get("maximum_total_campaign_pods") != 3
        or authorization.get("maximum_concurrent_pods") != 1
        or authorization.get("maximum_total_pod_hours") != 16
        or authorization.get("maximum_total_runpod_charges_usd") != 50
        or authorization.get("further_replacement") is not False
        or attempt_001.get("status") != "failed"
        or attempt_001.get("cleanup", {}).get("owned_pod_absent") is not True
        or attempt_002.get("status") != "failed"
        or attempt_002.get("uploaded_shards") != 11
        or attempt_002.get("cleanup", {}).get("owned_pod_absent") is not True
        or attempt_002.get("evidence") is not None
        or inventories.get("v1_pod_count") != 0
        or inventories.get("v2_pod_count") != 0
        or reconciliation.get("totals", {}).get("pods_created") != 2
    ):
        raise RuntimeError("recovery authorization, hashes, output, prior attempts, or cleanup mismatch")
    command = [sys.executable, str(FILES["controller"]), "run", "--output", str(OUT)]
    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
