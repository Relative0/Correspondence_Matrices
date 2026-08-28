"""Read-only final reconciliation; never creates, restarts, or replaces a pod."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    controller = load("cleanup_v1_controller", "runpod_retry_cpu8_v1_controller.py")
    reconcile = load("cleanup_inventory", "reconcile_cpu8.py")
    attempt = ROOT / "cpu8-v1-execute-001"
    reconcile.ATTEMPT = attempt
    reconcile.controller = controller
    state = json.loads((attempt / "controller-state.json").read_text())
    horizon = state["created_epoch"] + 1205
    guard = ROOT / "cpu8-v1-final-cleanup-guard"
    guard.mkdir(exist_ok=False)
    controller.OUT = guard
    with controller.host_awake_guard("reconciliation"):
        while True:
            with redirect_stdout(io.StringIO()):
                reconcile.main()
            latest = max(attempt.glob("INDEPENDENT-INVENTORY-*.json"), key=lambda path: path.name)
            snapshot = json.loads(latest.read_text())
            observed = [row for inventory in snapshot["inventories"] for row in inventory.get("pods", [])]
            print(json.dumps({"checked_utc": snapshot["checked_utc"],
                              "all_inventory_reads_succeeded": snapshot["all_inventory_reads_succeeded"],
                              "zero_pods_observed": snapshot["zero_pods_observed"],
                              "remaining_s": max(0, round(horizon-time.time())),
                              "watchdog_result": snapshot.get("watchdog_result")}), flush=True)
            if observed:
                raise RuntimeError("pod observed; inspect saved inventory before any resource action")
            if time.time() >= horizon:
                watchdog = snapshot.get("watchdog_result", {})
                released = snapshot.get("watchdog_awake_release", {})
                passed = (snapshot["zero_pods_observed"] and watchdog.get("owned_pod_absent")
                          and not watchdog.get("terminated") and released.get("released"))
                result = {"status": "owned_pod_absent_after_horizon" if passed else "unresolved",
                          "checked_utc": controller.utc_now(), "read_only": True,
                          "resource_writes": 0, "pod_creation_requests": 0,
                          "final_snapshot": str(latest), "snapshot": snapshot}
                controller.write_exclusive(ROOT / "CPU8-V1-FINAL-RECONCILIATION.json", result)
                print(json.dumps({"status": result["status"]}), flush=True)
                return int(not passed)
            time.sleep(min(45, max(0, horizon-time.time())))


if __name__ == "__main__":
    raise SystemExit(main())
