"""Freeze the one-pod C12 retry authorization artifacts."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c12_linux_confirmation"
MANIFEST = HERE / "c12_linux_upload_manifest.json"
PROTOCOL = HERE / "C12_SECOND_MACHINE_TIMING_RETRY_PROTOCOL_2026_08_30.md"
AUTHORIZATION = HERE / "RUNPOD_C12_LINUX_RETRY_AUTHORIZED_2026_08_30.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("file_count") != 14 or manifest.get("bytes") != 355934:
        raise SystemExit("changed C12 upload package")
    PROTOCOL.write_text("""# C12 second-machine same-pod retry protocol

Reuse the unchanged frozen 14-file, 355,934-byte C12 package. Create one Secure
Runpod CPU pod and no replacement pod. Require two successful health observations
before upload. If `POST /payload` returns proxy HTTP 404, retry that idempotent
request at most five times on the same owned pod, rechecking health between
attempts. All other upload errors fail closed.

Use the pinned Python 3.13.15 image, 2 vCPU, at least 4 GB RAM, 12 GB ephemeral
disk, no pod or network volume, one HTTPS port, a $0.25/hour rate ceiling, and a
controller-enforced $0.05 total ceiling. Retrieve at most 16 MiB, delete the pod
within ten minutes, and reconcile for twelve minutes. No training or production
write is permitted.
""", encoding="utf-8")
    authorization = {"schema": "crse-runpod-c12-linux-retry-authorization/v1",
        "authorized": True,
        "authorization_basis": "User re-authorized up to USD 5 as before on 2026-08-30 after the safely reconciled first attempt",
        "user_total_ceiling_usd": 5.0, "controller_total_ceiling_usd": 0.05,
        "one_create": True, "no_replacement": True, "source_files": 14,
        "source_bytes": 355934, "cases": 40, "repetitions": 16, "methods": 4,
        "https_ports": ["8080/http"], "vcpu_count": 2, "minimum_ram_gb": 4,
        "container_disk_gb": 12, "pod_volume_gb": 0, "network_volume": False,
        "cleanup_seconds": 600, "reconciliation_seconds": 720,
        "rate_cap_usd_per_hour": 0.25, "total_cost_cap_usd": 0.05,
        "same_pod_payload_attempt_limit": 6, "health_checks_before_upload": 2,
        "prior_authorization_consumed": True,
        "proposal_sha256": sha(PROTOCOL), "upload_manifest_sha256": sha(MANIFEST),
        "recorded_utc": datetime.now(timezone.utc).isoformat()}
    AUTHORIZATION.write_bytes(json.dumps(authorization, indent=2,
        sort_keys=True).encode() + b"\n")
    print(json.dumps({"protocol_sha256": sha(PROTOCOL),
        "authorization_sha256": sha(AUTHORIZATION),
        "manifest_sha256": sha(MANIFEST)}, sort_keys=True))


if __name__ == "__main__":
    main()
