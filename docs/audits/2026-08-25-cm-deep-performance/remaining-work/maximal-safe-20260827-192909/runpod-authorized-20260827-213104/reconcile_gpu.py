"""One read-only inventory snapshot for the ambiguous GPU creation request."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import time


ROOT = Path(__file__).resolve().parent
ATTEMPT = ROOT / "gpu-execute-001"
spec = importlib.util.spec_from_file_location("gpu_controller", ROOT / "runpod_gpu_smoke_controller.py")
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


def inventory(version, base, name):
    result = {"api_version": version, "checked_utc": controller.utc_now()}
    with controller.session() as client:
        try:
            response = client.get(base + "/pods", timeout=15, allow_redirects=False)
            result["http_status"] = response.status_code
            response.raise_for_status()
            body = response.json()
            pods = body if isinstance(body, list) else body.get("pods")
            if not isinstance(pods, list):
                raise ValueError("unexpected pod inventory schema")
            fields = ("id", "name", "status", "desiredStatus", "computeType",
                      "costPerHr", "vcpuCount", "memoryInGb", "containerDiskInGb", "volumeInGb")
            result["pods"] = [{key: row[key] for key in fields if key in row} for row in pods]
            result["owned_pods"] = [row for row in result["pods"] if row.get("name") == name]
        except Exception as exc:
            result["error_type"] = type(exc).__name__
    return result


def main():
    state = json.loads((ATTEMPT / "controller-state.json").read_text())
    result = {"read_only": True, "resource_writes": 0, "attempt": ATTEMPT.name,
              "checked_utc": controller.utc_now(), "owned_name": state["name"],
              "original_horizon_utc": datetime.fromtimestamp(state["created_epoch"] + 1200, timezone.utc).isoformat()}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(inventory, version, base, state["name"])
                   for version, base in (("v1", controller.REST_V1), ("v2", controller.REST_V2))]
        result["inventories"] = [future.result() for future in futures]
    for filename, key in (("WATCHDOG-RESULT.json", "watchdog_result"),
                          ("HOST-AWAKE-RELEASED-watchdog.json", "watchdog_awake_release")):
        path = ATTEMPT / filename
        if path.exists():
            result[key] = json.loads(path.read_text())
    result["after_original_horizon"] = time.time() >= state["created_epoch"] + 1200
    result["all_inventory_reads_succeeded"] = all("pods" in row for row in result["inventories"])
    result["zero_pods_observed"] = result["all_inventory_reads_succeeded"] and all(not row["pods"] for row in result["inventories"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    path = ATTEMPT / ("INDEPENDENT-INVENTORY-" + stamp + ".json")
    controller.write_exclusive(path, result)
    print(json.dumps({key: result.get(key) for key in
                      ("checked_utc", "after_original_horizon", "all_inventory_reads_succeeded",
                       "zero_pods_observed", "watchdog_result", "watchdog_awake_release")}, indent=2))
    print("evidence_file=" + str(path))
    return int(not result["zero_pods_observed"])


if __name__ == "__main__":
    raise SystemExit(main())
