"""Record an exact user authorization for the frozen successor request."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRELAUNCH = (
    ROOT
    / "docs/audits/2026-09-13-cm-benchmark-campaign/successor-prelaunch-002"
)
REQUEST = PRELAUNCH / "RUNPOD_APPROVAL_REQUEST.json"
AUTHORIZATION = PRELAUNCH / "RUNPOD_AUTHORIZATION.json"
CAMPAIGN = "cm-mega-successor-20260914-009"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(request_path: Path, out_path: Path, expected_request_sha256: str) -> dict:
    actual = digest(request_path)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if (
        actual != expected_request_sha256
        or request.get("campaign_id") != CAMPAIGN
        or request.get("status") != "exact_approval_pending"
        or request.get("authorization_granted") is not False
        or request.get("maximum_total_pods") != 1
        or request.get("maximum_concurrent_pods") != 1
        or request.get("maximum_phase_pod_hours") != 2.0
        or request.get("maximum_phase_runpod_charges_usd") != 1.35
        or request.get("automatic_replacement") is not False
        or request.get("further_creation_after_failure") is not False
    ):
        raise RuntimeError("successor approval request identity or bounds mismatch")
    document = {
        "schema": "cm-benchmark-runpod-successor-authorization/v1",
        "authorized": True,
        "recorded_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "explicit user message in current Codex task",
        "campaign_id": CAMPAIGN,
        "exact_authorized_text": request["approval_text_to_repeat"],
        "request_sha256": actual,
        "bound_sha256": request["bound_sha256"],
        "maximum_total_pods": 1,
        "maximum_concurrent_pods": 1,
        "maximum_phase_pod_hours": 2.0,
        "maximum_phase_runpod_charges_usd": 1.35,
        "maximum_combined_pod_hours": 16,
        "maximum_combined_runpod_charges_usd": 50,
        "maximum_result_archive_bytes": 256 << 20,
        "automatic_replacement": False,
        "further_creation_after_failure": False,
        "production_changes": False,
        "commit": False,
        "push": False,
        "publication": False,
        "credential_upload": False,
        "unrelated_resource_mutation": False,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(document, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-sha256", required=True)
    args = parser.parse_args()
    record(REQUEST, AUTHORIZATION, args.request_sha256)
    print(
        json.dumps(
            {
                "authorized": True,
                "authorization_sha256": digest(AUTHORIZATION),
                "request_sha256": digest(REQUEST),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
