"""Resume retry 002 with a bounded read-only CPU-availability wait."""
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
C16_CONTROLLER = ROOT / "docs/recognition/c16_linux_confirmation/runpod_c16_linux_controller_v2.py"
spec = importlib.util.spec_from_file_location("c16_transport", C16_CONTROLLER)
c16 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c16)
shared, base, preflight = c16.transport, c16.base, c16.preflight

OUT = HERE / "runpod-c23-linux-execute-002c"
MANIFEST = HERE / "c23_linux_upload_manifest.json"
AUTHORIZATION = HERE / "RUNPOD_C23_RETRY_002_EXACT_PAYLOAD_AUTHORIZED_2026_08_31.json"
PROTOCOL = HERE / "C23_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_08_31.md"
LOCAL_VALIDATION = HERE / "C23_PACKAGE_LOCAL_VALIDATION_20260831.json"
PRIOR_FAILURE = HERE / "RUNPOD_C23_FAILED_ATTEMPT_VERIFICATION_20260831.json"
RUN_NAME = "c23-yosys-fresh-gf2-table-linux-20260831-001"

old_stage = c16.new_command
new_stage = (
    "emit('stage', name='c23-linux-replication')\n"
    "    run('c23-linux-replication', [sys.executable, '-B',\n"
    "         'scripts/cm_comparative_c23_fresh_gf2_table.py', '--output',\n"
    "         str(OUT/'c23-yosys-fresh-gf2-table-linux-20260831-001'),\n"
    "         '--rounds', '5', '--max-seconds', '1200'], 240)\n"
    "    emit('stage', name='c23-linux-verification')\n"
    "    run('c23-linux-verification', [sys.executable, '-B',\n"
    "         'scripts/crse_gf2_fresh_table_verify.py',\n"
    "         str(OUT/'c23-yosys-fresh-gf2-table-linux-20260831-001')], 120)"
)
base.REMOTE_CODE = shared.replace_remote_once(base.REMOTE_CODE, old_stage, new_stage)
old_validation = (
    "    try:\n"
    "        summary = json.loads((OUT / 'c16-linux-confirmation/summary.json').read_text())\n"
    "        validation['confirmation_summary'] = {key: summary.get(key) for key in\n"
    "            ('status', 'semantic_mismatches', 'criteria', 'scientific_scope')}\n"
    "    except Exception as exc:\n"
    "        validation['validation_error'] = type(exc).__name__ + ': ' + str(exc)"
)
new_validation = (
    "    try:\n"
    "        study = OUT / 'c23-yosys-fresh-gf2-table-linux-20260831-001'\n"
    "        result = json.loads((study / 'results.json').read_text())\n"
    "        verified = json.loads((study / 'independent_verification.json').read_text())\n"
    "        validation['confirmation_summary'] = {\n"
    "            'status': result.get('status'),\n"
    "            'measurement_rows': result.get('measurement_rows'),\n"
    "            'memory_rows': result.get('memory_measurement_rows'),\n"
    "            'semantic_or_artifact_mismatches': result.get('semantic_or_artifact_mismatches'),\n"
    "            'verification_status': verified.get('status'),\n"
    "            'best_fixed_method': result.get('summary', {}).get('best_fixed_method')}\n"
    "    except Exception as exc:\n"
    "        validation['validation_error'] = type(exc).__name__ + ': ' + str(exc)"
)
base.REMOTE_CODE = shared.replace_remote_once(base.REMOTE_CODE, old_validation, new_validation)


def configure_transport() -> None:
    c16.OUT = OUT
    shared.OUT = OUT
    base.OUT = OUT
    shared.MANIFEST_PATH = MANIFEST
    shared.AUTHORIZATION_PATH = AUTHORIZATION
    shared.PROPOSAL_PATH = PROTOCOL
    for name, filename in {
        "STATE": "controller-state.json", "IDENTITY": "POD-IDENTITY.json",
        "READY": "watchdog-ready.json", "STATE_ACK": "watchdog-state-ack.json",
        "DONE": "watchdog-done.json", "ABORT": "abort-requested.json",
    }.items():
        setattr(shared, name, OUT / filename)


