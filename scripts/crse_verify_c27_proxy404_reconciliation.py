"""Independently reconcile the one-create C27 RunPod proxy-404 attempt."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c27_linux_confirmation"
CONTROLLER = HERE / "runpod_c27_linux_controller.py"
ATTEMPT = HERE / "runpod-c27-linux-execute-001d"
AUTHORIZATION = HERE / "RUNPOD_C27_EXACT_PAYLOAD_AUTHORIZED_2026_08_31.json"
MANIFEST = HERE / "c27_linux_upload_manifest.json"
OUTPUT = HERE / "RUNPOD_C27_PROXY_404_RECONCILIATION_20260901.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 proxy-404 reconciliation")
    spec = importlib.util.spec_from_file_location("c27_reconcile", CONTROLLER)
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    authorization = load(AUTHORIZATION)
    manifest = load(MANIFEST)
    run = load(ATTEMPT / "RUN.json")
    freeze = load(ATTEMPT / "TRANSPORT-FREEZE.json")
    released_controller = load(
        ATTEMPT / "HOST-AWAKE-RELEASED-c27-http-controller.json")
    released_watchdog = load(
        ATTEMPT / "HOST-AWAKE-RELEASED-c27-http-watchdog.json")
    watchdog = load(ATTEMPT / "WATCHDOG-RESULT.json")
    current = controller.preflight.check()
    inventories = current.get("inventories", {})
    normalized = controller.normalized_inventory(inventories)
    owned_id = run.get("pod_id")
    owned_name = run.get("name")
    owned_present = any(
        pod_id == owned_id or name == owned_name
        for rows in normalized.values() for pod_id, name in rows)
    resources = run.get("actual_resources", {})
    if (
        authorization.get("authorized") is not True
        or authorization.get("one_create") is not True
        or authorization.get("no_replacement") is not True
        or run.get("status") != "failed"
        or run.get("creation_attempted") is not True
        or run.get("creation_uncertain") is not False
        or run.get("creation_http_status") != 201
        or run.get("pod_created") is not True
        or run.get("uploaded_source_files") != 0
        or run.get("automatic_replacement_queued") is not False
        or run.get("error") != "proxy HTTP 404"
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or run.get("unrelated_baseline_preserved_or_completed") is not True
        or resources.get("rate_usd_per_hour") != 0.06
        or resources.get("vcpu_count") != 2
        or resources.get("ram_gb") != 4.0
        or resources.get("container_disk_gb") != 12
        or resources.get("pod_volume_gb") != 0
        or resources.get("image") != manifest["runtime"]["image"]
        or resources.get("cloud_evidence") != ["SECURE"]
        or float(run.get("estimated_compute_cost_usd", 1)) > 0.05
        or freeze.get("source_files") != 63
        or freeze.get("source_bytes") != 1078671
        or freeze.get("manifest_sha256") != sha256(MANIFEST)
        or released_controller.get("released") is not True
        or released_watchdog.get("released") is not True
        or watchdog.get("status") != "controller_cleanup_verified"
        or watchdog.get("errors") != []
        or owned_present
        or not controller.allowed_baseline(inventories)
        or current.get("resource_writes") != 0
        or current.get("credential_values_recorded") is not False
    ):
        raise ValueError("C27 proxy-404 reconciliation mismatch")
    result = {
        "schema": "crse-runpod-c27-proxy-404-reconciliation/v1",
        "status": "verified_reconciled",
        "create_requests": 1,
        "authorization_consumed": True,
        "replacement_authorized": False,
        "new_exact_create_authorization_required": True,
        "pod_id": owned_id,
        "pod_name": owned_name,
        "creation_http_status": 201,
        "resource_contract_passed": True,
        "source_files_uploaded": 0,
        "payload_attempts_recorded": "payload_attempts" in run,
        "failure": "transient_proxy_http_404_before_payload_acceptance",
        "owned_pod_absent": True,
        "cleanup_seconds_from_create": run["elapsed_since_create_s"],
        "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "controller_cost_ceiling_usd": 0.05,
        "unrelated_pod_preserved": True,
        "current_inventory": normalized,
        "run_sha256": sha256(ATTEMPT / "RUN.json"),
        "transport_freeze_sha256": sha256(ATTEMPT / "TRANSPORT-FREEZE.json"),
        "authorization_sha256": sha256(AUTHORIZATION),
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
