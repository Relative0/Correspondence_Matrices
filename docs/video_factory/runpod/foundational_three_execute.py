"""Execute the exactly approved foundational-three silent-master render on RunPod."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import struct
import subprocess
import sys
import time
from typing import Any
from urllib.parse import quote as urlquote
import uuid
import zipfile


HERE = Path(__file__).resolve().parent
FACTORY = HERE.parent
ROOT = FACTORY.parents[1]
PACKAGE_ROOT = HERE / "foundational_three_v1"
sys.path.insert(0, str(HERE))
import execute_approved_v4 as base  # noqa: E402


PROPOSAL_ID = "cm-video-foundational-three-production-remote-v1"
AUTHORIZATION_ID = PROPOSAL_ID + "-auth"
PROPOSAL_IDENTITY = "d9b61bab7474a3204effcf98c47c3ab13f5e1a7ae4a1e7384638380a5e2c19f8"
BUNDLE_SHA256 = "84173e23939d6dc470396dc4681d4b71df311ba4c24dc483b93a1cd4ebb077c5"
PACKAGE_IDENTITY = "57107a6e7eb497123ff00b7708e161aeba296d78b8511c8ff1586f9ccc64597c"
MANIFEST_IDENTITY = "05c5bb5f00d96ccce277d47dd6ce54299b5e38f70566e6ed8b252ea2b212fa55"
GPU_ID = "NVIDIA RTX A5000"
GPU_COUNT = 1
IMAGE = ("python:3.10.15-slim-bookworm@sha256:"
         "97ff6fda70178dee6c144d41030fb88b6ec86d75e1c517fe96b8f62094ea7ac2")
CONTAINER_DISK_GB = 30
MIN_VCPU = 4
MIN_RAM_GB = 8
RATE_CAP = 0.27
TOTAL_CAP = 1.25
MAX_CREATES = 1
MAX_RUNTIME_SECONDS = 14400
POD_NAME_PREFIX = "cm-foundational-three-v1-"
RUN_ID_PREFIX = "runpod-foundational-three-v1-"
EXPECTED = {
    "operator-cms-from-truth-tables": {"duration": 187, "frames": 5610, "content_hash": "dadeca980d7641727fb9c9829f4fadba1b27c3faec7104e79380c5dd59fda015"},
    "logical-matrices-to-higher-dimensional-cms": {"duration": 246, "frames": 7380, "content_hash": "cbe63ed4efb224c2991c20eece400396aef1e5b90ddfc379abd3c435f7271003"},
    "what-is-explicit-cm": {"duration": 220, "frames": 6600, "content_hash": "a03074878572928d3fa92b6b5f711a2dcb35123682dda1d7210c7efdedb73af8"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: Any, identity_key: str) -> str:
    material = dict(value)
    material.pop(identity_key, None)
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".pending-" + uuid.uuid4().hex)
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def verify_local_authorization() -> dict[str, Any]:
    proposal_path = PACKAGE_ROOT / "proposal.json"
    authorization_path = PACKAGE_ROOT / "authorization.json"
    manifest_path = PACKAGE_ROOT / "package_manifest.json"
    bundle = PACKAGE_ROOT / "bundle.zip"
    proposal = json.loads(proposal_path.read_text("utf-8"))
    authorization = json.loads(authorization_path.read_text("utf-8"))
    manifest = json.loads(manifest_path.read_text("utf-8"))
    ceiling = proposal["authorization_ceiling"]
    resource = proposal["resource"]
    checks = (
        proposal["proposal_id"] == PROPOSAL_ID,
        proposal["status"] == "exact_authorization_requested",
        proposal["remote_or_paid_work_authorized"] is False,
        proposal["proposal_sha256"] == canonical_hash(proposal, "proposal_sha256") == PROPOSAL_IDENTITY,
        authorization["authorization_id"] == AUTHORIZATION_ID,
        authorization["proposal_id"] == PROPOSAL_ID,
        authorization["proposal_identity"] == PROPOSAL_IDENTITY,
        authorization["proposal_file_sha256"] == sha256(proposal_path),
        authorization["status"] == "approved",
        authorization["remote_or_paid_work_authorized"] is True,
        authorization["bundle_sha256"] == proposal["immutable_inputs"]["bundle_sha256"] == sha256(bundle) == BUNDLE_SHA256,
        manifest["package_manifest_sha256"] == canonical_hash(manifest, "package_manifest_sha256") == MANIFEST_IDENTITY,
        authorization["package_manifest_identity"] == proposal["immutable_inputs"]["package_manifest_sha256"] == MANIFEST_IDENTITY,
        proposal["immutable_inputs"].get("controller_core_sha256") in (None, sha256(Path(__file__))),
        authorization["maximum_total_runpod_spend_usd"] == ceiling["maximum_total_runpod_spend_usd"] == TOTAL_CAP,
        authorization["maximum_pod_creates"] == ceiling["maximum_pod_creates"] == MAX_CREATES,
        authorization["maximum_parallel_pods"] == ceiling["maximum_parallel_pods"] == 1,
        authorization["maximum_runtime_seconds"] == ceiling["maximum_runtime_seconds"] == MAX_RUNTIME_SECONDS,
        resource["gpu_id"] == GPU_ID and resource["gpu_count"] == GPU_COUNT,
        resource["cloud"] == "SECURE" and resource["volume_gb"] == 0,
        resource["container_disk_gb"] == CONTAINER_DISK_GB and resource["ports"] == ["22/tcp"],
        resource["base_image"] == IMAGE,
        proposal["quote"]["rate_usd_per_hour"] == RATE_CAP,
        tuple(proposal["content_identity"]["scope"]) == tuple(EXPECTED),
        proposal["content_identity"]["production_package_identity"] == PACKAGE_IDENTITY,
    )
    if not all(checks):
        raise RuntimeError("local approval, immutable identities, or ceilings disagree")
    expected_entries = {item["path"]: item for item in manifest["entries"]}
    with zipfile.ZipFile(bundle) as archive:
        files = [info for info in archive.infolist() if not info.is_dir()]
        if {info.filename for info in files} != set(expected_entries):
            raise RuntimeError("bundle entries differ from the approved package manifest")
        if len(files) > 100 or sum(info.file_size for info in files) > 50_000_000:
            raise RuntimeError("bundle exceeds its local safety limits")
        for info in files:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError("bundle contains an unsafe path or symlink")
            data = archive.read(info)
            entry = expected_entries[info.filename]
            if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise RuntimeError("bundle entry identity changed: " + info.filename)
    return {"proposal": proposal, "authorization": authorization, "manifest": manifest, "bundle": bundle}


def gpu_catalog(client: Any) -> dict[str, Any]:
    body = base.request_json(
        client, "GET", base.V2 + "/catalog/gpus/" + urlquote(GPU_ID, safe=""),
        params={"include": "AVAILABILITY", "product": "POD", "cloud": "SECURE", "count": GPU_COUNT},
        timeout=20,
    )
    rate = float((body.get("price") or {}).get("secure", "nan")) * GPU_COUNT
    availability = body.get("availability")
    if (body.get("id") != GPU_ID or body.get("secure") is not True
            or not math.isfinite(rate) or not 0 < rate <= RATE_CAP):
        raise RuntimeError("approved Secure A5000 catalog identity or rate changed")
    return {"gpu_id": GPU_ID, "gpu_count": GPU_COUNT, "availability": availability,
            "rate_usd_per_hour": rate, "checked_utc": utc_now()}


def quote_gpu(client: Any) -> dict[str, Any]:
    offer = gpu_catalog(client)
    if offer["availability"] not in {"LOW", "MEDIUM", "HIGH"}:
        raise RuntimeError("approved Secure A5000 offer is unavailable")
    return offer


def wait_for_gpu_offer(client: Any, timeout: int = 1800) -> dict[str, Any]:
    deadline, check = time.time() + timeout, 0
    while time.time() < deadline:
        check += 1
        offer = gpu_catalog(client)
        print(f"capacity_check={check} availability={offer['availability']} rate={offer['rate_usd_per_hour']:.2f}",
              flush=True)
        if offer["availability"] in {"LOW", "MEDIUM", "HIGH"}:
            return offer
        time.sleep(15)
    raise RuntimeError("approved Secure A5000 capacity did not return within the bounded watch")


def account_ready(client: Any) -> dict[str, bool]:
    body = base.request_json(client, "POST", "https://api.runpod.io/graphql",
                             json={"query": "query { myself { clientBalance currentSpendPerHr spendLimit } }"}, timeout=20)
    if body.get("errors"):
        raise RuntimeError("account readiness query failed")
    account = body["data"]["myself"]
    balance = float(account["clientBalance"])
    current = float(account["currentSpendPerHr"])
    raw_limit = account.get("spendLimit")
    balance_ok = math.isfinite(balance) and balance >= TOTAL_CAP
    limit_ok = raw_limit is None or (math.isfinite(float(raw_limit)) and math.isfinite(current)
                                     and float(raw_limit) >= current + RATE_CAP)
    if not balance_ok or not limit_ok:
        raise RuntimeError("account cannot satisfy the approved spend ceiling")
    return {"balance_sufficient": balance_ok, "spend_limit_sufficient": limit_ok}


def create_body(name: str, token: str) -> dict[str, Any]:
    start = r'''set -eu
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates openssh-server unzip
rm -rf /var/lib/apt/lists/*
mkdir -p /run/sshd
printf 'root:%s\n' "$CM_BOOTSTRAP_TOKEN" | chpasswd
printf '%s\n' 'PermitRootLogin yes' 'PasswordAuthentication yes' 'KbdInteractiveAuthentication no' 'UsePAM no' > /etc/ssh/sshd_config.d/99-cm-video.conf
exec /usr/sbin/sshd -D -e'''
    return {
        "name": name, "computeType": "GPU", "cloudType": "SECURE", "imageName": IMAGE,
        "gpuTypeIds": [GPU_ID], "gpuTypePriority": "custom", "gpuCount": GPU_COUNT,
        "containerDiskInGb": CONTAINER_DISK_GB, "volumeInGb": 0, "volumeMountPath": "/workspace",
        "ports": ["22/tcp"], "supportPublicIp": True, "interruptible": False, "locked": False,
        "env": {"CM_BOOTSTRAP_TOKEN": token, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"},
        "dockerEntrypoint": ["sh", "-c"], "dockerStartCmd": [start],
    }


def verified_shape(pod: dict[str, Any], pod_id: str, name: str, quoted_rate: float) -> dict[str, Any]:
    machine, gpu = pod.get("machine") or {}, pod.get("gpu") or {}
    images = [pod.get(key) for key in ("image", "imageName") if pod.get(key) is not None]
    rate = float(pod.get("costPerHr", "nan"))
    secure = machine.get("secureCloud") is True or pod.get("cloudType") == "SECURE" or pod.get("cloud") == "SECURE"
    gpu_id = gpu.get("id") or machine.get("gpuTypeId")
    gpu_count = gpu.get("count", pod.get("gpuCount"))
    vcpu, ram = float(pod.get("vcpuCount", "nan")), float(pod.get("memoryInGb", "nan"))
    if (pod.get("id") != pod_id or pod.get("name") != name or gpu_id != GPU_ID
            or gpu_count not in (None, GPU_COUNT) or not math.isfinite(vcpu) or vcpu < MIN_VCPU
            or not math.isfinite(ram) or ram < MIN_RAM_GB
            or pod.get("containerDiskInGb") != CONTAINER_DISK_GB or pod.get("volumeInGb") not in (None, 0)
            or pod.get("networkVolume") or sorted(pod.get("ports") or []) != ["22/tcp"]
            or not images or any(image != IMAGE for image in images) or not secure
            or not math.isfinite(rate) or rate != quoted_rate or rate > RATE_CAP):
        raise RuntimeError("created pod differs from the approved resource or quote")
    return {"pod_id": pod_id, "gpu_id": GPU_ID, "gpu_count": GPU_COUNT, "vcpu": vcpu, "ram_gb": ram,
            "container_disk_gb": CONTAINER_DISK_GB, "volume_gb": 0, "ports": ["22/tcp"],
            "image": images[0], "secure_cloud": secure, "rate_usd_per_hour": rate}


def wait_for_ssh(client: Any, pod_id: str, name: str, token: str,
                 quoted_rate: float, timeout: int = 600) -> tuple[Any, dict[str, Any]]:
    deadline, last_error = time.time() + timeout, "not ready"
    while time.time() < deadline:
        try:
            pod = base.pod_detail(client, pod_id)
            shape = verified_shape(pod, pod_id, name, quoted_rate)
            mappings = pod.get("portMappings") or {}
            port = mappings.get("22") if isinstance(mappings, dict) else None
            port = port if port is not None else mappings.get(22) if isinstance(mappings, dict) else None
            if pod.get("publicIp") and port:
                ssh = base.paramiko.SSHClient()
                ssh.set_missing_host_key_policy(base.paramiko.AutoAddPolicy())
                ssh.connect(str(pod["publicIp"]), port=int(port), username="root", password=token,
                            look_for_keys=False, allow_agent=False, timeout=15, banner_timeout=15, auth_timeout=15)
                ssh.get_transport().set_keepalive(15)
                shape["ssh_host_key_sha256"] = hashlib.sha256(ssh.get_transport().get_remote_server_key().asbytes()).hexdigest()
                return ssh, shape
        except Exception as exc:
            last_error = type(exc).__name__
        time.sleep(6)
    raise RuntimeError("SSH did not become ready; last error type: " + last_error)


def arm_watchdog(run_dir: Path, name: str, deadline: float) -> tuple[subprocess.Popen[bytes], Path, Path]:
    state_path, done_path, ack_path = (run_dir / "controller_state.json", run_dir / "controller_done.json",
                                       run_dir / "watchdog_ack.json")
    state = {"schema_version": "1.0", "proposal_id": PROPOSAL_ID, "authorization_id": AUTHORIZATION_ID,
             "pod_name": name, "pod_id": None, "cleanup_epoch": deadline}
    atomic_json(state_path, state)
    with (run_dir / "watchdog.stdout.log").open("wb") as stdout, (run_dir / "watchdog.stderr.log").open("wb") as stderr:
        process = subprocess.Popen([sys.executable, str(HERE / "runpod_watchdog.py"), "--state", str(state_path),
                                    "--done", str(done_path), "--events", str(run_dir / "watchdog.jsonl"),
                                    "--ack", str(ack_path)], cwd=ROOT, stdout=stdout, stderr=stderr,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    limit = time.time() + 25
    while time.time() < limit and not ack_path.is_file():
        if process.poll() is not None:
            raise RuntimeError("watchdog exited before readiness")
        time.sleep(0.25)
    if not ack_path.is_file():
        raise RuntimeError("watchdog did not acknowledge readiness")
    ack = json.loads(ack_path.read_text("utf-8"))
    if (ack.get("status") != "armed" or ack.get("authorization_id") != AUTHORIZATION_ID
            or ack.get("pod_name") != name or ack.get("deadline_epoch") != deadline
            or ack.get("state_sha256") != sha256(state_path)):
        raise RuntimeError("watchdog acknowledgement mismatch")
    return process, state_path, done_path


def remote_command_progress(ssh: Any, command: str, log: Path, token: str, timeout: int) -> None:
    channel = ssh.get_transport().open_session(timeout=20)
    channel.exec_command(command)
    deadline, started, last_notice = time.time() + timeout, time.time(), 0
    chunks: list[bytes] = []
    while not channel.exit_status_ready():
        if time.time() >= deadline:
            channel.close()
            raise RuntimeError("remote render timed out")
        if channel.recv_ready():
            chunks.append(channel.recv(65536))
        if channel.recv_stderr_ready():
            chunks.append(channel.recv_stderr(65536))
        elapsed = int(time.time() - started)
        if elapsed - last_notice >= 20:
            last_notice = elapsed
            print(f"remote_render_progress elapsed_seconds={elapsed}", flush=True)
        time.sleep(0.2)
    while channel.recv_ready():
        chunks.append(channel.recv(65536))
    while channel.recv_stderr_ready():
        chunks.append(channel.recv_stderr(65536))
    status = channel.recv_exit_status()
    text = b"".join(chunks).decode("utf-8", errors="replace").replace(token, "<redacted>")
    log.write_text(text[-4_000_000:], encoding="utf-8")
    if status != 0:
        raise RuntimeError(f"remote render failed with exit status {status}")


def remote_capture(ssh: Any, command: str, token: str, timeout: int = 30) -> str:
    channel = ssh.get_transport().open_session(timeout=20)
    channel.exec_command(command)
    deadline, chunks = time.time() + timeout, []
    while not channel.exit_status_ready():
        if time.time() >= deadline:
            channel.close()
            raise RuntimeError("remote status check timed out")
        if channel.recv_ready():
            chunks.append(channel.recv(65536))
        if channel.recv_stderr_ready():
            chunks.append(channel.recv_stderr(65536))
        time.sleep(0.1)
    while channel.recv_ready():
        chunks.append(channel.recv(65536))
    while channel.recv_stderr_ready():
        chunks.append(channel.recv_stderr(65536))
    status = channel.recv_exit_status()
    text = b"".join(chunks).decode("utf-8", errors="replace").replace(token, "<redacted>")
    if status != 0:
        raise RuntimeError("remote status check failed")
    return text.strip()


def start_detached_render(ssh: Any, token: str, log: Path) -> None:
    command = (
        "set -eu; mkdir -p /workspace/bundle; "
        "unzip -q /workspace/input/bundle.zip -d /workspace/bundle; "
        "chmod 700 /workspace/bundle/runpod/bootstrap.sh; "
        "rm -f /workspace/foundational-job.exit /workspace/foundational-job.pid; "
        "nohup sh -c 'set +e; "
        "CM_FOUNDATIONAL_BUNDLE_ROOT=/workspace/bundle CM_FOUNDATIONAL_OUTPUT_ROOT=/workspace/foundational-output "
        "bash /workspace/bundle/runpod/bootstrap.sh; rc=$?; "
        "printf \"%s\\n\" \"$rc\" > /workspace/foundational-job.exit; exit \"$rc\"' "
        "> /workspace/foundational-job.log 2>&1 < /dev/null & "
        "echo $! > /workspace/foundational-job.pid"
    )
    base.remote_command(ssh, command, log, token, 120)


def wait_detached_render(client: Any, pod_id: str, name: str, token: str, rate: float,
                         ssh: Any, deadline: float) -> Any:
    status_command = (
        "if [ -f /workspace/foundational-job.exit ]; then printf 'EXIT:'; cat /workspace/foundational-job.exit; "
        "elif [ -f /workspace/foundational-job.pid ] && kill -0 \"$(cat /workspace/foundational-job.pid)\" 2>/dev/null; "
        "then echo RUNNING; else echo LOST; fi"
    )
    started, checks = time.time(), 0
    while time.time() < deadline:
        checks += 1
        try:
            if ssh is None or ssh.get_transport() is None or not ssh.get_transport().is_active():
                if ssh is not None:
                    ssh.close()
                ssh, _shape = wait_for_ssh(client, pod_id, name, token, rate, timeout=180)
                print("remote_monitor_reconnected", flush=True)
            status = remote_capture(ssh, status_command, token)
        except Exception:
            if ssh is not None:
                ssh.close()
            ssh = None
            print("remote_monitor_reconnect_pending", flush=True)
            time.sleep(10)
            continue
        if status.startswith("EXIT:"):
            if status != "EXIT:0":
                raise RuntimeError("detached remote render exited unsuccessfully")
            return ssh
        if status == "LOST":
            raise RuntimeError("detached remote render lost without an exit record")
        if status != "RUNNING":
            raise RuntimeError("detached remote render returned an invalid status")
        print(f"remote_render_progress elapsed_seconds={int(time.time() - started)} checks={checks}", flush=True)
        time.sleep(20)
    raise RuntimeError("detached remote render exceeded the approved runtime")


def safe_extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as handle:
        files = [item for item in handle.infolist() if not item.is_dir()]
        if len(files) > 100 or sum(item.file_size for item in files) > 1_000_000_000:
            raise RuntimeError("download archive exceeds safety limits")
        root = destination.resolve()
        for item in files:
            target = (destination / PurePosixPath(item.filename)).resolve()
            if root != target and root not in target.parents:
                raise RuntimeError("download archive path traversal")
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError("download archive contains a symlink")
        handle.extractall(destination)


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("QA artifact is not a PNG: " + path.name)
    return struct.unpack(">II", header[16:24])


def verify_results(root: Path, payload_sha256: str) -> dict[str, Any]:
    files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    expected_files = {"render_summary.json", "symbol_preflight/symbol_stress_manifest.json",
                      "symbol_preflight/symbol_specimen.png", "symbol_preflight/repeat_frames/f000000.png",
                      "symbol_preflight/repeat_frames/f000001.png"}
    for video_id in EXPECTED:
        prefix = video_id + "/"
        expected_files.update({prefix + "frame_manifest.json", prefix + "render_result.json",
                               prefix + video_id + ".silent-master.mp4", prefix + "qa_frames/opening.png",
                               prefix + "qa_frames/middle.png", prefix + "qa_frames/final.png"})
    if files != expected_files:
        raise RuntimeError("downloaded result contains missing or unexpected files")
    summary = json.loads((root / "render_summary.json").read_text("utf-8"))
    if (summary.get("status") != "passed" or summary.get("package_identity_sha256") != PACKAGE_IDENTITY
            or summary.get("narration") is not False or summary.get("publication_authorized") is not False
            or tuple(item.get("video_id") for item in summary.get("episodes", [])) != tuple(EXPECTED)):
        raise RuntimeError("render summary identity or scope mismatch")
    symbol = summary.get("symbol_preflight") or {}
    specimen = root / str((symbol.get("specimen") or {}).get("path", ""))
    repeats = [root / "symbol_preflight/repeat_frames/f000000.png", root / "symbol_preflight/repeat_frames/f000001.png"]
    if (symbol.get("status") != "passed" or symbol.get("font_cmap_coverage") is not True
            or symbol.get("repeat_frame_deterministic") is not True or not specimen.is_file()
            or sha256(specimen) != symbol["specimen"]["sha256"] or sha256(repeats[0]) != sha256(repeats[1])
            or png_dimensions(specimen) != (1920, 1080)):
        raise RuntimeError("remote mathematical-symbol preflight mismatch")
    verified = []
    for item in summary["episodes"]:
        video_id, contract = item["video_id"], EXPECTED[item["video_id"]]
        video = root / item["video"]["path"]
        technical = item["technical"]
        if (item.get("status") != "passed" or item.get("content_hash") != contract["content_hash"]
                or not video.is_file() or sha256(video) != item["video"]["sha256"]
                or video.stat().st_size != item["video"]["bytes"]
                or technical.get("width") != 1920 or technical.get("height") != 1080
                or abs(float(technical.get("fps", 0)) - 30) > 0.001 or technical.get("codec") != "h264"
                or technical.get("pixel_format") != "yuv420p" or technical.get("audio_streams") != 0
                or technical.get("frame_count") != contract["frames"]
                or abs(float(technical.get("duration_s", 0)) - contract["duration"]) > 0.05):
            raise RuntimeError("media contract mismatch for " + video_id)
        for name in ("opening", "middle", "final"):
            ref = item["qa_frames"][name]
            frame = root / ref["path"]
            if not frame.is_file() or sha256(frame) != ref["sha256"] or png_dimensions(frame) != (1920, 1080):
                raise RuntimeError("QA frame mismatch for " + video_id + ":" + name)
        local_result = json.loads((root / video_id / "render_result.json").read_text("utf-8"))
        if local_result != item:
            raise RuntimeError("per-episode result disagrees with render summary")
        verified.append({"video_id": video_id, "video_sha256": item["video"]["sha256"],
                         "bytes": item["video"]["bytes"], "frames": technical["frame_count"]})
    return {"status": "passed", "proposal_id": PROPOSAL_ID, "proposal_identity": PROPOSAL_IDENTITY,
            "bundle_sha256": BUNDLE_SHA256, "download_archive_sha256": payload_sha256,
            "package_identity_sha256": PACKAGE_IDENTITY, "episodes": verified,
            "symbol_specimen_sha256": sha256(specimen), "verified_utc": utc_now()}


def prior_consumption() -> tuple[int, float]:
    records = []
    remote = PACKAGE_ROOT / "remote"
    if remote.is_dir():
        for path in remote.glob("*/RUN.json"):
            try:
                records.append(json.loads(path.read_text("utf-8")))
            except (OSError, ValueError):
                raise RuntimeError("a prior run record is unreadable; refusing another create")
    creates = sum(record.get("creation_attempted") is True for record in records)
    spent = sum(float(record.get("estimated_compute_cost_usd", 0)) for record in records)
    return creates, spent


def preflight() -> dict[str, Any]:
    frozen = verify_local_authorization()
    creates, spent = prior_consumption()
    if creates >= MAX_CREATES or spent >= TOTAL_CAP:
        raise RuntimeError("the proposal's cross-run create or spend ceiling is already consumed")
    with base.api_session() as client:
        quote = quote_gpu(client)
        account = account_ready(client)
        inventory_clear = not any(str(pod.get("name", "")).startswith(POD_NAME_PREFIX)
                                  for api in (base.V1, base.V2) for pod in base.inventory(client, api))
    if not inventory_clear:
        raise RuntimeError("an owned pod for this proposal already exists")
    return {"status": "passed", "proposal_id": PROPOSAL_ID, "proposal_identity": PROPOSAL_IDENTITY,
            "bundle_sha256": sha256(frozen["bundle"]), "quote": quote, "account_readiness": account,
            "owned_inventory_clear": True, "pod_creates_consumed": creates,
            "estimated_prior_spend_usd": spent, "resource_writes": 0}


def run() -> int:
    frozen = verify_local_authorization()
    creates, prior_spend = prior_consumption()
    if creates >= MAX_CREATES or prior_spend >= TOTAL_CAP:
        raise RuntimeError("the proposal's cross-run create or spend ceiling is already consumed")
    run_id = RUN_ID_PREFIX + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = PACKAGE_ROOT / "remote" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    name = POD_NAME_PREFIX + uuid.uuid4().hex[:12]
    token = secrets.token_urlsafe(32)
    started, deadline = time.time(), time.time() + MAX_RUNTIME_SECONDS
    _watchdog, state_path, done_path = arm_watchdog(run_dir, name, deadline)
    pod_id, ssh, client = None, None, None
    events = base.Events(run_dir / "lifecycle.jsonl")
    record: dict[str, Any] = {
        "schema_version": "1.0", "proposal_id": PROPOSAL_ID, "proposal_identity": PROPOSAL_IDENTITY,
        "authorization_id": AUTHORIZATION_ID, "bundle_sha256": BUNDLE_SHA256, "run_id": run_id,
        "pod_name": name, "status": "started", "started_utc": utc_now(), "creation_attempted": False,
        "pod_created": False, "uploaded": False, "downloaded": False, "verified": False,
        "owned_pod_absent_verified": False, "credential_value_recorded": False,
    }
    print(f"run_dir={run_dir}", flush=True)
    try:
        client = base.api_session()
        offer, account = wait_for_gpu_offer(client), account_ready(client)
        if prior_spend + offer["rate_usd_per_hour"] * MAX_RUNTIME_SECONDS / 3600 > TOTAL_CAP:
            raise RuntimeError("approved spend cannot cover the maximum runtime")
        record["quote"], record["account_readiness"] = offer, account
        inventory_clear = not any(str(pod.get("name", "")).startswith(POD_NAME_PREFIX)
                                  for api in (base.V1, base.V2) for pod in base.inventory(client, api))
        if not inventory_clear:
            raise RuntimeError("an owned pod for this proposal already exists")
        print(f"preflight_passed rate={offer['rate_usd_per_hour']:.2f} availability={offer['availability']}", flush=True)
        record["creation_attempted"] = True
        atomic_json(run_dir / "RUN.json", record)
        events.emit("create_requested", pod_name=name)
        response = client.post(base.V1 + "/pods", json=create_body(name, token), timeout=(15, 120), allow_redirects=False)
        record["create_http_status"] = response.status_code
        if response.status_code not in (200, 201):
            raise RuntimeError("pod create failed with HTTP " + str(response.status_code))
        pod = response.json()
        pod = pod.get("pod", pod)
        pod_id = pod.get("id")
        if not isinstance(pod_id, str) or not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
            raise RuntimeError("pod creation response omitted a valid id")
        state = json.loads(state_path.read_text("utf-8"))
        state["pod_id"] = pod_id
        atomic_json(state_path, state)
        record["pod_created"], record["pod_id"] = True, pod_id
        print("pod_created waiting_for_exact_shape_and_ssh", flush=True)
        ssh, shape = wait_for_ssh(client, pod_id, name, token, offer["rate_usd_per_hour"])
        record["actual_resources"] = shape
        atomic_json(run_dir / "POD_RESOURCE_CHECK.json", shape)
        print("shape_and_ssh_verified", flush=True)
        base.upload_bundle(ssh, frozen["bundle"], token, run_dir / "ssh-mkdir.log")
        base.remote_command(ssh, "printf '%s  %s\\n' '" + BUNDLE_SHA256 + "' '/workspace/input/bundle.zip' | sha256sum --check -",
                            run_dir / "remote-bundle-verify.log", token, 90)
        record["uploaded"] = True
        print("bundle_uploaded_and_verified", flush=True)
        remaining = max(60, int(deadline - time.time() - 180))
        print("remote_render_started", flush=True)
        start_detached_render(ssh, token, run_dir / "remote-render-start.log")
        try:
            ssh = wait_detached_render(client, pod_id, name, token, offer["rate_usd_per_hour"], ssh,
                                       time.time() + remaining)
        except Exception:
            try:
                if ssh is None or ssh.get_transport() is None or not ssh.get_transport().is_active():
                    ssh, _shape = wait_for_ssh(client, pod_id, name, token, offer["rate_usd_per_hour"], timeout=120)
                with ssh.open_sftp() as sftp:
                    sftp.get("/workspace/foundational-job.log", str(run_dir / "remote-render.log"))
            except Exception:
                pass
            raise
        with ssh.open_sftp() as sftp:
            sftp.get("/workspace/foundational-job.log", str(run_dir / "remote-render.log"))
        print("remote_render_passed", flush=True)
        archive = run_dir / "foundational-three-results.zip"
        digest_file = run_dir / "foundational-three-results.zip.sha256"
        with ssh.open_sftp() as sftp:
            stat = sftp.stat("/workspace/foundational-three-results.zip")
            if stat.st_size <= 0 or stat.st_size > 500_000_000:
                raise RuntimeError("remote result archive exceeds the approved safety limit")
            sftp.get("/workspace/foundational-three-results.zip", str(archive))
            sftp.get("/workspace/foundational-three-results.zip.sha256", str(digest_file))
        remote_digest = digest_file.read_text("utf-8").strip().split()[0]
        if not re.fullmatch(r"[0-9a-f]{64}", remote_digest) or remote_digest != sha256(archive):
            raise RuntimeError("downloaded archive hash disagrees with the remote digest")
        record["downloaded"] = True
        record["download_archive_sha256"] = remote_digest
        record["download_archive_bytes"] = archive.stat().st_size
        results_root = run_dir / "results"
        safe_extract_zip(archive, results_root)
        verification = verify_results(results_root, remote_digest)
        atomic_json(run_dir / "LOCAL_VERIFICATION.json", verification)
        record["verification"], record["verified"], record["status"] = verification, True, "passed"
        print(f"results_verified episodes={len(EXPECTED)}", flush=True)
    except Exception as exc:
        record["status"], record["error_type"], record["error"] = "failed", type(exc).__name__, str(exc)
        print("terminal_failure error_type=" + type(exc).__name__, flush=True)
    finally:
        if ssh is not None:
            ssh.close()
        if client is None:
            try:
                client = base.api_session()
            except Exception:
                client = None
        if client is not None:
            cleanup_error = None
            for cleanup_attempt in range(1, 6):
                try:
                    absent = base.delete_owned(client, name, pod_id, events)
                    record["owned_pod_absent_verified"] = absent
                    if absent:
                        break
                    cleanup_error = "OwnedPodRemains"
                except Exception as exc:
                    cleanup_error = type(exc).__name__
                try:
                    client.close()
                except Exception:
                    pass
                time.sleep(3 * cleanup_attempt)
                try:
                    client = base.api_session()
                except Exception as exc:
                    cleanup_error = type(exc).__name__
                    client = None
                    break
            if not record["owned_pod_absent_verified"]:
                record["status"], record["cleanup_error_type"] = "failed", cleanup_error or "OwnedPodRemains"
                print("cleanup_failure error_type=" + str(record["cleanup_error_type"]), flush=True)
            else:
                print("cleanup_reconciled owned_pod_absent=true", flush=True)
            if client is not None:
                client.close()
        elapsed = time.time() - started
        rate = float((record.get("quote") or {}).get("rate_usd_per_hour", 0))
        cost = rate * elapsed / 3600 if record.get("pod_created") else 0.0
        record["elapsed_seconds"], record["estimated_compute_cost_usd"] = elapsed, cost
        record["finished_utc"] = utc_now()
        if prior_spend + cost > TOTAL_CAP:
            record["status"], record["budget_error"] = "failed", "estimated compute cost exceeded authorization"
        atomic_json(run_dir / "RUN.json", record)
        if record.get("owned_pod_absent_verified"):
            atomic_json(done_path, {"finished_utc": utc_now(), "owned_pod_absent_verified": True})
    passed = record.get("status") == "passed" and record.get("owned_pod_absent_verified")
    print(f"run_passed={str(bool(passed)).lower()} estimated_compute_cost_usd={record['estimated_compute_cost_usd']:.4f}", flush=True)
    return 0 if passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify-local", "preflight", "run"))
    args = parser.parse_args()
    if args.command == "verify-local":
        frozen = verify_local_authorization()
        print(json.dumps({"status": "passed", "proposal_id": PROPOSAL_ID,
                          "proposal_identity": PROPOSAL_IDENTITY, "bundle_sha256": sha256(frozen["bundle"]),
                          "resource_writes": 0}, indent=2))
    elif args.command == "preflight":
        print(json.dumps(preflight(), indent=2))
    else:
        raise SystemExit(run())


if __name__ == "__main__":
    main()