configure_transport()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_authorization() -> dict:
    authorization, manifest, validation = load(AUTHORIZATION), load(MANIFEST), load(LOCAL_VALIDATION)
    prior_failure = load(PRIOR_FAILURE)
    expected = {
        "schema": "crse-runpod-c23-retry-002-exact-payload-authorization/v1",
        "authorized": True,
        "retry_attempt": 2,
        "additional_create_requests": 1,
        "prior_failed_attempt_status": "verified_reconciled",
        "user_total_ceiling_usd": 5.0,
        "controller_total_ceiling_usd": 0.05,
        "one_create": True,
        "no_replacement": True,
        "source_files": 52,
        "source_bytes": 903745,
        "cases": 48,
        "rounds": 5,
        "methods": 7,
        "measurement_rows": 1680,
        "memory_rows": 56,
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
        "same_pod_payload_attempt_limit": 6,
        "health_checks_before_upload": 2,
        "result_cap_bytes": 16 << 20,
        "local_isolated_validation": "pass",
        "local_validation_pythonpath_injected": False,
        "credentials_recorded_or_uploaded": False,
    }
    if any(authorization.get(key) != value for key, value in expected.items()):
        raise RuntimeError("C23 authorization scope mismatch")
    if (
        authorization.get("upload_manifest_sha256") != sha256(MANIFEST)
        or authorization.get("protocol_sha256") != sha256(PROTOCOL)
        or authorization.get("local_validation_sha256") != sha256(LOCAL_VALIDATION)
        or authorization.get("prior_failed_attempt_verification_sha256") != sha256(PRIOR_FAILURE)
        or manifest.get("file_count") != 52
        or manifest.get("bytes") != 903745
        or validation.get("status") != "pass"
        or validation.get("manifest_sha256") != sha256(MANIFEST)
        or prior_failure.get("status") != "pass"
        or prior_failure.get("scientific_replication_complete") is not False
        or prior_failure.get("create_requests_this_authorization") != 1
        or prior_failure.get("pod_created") is not False
        or prior_failure.get("files_uploaded") != 0
        or prior_failure.get("owned_pod_absent_verified") is not True
        or prior_failure.get("final_inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("C23 authorization artifact mismatch")
    return authorization


def arm_watchdog():
    with (OUT / "watchdog.log").open("xb") as stream:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        process = subprocess.Popen(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--watchdog"],
            stdout=stream, stderr=subprocess.STDOUT, creationflags=flags, close_fds=True,
        )
    for _ in range(200):
        if shared.READY.exists():
            ready = load(shared.READY)
            if not ready.get("network_probe_passed") or any(ready["startup_inventories"].values()):
                raise RuntimeError("C23 watchdog zero-pod readiness failed")
            shared.write(OUT / "WATCHDOG-PROCESS-BINDING.json", shared.bind_watchdog(process, ready))
            return process
        if process.poll() is not None:
            raise RuntimeError("C23 watchdog exited before readiness")
        time.sleep(0.2)
    raise RuntimeError("C23 watchdog failed to arm")


def execute_remote(pod_id: str, token: str, raw: bytes, created: float, record: dict) -> str:
    endpoint = f"https://{pod_id}-8080.proxy.runpod.net"
    with shared.requests.Session() as proxy:
        proxy.trust_env = False
        proxy.headers["X-CM-Token"] = token
        proxy.headers["Content-Type"] = "application/octet-stream"
        consecutive_health = 0
        while time.time() < created + 240:
            try:
                health = json.loads(shared.proxy_request(proxy, "GET", endpoint + "/health", timeout=5))
                if health.get("service") == "cm-memory-http" and health.get("ready") is True:
                    consecutive_health += 1
                    if consecutive_health == 2:
                        break
                    time.sleep(2)
                    continue
            except (shared.requests.RequestException, RuntimeError, ValueError):
                pass
            consecutive_health = 0
            time.sleep(2)
        else:
            raise RuntimeError("C23 HTTP bootstrap did not remain ready")
        record["bootstrap_ready_utc"] = preflight.utc_now()
        record["health_checks_before_upload"] = consecutive_health
        upload_events = []
        accepted = None
        for attempt in range(1, 7):
            try:
                accepted = json.loads(shared.proxy_request(
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
                health = json.loads(shared.proxy_request(proxy, "GET", endpoint + "/health", timeout=5))
                if health.get("service") != "cm-memory-http" or health.get("ready") is not True:
                    record["payload_attempts"] = upload_events
                    raise RuntimeError("C23 bootstrap health changed during retry")
        record["payload_attempts"] = upload_events
        if accepted is None or accepted.get("accepted_sha256") != hashlib.sha256(raw).hexdigest():
            raise RuntimeError("C23 upload acknowledgement mismatch")
        record["uploaded_source_files"] = 52
        record["uploaded_transport_bytes"] = len(raw)
        shared.proxy_request(proxy, "POST", endpoint + "/run", data=b"", timeout=10)
        record["worker_started_utc"] = preflight.utc_now()
        observed = None
        allowed_work = {"c23-linux-replication", "c23-linux-verification"}
        while time.time() < created + shared.CLEANUP_AT - 30:
            try:
                progress = json.loads(shared.proxy_request(proxy, "GET", endpoint + "/progress", timeout=5))
            except shared.requests.RequestException:
                time.sleep(2)
                continue
            signature = (progress.get("stage"), progress.get("done"), progress.get("error"))
            if signature != observed:
                shared.append(OUT / "progress.jsonl", {"checked_utc": preflight.utc_now(), **progress})
                print(json.dumps({"stage": progress.get("stage"), "done": progress.get("done"),
                                  "error": progress.get("error")}), flush=True)
                observed = signature
            if progress.get("done"):
                record["remote_progress"] = progress
                return shared.proxy_request(
                    proxy, "GET", endpoint + "/results", cap=shared.CAP, timeout=20,
                ).decode("utf-8")
            if time.time() >= created + 300 and progress.get("stage") not in allowed_work:
                raise RuntimeError("C23 boot/install exceeded five-minute setup deadline")
            time.sleep(2)
    raise RuntimeError("C23 remote worker deadline exceeded")


def save_evidence(log: str) -> dict:
    lines = log.splitlines()
    starts = [json.loads(line[9:]) for line in lines
              if line.startswith("CM_EVENT ") and '"kind": "evidence_start"' in line]
    if not starts:
        raise RuntimeError("C23 remote evidence marker missing")
    plain = "\n".join(line for line in lines if not line.startswith("CM_EVIDENCE ")) + "\n"
    if len(plain.encode()) + int(starts[-1]["bytes"]) + int(starts[-1]["uncompressed_bytes"]) > shared.CAP:
        raise RuntimeError("C23 retrieved evidence exceeds cap")
    (OUT / "container.log").write_text(plain, encoding="utf-8")
    extracted = base.extract_evidence(lines)
    evidence = OUT / "evidence/run-output"
    validation = load(evidence / "REMOTE-VALIDATION.json")
    runtime = load(evidence / "RUNTIME.json")
    dependencies = load(evidence / "DEPENDENCIES.json")
    study = evidence / RUN_NAME
    result = load(study / "results.json")
    verification = load(study / "independent_verification.json")
    rows = [json.loads(line) for line in (study / "measurements.jsonl").read_text(
        encoding="utf-8").splitlines()]
    memory_rows = [json.loads(line) for line in (study / "memory_measurements.jsonl").read_text(
        encoding="utf-8").splitlines()]
    confirmation = validation.get("confirmation_summary", {})
    if (
        validation.get("status") != "complete"
        or validation.get("error") is not None
        or validation.get("validation_error") is not None
        or confirmation.get("status") != "complete"
        or confirmation.get("measurement_rows") != 1680
        or confirmation.get("memory_rows") != 56
        or confirmation.get("semantic_or_artifact_mismatches") != 0
        or confirmation.get("verification_status") != "verified"
        or result.get("status") != "complete"
        or result.get("measurement_rows") != 1680
        or result.get("memory_measurement_rows") != 56
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("claims", {}).get("unchanged_c21_methods") is not True
        or result.get("claims", {}).get("fresh_confirmation") is not True
        or result.get("claims", {}).get("production_promotion") is not False
        or result.get("environment", {}).get("dd_version") != "0.6.0"
        or verification.get("status") != "verified"
        or verification.get("measurement_rows_checked") != 1680
        or verification.get("memory_rows_checked") != 56
        or verification.get("semantic_or_artifact_mismatches") != 0
        or len(rows) != 1680
        or len(memory_rows) != 56
        or len({(row.get("case_id"), row.get("method"), row.get("round")) for row in rows}) != 1680
        or any(row.get("exact_check_passed") is not True for row in rows)
        or any(row.get("exact_check_passed") is not True for row in memory_rows)
        or runtime.get("source_files") != 52
        or runtime.get("runpod_pod_id") != load(shared.IDENTITY)["pod_id"]
        or runtime.get("image_tag") != base.IMAGE_TAG
        or runtime.get("image_amd64_digest") != base.IMAGE_AMD64_DIGEST
        or dependencies.get("numpy") != "2.3.2"
        or dependencies.get("dd") != "0.6.0"
    ):
        raise RuntimeError("retrieved C23 evidence failed frozen gates")
    extracted["validation"] = validation
    extracted["runtime_pod_id"] = runtime["runpod_pod_id"]
    extracted["c23_linux_replication"] = {
        "cases": 48,
        "methods": 7,
        "rounds": 5,
        "measurement_rows": 1680,
        "memory_rows": 56,
        "semantic_or_artifact_mismatches": 0,
        "best_fixed_method": result["summary"]["best_fixed_method"],
        "oracle_headroom_over_best_fixed": result["summary"]["oracle_headroom_over_best_fixed"],
    }
    return extracted


def run() -> int:
    record = {
        "started_utc": preflight.utc_now(), "status": "preflight",
        "creation_attempted": False, "creation_uncertain": False,
        "pod_created": False, "uploaded_source_files": 0,
        "automatic_replacement_queued": False,
    }
    state = client = None
    try:
        authorization = require_authorization()
        record["authorization_record_sha256"] = sha256(AUTHORIZATION)
        record["authorization_recorded_utc"] = authorization.get("recorded_utc")
        record["retry_attempt"] = 2
        record["prior_failed_attempt_verification_sha256"] = sha256(PRIOR_FAILURE)
        preflight_deadline = time.time() + 300
        preflight_poll_attempts = 0
        while True:
            preflight_poll_attempts += 1
            ready = preflight.check()
            offer = ready.get("selected_offer")
            rate = float(offer["rate_usd_per_hour"]) if offer else float("nan")
            projected = (rate + shared.STORAGE_RATE_RESERVE) * shared.CLEANUP_AT / 3600
            ready["c23_budget"] = {
                "rate_usd_per_hour": rate,
                "projected_10_minute_cost_usd": projected,
                "total_cost_cap_usd": shared.CAMPAIGN_CAP,
                "ready": bool(math.isfinite(rate) and 0 < rate <= shared.RATE_CAP
                              and projected <= shared.CAMPAIGN_CAP),
            }
            offers = ready.get("offers", [])
            shared.append(OUT / "preflight-availability.jsonl", {
                "attempt": preflight_poll_attempts,
                "checked_utc": ready.get("checked_utc"),
                "ready": ready.get("ready"),
                "selected_offer": offer and offer.get("id"),
                "inventories_empty": not any(ready.get("inventories", {}).values()),
                "offers": [{"id": row.get("id"), "availability": row.get("availability"),
                            "eligible": row.get("eligible")} for row in offers],
            })
            if (ready.get("ready") is True and ready["c23_budget"]["ready"] is True
                    and not any(ready["inventories"].values())):
                break
            availability_only = (
                offer is None
                and ready.get("credit_sufficient") is True
                and ready.get("spend_limit_sufficient") is True
                and ready.get("credential_values_recorded") is False
                and ready.get("resource_writes") == 0
                and not any(ready.get("inventories", {}).values())
                and bool(offers)
                and all(row.get("availability") == "NONE"
                        and row.get("eligible") is False for row in offers)
            )
            if not availability_only:
                shared.write(OUT / "PREFLIGHT.json", ready)
                raise RuntimeError("C23 account/resource/budget preflight failed")
            if time.time() >= preflight_deadline:
                shared.write(OUT / "PREFLIGHT.json", ready)
                raise RuntimeError("C23 Secure CPU availability wait expired before create")
            time.sleep(min(30, max(1, preflight_deadline - time.time())))
        record["preflight_poll_attempts"] = preflight_poll_attempts
        shared.write(OUT / "PREFLIGHT.json", ready)
        manifest = load(MANIFEST)
        if (
            manifest.get("schema") != "crse-c23-linux-replication-upload-manifest/v1"
            or manifest.get("file_count") != 52
            or len(manifest.get("files", [])) != 52
            or manifest.get("bytes") != 903745
            or manifest.get("authorization_status") != "authorized_by_current_user_request"
            or manifest.get("run_name") != RUN_NAME
            or manifest.get("network_during_workload") is not False
            or manifest.get("scientific_contract", {}).get("measurement_rows") != 1680
            or manifest.get("scientific_contract", {}).get("unchanged_c21_method_implementations") is not True
            or manifest.get("runtime", {}).get("image") != base.IMAGE
            or manifest.get("runtime", {}).get("python") != "3.13.15"
            or manifest.get("runtime", {}).get("numpy_requirement") != shared.NUMPY_REQUIREMENT
        ):
            raise RuntimeError("frozen C23 manifest mismatch")
        bundle = base.make_bundle(manifest)
        watchdog_process = arm_watchdog()
        client = preflight.session()
        if any(shared.inventories(client).values()):
            raise RuntimeError("zero-pod baseline changed before C23 creation")
        created = time.time()
        state = {"name": "cm-c7-linux-" + uuid.uuid4().hex[:12],
                 "created_epoch": created,
                 "cleanup_epoch": created + shared.CLEANUP_AT,
                 "horizon_epoch": created + shared.HORIZON}
        raw = shared.prepare_payload(bundle, manifest, created)
        token = secrets.token_urlsafe(32)
        body = shared.create_payload(state["name"], offer, token, raw, created)
        shared.write(OUT / "TRANSPORT-FREEZE.json", {
            "controller_sha256": sha256(Path(__file__)),
            "authorization_sha256": sha256(AUTHORIZATION),
            "protocol_sha256": sha256(PROTOCOL),
            "local_validation_sha256": sha256(LOCAL_VALIDATION),
            "prior_failed_attempt_verification_sha256": sha256(PRIOR_FAILURE),
            "bootstrap_sha256": sha256(shared.BOOTSTRAP_PATH),
            "source_bundle_sha256": hashlib.sha256(bundle).hexdigest(),
            "source_bundle_bytes": len(bundle),
            "source_files": 52,
            "source_bytes": manifest["bytes"],
            "transport_payload_sha256": hashlib.sha256(raw).hexdigest(),
            "transport_payload_bytes": len(raw),
            "manifest_sha256": sha256(MANIFEST),
            "credentials_recorded_or_uploaded": False,
        })
        shared.write(shared.STATE, state)
        shared.confirm_watchdog(watchdog_process, state)
        record.update({
            "creation_attempted": True,
            "creation_uncertain": True,
            "creation_request_utc": preflight.utc_now(),
            "creation_endpoint": preflight.V1 + "/pods",
            "name": state["name"],
            "selected_cpu": offer["id"],
            "quoted_rate_usd_per_hour": offer["rate_usd_per_hour"],
        })
        print(json.dumps({"action": "create_one_cpu_pod", "name": state["name"],
                          "cpu": offer["id"], "rate": offer["rate_usd_per_hour"]}), flush=True)
        response = client.post(preflight.V1 + "/pods", json=body, timeout=(10, 50),
                               allow_redirects=False)
        record["creation_http_status"] = response.status_code
        if response.status_code not in (200, 201):
            record["creation_uncertain"] = not 400 <= response.status_code < 500
            raise RuntimeError("C23 pod creation failed HTTP " + str(response.status_code))
        pod = response.json()
        pod = pod.get("pod", pod)
        pod_id = pod.get("id")
        if not isinstance(pod_id, str) or not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
            raise RuntimeError("C23 creation response has no valid pod ID")
        shared.write(shared.IDENTITY, {"pod_id": pod_id, "name": state["name"],
                                       "recorded_utc": preflight.utc_now(),
                                       "source": "this create response"})
        record.update({"pod_id": pod_id, "pod_created": True, "creation_uncertain": False})
        pod = shared.actual_pod(client, pod_id)
        shared.write(OUT / "POD-RESOURCE-CHECK.json", {
            "checked_utc": preflight.utc_now(),
            "response_fields": sorted(pod),
            "pod": {key: pod.get(key) for key in (
                "id", "name", "image", "imageName", "computeType", "cloudType", "cloud",
                "verified_v2_cloud", "cpuFlavorId", "vcpuCount", "memoryInGb", "costPerHr",
                "containerDiskInGb", "volumeInGb", "volumeMountPath", "ports")},
            "machine_secure_cloud": (pod.get("machine") or {}).get("secureCloud"),
            "gpu": {key: (pod.get("gpu") or {}).get(key) for key in ("id", "count")},
            "network_volume_present": bool(pod.get("networkVolume")),
        })
        record["actual_resources"] = shared.validate_pod(pod, state, offer)
        log = execute_remote(pod_id, token, raw, created, record)
        record["evidence"] = save_evidence(log)
        record["status"] = "complete"
    except Exception as exc:
        record["status"] = "failed"
        record["error_type"] = type(exc).__name__
        if type(exc) is RuntimeError:
            record["error"] = str(exc)
        if state is not None and not shared.ABORT.exists():
            shared.write(shared.ABORT, {"requested_utc": preflight.utc_now(),
                                        "reason": record["error_type"]})
    finally:
        if state is not None and client is not None:
            try:
                cleanup = shared.cleanup_owned(client, state, "controller")
                record["cleanup"] = cleanup
                if cleanup["owned_pod_absent"] and not record["creation_uncertain"]:
                    shared.write(shared.DONE, {"finished_utc": preflight.utc_now(),
                                               "owned_pod_absent_verified": True})
            except Exception as exc:
                record["cleanup_error_type"] = type(exc).__name__
        elif not shared.DONE.exists():
            shared.write(shared.DONE, {"finished_utc": preflight.utc_now(),
                                       "no_create_request": True})
        record["finished_utc"] = preflight.utc_now()
        if state is not None:
            record["elapsed_since_create_s"] = time.time() - state["created_epoch"]
            actual_rate = record.get("actual_resources", {}).get("rate_usd_per_hour")
            record["estimated_compute_cost_usd"] = (
                actual_rate * record["elapsed_since_create_s"] / 3600 if actual_rate else None)
        shared.write(OUT / "RUN.json", record)
        if client is not None:
            client.close()
    print(json.dumps(record, indent=2), flush=True)
    return int(record["status"] != "complete"
               or not record.get("cleanup", {}).get("owned_pod_absent"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watchdog", action="store_true")
    args = parser.parse_args()
    if not args.watchdog:
        OUT.mkdir(exist_ok=False)
    with base.host_awake_guard("c23-http-watchdog" if args.watchdog else "c23-http-controller"):
        return shared.watchdog() if args.watchdog else run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}), flush=True)
        raise SystemExit(2)
