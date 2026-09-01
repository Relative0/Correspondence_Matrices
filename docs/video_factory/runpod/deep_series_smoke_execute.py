"""Execute the exactly authorized first-five two-chapter smoke on RunPod."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tarfile
import time
from typing import Any
from urllib.parse import quote as urlquote
import uuid
import zipfile


HERE = Path(__file__).resolve().parent
FACTORY = HERE.parent
ROOT = FACTORY.parents[1]
SMOKE_ROOT = HERE / "deep_series_smoke_v1"
sys.path.insert(0, str(HERE))
import execute_approved_v4 as base  # noqa: E402


PROPOSAL_ID = "cm-video-deep-series-first5-smoke-remote-v1"
AUTHORIZATION_ID = PROPOSAL_ID + "-auth"
GPU_ID = "NVIDIA RTX A5000"
GPU_COUNT = 1
IMAGE = ("python:3.10.15-slim-bookworm@sha256:"
         "97ff6fda70178dee6c144d41030fb88b6ec86d75e1c517fe96b8f62094ea7ac2")
CONTAINER_DISK_GB = 30
MIN_VCPU = 4
MIN_RAM_GB = 8
RATE_CAP = 0.27
TOTAL_CAP = 2.0
MAX_CREATES = 2
MAX_RUNTIME_SECONDS = 10800
EXPECTED_JOBS = (
    "conceptual-vs-measured-c01-smoke",
    "what-is-explicit-cm-c01-smoke",
)
APPROVAL_PATH = FACTORY / "deep_series" / "production_planning" / "content_approval.json"
APPROVAL_SCOPE = "production_planning_only"
PROPOSAL_STATUS = "exact_authorization_requested"
POD_NAME_PREFIX = "cm-video-first5-smoke-v1-"
RUN_ID_PREFIX = "runpod-first5-smoke-v1-"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    proposal_path = SMOKE_ROOT / "proposal.json"
    authorization_path = SMOKE_ROOT / "authorization.json"
    proposal = json.loads(proposal_path.read_text("utf-8"))
    authorization = json.loads(authorization_path.read_text("utf-8"))
    record = json.loads((SMOKE_ROOT / "bundle_record.json").read_text("utf-8"))
    approval = json.loads(APPROVAL_PATH.read_text("utf-8"))
    immutable = proposal["immutable_inputs"]
    content = proposal["content_identity"]
    bundle = SMOKE_ROOT / immutable["bundle_file"]
    batch = SMOKE_ROOT / "batch_manifest.json"
    proposal_file_sha256 = sha256(proposal_path)
    authorization_file_sha256 = authorization.get(
        "proposal_file_sha256", authorization.get("proposal_sha256")
    )
    proposal_identity = proposal.get("proposal_sha256")
    authorization_identity = authorization.get("proposal_identity")
    checks = (
        proposal["proposal_id"] == PROPOSAL_ID,
        proposal["status"] == PROPOSAL_STATUS,
        proposal["remote_or_paid_work_authorized"] is False,
        authorization["authorization_id"] == AUTHORIZATION_ID,
        authorization["proposal_id"] == PROPOSAL_ID,
        authorization["status"] == "approved",
        authorization["remote_or_paid_work_authorized"] is True,
        authorization_file_sha256 == proposal_file_sha256,
        (
            proposal_identity is None
            and authorization_identity is None
            or isinstance(proposal_identity, str)
            and authorization_identity == proposal_identity
        ),
        authorization["bundle_sha256"] == immutable["bundle_sha256"] == record["bundle_sha256"] == sha256(bundle),
        authorization["batch_manifest_sha256"] == immutable["batch_manifest_sha256"] == record["batch_manifest_sha256"] == sha256(batch),
        authorization["bible_content_hash"] == content["bible_content_hash"] == approval["bible_content_hash"],
        authorization["review_manifest_sha256"] == content["review_manifest_sha256"] == approval["review_manifest_sha256"],
        approval["status"] == "approved",
        approval["scope"] == APPROVAL_SCOPE,
        approval["content_approval_authorizes_remote_or_paid_work"] is False,
        authorization["maximum_total_runpod_spend_usd"] == proposal["authorization_ceiling"]["maximum_total_runpod_spend_usd"] == TOTAL_CAP,
        authorization["maximum_pod_creates"] == proposal["authorization_ceiling"]["maximum_pod_creates"] == MAX_CREATES,
        proposal["authorization_ceiling"]["maximum_parallel_pods"] == 1,
        proposal["authorization_ceiling"]["maximum_runtime_seconds_per_pod"] == MAX_RUNTIME_SECONDS,
        proposal["quote"]["rate_cap_usd_per_hour"] == RATE_CAP,
        proposal["resource"]["gpu_id"] == GPU_ID,
        tuple(record["ordered_job_ids"]) == EXPECTED_JOBS,
        record["cloud_uploaded"] is False,
        record["runpod_resource_created"] is False,
    )
    if not all(checks):
        raise RuntimeError("local authorization identities or ceilings disagree")
    with zipfile.ZipFile(bundle) as archive:
        manifest = json.loads(archive.read("package_manifest.json"))
        if manifest["payload_sha256"] != immutable["payload_sha256"]:
            raise RuntimeError("approved payload identity changed")
        if hashlib.sha256(archive.read("cm/batch_manifest.json")).hexdigest() != immutable["batch_manifest_sha256"]:
            raise RuntimeError("approved archived batch changed")
    return {"proposal": proposal, "authorization": authorization, "bundle": bundle, "batch": batch}


def gpu_catalog(client: Any) -> dict[str, Any]:
    body = base.request_json(
        client, "GET", base.V2 + "/catalog/gpus/" + urlquote(GPU_ID, safe=""),
        params={"include": "AVAILABILITY", "product": "POD", "cloud": "SECURE", "count": GPU_COUNT},
        timeout=20,
    )
    rate = float((body.get("price") or {}).get("secure", "nan")) * GPU_COUNT
    availability = body.get("availability")
    if (
        body.get("id") != GPU_ID
        or body.get("secure") is not True
        or not math.isfinite(rate)
        or not 0 < rate <= RATE_CAP
    ):
        raise RuntimeError("approved Secure GPU catalog identity or rate changed")
    return {
        "gpu_id": GPU_ID,
        "gpu_count": GPU_COUNT,
        "availability": availability,
        "rate_usd_per_hour": rate,
        "checked_utc": utc_now(),
        "data_centers": [item.get("id") for item in body.get("dataCenters") or []],
    }


def quote_gpu(client: Any) -> dict[str, Any]:
    offer = gpu_catalog(client)
    if offer["availability"] not in {"LOW", "MEDIUM", "HIGH"}:
        raise RuntimeError("approved Secure GPU offer is unavailable")
    return offer


def wait_for_gpu_offer(client: Any, timeout: int = 1200) -> dict[str, Any]:
    deadline = time.time() + timeout
    check = 0
    while time.time() < deadline:
        check += 1
        offer = gpu_catalog(client)
        print(
            f"capacity_check={check} availability={offer['availability']} "
            f"rate={offer['rate_usd_per_hour']:.2f}",
            flush=True,
        )
        if offer["availability"] in {"LOW", "MEDIUM", "HIGH"}:
            return offer
        time.sleep(15)
    raise RuntimeError("approved Secure GPU capacity did not return within the bounded watch")


def account_ready(client: Any) -> dict[str, bool]:
    body = base.request_json(
        client, "POST", "https://api.runpod.io/graphql",
        json={"query": "query { myself { clientBalance currentSpendPerHr spendLimit } }"},
        timeout=20,
    )
    if body.get("errors"):
        raise RuntimeError("account readiness query failed")
    account = body["data"]["myself"]
    balance = float(account["clientBalance"])
    current = float(account["currentSpendPerHr"])
    raw_limit = account.get("spendLimit")
    balance_ok = math.isfinite(balance) and balance >= TOTAL_CAP
    limit_ok = raw_limit is None or (
        math.isfinite(float(raw_limit)) and math.isfinite(current)
        and float(raw_limit) >= current + RATE_CAP
    )
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
        "name": name,
        "computeType": "GPU",
        "cloudType": "SECURE",
        "imageName": IMAGE,
        "gpuTypeIds": [GPU_ID],
        "gpuTypePriority": "custom",
        "gpuCount": GPU_COUNT,
        "containerDiskInGb": CONTAINER_DISK_GB,
        "volumeInGb": 0,
        "volumeMountPath": "/workspace",
        "ports": ["22/tcp"],
        "supportPublicIp": True,
        "interruptible": False,
        "locked": False,
        "env": {
            "CM_BOOTSTRAP_TOKEN": token,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
            "CM_VIDEO_BUNDLE_ROOT": "/opt/cm-video/bundle",
            "POP_VIDEO_FFMPEG": "/usr/bin/ffmpeg",
        },
        "dockerEntrypoint": ["sh", "-c"],
        "dockerStartCmd": [start],
    }


def verified_shape(pod: dict[str, Any], pod_id: str, name: str, quoted_rate: float) -> dict[str, Any]:
    machine = pod.get("machine") or {}
    gpu = pod.get("gpu") or {}
    images = [pod.get(key) for key in ("image", "imageName") if pod.get(key) is not None]
    rate = float(pod.get("costPerHr", "nan"))
    ports = sorted(pod.get("ports") or [])
    secure = machine.get("secureCloud") is True or pod.get("cloudType") == "SECURE" or pod.get("cloud") == "SECURE"
    gpu_id = gpu.get("id") or machine.get("gpuTypeId")
    gpu_count = gpu.get("count", pod.get("gpuCount"))
    vcpu = float(pod.get("vcpuCount", "nan"))
    ram = float(pod.get("memoryInGb", "nan"))
    if (
        pod.get("id") != pod_id
        or pod.get("name") != name
        or gpu_id != GPU_ID
        or gpu_count not in (None, GPU_COUNT)
        or not math.isfinite(vcpu) or vcpu < MIN_VCPU
        or not math.isfinite(ram) or ram < MIN_RAM_GB
        or pod.get("containerDiskInGb") != CONTAINER_DISK_GB
        or pod.get("volumeInGb") not in (None, 0)
        or pod.get("networkVolume")
        or ports != ["22/tcp"]
        or not images or any(image != IMAGE for image in images)
        or not secure
        or not math.isfinite(rate) or rate != quoted_rate or rate > RATE_CAP
    ):
        raise RuntimeError("created pod differs from the approved shape or quote")
    return {
        "pod_id": pod_id,
        "gpu_id": GPU_ID,
        "gpu_count": GPU_COUNT,
        "vcpu": vcpu,
        "ram_gb": ram,
        "container_disk_gb": CONTAINER_DISK_GB,
        "volume_gb": 0,
        "ports": ["22/tcp"],
        "image": images[0],
        "secure_cloud": secure,
        "rate_usd_per_hour": rate,
    }


def wait_for_ssh(client: Any, pod_id: str, name: str, token: str, rate: float, timeout: int = 600) -> tuple[Any, dict[str, Any]]:
    deadline = time.time() + timeout
    last_error = "not ready"
    while time.time() < deadline:
        try:
            pod = base.pod_detail(client, pod_id)
            shape = verified_shape(pod, pod_id, name, rate)
            mappings = pod.get("portMappings") or {}
            port = mappings.get("22") if isinstance(mappings, dict) else None
            port = port if port is not None else mappings.get(22) if isinstance(mappings, dict) else None
            ip = pod.get("publicIp")
            if ip and port:
                ssh = base.paramiko.SSHClient()
                ssh.set_missing_host_key_policy(base.paramiko.AutoAddPolicy())
                ssh.connect(str(ip), port=int(port), username="root", password=token,
                            look_for_keys=False, allow_agent=False, timeout=15,
                            banner_timeout=15, auth_timeout=15)
                ssh.get_transport().set_keepalive(15)
                key = ssh.get_transport().get_remote_server_key()
                shape["ssh_host_key_sha256"] = hashlib.sha256(key.asbytes()).hexdigest()
                return ssh, shape
        except Exception as exc:
            last_error = type(exc).__name__
        time.sleep(6)
    raise RuntimeError("SSH did not become ready; last error type: " + last_error)


def verify_results(extracted: Path, payload_sha256: str) -> dict[str, Any]:
    batch_path = extracted / "results" / "batch_result.json"
    batch = json.loads(batch_path.read_text("utf-8"))
    if batch.get("passed") is not True or tuple(item["job_id"] for item in batch["jobs"]) != EXPECTED_JOBS:
        raise RuntimeError("downloaded batch result does not match the approved jobs")
    media = []
    for job_id in EXPECTED_JOBS:
        root = extracted / "results" / job_id
        result = json.loads((root / "render_result.json").read_text("utf-8"))
        video = root / f"{job_id}.mp4"
        manifest = video.with_suffix(".manifest.json")
        if (
            result.get("passed") is not True
            or result.get("status") != "passed"
            or result.get("job_id") != job_id
            or result.get("bundle_payload_sha256") != payload_sha256
            or sha256(video) != result["outputs"]["video_sha256"]
            or sha256(manifest) != result["outputs"]["encode_manifest_sha256"]
        ):
            raise RuntimeError("downloaded smoke output identity mismatch")
        for name, digest in result["preview_frame_hashes"].items():
            if sha256(root / "previews" / f"{name}.png") != digest:
                raise RuntimeError("downloaded preview identity mismatch")
        repeat_paths = sorted((root / "repeat-frame").glob("f*.png"))
        repeat = result["repeat_frame_determinism"]
        if len(repeat_paths) != 2 or repeat["identical"] is not True or [sha256(path) for path in repeat_paths] != repeat["hashes"]:
            raise RuntimeError("repeat-frame determinism evidence mismatch")
        tech = result["technical_observations"]
        if (
            (tech.get("width"), tech.get("height"), round(float(tech.get("fps", 0)))) != (1920, 1080, 30)
            or tech.get("codec") != "h264"
            or tech.get("has_audio") is not False
        ):
            raise RuntimeError("downloaded media contract mismatch")
        media.append({
            "job_id": job_id,
            "video": str(video),
            "video_sha256": result["outputs"]["video_sha256"],
            "duration_s": tech["duration_s"],
            "render_wall_seconds": result["timing"]["render_wall_seconds"],
            "frames_per_second": result["timing"]["frames_per_second"],
        })
    return {"status": "passed", "jobs": len(media), "media": media, "bundle_payload_sha256": payload_sha256}


def arm_watchdog(run_dir: Path, name: str, deadline: float) -> tuple[subprocess.Popen[bytes], Path, Path, Path]:
    state_path = run_dir / "controller_state.json"
    done_path = run_dir / "controller_done.json"
    ack_path = run_dir / "watchdog_ack.json"
    state = {
        "schema_version": "1.0",
        "proposal_id": PROPOSAL_ID,
        "authorization_id": AUTHORIZATION_ID,
        "pod_name": name,
        "pod_id": None,
        "cleanup_epoch": deadline,
    }
    atomic_json(state_path, state)
    with (run_dir / "watchdog.stdout.log").open("wb") as stdout, (run_dir / "watchdog.stderr.log").open("wb") as stderr:
        process = subprocess.Popen(
            [sys.executable, str(HERE / "runpod_watchdog.py"), "--state", str(state_path),
             "--done", str(done_path), "--events", str(run_dir / "watchdog.jsonl"),
             "--ack", str(ack_path)],
            cwd=ROOT, stdout=stdout, stderr=stderr,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    limit = time.time() + 25
    while time.time() < limit and not ack_path.is_file():
        if process.poll() is not None:
            raise RuntimeError("watchdog exited before readiness")
        time.sleep(0.25)
    if not ack_path.is_file():
        raise RuntimeError("watchdog did not acknowledge readiness")
    ack = json.loads(ack_path.read_text("utf-8"))
    if (
        ack.get("status") != "armed"
        or ack.get("authorization_id") != AUTHORIZATION_ID
        or ack.get("pod_name") != name
        or ack.get("deadline_epoch") != deadline
        or ack.get("state_sha256") != sha256(state_path)
    ):
        raise RuntimeError("watchdog acknowledgement mismatch")
    return process, state_path, done_path, ack_path


def run_attempt(
    client: Any, frozen: dict[str, Any], run_root: Path, attempt: int,
    spent_estimate: float, offer: dict[str, Any],
) -> tuple[dict[str, Any], float]:
    run_dir = run_root / f"attempt-{attempt}"
    run_dir.mkdir(parents=True, exist_ok=False)
    name = f"{POD_NAME_PREFIX}a{attempt}-" + uuid.uuid4().hex[:10]
    token = secrets.token_urlsafe(32)
    started = time.time()
    deadline = started + MAX_RUNTIME_SECONDS
    watchdog, state_path, done_path, _ack = arm_watchdog(run_dir, name, deadline)
    pod_id: str | None = None
    ssh = None
    record: dict[str, Any] = {
        "schema_version": "1.0",
        "proposal_id": PROPOSAL_ID,
        "authorization_id": AUTHORIZATION_ID,
        "attempt": attempt,
        "pod_name": name,
        "status": "started",
        "started_utc": utc_now(),
        "creation_attempted": False,
        "pod_created": False,
        "owned_pod_absent_verified": False,
        "credential_value_recorded": False,
    }
    print(f"attempt={attempt} watchdog_armed", flush=True)
    try:
        account = account_ready(client)
        if spent_estimate + offer["rate_usd_per_hour"] * MAX_RUNTIME_SECONDS / 3600 > TOTAL_CAP:
            raise RuntimeError("remaining approved spend cannot cover this attempt ceiling")
        record["quote"] = offer
        record["account_readiness"] = account
        if base.owned(client, name, None):
            raise RuntimeError("owned name unexpectedly exists before create")
        record["creation_attempted"] = True
        print(f"attempt={attempt} quote_verified rate={offer['rate_usd_per_hour']:.2f} availability={offer['availability']}", flush=True)
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
        record["pod_created"] = True
        record["pod_id"] = pod_id
        print(f"attempt={attempt} pod_created waiting_for_shape_and_ssh", flush=True)
        ssh, shape = wait_for_ssh(client, pod_id, name, token, offer["rate_usd_per_hour"])
        record["actual_resources"] = shape
        atomic_json(run_dir / "POD_RESOURCE_CHECK.json", shape)
        print(f"attempt={attempt} shape_and_ssh_verified", flush=True)
        base.upload_bundle(ssh, frozen["bundle"], token, run_dir / "ssh-mkdir.log")
        base.remote_command(
            ssh,
            "printf '%s  %s\\n' '" + frozen["proposal"]["immutable_inputs"]["bundle_sha256"] + "' '/workspace/input/bundle.zip' | sha256sum --check -",
            run_dir / "remote-bundle-verify.log", token, 90,
        )
        record["uploaded"] = True
        print(f"attempt={attempt} bundle_uploaded_and_verified", flush=True)
        remaining = max(60, int(deadline - time.time() - 120))
        bootstrap = (
            "unzip -p /workspace/input/bundle.zip runpod/deep_series_smoke_bootstrap.sh > /tmp/cm-video-smoke-bootstrap.sh && "
            "chmod 700 /tmp/cm-video-smoke-bootstrap.sh && "
            "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright /bin/sh /tmp/cm-video-smoke-bootstrap.sh "
            "/workspace/input/bundle.zip " + frozen["proposal"]["immutable_inputs"]["bundle_sha256"] + " /opt/cm-video/bundle"
        )
        print(f"attempt={attempt} remote_bootstrap_started", flush=True)
        base.remote_command(ssh, bootstrap, run_dir / "remote-bootstrap.log", token, min(2400, remaining))
        print(f"attempt={attempt} remote_bootstrap_passed", flush=True)
        remaining = max(60, int(deadline - time.time() - 120))
        command = (
            "set -u; "
            "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 "
            "python /opt/cm-video/bundle/runpod/deep_series_smoke_batch.py "
            "--bundle-root /opt/cm-video/bundle --output-root /workspace/results --timeout 7200 & "
            "batch_pid=$!; "
            "while kill -0 \"$batch_pid\" 2>/dev/null; do echo CM_BATCH_HEARTBEAT; sleep 20; done; "
            "wait \"$batch_pid\""
        )
        print(f"attempt={attempt} remote_batch_started", flush=True)
        base.remote_command(ssh, command, run_dir / "remote-batch.log", token, remaining)
        print(f"attempt={attempt} remote_batch_passed", flush=True)
        base.remote_command(ssh, "tar -C /workspace -czf /workspace/cm-video-smoke-results.tar.gz results",
                            run_dir / "remote-archive.log", token, 300)
        archive = run_dir / "cm-video-smoke-results.tar.gz"
        with ssh.open_sftp() as sftp:
            stat = sftp.stat("/workspace/cm-video-smoke-results.tar.gz")
            if stat.st_size <= 0 or stat.st_size > 300_000_000:
                raise RuntimeError("remote result archive exceeds the approved safety limit")
            sftp.get("/workspace/cm-video-smoke-results.tar.gz", str(archive))
        record["download_archive_sha256"] = sha256(archive)
        record["download_archive_bytes"] = archive.stat().st_size
        extracted = run_dir / "extracted"
        base.safe_extract(archive, extracted)
        verification = verify_results(extracted, frozen["proposal"]["immutable_inputs"]["payload_sha256"])
        atomic_json(run_dir / "LOCAL_VERIFICATION.json", verification)
        record["verification"] = verification
        record["status"] = "passed"
        print(f"attempt={attempt} results_verified jobs={len(EXPECTED_JOBS)}", flush=True)
    except Exception as exc:
        record["status"] = "failed"
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)
        print(f"attempt={attempt} terminal_failure error_type={type(exc).__name__}", flush=True)
    finally:
        if ssh is not None:
            ssh.close()
        try:
            record["owned_pod_absent_verified"] = base.delete_owned(client, name, pod_id, base.Events(run_dir / "lifecycle.jsonl"))
        except Exception as exc:
            record["owned_pod_absent_verified"] = False
            record["cleanup_error_type"] = type(exc).__name__
        elapsed = time.time() - started
        rate = float((record.get("quote") or {}).get("rate_usd_per_hour", 0))
        cost = rate * elapsed / 3600 if record.get("pod_created") else 0.0
        record["elapsed_seconds"] = elapsed
        record["estimated_compute_cost_usd"] = cost
        record["finished_utc"] = utc_now()
        if not record["owned_pod_absent_verified"]:
            record["status"] = "failed"
        atomic_json(run_dir / "RUN.json", record)
        if record["owned_pod_absent_verified"]:
            atomic_json(done_path, {"finished_utc": utc_now(), "owned_pod_absent_verified": True})
        print(f"attempt={attempt} cleanup_reconciled owned_pod_absent={str(record['owned_pod_absent_verified']).lower()}", flush=True)
    return record, cost


def preflight() -> dict[str, Any]:
    frozen = verify_local_authorization()
    with base.api_session() as client:
        quote = quote_gpu(client)
        account = account_ready(client)
        inventory_clear = not any(
            str(pod.get("name", "")).startswith(POD_NAME_PREFIX)
            for api in (base.V1, base.V2) for pod in base.inventory(client, api)
        )
    if not inventory_clear:
        raise RuntimeError("an owned pod for this proposal already exists")
    return {
        "status": "passed",
        "proposal_id": PROPOSAL_ID,
        "bundle_sha256": sha256(frozen["bundle"]),
        "quote": quote,
        "account_readiness": account,
        "owned_inventory_clear": inventory_clear,
        "resource_writes": 0,
    }


def run() -> int:
    frozen = verify_local_authorization()
    run_id = RUN_ID_PREFIX + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_root = SMOKE_ROOT / "remote" / run_id
    run_root.mkdir(parents=True, exist_ok=False)
    prior_records = [
        json.loads(path.read_text("utf-8"))
        for path in (SMOKE_ROOT / "remote").glob("*/attempt-*/RUN.json")
    ] if (SMOKE_ROOT / "remote").is_dir() else []
    creates_consumed = sum(record.get("creation_attempted") is True for record in prior_records)
    spent = sum(float(record.get("estimated_compute_cost_usd", 0)) for record in prior_records)
    if creates_consumed >= MAX_CREATES or spent >= TOTAL_CAP:
        raise RuntimeError("the proposal's cross-run create or spend ceiling is already consumed")
    records = []
    with base.api_session() as client:
        while creates_consumed < MAX_CREATES and spent < TOTAL_CAP:
            offer = wait_for_gpu_offer(client)
            attempt = creates_consumed + 1
            record, cost = run_attempt(client, frozen, run_root, attempt, spent, offer)
            records.append(record)
            spent += cost
            if record.get("creation_attempted") is True:
                creates_consumed += 1
            if record["status"] == "passed" and record["owned_pod_absent_verified"]:
                break
            if not record["owned_pod_absent_verified"] or spent >= TOTAL_CAP:
                break
            if record.get("creation_attempted") is not True:
                break
    summary = {
        "schema_version": "1.0",
        "proposal_id": PROPOSAL_ID,
        "authorization_id": AUTHORIZATION_ID,
        "run_id": run_id,
        "attempts": len(records),
        "pod_creates_consumed_total": creates_consumed,
        "estimated_compute_cost_usd": spent,
        "maximum_total_runpod_spend_usd": TOTAL_CAP,
        "passed": bool(records and records[-1]["status"] == "passed" and records[-1]["owned_pod_absent_verified"]),
        "owned_pod_absent_verified": all(record["owned_pod_absent_verified"] for record in records),
        "finished_utc": utc_now(),
    }
    atomic_json(run_root / "RUN_SUMMARY.json", summary)
    print(f"run_root={run_root}", flush=True)
    print(f"run_passed={str(summary['passed']).lower()} attempts={summary['attempts']} estimated_compute_cost_usd={spent:.4f}", flush=True)
    return 0 if summary["passed"] else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "run"))
    args = parser.parse_args()
    if args.command == "preflight":
        print(json.dumps(preflight(), indent=2))
    else:
        raise SystemExit(run())


if __name__ == "__main__":
    main()
