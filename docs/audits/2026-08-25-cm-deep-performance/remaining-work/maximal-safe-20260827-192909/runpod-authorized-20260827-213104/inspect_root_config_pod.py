"""Read-only Runpod lookup using the user-authorized project config loader."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import re
import sys

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(ROOT))
from cm_runpod_config import load_runpod_config

ENDPOINTS = (("v1", "https://rest.runpod.io/v1"), ("v2", "https://api.runpod.io/v2"))
POD_FIELDS = (
    "id", "name", "status", "desiredStatus", "computeType", "cloud", "cloudType",
    "costPerHr", "vcpuCount", "memoryInGb", "cpuFlavorId", "image", "imageName",
    "disk", "containerDiskInGb", "volumeInGb", "ports", "createdAt", "lastStartedAt",
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def inspect(api_version, base, pod_id, api_key):
    result = {"api_version": api_version, "checked_utc": utc_now()}
    with requests.Session() as client:
        # Avoid incidental credential loading through netrc or proxy configuration.
        client.trust_env = False
        client.headers["Authorization"] = "Bearer " + api_key
        for kind, path in (("detail", "/pods/" + pod_id), ("inventory", "/pods")):
            check = {}
            try:
                response = client.get(base + path, timeout=15, allow_redirects=False)
                check["http_status"] = response.status_code
                if response.status_code == 200:
                    body = response.json()
                    if kind == "detail":
                        pod = body.get("pod", body)
                        check["pod"] = {field: pod[field] for field in POD_FIELDS if field in pod}
                    else:
                        pods = body if isinstance(body, list) else body.get("pods")
                        if not isinstance(pods, list):
                            raise ValueError("unexpected inventory schema")
                        check["pod_count"] = len(pods)
                        check["target_in_inventory"] = any(pod.get("id") == pod_id for pod in pods)
                        check["pods"] = [
                            {field: pod[field] for field in ("id", "status", "desiredStatus", "computeType") if field in pod}
                            for pod in pods
                        ]
                # Error bodies and request/header objects are never saved or printed.
            except Exception as exc:
                check["error_type"] = type(exc).__name__
            result[kind] = check
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pod-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]{8,40}", args.pod_id):
        raise ValueError("invalid pod ID format")
    # Explicitly approved by Brian for private authentication in this lookup.
    config = load_runpod_config()
    if not config.api_key:
        print(json.dumps({"error": "project root loader returned no Runpod API key"}))
        return 2
    result = {
        "checked_utc": utc_now(), "requested_pod_id": args.pod_id,
        "credential_loader": "cm_runpod_config.load_runpod_config",
        "credential_use": "private authentication only; user approved",
        "configured_pod_id_matches_requested": config.pod_id == args.pod_id,
        "read_only": True, "resource_writes": 0, "files_uploaded": 0,
        "credential_files_changed": False, "credential_values_recorded": False,
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(inspect, version, base, args.pod_id, config.api_key)
                   for version, base in ENDPOINTS]
        result["checks"] = [future.result() for future in futures]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    output = HERE / ("ROOT-CONFIG-POD-INSPECTION-" + stamp + ".json")
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result, indent=2))
    print("evidence_file=" + str(output))
    return int(any("error_type" in row[kind] for row in result["checks"] for kind in ("detail", "inventory")))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # A config parse or network exception may contain private values.
        print(json.dumps({"error_type": type(exc).__name__}))
        raise SystemExit(2)
