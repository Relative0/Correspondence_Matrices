"""Bounded read-only readiness wait, then invoke the frozen P7 W4 controller."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import http_p7_w4_timing_preflight_v1 as preflight


HERE = Path(__file__).resolve().parent
CONTROLLER = HERE / "runpod_p7_w4_timing_controller_v1.py"
AUTHORIZATION = HERE / "HTTP-P7-W4-TIMING-V1-AUTHORIZED-20260831.json"
OUT = HERE / "p7-w4-timing-v1-001"
LOG = HERE / "P7-W4-TIMING-V1-READINESS-WAIT.jsonl"
WAIT_SECONDS = 600
INTERVAL_SECONDS = 20
CONTROLLER_SHA256 = "51ca1743ae15dc503407df63fc27852290096171008e68346b2834ada7dd67d2"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append(value: dict) -> None:
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")


def main() -> int:
    if OUT.exists():
        raise RuntimeError("W4 output identity already exists")
    if not AUTHORIZATION.is_file() or sha256(CONTROLLER) != CONTROLLER_SHA256:
        raise RuntimeError("W4 authorization or frozen controller identity is unavailable")
    deadline = time.monotonic() + WAIT_SECONDS
    attempt = 0
    while True:
        attempt += 1
        try:
            result = preflight.check()
            record = {
                "attempt": attempt,
                "checked_utc": result["checked_utc"],
                "ready": result["ready"],
                "resource_writes": result["resource_writes"],
                "host_ac_connected": result["host_ac_connected"],
                "inventories_empty": result["current_inventories"] == {"v1": [], "v2": []},
                "credit_sufficient": result["credit_sufficient"],
                "spend_limit_sufficient": result["spend_limit_sufficient"],
                "eligible_offers": [
                    {
                        "id": offer.get("id"),
                        "availability": offer.get("availability"),
                        "rate_usd_per_hour": offer.get("rate_usd_per_hour"),
                    }
                    for offer in result["offers"]
                    if offer.get("eligible")
                ],
                "selected_offer": None if result["selected_offer"] is None else result["selected_offer"]["id"],
                "projected_20_min_cost_usd": result["projected_20_min_cost_usd"],
                "projected_aggregate_cost_usd": result["projected_aggregate_cost_usd"],
            }
        except Exception as exc:
            result = None
            record = {
                "attempt": attempt,
                "checked_utc": preflight.utc_now(),
                "ready": False,
                "resource_writes": 0,
                "error_type": type(exc).__name__,
            }
        append(record)
        print(json.dumps(record, sort_keys=True), flush=True)
        if result is not None and result["ready"]:
            append({
                "checked_utc": preflight.utc_now(),
                "status": "invoking_frozen_controller",
                "controller_sha256": sha256(CONTROLLER),
            })
            return subprocess.run([sys.executable, str(CONTROLLER)], cwd=HERE, check=False).returncode
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            append({
                "checked_utc": preflight.utc_now(),
                "status": "bounded_wait_expired",
                "attempts": attempt,
                "resource_writes": 0,
            })
            return 3
        time.sleep(min(INTERVAL_SECONDS, remaining))


if __name__ == "__main__":
    raise SystemExit(main())
