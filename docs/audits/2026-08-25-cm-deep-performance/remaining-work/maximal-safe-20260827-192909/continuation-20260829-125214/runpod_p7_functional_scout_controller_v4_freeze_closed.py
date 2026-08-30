"""One-create all-freeze-source P7 Linux functional scout."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
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
import http_p7_functional_scout_preflight_v4_freeze_closed as preflight

HERE = Path(__file__).resolve().parent
TRANSPORT = HERE.parent / "runpod-authorized-20260827-213104"
OUT = HERE / "p7-functional-scout-v4-freeze-closed-001"
spec = importlib.util.spec_from_file_location("preserved_cpu_smoke", TRANSPORT / "runpod_retry_cpu8_v1_controller.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
REMOTE_CODE_PATH = HERE / "runpod_p7_functional_scout_remote_v1.py"
base.REMOTE_CODE = REMOTE_CODE_PATH.read_text(encoding="utf-8")
base.OUT = OUT
BOOTSTRAP_PATH = HERE / "http_native_scout_bootstrap_v2.py"
MANIFEST_PATH = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V6-20260830.json"
BUNDLE_PATH = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V6-20260830.zip"
PROPOSAL_PATH = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-V4-FREEZE-CLOSED-RETRY-PROPOSAL-20260830.md"
AUTHORIZATION_PATH = HERE / "HTTP-P7-FUNCTIONAL-SCOUT-V4-FREEZE-CLOSED-AUTHORIZED-20260830.json"
STATE = OUT / "controller-state.json"
IDENTITY = OUT / "POD-IDENTITY.json"
READY = OUT / "watchdog-ready.json"
STATE_ACK = OUT / "watchdog-state-ack.json"
DONE = OUT / "watchdog-done.json"
ABORT = OUT / "abort-requested.json"
HORIZON = 1200
CLEANUP_AT = 1080
CAP = 32 << 20
RATE_CAP = 0.25
PHASE_CAP = 0.10
CAMPAIGN_CAP = 1.00
STORAGE_RATE_RESERVE = 0.01
CHUNK_BYTES = 256 << 10
EXPECTED_PORTS = ["8080/http", "8081/http"]


def write(path, value):
    temporary = path.with_name(path.name + ".pending-" + uuid.uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # A hard link publishes the complete file atomically and fails if the
        # destination exists. Never expose a partly written watchdog state.
        os.link(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def append(path, value):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")


def require_authorization():
    if not AUTHORIZATION_PATH.is_file():
        raise RuntimeError("exact P7 functional-scout authorization record is absent")
    authorization = load(AUTHORIZATION_PATH)
    expected = {
        "schema": "cm-runpod-p7-functional-scout-v4-freeze-closed-authorization/v1",
        "authorized": True,
        "one_create": True,
        "no_replacement_within_this_controller": True,
        "external_source_upload_approved": True,
        "source_files": 212,
        "source_bytes": 24705826,
        "source_bundle_bytes": 4203964,
        "focused_tests": 32,
        "p7_ir_cells": 16,
        "p7_relation_cells": 20,
        "fresh_cell_processes": 36,
        "performance_ranking": False,
        "source_builds_allowed": [],
        "system_packages_allowed": [],
        "container_disk_gb": 12,
        "pod_volume_gb": 0,
        "network_volume": False,
        "lifetime_seconds": 1200,
        "phase_cap_usd": 0.10,
        "campaign_cap_usd": 1.00,
        "prior_native_bdd_persistence_pod_id": "du48i5xcu9f6rw",
        "prior_p7_functional_scout_pod_ids": ["1xh6csc4oxy067", "2fzt8mu6ji6nmw"],
        "chunk_bytes": CHUNK_BYTES,
    }
    if any(authorization.get(key) != value for key, value in expected.items()):
        raise RuntimeError("P7 functional-scout authorization scope mismatch")
    hashes = {
        "proposal_sha256": hashlib.sha256(PROPOSAL_PATH.read_bytes()).hexdigest(),
        "upload_manifest_sha256": hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest(),
        "upload_bundle_sha256": hashlib.sha256(BUNDLE_PATH.read_bytes()).hexdigest(),
        "controller_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "preflight_sha256": hashlib.sha256(Path(preflight.__file__).read_bytes()).hexdigest(),
        "remote_program_sha256": hashlib.sha256(REMOTE_CODE_PATH.read_bytes()).hexdigest(),
        "bootstrap_sha256": hashlib.sha256(BOOTSTRAP_PATH.read_bytes()).hexdigest(),
    }
    if any(authorization.get(key) != value for key, value in hashes.items()):
        raise RuntimeError("P7 functional-scout authorization hash mismatch")
    return authorization


def frozen_bundle(manifest):
    payload = BUNDLE_PATH.read_bytes()
    if len(payload) != 4203964 or hashlib.sha256(payload).hexdigest() != "cc75275cff77a52f319fbd5713d03faff8fa26cb0887b3df8e5a83728e70a352":
        raise RuntimeError("frozen source bundle identity mismatch")
    expected = {row["target"]: row for row in manifest["files"]}
    if len(expected) != len(manifest["files"]):
        raise RuntimeError("duplicate manifest target")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise RuntimeError("frozen source bundle member mismatch")
        for name in names:
            data = archive.read(name)
            row = expected[name]
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise RuntimeError("frozen source bundle payload mismatch: " + name)
    return payload

def inventories(client):
    return {"v1": preflight.inventory(client, preflight.V1), "v2": preflight.inventory(client, preflight.V2)}


def find_owned(snapshot, state):
    matches = {row["id"] for rows in snapshot.values() for row in rows if row.get("name") == state["name"]}
    if len(matches) > 1:
        raise RuntimeError("multiple matching pod names; manual review required")
    if IDENTITY.exists():
        expected = load(IDENTITY)["pod_id"]
        for rows in snapshot.values():
            for row in rows:
                if row.get("id") == expected and row.get("name") != state["name"]:
                    raise RuntimeError("pod ownership name mismatch; refusing deletion")
        if matches and matches != {expected}:
            raise RuntimeError("pod ownership ID mismatch; refusing deletion")
    return sorted(matches)


def cleanup_owned(client, state, role):
    snapshot = inventories(client)
    matches = find_owned(snapshot, state)
    attempts = []
    for pod_id in matches:
        if not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
            raise RuntimeError("invalid owned pod ID")
        for endpoint in (preflight.V1, preflight.V2):
            try:
                response = client.delete(endpoint + "/pods/" + pod_id, timeout=10, allow_redirects=False)
                attempts.append({"pod_id": pod_id, "api": endpoint, "http_status": response.status_code})
                if response.status_code in (200, 202, 204):
                    break
            except requests.RequestException as exc:
                attempts.append({"pod_id": pod_id, "api": endpoint, "error_type": type(exc).__name__})
    for index in range(3):
        snapshot = inventories(client)
        if not find_owned(snapshot, state):
            break
        if index < 2:
            time.sleep(2)
    result = {"checked_utc": preflight.utc_now(), "role": role, "attempts": attempts,
              "owned_pod_absent": not find_owned(snapshot, state), "inventories": snapshot}
    append(OUT / "cleanup-events.jsonl", result)
    return result


def watchdog():
    client = preflight.session()
    startup = inventories(client)
    write(READY, {"ready_utc": preflight.utc_now(), "ready_epoch": time.time(), "pid": os.getpid(), "parent_pid": os.getppid(),
                  "network_probe_passed": True, "startup_inventories": startup})
    waiting_until = time.time() + 120
    while not STATE.exists():
        if DONE.exists():
            return 0
        if time.time() >= waiting_until:
            write(OUT / "WATCHDOG-RESULT.json", {"status": "no_create_state", "finished_utc": preflight.utc_now()})
            return 0
        time.sleep(1)
    state = load(STATE)
    if (set(state) != {"name", "created_epoch", "cleanup_epoch", "horizon_epoch"}
        or not re.fullmatch(r"cm-p7-functional-scout-[a-f0-9]{12}", state["name"])
        or any(not math.isfinite(state[key]) for key in ("created_epoch", "cleanup_epoch", "horizon_epoch"))
        or abs(state["cleanup_epoch"] - state["created_epoch"] - CLEANUP_AT) > 0.001
        or abs(state["horizon_epoch"] - state["created_epoch"] - HORIZON) > 0.001):
        raise RuntimeError("invalid watchdog state")
    write(STATE_ACK, {"state": state, "pid": os.getpid(), "acknowledged_utc": preflight.utc_now()})
    errors = []
    last = None
    while True:
        if DONE.exists():
            write(OUT / "WATCHDOG-RESULT.json", {"status": "controller_cleanup_verified", "finished_utc": preflight.utc_now(),
                                                "errors": errors})
            return 0
        sampled = time.time()
        try:
            snapshot = inventories(client)
            matches = find_owned(snapshot, state)
            last = {"checked_utc": preflight.utc_now(), "epoch": sampled, "inventories": snapshot,
                    "owned_ids": matches, "after_horizon": sampled >= state["horizon_epoch"]}
            append(OUT / "watchdog-inventory.jsonl", last)
            if matches and (ABORT.exists() or sampled >= state["cleanup_epoch"]):
                cleanup_owned(client, state, "watchdog")
            if sampled >= state["horizon_epoch"]:
                final = cleanup_owned(client, state, "watchdog-final")
                write(OUT / "WATCHDOG-RESULT.json", {"status": "horizon_reconciled" if final["owned_pod_absent"] else "cleanup_failed",
                    "finished_utc": preflight.utc_now(), "errors": errors, "final": final})
                return int(not final["owned_pod_absent"])
        except Exception as exc:
            errors.append({"checked_utc": preflight.utc_now(), "error_type": type(exc).__name__})
            append(OUT / "watchdog-errors.jsonl", errors[-1])
            if sampled > state["horizon_epoch"] + 30:
                write(OUT / "WATCHDOG-RESULT.json", {"status": "reconciliation_failed", "errors": errors,
                                                    "finished_utc": preflight.utc_now(), "last_snapshot": last})
                return 1
        # Small sleeps allow prompt response to a completed controller; snapshots are spaced.
        for _ in range(20):
            if DONE.exists():
                break
            time.sleep(1)


def windows_pid_running(pid):
    """Read-only wait on a Windows process handle; never use os.kill(pid, 0)."""
    if os.name != "nt":
        raise RuntimeError("watchdog process check is validated for Windows only")
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only.
    if not handle:
        return False
    try:
        return kernel.WaitForSingleObject(handle, 0) == 258  # WAIT_TIMEOUT: alive.
    finally:
        kernel.CloseHandle(handle)


def bind_watchdog(proc, ready):
    pid = ready.get("pid")
    if (not isinstance(pid, int) or pid <= 0 or proc.poll() is not None
        or (pid != proc.pid and ready.get("parent_pid") != proc.pid)
        or not windows_pid_running(pid)):
        raise RuntimeError("watchdog worker is not live and bound to its launcher")
    proc.cm_watchdog_pid = pid
    return {"checked_utc": preflight.utc_now(), "launcher_pid": proc.pid,
            "watchdog_pid": pid, "watchdog_parent_pid": ready.get("parent_pid"),
            "venv_redirector_observed": pid != proc.pid, "worker_handle_reports_alive": True}


def arm_watchdog():
    with (OUT / "watchdog.log").open("xb") as stream:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        proc = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "--watchdog"],
                                stdout=stream, stderr=subprocess.STDOUT, creationflags=flags, close_fds=True)
    for _ in range(200):
        if READY.exists():
            ready = load(READY)
            if not ready.get("network_probe_passed") or any(ready["startup_inventories"].values()):
                raise RuntimeError("watchdog zero-pod network probe failed")
            write(OUT / "WATCHDOG-PROCESS-BINDING.json", bind_watchdog(proc, ready))
            return proc
        if proc.poll() is not None:
            raise RuntimeError("watchdog exited before readiness")
        time.sleep(0.2)
    raise RuntimeError("watchdog failed to arm")


def confirm_watchdog(proc, state):
    expected_pid = getattr(proc, "cm_watchdog_pid", proc.pid)
    for _ in range(50):
        if proc.poll() is not None or not windows_pid_running(expected_pid):
            raise RuntimeError("watchdog exited before create")
        if STATE_ACK.exists():
            ack = load(STATE_ACK)
            if ack.get("state") != state or ack.get("pid") != expected_pid:
                raise RuntimeError("watchdog did not acknowledge this exact state")
            if proc.poll() is not None or not windows_pid_running(expected_pid):
                raise RuntimeError("watchdog exited after state acknowledgement")
            return
        time.sleep(0.1)
    raise RuntimeError("watchdog state acknowledgement timed out; no create allowed")


def prepare_payload(bundle, manifest, created):
    payload = {"bundle": base64.b64encode(bundle).decode("ascii"),
               "manifest": base64.b64encode(json.dumps(manifest, sort_keys=True).encode()).decode("ascii"),
               "code": base64.b64encode(base.REMOTE_CODE.encode()).decode("ascii"),
               "environment": {"CM_BUNDLE_SHA256": hashlib.sha256(bundle).hexdigest(),
                               "CM_IMAGE_TAG": base.IMAGE_TAG, "CM_IMAGE_DIGEST": base.IMAGE_AMD64_DIGEST,
                               "CM_SETUP_DEADLINE": str(created + 780)}}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(raw) > 8 << 20:
        raise RuntimeError("transport payload exceeds eight MiB")
    return raw


def create_payload(name, offer, token, raw, created):
    bootstrap = BOOTSTRAP_PATH.read_bytes()
    compressed = base64.b64encode(zlib.compress(bootstrap, 9)).decode("ascii")
    code = "import base64,zlib;exec(zlib.decompress(base64.b64decode(" + repr(compressed) + ")))"
    start = "python -u -c " + shlex.quote(code)
    return {"name": name, "computeType": "CPU", "cloudType": "SECURE", "imageName": base.IMAGE,
            "cpuFlavorIds": [offer["id"]], "vcpuCount": 2,
            "containerDiskInGb": 12, "volumeInGb": 0, "volumeMountPath": "/workspace",
            "ports": EXPECTED_PORTS,
            "env": {"CM_BOOTSTRAP_TOKEN": token, "CM_PAYLOAD_SHA256": hashlib.sha256(raw).hexdigest(),
                    "CM_PAYLOAD_BYTES": str(len(raw)), "CM_HARD_DEADLINE": str(created + CLEANUP_AT)},
            "dockerEntrypoint": ["sh", "-c"], "dockerStartCmd": [start]}


def actual_pod(client, pod_id):
    response = client.get(preflight.V1 + "/pods/" + pod_id, timeout=10, allow_redirects=False)
    response.raise_for_status()
    value = response.json()
    pod = value.get("pod", value)
    # Current v1 responses use image and machine.secureCloud, unlike request
    # fields imageName/cloudType. Do not infer actual placement from our request.
    machine = pod.get("machine") or {}
    if not any(pod.get(key) is not None for key in ("cloudType", "cloud")) and machine.get("secureCloud") is None:
        response = client.get(preflight.V2 + "/pods/" + pod_id, timeout=10, allow_redirects=False)
        response.raise_for_status()
        extra = response.json()
        extra = extra.get("pod", extra)
        if extra.get("id") != pod_id:
            raise RuntimeError("v2 placement lookup returned a different pod")
        pod = {**pod, "verified_v2_cloud": extra.get("cloud")}
    return pod


def validate_pod(pod, state, offer, prior_cost):
    rate = float(pod.get("costPerHr", "nan"))
    ram = float(pod.get("memoryInGb", "nan"))
    projected = (rate + STORAGE_RATE_RESERVE) / 3
    images = [pod[key] for key in ("image", "imageName") if pod.get(key) is not None]
    clouds = [pod[key] for key in ("cloud", "cloudType", "verified_v2_cloud") if pod.get(key) is not None]
    secure_machine = (pod.get("machine") or {}).get("secureCloud")
    secure_verified = bool(clouds or secure_machine is not None) and all(value == "SECURE" for value in clouds) and secure_machine in (None, True)
    gpu = pod.get("gpu") or {}
    if (pod.get("id") != load(IDENTITY)["pod_id"] or pod.get("name") != state["name"]
        or pod.get("computeType") not in (None, "CPU") or gpu.get("id") or gpu.get("count", 0) not in (None, 0)
        or not secure_verified or pod.get("cpuFlavorId") != offer["id"]
        or pod.get("vcpuCount") != 2 or not math.isfinite(ram) or ram < 4
        or not images or any(value != base.IMAGE for value in images) or pod.get("containerDiskInGb") != 12
        or type(pod.get("volumeInGb")) is not int or pod.get("volumeInGb") != 0 or pod.get("volumeMountPath") != "/workspace"
        or sorted(pod.get("ports") or []) != sorted(EXPECTED_PORTS) or pod.get("networkVolume")
        or not math.isfinite(rate) or not 0 < rate <= RATE_CAP
        or not math.isfinite(prior_cost) or prior_cost < preflight.PRIOR_HTTP_RESERVE
        or projected > PHASE_CAP or projected + prior_cost > CAMPAIGN_CAP):
        raise RuntimeError("created pod differs from approved identity/resources/budget")
    return {"rate_usd_per_hour": rate, "ram_gb": ram, "projected_20_min_cost_usd": projected,
            "pod_id": pod["id"], "cpu_flavor": offer["id"], "vcpu_count": 2,
            "prior_cost_bound_usd": prior_cost, "projected_aggregate_http_cost_usd": projected + prior_cost,
            "container_disk_gb": 12, "pod_volume_gb": 0, "ports": EXPECTED_PORTS,
            "image": images[0], "cloud_evidence": clouds, "machine_secure_cloud": secure_machine,
            "cpu_evidence": "matching assigned CPU flavor, vCPU/RAM, no GPU, any explicit computeType agrees"}


def bounded_response(response, cap):
    if int(response.headers.get("Content-Length", "0")) > cap:
        raise RuntimeError("response exceeds cap")
    data = bytearray()
    for chunk in response.iter_content(65536):
        if len(data) + len(chunk) > cap:
            raise RuntimeError("response exceeds cap")
        data.extend(chunk)
    return bytes(data)


def proxy_request(client, method, url, *, data=None, headers=None, cap=16384, timeout=10):
    with client.request(method, url, data=data, headers=headers, timeout=timeout, allow_redirects=False, stream=True) as response:
        if response.status_code not in (200, 202):
            raise RuntimeError("proxy HTTP " + str(response.status_code))
        return bounded_response(response, cap)


def validate_upload_status(value, size, digest):
    accepted = value.get("accepted_bytes")
    if (type(accepted) is not int or not 0 <= accepted <= size
        or value.get("expected_bytes") != size
        or accepted not in ({size} | set(range(0, size, CHUNK_BYTES)))
        or value.get("error") is not None
        or (value.get("uploaded") is True and (accepted != size or value.get("payload_sha256") != digest))
        or value.get("started") is True):
        raise RuntimeError("remote upload status violates chunk protocol")
    return accepted


def upload_payload(proxy, boot, raw, deadline):
    digest = hashlib.sha256(raw).hexdigest()

    def status():
        while True:
            try:
                value = json.loads(proxy_request(proxy, "GET", boot + "/upload", timeout=10))
                validate_upload_status(value, len(raw), digest)
                return value
            except RuntimeError as exc:
                if str(exc) != "proxy HTTP 404" or time.time() + 2 >= deadline:
                    raise
                time.sleep(2)

    current = status()
    while current["accepted_bytes"] < len(raw):
        if time.time() >= deadline:
            raise RuntimeError("bounded chunk upload deadline exceeded")
        offset = current["accepted_bytes"]
        chunk = raw[offset:offset + CHUNK_BYTES]
        expected_end = offset + len(chunk)
        headers = {
            "X-CM-Offset": str(offset),
            "X-CM-Chunk-SHA256": hashlib.sha256(chunk).hexdigest(),
        }
        attempts = 0
        while True:
            attempts += 1
            try:
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise RuntimeError("bounded chunk upload deadline exceeded")
                acknowledged = json.loads(proxy_request(
                    proxy, "POST", boot + "/payload", data=chunk, headers=headers,
                    timeout=(min(10, remaining), min(60, remaining)),
                ))
                accepted = validate_upload_status(acknowledged, len(raw), digest)
                if acknowledged.get("chunk_sha256") != headers["X-CM-Chunk-SHA256"] or accepted != expected_end:
                    raise RuntimeError("chunk acknowledgement mismatch")
                current = acknowledged
                break
            except (requests.ReadTimeout, requests.ConnectionError, RuntimeError) as exc:
                if isinstance(exc, RuntimeError) and str(exc) != "proxy HTTP 404":
                    raise
                reconcile_deadline = min(time.time() + 45, deadline)
                while time.time() < reconcile_deadline:
                    try:
                        observed = status()
                    except (requests.RequestException, RuntimeError) as status_exc:
                        if isinstance(status_exc, RuntimeError) and str(status_exc) != "proxy HTTP 404":
                            raise
                        time.sleep(1)
                        continue
                    accepted = observed["accepted_bytes"]
                    if accepted == expected_end:
                        current = observed
                        break
                    if accepted != offset:
                        raise RuntimeError("ambiguous noncontiguous chunk acceptance")
                    time.sleep(1)
                else:
                    if attempts < 3:
                        continue
                    raise RuntimeError("chunk acceptance could not be reconciled")
                break
    validation_deadline = min(time.time() + 60, deadline)
    while not current.get("uploaded") and time.time() < validation_deadline:
        time.sleep(1)
        current = status()
    if not current.get("uploaded"):
        raise RuntimeError("complete payload was not validated")
    return current


def execute_remote(pod_id, token, raw, created, record):
    boot = f"https://{pod_id}-8080.proxy.runpod.net"
    worker = f"https://{pod_id}-8081.proxy.runpod.net"
    with requests.Session() as proxy:
        proxy.trust_env = False
        proxy.headers["X-CM-Token"] = token
        proxy.headers["Content-Type"] = "application/octet-stream"
        for url in (boot, worker):
            while time.time() < created + 240:
                try:
                    health = json.loads(proxy_request(proxy, "GET", url + "/health", timeout=5))
                    if health.get("service") == "cm-native-scout-http" and health.get("ready") is True:
                        break
                except (requests.RequestException, RuntimeError, ValueError):
                    pass
                time.sleep(2)
            else:
                raise RuntimeError("HTTP bootstrap did not become ready within setup reserve")
        record["bootstrap_ready_utc"] = preflight.utc_now()
        accepted = upload_payload(proxy, boot, raw, created + 300)
        record["uploaded_source_files"] = 212
        record["uploaded_transport_bytes"] = len(raw)
        record["upload_chunks"] = math.ceil(len(raw) / CHUNK_BYTES)
        record["upload_payload_sha256"] = accepted["payload_sha256"]
        proxy_request(proxy, "POST", worker + "/run", data=b"", timeout=10)
        record["worker_started_utc"] = preflight.utc_now()
        observed = None
        while time.time() < created + CLEANUP_AT - 30:
            try:
                progress = json.loads(proxy_request(proxy, "GET", worker + "/progress", timeout=5))
            except requests.RequestException:
                time.sleep(2)
                continue
            signature = (progress.get("stage"), progress.get("done"), progress.get("error"))
            if signature != observed:
                append(OUT / "progress.jsonl", {"checked_utc": preflight.utc_now(), **progress})
                print(json.dumps({"stage": progress.get("stage"), "done": progress.get("done"), "error": progress.get("error")}), flush=True)
                observed = signature
            if progress.get("done"):
                record["remote_progress"] = progress
                return proxy_request(proxy, "GET", worker + "/results", cap=CAP, timeout=20).decode("utf-8")
            if time.time() >= created + 780 and progress.get("stage") not in ("focused-tests", "offline-gate", "p7-ir", "p7-relation"):
                raise RuntimeError("boot/install/build exceeded thirteen-minute setup deadline")
            time.sleep(2)
    raise RuntimeError("remote worker deadline exceeded")


def _p7_terminal_check(root, expected_cells, policy_id):
    summary = load(root / "summary.json")
    plan = load(root / "plan.json")
    verification = load(root.parent / (root.name + "-verify.stdout.txt"))
    rows = []
    for segment in sorted((root / "ledger").glob("segment-*.jsonl")):
        rows.extend(json.loads(line) for line in segment.read_text(encoding="utf-8").splitlines() if line.strip())
    terminals = [row for row in rows if row.get("status") == "ok" and isinstance(row.get("result"), dict)]
    ids = {row.get("cell_id") for row in terminals}
    resources_ok = True
    pids = []
    for row in terminals:
        result = row["result"]
        worker = result.get("worker") or {}
        resources = result.get("resources") or {}
        timings = result.get("timings_ns") or {}
        pid = (worker.get("environment") or {}).get("pid")
        if (
            result.get("status") != "ok"
            or result.get("outside_span_validation") is not True
            or result.get("performance_measurement") is not False
            or worker.get("status") != "ok"
            or worker.get("performance_measurement") is not False
            or worker.get("validation_in_timed_span") is not False
            or type(pid) is not int
            or type(timings.get("task_total_wall_ns")) is not int
            or timings["task_total_wall_ns"] <= 0
            or type(result.get("process_tree_peak_rss_bytes")) is not int
            or result["process_tree_peak_rss_bytes"] <= 0
            or resources.get("cleanup_verified") is not True
            or resources.get("streams_closed") is not True
            or resources.get("whole_tree_rss_measured") is not True
        ):
            resources_ok = False
        pids.append(pid)
    reconciliation = summary.get("reconciliation") or {}
    valid = (
        summary.get("status") == "passed"
        and summary.get("policy_id") == policy_id
        and summary.get("profile") == "functional"
        and summary.get("performance_measurement") is False
        and summary.get("performance_claim_permitted") is False
        and summary.get("source_unchanged") is True
        and reconciliation.get("complete") is True
        and reconciliation.get("planned_cells") == expected_cells
        and reconciliation.get("observed_cells") == expected_cells
        and reconciliation.get("statuses") == {"ok": expected_cells}
        and reconciliation.get("missing_cells") == []
        and reconciliation.get("unexpected_cells") == []
        and reconciliation.get("running_cells") == []
        and reconciliation.get("partial_tail_segments") == []
        and len(plan.get("cells") or []) == expected_cells
        and {row.get("cell_id") for row in plan.get("cells") or []} == ids
        and len(terminals) == expected_cells
        and len(pids) == len(set(pids)) == expected_cells
        and resources_ok
        and verification.get("verified") is True
        and verification.get("status") == "passed"
        and verification.get("performance_claim_permitted") is False
    )
    return valid, summary, verification, pids


def save_evidence(log):
    lines = log.splitlines()
    starts = [json.loads(line[9:]) for line in lines if line.startswith("CM_EVENT ") and '"kind": "evidence_start"' in line]
    if not starts:
        raise RuntimeError("remote evidence marker missing")
    plain_log = "\n".join(line for line in lines if not line.startswith("CM_EVIDENCE ")) + "\n"
    if len(plain_log.encode()) + int(starts[-1]["bytes"]) + int(starts[-1]["uncompressed_bytes"]) > CAP:
        raise RuntimeError("saved evidence aggregate exceeds 32 MiB")
    with (OUT / "container.log").open("x", encoding="utf-8") as stream:
        stream.write(plain_log)
    result = base.extract_evidence(lines)
    evidence_root = OUT / "evidence/run-output"
    validation = load(evidence_root / "REMOTE-VALIDATION.json")
    runtime = load(evidence_root / "RUNTIME.json")
    result.update({"validation": validation, "runtime_pod_id": runtime.get("runpod_pod_id"), "verified": False})
    if validation.get("status") != "complete":
        result["partial_evidence"] = {
            "remote_status": validation.get("status"), "remote_error": validation.get("error"),
            "validation_errors": validation.get("validation_errors", []),
            "junit_testcases": validation.get("junit_testcases"),
            "source_unchanged": validation.get("source_unchanged"),
        }
        return result
    try:
        offline = load(evidence_root / "offline-gate-verify.stdout.txt")
        ir_ok, _ir_summary, _ir_verify, ir_pids = _p7_terminal_check(evidence_root / "p7-ir", 16, "p7-ir")
        relation_ok, _relation_summary, _relation_verify, relation_pids = _p7_terminal_check(
            evidence_root / "p7-relation", 20, "p7-relation"
        )
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        result["partial_evidence"] = {"evidence_error_type": type(exc).__name__, "evidence_error": str(exc)[:500]}
        return result
    junit_metadata = validation.get("junit_metadata") or {}
    if (
        validation.get("junit_testcases") != {"tests": 32, "failures": 0, "errors": 0, "skipped": 0}
        or type(junit_metadata.get("tests")) is not int or junit_metadata.get("tests", 0) < 32
        or {key: junit_metadata.get(key) for key in ("failures", "errors", "skipped")}
        != {"failures": 0, "errors": 0, "skipped": 0}
        or validation.get("validation_errors") != []
        or validation.get("source_unchanged") is not True
        or validation.get("source_files") != 212
        or runtime.get("source_files") != 212
        or runtime.get("runpod_pod_id") != load(IDENTITY)["pod_id"]
        or len(runtime.get("affinity", [])) != 2
        or offline.get("package_verified") is not True
        or offline.get("performance_measurement") is not False
        or not ir_ok or not relation_ok
        or len(set(ir_pids + relation_pids)) != 36
    ):
        result["partial_evidence"] = {
            "remote_status": validation.get("status"),
            "validation_failure": "retrieved evidence did not satisfy frozen P7 functional-scout gates",
        }
        return result
    result["verified"] = True
    result["p7"] = {
        "focused_tests": 32, "policies": ["p7-ir", "p7-relation"],
        "cases_per_policy": 2, "blocks": 2, "cells": 36,
        "fresh_cell_processes": 36, "source_unchanged": True,
        "performance_measurement": False, "performance_ranking_permitted": False,
    }
    return result

def run():
    record = {"started_utc": preflight.utc_now(), "status": "preflight", "creation_attempted": False,
              "creation_uncertain": False, "pod_created": False, "uploaded_source_files": 0}
    state = None
    client = None
    try:
        authorization = require_authorization()
        record["authorization_record_sha256"] = hashlib.sha256(AUTHORIZATION_PATH.read_bytes()).hexdigest()
        record["authorization_recorded_utc"] = authorization.get("recorded_utc")
        prior = load(TRANSPORT / "GPU-FINAL-OUTCOME.json")
        if prior.get("final_reconciliation") != "owned_pod_absent_after_horizon":
            raise RuntimeError("prior uncertain request is not reconciled")
        ready = preflight.check()
        write(OUT / "PREFLIGHT.json", ready)
        if not ready["ready"]:
            raise RuntimeError("current account/resource/budget preflight failed")
        offer = ready["selected_offer"]
        manifest = load(MANIFEST_PATH)
        lock = load(base.LOCK_PATH)
        if (len(manifest["files"]) != 212 or manifest.get("bytes") != 24705826
                or manifest.get("authorization_status") != "pending"
                or len(lock["packages"]) != 13 or lock["source_builds_allowed"]):
            raise RuntimeError("frozen P7 functional-scout package mismatch")
        bundle = frozen_bundle(manifest)
        watchdog_process = arm_watchdog()
        client = preflight.session()
        if any(inventories(client).values()):
            raise RuntimeError("zero-pod baseline changed before creation")
        created = time.time()
        state = {"name": "cm-p7-functional-scout-" + uuid.uuid4().hex[:12], "created_epoch": created,
                 "cleanup_epoch": created + CLEANUP_AT, "horizon_epoch": created + HORIZON}
        raw = prepare_payload(bundle, manifest, created)
        token = secrets.token_urlsafe(32)
        body = create_payload(state["name"], offer, token, raw, created)
        write(OUT / "TRANSPORT-FREEZE.json", {
            "controller_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "authorization_sha256": hashlib.sha256(AUTHORIZATION_PATH.read_bytes()).hexdigest(),
            "proposal_sha256": hashlib.sha256(PROPOSAL_PATH.read_bytes()).hexdigest(),
            "bootstrap_sha256": hashlib.sha256(BOOTSTRAP_PATH.read_bytes()).hexdigest(),
            "preflight_sha256": hashlib.sha256(Path(preflight.__file__).read_bytes()).hexdigest(),
            "remote_program_sha256": hashlib.sha256(REMOTE_CODE_PATH.read_bytes()).hexdigest(),
            "preserved_remote_code_sha256": hashlib.sha256(base.REMOTE_CODE.encode()).hexdigest(),
            "source_bundle_sha256": hashlib.sha256(bundle).hexdigest(), "source_bundle_bytes": len(bundle),
            "source_files": 212, "source_bytes": sum(row["bytes"] for row in manifest["files"]),
            "transport_payload_sha256": hashlib.sha256(raw).hexdigest(), "transport_payload_bytes": len(raw),
            "manifest_sha256": hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest(),
            "wheel_lock_sha256": hashlib.sha256(base.LOCK_PATH.read_bytes()).hexdigest(),
            "create_json_bytes": len(json.dumps(body).encode()), "create_environment_variables": len(body["env"]),
            "create_command_bytes": len(body["dockerStartCmd"][0].encode()),
            "credentials_recorded_or_uploaded": False})
        write(STATE, state)
        confirm_watchdog(watchdog_process, state)
        record.update({"creation_attempted": True, "creation_uncertain": True,
                       "creation_request_utc": preflight.utc_now(), "creation_endpoint": preflight.V1 + "/pods",
                       "name": state["name"], "selected_cpu": offer["id"], "quoted_rate_usd_per_hour": offer["rate_usd_per_hour"]})
        print(json.dumps({"action": "create_one_cpu_pod_for_p7_functional_scout", "name": state["name"], "cpu": offer["id"], "rate": offer["rate_usd_per_hour"]}), flush=True)
        response = client.post(preflight.V1 + "/pods", json=body, timeout=(10, 50), allow_redirects=False)
        record["creation_http_status"] = response.status_code
        record["creation_response_headers"] = {key: response.headers[key][:400] for key in ("Date", "X-Request-Id", "X-Correlation-Id", "CF-Ray") if key in response.headers}
        if response.status_code not in (200, 201):
            record["creation_uncertain"] = not 400 <= response.status_code < 500
            try:
                detail = response.json()
                text = json.dumps({key: detail.get(key) for key in ("title", "detail", "error", "message") if detail.get(key)})
                for secret in (token, client.headers["Authorization"], client.headers["Authorization"].removeprefix("Bearer ")):
                    text = text.replace(secret, "<redacted>")
                record["provider_error"] = text[:1800]
            except (ValueError, TypeError):
                pass
            raise RuntimeError("pod creation failed HTTP " + str(response.status_code))
        pod = response.json()
        pod = pod.get("pod", pod)
        pod_id = pod.get("id")
        if not isinstance(pod_id, str) or not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
            raise RuntimeError("creation response has no valid pod ID")
        write(IDENTITY, {"pod_id": pod_id, "name": state["name"], "recorded_utc": preflight.utc_now(), "source": "this create response"})
        record.update({"pod_id": pod_id, "pod_created": True, "creation_uncertain": False})
        pod = actual_pod(client, pod_id)
        write(OUT / "POD-RESOURCE-CHECK.json", {
            "checked_utc": preflight.utc_now(), "response_fields": sorted(pod),
            "pod": {key: pod.get(key) for key in ("id", "name", "image", "imageName", "computeType", "cloudType", "cloud", "verified_v2_cloud",
                    "cpuFlavorId", "vcpuCount", "memoryInGb", "costPerHr", "containerDiskInGb", "volumeInGb", "volumeMountPath", "ports")},
            "machine_secure_cloud": (pod.get("machine") or {}).get("secureCloud"),
            "gpu": {key: (pod.get("gpu") or {}).get(key) for key in ("id", "count")},
            "network_volume_present": bool(pod.get("networkVolume"))})
        record["actual_resources"] = validate_pod(pod, state, offer, ready["prior_cost_bound_usd"])
        log = execute_remote(pod_id, token, raw, created, record)
        record["evidence"] = save_evidence(log)
        if record["evidence"].get("verified") is not True:
            raise RuntimeError("remote workload reported failure")
        record["status"] = "complete"
    except Exception as exc:
        record["status"] = "failed"
        record["error_type"] = type(exc).__name__
        # Only messages created here are retained; request/config exceptions may contain secrets.
        if type(exc) is RuntimeError:
            record["error"] = str(exc)
        if state is not None and not ABORT.exists():
            write(ABORT, {"requested_utc": preflight.utc_now(), "reason": record["error_type"]})
    finally:
        if state is not None and client is not None:
            try:
                cleanup = cleanup_owned(client, state, "controller")
                record["cleanup"] = cleanup
                if cleanup["owned_pod_absent"] and not record["creation_uncertain"]:
                    write(DONE, {"finished_utc": preflight.utc_now(), "owned_pod_absent_verified": True})
            except Exception as exc:
                record["cleanup_error_type"] = type(exc).__name__
        elif not DONE.exists():
            write(DONE, {"finished_utc": preflight.utc_now(), "no_create_request": True})
        record["finished_utc"] = preflight.utc_now()
        if state is not None:
            record["elapsed_since_create_s"] = time.time() - state["created_epoch"]
            actual_rate = record.get("actual_resources", {}).get("rate_usd_per_hour")
            record["estimated_compute_cost_usd"] = actual_rate * record["elapsed_since_create_s"] / 3600 if actual_rate is not None else None
        write(OUT / "RUN.json", record)
        if client is not None:
            client.close()
    print(json.dumps(record, indent=2), flush=True)
    return int(record["status"] != "complete" or not record.get("cleanup", {}).get("owned_pod_absent"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watchdog", action="store_true")
    args = parser.parse_args()
    if not args.watchdog:
        OUT.mkdir(exist_ok=False)
    with base.host_awake_guard("http-watchdog" if args.watchdog else "http-controller"):
        return watchdog() if args.watchdog else run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}), flush=True)
        raise SystemExit(2)


























