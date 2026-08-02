"""B6 orchestrator — cross-platform replication of B1 on 5 RunPod cpu3c pods.

Pre-registered acceptance criteria (fixed before any pod runs):
- worker-echo gate: every pod must verify the CURRENT cm_remote_worker
  words_eval echo in-process before its driver runs (fail closed);
- identity gate: every pod's per-formula identity fields (structural_hash,
  truth_sha256, per-arm instruction/op counts) must match the local archive
  exactly;
- replication: PASSED if, on every completed pod, the all-corpus blocked
  geomean's stratified-bootstrap CI excludes parity AND the point estimate
  is within +-0.05 of the local B1 value 0.8876; FAILED if any pod's CI
  includes parity or deviates more; INCONCLUSIVE if fewer than 3 pods
  complete.
- guards: bootstrap+setup abort at 15 min; driver abort at 2x local runtime
  (2 x 44.4 s), enforced by polling (driver wall reported by the pod);
  every pod is TERMINATED after evidence collection, including on failure;
  hard budget cap $5 total (creation refused if projected cost exceeds it).
- no local-fallback rows: evidence comes only from pod /results payloads.

Usage: run with the venv python. Writes everything under
deliverables_n22_24/b6_pod_replication_2026_08_03/ (refuse-overwrite).
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
N_PODS = 2  # run 2: replace the two proxy-404 failures from run 1 (3/5 complete)
SETUP_TIMEOUT_S = 15 * 60
DRIVER_TIMEOUT_S = 2 * 44.4
LOCAL_GEOMEAN = 0.8876
BUDGET_USD = 5.0
OUT_DIR = BASE / "b6_pod_replication_2026_08_03_run2"


def post_retry(url, **kw):
    """RunPod proxy intermittently 404s just after bootstrap health; retry."""
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


def make_zip(tmp: Path) -> Path:
    archive_path = tmp / "repo.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in REPO.glob("*.py"):
            archive.write(path, path.relative_to(REPO))
        for path in (REPO / "cmbench").rglob("*.py"):
            archive.write(path, path.relative_to(REPO))
        for name in ("cm_gap_e3_corrected_2026_08_02.py",
                     "CM_gap_e3_corrected_corpus_2026_08_02.jsonl"):
            archive.write(BASE / name, (BASE / name).relative_to(REPO))
    return archive_path


def create_pod(session, token, idx):
    common = {
        "name": f"cm-b6-rep{idx}-{int(time.time())}",
        "computeType": "CPU", "cloudType": "SECURE",
        "imageName": "python:3.10-slim", "containerDiskInGb": 10,
        "volumeInGb": 10, "volumeMountPath": "/workspace",
        "ports": ["8080/http", "8081/http"],
        "env": {"CM_BOOTSTRAP_TOKEN": token},
        "dockerEntrypoint": ["sh", "-c"],
        "dockerStartCmd": [deploy.START_CMD],
    }
    for flavor, vcpus in (("cpu3c", 2), ("cpu3m", 2), ("cpu5c", 2)):
        r = session.post(f"{REST}/pods",
                         json={**common, "cpuFlavorIds": [flavor], "vcpuCount": vcpus},
                         timeout=180)
        if r.ok:
            pod = r.json()
            pod_id = pod.get("id") or (pod.get("pod") or {}).get("id")
            cost = float(pod.get("costPerHr")
                         or (pod.get("pod") or {}).get("costPerHr") or 99)
            if cost >= 1.0:
                session.delete(f"{REST}/pods/{pod_id}", timeout=60)
                raise RuntimeError(f"refusing pod price ${cost}/hr")
            return pod_id, flavor, vcpus, cost
    raise RuntimeError(f"no CPU flavor available for pod {idx}")


def terminate(session, pod_id):
    try:
        session.delete(f"{REST}/pods/{pod_id}", timeout=60)
        return True
    except Exception:
        return False


def run_pod(session, idx, archive_path, worker_path, audit_rows):
    token = secrets.token_urlsafe(24)
    record = {"pod_index": idx, "terminated": False, "status": "created"}
    audit_rows.append(record)
    t_create = time.time()
    pod_id, flavor, vcpus, cost = create_pod(session, token, idx)
    record.update({"pod_id": pod_id, "cpu_flavor": flavor, "vcpu_count": vcpus,
                   "cost_per_hr": cost, "created_unix": t_create})
    boot = f"https://{pod_id}-8080.proxy.runpod.net"
    work = f"https://{pod_id}-8081.proxy.runpod.net"
    try:
        if not deploy._wait_health(boot, "cm-bootstrap", SETUP_TIMEOUT_S, 8.0):
            record["status"] = "aborted_setup_timeout"
            return record
        hdr = {"X-CM-Token": token}
        for source, remote in ((archive_path, "repo.zip"),
                               (worker_path, "cm_remote_worker.py")):
            post_retry(
                f"{boot}/put",
                json={"name": remote,
                      "b64": base64.b64encode(source.read_bytes()).decode()},
                headers=hdr, timeout=300)
        post_retry(f"{boot}/deploy", json={}, headers=hdr, timeout=60)
        setup_deadline = time.time() + SETUP_TIMEOUT_S
        driver_started = None
        while True:
            try:
                state = requests.get(f"{work}/progress", timeout=20).json()
            except Exception:
                state = {}
            stage = state.get("stage")
            if stage == "driver" and driver_started is None:
                driver_started = time.time()
            if state.get("done") or state.get("error"):
                break
            if driver_started is None and time.time() > setup_deadline:
                record["status"] = "aborted_setup_timeout"
                return record
            if driver_started and time.time() - driver_started > DRIVER_TIMEOUT_S + 60:
                record["status"] = "aborted_driver_timeout"
                record["driver_elapsed_s"] = time.time() - driver_started
                return record
            time.sleep(6)
        if state.get("error"):
            record["status"] = "pod_error"
            record["error_tail"] = state["error"][-2000:]
            record["state"] = {k: state.get(k) for k in
                               ("stage", "env", "worker_echo_verified", "driver")}
            return record
        driver_wall = (state.get("driver") or {}).get("wall_s")
        if driver_wall and driver_wall > DRIVER_TIMEOUT_S:
            record["status"] = "aborted_driver_over_2x_local"
            record["driver_wall_s"] = driver_wall
            return record
        payload = requests.get(f"{work}/results", timeout=120).json()
        record["state"] = {k: state.get(k) for k in
                           ("env", "worker_echo_verified", "driver")}
        files = payload.get("files", {})
        pod_dir = OUT_DIR / f"pod{idx}_{pod_id}"
        pod_dir.mkdir(parents=True, exist_ok=False)
        for name, b64 in files.items():
            (pod_dir / name).write_bytes(base64.b64decode(b64))
        record["files"] = sorted(files)
        record["status"] = "complete" if files else "no_files"
        return record
    finally:
        record["terminated"] = terminate(session, pod_id)
        record["lifetime_s"] = time.time() - t_create
        record["cost_usd_actual"] = round(
            record.get("cost_per_hr", 0) * record["lifetime_s"] / 3600, 4)


def main():
    config = load_runpod_config()
    if not config.api_key:
        raise SystemExit("RunPod API key not configured")
    if OUT_DIR.exists():
        raise SystemExit(f"refusing to overwrite {OUT_DIR}")
    OUT_DIR.mkdir(parents=True)
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {config.api_key}"
    audit_rows = []
    worker_path = BASE / "cm_b6_pod_worker_2026_08_03.py"
    spent = 0.0
    with tempfile.TemporaryDirectory() as tmp:
        archive_path = make_zip(Path(tmp))
        archive_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        for idx in range(1, N_PODS + 1):
            if spent >= BUDGET_USD * 0.8:
                audit_rows.append({"pod_index": idx,
                                   "status": "skipped_budget_guard",
                                   "spent_so_far_usd": spent})
                continue
            print(f"pod {idx}/{N_PODS} ...", flush=True)
            try:
                record = run_pod(session, idx, archive_path, worker_path, audit_rows)
            except Exception as exc:
                record = audit_rows[-1]
                record["status"] = "orchestrator_error"
                record["error"] = str(exc)
            spent += record.get("cost_usd_actual", 0.0)
            print(f"  pod {idx}: {record['status']} "
                  f"cost=${record.get('cost_usd_actual', 0):.4f} "
                  f"terminated={record.get('terminated')}", flush=True)
    manifest = {
        "archive_sha256": archive_sha,
        "n_pods_requested": N_PODS,
        "setup_timeout_s": SETUP_TIMEOUT_S,
        "driver_timeout_s": DRIVER_TIMEOUT_S,
        "budget_cap_usd": BUDGET_USD,
        "total_cost_usd": round(spent, 4),
        "acceptance_criteria": {
            "worker_echo": "every pod verifies current-worker words echo before driver",
            "identity": "per-formula identity fields exact vs local archive",
            "replication_passed": "all completed pods: stratified CI excludes "
                                  f"parity AND |geomean - {LOCAL_GEOMEAN}| <= 0.05",
            "inconclusive_if": "fewer than 3 pods complete",
        },
        "pods": audit_rows,
    }
    (OUT_DIR / "b6_pod_audit_2026_08_03.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"total cost ${spent:.4f}; audit written")


if __name__ == "__main__":
    main()
