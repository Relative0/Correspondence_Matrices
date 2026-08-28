"""Read-only reconciliation through retry 007's original 20-minute horizon."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
ATTEMPT = ROOT / "v2-execute-007"
spec = importlib.util.spec_from_file_location("reconcile_controller", ROOT / "runpod_retry_v2_controller.py")
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


def main():
    state = json.loads((ATTEMPT / "controller-state.json").read_text())
    deadline = state["created_epoch"] + 1200 + 2
    result = {"read_only": True, "resource_writes": 0, "snapshots": [],
              "original_horizon_utc": datetime.fromtimestamp(deadline, timezone.utc).isoformat()}
    client = controller.session()
    while True:
        snapshot = {"checked_utc": controller.utc_now(), "pods": controller.safe_pods(client)}
        result["snapshots"].append(snapshot)
        print(json.dumps({"checked_utc": snapshot["checked_utc"], "pod_count": len(snapshot["pods"]),
                          "remaining_horizon_s": max(0, round(deadline - time.time())),
                          "watchdog_result_present": (ATTEMPT / "WATCHDOG-RESULT.json").exists()}), flush=True)
        if snapshot["pods"]:
            result["status"] = "pod_observed_manual_reconciliation_required"
            break
        if time.time() >= deadline:
            response = client.get(controller.REST_V2 + "/pods", timeout=15, allow_redirects=False)
            response.raise_for_status()
            body = response.json()
            pods = body if isinstance(body, list) else body.get("pods")
            if not isinstance(pods, list):
                raise RuntimeError("unexpected v2 inventory schema")
            result["v2_pods"] = [{key: row[key] for key in ("id", "name", "status") if key in row}
                                 for row in pods]
            watchdog = json.loads((ATTEMPT / "WATCHDOG-RESULT.json").read_text())
            result["watchdog_result"] = watchdog
            result["status"] = ("owned_pod_absent_after_horizon" if not pods and
                                watchdog.get("owned_pod_absent") and not watchdog.get("terminated")
                                else "manual_reconciliation_required")
            break
        time.sleep(min(45, max(0, deadline - time.time())))
    result["finished_utc"] = controller.utc_now()
    controller.write_exclusive(ROOT / "RETRY007-HORIZON-RECONCILIATION.json", result)
    client.close()
    print(json.dumps({"status": result["status"], "finished_utc": result["finished_utc"]}), flush=True)
    return int(result["status"] != "owned_pod_absent_after_horizon")


if __name__ == "__main__":
    raise SystemExit(main())
