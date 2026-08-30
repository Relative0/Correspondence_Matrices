"""Execute the exactly approved CM proof batch on one disposable RunPod CPU pod."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import secrets
import subprocess
import sys
import tarfile
import time
import uuid
import zipfile

import requests


FACTORY = Path(__file__).resolve().parents[1]
ROOT = FACTORY.parents[1]
CONTROLLER_DEPS = FACTORY / "tmp" / "controller-deps"
sys.path.insert(0, str(CONTROLLER_DEPS))
sys.path.insert(0, str(ROOT))
import paramiko  # noqa: E402
from cm_runpod_config import load_runpod_config  # noqa: E402

V1 = "https://rest.runpod.io/v1"
V2 = "https://api.runpod.io/v2"
PROPOSAL_ID = "cm-video-proof3-cpu-remote-v4"
AUTHORIZATION_ID = "cm-video-proof3-cpu-remote-v4-auth"
BATCH_ID = "cm-video-level1-proof3-v1"
BUNDLE_SHA256 = "c36710478f77301244ffa76cfc16de291e0cdfca31f3990504cb6250aa43b7ad"
PAYLOAD_SHA256 = "e5f87d5a2c2a9ec1f9e8cb0e0350cb81d39d70d804e67613141929b3bac4f281"
BATCH_SHA256 = "88e986da255f82cc00b7231fb678bb6397c970eb59775c562b333821c9649f3d"
IMAGE = ("python:3.10.15-slim-bookworm@sha256:"
         "97ff6fda70178dee6c144d41030fb88b6ec86d75e1c517fe96b8f62094ea7ac2")
CPU_FLAVOR = "cpu5c"
VCPU = 4
RAM_GB = 8
CONTAINER_DISK_GB = 30
RATE_CAP = 0.27
TOTAL_CAP = 0.25
TIMEOUT_SECONDS = 1800
EXPECTED_JOBS = {
    "cm-video-level1-cm-foundation-16x9-v1",
    "cm-video-level1-explicit-cm-vs-cm-ir-16x9-v1",
    "cm-video-level1-cm-ir-vs-cse-flat-16x9-v1",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_frozen_bundle(bundle: Path, batch: Path) -> dict[str, object]:
    if sha256(bundle) != BUNDLE_SHA256 or sha256(batch) != BATCH_SHA256:
        raise RuntimeError("frozen bundle or batch identity changed")
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError("frozen bundle contains duplicate paths")
        manifest = json.loads(archive.read("package_manifest.json"))
        files = manifest.get("files")
        if not isinstance(files, list):
            raise RuntimeError("frozen bundle manifest has no file list")
        for entry in files:
            name = entry.get("path")
            path = PurePosixPath(name) if isinstance(name, str) else None
            if path is None or path.is_absolute() or ".." in path.parts:
                raise RuntimeError("frozen bundle manifest has an unsafe path")
            payload = archive.read(name)
            if len(payload) != entry.get("size") or hashlib.sha256(payload).hexdigest() != entry.get("sha256"):
                raise RuntimeError("frozen bundle entry identity changed: " + name)
        canonical = json.dumps(
            files, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        if hashlib.sha256(canonical).hexdigest() != PAYLOAD_SHA256:
            raise RuntimeError("frozen bundle payload identity changed")
        if manifest.get("payload_sha256") != PAYLOAD_SHA256:
            raise RuntimeError("frozen bundle manifest payload identity changed")
        archived_batch = archive.read("cm/batch_manifest.json")
        if archived_batch != batch.read_bytes() or hashlib.sha256(archived_batch).hexdigest() != BATCH_SHA256:
            raise RuntimeError("frozen bundle batch does not match approved batch")
        required = {
            "ivc/schemas/orchestration_response.schema.json",
            "cm/proofs/cm-foundation/render_job.json",
            "cm/proofs/explicit-cm-vs-cm-ir/render_job.json",
            "cm/proofs/cm-ir-vs-cse-flat/render_job.json",
        }
        if not required.issubset(names):
            raise RuntimeError("frozen bundle is missing a required runtime artifact")
    return {"files": len(files), "bundle_bytes": bundle.stat().st_size}


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".pending-" + uuid.uuid4().hex)
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


class Events:
    def __init__(self, path: Path):
        self.path = path
        self.sequence = 0

    def emit(self, event: str, **fields: object) -> None:
        self.sequence += 1
        record = {"schema_version": "1.0", "sequence": self.sequence,
                  "timestamp": utc_now(), "actor": "controller", "event": event, **fields}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()


def api_session() -> requests.Session:
    config = load_runpod_config()
    if not config.api_key or any(character.isspace() for character in config.api_key):
        raise RuntimeError("credential reference unavailable")
    client = requests.Session()
    client.trust_env = False
    client.headers["Authorization"] = "Bearer " + config.api_key
    return client


def request_json(client: requests.Session, method: str, url: str, **kwargs: object) -> object:
    response = client.request(method, url, allow_redirects=False, **kwargs)
    if response.status_code >= 300:
        raise RuntimeError(f"provider request failed: {method} {url.rsplit('/', 1)[-1]} HTTP {response.status_code}")
    return response.json() if response.content else {}


def inventory(client: requests.Session, base: str) -> list[dict[str, object]]:
    body = request_json(client, "GET", base + "/pods", timeout=20)
    pods = body if isinstance(body, list) else body.get("pods")
    if not isinstance(pods, list):
        raise RuntimeError("invalid inventory response")
    return pods


def owned(client: requests.Session, pod_name: str, pod_id: str | None) -> set[str]:
    matches: set[str] = set()
    for base in (V1, V2):
        for pod in inventory(client, base):
            candidate = pod.get("id")
            if pod.get("name") == pod_name:
                if not isinstance(candidate, str) or not re.fullmatch(r"[a-z0-9]{8,40}", candidate):
                    raise RuntimeError("owned-name match has invalid pod id")
                if pod_id and candidate != pod_id:
                    raise RuntimeError("owned-name match disagrees with recorded pod id")
                matches.add(candidate)
            if pod_id and candidate == pod_id and pod.get("name") != pod_name:
                raise RuntimeError("recorded pod id no longer has the owned name")
    if len(matches) > 1:
        raise RuntimeError("multiple pods match the unique owned name")
    return matches


def quote(client: requests.Session) -> dict[str, object]:
    body = request_json(
        client, "GET", V2 + "/catalog/cpus/" + CPU_FLAVOR,
        params={"include": "AVAILABILITY", "product": "POD", "vcpuCount": VCPU}, timeout=20,
    )
    rate = float(body["price"]["securePerVcpu"]) * VCPU
    ram = float(body["ramGbPerVcpu"]) * VCPU
    availability = body.get("availability")
    limits = body.get("vcpu") or {}
    if (body.get("id") != CPU_FLAVOR or availability not in {"LOW", "MEDIUM", "HIGH"}
            or not math.isfinite(rate) or not 0 < rate <= RATE_CAP
            or ram != RAM_GB or not int(limits["min"]) <= VCPU <= int(limits["max"])):
        raise RuntimeError("CPU quote is unavailable or outside the approved gate")
    return {"id": CPU_FLAVOR, "availability": availability, "vcpu": VCPU,
            "ram_gb": ram, "rate_usd_per_hour": rate, "checked_utc": utc_now()}


def account_ready(client: requests.Session) -> dict[str, bool]:
    body = request_json(client, "POST", "https://api.runpod.io/graphql",
                        json={"query": "query { myself { clientBalance currentSpendPerHr spendLimit } }"},
                        timeout=20)
    if body.get("errors"):
        raise RuntimeError("account readiness query failed")
    account = body["data"]["myself"]
    balance = float(account["clientBalance"])
    current = float(account["currentSpendPerHr"])
    raw_limit = account.get("spendLimit")
    sufficient_balance = math.isfinite(balance) and balance >= TOTAL_CAP
    sufficient_limit = raw_limit is None or (
        math.isfinite(float(raw_limit)) and math.isfinite(current)
        and float(raw_limit) >= current + RATE_CAP
    )
    if not sufficient_balance or not sufficient_limit:
        raise RuntimeError("account balance or spend limit cannot satisfy the authorization")
    return {"balance_sufficient": sufficient_balance, "spend_limit_sufficient": sufficient_limit}


def create_body(pod_name: str, token: str) -> dict[str, object]:
    start = r'''set -eu
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates openssh-server unzip
rm -rf /var/lib/apt/lists/*
mkdir -p /run/sshd
printf 'root:%s\n' "$CM_BOOTSTRAP_TOKEN" | chpasswd
printf '%s\n' 'PermitRootLogin yes' 'PasswordAuthentication yes' 'KbdInteractiveAuthentication no' 'UsePAM no' > /etc/ssh/sshd_config.d/99-cm-video.conf
exec /usr/sbin/sshd -D -e'''
    return {
        "name": pod_name, "computeType": "CPU", "cloudType": "SECURE",
        "imageName": IMAGE, "cpuFlavorIds": [CPU_FLAVOR], "cpuFlavorPriority": "custom",
        "vcpuCount": VCPU, "containerDiskInGb": CONTAINER_DISK_GB,
        "volumeInGb": 0, "volumeMountPath": "/workspace", "ports": ["22/tcp"],
        "supportPublicIp": True, "interruptible": False, "locked": False,
        "env": {
            "CM_BOOTSTRAP_TOKEN": token, "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1", "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
            "CM_VIDEO_BUNDLE_ROOT": "/opt/cm-video/bundle", "IVC_DATA": "/workspace/cache",
            "POP_VIDEO_FFMPEG": "/usr/bin/ffmpeg",
        },
        "dockerEntrypoint": ["sh", "-c"], "dockerStartCmd": [start],
    }


def pod_detail(client: requests.Session, pod_id: str) -> dict[str, object]:
    body = request_json(client, "GET", V1 + "/pods/" + pod_id,
                        params={"includeMachine": "true"}, timeout=20)
    return body.get("pod", body)


def verified_shape(pod: dict[str, object], pod_id: str, pod_name: str,
                   quoted_rate: float) -> dict[str, object]:
    machine = pod.get("machine") or {}
    gpu = pod.get("gpu") or {}
    images = [pod.get(key) for key in ("image", "imageName") if pod.get(key) is not None]
    rate = float(pod.get("costPerHr", "nan"))
    ports = sorted(pod.get("ports") or [])
    secure = machine.get("secureCloud") is True or pod.get("cloudType") == "SECURE" or pod.get("cloud") == "SECURE"
    if (pod.get("id") != pod_id or pod.get("name") != pod_name
            or pod.get("cpuFlavorId") != CPU_FLAVOR or pod.get("vcpuCount") != VCPU
            or float(pod.get("memoryInGb", "nan")) != RAM_GB
            or pod.get("containerDiskInGb") != CONTAINER_DISK_GB
            or type(pod.get("volumeInGb")) is not int or pod.get("volumeInGb") != 0
            or pod.get("networkVolume") or ports != ["22/tcp"]
            or not images or any(image != IMAGE for image in images) or not secure
            or gpu.get("id") or gpu.get("count", 0) not in (None, 0)
            or not math.isfinite(rate) or rate != quoted_rate or rate > RATE_CAP):
        raise RuntimeError("created pod differs from the approved shape or quote")
    return {"pod_id": pod_id, "cpu_flavor": CPU_FLAVOR, "vcpu": VCPU, "ram_gb": RAM_GB,
            "container_disk_gb": CONTAINER_DISK_GB, "volume_gb": 0,
            "ports": ["22/tcp"], "image": images[0], "secure_cloud": secure,
            "rate_usd_per_hour": rate}


def wait_for_ssh(client: requests.Session, pod_id: str, pod_name: str, token: str,
                 quoted_rate: float, timeout: int = 360) -> tuple[paramiko.SSHClient, dict[str, object]]:
    deadline = time.time() + timeout
    last_error = "not ready"
    while time.time() < deadline:
        try:
            pod = pod_detail(client, pod_id)
            shape = verified_shape(pod, pod_id, pod_name, quoted_rate)
            ip = pod.get("publicIp")
            mappings = pod.get("portMappings") or {}
            port = mappings.get("22") if isinstance(mappings, dict) else None
            port = port if port is not None else mappings.get(22) if isinstance(mappings, dict) else None
            if ip and port:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(str(ip), port=int(port), username="root", password=token,
                            look_for_keys=False, allow_agent=False, timeout=15,
                            banner_timeout=15, auth_timeout=15)
                key = ssh.get_transport().get_remote_server_key()
                shape["ssh_host_key_sha256"] = hashlib.sha256(key.asbytes()).hexdigest()
                shape["public_ip_present"] = True
                shape["external_ssh_port_present"] = True
                return ssh, shape
        except Exception as exc:
            last_error = type(exc).__name__
        time.sleep(6)
    raise RuntimeError("SSH did not become ready; last error type: " + last_error)


def remote_command(ssh: paramiko.SSHClient, command: str, log: Path,
                   token: str, timeout: int) -> None:
    channel = ssh.get_transport().open_session(timeout=20)
    channel.exec_command(command)
    deadline = time.time() + timeout
    chunks: list[bytes] = []
    while not channel.exit_status_ready():
        if time.time() >= deadline:
            channel.close()
            raise RuntimeError("remote command timed out")
        if channel.recv_ready():
            chunks.append(channel.recv(65536))
        if channel.recv_stderr_ready():
            chunks.append(channel.recv_stderr(65536))
        time.sleep(0.2)
    while channel.recv_ready():
        chunks.append(channel.recv(65536))
    while channel.recv_stderr_ready():
        chunks.append(channel.recv_stderr(65536))
    status = channel.recv_exit_status()
    text = b"".join(chunks).decode("utf-8", errors="replace").replace(token, "<redacted>")
    log.write_text(text[-2_000_000:], encoding="utf-8")
    if status != 0:
        raise RuntimeError(f"remote command failed with exit status {status}")


def upload_bundle(ssh: paramiko.SSHClient, bundle: Path, token: str, log: Path) -> None:
    remote_command(ssh, "mkdir -p /workspace/input /workspace/results", log, token, 30)
    with ssh.open_sftp() as sftp:
        sftp.put(str(bundle), "/workspace/input/bundle.zip", confirm=True)


def safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive, "r:gz") as handle:
        members = handle.getmembers()
        if len(members) > 1000 or sum(max(0, member.size) for member in members) > 300_000_000:
            raise RuntimeError("download archive exceeds safety limits")
        root = destination.resolve()
        for member in members:
            target = (destination / member.name).resolve()
            if root != target and root not in target.parents:
                raise RuntimeError("download archive path traversal")
            if member.issym() or member.islnk() or member.isdev():
                raise RuntimeError("download archive contains an unsupported entry")
        handle.extractall(destination)


def verify_results(extracted: Path) -> dict[str, object]:
    result_paths = sorted(extracted.glob("results/*/render_result.json"))
    results = [json.loads(path.read_text("utf-8")) for path in result_paths]
    if {row.get("job_id") for row in results} != EXPECTED_JOBS or len(results) != 3:
        raise RuntimeError("downloaded result set does not match the approved jobs")
    media = []
    for path, result in zip(result_paths, results):
        if (result.get("status") != "passed" or result.get("passed") is not True
                or result.get("technical_observations", {}).get("bundle_payload_sha256") != PAYLOAD_SHA256):
            raise RuntimeError("downloaded result did not pass or has the wrong bundle identity")
        job_root = path.parent
        videos = list(job_root.glob("ivc-output/*/*-16x9.mp4"))
        if len(videos) != 1 or sha256(videos[0]) != result["outputs"]["video"]:
            raise RuntimeError("downloaded video hash does not match its result")
        run_dir = videos[0].parent
        for key, filename in (("provenance", "provenance.json"), ("gap_report", "gap_report.json"),
                              ("cadence_report", "cadence_report.json")):
            if sha256(run_dir / filename) != result["outputs"][key]:
                raise RuntimeError(f"downloaded {key} hash mismatch")
        for name, digest in result["preview_frame_hashes"].items():
            if sha256(job_root / "previews" / (name + ".png")) != digest:
                raise RuntimeError("downloaded preview hash mismatch")
        tech = result["technical_observations"]
        if (tech.get("width"), tech.get("height"), round(float(tech.get("fps", 0)))) != (1920, 1080, 30):
            raise RuntimeError("downloaded media dimensions or frame rate mismatch")
        if tech.get("codec") != "h264" or tech.get("has_audio") is not False:
            raise RuntimeError("downloaded media stream contract mismatch")
        media.append({"job_id": result["job_id"], "video": str(videos[0]),
                      "video_sha256": result["outputs"]["video"],
                      "duration_s": tech.get("duration_s")})
    return {"status": "passed", "jobs": len(results), "media": media,
            "bundle_payload_sha256": PAYLOAD_SHA256}


def delete_owned(client: requests.Session, pod_name: str, pod_id: str | None,
                 events: Events) -> bool:
    matches = owned(client, pod_name, pod_id)
    for candidate in matches:
        attempts = []
        for base in (V1, V2):
            response = client.delete(base + "/pods/" + candidate, timeout=20, allow_redirects=False)
            attempts.append({"api": base.rsplit("/", 1)[-1], "status": response.status_code})
            if response.status_code in (200, 202, 204, 404):
                break
        events.emit("owned_pod_delete_attempted", pod_id=candidate, attempts=attempts)
    for _ in range(8):
        if not owned(client, pod_name, pod_id):
            return True
        time.sleep(5)
    return False


def run() -> int:
    preflight_path = FACTORY / "runpod" / "preflight.json"
    preflight = json.loads(preflight_path.read_text("utf-8"))
    bundle = FACTORY / "runpod" / preflight["bundle"]["file"]
    batch = FACTORY / "batch_manifest.json"
    if (preflight["proposal_id"] != PROPOSAL_ID or preflight["authorization_id"] != AUTHORIZATION_ID
            or sha256(bundle) != BUNDLE_SHA256 or sha256(batch) != BATCH_SHA256
            or preflight["bundle"]["payload_sha256"] != PAYLOAD_SHA256):
        raise RuntimeError("approved local identities no longer match")
    frozen_gate = verify_frozen_bundle(bundle, batch)
    run_id = "runpod-video-v4-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = FACTORY / "runpod" / "remote" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    events = Events(run_dir / "lifecycle.jsonl")
    state_path = run_dir / "controller_state.json"
    done_path = run_dir / "controller_done.json"
    watchdog_ack_path = run_dir / "watchdog_ack.json"
    record_path = run_dir / "RUN.json"
    pod_name = "cm-video-proof3-v4-" + uuid.uuid4().hex[:12]
    token = secrets.token_urlsafe(32)
    pod_id: str | None = None
    ssh: paramiko.SSHClient | None = None
    client: requests.Session | None = None
    started = time.time()
    cleanup_epoch = started + TIMEOUT_SECONDS
    record: dict[str, object] = {
        "schema_version": "1.0", "proposal_id": PROPOSAL_ID,
        "authorization_id": AUTHORIZATION_ID, "batch_id": BATCH_ID,
        "bundle_sha256": BUNDLE_SHA256, "batch_manifest_sha256": BATCH_SHA256,
        "status": "started", "started_utc": utc_now(), "pod_name": pod_name,
        "creation_attempted": False, "pod_created": False, "uploaded": False,
        "downloaded": False, "verified": False, "owned_pod_absent_verified": False,
        "credential_value_recorded": False,
    }
    state = {"schema_version": "1.0", "proposal_id": PROPOSAL_ID,
             "authorization_id": AUTHORIZATION_ID, "pod_name": pod_name,
             "pod_id": None, "cleanup_epoch": cleanup_epoch}
    atomic_json(state_path, state)
    with (run_dir / "watchdog.stdout.log").open("wb") as watchdog_stdout, \
            (run_dir / "watchdog.stderr.log").open("wb") as watchdog_stderr:
        watchdog = subprocess.Popen(
            [sys.executable, str(FACTORY / "runpod" / "runpod_watchdog.py"),
             "--state", str(state_path), "--done", str(done_path),
             "--events", str(run_dir / "watchdog.jsonl"),
             "--ack", str(watchdog_ack_path)],
            cwd=ROOT, stdout=watchdog_stdout, stderr=watchdog_stderr,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    watchdog_deadline = time.time() + 20
    while time.time() < watchdog_deadline and not watchdog_ack_path.is_file():
        if watchdog.poll() is not None:
            raise RuntimeError("watchdog exited before acknowledging readiness")
        time.sleep(0.25)
    if not watchdog_ack_path.is_file():
        raise RuntimeError("watchdog did not acknowledge readiness")
    watchdog_ack = json.loads(watchdog_ack_path.read_text("utf-8"))
    if (watchdog_ack.get("status") != "armed"
            or watchdog_ack.get("authorization_id") != AUTHORIZATION_ID
            or watchdog_ack.get("pod_name") != pod_name
            or watchdog_ack.get("deadline_epoch") != cleanup_epoch
            or watchdog_ack.get("state_sha256") != sha256(state_path)):
        raise RuntimeError("watchdog acknowledgement does not match controller state")
    events.emit("authorization_verified", proposal_id=PROPOSAL_ID,
                bundle_sha256=BUNDLE_SHA256, batch_manifest_sha256=BATCH_SHA256,
                bootstrap_token_sha256=hashlib.sha256(token.encode()).hexdigest(),
                watchdog_pid=watchdog.pid, cleanup_epoch=cleanup_epoch)
    events.emit("frozen_bundle_verified", payload_sha256=PAYLOAD_SHA256,
                **frozen_gate)
    events.emit("watchdog_armed", watchdog_pid=watchdog.pid,
                state_sha256=watchdog_ack["state_sha256"])
    print(f"run_dir={run_dir}", flush=True)
    try:
        client = api_session()
        offer = quote(client)
        account = account_ready(client)
        record["quote"] = offer
        record["account_readiness"] = account
        events.emit("quote_verified", **offer)
        print(f"quote_verified rate={offer['rate_usd_per_hour']:.2f}/hour availability={offer['availability']}", flush=True)
        before = owned(client, pod_name, None)
        if before:
            raise RuntimeError("unique owned pod name already exists")
        record["creation_attempted"] = True
        events.emit("create_requested", pod_name=pod_name)
        print("create_requested", flush=True)
        response = client.post(V1 + "/pods", json=create_body(pod_name, token),
                               timeout=(15, 90), allow_redirects=False)
        record["create_http_status"] = response.status_code
        if response.status_code not in (200, 201):
            raise RuntimeError("pod create failed with HTTP " + str(response.status_code))
        pod = response.json()
        pod = pod.get("pod", pod)
        pod_id = pod.get("id")
        if not isinstance(pod_id, str) or not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
            raise RuntimeError("creation response has no valid pod id")
        state["pod_id"] = pod_id
        atomic_json(state_path, state)
        record["pod_id"] = pod_id
        record["pod_created"] = True
        events.emit("pod_created", pod_id=pod_id)
        print("pod_created; waiting_for_exact_shape_and_ssh", flush=True)
        ssh, shape = wait_for_ssh(client, pod_id, pod_name, token, float(offer["rate_usd_per_hour"]))
        record["actual_resources"] = shape
        atomic_json(run_dir / "POD_RESOURCE_CHECK.json", shape)
        events.emit("shape_and_ssh_verified", pod_id=pod_id,
                    rate_usd_per_hour=shape["rate_usd_per_hour"],
                    ssh_host_key_sha256=shape["ssh_host_key_sha256"])
        print("shape_and_ssh_verified", flush=True)
        upload_bundle(ssh, bundle, token, run_dir / "ssh-mkdir.log")
        remote_hash_log = run_dir / "remote-bundle-verify.log"
        remote_command(ssh, "printf '%s  %s\\n' '" + BUNDLE_SHA256 + "' '/workspace/input/bundle.zip' | sha256sum --check -",
                       remote_hash_log, token, 60)
        record["uploaded"] = True
        events.emit("bundle_uploaded_and_verified", bundle_sha256=BUNDLE_SHA256,
                    bundle_bytes=bundle.stat().st_size)
        print("bundle_uploaded_and_verified", flush=True)
        remaining = max(60, int(cleanup_epoch - time.time() - 90))
        bootstrap_command = (
            "unzip -p /workspace/input/bundle.zip runpod/bootstrap.sh > /tmp/cm-video-bootstrap.sh && "
            "chmod 700 /tmp/cm-video-bootstrap.sh && "
            "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright /bin/sh /tmp/cm-video-bootstrap.sh "
            "/workspace/input/bundle.zip " + BUNDLE_SHA256 + " /opt/cm-video/bundle"
        )
        print("remote_bootstrap_started", flush=True)
        remote_command(ssh, bootstrap_command, run_dir / "remote-bootstrap.log", token, remaining)
        events.emit("remote_bootstrap_passed")
        print("remote_bootstrap_passed", flush=True)
        remaining = max(60, int(cleanup_epoch - time.time() - 90))
        batch_command = (
            "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 "
            "python /opt/cm-video/bundle/runpod/batch_runner.py "
            "--bundle-root /opt/cm-video/bundle --output-root /workspace/results "
            "--max-parallel 1 --timeout " + str(min(1800, remaining))
        )
        print("remote_batch_started", flush=True)
        remote_command(ssh, batch_command, run_dir / "remote-batch.log", token, remaining)
        events.emit("remote_batch_passed")
        print("remote_batch_passed", flush=True)
        remote_command(ssh, "tar -C /workspace -czf /workspace/cm-video-results.tar.gz results",
                       run_dir / "remote-archive.log", token, 120)
        archive = run_dir / "cm-video-results.tar.gz"
        with ssh.open_sftp() as sftp:
            stat = sftp.stat("/workspace/cm-video-results.tar.gz")
            if stat.st_size <= 0 or stat.st_size > 300_000_000:
                raise RuntimeError("remote results archive exceeds safety limits")
            sftp.get("/workspace/cm-video-results.tar.gz", str(archive))
        record["downloaded"] = True
        record["download_archive_sha256"] = sha256(archive)
        record["download_archive_bytes"] = archive.stat().st_size
        events.emit("results_downloaded", archive_sha256=record["download_archive_sha256"],
                    archive_bytes=archive.stat().st_size)
        extracted = run_dir / "extracted"
        safe_extract(archive, extracted)
        verification = verify_results(extracted)
        atomic_json(run_dir / "LOCAL_VERIFICATION.json", verification)
        record["verification"] = verification
        record["verified"] = True
        record["status"] = "passed"
        events.emit("results_verified", jobs=3)
        print("results_verified jobs=3", flush=True)
    except Exception as exc:
        record["status"] = "failed"
        record["error_type"] = type(exc).__name__
        if isinstance(exc, RuntimeError):
            record["error"] = str(exc)
        events.emit("terminal_failure", error_type=type(exc).__name__)
        print("terminal_failure error_type=" + type(exc).__name__, flush=True)
    finally:
        if ssh is not None:
            ssh.close()
        if client is None:
            try:
                client = api_session()
            except Exception:
                client = None
        if client is not None:
            try:
                absent = delete_owned(client, pod_name, pod_id, events)
                record["owned_pod_absent_verified"] = absent
                if not absent:
                    record["status"] = "failed"
                    record["cleanup_error_type"] = "OwnedPodRemains"
                print(f"cleanup_reconciled owned_pod_absent={str(absent).lower()}", flush=True)
            except Exception as exc:
                record["status"] = "failed"
                record["cleanup_error_type"] = type(exc).__name__
                events.emit("cleanup_failure", error_type=type(exc).__name__)
                print("cleanup_failure error_type=" + type(exc).__name__, flush=True)
            client.close()
        record["finished_utc"] = utc_now()
        record["elapsed_seconds"] = time.time() - started
        rate = float((record.get("quote") or {}).get("rate_usd_per_hour", 0))
        record["estimated_compute_cost_usd"] = rate * float(record["elapsed_seconds"]) / 3600
        if record["estimated_compute_cost_usd"] > TOTAL_CAP:
            record["status"] = "failed"
            record["budget_error"] = "estimated compute cost exceeded authorization"
        atomic_json(record_path, record)
        if record.get("owned_pod_absent_verified"):
            atomic_json(done_path, {"finished_utc": utc_now(), "owned_pod_absent_verified": True})
    return 0 if record.get("status") == "passed" and record.get("owned_pod_absent_verified") else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    raise SystemExit(run())


if __name__ == "__main__":
    main()
