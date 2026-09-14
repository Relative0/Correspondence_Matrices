"""Run the separately authorized CM counting/biology/affine results Pod."""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shlex
import subprocess
import sys
import time
import uuid
import zipfile
import zlib

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cm_runpod_config import load_runpod_config

BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
PRELAUNCH = BASE / "prelaunch-008"
AUTHORIZATION = BASE / "results-authorization-001/RUNPOD_RESULTS_AUTHORIZATION.json"
REQUEST = BASE / "results-approval-request-001/RUNPOD_RESULTS_APPROVAL_REQUEST.json"
MANIFEST = PRELAUNCH / "UPLOAD_MANIFEST.json"
BOOTSTRAP = ROOT / "scripts/cm_benchmark_runpod_bootstrap.py"
REMOTE = ROOT / "scripts/cm_benchmark_runpod_remote_v3.py"
CORE_SCREEN = ROOT / "scripts/cm_benchmark_core_screen.py"
CORE_PLAN = BASE / "core-screen-freeze-001/PLAN.json"
RECONCILIATION = BASE / "campaign-reconciliation-002/RUNPOD_RECONCILIATION.json"
EXPECTED_OUT = BASE / "runpod-results-001"
V1, V2 = "https://rest.runpod.io/v1", "https://api.runpod.io/v2"
GRAPHQL = "https://api.runpod.io/graphql"
CAMPAIGN = "cm-mega-prelaunch-20260914-008"
IMAGE = "python:3.13.15-bookworm@sha256:a53008522631dbcb063c4d5982aa91a00e86e51d90bbcf3513313f1a5c163af8"
CPU, VCPU, RAM_GB, DISK_GB = "cpu3g", 16, 64.0, 30
RATE_CAP = 0.64
LIFETIME = 2 * 3600
HORIZON = LIFETIME + 300
PHASE_COST_CAP = 1.35
RESULT_CAP = 256 << 20


def now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def append(path, value):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")


def session():
    key = load_runpod_config().api_key
    if not key or any(char.isspace() for char in key):
        raise RuntimeError("RunPod API credential missing or malformed")
    client = requests.Session()
    client.trust_env = False
    client.headers["Authorization"] = "Bearer " + key
    return client


def inventory(client, endpoint):
    response = client.get(endpoint + "/pods", timeout=15, allow_redirects=False)
    response.raise_for_status()
    value = response.json()
    pods = value if isinstance(value, list) else value.get("pods")
    if not isinstance(pods, list):
        raise RuntimeError("unexpected inventory schema")
    return [{key: row.get(key) for key in ("id", "name", "status", "desiredStatus")} for row in pods]


def inventories(client):
    return {"v1": inventory(client, V1), "v2": inventory(client, V2)}


def require_authorization():
    authorization, request, manifest = load(AUTHORIZATION), load(REQUEST), load(MANIFEST)
    reconciliation = load(RECONCILIATION)
    bound = {
        "upload_manifest": digest(MANIFEST),
        "final_reconciliation": digest(RECONCILIATION),
        "bootstrap": digest(BOOTSTRAP),
        "results_remote_worker": digest(REMOTE),
        "core_screen_runner": digest(CORE_SCREEN),
        "core_screen_plan": digest(CORE_PLAN),
        "results_controller": digest(Path(__file__).resolve()),
    }
    totals = reconciliation.get("totals", {})
    inventories = reconciliation.get("inventories", {})
    if (authorization.get("authorized") is not True or authorization.get("campaign_id") != CAMPAIGN
            or authorization.get("request_sha256") != digest(REQUEST)
            or authorization.get("exact_authorized_text") != request.get("approval_text_to_repeat")
            or authorization.get("bound_sha256") != bound or request.get("bound_sha256") != bound
            or digest(MANIFEST) != "f12864a3d072062526ea298aaa1c14ec8a6cb972314de7e9762bf21ba1277e72"
            or authorization.get("maximum_concurrent_pods") != 1
            or authorization.get("maximum_additional_pods") != 1
            or authorization.get("maximum_total_campaign_pods") != 4
            or authorization.get("maximum_phase_pod_hours") != 2
            or authorization.get("maximum_phase_runpod_charges_usd") != PHASE_COST_CAP
            or authorization.get("maximum_total_pod_hours") != 16
            or authorization.get("maximum_total_runpod_charges_usd") != 50
            or authorization.get("maximum_result_archive_bytes") != RESULT_CAP
            or authorization.get("further_replacement") is not False
            or any(authorization.get(key) is not False for key in
                   ("production_changes", "commit", "push", "publication", "credential_upload"))
            or manifest.get("campaign_id") != CAMPAIGN or len(manifest.get("bundles", [])) != 11
            or reconciliation.get("authorization_exhausted") is not True
            or reconciliation.get("further_create_authorized") is not False
            or totals.get("pods_created") != 3
            or float(totals.get("estimated_total_pod_hours", 99)) >= 14
            or float(totals.get("estimated_compute_cost_usd", 99)) >= 48
            or inventories.get("v1_pod_count") != 0 or inventories.get("v2_pod_count") != 0):
        raise RuntimeError("authorization or frozen manifest mismatch")
    for row in manifest["bundles"]:
        path = PRELAUNCH / row["path"]
        if path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise RuntimeError("authorized shard changed: " + row["path"])
    return authorization, request, manifest


