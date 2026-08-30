"""Execute the frozen, explicitly authorized C16 Linux confirmation."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD_PATH = ROOT / "docs/recognition/c7_linux_confirmation/runpod_c7_linux_single_port_controller.py"
spec = importlib.util.spec_from_file_location("c7_transport", OLD_PATH)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
preflight, base = transport.preflight, transport.base

OUT = HERE / "runpod-c16-linux-execute-001"
MANIFEST = HERE / "c16_linux_upload_manifest.json"
AUTHORIZATION = HERE / "RUNPOD_C16_LINUX_AUTHORIZED_2026_08_30.json"
PROTOCOL = HERE / "C16_SECOND_MACHINE_TIMING_PROTOCOL_2026_08_30.md"
LOCAL_VALIDATION = HERE / "C16_PACKAGE_LOCAL_VALIDATION_20260830.json"
DATASET = HERE / "c16_dataset.json"
NUMPY_REQUIREMENT = transport.NUMPY_REQUIREMENT

old_command = (
    "emit('stage', name='yosys-c7-linux-confirmation')\n"
    "    run('yosys-c7-linux-confirmation', [sys.executable, '-B',\n"
    "         'scripts/crse_yosys_source_anf_linux_confirmation.py', '--dataset',\n"
    "         'study/yosys-c7-dataset.json', '--output',\n"
    "         str(OUT/'yosys-c7-linux-confirmation'), '--repetitions', '9'], 420)"
)
new_command = (
    "emit('stage', name='yosys-c7-linux-confirmation')\n"
    "    run('yosys-c7-linux-confirmation', [sys.executable, '-B',\n"
    "         'scripts/crse_gf2_screening_linux_confirmation.py', '--dataset',\n"
    "         'study/c16-dataset.json', '--output',\n"
    "         str(OUT/'c16-linux-confirmation'), '--repetitions', '3'], 420)"
)
base.REMOTE_CODE = transport.replace_remote_once(base.REMOTE_CODE, old_command, new_command)
base.REMOTE_CODE = transport.replace_remote_once(
    base.REMOTE_CODE,
    "OUT / 'yosys-c7-linux-confirmation/summary.json'",
    "OUT / 'c16-linux-confirmation/summary.json'",
)


def configure_transport_paths() -> None:
    transport.OUT = OUT
    base.OUT = OUT
    transport.MANIFEST_PATH = MANIFEST
    transport.AUTHORIZATION_PATH = AUTHORIZATION
    transport.PROPOSAL_PATH = PROTOCOL
    for name, filename in {
        "STATE": "controller-state.json", "IDENTITY": "POD-IDENTITY.json",
        "READY": "watchdog-ready.json", "STATE_ACK": "watchdog-state-ack.json",
        "DONE": "watchdog-done.json", "ABORT": "abort-requested.json",
    }.items():
        setattr(transport, name, OUT / filename)


configure_transport_paths()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_authorization() -> dict:
    authorization = load(AUTHORIZATION)
    manifest = load(MANIFEST)
    expected = {"schema": "crse-runpod-c16-linux-authorization/v1", "authorized": True,
        "user_total_ceiling_usd": 5.0, "controller_total_ceiling_usd": 0.05,
        "one_create": True, "no_replacement": True, "source_files": 18,
        "source_bytes": manifest["bytes"], "cases": 40, "repetitions": 3, "methods": 3,
        "https_ports": ["8080/http"], "vcpu_count": 2, "minimum_ram_gb": 4,
        "container_disk_gb": 12, "pod_volume_gb": 0, "network_volume": False,
        "cleanup_seconds": 600, "reconciliation_seconds": 720,
        "rate_cap_usd_per_hour": 0.25, "total_cost_cap_usd": 0.05,
        "same_pod_payload_attempt_limit": 6, "health_checks_before_upload": 2,
        "local_isolated_validation": "pass"}
    if any(authorization.get(key) != value for key, value in expected.items()):
        raise RuntimeError("C16 authorization scope mismatch")
    if (authorization.get("proposal_sha256") != sha(PROTOCOL)
            or authorization.get("upload_manifest_sha256") != sha(MANIFEST)
            or authorization.get("local_validation_sha256") != sha(LOCAL_VALIDATION)):
        raise RuntimeError("C16 authorization artifact hash mismatch")
    return authorization


def arm_watchdog():
    with (OUT / "watchdog.log").open("xb") as stream:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        proc = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "--watchdog"],
                                stdout=stream, stderr=subprocess.STDOUT,
                                creationflags=flags, close_fds=True)
    for _ in range(200):
        if transport.READY.exists():
            ready = load(transport.READY)
            if not ready.get("network_probe_passed") or any(ready["startup_inventories"].values()):
                raise RuntimeError("watchdog zero-pod network probe failed")
            transport.write(OUT / "WATCHDOG-PROCESS-BINDING.json", transport.bind_watchdog(proc, ready))
            return proc
        if proc.poll() is not None:
            raise RuntimeError("watchdog exited before readiness")
        time.sleep(.2)
    raise RuntimeError("watchdog failed to arm")


def save_evidence(log: str) -> dict:
    lines = log.splitlines()
    starts = [json.loads(line[9:]) for line in lines
              if line.startswith("CM_EVENT ") and '"kind": "evidence_start"' in line]
    if not starts:
        raise RuntimeError("remote evidence marker missing")
    plain = "\n".join(line for line in lines if not line.startswith("CM_EVIDENCE ")) + "\n"
    if len(plain.encode()) + int(starts[-1]["bytes"]) + int(starts[-1]["uncompressed_bytes"]) > transport.CAP:
        raise RuntimeError("saved C16 evidence exceeds cap")
    (OUT / "container.log").write_text(plain, encoding="utf-8")
    result = base.extract_evidence(lines)
    evidence = OUT / "evidence/run-output"
    validation = load(evidence / "REMOTE-VALIDATION.json")
    runtime = load(evidence / "RUNTIME.json")
    dependencies = load(evidence / "DEPENDENCIES.json")
    study = evidence / "c16-linux-confirmation"
    summary = load(study / "summary.json")
    rows = [json.loads(line) for line in (study / "measurements.jsonl").read_text(encoding="utf-8").splitlines()]
    methods = {"explicit_cm_exhaustive", "explicit_cm_screened", "packed_source_anf_screened"}
    documents = load(DATASET)["cases"]
    expected_keys = {(repetition, method, row["case_id"])
                     for repetition in range(3) for method in methods for row in documents}
    observed_keys = {(row.get("repetition"), row.get("method"), row.get("split"), row.get("case_id")) for row in rows}
    observed_keys = {(repetition, method, case_id) for repetition, method, _split, case_id in observed_keys}
    confirmation = validation.get("confirmation_summary", {})
    config = summary.get("config", {})
    if (validation.get("status") != "complete" or validation.get("error") is not None
        or confirmation.get("status") != "complete" or confirmation.get("semantic_mismatches") != 0
        or confirmation.get("criteria") != summary.get("criteria")
        or summary.get("schema") != "crse-c16-gf2-screened-tail-linux-confirmation/v1"
        or summary.get("status") != "complete" or summary.get("semantic_mismatches") != 0
        or summary.get("scientific_scope") != "second-machine timing of the frozen C16 exact-screened GF(2) tail"
        or config.get("cases") != 40 or config.get("repetitions") != 3
        or config.get("max_partitions") != 64 or config.get("materialize_budget") != 4
        or set(config.get("methods", [])) != methods
        or summary.get("criteria", {}).get("exact") is not True
        or summary.get("second_machine_gate") is not True
        or len(summary.get("functional_rows", [])) != 40 or len(rows) != 360
        or observed_keys != expected_keys
        or any(row.get("semantic_mismatches") != 0 or row.get("artifact_mismatches") != 0
               or any(type(row.get(field)) is not int or row[field] < 0
                      for field in ("representation_ns", "analysis_ns", "total_ns")) for row in rows)
        or dependencies.get("numpy") != "2.3.2" or runtime.get("source_files") != 18
        or runtime.get("runpod_pod_id") != load(transport.IDENTITY)["pod_id"]
        or runtime.get("image_tag") != base.IMAGE_TAG
        or runtime.get("image_amd64_digest") != base.IMAGE_AMD64_DIGEST):
        raise RuntimeError("retrieved evidence did not satisfy frozen C16 gates")
    result["validation"] = validation
    result["runtime_pod_id"] = runtime["runpod_pod_id"]
    result["c16_linux_confirmation"] = {"cases": 40, "repetitions": 3, "methods": 3,
        "measurement_rows": len(rows), "semantic_mismatches": 0,
        "criteria": summary["criteria"], "speedup": summary["speedup"],
        "median_case_sum_ns": summary["median_case_sum_ns"]}
    return result


def execute_remote_v2(pod_id: str, token: str, raw: bytes, created: float, record: dict) -> str:
    """Use two health observations and bounded same-pod retries for proxy 404."""
    endpoint = f"https://{pod_id}-8080.proxy.runpod.net"
    with transport.requests.Session() as proxy:
        proxy.trust_env = False
        proxy.headers["X-CM-Token"] = token
        proxy.headers["Content-Type"] = "application/octet-stream"
        consecutive_health = 0
        while time.time() < created + 240:
            try:
                health = json.loads(transport.proxy_request(proxy, "GET", endpoint + "/health", timeout=5))
                if health.get("service") == "cm-memory-http" and health.get("ready") is True:
                    consecutive_health += 1
                    if consecutive_health == 2:
                        break
                    time.sleep(2)
                    continue
            except (transport.requests.RequestException, RuntimeError, ValueError):
                pass
            consecutive_health = 0
            time.sleep(2)
        else:
            raise RuntimeError("HTTP bootstrap did not remain ready for two observations")
        record["bootstrap_ready_utc"] = preflight.utc_now()
        record["health_checks_before_upload"] = consecutive_health
        upload_events = []
        accepted = None
        for attempt in range(1, 7):
            try:
                accepted = json.loads(transport.proxy_request(
                    proxy, "POST", endpoint + "/payload", data=raw, timeout=20))
                upload_events.append({"attempt": attempt, "checked_utc": preflight.utc_now(),
                                      "status": "accepted"})
                break
            except RuntimeError as exc:
                upload_events.append({"attempt": attempt, "checked_utc": preflight.utc_now(),
                                      "status": str(exc)})
                if str(exc) != "proxy HTTP 404" or attempt == 6:
                    record["payload_attempts"] = upload_events
                    raise
                time.sleep(2)
                health = json.loads(transport.proxy_request(proxy, "GET", endpoint + "/health", timeout=5))
                if health.get("service") != "cm-memory-http" or health.get("ready") is not True:
                    record["payload_attempts"] = upload_events
                    raise RuntimeError("bootstrap health changed during payload retry")
        record["payload_attempts"] = upload_events
        if accepted.get("accepted_sha256") != hashlib.sha256(raw).hexdigest():
            raise RuntimeError("upload acknowledgement hash mismatch")
        record["uploaded_source_files"] = 18
        record["uploaded_transport_bytes"] = len(raw)
        transport.proxy_request(proxy, "POST", endpoint + "/run", data=b"", timeout=10)
        record["worker_started_utc"] = preflight.utc_now()
        observed = None
        while time.time() < created + transport.CLEANUP_AT - 30:
            try:
                progress = json.loads(transport.proxy_request(proxy, "GET", endpoint + "/progress", timeout=5))
            except transport.requests.RequestException:
                time.sleep(2)
                continue
            signature = (progress.get("stage"), progress.get("done"), progress.get("error"))
            if signature != observed:
                transport.append(OUT / "progress.jsonl", {"checked_utc": preflight.utc_now(), **progress})
                print(json.dumps({"stage": progress.get("stage"), "done": progress.get("done"),
                                  "error": progress.get("error")}), flush=True)
                observed = signature
            if progress.get("done"):
                record["remote_progress"] = progress
                return transport.proxy_request(proxy, "GET", endpoint + "/results",
                    cap=transport.CAP, timeout=20).decode("utf-8")
            if time.time() >= created + 300 and progress.get("stage") != "yosys-c7-linux-confirmation":
                raise RuntimeError("boot/install exceeded five-minute setup deadline")
            time.sleep(2)
    raise RuntimeError("remote worker deadline exceeded")


def run() -> int:
    record = {"started_utc": preflight.utc_now(), "status": "preflight", "creation_attempted": False,
              "creation_uncertain": False, "pod_created": False, "uploaded_source_files": 0,
              "automatic_replacement_queued": False}
    state = client = None
    try:
        local_validation = load(LOCAL_VALIDATION)
        if (local_validation.get("status") != "pass"
                or local_validation.get("initial_file_count") != 18
                or local_validation.get("manifest_sha256") != sha(MANIFEST)
                or local_validation.get("semantic_mismatches") != 0
                or local_validation.get("measurement_rows") != 360):
            raise RuntimeError("C16 package has not passed isolated local validation")
        authorization = require_authorization()
        record["authorization_record_sha256"] = sha(AUTHORIZATION)
        record["authorization_recorded_utc"] = authorization["recorded_utc"]
        ready = preflight.check()
        offer = ready.get("selected_offer")
        rate = float(offer["rate_usd_per_hour"]) if offer else float("nan")
        projected = (rate + transport.STORAGE_RATE_RESERVE) * transport.CLEANUP_AT / 3600
        ready["c16_budget"] = {"rate_usd_per_hour": rate, "projected_10_minute_cost_usd": projected,
            "total_cost_cap_usd": transport.CAMPAIGN_CAP,
            "ready": bool(math.isfinite(rate) and 0 < rate <= transport.RATE_CAP and projected <= transport.CAMPAIGN_CAP)}
        transport.write(OUT / "PREFLIGHT.json", ready)
        if not ready["ready"] or not ready["c16_budget"]["ready"] or any(ready["inventories"].values()):
            raise RuntimeError("current account/resource/budget preflight failed")
        manifest = load(MANIFEST)
        expected_command = ["python", "-B", "scripts/crse_gf2_screening_linux_confirmation.py",
            "--dataset", "study/c16-dataset.json", "--output",
            "run-output/c16-linux-confirmation", "--repetitions", "3"]
        if (manifest.get("schema") != "crse-c16-linux-confirmation-upload-manifest/v1"
                or manifest.get("file_count") != 18 or len(manifest.get("files", [])) != 18
                or manifest.get("bytes") != authorization["source_bytes"]
                or manifest.get("authorization_status") != "authorized_under_user_5_usd_ceiling"
                or manifest.get("command") != expected_command or manifest.get("network_during_workload") is not False
                or manifest.get("runtime") != {"architecture": "amd64", "image": base.IMAGE,
                    "numpy": "2.3.2", "python": "3.13.15", "numpy_requirement": NUMPY_REQUIREMENT}):
            raise RuntimeError("frozen C16 package mismatch")
        bundle = base.make_bundle(manifest)
        watchdog_process = arm_watchdog()
        client = preflight.session()
        if any(transport.inventories(client).values()):
            raise RuntimeError("zero-pod baseline changed before creation")
        created = time.time()
        # The shared, independently tested watchdog owns only this historical prefix.
        state = {"name": "cm-c7-linux-" + uuid.uuid4().hex[:12], "created_epoch": created,
                 "cleanup_epoch": created + transport.CLEANUP_AT,
                 "horizon_epoch": created + transport.HORIZON}
        raw = transport.prepare_payload(bundle, manifest, created)
        token = secrets.token_urlsafe(32)
        body = transport.create_payload(state["name"], offer, token, raw, created)
        transport.write(OUT / "TRANSPORT-FREEZE.json", {
            "controller_sha256": sha(Path(__file__)), "authorization_sha256": sha(AUTHORIZATION),
            "protocol_sha256": sha(PROTOCOL), "bootstrap_sha256": sha(transport.BOOTSTRAP_PATH),
            "source_bundle_sha256": hashlib.sha256(bundle).hexdigest(), "source_bundle_bytes": len(bundle),
            "source_files": 18, "source_bytes": manifest["bytes"],
            "transport_payload_sha256": hashlib.sha256(raw).hexdigest(), "transport_payload_bytes": len(raw),
            "manifest_sha256": sha(MANIFEST), "credentials_recorded_or_uploaded": False})
        transport.write(transport.STATE, state)
        transport.confirm_watchdog(watchdog_process, state)
        record.update({"creation_attempted": True, "creation_uncertain": True,
            "creation_request_utc": preflight.utc_now(), "creation_endpoint": preflight.V1 + "/pods",
            "name": state["name"], "selected_cpu": offer["id"],
            "quoted_rate_usd_per_hour": offer["rate_usd_per_hour"]})
        print(json.dumps({"action": "create_one_cpu_pod", "name": state["name"],
                          "cpu": offer["id"], "rate": offer["rate_usd_per_hour"]}), flush=True)
        response = client.post(preflight.V1 + "/pods", json=body, timeout=(10, 50), allow_redirects=False)
        record["creation_http_status"] = response.status_code
        if response.status_code not in (200, 201):
            record["creation_uncertain"] = not 400 <= response.status_code < 500
            raise RuntimeError("pod creation failed HTTP " + str(response.status_code))
        pod = response.json(); pod = pod.get("pod", pod); pod_id = pod.get("id")
        if not isinstance(pod_id, str) or not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
            raise RuntimeError("creation response has no valid pod ID")
        transport.write(transport.IDENTITY, {"pod_id": pod_id, "name": state["name"],
            "recorded_utc": preflight.utc_now(), "source": "this create response"})
        record.update({"pod_id": pod_id, "pod_created": True, "creation_uncertain": False})
        pod = transport.actual_pod(client, pod_id)
        transport.write(OUT / "POD-RESOURCE-CHECK.json", {"checked_utc": preflight.utc_now(),
            "response_fields": sorted(pod), "pod": {key: pod.get(key) for key in (
                "id", "name", "image", "imageName", "computeType", "cloudType", "cloud",
                "verified_v2_cloud", "cpuFlavorId", "vcpuCount", "memoryInGb", "costPerHr",
                "containerDiskInGb", "volumeInGb", "volumeMountPath", "ports")},
            "machine_secure_cloud": (pod.get("machine") or {}).get("secureCloud"),
            "gpu": {key: (pod.get("gpu") or {}).get(key) for key in ("id", "count")},
            "network_volume_present": bool(pod.get("networkVolume"))})
        record["actual_resources"] = transport.validate_pod(pod, state, offer)
        log = execute_remote_v2(pod_id, token, raw, created, record)
        record["evidence"] = save_evidence(log)
        record["status"] = "complete"
    except Exception as exc:
        record["status"] = "failed"; record["error_type"] = type(exc).__name__
        if type(exc) is RuntimeError:
            record["error"] = str(exc)
        if state is not None and not transport.ABORT.exists():
            transport.write(transport.ABORT, {"requested_utc": preflight.utc_now(), "reason": record["error_type"]})
    finally:
        if state is not None and client is not None:
            try:
                cleanup = transport.cleanup_owned(client, state, "controller")
                record["cleanup"] = cleanup
                if cleanup["owned_pod_absent"] and not record["creation_uncertain"]:
                    transport.write(transport.DONE, {"finished_utc": preflight.utc_now(), "owned_pod_absent_verified": True})
            except Exception as exc:
                record["cleanup_error_type"] = type(exc).__name__
        elif not transport.DONE.exists():
            transport.write(transport.DONE, {"finished_utc": preflight.utc_now(), "no_create_request": True})
        record["finished_utc"] = preflight.utc_now()
        if state is not None:
            record["elapsed_since_create_s"] = time.time() - state["created_epoch"]
            actual_rate = record.get("actual_resources", {}).get("rate_usd_per_hour")
            record["estimated_compute_cost_usd"] = actual_rate * record["elapsed_since_create_s"] / 3600 if actual_rate else None
        transport.write(OUT / "RUN.json", record)
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
    with base.host_awake_guard("c16-http-watchdog" if args.watchdog else "c16-http-controller"):
        return transport.watchdog() if args.watchdog else run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}), flush=True)
        raise SystemExit(2)
