"""B5 orchestrator â€” one Linux pod with dd.cudd for the matched comparison.

Guards: price < $1/hr; setup (bootstrap+apt+pip, CUDD builds from source)
capped at 25 min; driver capped at 40 min; pod TERMINATED after evidence
collection, including on failure; cost recorded. Full python:3.10 image
(gcc needed to build CUDD). Fail closed on dd.cudd (enforced pod-side).
"""
from __future__ import annotations

import base64
import hashlib
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
SETUP_TIMEOUT_S = 25 * 60
DRIVER_TIMEOUT_S = 40 * 60
OUT_DIR = BASE / "bx2_cudd_orders_2026_08_03"


def post_retry(url, **kw):
    """The RunPod proxy intermittently 404s just after the bootstrap becomes
    healthy; retry 404/5xx with backoff (observed in run 1)."""
    last = None
    for _ in range(15):
        try:
            r = requests.post(url, **kw)
            if r.status_code not in (404, 502, 503):
                r.raise_for_status()
                return r
            last = r
        except requests.RequestException as exc:
            last = exc
        time.sleep(8)
    raise RuntimeError(f"POST {url} failed after retries: {last}")


def main():
    config = load_runpod_config()
    if not config.api_key:
        raise SystemExit("RunPod API key not configured")
    if OUT_DIR.exists():
        raise SystemExit(f"refusing to overwrite {OUT_DIR}")
    OUT_DIR.mkdir(parents=True)
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {config.api_key}"
    token = secrets.token_urlsafe(24)
    audit = {"terminated": False}
    pod_id = None
    t_create = time.time()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "repo.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as ar:
                for path in REPO.glob("*.py"):
                    ar.write(path, path.relative_to(REPO))
                for path in (REPO / "cmbench").rglob("*.py"):
                    ar.write(path, path.relative_to(REPO))
                for name in ("cm_bx2_cudd_orders_2026_08_03.py",
                             "CM_gap_e3_corrected_corpus_2026_08_02.jsonl"):
                    ar.write(BASE / name, (BASE / name).relative_to(REPO))
            audit["archive_sha256"] = hashlib.sha256(
                archive_path.read_bytes()).hexdigest()
            common = {
                "name": f"cm-bx2-cudd-{int(time.time())}",
                "computeType": "CPU", "cloudType": "SECURE",
                "imageName": "python:3.10", "containerDiskInGb": 15,
                "volumeInGb": 10, "volumeMountPath": "/workspace",
                "ports": ["8080/http", "8081/http"],
                "env": {"CM_BOOTSTRAP_TOKEN": token},
                "dockerEntrypoint": ["sh", "-c"],
                "dockerStartCmd": [deploy.START_CMD],
            }
            pod = None
            for flavor, vcpus in (("cpu3c", 2), ("cpu3m", 2), ("cpu5c", 2)):
                r = session.post(f"{REST}/pods",
                                 json={**common, "cpuFlavorIds": [flavor],
                                       "vcpuCount": vcpus}, timeout=180)
                if r.ok:
                    pod = r.json()
                    audit.update({"cpu_flavor": flavor, "vcpu_count": vcpus})
                    break
            if pod is None:
                raise RuntimeError("no CPU flavor available")
            pod_id = pod.get("id") or (pod.get("pod") or {}).get("id")
            cost = float(pod.get("costPerHr")
                         or (pod.get("pod") or {}).get("costPerHr") or 99)
            if cost >= 1.0:
                raise RuntimeError(f"refusing pod price ${cost}/hr")
            audit.update({"pod_id": pod_id, "cost_per_hr": cost,
                          "image": "python:3.10"})
            boot = f"https://{pod_id}-8080.proxy.runpod.net"
            work = f"https://{pod_id}-8081.proxy.runpod.net"
            if not deploy._wait_health(boot, "cm-bootstrap", SETUP_TIMEOUT_S, 8.0):
                raise RuntimeError("bootstrap never healthy")
            hdr = {"X-CM-Token": token}
            for source, remote in ((archive_path, "repo.zip"),
                                   (BASE / "cm_bx2_pod_worker_2026_08_03.py",
                                    "cm_remote_worker.py")):
                post_retry(
                    f"{boot}/put",
                    json={"name": remote,
                          "b64": base64.b64encode(source.read_bytes()).decode()},
                    headers=hdr, timeout=300)
            post_retry(f"{boot}/deploy", json={}, headers=hdr, timeout=60)
        setup_deadline = time.time() + SETUP_TIMEOUT_S
        driver_started = None
        state = {}
        while True:
            try:
                state = requests.get(f"{work}/progress", timeout=20).json()
            except Exception:
                state = state or {}
            stage = state.get("stage")
            print(f"  stage={stage}", flush=True)
            if stage == "driver" and driver_started is None:
                driver_started = time.time()
            if state.get("done") or state.get("error"):
                break
            if driver_started is None and time.time() > setup_deadline:
                audit["status"] = "aborted_setup_timeout"
                raise RuntimeError("setup timeout")
            if driver_started and time.time() - driver_started > DRIVER_TIMEOUT_S:
                audit["status"] = "aborted_driver_timeout"
                raise RuntimeError("driver timeout")
            time.sleep(15)
        audit["state"] = {k: state.get(k) for k in ("env", "install", "driver")}
        if state.get("error"):
            audit["status"] = "pod_error"
            audit["error_tail"] = state["error"][-3000:]
        else:
            payload = requests.get(f"{work}/results", timeout=120).json()
            for name, b64 in payload.get("files", {}).items():
                (OUT_DIR / name).write_bytes(base64.b64decode(b64))
            audit["files"] = sorted(payload.get("files", {}))
            audit["status"] = "complete" if payload.get("files") else "no_files"
    except Exception as exc:
        audit.setdefault("status", "orchestrator_error")
        audit["error"] = str(exc)
    finally:
        if pod_id:
            try:
                session.delete(f"{REST}/pods/{pod_id}", timeout=60)
                audit["terminated"] = True
            except Exception:
                audit["terminated"] = False
        audit["lifetime_s"] = time.time() - t_create
        audit["cost_usd_actual"] = round(
            audit.get("cost_per_hr", 0) * audit["lifetime_s"] / 3600, 4)
        (OUT_DIR / "bx2_pod_audit_2026_08_03.json").write_text(
            json.dumps(audit, indent=2), encoding="utf-8")
        print(json.dumps({k: audit.get(k) for k in
                          ("status", "cost_usd_actual", "terminated")}, indent=2))


if __name__ == "__main__":
    main()