def live_preflight(client):
    snapshot = inventories(client)
    if any(snapshot.values()):
        raise RuntimeError("zero-pod concurrency preflight failed")
    response = client.get(V2 + "/catalog/cpus/" + CPU,
                          params={"include": "AVAILABILITY", "product": "POD", "vcpuCount": VCPU},
                          timeout=30, allow_redirects=False)
    response.raise_for_status()
    offer = response.json()
    rate = float(offer["price"]["securePerVcpu"]) * VCPU
    ram = float(offer["ramGbPerVcpu"]) * VCPU
    if (offer.get("id") != CPU or offer.get("availability") not in {"LOW", "MEDIUM", "HIGH"}
            or rate != RATE_CAP or ram < RAM_GB):
        raise RuntimeError("approved live CPU offer unavailable or changed")
    response = client.post(GRAPHQL, json={"query": "query { myself { clientBalance currentSpendPerHr spendLimit } }"},
                           timeout=30, allow_redirects=False)
    response.raise_for_status()
    account = response.json().get("data", {}).get("myself", {})
    credit = float(account["clientBalance"])
    current, limit = float(account["currentSpendPerHr"]), float(account["spendLimit"])
    if credit < PHASE_COST_CAP or limit < current + RATE_CAP:
        raise RuntimeError("account funding is insufficient for environment/probe stage")
    return {"checked_utc": now(), "inventories": snapshot,
            "offer": {"id": CPU, "availability": offer["availability"], "vcpu": VCPU,
                      "ram_gb": ram, "rate_usd_per_hour": rate},
            "credit_sufficient": True, "spend_limit_sufficient": True,
            "financial_values_recorded": False, "resource_writes": 0}


def find_owned(snapshot, state):
    matches = {row["id"] for rows in snapshot.values() for row in rows if row.get("name") == state["name"]}
    if len(matches) > 1:
        raise RuntimeError("multiple same-name Pods; refusing cleanup")
    identity = Path(state["output"]) / "POD-IDENTITY.json"
    if identity.exists() and matches and matches != {load(identity)["pod_id"]}:
        raise RuntimeError("owned Pod identity mismatch; refusing cleanup")
    return sorted(matches)


def cleanup(client, state, role):
    attempts = []
    matches = find_owned(inventories(client), state)
    for pod_id in matches:
        if not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
            raise RuntimeError("unsafe Pod ID")
        for endpoint in (V1, V2):
            response = client.delete(endpoint + "/pods/" + pod_id, timeout=20, allow_redirects=False)
            attempts.append({"api": endpoint, "http_status": response.status_code})
            if response.status_code in {200, 202, 204, 404}:
                break
    for _ in range(5):
        snapshot = inventories(client)
        if not find_owned(snapshot, state):
            break
        time.sleep(3)
    result = {"checked_utc": now(), "role": role, "attempts": attempts,
              "owned_pod_absent": not find_owned(snapshot, state), "inventories": snapshot}
    append(Path(state["output"]) / "cleanup-events.jsonl", result)
    return result


def watchdog(out):
    ready, state_path, done, abort = (out / name for name in
        ("watchdog-ready.json", "controller-state.json", "watchdog-done.json", "abort-requested.json"))
    client = session()
    write(ready, {"ready_utc": now(), "pid": os.getpid(), "inventories": inventories(client)})
    until = time.time() + 180
    while not state_path.exists() and time.time() < until:
        if done.exists(): return 0
        time.sleep(1)
    if not state_path.exists(): return 0
    state = load(state_path)
    if not re.fullmatch(re.escape(CAMPAIGN) + r"-results-[a-f0-9]{12}", state.get("name", "")):
        raise RuntimeError("watchdog state name invalid")
    write(out / "watchdog-state-ack.json", {"state": state, "pid": os.getpid(), "utc": now()})
    while True:
        if done.exists(): return 0
        if abort.exists() or time.time() >= state["cleanup_epoch"]:
            result = cleanup(client, state, "watchdog")
            if result["owned_pod_absent"]:
                write(out / "WATCHDOG-RESULT.json", result)
                return 0
        if time.time() >= state["horizon_epoch"]:
            result = cleanup(client, state, "watchdog-final")
            write(out / "WATCHDOG-RESULT.json", result)
            return int(not result["owned_pod_absent"])
        time.sleep(20)


