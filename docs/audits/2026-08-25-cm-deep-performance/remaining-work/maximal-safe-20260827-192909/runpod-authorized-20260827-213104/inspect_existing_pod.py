"""Inspect one user-supplied pod ID; no create/start/stop/upload requests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("inspection_auth", HERE / "runpod_gpu_smoke_controller.py")
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


def inspect(version, base, pod_id):
    result = {"api_version": version, "checked_utc": controller.utc_now(), "requested_pod_id": pod_id}
    with controller.session() as client:
        response = client.get(base + "/pods/" + pod_id, timeout=15, allow_redirects=False)
        result["detail_http_status"] = response.status_code
        if response.status_code == 200:
            body = response.json()
            pod = body.get("pod", body)
            # Never access or record env, registry auth, commands, tokens, or keys.
            fields = ("id", "name", "status", "desiredStatus", "computeType", "cloud", "cloudType",
                      "cost", "costPerHr", "vcpuCount", "memoryInGb", "cpuFlavorId",
                      "image", "imageName", "disk", "containerDiskInGb", "volumeInGb",
                      "ports", "createdAt", "lastStartedAt", "dataCenterId")
            result["pod"] = {key: pod[key] for key in fields if key in pod}
            gpu = pod.get("gpu") or {}
            result["gpu"] = {key: gpu[key] for key in ("id", "count", "displayName") if key in gpu}
            machine = pod.get("machine") or {}
            result["machine"] = {key: machine[key] for key in ("gpuTypeId", "secureCloud", "dataCenterId") if key in machine}
            result["persistent_mount_present"] = bool((pod.get("mounts") or {}).get("persistent"))
            result["network_volume_present"] = bool(pod.get("networkVolume") or (pod.get("mounts") or {}).get("network"))
        response = client.get(base + "/pods", timeout=15, allow_redirects=False)
        result["inventory_http_status"] = response.status_code
        if response.status_code == 200:
            body = response.json()
            pods = body if isinstance(body, list) else body.get("pods")
            if not isinstance(pods, list):
                raise ValueError("unexpected inventory schema")
            result["inventory_count"] = len(pods)
            result["target_in_inventory"] = any(pod.get("id") == pod_id for pod in pods)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pod-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]{8,40}", args.pod_id):
        raise ValueError("invalid pod ID format")
    result = {"checked_utc": controller.utc_now(), "user_supplied_pod_id": args.pod_id,
              "read_only": True, "resource_writes": 0, "files_uploaded": 0, "config_changed": False}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(inspect, version, base, args.pod_id)
                   for version, base in (("v1", controller.REST_V1), ("v2", controller.REST_V2))]
        results = []
        for future in futures:
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({"error_type": type(exc).__name__})
        result["checks"] = results
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    output = HERE / ("USER-POD-INSPECTION-" + stamp + ".json")
    controller.write_exclusive(output, result)
    print(json.dumps(result, indent=2))
    print("evidence_file=" + str(output))
    return int(any("error_type" in row for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
