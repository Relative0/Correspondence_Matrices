"""Record the user's exact one-Pod replacement authorization locally."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
REQUEST = BASE / "replacement-approval-request-001/RUNPOD_PRIMARY_REPLACEMENT_APPROVAL_REQUEST.json"
OUT = BASE / "replacement-authorization-001/RUNPOD_PRIMARY_REPLACEMENT_AUTHORIZATION.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    document = {
        "schema": "cm-benchmark-runpod-primary-replacement-authorization/v1",
        "authorized": True,
        "recorded_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "explicit user message in current Codex task",
        "exact_authorized_text": request["approval_text_to_repeat"],
        "request_sha256": digest(REQUEST),
        "bound_sha256": request["bound_sha256"],
        "maximum_additional_pods": 1,
        "maximum_total_campaign_pods": 2,
        "automatic_or_further_replacement": False,
        "original_limits_unchanged": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=False)
    OUT.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"authorized": True, "authorization_sha256": digest(OUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
