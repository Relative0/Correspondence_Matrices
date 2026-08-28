"""Fail-closed controller for CM-MEMORY-SMOKE-20260827-192909 only."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
import shlex
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time
import uuid
import zipfile

import requests


ROOT = Path(__file__).resolve().parents[6]
CAMPAIGN = ROOT / "docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909"
OUT = Path(__file__).resolve().parent / "retry-v2"
ENV_PATH = CAMPAIGN / ".env.runpod.local"
MANIFEST_PATH = CAMPAIGN / "RUNPOD-UPLOAD-MANIFEST-FINAL.json"
LOCK_PATH = CAMPAIGN / "RUNPOD-WHEEL-LOCK.json"
REST_V1 = "https://rest.runpod.io/v1"
REST_V2 = "https://api.runpod.io/v2"
PACKAGE_ID = "CM-MEMORY-SMOKE-20260827-192909"
IMAGE_TAG = "python:3.13.15-slim-bookworm"
IMAGE_AMD64_DIGEST = "sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129"
IMAGE = f"{IMAGE_TAG}@{IMAGE_AMD64_DIGEST}"
CPU_ID = "cpu3c"
VCPU = 2
RAM_GB = 4
CONTAINER_DISK_GB = 10
RATE_CAP = 0.20
TOTAL_CAP = 0.10
HARD_LIFETIME_S = 20 * 60
CONTROLLER_DEADLINE_S = 18 * 60
EVIDENCE_CAP = 16 << 20
STATE = OUT / "controller-state.json"
POD_IDENTITY = OUT / "POD-IDENTITY.json"
WATCHDOG_READY = OUT / "watchdog-ready.json"
WATCHDOG_DONE = OUT / "watchdog-done"
RUN_RECORD = OUT / "RUN.json"


REMOTE_CODE = r'''
import base64, hashlib, importlib.metadata, io, json, os, platform, signal, subprocess, sys, sysconfig, time, zipfile
from pathlib import Path, PurePosixPath

ROOT = Path('/workspace/cm-memory-smoke')
OUT = ROOT / 'run-output'
CAP = 16 << 20

def emit(kind, **fields):
    print('CM_EVENT ' + json.dumps({'kind': kind, **fields}, sort_keys=True), flush=True)

def run(name, command, timeout):
    started = time.monotonic()
    stdout = OUT / (name + '.stdout.txt')
    stderr = OUT / (name + '.stderr.txt')
    with stdout.open('xb') as out, stderr.open('xb') as err:
        proc = subprocess.Popen(command, cwd=ROOT, stdout=out, stderr=err, start_new_session=True,
                                env={**os.environ, 'OPENBLAS_NUM_THREADS':'1', 'OMP_NUM_THREADS':'1',
                                     'MKL_NUM_THREADS':'1', 'NUMEXPR_NUM_THREADS':'1'})
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise RuntimeError(name + ' timed out')
    record = {'name': name, 'command': command, 'returncode': code,
              'wall_s': time.monotonic() - started,
              'stdout_sha256': hashlib.sha256(stdout.read_bytes()).hexdigest(),
              'stderr_sha256': hashlib.sha256(stderr.read_bytes()).hexdigest()}
    if code:
        record['stderr_tail'] = stderr.read_text(errors='replace')[-3000:]
    with (OUT / (name + '.json')).open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    if code:
        raise RuntimeError(name + ' failed with exit code ' + str(code))
    return record

def evidence(status, error=None):
    validation = {'status': status, 'error': error, 'python': sys.version,
                  'platform': platform.platform(), 'machine': platform.machine(),
                  'logical_cpus': os.cpu_count(), 'pid': os.getpid(),
                  'blas_threads': 1}
    try:
        import xml.etree.ElementTree as ET
        xml = ET.parse(OUT / 'focused.xml').getroot()
        suites = list(xml.iter('testsuite'))
        validation['junit'] = {key: sum(int(row.get(key, '0')) for row in suites)
                               for key in ('tests','failures','errors','skipped')}
        summary = json.loads((OUT / 'memory/summary.json').read_text())
        validation['memory_summary'] = {key: summary.get(key) for key in
                                        ('rows','statuses','source_unchanged','production_estimator_accepted')}
    except Exception as exc:
        validation['validation_error'] = type(exc).__name__ + ': ' + str(exc)
    with (OUT / 'REMOTE-VALIDATION.json').open('x') as stream:
        json.dump(validation, stream, indent=2, sort_keys=True)
        stream.write('\n')
    archive = io.BytesIO()
    total = 0
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(OUT.rglob('*')):
            if not path.is_file() or 'pytest-temp' in path.parts:
                continue
            data = path.read_bytes()
            total += len(data)
            if total > CAP:
                raise RuntimeError('evidence file total exceeds 16 MiB cap')
            zf.writestr(path.relative_to(ROOT).as_posix(), data)
    data = archive.getvalue()
    if len(data) > CAP:
        raise RuntimeError('evidence archive exceeds 16 MiB cap')
    encoded = base64.b64encode(data).decode('ascii')
    digest = hashlib.sha256(data).hexdigest()
    chunk = 3072
    emit('evidence_start', bytes=len(data), sha256=digest,
         chunks=(len(encoded) + chunk - 1) // chunk, uncompressed_bytes=total)
    for index in range(0, len(encoded), chunk):
        print('CM_EVIDENCE %06d %s' % (index // chunk, encoded[index:index+chunk]), flush=True)
    emit('evidence_end', sha256=digest)

OUT.mkdir(parents=True, exist_ok=False)
status = 'failed'
error = None
try:
    bundle = base64.b64decode(''.join(os.environ.pop(name) for name in sorted(os.environ)
                                     if name.startswith('CM_BUNDLE_') and name[10:].isdigit()))
    expected_bundle = os.environ.pop('CM_BUNDLE_SHA256')
    if hashlib.sha256(bundle).hexdigest() != expected_bundle:
        raise RuntimeError('uploaded source archive hash mismatch')
    manifest = json.loads(base64.b64decode(os.environ.pop('CM_UPLOAD_MANIFEST')).decode())
    expected = {row['target']: row for row in manifest['files']}
    with zipfile.ZipFile(io.BytesIO(bundle)) as zf:
        names = zf.namelist()
        if set(names) != set(expected) or len(names) != len(set(names)):
            raise RuntimeError('uploaded source archive member mismatch')
        for name in names:
            pure = PurePosixPath(name)
            if pure.is_absolute() or '..' in pure.parts:
                raise RuntimeError('unsafe uploaded source target')
            data = zf.read(name)
            row = expected[name]
            if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
                raise RuntimeError('uploaded source member hash mismatch: ' + name)
            target = ROOT / pure
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(data)
    runtime = {'python': sys.version, 'platform': platform.platform(), 'machine': platform.machine(),
               'logical_cpus': os.cpu_count(), 'image_tag': os.environ.pop('CM_IMAGE_TAG'),
               'image_amd64_digest': os.environ.pop('CM_IMAGE_DIGEST'),
               'bundle_sha256': expected_bundle, 'source_files': len(expected),
               'runpod_pod_id': os.environ.get('RUNPOD_POD_ID'),
               'affinity': sorted(os.sched_getaffinity(0)),
               'gil_disabled': sysconfig.get_config_var('Py_GIL_DISABLED')}
    cpu = Path('/proc/cpuinfo').read_text()
    runtime['cpu_model'] = next((line.partition(':')[2].strip() for line in cpu.splitlines() if line.startswith('model name')), None)
    runtime['cpu_flags'] = next((line.partition(':')[2].strip() for line in cpu.splitlines() if line.startswith('flags')), None)
    for name, path in [('cgroup_memory_max','/sys/fs/cgroup/memory.max'), ('cgroup_cpu_max','/sys/fs/cgroup/cpu.max')]:
        runtime[name] = Path(path).read_text().strip() if Path(path).exists() else None
    if (sys.version_info[:3] != (3,13,15) or platform.machine().lower() not in ('x86_64','amd64')
            or runtime['gil_disabled'] or not runtime['runpod_pod_id']):
        raise RuntimeError('runtime identity mismatch')
    with (OUT / 'RUNTIME.json').open('x') as stream:
        json.dump(runtime, stream, indent=2, sort_keys=True)
        stream.write('\n')
    emit('stage', name='install')
    setup_deadline = float(os.environ.pop('CM_SETUP_DEADLINE'))
    remaining_setup = setup_deadline - time.time()
    if remaining_setup <= 0:
        raise RuntimeError('boot consumed setup deadline')
    run('pip-install', [sys.executable, '-m', 'pip', 'install', '--require-hashes',
                        '--only-binary=:all:', '-r', 'runpod-requirements.lock'], min(300, remaining_setup))
    remaining_setup = setup_deadline - time.time()
    if remaining_setup <= 0:
        raise RuntimeError('install consumed setup deadline')
    run('pip-check', [sys.executable, '-m', 'pip', 'check'], min(30, remaining_setup))
    with (OUT / 'DEPENDENCIES.json').open('x') as stream:
        json.dump({dist.metadata['Name']: dist.version for dist in importlib.metadata.distributions()}, stream, indent=2, sort_keys=True)
        stream.write('\n')
    emit('stage', name='focused-tests')
    run('focused-tests', [sys.executable, '-m', 'pytest', '-q', 'tests/test_output_budget.py',
                          '-p', 'no:cacheprovider', '--basetemp', str(OUT/'pytest-temp'),
                          '--junitxml', str(OUT/'focused.xml')], 120)
    emit('stage', name='memory-study')
    run('memory-study', [sys.executable, 'scripts/cm_memory_estimator_study.py',
                         '--execution', 'runpod', '--supports', '6', '8', '--families',
                         'mixed-chain', 'alternating-tree', '--contexts', 'none',
                         '--schedules', 'cold', 'warm', '--repetitions', '3',
                         '--output-dir', str(OUT/'memory')], 300)
    status = 'complete'
except Exception as exc:
    error = type(exc).__name__ + ': ' + str(exc)
    emit('failure', error=error)
finally:
    try:
        evidence(status, error)
    except Exception as exc:
        emit('evidence_failure', error=type(exc).__name__ + ': ' + str(exc))
    emit('done', status=status)
'''


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_exclusive(path: Path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def read_key():
    key = None
    for raw in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
        name, separator, value = raw.strip().removeprefix("export ").partition("=")
        if separator and name.strip() == "RUNPOD_API_KEY":
            if key is not None:
                raise RuntimeError("duplicate RUNPOD_API_KEY")
            key = value.strip().strip('"').strip("'")
    if not key or any(character.isspace() for character in key):
        raise RuntimeError("RUNPOD_API_KEY missing or malformed")
    return key


def session():
    result = requests.Session()
    result.headers["Authorization"] = "Bearer " + read_key()
    return result


def safe_pods(client):
    response = client.get(REST_V1 + "/pods", timeout=10, allow_redirects=False)
    response.raise_for_status()
    value = response.json()
    pods = value if isinstance(value, list) else value.get("pods")
    if not isinstance(pods, list):
        raise RuntimeError("unexpected pod inventory schema")
    fields = ("id", "name", "desiredStatus", "computeType", "costPerHr", "vcpuCount",
              "memoryInGb", "cpuFlavorId", "containerDiskInGb", "volumeInGb")
    return [{key: pod.get(key) for key in fields if key in pod} for pod in pods]


def catalog_offer(client):
    response = client.get(REST_V2 + "/catalog/cpus", params={"include": "AVAILABILITY",
                          "product": "POD", "vcpuCount": VCPU}, timeout=30, allow_redirects=False)
    response.raise_for_status()
    offers = response.json().get("cpus", [])
    offer = next((row for row in offers if row.get("id") == CPU_ID), None)
    if not offer or offer.get("availability") == "NONE":
        raise RuntimeError("approved CPU flavor is unavailable")
    rate = float(offer["price"]["securePerVcpu"]) * VCPU
    ram = float(offer["ramGbPerVcpu"]) * VCPU
    if rate > RATE_CAP or ram < RAM_GB:
        raise RuntimeError("live CPU offer exceeds approved resource caps")
    return offer, rate, ram


def make_bundle(manifest):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for row in manifest["files"]:
            data = (ROOT / row["source"]).read_bytes()
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise RuntimeError("approved upload hash mismatch: " + row["source"])
            zf.writestr(row["target"], data)
    return archive.getvalue()


def terminate(client, pod_id):
    attempts = []
    for url in (REST_V2 + "/pods/" + pod_id, REST_V1 + "/pods/" + pod_id):
        try:
            response = client.delete(url, timeout=10, allow_redirects=False)
            attempts.append({"url": url.rsplit("/", 1)[0] + "/<owned-pod>", "status": response.status_code})
            if response.status_code in (200, 202, 204, 404):
                break
        except requests.RequestException as exc:
            attempts.append({"url": url.rsplit("/", 1)[0] + "/<owned-pod>", "error": type(exc).__name__})
    for _ in range(6):
        try:
            if all(row.get("id") != pod_id for row in safe_pods(client)):
                return True, attempts
        except requests.RequestException:
            pass
        time.sleep(3)
    return False, attempts


def parse_sse(response, event_ids, lines, deadline, setup_deadline):
    event_id = None
    for raw in response.iter_lines(decode_unicode=True):
        if time.time() >= deadline:
            return
        setup_complete = any('"name": "focused-tests"' in line for line in lines)
        if time.time() >= setup_deadline and not setup_complete:
            raise RuntimeError("boot/install exceeded the five-minute setup deadline")
        if not raw:
            event_id = None
        elif raw.startswith("id:"):
            event_id = raw[3:].strip()
        elif raw.startswith("data:") and (event_id is None or event_id not in event_ids):
            payload = json.loads(raw[5:].strip())
            if payload.get("source") == "container":
                line = payload.get("line", "")
                event_ids.add(event_id or (payload.get("ts"), line))
                lines.append(line)
                if sum(len(item) for item in lines) > EVIDENCE_CAP:
                    raise RuntimeError("container log collection exceeded cap")
                if line.startswith("CM_EVENT ") and json.loads(line[len("CM_EVENT "):]).get("kind") == "done":
                    return


def collect_logs(client, pod_id, deadline, setup_deadline, lines=None):
    event_ids, lines = set(), [] if lines is None else lines
    events = []
    while time.time() < deadline:
        try:
            response = client.get(REST_V2 + f"/pods/{pod_id}/logs", params={"source": "container", "tail": 5000},
                                  timeout=(3, 3), stream=True, allow_redirects=False)
            if response.status_code == 200:
                response.encoding = "utf-8"
                try:
                    parse_sse(response, event_ids, lines, deadline, setup_deadline)
                finally:
                    response.close()
            else:
                response.close()
                if response.status_code in (400, 401, 403):
                    raise RuntimeError("pod logs unavailable HTTP " + str(response.status_code))
        except (requests.RequestException, ValueError, json.JSONDecodeError):
            pass
        with (OUT / "container-events.jsonl").open("a", encoding="utf-8") as stream:
            for line in lines:
                if line.startswith("CM_EVENT "):
                    stream.write(line[len("CM_EVENT "):] + "\n")
        events = []
        for line in lines:
            if line.startswith("CM_EVENT "):
                try:
                    events.append(json.loads(line[len("CM_EVENT "):]))
                except json.JSONDecodeError:
                    pass
        if any(row.get("kind") == "done" for row in events):
            return lines, events
        time.sleep(2)
    return lines, events


def extract_evidence(lines):
    starts = [json.loads(line[len("CM_EVENT "):]) for line in lines
              if line.startswith("CM_EVENT ") and '"kind": "evidence_start"' in line]
    ends = [json.loads(line[len("CM_EVENT "):]) for line in lines
            if line.startswith("CM_EVENT ") and '"kind": "evidence_end"' in line]
    chunks = {}
    for line in lines:
        if line.startswith("CM_EVIDENCE "):
            _, number, data = line.split(" ", 2)
            chunks[int(number)] = data
    if not starts or not ends:
        raise RuntimeError("complete evidence markers absent")
    start = starts[-1]
    if set(chunks) != set(range(start["chunks"])):
        raise RuntimeError("evidence chunks incomplete")
    data = base64.b64decode("".join(chunks[index] for index in range(start["chunks"])), validate=True)
    if len(data) != start["bytes"] or len(data) > EVIDENCE_CAP or hashlib.sha256(data).hexdigest() != start["sha256"]:
        raise RuntimeError("evidence archive integrity failure")
    archive = OUT / "evidence.zip"
    with archive.open("xb") as stream:
        stream.write(data)
    evidence = OUT / "evidence"
    evidence.mkdir(exist_ok=False)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        if sum(info.file_size for info in zf.infolist()) + len(data) > EVIDENCE_CAP:
            raise RuntimeError("collected and extracted evidence exceeds cap")
        for info in zf.infolist():
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or ".." in pure.parts:
                raise RuntimeError("unsafe evidence path")
            target = evidence / pure
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(zf.read(info))
    return {"bytes": len(data), "sha256": start["sha256"], "files": len(zf.infolist())}


def watchdog():
    ready = {"ready_utc": utc_now(), "pid": os.getpid(), "deadline_epoch": time.time() + HARD_LIFETIME_S}
    write_exclusive(WATCHDOG_READY, ready)
    pod_id = None
    deadline = ready["deadline_epoch"]
    while time.time() < deadline:
        if WATCHDOG_DONE.exists():
            return 0
        if STATE.exists():
            try:
                value = json.loads(STATE.read_text())
            except (OSError, ValueError):
                time.sleep(1)
                continue
            deadline = min(deadline, float(value.get("hard_deadline_epoch", deadline)))
        if POD_IDENTITY.exists():
            try:
                pod_id = json.loads(POD_IDENTITY.read_text())["pod_id"]
            except (OSError, ValueError, KeyError):
                pass
        time.sleep(3)
    result = {"activated_utc": utc_now(), "pod_id_known": bool(pod_id), "terminated": False}
    client = session()
    if not pod_id and STATE.exists():
        name = json.loads(STATE.read_text())["name"]
        matching = [row for row in safe_pods(client) if row.get("name") == name]
        if len(matching) == 1:
            pod_id = matching[0]["id"]
    if pod_id:
        result["terminated"], result["termination_attempts"] = terminate(client, pod_id)
    write_exclusive(OUT / "WATCHDOG-RESULT.json", result)
    return int(not result["terminated"])


def run():
    if RUN_RECORD.exists() or STATE.exists() or WATCHDOG_READY.exists():
        raise RuntimeError("refusing to reuse controller output")
    watchdog_log = (OUT / "watchdog.log").open("xb")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--watchdog"], stdout=watchdog_log,
                     stderr=subprocess.STDOUT, creationflags=flags, close_fds=True)
    for _ in range(25):
        if WATCHDOG_READY.exists():
            break
        time.sleep(0.2)
    if not WATCHDOG_READY.exists():
        raise RuntimeError("independent teardown watchdog did not arm")
    client = session()
    record = {"package_id": PACKAGE_ID, "started_utc": utc_now(), "status": "preflight",
              "image": IMAGE, "pod_created": False, "terminated": False,
              "creation_attempted": False, "creation_uncertain": False}
    pod_id = None
    created = time.time()
    lines = []
    name = "cm-memory-smoke-" + uuid.uuid4().hex[:12]
    try:
        pods = safe_pods(client)
        if pods:
            raise RuntimeError("zero-pod preflight failed")
        offer, quoted_rate, quoted_ram = catalog_offer(client)
        manifest = json.loads(MANIFEST_PATH.read_text())
        lock = json.loads(LOCK_PATH.read_text())
        if len(manifest["files"]) != 65 or len(lock["packages"]) != 13 or lock["source_builds_allowed"]:
            raise RuntimeError("approved package metadata mismatch")
        bundle = make_bundle(manifest)
        encoded = base64.b64encode(bundle).decode("ascii")
        environment = {f"CM_BUNDLE_{index:03d}": encoded[start:start+16000]
                       for index, start in enumerate(range(0, len(encoded), 16000))}
        environment.update({"CM_BUNDLE_SHA256": hashlib.sha256(bundle).hexdigest(),
                            "CM_UPLOAD_MANIFEST": base64.b64encode(json.dumps(manifest).encode()).decode(),
                            "CM_IMAGE_TAG": IMAGE_TAG, "CM_IMAGE_DIGEST": IMAGE_AMD64_DIGEST,
                            "CM_SETUP_DEADLINE": str(created + 300),
                            "PYTHONUNBUFFERED": "1",
                            "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                            "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"})
        projected = (quoted_rate + 0.002) * HARD_LIFETIME_S / 3600
        if quoted_rate > RATE_CAP or projected > TOTAL_CAP:
            raise RuntimeError("live quote exceeds approved financial caps")
        state = {"package_id": PACKAGE_ID, "name": name, "created_epoch": created,
                 "hard_deadline_epoch": created + CONTROLLER_DEADLINE_S, "pod_id": None}
        write_exclusive(STATE, state)
        bootstrap = "import base64;exec(base64.b64decode(" + repr(base64.b64encode(REMOTE_CODE.encode()).decode()) + "))"
        payload = {"name": name, "cloud": "SECURE", "image": IMAGE,
                   "disk": CONTAINER_DISK_GB, "mounts": {},
                   "cpu": {"id": CPU_ID, "vcpuCount": VCPU},
                   "ports": [], "env": environment,
                   "args": "python -u -c " + shlex.quote(bootstrap),
                   "startSsh": False, "startJupyter": False, "globalNetworking": False}
        record["creation_attempted"] = True
        record["creation_uncertain"] = True
        response = client.post(REST_V2 + "/pods", json=payload, timeout=120, allow_redirects=False)
        record["creation_http_status"] = response.status_code
        if 400 <= response.status_code < 500:
            record["creation_uncertain"] = False
        if response.status_code not in (200, 201):
            title = None
            try:
                body = response.json()
                title = {key: body.get(key) for key in ("title", "detail", "error", "message", "errors") if body.get(key)}
                title = str(title).replace(read_key(), "<redacted>")[:2000]
            except ValueError:
                pass
            raise RuntimeError(f"pod creation failed HTTP {response.status_code}: {title}")
        pod = response.json().get("pod", response.json())
        pod_id = pod.get("id")
        if not pod_id:
            raise RuntimeError("pod creation response omitted id")
        record["creation_uncertain"] = False
        write_exclusive(POD_IDENTITY, {"pod_id": pod_id, "name": name, "recorded_utc": utc_now()})
        created_mounts = pod.get("mounts") or {}
        detail = client.get(REST_V1 + "/pods/" + pod_id, timeout=10, allow_redirects=False)
        detail.raise_for_status()
        pod = detail.json().get("pod", detail.json())
        actual_rate = float(pod["costPerHr"])
        record.update({"pod_created": True, "pod_id": pod_id, "status": "running",
                       "cpu_id": pod.get("cpuFlavorId"), "vcpu": pod.get("vcpuCount"),
                       "ram_gb": pod.get("memoryInGb"), "container_disk_gb": pod.get("containerDiskInGb"),
                       "volume_gb": pod.get("volumeInGb"), "mounts": created_mounts, "quoted_rate_usd_per_hour": quoted_rate,
                       "actual_rate_usd_per_hour": actual_rate, "projected_20_min_cost_usd": (actual_rate+0.002)/3,
                       "storage_rate_reserve_usd_per_hour": 0.002,
                       "offer_availability": offer.get("availability")})
        if (actual_rate > RATE_CAP or record["projected_20_min_cost_usd"] > TOTAL_CAP
                or record["container_disk_gb"] is None or record["container_disk_gb"] > CONTAINER_DISK_GB or record["volume_gb"] not in (None, 0) or record["mounts"]
                or record["vcpu"] != VCPU or float(record["ram_gb"]) < RAM_GB):
            raise RuntimeError("created pod differs from approved resource/financial bounds")
        lines, events = collect_logs(client, pod_id, created + CONTROLLER_DEADLINE_S, created + 300, lines)
        record["events"] = events
        record["evidence"] = extract_evidence(lines)
        completed = [row for row in events if row.get("kind") == "done"]
        if not completed:
            raise RuntimeError("remote completion marker absent at deadline")
        done = completed[-1]
        record["remote_status"] = done.get("status")
        record["status"] = "complete" if record["remote_status"] == "complete" else "remote_failed"
    except Exception as exc:
        record["status"] = "orchestrator_error"
        record["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        if not pod_id:
            try:
                matching = [row for row in safe_pods(client) if row.get("name") == name]
                if len(matching) == 1:
                    pod_id = matching[0]["id"]
                    record["recovered_pod_id"] = pod_id
                    record["pod_created"] = True
            except Exception as exc:
                record["recovery_error"] = type(exc).__name__
        if pod_id:
            if not lines:
                try:
                    collect_logs(client, pod_id, min(time.time()+5, created+CONTROLLER_DEADLINE_S), created+300, lines)
                except Exception as exc:
                    record["final_log_collection_error"] = type(exc).__name__
            try:
                with (OUT / "container.log").open("x", encoding="utf-8") as stream:
                    stream.write("\n".join(line for line in lines if not line.startswith("CM_EVIDENCE ")) + "\n")
            except OSError as exc:
                record["log_save_error"] = type(exc).__name__
            record["terminated"], record["termination_attempts"] = terminate(client, pod_id)
        try:
            record["postflight_pods"] = safe_pods(client)
        except Exception as exc:
            record["postflight_error"] = type(exc).__name__
        record["finished_utc"] = utc_now()
        record["lifetime_s"] = time.time() - created
        record["estimated_compute_cost_usd"] = round(float(record.get("actual_rate_usd_per_hour", 0)) * record["lifetime_s"] / 3600, 6)
        write_exclusive(RUN_RECORD, record)
        if ((record.get("terminated") or not pod_id) and "postflight_pods" in record
                and not record["creation_uncertain"]):
            WATCHDOG_DONE.write_text(utc_now() + "\n")
    print(json.dumps({key: record.get(key) for key in ("status", "pod_created", "pod_id", "terminated", "lifetime_s", "estimated_compute_cost_usd", "remote_status", "error")}, indent=2))
    return int(record["status"] != "complete" or not record.get("terminated") or record.get("postflight_pods"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watchdog", action="store_true")
    args = parser.parse_args()
    if not args.watchdog:
        OUT.mkdir(exist_ok=False)
    return watchdog() if args.watchdog else run()


if __name__ == "__main__":
    raise SystemExit(main())