@contextmanager
def awake():
    if os.name == "nt":
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        if not kernel.SetThreadExecutionState(0x80000001):
            raise RuntimeError("host wake guard failed")
    try:
        yield
    finally:
        if os.name == "nt": kernel.SetThreadExecutionState(0x80000000)


def render_remote():
    remote = REMOTE.read_text(encoding="utf-8")
    injections = {
        '"__CM_CORE_SCREEN_CODE_B64__"': repr(base64.b64encode(CORE_SCREEN.read_bytes()).decode()),
        '"__CM_CORE_SCREEN_PLAN_B64__"': repr(base64.b64encode(CORE_PLAN.read_bytes()).decode()),
    }
    for marker, value in injections.items():
        if remote.count(marker) != 1:
            raise RuntimeError("remote core-screen marker mismatch")
        remote = remote.replace(marker, value)
    return remote


def create_payload(name, manifest, token, created):
    remote = render_remote()
    source = BOOTSTRAP.read_text(encoding="utf-8")
    marker = '"__CM_REMOTE_CODE_B64__"'
    if source.count(marker) != 1:
        raise RuntimeError("bootstrap marker mismatch")
    source = source.replace(marker, repr(base64.b64encode(remote.encode()).decode()))
    packed = base64.b64encode(zlib.compress(source.encode(), 9)).decode()
    command = "import base64,zlib;exec(zlib.decompress(base64.b64decode(" + repr(packed) + ")))"
    return {"name": name, "computeType": "CPU", "cloudType": "SECURE", "imageName": IMAGE,
            "cpuFlavorIds": [CPU], "vcpuCount": VCPU, "containerDiskInGb": DISK_GB,
            "volumeInGb": 0, "volumeMountPath": "/workspace", "ports": ["8080/http"],
            "env": {"CM_BOOTSTRAP_TOKEN": token, "CM_SHARDS_JSON": json.dumps(manifest["bundles"]),
                    "CM_HARD_DEADLINE": str(created + LIFETIME),
                    "CM_CORE_SCREEN_SHA256": digest(CORE_SCREEN),
                    "CM_CORE_SCREEN_PLAN_SHA256": digest(CORE_PLAN)},
            "dockerEntrypoint": ["sh", "-c"],
            "dockerStartCmd": ["python -u -c " + shlex.quote(command)]}


def proxy(client, method, url, *, data=None, cap=16384, timeout=30):
    with client.request(method, url, data=data, timeout=timeout, allow_redirects=False, stream=True) as response:
        if response.status_code not in {200, 202}:
            raise RuntimeError("proxy HTTP " + str(response.status_code))
        result = bytearray()
        for chunk in response.iter_content(1 << 20):
            if len(result) + len(chunk) > cap:
                raise RuntimeError("proxy response cap exceeded")
            result.extend(chunk)
        return bytes(result)


def upload_shard(transport, endpoint, index, row, raw, *, attempts=6):
    history = []
    for attempt in range(1, attempts + 1):
        try:
            accepted = json.loads(proxy(
                transport, "POST", endpoint + f"/shard/{index:03d}", data=raw,
                cap=16384, timeout=180,
            ))
            if accepted.get("accepted_sha256") != row["sha256"]:
                raise RuntimeError("shard acknowledgement mismatch")
            history.append({"attempt": attempt, "status": "accepted"})
            return history
        except RuntimeError as exc:
            history.append({"attempt": attempt, "status": str(exc)})
            if str(exc) != "proxy HTTP 404" or attempt == attempts:
                raise
            time.sleep(2 * attempt)
    raise RuntimeError("shard upload attempts exhausted")


def get_actual(client, pod_id):
    for _ in range(30):
        response = client.get(V1 + "/pods/" + pod_id, timeout=15, allow_redirects=False)
        response.raise_for_status()
        pod = response.json(); pod = pod.get("pod", pod)
        if pod.get("vcpuCount") is not None and pod.get("memoryInGb") is not None:
            return pod
        time.sleep(2)
    raise RuntimeError("Pod resources did not become observable")


