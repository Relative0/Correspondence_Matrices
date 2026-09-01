"""Seal the C27 retry-002 HTTP-500 create reconciliation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c27_linux_confirmation"
ATTEMPT = HERE / "runpod-c27-linux-execute-001e"
AUTHORIZATION = HERE / "RUNPOD_C27_RETRY_002_EXACT_PAYLOAD_AUTHORIZED_2026_09_01.json"
REQUEST = HERE / "RUNPOD_C27_RETRY_002_AUTHORIZATION_REQUEST_20260901.json"
MANIFEST = HERE / "c27_linux_upload_manifest.json"
OUTPUT = HERE / "RUNPOD_C27_RETRY_002_HTTP500_RECONCILIATION_20260901.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(inventories: dict) -> dict[str, list[list[str]]]:
    return {
        version: [list(item) for item in sorted({
            (row.get("id"), row.get("name"))
            for row in inventories.get(version, [])})]
        for version in ("v1", "v2")
    }


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 retry-002 reconciliation")
    run = load(ATTEMPT / "RUN.json")
    state = load(ATTEMPT / "controller-state.json")
    freeze = load(ATTEMPT / "TRANSPORT-FREEZE.json")
    watchdog = load(ATTEMPT / "WATCHDOG-RESULT.json")
    inventory_rows = rows(ATTEMPT / "watchdog-inventory.jsonl")
    controller_release = load(
        ATTEMPT / "HOST-AWAKE-RELEASED-c27-http-controller.json")
    watchdog_release = load(
        ATTEMPT / "HOST-AWAKE-RELEASED-c27-http-watchdog.json")
    authorization = load(AUTHORIZATION)
    request = load(REQUEST)
    expected = {
        "v1": [["vqos7wif838oxx", "cm-video-first5-production-v1-a1-339b3cfb0d"]],
        "v2": [["vqos7wif838oxx", "cm-video-first5-production-v1-a1-339b3cfb0d"]],
    }
    final_inventory = normalized(watchdog.get("final", {}).get("inventories", {}))
    if (
        authorization.get("authorized") is not True
        or authorization.get("retry_attempt") != 2
        or authorization.get("additional_create_requests") != 1
        or authorization.get("one_create") is not True
        or authorization.get("no_replacement") is not True
        or authorization.get("authorization_request_sha256") != sha256(REQUEST)
        or request.get("requested_additional_create_requests") != 1
        or run.get("status") != "failed"
        or run.get("creation_attempted") is not True
        or run.get("creation_uncertain") is not True
        or run.get("creation_http_status") != 500
        or run.get("pod_created") is not False
        or run.get("uploaded_source_files") != 0
        or run.get("automatic_replacement_queued") is not False
        or run.get("error") != "C27 pod creation failed HTTP 500"
        or run.get("name") != state.get("name")
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or run.get("unrelated_baseline_preserved_or_completed") is not True
        or freeze.get("authorization_sha256") != sha256(AUTHORIZATION)
        or freeze.get("manifest_sha256") != sha256(MANIFEST)
        or freeze.get("source_files") != 63
        or freeze.get("source_bytes") != 1078671
        or not inventory_rows
        or any(row.get("owned_ids") != [] for row in inventory_rows)
        or inventory_rows[-1].get("after_horizon") is not True
        or watchdog.get("status") != "horizon_reconciled"
        or watchdog.get("errors") != []
        or watchdog.get("final", {}).get("owned_pod_absent") is not True
        or final_inventory != expected
        or controller_release.get("released") is not True
        or watchdog_release.get("released") is not True
    ):
        raise ValueError("C27 retry-002 HTTP-500 reconciliation mismatch")
    result = {
        "schema": "crse-runpod-c27-retry-002-http500-reconciliation/v1",
        "status": "verified_reconciled",
        "retry_attempt": 2,
        "create_requests": 1,
        "create_http_status": 500,
        "create_response_uncertain": True,
        "authorization_consumed": True,
        "replacement_authorized": False,
        "pod_ever_observed": False,
        "pod_created": False,
        "source_files_uploaded": 0,
        "automatic_replacement_queued": False,
        "watchdog_inventory_checks": len(inventory_rows),
        "post_horizon_inventory_checked": True,
        "owned_pod_absent": True,
        "final_inventory": final_inventory,
        "unrelated_pod_preserved": True,
        "estimated_compute_cost_usd": 0.0,
        "billing_may_lag": True,
        "scientific_replication_complete": False,
        "failure": "runpod_create_http_500_no_pod_observed_through_horizon",
        "run_sha256": sha256(ATTEMPT / "RUN.json"),
        "watchdog_result_sha256": sha256(ATTEMPT / "WATCHDOG-RESULT.json"),
        "watchdog_inventory_sha256": sha256(ATTEMPT / "watchdog-inventory.jsonl"),
        "authorization_sha256": sha256(AUTHORIZATION),
        "authorization_request_sha256": sha256(REQUEST),
        "manifest_sha256": sha256(MANIFEST),
        "credentials_recorded_or_uploaded": False,
        "training": False,
        "production_write": False,
    }
    OUTPUT.write_bytes(json.dumps(
        result, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
