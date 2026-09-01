"""Read-only bounded wait for unrelated RunPod inventory to clear before C27."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
CONTROLLER = HERE / "runpod_c27_linux_controller.py"
spec = importlib.util.spec_from_file_location("c27_controller_wait", CONTROLLER)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)

OUTPUT = HERE / "C27_AVAILABILITY_WAIT_V2_20260901.jsonl"
MAX_SECONDS = 300
POLL_SECONDS = 30


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 zero-inventory wait")
    started = time.time()
    attempt = 0
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle:
        while True:
            attempt += 1
            checked = controller.preflight.check()
            inventories = checked.get("inventories", {})
            names = sorted({
                row.get("name") for version in ("v1", "v2")
                for row in inventories.get(version, []) if row.get("name")
            })
            ready = bool(
                not any(inventories.values())
                and checked.get("selected_offer")
                and checked.get("credit_sufficient") is True
                and checked.get("spend_limit_sufficient") is True
                and checked.get("credential_values_recorded") is False
                and checked.get("resource_writes") == 0
            )
            record = {
                "attempt": attempt,
                "checked_utc": checked.get("checked_utc"),
                "inventory_counts": {
                    version: len(inventories.get(version, [])) for version in ("v1", "v2")
                },
                "pod_names": names,
                "eligible_offer": (
                    checked.get("selected_offer") or {}).get("id"),
                "resource_writes": checked.get("resource_writes"),
                "credential_values_recorded": checked.get("credential_values_recorded"),
                "ready": ready,
            }
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            print(json.dumps(record, sort_keys=True), flush=True)
            if ready:
                return 0
            if time.time() - started >= MAX_SECONDS:
                return 1
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())

