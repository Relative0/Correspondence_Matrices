"""Record the user's exact authorization for one fourth-Pod creation retry."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
REQUEST = BASE / "results-retry-approval-request-001/RUNPOD_RESULTS_RETRY_APPROVAL_REQUEST.json"
OUT = BASE / "results-retry-authorization-001/RUNPOD_RESULTS_RETRY_AUTHORIZATION.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    document = {
        "schema": "cm-benchmark-runpod-results-retry-authorization/v1",
        "authorized": True,
        "recorded_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "explicit user message in current Codex task",
        "campaign_id": request["campaign_id"],
        "exact_authorized_text": request["approval_text_to_repeat"],
        "request_sha256": digest(REQUEST),
        "bound_sha256": request["bound_sha256"],
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
    OUT.parent.mkdir(parents=True, exist_ok=False)
    OUT.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"authorized": True, "authorization_sha256": digest(OUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
