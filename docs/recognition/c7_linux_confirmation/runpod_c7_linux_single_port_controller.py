"""One separately authorized C7 confirmation through a single HTTPS port."""
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

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
LEGACY_HERE = (PROJECT_ROOT / "docs" / "audits" / "2026-08-25-cm-deep-performance" /
               "remaining-work" / "maximal-safe-20260827-192909" /
               "runpod-authorized-20260827-213104")
sys.path.insert(0, str(LEGACY_HERE))
import http_corpus_preflight_v4 as preflight

OUT = HERE / "runpod-c7-linux-single-port-execute-001"
PRIOR_FINAL = HERE / "RUNPOD_C7_LINUX_FINAL_VERIFICATION_20260830-031326-558392.json"
spec = importlib.util.spec_from_file_location(
    "preserved_cpu_smoke", LEGACY_HERE / "runpod_retry_cpu8_v1_controller.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def replace_remote_once(source, old, new):
    if source.count(old) != 1:
        raise RuntimeError("frozen remote-code transformation is not unique")
    return source.replace(old, new)


# Derive the approved confirmation command from the preserved remote program. Each
# mutation is exact and must occur once; the preserved source is never edited.
base.REMOTE_CODE = replace_remote_once(
    base.REMOTE_CODE,
    "    try:\n"
    "        import xml.etree.ElementTree as ET\n"
    "        xml = ET.parse(OUT / 'focused.xml').getroot()\n"
    "        suites = list(xml.iter('testsuite'))\n"
    "        validation['junit'] = {key: sum(int(row.get(key, '0')) for row in suites)\n"
    "                               for key in ('tests','failures','errors','skipped')}\n"
    "        summary = json.loads((OUT / 'memory/summary.json').read_text())\n"
    "        validation['memory_summary'] = {key: summary.get(key) for key in\n"
    "                                        ('rows','statuses','source_unchanged','production_estimator_accepted')}\n"
    "    except Exception as exc:\n"
    "        validation['validation_error'] = type(exc).__name__ + ': ' + str(exc)",
    "    try:\n"
    "        summary = json.loads((OUT / 'yosys-c7-linux-confirmation/summary.json').read_text())\n"
    "        validation['confirmation_summary'] = {key: summary.get(key) for key in\n"
    "            ('status', 'semantic_mismatches', 'criteria', 'scientific_scope')}\n"
    "    except Exception as exc:\n"
    "        validation['validation_error'] = type(exc).__name__ + ': ' + str(exc)",
)
base.REMOTE_CODE = replace_remote_once(
    base.REMOTE_CODE,
    "    run('pip-install', [sys.executable, '-m', 'pip', 'install', '--require-hashes',\n"
    "                        '--only-binary=:all:', '-r', 'runpod-requirements.lock'], min(300, remaining_setup))",
    "    requirement = OUT / 'numpy-requirement.txt'\n"
    "    requirement.write_text('numpy==2.3.2 --hash=sha256:938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f\\n')\n"
    "    run('pip-install', [sys.executable, '-m', 'pip', 'install', '--require-hashes',\n"
    "                        '--only-binary=:all:', '-r', str(requirement)], min(300, remaining_setup))",
)
base.REMOTE_CODE = replace_remote_once(
    base.REMOTE_CODE,
    "emit('stage', name='focused-tests')\n"
    "    run('focused-tests', [sys.executable, '-m', 'pytest', '-q', 'tests/test_output_budget.py',\n"
    "                          '-p', 'no:cacheprovider', '--basetemp', str(OUT/'pytest-temp'),\n"
    "                          '--junitxml', str(OUT/'focused.xml')], 120)\n"
    "    emit('stage', name='memory-study')\n"
    "    run('memory-study', [sys.executable, 'scripts/cm_memory_estimator_study.py',\n"
    "                         '--execution', 'runpod', '--supports', '6', '8', '--families',\n"
    "                         'mixed-chain', 'alternating-tree', '--contexts', 'none',\n"
    "                         '--schedules', 'cold', 'warm', '--repetitions', '3',\n"
    "                         '--output-dir', str(OUT/'memory')], 300)",
    "emit('stage', name='yosys-c7-linux-confirmation')\n"
    "    run('yosys-c7-linux-confirmation', [sys.executable, '-B',\n"
    "         'scripts/crse_yosys_source_anf_linux_confirmation.py', '--dataset',\n"
    "         'study/yosys-c7-dataset.json', '--output',\n"
    "         str(OUT/'yosys-c7-linux-confirmation'), '--repetitions', '9'], 420)",
)
base.OUT = OUT
BOOTSTRAP_PATH = HERE / "http_transport_bootstrap_c7_single_port.py"
MANIFEST_PATH = HERE / "c7_linux_upload_manifest.json"
PROPOSAL_PATH = HERE / "C7_SECOND_MACHINE_TIMING_SINGLE_PORT_PROTOCOL_2026_08_30.md"
AUTHORIZATION_PATH = HERE / "RUNPOD_C7_LINUX_SINGLE_PORT_AUTHORIZED_2026_08_30.json"
REQUIREMENTS_LOCK_PATH = LEGACY_HERE.parent / "runpod-requirements.lock"
NUMPY_REQUIREMENT = "numpy==2.3.2 --hash=sha256:938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f"
STATE = OUT / "controller-state.json"
IDENTITY = OUT / "POD-IDENTITY.json"
READY = OUT / "watchdog-ready.json"
STATE_ACK = OUT / "watchdog-state-ack.json"
DONE = OUT / "watchdog-done.json"
ABORT = OUT / "abort-requested.json"
HORIZON = 720
CLEANUP_AT = 600
CAP = 16 << 20
RATE_CAP = 0.25
PHASE_CAP = 0.05
CAMPAIGN_CAP = 0.05
STORAGE_RATE_RESERVE = 0.01
EXPECTED_PORTS = ["8080/http"]


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
        raise RuntimeError("exact C7 Linux-confirmation authorization record is absent")
    authorization = load(AUTHORIZATION_PATH)
    expected = {
        "schema": "crse-runpod-c7-linux-single-port-authorization/v1",
        "authorized": True,
        "one_create": True,
        "no_replacement": True,
        "source_files": 14,
        "source_bytes": 322080,
        "cases": 40,
        "repetitions": 9,
        "methods": 6,
        "https_ports": ["8080/http"],
        "vcpu_count": 2,
        "minimum_ram_gb": 4,
        "container_disk_gb": 12,
        "pod_volume_gb": 0,
        "network_volume": False,
        "cleanup_seconds": 600,
        "reconciliation_seconds": 720,
        "rate_cap_usd_per_hour": 0.25,
        "total_cost_cap_usd": 0.05,
    }
    if any(authorization.get(key) != value for key, value in expected.items()):
        raise RuntimeError("C7 Linux-confirmation authorization scope mismatch")
    if authorization.get("proposal_sha256") != hashlib.sha256(PROPOSAL_PATH.read_bytes()).hexdigest():
        raise RuntimeError("authorized proposal hash mismatch")
    if authorization.get("upload_manifest_sha256") != hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest():
        raise RuntimeError("authorized upload manifest hash mismatch")
    return authorization


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
        or not re.fullmatch(r"cm-c7-linux-[a-f0-9]{12}", state["name"])
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
                               "CM_SETUP_DEADLINE": str(created + 300)}}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(raw) > 1 << 20:
        raise RuntimeError("transport payload exceeds one MiB")
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


