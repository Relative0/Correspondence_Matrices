"""Record the user's exact CM benchmark RunPod authorization locally."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign/approval-request-001/RUNPOD_PAID_LAUNCH_APPROVAL_REQUEST.json"
OUT = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign/authorization-001/RUNPOD_AUTHORIZATION.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    document = {
        "schema": "cm-benchmark-runpod-authorization/v1",
        "authorized": True,
        "recorded_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "explicit user message in current Codex task",
        "exact_authorized_text": request["approval_text_to_repeat"],
        "approval_request_sha256": sha256(REQUEST),
        "upload_manifest_file_sha256": request["frozen_artifacts"]["upload_manifest"]["file_sha256"],
        "campaign_id": request["campaign_id"],
        "maximum_total_pod_hours": 16,
        "maximum_total_runpod_charges_usd": 50,
        "maximum_concurrent_pods": 1,
        "maximum_total_pods": 2,
        "automatic_replacement": False,
        "production_changes": False,
        "commit": False,
        "push": False,
        "publication": False,
        "credential_upload": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=False)
    OUT.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"authorized": True, "authorization_sha256": sha256(OUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
