"""Execute one bounded, explicitly authorized C38 Linux/GCC replication."""
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
C31_CONTROLLER = ROOT / "docs/recognition/c31_linux_confirmation/runpod_c31_linux_controller.py"
spec = importlib.util.spec_from_file_location("c31_transport", C31_CONTROLLER)
c31 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c31)
shared, base, preflight = c31.shared, c31.base, c31.preflight

OUT = HERE / "runpod-c38-linux-execute-001"
MANIFEST = HERE / "c38_linux_upload_manifest.json"
AUTHORIZATION = HERE / "RUNPOD_C38_EXACT_PAYLOAD_AUTHORIZED_2026_09_03.json"
PROTOCOL = HERE / "C38_C37_NATIVE_SECOND_MACHINE_PROTOCOL_2026_09_03.md"
CONTRACT = HERE / "c38_c37_native_replication_contract.json"
LOCAL_VALIDATION = HERE / "C38_PACKAGE_LOCAL_VALIDATION_20260903.json"
REQUEST = HERE / "RUNPOD_C38_AUTHORIZATION_REQUEST_20260903.json"
RUN_NAME = "c38-c37-native-linux-gcc-20260903-001"
IMAGE_TAG = "python:3.13.15-bookworm"
IMAGE_AMD64_DIGEST = (
    "sha256:a53008522631dbcb063c4d5982aa91a00e86e51d90bbcf3513313f1a5c163af8"
)
IMAGE = f"{IMAGE_TAG}@{IMAGE_AMD64_DIGEST}"
RESULT_CAP_BYTES = 24 << 20

base.IMAGE_TAG = IMAGE_TAG
base.IMAGE_AMD64_DIGEST = IMAGE_AMD64_DIGEST
base.IMAGE = IMAGE
base.EVIDENCE_CAP = RESULT_CAP_BYTES
shared.CAP = RESULT_CAP_BYTES
base.REMOTE_CODE = shared.replace_remote_once(
    base.REMOTE_CODE, "CAP = 16 << 20", f"CAP = {RESULT_CAP_BYTES}",
)

C38_STAGE = (
    "emit('stage', name='c38-linux-replication')\n"
    "    run('c38-linux-replication', [sys.executable, '-B',\n"
    "         'scripts/cm_c38_linux_replication.py', '--run-id',\n"
    "         'c38-c37-native-linux-gcc-20260903-001', '--output',\n"
    "         str(OUT/'c38-c37-native-linux-gcc-20260903-001'),\n"
    "         '--compiler', 'cc', '--max-seconds', '1200'], 420)\n"
    "    emit('stage', name='c37-independent-verification')\n"
    "    run('c37-independent-verification', [sys.executable, '-B',\n"
    "         'scripts/crse_native_exact_confirmation_verify.py', '--run-dir',\n"
    "         str(OUT/'c38-c37-native-linux-gcc-20260903-001')], 180)\n"
    "    emit('stage', name='c38-independent-verification')\n"
    "    run('c38-independent-verification', [sys.executable, '-B',\n"
    "         'scripts/crse_c38_linux_replication_verify.py', '--run-dir',\n"
    "         str(OUT/'c38-c37-native-linux-gcc-20260903-001')], 180)"
)
base.REMOTE_CODE = shared.replace_remote_once(base.REMOTE_CODE, c31.new_stage, C38_STAGE)

C38_VALIDATION = (
    "    try:\n"
    "        study = OUT / 'c38-c37-native-linux-gcc-20260903-001'\n"
    "        result = json.loads((study / 'results.json').read_text())\n"
    "        c37_verified = json.loads((study / 'independent_verification.json').read_text())\n"
    "        c38_verified = json.loads((study / 'c38_independent_verification.json').read_text())\n"
    "        binding = json.loads((study / 'c38_runtime_binding.json').read_text())\n"
    "        validation['confirmation_summary'] = {\n"
    "            'status': result.get('status'),\n"
    "            'c37_verification_status': c37_verified.get('status'),\n"
    "            'c38_verification_status': c38_verified.get('status'),\n"
    "            'raw_sessions': c38_verified.get('raw_sessions_checked'),\n"
    "            'single_root_queries': c38_verified.get('single_root_queries_checked'),\n"
    "            'multi_root_output_queries': c38_verified.get('multi_root_output_queries_checked'),\n"
    "            'local_platform_validation_only': binding.get('local_platform_validation_only'),\n"
    "            'compiler': binding.get('compiler'),\n"
    "            'all_predeclared_gates_passed': result.get('decision', {}).get(\n"
    "                'all_predeclared_gates_passed'),\n"
    "            'single_root_speedup': result.get('single_root', {}).get(\n"
    "                'native_speedup_over_python_r2'),\n"
    "            'multi_root_speedup': result.get('multi_root', {}).get(\n"
    "                'union_speedup_over_separate')}\n"
    "    except Exception as exc:\n"
    "        validation['validation_error'] = type(exc).__name__ + ': ' + str(exc)"
)
base.REMOTE_CODE = shared.replace_remote_once(
    base.REMOTE_CODE, c31.new_validation, C38_VALIDATION,
)


