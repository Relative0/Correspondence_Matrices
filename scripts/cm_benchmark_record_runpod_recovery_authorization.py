"""Record the user's exact one-Pod environment-recovery authorization locally."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
REQUEST = BASE / "recovery-approval-request-001/RUNPOD_ENVIRONMENT_RECOVERY_APPROVAL_REQUEST.json"
OUT = BASE / "recovery-authorization-001/RUNPOD_ENVIRONMENT_RECOVERY_AUTHORIZATION.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    document = {
        "schema": "cm-benchmark-runpod-environment-recovery-authorization/v1",
        "authorized": True,
        "recorded_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "explicit user message in current Codex task",
        "exact_authorized_text": request["approval_text_to_repeat"],
        "request_sha256": digest(REQUEST),
        "bound_sha256": request["bound_sha256"],
        "maximum_additional_pods": 1,
        "maximum_total_campaign_pods": 3,
        "maximum_concurrent_pods": 1,
        "maximum_total_pod_hours": 16,
        "maximum_total_runpod_charges_usd": 50,
        "further_replacement": False,
        "original_limits_unchanged_except_total_campaign_pods": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=False)
    OUT.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"authorized": True, "authorization_sha256": digest(OUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
