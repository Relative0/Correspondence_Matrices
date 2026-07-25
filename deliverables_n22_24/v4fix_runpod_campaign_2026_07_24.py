"""Provision a fresh sub-$1/hr CPU pod, run V4 same-corpus campaigns, terminate."""
from __future__ import annotations

import base64
import json
import secrets
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
import cm_runpod_deploy as deploy
from cm_runpod_config import load_runpod_config

REST = "https://rest.runpod.io/v1"


def main() -> None:
    config = load_runpod_config()
    if not config.api_key:
        raise SystemExit("RunPod API key is not configured")
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {config.api_key}"
    token = secrets.token_urlsafe(24)
    pod_id = None
    audit = {"created_at_unix": time.time(), "terminated": False}
    try:
        common = {
            "name": f"cm-v4fix-{int(time.time())}",
            "computeType": "CPU", "cloudType": "SECURE",
            "imageName": "python:3.10-slim", "containerDiskInGb": 10,
            "volumeInGb": 10, "volumeMountPath": "/workspace",
            "ports": ["8080/http", "8081/http"],
            "env": {"CM_BOOTSTRAP_TOKEN": token},
            "dockerEntrypoint": ["sh", "-c"],
            "dockerStartCmd": [deploy.START_CMD],
        }
        pod = None
        for flavor, vcpus in (("cpu3c", 4), ("cpu3m", 4), ("cpu5m", 4), ("cpu3c", 2)):
            response = session.post(
                f"{REST}/pods",
                json={**common, "cpuFlavorIds": [flavor], "vcpuCount": vcpus},
                timeout=180,
            )
            if response.ok:
                pod = response.json()
                audit.update({"cpu_flavor": flavor, "vcpu_count": vcpus})
                break
        if pod is None:
            raise RuntimeError("no requested CPU flavor was available")
        pod_id = pod.get("id") or (pod.get("pod") or {}).get("id")
        cost = float(pod.get("costPerHr") or (pod.get("pod") or {}).get("costPerHr") or 99)
        if cost >= 1:
            raise RuntimeError(f"refusing pod price {cost}/hr")
        audit.update({"pod_id": pod_id, "cost_per_hr": cost})
        boot = f"https://{pod_id}-8080.proxy.runpod.net"
        work = f"https://{pod_id}-8081.proxy.runpod.net"
        if not deploy._wait_health(boot, "cm-bootstrap", 900, 8.0):
            raise RuntimeError("bootstrap did not become healthy")
        with tempfile.TemporaryDirectory() as temp:
            archive_path = Path(temp) / "repo.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in REPO.glob("*.py"):
                    archive.write(path, path.relative_to(REPO))
                for path in (REPO / "cmbench").rglob("*.py"):
                    archive.write(path, path.relative_to(REPO))
                for name in (
                    "v4audit_corpus_2026_07_24.jsonl",
                    "v4audit_symbolic_build_2026_07_24.py",
                    "v4audit_packed_eval_2026_07_24.py",
                ):
                    path = BASE / name
                    archive.write(path, path.relative_to(REPO))
            headers = {"X-CM-Token": token}
            for source, remote in (
                (archive_path, "repo.zip"),
                (BASE / "v4fix_runpod_worker_2026_07_24.py", "cm_remote_worker.py"),
            ):
                response = requests.post(
                    f"{boot}/put",
                    json={"name": remote, "b64": base64.b64encode(source.read_bytes()).decode()},
                    headers=headers, timeout=300,
                )
                response.raise_for_status()
            response = requests.post(f"{boot}/deploy", json={}, headers=headers, timeout=60)
            response.raise_for_status()
        deadline = time.time() + 3600
        state = {}
        while time.time() < deadline:
            try:
                state = requests.get(f"{work}/progress", timeout=20).json()
                print(json.dumps({k: state.get(k) for k in ("stage", "done", "error")}), flush=True)
                if state.get("done") or state.get("error"):
                    break
            except Exception:
                pass
            time.sleep(10)
        if not state.get("done"):
            raise RuntimeError(f"campaign did not complete: {state}")
        result = requests.get(f"{work}/results", timeout=120).json()
        for name, encoded in result["files"].items():
            (BASE / name.replace(".csv", "_runpod.csv")).write_bytes(base64.b64decode(encoded))
        audit["result_files"] = sorted(result["files"])
        audit["commands"] = state.get("commands")
    finally:
        if pod_id:
            response = session.delete(f"{REST}/pods/{pod_id}", timeout=180)
            audit["terminate_http_status"] = response.status_code
            audit["terminated"] = response.status_code < 300
        audit["finished_at_unix"] = time.time()
        (BASE / "CM_v4fix_runpod_audit.json").write_text(
            json.dumps(audit, indent=2), encoding="utf-8"
        )
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