def configure_transport() -> None:
    c31.OUT = OUT
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
    paths = {
        Path(__file__).resolve(),
        C31_CONTROLLER.resolve(),
        Path(c31.C16_CONTROLLER).resolve(),
        Path(c31.c16.OLD_PATH).resolve(),
        Path(c31.c16.transport.LEGACY_HERE / "runpod_retry_cpu8_v1_controller.py").resolve(),
        Path(c31.c16.transport.LEGACY_HERE / "http_corpus_preflight_v4.py").resolve(),
        Path(shared.BOOTSTRAP_PATH).resolve(),
    }
    return {
        path.relative_to(ROOT).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(paths)
    }


def require_authorization() -> dict:
    authorization = load(AUTHORIZATION)
    manifest = load(MANIFEST)
    validation = load(LOCAL_VALIDATION)
    request = load(REQUEST)
    expected = {
        "schema": "crse-runpod-c38-exact-payload-authorization/v1",
        "authorized": True,
        "user_total_ceiling_usd": 5.0,
        "controller_total_ceiling_usd": 0.05,
        "one_create": True,
        "no_replacement": True,
        "source_files": manifest["file_count"],
        "source_bytes": manifest["bytes"],
        "single_root_cases": 18,
        "single_root_blocks": 12,
        "multi_root_workloads": 6,
        "multi_root_blocks": 20,
        "raw_sessions": 954,
        "single_root_query_checks": 44928,
        "multi_root_output_query_checks": 48384,
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
        "credentials_recorded_or_uploaded": False,
        "training": False,
        "website_update": False,
        "production_write": False,
        "production_promotion": False,
    }
    if any(authorization.get(key) != value for key, value in expected.items()):
        raise RuntimeError("C38 authorization scope mismatch")
    if (
        authorization.get("upload_manifest_sha256") != sha256(MANIFEST)
        or authorization.get("protocol_sha256") != sha256(PROTOCOL)
        or authorization.get("local_validation_sha256") != sha256(LOCAL_VALIDATION)
        or authorization.get("replication_contract_sha256") != sha256(CONTRACT)
        or authorization.get("authorization_request_sha256") != sha256(REQUEST)
        or authorization.get("controller_sha256") != sha256(Path(__file__))
        or authorization.get("transport_sources") != transport_source_identities()
        or request.get("controller_sha256") != sha256(Path(__file__))
        or request.get("transport_sources") != transport_source_identities()
        or validation.get("status") != "pass"
        or validation.get("manifest_sha256") != sha256(MANIFEST)
        or validation.get("local_platform_validation_only") is not True
        or validation.get("timing_result_used_for_c38_decision") is not False
    ):
        raise RuntimeError("C38 authorization artifact mismatch")
    return authorization


