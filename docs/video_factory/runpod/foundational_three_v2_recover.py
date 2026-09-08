"""Recover monitoring/download for the existing v2 pod without creating a resource."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys
import time
from typing import Any


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import foundational_three_v2_execute as wrapper  # noqa: E402

wrapper.configure()
c = wrapper.controller

RUN_DIR = c.PACKAGE_ROOT / "remote" / "runpod-foundational-three-v2-20260901-112500"
STATE_PATH = RUN_DIR / "controller_state.json"
RECORD_PATH = RUN_DIR / "RUN.json"
DONE_PATH = RUN_DIR / "controller_done.json"


def pod_elapsed_seconds(pod: dict[str, Any]) -> float:
    raw = str(pod.get("createdAt") or pod.get("lastStartedAt") or "")
    try:
        started = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc) - started).total_seconds())
    except ValueError:
        return 0.0


def remote_status(ssh: Any, token: str) -> str:
    command = (
        "if [ -f /workspace/foundational-job.exit ]; then printf 'EXIT:'; cat /workspace/foundational-job.exit; "
        "elif [ -f /workspace/foundational-job.pid ] && kill -0 \"$(cat /workspace/foundational-job.pid)\" 2>/dev/null; "
        "then echo RUNNING; else echo LOST; fi"
    )
    return c.remote_capture(ssh, command, token)


def retrieve_log(ssh: Any) -> None:
    try:
        with ssh.open_sftp() as sftp:
            sftp.get("/workspace/foundational-job.log", str(RUN_DIR / "remote-render.log"))
    except Exception:
        pass


def download_and_verify(ssh: Any) -> dict[str, Any]:
    archive = RUN_DIR / "foundational-three-results.zip"
    digest_file = RUN_DIR / "foundational-three-results.zip.sha256"
    with ssh.open_sftp() as sftp:
        stat = sftp.stat("/workspace/foundational-three-results.zip")
        if stat.st_size <= 0 or stat.st_size > 500_000_000:
            raise RuntimeError("remote result archive exceeds the approved safety limit")
        sftp.get("/workspace/foundational-three-results.zip", str(archive))
        sftp.get("/workspace/foundational-three-results.zip.sha256", str(digest_file))
    remote_digest = digest_file.read_text("utf-8").strip().split()[0]
    if not re.fullmatch(r"[0-9a-f]{64}", remote_digest) or remote_digest != c.sha256(archive):
        raise RuntimeError("downloaded archive hash disagrees with the remote digest")
    results_root = RUN_DIR / "results"
    if results_root.exists():
        raise RuntimeError("results destination already exists; refusing to overwrite")
    c.safe_extract_zip(archive, results_root)
    return c.verify_results(results_root, remote_digest)


def cleanup(client: Any, name: str, pod_id: str, record: dict[str, Any]) -> tuple[Any, bool]:
    events = c.base.Events(RUN_DIR / "recovery-lifecycle.jsonl")
    error = None
    for attempt in range(1, 6):
        try:
            absent = c.base.delete_owned(client, name, pod_id, events)
            if absent:
                record["owned_pod_absent_verified"] = True
                return client, True
            error = "OwnedPodRemains"
        except Exception as exc:
            error = type(exc).__name__
        try:
            client.close()
        except Exception:
            pass
        time.sleep(3 * attempt)
        try:
            client = c.base.api_session()
        except Exception as exc:
            error = type(exc).__name__
            client = None
            break
    record["cleanup_error_type"] = error or "OwnedPodRemains"
    return client, False


def run() -> int:
    c.verify_local_authorization()
    state = json.loads(STATE_PATH.read_text("utf-8"))
    record = json.loads(RECORD_PATH.read_text("utf-8"))
    pod_id, name = state.get("pod_id"), state.get("pod_name")
    if not isinstance(pod_id, str) or not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
        raise RuntimeError("durable state has no valid existing pod id")
    if name != record.get("pod_name") or not name.startswith(c.POD_NAME_PREFIX):
        raise RuntimeError("durable state pod identity mismatch")
    client, ssh, token = None, None, ""
    terminal = False
    verified = False
    pod_elapsed = 0.0
    try:
        client = c.base.api_session()
        matches = c.base.owned(client, name, pod_id)
        if matches != {pod_id}:
            raise RuntimeError("the exact existing pod is absent or ambiguous")
        pod = c.base.pod_detail(client, pod_id)
        shape = c.verified_shape(pod, pod_id, name, c.RATE_CAP)
        environment = pod.get("env") or {}
        token = str(environment.get("CM_BOOTSTRAP_TOKEN") or "") if isinstance(environment, dict) else ""
        if not token or any(character.isspace() for character in token):
            raise RuntimeError("existing pod bootstrap credential reference is unavailable")
        pod_elapsed = pod_elapsed_seconds(pod)
        record["pod_created"] = True
        record["pod_id"] = pod_id
        record["actual_resources"] = shape
        record["recovery_attached_utc"] = c.utc_now()
        record["credential_value_recorded"] = False
        c.atomic_json(RECORD_PATH, record)
        ssh, shape = c.wait_for_ssh(client, pod_id, name, token, c.RATE_CAP, timeout=180)
        status = remote_status(ssh, token)
        print("existing_pod_verified", flush=True)
        print("remote_job_status=" + status, flush=True)
        if status == "RUNNING":
            deadline = min(float(state["cleanup_epoch"]) - 180, time.time() + c.MAX_RUNTIME_SECONDS)
            ssh = c.wait_detached_render(client, pod_id, name, token, c.RATE_CAP, ssh, deadline)
            status = remote_status(ssh, token)
        if status == "EXIT:0":
            retrieve_log(ssh)
            verification = download_and_verify(ssh)
            c.atomic_json(RUN_DIR / "LOCAL_VERIFICATION.json", verification)
            record["downloaded"] = True
            record["verified"] = True
            record["verification"] = verification
            record["download_archive_sha256"] = verification["download_archive_sha256"]
            record["download_archive_bytes"] = (RUN_DIR / "foundational-three-results.zip").stat().st_size
            record["status"] = "passed"
            verified = terminal = True
            print("results_verified episodes=3", flush=True)
        elif status.startswith("EXIT:") or status == "LOST":
            retrieve_log(ssh)
            record["status"] = "failed"
            record["error"] = "remote render terminal status: " + status
            terminal = True
            print("remote_render_terminal_failure status=" + status, flush=True)
        else:
            raise RuntimeError("remote status is neither running nor terminal")
    except Exception as exc:
        record["recovery_error_type"] = type(exc).__name__
        record["recovery_error"] = str(exc)
        record["status"] = "monitor_interrupted_preserved"
        print("recovery_monitor_interrupted pod_preserved=true error_type=" + type(exc).__name__, flush=True)
    finally:
        if ssh is not None:
            ssh.close()
        if terminal and client is not None:
            client, absent = cleanup(client, name, pod_id, record)
            if absent:
                print("cleanup_reconciled owned_pod_absent=true", flush=True)
                c.atomic_json(DONE_PATH, {"finished_utc": c.utc_now(), "owned_pod_absent_verified": True,
                                          "recovered_controller": True})
            else:
                record["status"] = "failed"
                print("cleanup_failure pod_may_remain=true", flush=True)
        if client is not None:
            client.close()
        if pod_elapsed <= 0 and record.get("actual_resources"):
            pod_elapsed = max(0.0, time.time() - float(state["cleanup_epoch"]) + c.MAX_RUNTIME_SECONDS)
        record["estimated_compute_cost_usd"] = c.RATE_CAP * pod_elapsed / 3600
        record["finished_utc"] = c.utc_now() if terminal else None
        record["credential_value_recorded"] = False
        c.atomic_json(RECORD_PATH, record)
    return 0 if verified and record.get("owned_pod_absent_verified") else 1


if __name__ == "__main__":
    raise SystemExit(run())
