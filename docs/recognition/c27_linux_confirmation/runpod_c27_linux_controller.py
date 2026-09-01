"""Run one exactly authorized C27 Secure CPU replication with bounded cleanup."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
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

OUT = HERE / "runpod-c27-linux-execute-001f"
MANIFEST = HERE / "c27_linux_upload_manifest.json"
AUTHORIZATION = HERE / "RUNPOD_C27_RETRY_003_EXACT_PAYLOAD_AUTHORIZED_2026_09_01.json"
PROTOCOL = HERE / "C27_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_08_31.md"
LOCAL_VALIDATION = HERE / "C27_PACKAGE_LOCAL_VALIDATION_20260831.json"
PRECREATE_BLOCKER = HERE / "RUNPOD_C27_PRECREATE_BLOCKER_VERIFICATION_20260831.json"
AVAILABILITY_BLOCKER = HERE / "RUNPOD_C27_AVAILABILITY_BLOCKED_VERIFICATION_V2_20260901.json"
PRIOR_RECONCILIATION = HERE / "RUNPOD_C27_RETRY_002_HTTP500_RECONCILIATION_20260901.json"
RETRY_REQUEST = HERE / "RUNPOD_C27_RETRY_003_AUTHORIZATION_REQUEST_20260901.json"
READINESS = HERE / "RUNPOD_C27_RETRY_003_READINESS_20260901.json"
DOCKER_REPEATABILITY = HERE / "C27_DOCKER_LINUX_REPEATABILITY_VERIFICATION_20260901.json"
PORTABLE_VALIDATION = (
    ROOT / "docs/recognition/c27_independent_docker_confirmation/"
    "C27_INDEPENDENT_DOCKER_PACKAGE_LOCAL_VALIDATION_20260901.json"
)
RUN_NAME = "c27-support-aware-fresh-linux-20260831-001"

old_stage = c16.new_command
new_stage = (
    "emit('stage', name='c27-linux-replication')\n"
    "    run('c27-linux-replication', [sys.executable, '-B',\n"
    "         'scripts/cm_comparative_c27_support_aware.py', '--output',\n"
    "         str(OUT/'c27-support-aware-fresh-linux-20260831-001'),\n"
    "         '--rounds', '5', '--max-seconds', '1200'], 300)\n"
    "    emit('stage', name='c27-linux-verification')\n"
    "    run('c27-linux-verification', [sys.executable, '-B',\n"
    "         'scripts/crse_gf2_support_aware_verify.py',\n"
    "         str(OUT/'c27-support-aware-fresh-linux-20260831-001')], 120)"
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
    "        study = OUT / 'c27-support-aware-fresh-linux-20260831-001'\n"
    "        result = json.loads((study / 'results.json').read_text())\n"
    "        verified = json.loads((study / 'independent_verification.json').read_text())\n"
    "        validation['confirmation_summary'] = {\n"
    "            'status': result.get('status'),\n"
    "            'measurement_batches': result.get('measurement_batches'),\n"
    "            'timed_queries': result.get('timed_queries'),\n"
    "            'memory_batches': result.get('memory_measurement_batches'),\n"
    "            'fallback_controls': result.get('fallback_controls'),\n"
    "            'selected_path_controls': result.get('selected_path_controls'),\n"
    "            'refusal_controls': result.get('refusal_controls'),\n"
    "            'semantic_or_artifact_mismatches': result.get('semantic_or_artifact_mismatches'),\n"
    "            'verification_status': verified.get('status'),\n"
    "            'timing_gate': result.get('summary', {}).get(\n"
    "                'support_aware_confirmation_gate'),\n"
    "            'break_even': result.get('summary', {}).get(\n"
    "                'support_aware_break_even_query_count')}\n"
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


@contextmanager
def c27_host_awake_guard(role: str):
    """Keep this batteryless Windows host awake; refuse an explicit battery state."""
    if os.name != "nt":
        raise RuntimeError("C27 host wake guard is validated for Windows only")
    import ctypes
    from ctypes import wintypes

    class PowerStatus(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", wintypes.BYTE), ("BatteryFlag", wintypes.BYTE),
            ("BatteryLifePercent", wintypes.BYTE), ("SystemStatusFlag", wintypes.BYTE),
            ("BatteryLifeTime", wintypes.DWORD), ("BatteryFullLifeTime", wintypes.DWORD),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    power = PowerStatus()
    if not kernel.GetSystemPowerStatus(ctypes.byref(power)):
        raise RuntimeError("C27 Windows power telemetry failed")
    if power.ACLineStatus == 0:
        raise RuntimeError("plug the C27 controller host into AC power before launching a pod")
    if power.ACLineStatus not in (1, 255):
        raise RuntimeError("C27 Windows power telemetry returned an unsupported state")
    set_state = kernel.SetThreadExecutionState
    set_state.argtypes = [wintypes.DWORD]
    set_state.restype = wintypes.DWORD
    requested = 0x80000001
    if not set_state(requested):
        raise RuntimeError("failed to establish temporary C27 idle-sleep prevention")
    shared.write(OUT / ("HOST-AWAKE-" + role + ".json"), {
        "started_utc": preflight.utc_now(),
        "pid": os.getpid(),
        "ac_line_status_raw": int(power.ACLineStatus),
        "ac_status_interpretation": (
            "connected" if power.ACLineStatus == 1
            else "unknown_allowed_for_batteryless_host_with_user_confirmation"),
        "win32_battery_observed_before_launch": False,
        "user_confirmed_host_plugged_in": True,
        "requested_execution_state": requested,
        "persistent_power_settings_changed": False,
        "limitation": "does not prevent explicit sleep, power loss, or network loss",
    })
    try:
        yield
    finally:
        released = bool(set_state(0x80000000))
        shared.write(OUT / ("HOST-AWAKE-RELEASED-" + role + ".json"), {
            "released_utc": preflight.utc_now(), "released": released, "pid": os.getpid(),
        })


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_inventory(inventories: dict) -> dict[str, list[tuple[str, str]]]:
    return {
        version: sorted({(row.get("id"), row.get("name"))
                         for row in inventories.get(version, [])})
        for version in ("v1", "v2")
    }


def allowed_baseline(inventories: dict) -> bool:
    expected = [("vqos7wif838oxx", "cm-video-first5-production-v1-a1-339b3cfb0d")]
    normalized = normalized_inventory(inventories)
    return normalized in ({"v1": expected, "v2": expected}, {"v1": [], "v2": []})


def require_authorization() -> dict:
    authorization, manifest, validation = load(AUTHORIZATION), load(MANIFEST), load(LOCAL_VALIDATION)
    blocker = load(PRECREATE_BLOCKER)
    availability = load(AVAILABILITY_BLOCKER)
    prior = load(PRIOR_RECONCILIATION)
    retry_request = load(RETRY_REQUEST)
    readiness = load(READINESS)
    expected = {
        "schema": "crse-runpod-c27-retry-003-exact-payload-authorization/v1",
        "authorized": True,
        "create_requests": 1,
        "additional_create_requests": 1,
        "prior_create_requests": 2,
        "retry_attempt": 3,
        "controller_total_ceiling_usd": 0.05,
        "one_create": True,
        "no_replacement": True,
        "required_cpu_flavor": "cpu5c",
        "fallback_cpu_flavors": [],
        "quoted_rate_usd_per_hour": 0.07,
        "source_files": 63,
        "source_bytes": 1078671,
        "cases": 48,
        "rounds": 5,
        "methods": 6,
        "measurement_batches": 720,
        "timed_queries": 7560,
        "memory_batches": 24,
        "https_ports": ["8080/http"],
        "vcpu_count": 2,
        "minimum_ram_gb": 4,
        "container_disk_gb": 12,
        "pod_volume_gb": 0,
        "network_volume": False,
        "cleanup_seconds": 600,
        "reconciliation_seconds": 720,
        "rate_cap_usd_per_hour": 0.07,
        "total_cost_cap_usd": 0.05,
        "precreate_wait_seconds": 900,
        "same_pod_payload_attempt_limit": 6,
        "health_checks_before_upload": 2,
        "result_cap_bytes": 16 << 20,
        "local_isolated_validation": "pass",
        "local_validation_pythonpath_injected": False,
        "isolated_timing_gate": False,
        "timing_gate_failure_is_valid_evidence": True,
        "training": False,
        "production_write": False,
        "production_promotion": False,
        "credentials_recorded_or_uploaded": False,
    }
    if any(authorization.get(key) != value for key, value in expected.items()):
        raise RuntimeError("C27 authorization scope mismatch")
    if (
        authorization.get("upload_manifest_sha256") != sha256(MANIFEST)
        or authorization.get("protocol_sha256") != sha256(PROTOCOL)
        or authorization.get("local_validation_sha256") != sha256(LOCAL_VALIDATION)
        or authorization.get("prior_reconciliation_sha256")
        != sha256(PRIOR_RECONCILIATION)
        or authorization.get("authorization_request_sha256") != sha256(RETRY_REQUEST)
        or authorization.get("readiness_sha256") != sha256(READINESS)
        or authorization.get("docker_repeatability_verification_sha256")
        != sha256(DOCKER_REPEATABILITY)
        or authorization.get("portable_package_validation_sha256")
        != sha256(PORTABLE_VALIDATION)
        or authorization.get("transport_regression_test_sha256")
        != sha256(ROOT / "tests/test_c27_runpod_transport.py")
        or manifest.get("file_count") != 63
        or manifest.get("bytes") != 1078671
        or validation.get("status") != "pass"
        or validation.get("manifest_sha256") != sha256(MANIFEST)
        or blocker.get("status") != "pass"
        or blocker.get("create_requests") != 0
        or blocker.get("pod_created") is not False
        or blocker.get("files_uploaded") != 0
        or blocker.get("authorization_remains_unused") is not True
        or blocker.get("allowed_unrelated_baseline", {}).get("pod_id") != "vqos7wif838oxx"
        or blocker.get("allowed_unrelated_baseline", {}).get("ownership")
        != "unrelated_do_not_modify"
        or availability.get("status") != "verified_reconciled"
        or availability.get("create_requests") != 0
        or availability.get("pod_created") is not False
        or availability.get("files_uploaded") != 0
        or availability.get("authorization_remains_unused") is not True
        or availability.get("unrelated_pod", {}).get("pod_id") != "vqos7wif838oxx"
        or availability.get("unrelated_pod", {}).get("ownership")
        != "unrelated_not_modified"
        or prior.get("status") != "verified_reconciled"
        or prior.get("create_requests") != 1
        or prior.get("create_http_status") != 500
        or prior.get("authorization_consumed") is not True
        or prior.get("pod_created") is not False
        or prior.get("pod_ever_observed") is not False
        or prior.get("replacement_authorized") is not False
        or prior.get("source_files_uploaded") != 0
        or prior.get("owned_pod_absent") is not True
        or prior.get("unrelated_pod_preserved") is not True
        or readiness.get("status") != "ready_read_only"
        or readiness.get("create_requests") != 0
        or readiness.get("resource_writes") != 0
        or readiness.get("credentials_recorded_or_uploaded") is not False
        or readiness.get("preferred_cpu_flavor") != "cpu5c"
        or readiness.get("preferred_eligible") is not True
        or readiness.get("preferred_rate_usd_per_hour") != 0.07
        or retry_request.get("status") != "awaiting_exact_user_approval"
        or retry_request.get("authorization_granted") is not False
        or retry_request.get("requested_additional_create_requests") != 1
        or retry_request.get("retry_attempt") != 3
        or retry_request.get("required_cpu_flavor") != "cpu5c"
        or retry_request.get("fallback_cpu_flavors") != []
        or retry_request.get("rate_cap_usd_per_hour") != 0.07
    ):
        raise RuntimeError("C27 authorization artifact mismatch")
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
            if (not ready.get("network_probe_passed")
                    or not allowed_baseline(ready["startup_inventories"])):
                raise RuntimeError("C27 watchdog unrelated-baseline readiness failed")
            shared.write(OUT / "WATCHDOG-BASELINE.json", {
                "checked_utc": preflight.utc_now(),
                "startup_inventory": normalized_inventory(ready["startup_inventories"]),
                "unrelated_baseline_allowed": True,
                "unrelated_baseline_modified": False,
            })
            shared.write(OUT / "WATCHDOG-PROCESS-BINDING.json", shared.bind_watchdog(process, ready))
            return process
        if process.poll() is not None:
            raise RuntimeError("C27 watchdog exited before readiness")
        time.sleep(0.2)
    raise RuntimeError("C27 watchdog failed to arm")


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
            raise RuntimeError("C27 HTTP bootstrap did not remain ready")
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
                try:
                    health = json.loads(shared.proxy_request(
                        proxy, "GET", endpoint + "/health", timeout=5))
                except (shared.requests.RequestException, RuntimeError, ValueError) as health_exc:
                    upload_events[-1]["health_recheck"] = type(health_exc).__name__
                    upload_events[-1]["health_recheck_status"] = str(health_exc)
                    if (isinstance(health_exc, RuntimeError)
                            and str(health_exc) != "proxy HTTP 404"):
                        record["payload_attempts"] = upload_events
                        raise
                    time.sleep(2)
                    continue
                if health.get("service") != "cm-memory-http" or health.get("ready") is not True:
                    record["payload_attempts"] = upload_events
                    raise RuntimeError("C27 bootstrap health changed during retry")
        record["payload_attempts"] = upload_events
        if accepted is None or accepted.get("accepted_sha256") != hashlib.sha256(raw).hexdigest():
            raise RuntimeError("C27 upload acknowledgement mismatch")
        record["uploaded_source_files"] = 63
        record["uploaded_transport_bytes"] = len(raw)
        shared.proxy_request(proxy, "POST", endpoint + "/run", data=b"", timeout=10)
        record["worker_started_utc"] = preflight.utc_now()
        observed = None
        allowed_work = {"c27-linux-replication", "c27-linux-verification"}
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
                raise RuntimeError("C27 boot/install exceeded five-minute setup deadline")
            time.sleep(2)
    raise RuntimeError("C27 remote worker deadline exceeded")


def save_evidence(log: str) -> dict:
    lines = log.splitlines()
    starts = [json.loads(line[9:]) for line in lines
              if line.startswith("CM_EVENT ") and '"kind": "evidence_start"' in line]
    if not starts:
        raise RuntimeError("C27 remote evidence marker missing")
    plain = "\n".join(line for line in lines if not line.startswith("CM_EVIDENCE ")) + "\n"
    if len(plain.encode()) + int(starts[-1]["bytes"]) + int(starts[-1]["uncompressed_bytes"]) > shared.CAP:
        raise RuntimeError("C27 retrieved evidence exceeds cap")
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
        or confirmation.get("measurement_batches") != 720
        or confirmation.get("timed_queries") != 7560
        or confirmation.get("memory_batches") != 24
        or confirmation.get("fallback_controls") != 48
        or confirmation.get("selected_path_controls") != 48
        or confirmation.get("refusal_controls") != 10
        or confirmation.get("semantic_or_artifact_mismatches") != 0
        or confirmation.get("verification_status") != "verified"
        or result.get("status") != "complete"
        or result.get("measurement_batches") != 720
        or result.get("timed_queries") != 7560
        or result.get("memory_measurement_batches") != 24
        or result.get("fallback_controls") != 48
        or result.get("selected_path_controls") != 48
        or result.get("tiny_truth_path_controls") != 24
        or result.get("large_packed_path_controls") != 24
        or result.get("refusal_controls") != 10
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("claims", {}).get("unchanged_c25_direct_controls") is not True
        or result.get("claims", {}).get("support_policy_frozen_before_corpus") is not True
        or result.get("claims", {}).get("fresh_confirmation") is not True
        or result.get("claims", {}).get("production_promotion") is not False
        or result.get("environment", {}).get("dd_version") != "0.6.0"
        or verification.get("status") != "verified"
        or verification.get("measurement_batches_checked") != 720
        or verification.get("timed_query_records_checked") != 7560
        or verification.get("memory_batches_checked") != 24
        or verification.get("semantic_or_artifact_mismatches") != 0
        or len(rows) != 720
        or len(memory_rows) != 24
        or len({(row.get("n_vars"), row.get("query_count"), row.get("method"),
                row.get("round")) for row in rows}) != 720
        or sum(len(row.get("query_records", [])) for row in rows) != 7560
        or any(row.get("exact_check_passed") is not True for row in rows)
        or any(row.get("exact_check_passed") is not True for row in memory_rows)
        or runtime.get("source_files") != 63
        or runtime.get("runpod_pod_id") != load(shared.IDENTITY)["pod_id"]
        or runtime.get("image_tag") != base.IMAGE_TAG
        or runtime.get("image_amd64_digest") != base.IMAGE_AMD64_DIGEST
        or set(dependencies) != {"numpy", "pip"}
        or dependencies.get("numpy") != "2.3.2"
        or dependencies.get("dd") is not None
    ):
        raise RuntimeError("retrieved C27 evidence failed frozen gates")
    extracted["validation"] = validation
    extracted["runtime_pod_id"] = runtime["runpod_pod_id"]
    extracted["c27_linux_replication"] = {
        "cases": 48,
        "methods": 6,
        "rounds": 5,
        "measurement_batches": 720,
        "timed_queries": 7560,
        "memory_batches": 24,
        "semantic_or_artifact_mismatches": 0,
        "support_aware_confirmation_gate": result["summary"][
            "support_aware_confirmation_gate"],
        "support_aware_break_even_query_count": result["summary"][
            "support_aware_break_even_query_count"],
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
        record["precreate_blocker_verification_sha256"] = sha256(PRECREATE_BLOCKER)
        record["availability_blocker_verification_sha256"] = sha256(AVAILABILITY_BLOCKER)
        record["prior_reconciliation_sha256"] = sha256(PRIOR_RECONCILIATION)
        record["retry_authorization_request_sha256"] = sha256(RETRY_REQUEST)
        record["retry_readiness_sha256"] = sha256(READINESS)
        record["docker_repeatability_verification_sha256"] = sha256(DOCKER_REPEATABILITY)
        record["portable_package_validation_sha256"] = sha256(PORTABLE_VALIDATION)
        record["unrelated_baseline_policy"] = "preserve exact video pod or allow it to disappear"
        preflight_deadline = time.time() + authorization["precreate_wait_seconds"]
        preflight_poll_attempts = 0
        while True:
            preflight_poll_attempts += 1
            ready = preflight.check()
            offers = ready.get("offers", [])
            required_rows = [row for row in offers
                             if row.get("id") == authorization["required_cpu_flavor"]]
            if len(required_rows) != 1:
                raise RuntimeError("C27 required cpu5c offer missing or duplicated")
            required_offer = required_rows[0]
            offer = required_offer if required_offer.get("eligible") is True else None
            rate = float(offer["rate_usd_per_hour"]) if offer else float("nan")
            projected = (rate + shared.STORAGE_RATE_RESERVE) * shared.CLEANUP_AT / 3600
            ready["c27_budget"] = {
                "rate_usd_per_hour": rate,
                "projected_10_minute_cost_usd": projected,
                "total_cost_cap_usd": shared.CAMPAIGN_CAP,
                "ready": bool(math.isfinite(rate) and 0 < rate
                              <= authorization["rate_cap_usd_per_hour"]
                              and projected <= shared.CAMPAIGN_CAP),
            }
            baseline_ok = allowed_baseline(ready.get("inventories", {}))
            account_ready = bool(
                ready.get("credit_sufficient") is True
                and ready.get("spend_limit_sufficient") is True
                and ready.get("credential_values_recorded") is False
                and ready.get("resource_writes") == 0)
            shared.append(OUT / "preflight-availability.jsonl", {
                "attempt": preflight_poll_attempts,
                "checked_utc": ready.get("checked_utc"),
                "ready": ready.get("ready"),
                "preflight_default_offer": (ready.get("selected_offer") or {}).get("id"),
                "selected_offer": offer and offer.get("id"),
                "required_cpu_flavor": authorization["required_cpu_flavor"],
                "inventories_empty": not any(ready.get("inventories", {}).values()),
                "unrelated_baseline_allowed": baseline_ok,
                "normalized_inventory": normalized_inventory(ready.get("inventories", {})),
                "offers": [{"id": row.get("id"), "availability": row.get("availability"),
                            "eligible": row.get("eligible")} for row in offers],
            })
            if (offer is not None and account_ready and baseline_ok
                    and ready["c27_budget"]["ready"] is True):
                break
            availability_only = (
                offer is None
                and account_ready
                and baseline_ok
                and required_offer.get("availability") == "NONE"
                and required_offer.get("eligible") is False
            )
            if not availability_only:
                shared.write(OUT / "PREFLIGHT.json", ready)
                raise RuntimeError("C27 account/resource/budget preflight failed")
            if time.time() >= preflight_deadline:
                shared.write(OUT / "PREFLIGHT.json", ready)
                raise RuntimeError("C27 Secure CPU availability wait expired before create")
            time.sleep(min(15, max(1, preflight_deadline - time.time())))
        record["preflight_poll_attempts"] = preflight_poll_attempts
        shared.write(OUT / "PREFLIGHT.json", ready)
        manifest = load(MANIFEST)
        if (
            manifest.get("schema") != "crse-c27-linux-replication-upload-manifest/v1"
            or manifest.get("file_count") != 63
            or len(manifest.get("files", [])) != 63
            or manifest.get("bytes") != 1078671
            or manifest.get("authorization_status")
            != "upload_not_authorized_exact_approval_pending"
            or manifest.get("run_name") != RUN_NAME
            or manifest.get("network_during_workload") is not False
            or manifest.get("scientific_contract", {}).get("measurement_batches") != 720
            or manifest.get("scientific_contract", {}).get("timed_queries") != 7560
            or manifest.get("scientific_contract", {}).get(
                "unchanged_c25_direct_controls") is not True
            or manifest.get("runtime", {}).get("image") != base.IMAGE
            or manifest.get("runtime", {}).get("python") != "3.13.15"
            or manifest.get("runtime", {}).get("numpy_requirement") != shared.NUMPY_REQUIREMENT
        ):
            raise RuntimeError("frozen C27 manifest mismatch")
        bundle = base.make_bundle(manifest)
        watchdog_process = arm_watchdog()
        client = preflight.session()
        live_baseline = shared.inventories(client)
        if not allowed_baseline(live_baseline):
            raise RuntimeError("unrelated RunPod baseline changed before C27 creation")
        shared.write(OUT / "PRECREATE-BASELINE.json", {
            "checked_utc": preflight.utc_now(),
            "inventory": normalized_inventory(live_baseline),
            "unrelated_baseline_allowed": True,
            "unrelated_baseline_modified": False,
        })
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
            "precreate_blocker_verification_sha256": sha256(PRECREATE_BLOCKER),
            "availability_blocker_verification_sha256": sha256(AVAILABILITY_BLOCKER),
            "prior_reconciliation_sha256": sha256(PRIOR_RECONCILIATION),
            "retry_authorization_request_sha256": sha256(RETRY_REQUEST),
            "retry_readiness_sha256": sha256(READINESS),
            "docker_repeatability_verification_sha256": sha256(DOCKER_REPEATABILITY),
            "portable_package_validation_sha256": sha256(PORTABLE_VALIDATION),
            "bootstrap_sha256": sha256(shared.BOOTSTRAP_PATH),
            "source_bundle_sha256": hashlib.sha256(bundle).hexdigest(),
            "source_bundle_bytes": len(bundle),
            "source_files": 63,
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
            raise RuntimeError("C27 pod creation failed HTTP " + str(response.status_code))
        pod = response.json()
        pod = pod.get("pod", pod)
        pod_id = pod.get("id")
        if not isinstance(pod_id, str) or not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
            raise RuntimeError("C27 creation response has no valid pod ID")
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
                record["unrelated_baseline_preserved_or_completed"] = allowed_baseline(
                    cleanup.get("inventories", {}))
                if (cleanup["owned_pod_absent"]
                        and record["unrelated_baseline_preserved_or_completed"]
                        and not record["creation_uncertain"]):
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
               or not record.get("cleanup", {}).get("owned_pod_absent")
               or record.get("unrelated_baseline_preserved_or_completed") is not True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watchdog", action="store_true")
    args = parser.parse_args()
    if not args.watchdog:
        OUT.mkdir(exist_ok=False)
    with c27_host_awake_guard(
            "c27-http-watchdog" if args.watchdog else "c27-http-controller"):
        return shared.watchdog() if args.watchdog else run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        error = {"error_type": type(exc).__name__}
        if type(exc) is RuntimeError:
            error["error"] = str(exc)
        print(json.dumps(error), flush=True)
        raise SystemExit(2)