def arm_watchdog():
    with (OUT / "watchdog.log").open("xb") as stream:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0
        )
        process = subprocess.Popen(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--watchdog"],
            stdout=stream, stderr=subprocess.STDOUT, creationflags=flags,
            close_fds=True,
        )
    for _ in range(200):
        if shared.READY.exists():
            ready = load(shared.READY)
            if not ready.get("network_probe_passed") or any(ready["startup_inventories"].values()):
                raise RuntimeError("C38 watchdog zero-pod readiness failed")
            shared.write(OUT / "WATCHDOG-PROCESS-BINDING.json", shared.bind_watchdog(process, ready))
            return process
        if process.poll() is not None:
            raise RuntimeError("C38 watchdog exited before readiness")
        time.sleep(0.2)
    raise RuntimeError("C38 watchdog failed to arm")


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
            raise RuntimeError("C38 HTTP bootstrap did not remain ready")
        record["bootstrap_ready_utc"] = preflight.utc_now()
        record["health_checks_before_upload"] = consecutive_health
        upload_events = []
        accepted = None
        for attempt in range(1, 7):
            try:
                accepted = json.loads(shared.proxy_request(
                    proxy, "POST", endpoint + "/payload", data=raw, timeout=20,
                ))
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
        record["payload_attempts"] = upload_events
        if accepted is None or accepted.get("accepted_sha256") != hashlib.sha256(raw).hexdigest():
            raise RuntimeError("C38 upload acknowledgement mismatch")
        record["uploaded_source_files"] = manifest["file_count"]
        record["uploaded_transport_bytes"] = len(raw)
        shared.proxy_request(proxy, "POST", endpoint + "/run", data=b"", timeout=10)
        record["worker_started_utc"] = preflight.utc_now()
        observed = None
        allowed_work = {
            "c38-linux-replication", "c37-independent-verification",
            "c38-independent-verification",
        }
        while time.time() < created + shared.CLEANUP_AT - 30:
            try:
                progress = json.loads(shared.proxy_request(
                    proxy, "GET", endpoint + "/progress", timeout=5,
                ))
            except (shared.requests.RequestException, RuntimeError, ValueError):
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
                    proxy, "GET", endpoint + "/results", cap=RESULT_CAP_BYTES, timeout=30,
                ).decode("utf-8")
            if time.time() >= created + 360 and progress.get("stage") not in allowed_work:
                raise RuntimeError("C38 boot/install exceeded six-minute setup deadline")
            time.sleep(2)
    raise RuntimeError("C38 remote worker deadline exceeded")