def validate_actual(pod, state):
    rate, ram = float(pod.get("costPerHr", "nan")), float(pod.get("memoryInGb", "nan"))
    images = [pod[key] for key in ("image", "imageName") if pod.get(key)]
    secure = (pod.get("machine") or {}).get("secureCloud")
    if (pod.get("name") != state["name"] or pod.get("cpuFlavorId") != CPU
            or pod.get("vcpuCount") != VCPU or not math.isfinite(ram) or ram < RAM_GB
            or not math.isfinite(rate) or not 0 < rate <= RATE_CAP
            or pod.get("containerDiskInGb") != DISK_GB or pod.get("volumeInGb") != 0
            or pod.get("networkVolume") or sorted(pod.get("ports") or []) != ["8080/http"]
            or secure is False or not images or any(image != IMAGE for image in images)):
        raise RuntimeError("created Pod differs from authorized resources")
    return {"rate_usd_per_hour": rate, "ram_gb": ram, "vcpu_count": VCPU,
            "cpu_flavor": CPU, "container_disk_gb": DISK_GB,
            "projected_two_hour_usd": rate * 2 + 30 * .1 * 2 / 720}


def extract_artifact(out, data):
    if len(data) > RESULT_CAP:
        raise RuntimeError("result cap exceeded")
    archive_path = out / "evidence.zip"
    archive_path.write_bytes(data)
    evidence = out / "evidence"; evidence.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or ".." in pure.parts:
                raise RuntimeError("unsafe result member")
            target = evidence.joinpath(*pure.parts); target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
    summary = load(evidence / "SUMMARY.json")
    if (summary.get("status") != "passed" or summary.get("shards") != 11
            or summary.get("schema") != "cm-benchmark-runpod-core-screen/v1"
            or summary.get("benchmark_measurements", 0) <= 0
            or not isinstance(summary.get("core_screen"), dict)):
        raise RuntimeError("retrieved core-screen summary failed")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "files": len(archive.infolist()), "summary": summary}


