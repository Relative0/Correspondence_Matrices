"""Execute one bounded, exactly authorized query-ladder retry 002 on RunPod."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_CONTROLLER_PATH = ROOT / "scripts/runpod_architecture_query_ladder_controller.py"
spec = importlib.util.spec_from_file_location("query_ladder_attempt_001_transport", BASE_CONTROLLER_PATH)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
shared = controller.shared
base = controller.base

HERE = ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
OUT = HERE / "runpod-architecture-query-ladder-execute-002"
MANIFEST = HERE / "UPLOAD_MANIFEST.json"
AUTHORIZATION = HERE / "RUNPOD_ARCHITECTURE_QUERY_LADDER_RETRY_002_EXACT_PAYLOAD_AUTHORIZED_2026_09_04.json"
PROTOCOL = HERE / "PROTOCOL.md"
CONTRACT = HERE / "EXECUTION_CONTRACT.json"
LOCAL_VALIDATION = HERE / "LOCAL_PACKAGE_VALIDATION.json"
REQUEST = HERE / "RUNPOD_RETRY_002_AUTHORIZATION_REQUEST_20260904.json"
FREEZE = ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_freeze_20260904/FREEZE.json"
RUN_NAME = "architecture-query-ladder-linux-gcc-20260904-002"
TOTAL_COST_CAP_USD = 0.04
PRIOR_ESTIMATED_COST_USD = 0.008934310547510782
CUMULATIVE_HARD_CEILING_USD = 0.05


RETRY_STAGE = (
    controller.QUERY_LADDER_STAGE
    .replace("architecture-query-ladder-linux-gcc-20260903-001", RUN_NAME)
    .replace(
        "docs/recognition/architecture_query_ladder_followup_freeze_20260903/FREEZE.json",
        FREEZE.relative_to(ROOT).as_posix(),
    )
)
base.REMOTE_CODE = shared.replace_remote_once(
    base.REMOTE_CODE, controller.QUERY_LADDER_STAGE, RETRY_STAGE,
)
RETRY_VALIDATION = controller.QUERY_LADDER_VALIDATION.replace(
    "architecture-query-ladder-linux-gcc-20260903-001", RUN_NAME,
)
base.REMOTE_CODE = shared.replace_remote_once(
    base.REMOTE_CODE, controller.QUERY_LADDER_VALIDATION, RETRY_VALIDATION,
)

BASE_TRANSPORT_SOURCES = controller.transport_source_identities()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def transport_source_identities() -> dict[str, dict[str, int | str]]:
    rows = dict(BASE_TRANSPORT_SOURCES)
    path = Path(__file__).resolve()
    rows[path.relative_to(ROOT).as_posix()] = {
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }
    return dict(sorted(rows.items()))


def require_authorization() -> dict:
    authorization = _load(AUTHORIZATION)
    manifest = _load(MANIFEST)
    validation = _load(LOCAL_VALIDATION)
    request = _load(REQUEST)
    expected = {
        "schema": "cm-runpod-architecture-query-ladder-retry-002-exact-payload-authorization/v1",
        "authorized": True,
        "user_total_ceiling_usd": TOTAL_COST_CAP_USD,
        "controller_total_ceiling_usd": TOTAL_COST_CAP_USD,
        "cumulative_hard_ceiling_usd": CUMULATIVE_HARD_CEILING_USD,
        "prior_attempt_estimated_cost_usd": PRIOR_ESTIMATED_COST_USD,
        "one_create": True,
        "no_replacement": True,
        "source_files": manifest["file_count"],
        "source_bytes": manifest["bytes"],
        "planned_rows": 27_648,
        "query_rows": {"1": 6_912, "4": 6_912, "16": 6_912, "64": 6_912},
        "https_ports": ["8080/http"],
        "vcpu_count": 2,
        "minimum_ram_gb": 4,
        "container_disk_gb": 12,
        "pod_volume_gb": 0,
        "network_volume": False,
        "cleanup_seconds": 600,
        "reconciliation_seconds": 720,
        "rate_cap_usd_per_hour": 0.25,
        "total_cost_cap_usd": TOTAL_COST_CAP_USD,
        "same_pod_payload_attempt_limit": 6,
        "health_checks_before_upload": 2,
        "result_cap_bytes": 48 << 20,
        "compiler": "cc",
        "image": controller.IMAGE,
        "local_isolated_validation": "pass",
        "local_validation_pythonpath_injected": False,
        "isolated_memory_method": "isolated_fork_child_wait4_ru_maxrss/v1",
        "isolated_cleanup_method": "cache_clear_then_isolated_child_exit",
        "credentials_recorded_or_uploaded": False,
        "prior_authorization_reused": False,
        "training": False,
        "selector_fit": False,
        "website_update": False,
        "production_write": False,
    }
    if any(authorization.get(key) != value for key, value in expected.items()):
        raise RuntimeError("query-ladder retry 002 authorization scope mismatch")
    hashes = {
        "upload_manifest_sha256": _sha256(MANIFEST),
        "protocol_sha256": _sha256(PROTOCOL),
        "execution_contract_sha256": _sha256(CONTRACT),
        "local_validation_sha256": _sha256(LOCAL_VALIDATION),
        "freeze_sha256": _sha256(FREEZE),
        "authorization_request_sha256": _sha256(REQUEST),
        "controller_sha256": _sha256(Path(__file__)),
    }
    if (
        any(authorization.get(key) != value for key, value in hashes.items())
        or authorization.get("transport_sources") != transport_source_identities()
        or any(request.get(key) != value for key, value in hashes.items() if key != "authorization_request_sha256")
        or request.get("transport_sources") != transport_source_identities()
        or validation.get("status") != "pass"
        or validation.get("manifest_sha256") != _sha256(MANIFEST)
        or validation.get("pythonpath_injected") is not False
        or validation.get("parent_and_followup_freeze_verification_passed") is not True
        or validation.get("timing_evidence_produced") is not False
        or validation.get("memory_evidence_produced") is not False
        or validation.get("decision_bearing_result_produced") is not False
    ):
        raise RuntimeError("query-ladder retry 002 authorization artifact mismatch")
    return authorization


controller.OUT = OUT
controller.MANIFEST = MANIFEST
controller.AUTHORIZATION = AUTHORIZATION
controller.PROTOCOL = PROTOCOL
controller.CONTRACT = CONTRACT
controller.LOCAL_VALIDATION = LOCAL_VALIDATION
controller.REQUEST = REQUEST
controller.FREEZE = FREEZE
controller.RUN_NAME = RUN_NAME
controller.shared.CAMPAIGN_CAP = TOTAL_COST_CAP_USD
controller.transport_source_identities = transport_source_identities
controller.require_authorization = require_authorization
controller.__file__ = str(Path(__file__).resolve())
controller.configure_transport()


def main() -> int:
    return controller.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}), flush=True)
        raise SystemExit(2)
