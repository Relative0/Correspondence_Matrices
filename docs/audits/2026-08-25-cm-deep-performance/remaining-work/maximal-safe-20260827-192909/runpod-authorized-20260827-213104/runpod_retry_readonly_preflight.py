"""Read-only Runpod inventory/capacity probe; no pod writes or source upload."""
from datetime import datetime, timezone
import json
from pathlib import Path

import requests


OUT = Path(__file__).resolve().parent
CREDENTIAL = OUT.parent / ".env.runpod.local"


def main():
    key = None
    for raw in CREDENTIAL.read_text(encoding="utf-8-sig").splitlines():
        name, separator, value = raw.strip().removeprefix("export ").partition("=")
        if separator and name.strip() == "RUNPOD_API_KEY":
            if key is not None:
                raise RuntimeError("duplicate RUNPOD_API_KEY")
            key = value.strip().strip('"').strip("'")
    if not key or any(character.isspace() for character in key):
        raise RuntimeError("RUNPOD_API_KEY missing or malformed")
    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + key
    result = {"checked_utc": datetime.now(timezone.utc).isoformat(),
              "read_only": True, "source_uploads": 0, "pod_creation_requests": 0}
    pod_fields = ("id", "name", "desiredStatus", "computeType", "costPerHr",
                  "vcpuCount", "memoryInGb", "containerDiskInGb", "volumeInGb")
    try:
        response = session.get("https://rest.runpod.io/v1/pods", timeout=15,
                               allow_redirects=False)
        result["inventory_http_status"] = response.status_code
        response.raise_for_status()
        body = response.json()
        pods = body if isinstance(body, list) else body.get("pods")
        if not isinstance(pods, list):
            raise ValueError("unexpected inventory schema")
        result["pods"] = [{field: row[field] for field in pod_fields if field in row}
                          for row in pods]
    except Exception as exc:
        result["inventory_error_type"] = type(exc).__name__
    try:
        response = session.get("https://api.runpod.io/v2/catalog/cpus",
                               params={"include": "AVAILABILITY", "product": "POD",
                                       "vcpuCount": 2}, timeout=30, allow_redirects=False)
        result["catalog_http_status"] = response.status_code
        response.raise_for_status()
        cpus = response.json()["cpus"]
        result["cpu_offers"] = [{field: row[field] for field in
                                 ("id", "availability", "price", "ramGbPerVcpu", "vcpu", "dataCenters")
                                 if field in row} for row in cpus]
    except Exception as exc:
        result["catalog_error_type"] = type(exc).__name__
    session.close()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    path = OUT / ("READONLY-RETRY-PREFLIGHT-" + stamp + ".json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"evidence_file": str(path), "read_only": True,
                      "inventory_http_status": result.get("inventory_http_status"),
                      "account_pod_count": len(result["pods"]) if "pods" in result else None,
                      "catalog_http_status": result.get("catalog_http_status"),
                      "cpu3c": next((row for row in result.get("cpu_offers", [])
                                      if row["id"] == "cpu3c"), None)}, indent=2))
    return int("pods" not in result or "cpu_offers" not in result)


if __name__ == "__main__":
    raise SystemExit(main())