def run(out):
    out.mkdir(parents=True, exist_ok=False)
    record = {"status": "preflight", "started_utc": now(), "creation_attempted": False,
              "creation_uncertain": False, "pod_created": False, "uploaded_shards": 0}
    client = state = None
    try:
        authorization, request, manifest = require_authorization()
        record["authorization_sha256"] = digest(AUTHORIZATION)
        client = session(); preflight = live_preflight(client); write(out / "PREFLIGHT.json", preflight)
        with (out / "watchdog.log").open("x", encoding="utf-8") as log:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
            watcher = subprocess.Popen([sys.executable, str(Path(__file__)), "watchdog", "--output", str(out)],
                                       stdout=log, stderr=subprocess.STDOUT, creationflags=flags, close_fds=True)
        for _ in range(100):
            if (out / "watchdog-ready.json").exists(): break
            if watcher.poll() is not None: raise RuntimeError("watchdog exited before readiness")
            time.sleep(.2)
        else: raise RuntimeError("watchdog readiness timeout")
        if any(load(out / "watchdog-ready.json")["inventories"].values()):
            raise RuntimeError("watchdog observed nonzero Pod baseline")
        created = time.time()
        state = {"name": CAMPAIGN + "-results-" + uuid.uuid4().hex[:12], "created_epoch": created,
                 "cleanup_epoch": created + LIFETIME, "horizon_epoch": created + HORIZON,
                 "output": str(out.resolve())}
        write(out / "controller-state.json", state)
        for _ in range(100):
            if (out / "watchdog-state-ack.json").exists(): break
            time.sleep(.2)
        else: raise RuntimeError("watchdog state acknowledgement timeout")
        token = secrets.token_urlsafe(32)
        body = create_payload(state["name"], manifest, token, created)
        record.update({"creation_attempted": True, "creation_uncertain": True, "name": state["name"],
                       "quoted_rate_usd_per_hour": RATE_CAP})
        print(json.dumps({"stage": "create-results", "rate_usd_per_hour": RATE_CAP}), flush=True)
        response = client.post(V1 + "/pods", json=body, timeout=(15, 90), allow_redirects=False)
        record["creation_http_status"] = response.status_code
        if response.status_code not in {200, 201}:
            record["creation_uncertain"] = not 400 <= response.status_code < 500
            raise RuntimeError("Pod creation HTTP " + str(response.status_code))
        pod = response.json(); pod = pod.get("pod", pod); pod_id = pod.get("id")
        if not isinstance(pod_id, str) or not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
            raise RuntimeError("creation response omitted valid Pod ID")
        write(out / "POD-IDENTITY.json", {"pod_id": pod_id, "name": state["name"], "recorded_utc": now()})
        record.update({"pod_created": True, "pod_id": pod_id, "creation_uncertain": False})
        actual = get_actual(client, pod_id); record["actual_resources"] = validate_actual(actual, state)
        endpoint = f"https://{pod_id}-8080.proxy.runpod.net"
        with requests.Session() as transport:
            transport.trust_env = False; transport.headers["X-CM-Token"] = token
            consecutive_health = 0
            for _ in range(180):
                try:
                    health = json.loads(proxy(transport, "GET", endpoint + "/health", timeout=5))
                    if health.get("ready") is True:
                        consecutive_health += 1
                        if consecutive_health >= 2: break
                        time.sleep(2)
                        continue
                except (requests.RequestException, RuntimeError, ValueError):
                    pass
                consecutive_health = 0
                time.sleep(2)
            else: raise RuntimeError("bootstrap health timeout")
            record["health_checks_before_upload"] = consecutive_health
            record["shard_upload_attempts"] = []
            for index, row in enumerate(manifest["bundles"], 1):
                raw = (PRELAUNCH / row["path"]).read_bytes()
                history = upload_shard(transport, endpoint, index, row, raw)
                record["shard_upload_attempts"].append({"shard": row["path"], "attempts": history})
                record["uploaded_shards"] = index
                print(json.dumps({"stage": "upload", "shard": index, "of": 11}), flush=True)
            proxy(transport, "POST", endpoint + "/run", data=b"", timeout=20)
            observed = None
            while time.time() < created + LIFETIME - 120:
                try:
                    progress = json.loads(proxy(transport, "GET", endpoint + "/progress", timeout=10))
                except (requests.RequestException, RuntimeError, ValueError):
                    time.sleep(5); continue
                signature = (progress.get("stage"), progress.get("done"), progress.get("error"))
                if signature != observed:
                    append(out / "progress.jsonl", {"checked_utc": now(), **progress})
                    print(json.dumps({"stage": progress.get("stage"), "done": progress.get("done"),
                                      "error": progress.get("error")}), flush=True)
                    observed = signature
                if progress.get("done"):
                    log = proxy(transport, "GET", endpoint + "/log", cap=RESULT_CAP, timeout=120)
                    (out / "remote.log").write_bytes(log)
                    if progress.get("error"): raise RuntimeError("remote worker failed: " + str(progress["error"]))
                    artifact = proxy(transport, "GET", endpoint + "/artifact", cap=RESULT_CAP, timeout=300)
                    record["evidence"] = extract_artifact(out, artifact)
                    break
                time.sleep(5)
            else: raise RuntimeError("core-screen stage deadline exceeded")
        record["status"] = "complete"
    except Exception as exc:
        record.update({"status": "failed", "error_type": type(exc).__name__})
        if isinstance(exc, (RuntimeError, ValueError)): record["error"] = str(exc)
        if state is not None and not (out / "abort-requested.json").exists():
            write(out / "abort-requested.json", {"utc": now(), "reason": type(exc).__name__})
    finally:
        if state is not None and client is not None:
            try: record["cleanup"] = cleanup(client, state, "controller")
            except Exception as exc: record["cleanup_error_type"] = type(exc).__name__
        if record.get("cleanup", {}).get("owned_pod_absent") and not record["creation_uncertain"]:
            write(out / "watchdog-done.json", {"utc": now(), "owned_pod_absent": True})
        record["finished_utc"] = now()
        if state is not None:
            elapsed = time.time() - state["created_epoch"]; record["elapsed_since_create_s"] = elapsed
            rate = record.get("actual_resources", {}).get("rate_usd_per_hour")
            record["estimated_compute_cost_usd"] = rate * elapsed / 3600 if rate else None
        write(out / "RUN.json", record)
        if client is not None: client.close()
    print(json.dumps({key: record.get(key) for key in
                      ("status", "pod_created", "uploaded_shards", "estimated_compute_cost_usd", "cleanup", "error")},
                     indent=2), flush=True)
    return int(record["status"] != "complete" or not record.get("cleanup", {}).get("owned_pod_absent"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run", "watchdog", "preflight"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); out = args.output.resolve()
    if out != EXPECTED_OUT.resolve():
        raise RuntimeError("results controller output path mismatch")
    if args.action == "watchdog": return watchdog(out)
    if args.action == "preflight":
        require_authorization(); client = session()
        try: print(json.dumps(live_preflight(client), indent=2, sort_keys=True))
        finally: client.close()
        return 0
    with awake(): return run(out)


if __name__ == "__main__":
    raise SystemExit(main())
