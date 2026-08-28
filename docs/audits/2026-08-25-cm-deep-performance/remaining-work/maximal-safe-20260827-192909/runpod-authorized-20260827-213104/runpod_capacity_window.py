"""Three bounded, read-only CPU3C capacity samples; never creates resources."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import time


ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("smoke_readonly", ROOT / "runpod_retry_v2_controller.py")
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    result = {"started_utc": now(), "read_only": True, "pod_creation_requests": 0,
              "source_uploads": 0, "samples": []}
    client = controller.session()
    result["preflight_pods"] = controller.safe_pods(client)
    if result["preflight_pods"]:
        raise RuntimeError("zero-pod baseline absent; no capacity campaign attempted")
    for index in range(3):
        sample = {"sample": index + 1, "checked_utc": now()}
        for label, suffix in (("catalog", ""), ("cpu3c_detail", "/cpu3c")):
            try:
                response = client.get(controller.REST_V2 + "/catalog/cpus" + suffix,
                                      params={"include": "AVAILABILITY", "product": "POD",
                                              "vcpuCount": 2}, timeout=15, allow_redirects=False)
                entry = {"http_status": response.status_code,
                         "headers": {key: response.headers[key] for key in
                                     ("Date", "Age", "Cache-Control", "CF-Cache-Status")
                                     if key in response.headers}}
                response.raise_for_status()
                body = response.json()
                entry["data"] = body
                sample[label] = entry
            except Exception as exc:
                sample[label] = {"error_type": type(exc).__name__}
        result["samples"].append(sample)
        offers = sample.get("catalog", {}).get("data", {}).get("cpus", [])
        detail = sample.get("cpu3c_detail", {}).get("data", {})
        detail = detail.get("cpu", detail)
        print(json.dumps({"sample": index + 1, "checked_utc": sample["checked_utc"],
                          "catalog": {row.get("id"): row.get("availability") for row in offers},
                          "cpu3c_detail_availability": detail.get("availability")}), flush=True)
        usable = {"LOW", "MEDIUM", "HIGH"}
        if any(row.get("id") == "cpu3c" and row.get("availability") in usable for row in offers):
            result["cpu3c_catalog_capacity_seen"] = True
            break
        if index < 2:
            time.sleep(20)
    result["postflight_pods"] = controller.safe_pods(client)
    result["finished_utc"] = now()
    client.close()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    path = ROOT / ("CAPACITY-WINDOW-" + stamp + ".json")
    controller.write_exclusive(path, result)
    print(json.dumps({"evidence_file": str(path), "account_pod_count": len(result["postflight_pods"]),
                      "cpu3c_catalog_capacity_seen": result.get("cpu3c_catalog_capacity_seen", False)}), flush=True)


if __name__ == "__main__":
    main()
