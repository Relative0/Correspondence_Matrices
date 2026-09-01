"""Record a zero-write C27 retry-003 RunPod readiness snapshot."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C27 = ROOT / "docs/recognition/c27_linux_confirmation"
DOCKER = ROOT / "docs/recognition/c27_independent_docker_confirmation"
CONTROLLER = C27 / "runpod_c27_linux_controller.py"
PRIOR = C27 / "RUNPOD_C27_RETRY_002_HTTP500_RECONCILIATION_20260901.json"
PACKAGE_VALIDATION = DOCKER / "C27_INDEPENDENT_DOCKER_PACKAGE_LOCAL_VALIDATION_20260901.json"
OUTPUT = C27 / "RUNPOD_C27_RETRY_003_READINESS_20260901.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 retry-003 readiness")
    prior = load(PRIOR)
    package = load(PACKAGE_VALIDATION)
    if (
        prior.get("status") != "verified_reconciled"
        or prior.get("authorization_consumed") is not True
        or prior.get("owned_pod_absent") is not True
        or package.get("status") != "pass"
        or package.get("second_machine_replication") is not False
    ):
        raise ValueError("C27 retry-003 readiness prerequisites mismatch")
    spec = importlib.util.spec_from_file_location("c27_retry003_readiness", CONTROLLER)
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    checked = controller.preflight.check()
    offers = [{
        "id": row.get("id"),
        "availability": row.get("availability"),
        "eligible": row.get("eligible"),
        "rate_usd_per_hour": row.get("rate_usd_per_hour"),
    } for row in checked.get("offers", [])]
    preferred = next((row for row in offers if row["id"] == "cpu5c"), None)
    if (
        preferred is None
        or preferred.get("availability") != "HIGH"
        or preferred.get("eligible") is not True
        or float(preferred.get("rate_usd_per_hour", 1)) > 0.25
        or checked.get("credit_sufficient") is not True
        or checked.get("spend_limit_sufficient") is not True
        or checked.get("credential_values_recorded") is not False
        or checked.get("resource_writes") != 0
        or not controller.allowed_baseline(checked.get("inventories", {}))
    ):
        raise ValueError("C27 retry-003 readiness gate failed")
    result = {
        "schema": "crse-runpod-c27-retry-003-readiness/v1",
        "status": "ready_read_only",
        "checked_utc": checked.get("checked_utc"),
        "offers": offers,
        "preferred_cpu_flavor": "cpu5c",
        "preferred_rate_usd_per_hour": preferred["rate_usd_per_hour"],
        "preferred_availability": preferred["availability"],
        "preferred_eligible": True,
        "baseline_allowed": True,
        "account_ready": True,
        "resource_writes": 0,
        "create_requests": 0,
        "credentials_recorded_or_uploaded": False,
        "production_write": False,
    }
    OUTPUT.write_bytes(json.dumps(
        result, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
