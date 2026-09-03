"""Execute one bounded, exactly authorized query-ladder follow-up on RunPod."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import uuid


ROOT = Path(__file__).resolve().parents[1]
PARENT_CONTROLLER = ROOT / "scripts/runpod_architecture_comparison_controller.py"
spec = importlib.util.spec_from_file_location("architecture_comparison_transport", PARENT_CONTROLLER)
parent_controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent_controller)
shared = parent_controller.shared
base = parent_controller.base
preflight = parent_controller.preflight

HERE = ROOT / "docs/recognition/architecture_query_ladder_followup_execution_20260903"
OUT = HERE / "runpod-architecture-query-ladder-execute-001"
MANIFEST = HERE / "UPLOAD_MANIFEST.json"
AUTHORIZATION = HERE / "RUNPOD_ARCHITECTURE_QUERY_LADDER_EXACT_PAYLOAD_AUTHORIZED_2026_09_03.json"
PROTOCOL = HERE / "PROTOCOL.md"
CONTRACT = HERE / "EXECUTION_CONTRACT.json"
LOCAL_VALIDATION = HERE / "LOCAL_PACKAGE_VALIDATION.json"
REQUEST = HERE / "RUNPOD_AUTHORIZATION_REQUEST_20260903.json"
FREEZE = ROOT / "docs/recognition/architecture_query_ladder_followup_freeze_20260903/FREEZE.json"
RUN_NAME = "architecture-query-ladder-linux-gcc-20260903-001"
IMAGE_TAG = "python:3.13.15-bookworm"
IMAGE_AMD64_DIGEST = "sha256:a53008522631dbcb063c4d5982aa91a00e86e51d90bbcf3513313f1a5c163af8"
IMAGE = f"{IMAGE_TAG}@{IMAGE_AMD64_DIGEST}"
RESULT_CAP_BYTES = 48 << 20
TOTAL_ROWS = 27_648
QUERY_ROWS = {"1": 6_912, "4": 6_912, "16": 6_912, "64": 6_912}
EXPECTED_COUNTS = {"ok": TOTAL_ROWS, "refused": 0, "failed": 0}
DEPENDENCIES = parent_controller.DEPENDENCIES
INSTALL_CODE = parent_controller.INSTALL_CODE


base.IMAGE_TAG = IMAGE_TAG
base.IMAGE_AMD64_DIGEST = IMAGE_AMD64_DIGEST
base.IMAGE = IMAGE
base.EVIDENCE_CAP = RESULT_CAP_BYTES
shared.CAP = RESULT_CAP_BYTES
shared.CAMPAIGN_CAP = 0.05
shared.RATE_CAP = 0.25
shared.CLEANUP_AT = 600
shared.HORIZON = 720

QUERY_LADDER_STAGE = (
    "emit('stage', name='architecture-dependencies-install')\n"
    f"    run('architecture-dependencies-install', [sys.executable, '-c', {INSTALL_CODE!r}, "
    "str(OUT/'ARCHITECTURE-DEPENDENCIES.json')], 180)\n"
    "    emit('stage', name='architecture-query-ladder-campaign')\n"
    "    run('architecture-query-ladder-campaign', [sys.executable, '-B',\n"
    "         'scripts/cm_architecture_query_ladder_campaign.py', '--output',\n"
    "         str(OUT/'architecture-query-ladder-linux-gcc-20260903-001'),\n"
    "         '--compiler', 'cc', '--freeze',\n"
    "         'docs/recognition/architecture_query_ladder_followup_freeze_20260903/FREEZE.json',\n"
    "         '--oracles',\n"
    "         'docs/recognition/architecture_comparison_execution_retry_20260903/ORACLES.json',\n"
    "         '--max-seconds', '420'], 480)\n"
    "    emit('stage', name='architecture-query-ladder-verification')\n"
    "    run('architecture-query-ladder-verification', [sys.executable, '-B',\n"
    "         'scripts/crse_verify_architecture_query_ladder_campaign.py', '--run-dir',\n"
    "         str(OUT/'architecture-query-ladder-linux-gcc-20260903-001'), '--freeze',\n"
    "         'docs/recognition/architecture_query_ladder_followup_freeze_20260903/FREEZE.json',\n"
    "         '--oracles',\n"
    "         'docs/recognition/architecture_comparison_execution_retry_20260903/ORACLES.json'], 120)"
)
base.REMOTE_CODE = shared.replace_remote_once(
    base.REMOTE_CODE, parent_controller.ARCHITECTURE_STAGE, QUERY_LADDER_STAGE,
)

QUERY_LADDER_VALIDATION = (
    "    try:\n"
    "        study = OUT / 'architecture-query-ladder-linux-gcc-20260903-001'\n"
    "        result = json.loads((study / 'results.json').read_text())\n"
    "        verified = json.loads((study / 'independent_verification.json').read_text())\n"
    "        binding = json.loads((study / 'runtime_binding.json').read_text())\n"
    "        dependencies = json.loads((OUT / 'ARCHITECTURE-DEPENDENCIES.json').read_text())\n"
    "        validation['query_ladder_summary'] = {\n"
    "            'status': result.get('status'),\n"
    "            'verification_status': verified.get('status'),\n"
    "            'rows_checked': verified.get('rows_checked'),\n"
    "            'query_rows': verified.get('query_rows'),\n"
    "            'counts': verified.get('counts'),\n"
    "            'semantic_mismatches': verified.get('semantic_mismatches'),\n"
    "            'schedule_mismatches': verified.get('schedule_mismatches'),\n"
    "            'source_or_artifact_mismatches': verified.get('source_or_artifact_mismatches'),\n"
    "            'memory_measurement_mismatches': verified.get('memory_measurement_mismatches'),\n"
    "            'all_query_counts_separately_timed': verified.get('all_query_counts_separately_timed'),\n"
    "            'all_cells_isolated_for_memory': verified.get('all_cells_isolated_for_memory'),\n"
    "            'runtime_role': binding.get('role'),\n"
    "            'compiler_version': binding.get('compiler_version'),\n"
    "            'dependency_versions': dependencies.get('versions')}\n"
    "    except Exception as exc:\n"
    "        validation['validation_error'] = type(exc).__name__ + ': ' + str(exc)"
)
base.REMOTE_CODE = shared.replace_remote_once(
    base.REMOTE_CODE, parent_controller.ARCHITECTURE_VALIDATION, QUERY_LADDER_VALIDATION,
)


def configure_transport() -> None:
    parent_controller.OUT = OUT
    parent_controller.c38.OUT = OUT
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


def transport_source_identities() -> dict[str, dict[str, int | str]]:
    rows = parent_controller.transport_source_identities()
    controller = Path(__file__).resolve()
    rows[controller.relative_to(ROOT).as_posix()] = {
        "bytes": controller.stat().st_size,
        "sha256": sha256(controller),
    }
    return dict(sorted(rows.items()))


def require_authorization() -> dict:
    authorization = load(AUTHORIZATION)
    manifest = load(MANIFEST)
    validation = load(LOCAL_VALIDATION)
    request = load(REQUEST)
    expected = {
        "schema": "cm-runpod-architecture-query-ladder-exact-payload-authorization/v1",
        "authorized": True,
        "user_total_ceiling_usd": 0.05,
        "controller_total_ceiling_usd": 0.05,
        "one_create": True,
        "no_replacement": True,
        "source_files": manifest["file_count"],
        "source_bytes": manifest["bytes"],
        "planned_rows": TOTAL_ROWS,
        "query_rows": QUERY_ROWS,
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
        "result_cap_bytes": RESULT_CAP_BYTES,
        "compiler": "cc",
        "image": IMAGE,
        "local_isolated_validation": "pass",
        "local_validation_pythonpath_injected": False,
        "isolated_memory_method": "isolated_fork_child_wait4_ru_maxrss/v1",
        "credentials_recorded_or_uploaded": False,
        "prior_authorization_reused": False,
        "training": False,
        "selector_fit": False,
        "website_update": False,
        "production_write": False,
    }
    if any(authorization.get(key) != value for key, value in expected.items()):
        raise RuntimeError("query-ladder authorization scope mismatch")
    hashes = {
        "upload_manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "execution_contract_sha256": sha256(CONTRACT),
        "local_validation_sha256": sha256(LOCAL_VALIDATION),
        "freeze_sha256": sha256(FREEZE),
        "authorization_request_sha256": sha256(REQUEST),
        "controller_sha256": sha256(Path(__file__)),
    }
    if (
        any(authorization.get(key) != value for key, value in hashes.items())
        or authorization.get("transport_sources") != transport_source_identities()
        or any(request.get(key) != value for key, value in hashes.items() if key != "authorization_request_sha256")
        or request.get("transport_sources") != transport_source_identities()
        or validation.get("status") != "pass"
        or validation.get("manifest_sha256") != sha256(MANIFEST)
        or validation.get("pythonpath_injected") is not False
        or validation.get("parent_and_followup_freeze_verification_passed") is not True
        or validation.get("timing_evidence_produced") is not False
        or validation.get("memory_evidence_produced") is not False
        or validation.get("decision_bearing_result_produced") is not False
    ):
        raise RuntimeError("query-ladder authorization artifact mismatch")
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
                raise RuntimeError("query-ladder watchdog zero-pod readiness failed")
            shared.write(OUT / "WATCHDOG-PROCESS-BINDING.json", shared.bind_watchdog(process, ready))
            return process
        if process.poll() is not None:
            raise RuntimeError("query-ladder watchdog exited before readiness")
        time.sleep(0.2)
    raise RuntimeError("query-ladder watchdog failed to arm")


def execute_remote(pod_id: str, token: str, raw: bytes, created: float, record: dict) -> str:
    endpoint = f"https://{pod_id}-8080.proxy.runpod.net"
    manifest = load(MANIFEST)
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
            raise RuntimeError("query-ladder HTTP bootstrap did not remain ready")
        record["bootstrap_ready_utc"] = preflight.utc_now()
        record["health_checks_before_upload"] = consecutive_health
        accepted = None
        attempts = []
        for attempt in range(1, 7):
            try:
                accepted = json.loads(shared.proxy_request(proxy, "POST", endpoint + "/payload", data=raw, timeout=20))
                attempts.append({"attempt": attempt, "checked_utc": preflight.utc_now(), "status": "accepted"})
                break
            except RuntimeError as exc:
                attempts.append({"attempt": attempt, "checked_utc": preflight.utc_now(), "status": str(exc)})
                if str(exc) != "proxy HTTP 404" or attempt == 6:
                    record["payload_attempts"] = attempts
                    raise
                time.sleep(2)
        record["payload_attempts"] = attempts
        if accepted is None or accepted.get("accepted_sha256") != hashlib.sha256(raw).hexdigest():
            raise RuntimeError("query-ladder upload acknowledgement mismatch")
        record["uploaded_source_files"] = manifest["file_count"]
        record["uploaded_transport_bytes"] = len(raw)
        shared.proxy_request(proxy, "POST", endpoint + "/run", data=b"", timeout=10)
        record["worker_started_utc"] = preflight.utc_now()
        observed = None
        allowed_work = {"architecture-query-ladder-campaign", "architecture-query-ladder-verification"}
        while time.time() < created + shared.CLEANUP_AT - 30:
            try:
                progress = json.loads(shared.proxy_request(proxy, "GET", endpoint + "/progress", timeout=5))
            except (shared.requests.RequestException, RuntimeError, ValueError):
                time.sleep(2)
                continue
            signature = (progress.get("stage"), progress.get("done"), progress.get("error"))
            if signature != observed:
                shared.append(OUT / "progress.jsonl", {"checked_utc": preflight.utc_now(), **progress})
                print(json.dumps({"stage": progress.get("stage"), "done": progress.get("done"), "error": progress.get("error")}), flush=True)
                observed = signature
            if progress.get("done"):
                record["remote_progress"] = progress
                return shared.proxy_request(
                    proxy, "GET", endpoint + "/results", cap=RESULT_CAP_BYTES, timeout=30,
                ).decode("utf-8")
            if time.time() >= created + 360 and progress.get("stage") not in allowed_work:
                raise RuntimeError("query-ladder boot/install exceeded six-minute deadline")
            time.sleep(2)
    raise RuntimeError("query-ladder remote worker deadline exceeded")


def save_evidence(log: str) -> dict:
    lines = log.splitlines()
    starts = [
        json.loads(line[9:]) for line in lines
        if line.startswith("CM_EVENT ") and '"kind": "evidence_start"' in line
    ]
    if not starts:
        raise RuntimeError("query-ladder remote evidence marker missing")
    plain = "\n".join(line for line in lines if not line.startswith("CM_EVIDENCE ")) + "\n"
    if len(plain.encode()) + int(starts[-1]["bytes"]) + int(starts[-1]["uncompressed_bytes"]) > RESULT_CAP_BYTES:
        raise RuntimeError("query-ladder retrieved evidence exceeds cap")
    (OUT / "container.log").write_text(plain, encoding="utf-8")
    extracted = base.extract_evidence(lines)
    evidence = OUT / "evidence/run-output"
    validation = load(evidence / "REMOTE-VALIDATION.json")
    runtime = load(evidence / "RUNTIME.json")
    dependencies = load(evidence / "ARCHITECTURE-DEPENDENCIES.json")
    study = evidence / RUN_NAME
    result = load(study / "results.json")
    verified = load(study / "independent_verification.json")
    binding = load(study / "runtime_binding.json")
    summary = validation.get("query_ladder_summary", {})
    manifest = load(MANIFEST)
    raw_rows = sum(1 for line in (study / "raw_measurements.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())
    versions = dependencies.get("versions", {})
    if (
        validation.get("status") != "complete"
        or validation.get("error") is not None
        or validation.get("validation_error") is not None
        or summary.get("status") != "complete"
        or summary.get("verification_status") != "verified_complete"
        or summary.get("rows_checked") != TOTAL_ROWS
        or summary.get("query_rows") != QUERY_ROWS
        or summary.get("counts") != EXPECTED_COUNTS
        or any(summary.get(key) != 0 for key in (
            "semantic_mismatches", "schedule_mismatches", "source_or_artifact_mismatches",
            "memory_measurement_mismatches",
        ))
        or summary.get("all_query_counts_separately_timed") is not True
        or summary.get("all_cells_isolated_for_memory") is not True
        or result.get("status") != "complete"
        or result.get("expected_rows") != TOTAL_ROWS
        or result.get("counts") != EXPECTED_COUNTS
        or raw_rows != TOTAL_ROWS
        or verified.get("status") != "verified_complete"
        or verified.get("rows_checked") != TOTAL_ROWS
        or verified.get("query_rows") != QUERY_ROWS
        or any(verified.get(key) != 0 for key in (
            "semantic_mismatches", "schedule_mismatches", "source_or_artifact_mismatches",
            "memory_measurement_mismatches",
        ))
        or binding.get("role") != "decision_bearing_linux_query_ladder_followup"
        or not binding.get("compiler_version")
        or not re.fullmatch(r"[0-9a-f]{64}", binding.get("compiler_executable_sha256", ""))
        or versions != {"networkx": "3.6.1", "python-sat": "1.9.dev15", "six": "1.17.0"}
        or runtime.get("source_files") != manifest["file_count"]
        or runtime.get("runpod_pod_id") != load(shared.IDENTITY)["pod_id"]
        or runtime.get("image_tag") != IMAGE_TAG
        or runtime.get("image_amd64_digest") != IMAGE_AMD64_DIGEST
        or any(result.get("decision", {}).get(key) is not False for key in (
            "selector_fitted", "neural_training", "production_routing_changed", "website_updated"
        ))
    ):
        raise RuntimeError("retrieved query-ladder evidence failed frozen checks")
    extracted["validation"] = validation
    extracted["runtime_pod_id"] = runtime["runpod_pod_id"]
    extracted["architecture_query_ladder"] = {
        "rows": TOTAL_ROWS,
        "query_rows": QUERY_ROWS,
        "counts": EXPECTED_COUNTS,
        "compiler_version": binding["compiler_version"],
        "performance_interpretation_permitted": True,
        "descriptive_host_memory_interpretation_permitted": True,
        "cross_machine_claim_permitted": False,
        "selector_or_neural_claim_permitted": False,
        "website_update_permitted": False,
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
        ready = preflight.check()
        offer = ready.get("selected_offer")
        rate = float(offer["rate_usd_per_hour"]) if offer else float("nan")
        projected = (rate + shared.STORAGE_RATE_RESERVE) * shared.CLEANUP_AT / 3600
        ready["query_ladder_budget"] = {
            "rate_usd_per_hour": rate,
            "projected_10_minute_cost_usd": projected,
            "total_cost_cap_usd": shared.CAMPAIGN_CAP,
            "ready": bool(math.isfinite(rate) and 0 < rate <= shared.RATE_CAP and projected <= shared.CAMPAIGN_CAP),
        }
        shared.write(OUT / "PREFLIGHT.json", ready)
        if not ready["ready"] or not ready["query_ladder_budget"]["ready"] or any(ready["inventories"].values()):
            raise RuntimeError("query-ladder account/resource/budget preflight failed")
        manifest = load(MANIFEST)
        contract = load(CONTRACT)
        runtime_dependencies = {row.get("name"): row for row in manifest.get("runtime", {}).get("dependencies", [])}
        if (
            manifest.get("schema") != "cm-architecture-query-ladder-runpod-upload-manifest/v1"
            or manifest.get("file_count") != len(manifest.get("files", []))
            or manifest.get("bytes") != sum(row["bytes"] for row in manifest["files"])
            or manifest.get("authorization_status") != "upload_not_authorized_exact_approval_pending"
            or manifest.get("run_name") != RUN_NAME
            or manifest.get("network_during_workload") is not False
            or manifest.get("result_cap_bytes") != RESULT_CAP_BYTES
            or manifest.get("execution_contract_sha256") != sha256(CONTRACT)
            or manifest.get("protocol_sha256") != sha256(PROTOCOL)
            or manifest.get("freeze_sha256") != sha256(FREEZE)
            or manifest.get("runtime", {}).get("image") != IMAGE
            or runtime_dependencies.get("numpy", {}).get("version") != "2.3.2"
            or runtime_dependencies.get("numpy", {}).get("sha256") != "938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f"
            or any(runtime_dependencies.get(row["name"]) != row for row in DEPENDENCIES)
            or contract.get("schedule", {}).get("total_cells") != TOTAL_ROWS
            or contract.get("schedule", {}).get("cells_per_query_count") != 6_912
            or contract.get("schedule", {}).get("query_counts") != [1, 4, 16, 64]
            or contract.get("limits", {}).get("workload_wall_seconds") != 420
            or contract.get("memory", {}).get("method") != "isolated_fork_child_wait4_ru_maxrss/v1"
        ):
            raise RuntimeError("frozen query-ladder manifest mismatch")
        bundle = base.make_bundle(manifest)
        watchdog_process = arm_watchdog()
        client = preflight.session()
        if any(shared.inventories(client).values()):
            raise RuntimeError("zero-pod baseline changed before query-ladder creation")
        created = time.time()
        state = {
            "name": "cm-c7-linux-" + uuid.uuid4().hex[:12],
            "created_epoch": created,
            "cleanup_epoch": created + shared.CLEANUP_AT,
            "horizon_epoch": created + shared.HORIZON,
        }
        raw = shared.prepare_payload(bundle, manifest, created)
        token = secrets.token_urlsafe(32)
        body = shared.create_payload(state["name"], offer, token, raw, created)
        shared.write(OUT / "TRANSPORT-FREEZE.json", {
            "controller_sha256": sha256(Path(__file__)),
            "authorization_sha256": sha256(AUTHORIZATION),
            "protocol_sha256": sha256(PROTOCOL),
            "execution_contract_sha256": sha256(CONTRACT),
            "local_validation_sha256": sha256(LOCAL_VALIDATION),
            "authorization_request_sha256": sha256(REQUEST),
            "freeze_sha256": sha256(FREEZE),
            "transport_sources": transport_source_identities(),
            "source_bundle_sha256": hashlib.sha256(bundle).hexdigest(),
            "source_bundle_bytes": len(bundle),
            "source_files": manifest["file_count"],
            "source_bytes": manifest["bytes"],
            "transport_payload_sha256": hashlib.sha256(raw).hexdigest(),
            "transport_payload_bytes": len(raw),
            "manifest_sha256": sha256(MANIFEST),
            "credentials_recorded_or_uploaded": False,
        })
        shared.write(shared.STATE, state)
        shared.confirm_watchdog(watchdog_process, state)
        record.update({
            "creation_attempted": True, "creation_uncertain": True,
            "creation_request_utc": preflight.utc_now(),
            "creation_endpoint": preflight.V1 + "/pods", "name": state["name"],
            "selected_cpu": offer["id"], "quoted_rate_usd_per_hour": offer["rate_usd_per_hour"],
        })
        print(json.dumps({"action": "create_one_cpu_pod", "name": state["name"], "cpu": offer["id"], "rate": offer["rate_usd_per_hour"]}), flush=True)
        response = client.post(preflight.V1 + "/pods", json=body, timeout=(10, 50), allow_redirects=False)
        record["creation_http_status"] = response.status_code
        if response.status_code not in (200, 201):
            record["creation_uncertain"] = not 400 <= response.status_code < 500
            raise RuntimeError("query-ladder pod creation failed HTTP " + str(response.status_code))
        pod = response.json()
        pod = pod.get("pod", pod)
        pod_id = pod.get("id")
        if not isinstance(pod_id, str) or not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
            raise RuntimeError("query-ladder creation response has no valid pod ID")
        shared.write(shared.IDENTITY, {
            "pod_id": pod_id, "name": state["name"], "recorded_utc": preflight.utc_now(),
            "source": "this create response",
        })
        record.update({"pod_id": pod_id, "pod_created": True, "creation_uncertain": False})
        pod = shared.actual_pod(client, pod_id)
        shared.write(OUT / "POD-RESOURCE-CHECK.json", {
            "checked_utc": preflight.utc_now(), "response_fields": sorted(pod),
            "pod": {key: pod.get(key) for key in (
                "id", "name", "image", "imageName", "computeType", "cloudType", "cloud",
                "verified_v2_cloud", "cpuFlavorId", "vcpuCount", "memoryInGb", "costPerHr",
                "containerDiskInGb", "volumeInGb", "volumeMountPath", "ports",
            )},
            "machine_secure_cloud": (pod.get("machine") or {}).get("secureCloud"),
            "gpu": {key: (pod.get("gpu") or {}).get(key) for key in ("id", "count")},
            "network_volume_present": bool(pod.get("networkVolume")),
        })
        record["actual_resources"] = shared.validate_pod(pod, state, offer)
        record["evidence"] = save_evidence(execute_remote(pod_id, token, raw, created, record))
        record["status"] = "complete"
    except Exception as exc:
        record["status"] = "failed"
        record["error_type"] = type(exc).__name__
        if type(exc) is RuntimeError:
            record["error"] = str(exc)
        if state is not None and not shared.ABORT.exists():
            shared.write(shared.ABORT, {"requested_utc": preflight.utc_now(), "reason": record["error_type"]})
    finally:
        if state is not None and client is not None:
            try:
                cleanup = shared.cleanup_owned(client, state, "controller")
                record["cleanup"] = cleanup
                if cleanup["owned_pod_absent"] and not record["creation_uncertain"]:
                    shared.write(shared.DONE, {"finished_utc": preflight.utc_now(), "owned_pod_absent_verified": True})
            except Exception as exc:
                record["cleanup_error_type"] = type(exc).__name__
        elif not shared.DONE.exists():
            shared.write(shared.DONE, {"finished_utc": preflight.utc_now(), "no_create_request": True})
        record["finished_utc"] = preflight.utc_now()
        if state is not None:
            record["elapsed_since_create_s"] = time.time() - state["created_epoch"]
            actual_rate = record.get("actual_resources", {}).get("rate_usd_per_hour")
            record["estimated_compute_cost_usd"] = actual_rate * record["elapsed_since_create_s"] / 3600 if actual_rate else None
        shared.write(OUT / "RUN.json", record)
        if client is not None:
            client.close()
    print(json.dumps(record, indent=2), flush=True)
    return int(record["status"] != "complete" or not record.get("cleanup", {}).get("owned_pod_absent"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watchdog", action="store_true")
    args = parser.parse_args()
    if not args.watchdog:
        OUT.mkdir(exist_ok=False)
    with base.host_awake_guard(
        "architecture-query-ladder-watchdog" if args.watchdog else "architecture-query-ladder-controller"
    ):
        return shared.watchdog() if args.watchdog else run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}), flush=True)
        raise SystemExit(2)
