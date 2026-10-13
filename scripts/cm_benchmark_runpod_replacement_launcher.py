"""One-time launcher enforcing the exact hardened replacement authorization."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
REQUEST = BASE / "replacement-approval-request-001/RUNPOD_PRIMARY_REPLACEMENT_APPROVAL_REQUEST.json"
AUTHORIZATION = BASE / "replacement-authorization-001/RUNPOD_PRIMARY_REPLACEMENT_AUTHORIZATION.json"
OUT = BASE / "runpod-primary-002"
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


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    request, authorization, prior = load(REQUEST), load(AUTHORIZATION), load(FILES["prior_run"])
    current = {name: digest(path) for name, path in FILES.items()}
    if (OUT.exists() or authorization.get("authorized") is not True
            or authorization.get("request_sha256") != digest(REQUEST)
            or authorization.get("exact_authorized_text") != request.get("approval_text_to_repeat")
            or authorization.get("bound_sha256") != current or request.get("bound_sha256") != current
            or authorization.get("maximum_additional_pods") != 1
            or authorization.get("maximum_total_campaign_pods") != 2
            or authorization.get("automatic_or_further_replacement") is not False
            or prior.get("status") != "failed" or prior.get("uploaded_shards") != 0
            or prior.get("cleanup", {}).get("owned_pod_absent") is not True):
        raise RuntimeError("replacement authorization, hashes, output, or prior cleanup mismatch")
    command = [sys.executable, str(FILES["controller"]), "run", "--output", str(OUT)]
    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
