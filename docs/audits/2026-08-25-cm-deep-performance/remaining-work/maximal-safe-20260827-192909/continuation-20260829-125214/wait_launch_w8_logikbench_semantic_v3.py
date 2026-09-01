"""Bounded read-only availability wait, then invoke the frozen V3 controller."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time

import http_w8_logikbench_semantic_preflight_v2 as preflight


HERE = Path(__file__).resolve().parent
CONTROLLER = HERE / "runpod_w8_logikbench_semantic_controller_v3.py"
OUT = HERE / "w8-logikbench-semantic-v3-001"
LOG = HERE / "W8-LOGIKBENCH-SEMANTIC-V3-AVAILABILITY-WAIT.jsonl"
WAIT_SECONDS = 600
INTERVAL_SECONDS = 20


def append(value: dict) -> None:
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")


def main() -> int:
    if OUT.exists():
        raise RuntimeError("V3 output identity already exists")
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
                "offers": [
                    {
                        "id": offer.get("id"),
                        "availability": offer.get("availability"),
                        "eligible": offer.get("eligible"),
                        "rate_usd_per_hour": offer.get("rate_usd_per_hour"),
                    }
                    for offer in result["offers"]
                ],
                "selected_offer": None if result["selected_offer"] is None else result["selected_offer"]["id"],
                "projected_20_min_cost_usd": result["projected_20_min_cost_usd"],
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
            return subprocess.run(
                [sys.executable, str(CONTROLLER)], cwd=HERE, check=False
            ).returncode
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            append({
                "checked_utc": preflight.utc_now(), "status": "bounded_wait_expired",
                "attempts": attempt, "resource_writes": 0,
            })
            return 3
        time.sleep(min(INTERVAL_SECONDS, remaining))


if __name__ == "__main__":
    raise SystemExit(main())