def save_evidence(log: str) -> dict:
    lines = log.splitlines()
    starts = [json.loads(line[9:]) for line in lines
              if line.startswith("CM_EVENT ") and '"kind": "evidence_start"' in line]
    if not starts:
        raise RuntimeError("C38 remote evidence marker missing")
    plain = "\n".join(line for line in lines if not line.startswith("CM_EVIDENCE ")) + "\n"
    if len(plain.encode()) + int(starts[-1]["bytes"]) + int(starts[-1]["uncompressed_bytes"]) > RESULT_CAP_BYTES:
        raise RuntimeError("C38 retrieved evidence exceeds cap")
    (OUT / "container.log").write_text(plain, encoding="utf-8")
    extracted = base.extract_evidence(lines)
    evidence = OUT / "evidence/run-output"
    validation = load(evidence / "REMOTE-VALIDATION.json")
    runtime = load(evidence / "RUNTIME.json")
    dependencies = load(evidence / "DEPENDENCIES.json")
    study = evidence / RUN_NAME
    result = load(study / "results.json")
    c37_verified = load(study / "independent_verification.json")
    c38_verified = load(study / "c38_independent_verification.json")
    binding = load(study / "c38_runtime_binding.json")
    confirmation = validation.get("confirmation_summary", {})
    rows = [line for line in (study / "raw_measurements.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    compiler = binding.get("compiler", {})
    mismatch_fields = (
        "parent_identity_mismatches", "derived_identity_mismatches",
        "source_map_mismatches", "dataset_rebinding_mismatches",
        "verification_rebinding_mismatches", "freeze_binding_mismatches",
        "c37_verification_mismatches", "result_boundary_mismatches",
    )
    manifest = load(MANIFEST)
    if (
        validation.get("status") != "complete"
        or validation.get("error") is not None
        or validation.get("validation_error") is not None
        or confirmation.get("status") != "complete"
        or confirmation.get("c37_verification_status") != "verified"
        or confirmation.get("c38_verification_status") != "verified"
        or confirmation.get("raw_sessions") != 954
        or confirmation.get("single_root_queries") != 44928
        or confirmation.get("multi_root_output_queries") != 48384
        or confirmation.get("local_platform_validation_only") is not False
        or result.get("status") != "complete"
        or result.get("correctness", {}).get("canonical_delivery_mismatches") != 0
        or result.get("decision", {}).get("training") is not False
        or result.get("decision", {}).get("policy_refit") is not False
        or result.get("decision", {}).get("gate_refit") is not False
        or result.get("decision", {}).get("production_promotion") is not False
        or c37_verified.get("status") != "verified"
        or c37_verified.get("raw_sessions_checked") != 954
        or c38_verified.get("status") != "verified"
        or c38_verified.get("local_platform_validation_only") is not False
        or any(c38_verified.get(field) != 0 for field in mismatch_fields)
        or len(rows) != 954
        or binding.get("local_platform_validation_only") is not False
        or compiler.get("kind") != "posix_c11"
        or compiler.get("role") != "decision_bearing_linux_replication"
        or not isinstance(compiler.get("version"), str) or not compiler["version"]
        or not re.fullmatch(r"[0-9a-f]{64}", compiler.get("executable_sha256", ""))
        or runtime.get("source_files") != manifest["file_count"]
        or runtime.get("runpod_pod_id") != load(shared.IDENTITY)["pod_id"]
        or runtime.get("image_tag") != IMAGE_TAG
        or runtime.get("image_amd64_digest") != IMAGE_AMD64_DIGEST
        or dependencies.get("numpy") != "2.3.2"
        or dependencies.get("dd") is not None
    ):
        raise RuntimeError("retrieved C38 evidence failed frozen exactness/binding checks")
    extracted["validation"] = validation
    extracted["runtime_pod_id"] = runtime["runpod_pod_id"]
    extracted["c38_linux_replication"] = {
        "compiler": compiler,
        "raw_sessions": 954,
        "single_root_query_checks": 44928,
        "multi_root_output_query_checks": 48384,
        "all_predeclared_gates_passed": result["decision"]["all_predeclared_gates_passed"],
        "single_root_speedup": result["single_root"]["native_speedup_over_python_r2"],
        "single_root_minimum_case_speedup": result["single_root"][
            "minimum_case_speedup_over_python_r2"
        ],
        "multi_root_speedup": result["multi_root"]["union_speedup_over_separate"],
        "multi_root_minimum_workload_speedup": result["multi_root"][
            "minimum_workload_speedup"
        ],
        "production_promotion": False,
    }
    return extracted


def write_cross_machine_summary() -> None:
    local_dir = ROOT / "docs/recognition/runs/c37-native-exact-confirmation-windows-20260903-001"
    remote_dir = OUT / "evidence/run-output" / RUN_NAME
    windows = load(local_dir / "results.json")
    linux = load(remote_dir / "results.json")
    linux_verification = load(remote_dir / "c38_independent_verification.json")
    document = {
        "schema": "crse-c38-c37-native-cross-machine-summary/v1",
        "status": (
            "cross_machine_performance_confirmed"
            if windows["decision"]["all_predeclared_gates_passed"]
            and linux["decision"]["all_predeclared_gates_passed"]
            else "exact_cross_machine_replication_complete_performance_not_confirmed"
        ),
        "executions": {
            "windows_msvc": {
                "results_sha256": sha256(local_dir / "results.json"),
                "all_predeclared_gates_passed": windows["decision"]["all_predeclared_gates_passed"],
                "single_root_speedup": windows["single_root"]["native_speedup_over_python_r2"],
                "multi_root_speedup": windows["multi_root"]["union_speedup_over_separate"],
            },
            "linux_gcc": {
                "results_sha256": sha256(remote_dir / "results.json"),
                "verification_sha256": sha256(
                    remote_dir / "c38_independent_verification.json"
                ),
                "compiler": linux_verification["compiler"],
                "pod_id": load(shared.IDENTITY)["pod_id"],
                "all_predeclared_gates_passed": linux["decision"]["all_predeclared_gates_passed"],
                "single_root_speedup": linux["single_root"]["native_speedup_over_python_r2"],
                "multi_root_speedup": linux["multi_root"]["union_speedup_over_separate"],
            },
        },
        "exactness_verified_on_both": True,
        "os_and_compiler_families": 2,
        "training": False,
        "website_update": False,
        "production_promotion": False,
    }
    shared.write(OUT / "C38-CROSS-MACHINE-SUMMARY.json", document)


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
        ready["c38_budget"] = {
            "rate_usd_per_hour": rate,
            "projected_10_minute_cost_usd": projected,
            "total_cost_cap_usd": shared.CAMPAIGN_CAP,
            "ready": bool(math.isfinite(rate) and 0 < rate <= shared.RATE_CAP
                          and projected <= shared.CAMPAIGN_CAP),
        }
        shared.write(OUT / "PREFLIGHT.json", ready)
        if not ready["ready"] or not ready["c38_budget"]["ready"] or any(ready["inventories"].values()):
            raise RuntimeError("C38 account/resource/budget preflight failed")
        manifest = load(MANIFEST)
        contract = manifest.get("scientific_contract", {})
        if (
            manifest.get("schema")
            != "crse-c38-c37-native-linux-replication-upload-manifest/v1"
            or manifest.get("file_count") != len(manifest.get("files", []))
            or manifest.get("bytes") != sum(row["bytes"] for row in manifest["files"])
            or manifest.get("authorization_status")
            != "upload_not_authorized_exact_approval_pending"
            or manifest.get("run_name") != RUN_NAME
            or manifest.get("network_during_workload") is not False
            or manifest.get("result_cap_bytes") != RESULT_CAP_BYTES
            or contract.get("raw_sessions") != 954
            or contract.get("single_root_exact_query_checks") != 44928
            or contract.get("multi_root_exact_output_query_checks") != 48384
            or manifest.get("replication_contract_sha256") != sha256(CONTRACT)
            or manifest.get("protocol_sha256") != sha256(PROTOCOL)
            or manifest.get("runtime", {}).get("image") != IMAGE
            or manifest.get("runtime", {}).get("python") != "3.13.15"
            or manifest.get("runtime", {}).get("numpy_requirement") != shared.NUMPY_REQUIREMENT
        ):
            raise RuntimeError("frozen C38 manifest mismatch")
        bundle = base.make_bundle(manifest)
        watchdog_process = arm_watchdog()
        client = preflight.session()
        if any(shared.inventories(client).values()):
            raise RuntimeError("zero-pod baseline changed before C38 creation")
        created = time.time()
        state = {
            "name": "cm-c38-linux-" + uuid.uuid4().hex[:12],
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
            "local_validation_sha256": sha256(LOCAL_VALIDATION),
            "replication_contract_sha256": sha256(CONTRACT),
            "authorization_request_sha256": sha256(REQUEST),
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
        response = client.post(
            preflight.V1 + "/pods", json=body, timeout=(10, 50), allow_redirects=False,
        )
        record["creation_http_status"] = response.status_code
        if response.status_code not in (200, 201):
            record["creation_uncertain"] = not 400 <= response.status_code < 500
            raise RuntimeError("C38 pod creation failed HTTP " + str(response.status_code))
        pod = response.json()
        pod = pod.get("pod", pod)
        pod_id = pod.get("id")
        if not isinstance(pod_id, str) or not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
            raise RuntimeError("C38 creation response has no valid pod ID")
        shared.write(shared.IDENTITY, {
            "pod_id": pod_id, "name": state["name"],
            "recorded_utc": preflight.utc_now(), "source": "this create response",
        })
        record.update({"pod_id": pod_id, "pod_created": True, "creation_uncertain": False})
        pod = shared.actual_pod(client, pod_id)
        shared.write(OUT / "POD-RESOURCE-CHECK.json", {
            "checked_utc": preflight.utc_now(),
            "response_fields": sorted(pod),
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
        log = execute_remote(pod_id, token, raw, created, record)
        record["evidence"] = save_evidence(log)
        write_cross_machine_summary()
        record["status"] = "complete"
    except Exception as exc:
        record["status"] = "failed"
        record["error_type"] = type(exc).__name__
        if type(exc) is RuntimeError:
            record["error"] = str(exc)
        if state is not None and not shared.ABORT.exists():
            shared.write(shared.ABORT, {
                "requested_utc": preflight.utc_now(), "reason": record["error_type"],
            })
    finally:
        if state is not None and client is not None:
            try:
                cleanup = shared.cleanup_owned(client, state, "controller")
                record["cleanup"] = cleanup
                if cleanup["owned_pod_absent"] and not record["creation_uncertain"]:
                    shared.write(shared.DONE, {
                        "finished_utc": preflight.utc_now(), "owned_pod_absent_verified": True,
                    })
            except Exception as exc:
                record["cleanup_error_type"] = type(exc).__name__
        elif not shared.DONE.exists():
            shared.write(shared.DONE, {
                "finished_utc": preflight.utc_now(), "no_create_request": True,
            })
        record["finished_utc"] = preflight.utc_now()
        if state is not None:
            record["elapsed_since_create_s"] = time.time() - state["created_epoch"]
            actual_rate = record.get("actual_resources", {}).get("rate_usd_per_hour")
            record["estimated_compute_cost_usd"] = (
                actual_rate * record["elapsed_since_create_s"] / 3600
                if actual_rate else None
            )
        shared.write(OUT / "RUN.json", record)
        if client is not None:
            client.close()
    print(json.dumps(record, indent=2), flush=True)
    return int(
        record["status"] != "complete"
        or not record.get("cleanup", {}).get("owned_pod_absent")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watchdog", action="store_true")
    args = parser.parse_args()
    if not args.watchdog:
        OUT.mkdir(exist_ok=False)
    with base.host_awake_guard(
        "c38-http-watchdog" if args.watchdog else "c38-http-controller"
    ):
        return shared.watchdog() if args.watchdog else run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}), flush=True)
        raise SystemExit(2)