def validate_pod(pod, state, offer):
    rate = float(pod.get("costPerHr", "nan"))
    ram = float(pod.get("memoryInGb", "nan"))
    projected = (rate + STORAGE_RATE_RESERVE) * CLEANUP_AT / 3600
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
        or projected > PHASE_CAP or projected > CAMPAIGN_CAP):
        raise RuntimeError("created pod differs from approved identity/resources/budget")
    return {"rate_usd_per_hour": rate, "ram_gb": ram, "projected_10_min_cost_usd": projected,
            "pod_id": pod["id"], "cpu_flavor": offer["id"], "vcpu_count": 2,
            "total_cost_cap_usd": CAMPAIGN_CAP,
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


def proxy_request(client, method, url, *, data=None, cap=16384, timeout=10):
    with client.request(method, url, data=data, timeout=timeout, allow_redirects=False, stream=True) as response:
        if response.status_code not in (200, 202):
            raise RuntimeError("proxy HTTP " + str(response.status_code))
        return bounded_response(response, cap)


def execute_remote(pod_id, token, raw, created, record):
    endpoint = f"https://{pod_id}-8080.proxy.runpod.net"
    with requests.Session() as proxy:
        proxy.trust_env = False
        proxy.headers["X-CM-Token"] = token
        proxy.headers["Content-Type"] = "application/octet-stream"
        while time.time() < created + 240:
            try:
                health = json.loads(proxy_request(proxy, "GET", endpoint + "/health", timeout=5))
                if health.get("service") == "cm-memory-http" and health.get("ready") is True:
                    break
            except (requests.RequestException, RuntimeError, ValueError):
                pass
            time.sleep(2)
        else:
            raise RuntimeError("HTTP bootstrap did not become ready within setup reserve")
        record["bootstrap_ready_utc"] = preflight.utc_now()
        accepted = json.loads(proxy_request(proxy, "POST", endpoint + "/payload", data=raw, timeout=20))
        if accepted.get("accepted_sha256") != hashlib.sha256(raw).hexdigest():
            raise RuntimeError("upload acknowledgement hash mismatch")
        record["uploaded_source_files"] = 14
        record["uploaded_transport_bytes"] = len(raw)
        proxy_request(proxy, "POST", endpoint + "/run", data=b"", timeout=10)
        record["worker_started_utc"] = preflight.utc_now()
        observed = None
        while time.time() < created + CLEANUP_AT - 30:
            try:
                progress = json.loads(proxy_request(proxy, "GET", endpoint + "/progress", timeout=5))
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
                return proxy_request(proxy, "GET", endpoint + "/results", cap=CAP, timeout=20).decode("utf-8")
            if time.time() >= created + 300 and progress.get("stage") != "yosys-c7-linux-confirmation":
                raise RuntimeError("boot/install exceeded five-minute setup deadline")
            time.sleep(2)
    raise RuntimeError("remote worker deadline exceeded")


def save_evidence(log):
    lines = log.splitlines()
    starts = [json.loads(line[9:]) for line in lines if line.startswith("CM_EVENT ") and '"kind": "evidence_start"' in line]
    if not starts:
        raise RuntimeError("remote evidence marker missing")
    plain_log = "\n".join(line for line in lines if not line.startswith("CM_EVIDENCE ")) + "\n"
    if len(plain_log.encode()) + int(starts[-1]["bytes"]) + int(starts[-1]["uncompressed_bytes"]) > CAP:
        raise RuntimeError("saved evidence aggregate exceeds 16 MiB")
    with (OUT / "container.log").open("x", encoding="utf-8") as stream:
        stream.write(plain_log)
    result = base.extract_evidence(lines)
    evidence_root = OUT / "evidence/run-output"
    validation = load(evidence_root / "REMOTE-VALIDATION.json")
    runtime = load(evidence_root / "RUNTIME.json")
    dependencies = load(evidence_root / "DEPENDENCIES.json")
    study = evidence_root / "yosys-c7-linux-confirmation"
    summary_path = study / "summary.json"
    measurements_path = study / "measurements.jsonl"
    per_case_path = study / "per_case.json"
    artifacts = load(study / "manifest.json")
    summary = load(summary_path)
    per_case = load(per_case_path)
    rows = [json.loads(line) for line in measurements_path.read_text(encoding="utf-8").splitlines()]
    measured_hashes = {
        "measurements.jsonl": hashlib.sha256(measurements_path.read_bytes()).hexdigest(),
        "per_case.json": hashlib.sha256(per_case_path.read_bytes()).hexdigest(),
        "summary.json": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
    }
    methods = {"set_source_anf", "packed_source_anf", "cached_packed_cold",
               "cached_packed_warm", "bitset_truth_vector_anf", "numpy_truth_vector_anf"}
    expected_keys = {(repetition, method, split, case["case_id"])
                     for repetition in range(9) for method in methods
                     for split in ("sealed_a", "sealed_b")
                     for case in load(PROJECT_ROOT / "docs" / "recognition" / "runs" /
                                      "yosys-source-anf-confirmation-20260830-002" / "dataset.json")
                     if case["split"] == split}
    observed_keys = {(row.get("repetition"), row.get("method"), row.get("split"), row.get("case_id"))
                     for row in rows}
    confirmation = validation.get("confirmation_summary", {})
    config = summary.get("config", {})
    if (validation.get("status") != "complete" or validation.get("error") is not None
        or confirmation.get("status") != "complete" or confirmation.get("semantic_mismatches") != 0
        or confirmation.get("criteria") != summary.get("criteria")
        or summary.get("schema") != "crse-yosys-source-anf-linux-confirmation/v1"
        or summary.get("status") != "complete" or summary.get("semantic_mismatches") != 0
        or summary.get("scientific_scope") != "second-machine timing of the unchanged sealed C7 Yosys source-ANF dataset"
        or config.get("cases") != 40 or config.get("repetitions") != 9
        or config.get("cpu_threads") != 1 or config.get("cache_capacity") != 1024
        or set(config.get("methods", [])) != methods
        or summary.get("input") != {"dataset_sha256": "3ca1ae22fd79bac68c37e78fe497701cb100713b0077130e5263cb1f66145864",
                                    "training_use": False,
                                    "source_commit": "52ff6fa991f2ab509618d8aaad02f307aac78848"}
        or summary.get("criteria", {}).get("exact") is not True
        or summary.get("runtime", {}).get("python") != "3.13.15"
        or summary.get("runtime", {}).get("numpy") != "2.3.2"
        or artifacts.get("schema") != "crse-yosys-source-anf-linux-artifacts/v1"
        or artifacts.get("files_sha256") != measured_hashes
        or len(rows) != 2160 or observed_keys != expected_keys
        or len(per_case) != 240
        or any(row.get("schema") != "crse-yosys-source-anf-linux-measurement/v1"
               or row.get("predicted") != row.get("label")
               or row.get("canonical_partition_match") is not True
               or row.get("semantic_mismatch") is not False
               or any(type(row.get(field)) is not int or row[field] < 0
                      for field in ("signature_ns", "exact_check_ns", "total_ns")) for row in rows)
        or dependencies.get("numpy") != "2.3.2"
        or runtime.get("source_files") != 14 or runtime.get("runpod_pod_id") != load(IDENTITY)["pod_id"]
        or runtime.get("image_tag") != base.IMAGE_TAG or runtime.get("image_amd64_digest") != base.IMAGE_AMD64_DIGEST):
        raise RuntimeError("retrieved evidence did not satisfy frozen C7 Linux-confirmation gates")
    result["validation"] = validation
    result["runtime_pod_id"] = runtime["runpod_pod_id"]
    result["c7_linux_confirmation"] = {
        "cases": 40,
        "repetitions": 9,
        "methods": 6,
        "measurement_rows": len(rows),
        "per_case_rows": len(per_case),
        "semantic_mismatches": 0,
        "criteria": summary.get("criteria"),
        "method_summary": summary.get("method_summary"),
    }
    return result


def run():
    record = {"started_utc": preflight.utc_now(), "status": "preflight", "creation_attempted": False,
              "creation_uncertain": False, "pod_created": False, "uploaded_source_files": 0}
    state = None
    client = None
    try:
        prior_c7 = load(PRIOR_FINAL)
        if (prior_c7.get("status") != "safe_failure_reconciled"
                or prior_c7.get("complete") is not True
                or prior_c7.get("scientific_confirmation_complete") is not False
                or prior_c7.get("create_requests_this_authorization") != 1
                or prior_c7.get("automatic_replacement_queued") is not False
                or prior_c7.get("owned_pod_absent_verified") is not True
                or prior_c7.get("uploaded_source_files") != 0):
            raise RuntimeError("prior C7 authorization is not safely reconciled")
        authorization = require_authorization()
        record["authorization_record_sha256"] = hashlib.sha256(AUTHORIZATION_PATH.read_bytes()).hexdigest()
        record["authorization_recorded_utc"] = authorization.get("recorded_utc")
        prior = load(PROJECT_ROOT / "docs" / "recognition" / "linux_confirmation" /
                     "RUNPOD_LINUX_ONE_PASS_FINAL_VERIFICATION_20260829-092727-102016.json")
        if (prior.get("complete") is not True or prior.get("pod_id") != "ek7697wrnxuawo"
                or prior.get("owned_pod_absent_verified") is not True
                or prior.get("create_requests_this_authorization") != 1
                or prior.get("automatic_replacement_queued") is not False):
            raise RuntimeError("prior Runpod request is not reconciled")
        ready = preflight.check()
        offer = ready.get("selected_offer")
        rate = float(offer["rate_usd_per_hour"]) if offer else float("nan")
        projected = (rate + STORAGE_RATE_RESERVE) * CLEANUP_AT / 3600
        ready["linux_confirmation_budget"] = {
            "rate_usd_per_hour": rate,
            "projected_10_minute_cost_usd": projected,
            "total_cost_cap_usd": CAMPAIGN_CAP,
            "ready": bool(math.isfinite(rate) and 0 < rate <= RATE_CAP and projected <= CAMPAIGN_CAP),
        }
        write(OUT / "PREFLIGHT.json", ready)
        if (not ready["ready"] or not ready["linux_confirmation_budget"]["ready"]
                or any(ready["inventories"].values())):
            raise RuntimeError("current account/resource/budget preflight failed")
        manifest = load(MANIFEST_PATH)
        expected_command = ["python", "-B", "scripts/crse_yosys_source_anf_linux_confirmation.py",
            "--dataset", "study/yosys-c7-dataset.json", "--output",
            "run-output/yosys-c7-linux-confirmation", "--repetitions", "9"]
        lock_lines = REQUIREMENTS_LOCK_PATH.read_text(encoding="utf-8").splitlines()
        if (manifest.get("schema") != "crse-c7-linux-confirmation-upload-manifest/v1"
                or len(manifest["files"]) != 14 or manifest.get("file_count") != 14
                or manifest.get("bytes") != 322080 or manifest.get("authorization_status") != "pending"
                or manifest.get("command") != expected_command or manifest.get("network_during_workload") is not False
                or manifest.get("runtime") != {"architecture": "amd64", "image": base.IMAGE,
                    "numpy": "2.3.2", "python": "3.13.15", "numpy_requirement": NUMPY_REQUIREMENT}
                or NUMPY_REQUIREMENT not in lock_lines):
            raise RuntimeError("frozen C7 Linux-confirmation package mismatch")
        bundle = base.make_bundle(manifest)
        watchdog_process = arm_watchdog()
        client = preflight.session()
        if any(inventories(client).values()):
            raise RuntimeError("zero-pod baseline changed before creation")
        created = time.time()
        state = {"name": "cm-c7-linux-" + uuid.uuid4().hex[:12], "created_epoch": created,
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
            "preserved_remote_code_sha256": hashlib.sha256(base.REMOTE_CODE.encode()).hexdigest(),
            "source_bundle_sha256": hashlib.sha256(bundle).hexdigest(), "source_bundle_bytes": len(bundle),
            "source_files": 14, "source_bytes": sum(row["bytes"] for row in manifest["files"]),
            "transport_payload_sha256": hashlib.sha256(raw).hexdigest(), "transport_payload_bytes": len(raw),
            "manifest_sha256": hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest(),
            "requirements_lock_sha256": hashlib.sha256(REQUIREMENTS_LOCK_PATH.read_bytes()).hexdigest(),
            "numpy_requirement_sha256": hashlib.sha256((NUMPY_REQUIREMENT + "\n").encode()).hexdigest(),
            "create_json_bytes": len(json.dumps(body).encode()), "create_environment_variables": len(body["env"]),
            "create_command_bytes": len(body["dockerStartCmd"][0].encode()),
            "credentials_recorded_or_uploaded": False})
        write(STATE, state)
        confirm_watchdog(watchdog_process, state)
        record.update({"creation_attempted": True, "creation_uncertain": True,
                       "creation_request_utc": preflight.utc_now(), "creation_endpoint": preflight.V1 + "/pods",
                       "name": state["name"], "selected_cpu": offer["id"], "quoted_rate_usd_per_hour": offer["rate_usd_per_hour"]})
        print(json.dumps({"action": "create_one_cpu_pod", "name": state["name"], "cpu": offer["id"], "rate": offer["rate_usd_per_hour"]}), flush=True)
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
        record["actual_resources"] = validate_pod(pod, state, offer)
        log = execute_remote(pod_id, token, raw, created, record)
        record["evidence"] = save_evidence(log)
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
