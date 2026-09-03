"""Execute one exactly authorized Clang query-ladder replication on a different host class."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RETRY_CONTROLLER_PATH = ROOT / "scripts/runpod_architecture_query_ladder_retry_002_controller.py"
spec = importlib.util.spec_from_file_location(
    "query_ladder_cross_machine_base", RETRY_CONTROLLER_PATH,
)
retry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retry)
controller = retry.controller
shared = retry.shared
base = retry.base

HERE = ROOT / "docs/recognition/architecture_query_ladder_cross_machine_execution_20260904"
OUT = HERE / "runpod-architecture-query-ladder-cross-machine-execute-001"
MANIFEST = HERE / "UPLOAD_MANIFEST.json"
AUTHORIZATION = (
    HERE
    / "RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_EXACT_PAYLOAD_AUTHORIZED_2026_09_04.json"
)
PROTOCOL = HERE / "PROTOCOL.md"
CONTRACT = HERE / "EXECUTION_CONTRACT.json"
LOCAL_VALIDATION = HERE / "LOCAL_PACKAGE_VALIDATION.json"
REQUEST = HERE / "RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_AUTHORIZATION_REQUEST_20260904.json"
FREEZE = ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_freeze_20260904/FREEZE.json"
PRIOR_ROOT = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
    / "runpod-architecture-query-ladder-execute-002"
)
PRIOR_RUN = PRIOR_ROOT / "RUN.json"
PRIOR_RUNTIME = PRIOR_ROOT / "evidence/run-output/RUNTIME.json"
PRIOR_STUDY = (
    PRIOR_ROOT / "evidence/run-output/architecture-query-ladder-linux-gcc-20260904-002"
)
PRIOR_RESULTS = PRIOR_STUDY / "results.json"
PRIOR_VERIFICATION = PRIOR_STUDY / "independent_verification.json"
PRIOR_BINDING = PRIOR_STUDY / "runtime_binding.json"
PRIOR_POST_INVENTORY = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
    / "POST_RUN_INVENTORY.json"
)

RUN_NAME = "architecture-query-ladder-linux-clang-20260904-003"
COMPILER = "/usr/bin/clang-14"
CLANG_PACKAGE = "clang-14"
CLANG_PACKAGE_VERSION = "1:14.0.6-12"
PREFERRED_CPU_FLAVOR = "cpu5c"
PRIOR_CPU_FLAVOR = "cpu3c"
PRIOR_POD_ID = "r5wx3ximopqw7g"
PRIOR_CPU_MODEL = "AMD EPYC 9655 96-Core Processor"
PRIOR_COMPILER_SHA256 = "75e997ec62297a6484f491bae28ab0ccb489daba23e398fd10fe68e9e6f0def8"
TOTAL_COST_CAP_USD = 0.02
CUMULATIVE_HARD_CEILING_USD = 0.04
RATE_CAP_USD_PER_HOUR = 0.10
PRIOR_ESTIMATED_COST_USD = 0.0115828542470932


HOST_PREFLIGHT_CODE = f"""
import hashlib
import json
from pathlib import Path
import sys

output = Path(sys.argv[1])
runtime = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
cpu_model = runtime.get('cpu_model')
pod_id = runtime.get('runpod_pod_id')
if not isinstance(cpu_model, str) or not cpu_model or cpu_model == {PRIOR_CPU_MODEL!r}:
    raise SystemExit('replication host CPU model is not independent from prior host class')
if not isinstance(pod_id, str) or not pod_id or pod_id == {PRIOR_POD_ID!r}:
    raise SystemExit('replication Pod identity is not new')
boot_path = Path('/proc/sys/kernel/random/boot_id')
boot_id = boot_path.read_text(encoding='utf-8').strip()
if not boot_id:
    raise SystemExit('host boot identity unavailable')
document = {{
    'schema': 'cm-architecture-query-ladder-cross-machine-host-preflight/v1',
    'status': 'pass',
    'prior_pod_id': {PRIOR_POD_ID!r},
    'current_pod_id': pod_id,
    'prior_cpu_model': {PRIOR_CPU_MODEL!r},
    'current_cpu_model': cpu_model,
    'cpu_model_differs': True,
    'boot_id_sha256': hashlib.sha256(boot_id.encode()).hexdigest(),
}}
output.write_text(json.dumps(document, indent=2, sort_keys=True) + '\\n', encoding='utf-8')
""".strip()


CLANG_INSTALL_CODE = f"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

output = Path(sys.argv[1])
environment = os.environ.copy()
environment['DEBIAN_FRONTEND'] = 'noninteractive'
subprocess.run(['apt-get', 'update', '-qq'], check=True, env=environment)
subprocess.run([
    'apt-get', 'install', '-y', '-qq', '--no-install-recommends',
    {f'{CLANG_PACKAGE}={CLANG_PACKAGE_VERSION}'!r},
], check=True, env=environment)
resolved = shutil.which({CLANG_PACKAGE!r})
if resolved is None:
    raise SystemExit('version-locked Clang executable unavailable after install')
executable = Path(resolved).resolve()
package_version = subprocess.run([
    'dpkg-query', '-W', '-f=${{Version}}', {CLANG_PACKAGE!r},
], check=True, capture_output=True, text=True, timeout=20).stdout.strip()
version = subprocess.run([
    str(executable), '--version',
], check=True, capture_output=True, text=True, timeout=20).stdout.strip()
if package_version != {CLANG_PACKAGE_VERSION!r} or 'clang version 14.0.6' not in version:
    raise SystemExit('installed Clang identity differs from frozen compiler contract')
document = {{
    'schema': 'cm-architecture-query-ladder-clang-install/v1',
    'status': 'pass',
    'apt_package': {CLANG_PACKAGE!r},
    'apt_package_version': package_version,
    'compiler_executable': str(executable),
    'compiler_executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
    'compiler_version': version,
}}
output.write_text(json.dumps(document, indent=2, sort_keys=True) + '\\n', encoding='utf-8')
""".strip()


REPLICATION_STAGE = (
    "emit('stage', name='architecture-cross-machine-host-preflight')\n"
    f"    run('architecture-cross-machine-host-preflight', [sys.executable, '-c', {HOST_PREFLIGHT_CODE!r}, "
    "str(OUT/'CROSS-MACHINE-HOST-PREFLIGHT.json'), str(OUT/'RUNTIME.json')], 30)\n"
    "    emit('stage', name='architecture-clang-install')\n"
    f"    run('architecture-clang-install', [sys.executable, '-c', {CLANG_INSTALL_CODE!r}, "
    "str(OUT/'CLANG-INSTALL.json')], 180)\n"
    + "    "
    + retry.RETRY_STAGE.replace(retry.RUN_NAME, RUN_NAME).replace(
        "'--compiler', 'cc'", f"'--compiler', {COMPILER!r}",
    )
)
base.REMOTE_CODE = shared.replace_remote_once(
    base.REMOTE_CODE, retry.RETRY_STAGE, REPLICATION_STAGE,
)

REPLICATION_VALIDATION = (
    retry.RETRY_VALIDATION.replace(retry.RUN_NAME, RUN_NAME)
    + "\n    try:\n"
    "        host_check = json.loads((OUT / 'CROSS-MACHINE-HOST-PREFLIGHT.json').read_text())\n"
    "        clang_check = json.loads((OUT / 'CLANG-INSTALL.json').read_text())\n"
    f"        binding = json.loads((OUT / {RUN_NAME!r} / 'runtime_binding.json').read_text())\n"
    "        validation['cross_machine_replication'] = {\n"
    "            'host_preflight_status': host_check.get('status'),\n"
    "            'prior_cpu_model': host_check.get('prior_cpu_model'),\n"
    "            'current_cpu_model': host_check.get('current_cpu_model'),\n"
    "            'cpu_model_differs': host_check.get('cpu_model_differs'),\n"
    "            'clang_install_status': clang_check.get('status'),\n"
    "            'clang_package_version': clang_check.get('apt_package_version'),\n"
    "            'compiler_executable_sha256': binding.get('compiler_executable_sha256'),\n"
    "            'compiler_version': binding.get('compiler_version')}\n"
    "    except Exception as exc:\n"
    "        validation['cross_machine_replication_error'] = type(exc).__name__ + ': ' + str(exc)"
)
base.REMOTE_CODE = shared.replace_remote_once(
    base.REMOTE_CODE, retry.RETRY_VALIDATION, REPLICATION_VALIDATION,
)

BASE_TRANSPORT_SOURCES = retry.transport_source_identities()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def transport_source_identities() -> dict[str, dict[str, int | str]]:
    rows = dict(BASE_TRANSPORT_SOURCES)
    path = Path(__file__).resolve()
    rows[path.relative_to(ROOT).as_posix()] = {
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }
    return dict(sorted(rows.items()))


class _ReplicationPreflight:
    def __init__(self, delegate):
        self._delegate = delegate

    def __getattr__(self, name):
        return getattr(self._delegate, name)

    def check(self):
        result = self._delegate.check()
        selected = next(
            (
                offer for offer in result.get("offers", [])
                if offer.get("id") == PREFERRED_CPU_FLAVOR and offer.get("eligible") is True
            ),
            None,
        )
        rate = float(selected["rate_usd_per_hour"]) if selected is not None else float("nan")
        projected = (rate + shared.STORAGE_RATE_RESERVE) * shared.CLEANUP_AT / 3600
        maximum_cumulative = PRIOR_ESTIMATED_COST_USD + TOTAL_COST_CAP_USD
        budget = {
            "rate_usd_per_hour": rate,
            "projected_10_minute_cost_usd": projected,
            "phase_cost_cap_usd": TOTAL_COST_CAP_USD,
            "prior_query_ladder_estimated_cost_usd": PRIOR_ESTIMATED_COST_USD,
            "maximum_authorized_cumulative_cost_usd": maximum_cumulative,
            "cumulative_hard_ceiling_usd": CUMULATIVE_HARD_CEILING_USD,
            "ready": bool(
                selected is not None
                and math.isfinite(rate)
                and 0 < rate <= RATE_CAP_USD_PER_HOUR
                and projected <= TOTAL_COST_CAP_USD
                and maximum_cumulative <= CUMULATIVE_HARD_CEILING_USD
            ),
        }
        result["selected_offer"] = selected
        result["budget"] = budget
        result["cross_machine_cpu_constraint"] = {
            "required_cpu_flavor": PREFERRED_CPU_FLAVOR,
            "prior_cpu_flavor": PRIOR_CPU_FLAVOR,
            "prior_cpu_model": PRIOR_CPU_MODEL,
            "same_cpu_model_rejected_before_workload": True,
        }
        result["ready"] = bool(
            selected is not None
            and not any(result.get("inventories", {}).values())
            and result.get("credit_sufficient") is True
            and result.get("spend_limit_sufficient") is True
            and budget.get("ready") is True
        )
        return result


def require_authorization() -> dict:
    authorization = _load(AUTHORIZATION)
    manifest = _load(MANIFEST)
    validation = _load(LOCAL_VALIDATION)
    request = _load(REQUEST)
    contract = _load(CONTRACT)
    expected = {
        "schema": "cm-runpod-architecture-query-ladder-cross-machine-exact-payload-authorization/v1",
        "authorized": True,
        "user_total_ceiling_usd": TOTAL_COST_CAP_USD,
        "controller_total_ceiling_usd": TOTAL_COST_CAP_USD,
        "cumulative_hard_ceiling_usd": CUMULATIVE_HARD_CEILING_USD,
        "prior_estimated_cost_usd": PRIOR_ESTIMATED_COST_USD,
        "one_create": True,
        "no_replacement": True,
        "source_files": manifest["file_count"],
        "source_bytes": manifest["bytes"],
        "planned_rows": 27_648,
        "query_rows": {"1": 6_912, "4": 6_912, "16": 6_912, "64": 6_912},
        "https_ports": ["8080/http"],
        "vcpu_count": 2,
        "minimum_ram_gb": 4,
        "container_disk_gb": 12,
        "pod_volume_gb": 0,
        "network_volume": False,
        "cleanup_seconds": 600,
        "reconciliation_seconds": 720,
        "rate_cap_usd_per_hour": RATE_CAP_USD_PER_HOUR,
        "total_cost_cap_usd": TOTAL_COST_CAP_USD,
        "same_pod_payload_attempt_limit": 6,
        "health_checks_before_upload": 2,
        "result_cap_bytes": 48 << 20,
        "preferred_cpu_flavor": PREFERRED_CPU_FLAVOR,
        "prior_cpu_flavor": PRIOR_CPU_FLAVOR,
        "prior_pod_id": PRIOR_POD_ID,
        "prior_cpu_model": PRIOR_CPU_MODEL,
        "reject_same_cpu_model": True,
        "compiler": COMPILER,
        "clang_package": CLANG_PACKAGE,
        "clang_package_version": CLANG_PACKAGE_VERSION,
        "image": controller.IMAGE,
        "local_isolated_validation": "pass",
        "local_validation_pythonpath_injected": False,
        "isolated_memory_method": "isolated_fork_child_wait4_ru_maxrss/v1",
        "isolated_cleanup_method": "cache_clear_then_isolated_child_exit",
        "credentials_recorded_or_uploaded": False,
        "prior_authorization_reused": False,
        "training": False,
        "selector_fit": False,
        "website_update": False,
        "production_write": False,
    }
    if any(authorization.get(key) != value for key, value in expected.items()):
        raise RuntimeError("cross-machine query-ladder authorization scope mismatch")
    hashes = {
        "upload_manifest_sha256": _sha256(MANIFEST),
        "protocol_sha256": _sha256(PROTOCOL),
        "execution_contract_sha256": _sha256(CONTRACT),
        "local_validation_sha256": _sha256(LOCAL_VALIDATION),
        "freeze_sha256": _sha256(FREEZE),
        "authorization_request_sha256": _sha256(REQUEST),
        "controller_sha256": _sha256(Path(__file__)),
        "prior_run_sha256": _sha256(PRIOR_RUN),
        "prior_results_sha256": _sha256(PRIOR_RESULTS),
        "prior_verification_sha256": _sha256(PRIOR_VERIFICATION),
        "prior_runtime_sha256": _sha256(PRIOR_RUNTIME),
        "prior_binding_sha256": _sha256(PRIOR_BINDING),
        "prior_post_inventory_sha256": _sha256(PRIOR_POST_INVENTORY),
    }
    if (
        any(authorization.get(key) != value for key, value in hashes.items())
        or any(
            request.get(key) != value
            for key, value in hashes.items()
            if key != "authorization_request_sha256"
        )
        or authorization.get("transport_sources") != transport_source_identities()
        or request.get("transport_sources") != transport_source_identities()
        or validation.get("status") != "pass"
        or validation.get("manifest_sha256") != _sha256(MANIFEST)
        or validation.get("timing_evidence_produced") is not False
        or validation.get("memory_evidence_produced") is not False
        or validation.get("decision_bearing_result_produced") is not False
        or contract.get("host_separation", {}).get("reject_prior_cpu_model_before_workload") is not True
    ):
        raise RuntimeError("cross-machine query-ladder authorization artifact mismatch")
    prior_run = _load(PRIOR_RUN)
    prior_verification = _load(PRIOR_VERIFICATION)
    prior_runtime = _load(PRIOR_RUNTIME)
    prior_binding = _load(PRIOR_BINDING)
    prior_inventory = _load(PRIOR_POST_INVENTORY)
    if (
        prior_run.get("status") != "complete"
        or prior_run.get("pod_id") != PRIOR_POD_ID
        or prior_run.get("selected_cpu") != PRIOR_CPU_FLAVOR
        or prior_run.get("cleanup", {}).get("owned_pod_absent") is not True
        or prior_verification.get("status") != "verified_complete"
        or prior_verification.get("rows_checked") != 27_648
        or prior_runtime.get("cpu_model") != PRIOR_CPU_MODEL
        or prior_binding.get("compiler_executable_sha256") != PRIOR_COMPILER_SHA256
        or prior_inventory.get("owned_pod_absent") is not True
        or prior_inventory.get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("prior query-ladder result is not closed and bound")
    return authorization


_original_validate_pod = shared.validate_pod


def validate_replication_pod(pod, state, offer):
    result = _original_validate_pod(pod, state, offer)
    machine_id = pod.get("machineId")
    if (
        offer.get("id") != PREFERRED_CPU_FLAVOR
        or pod.get("cpuFlavorId") != PREFERRED_CPU_FLAVOR
        or pod.get("id") == PRIOR_POD_ID
        or not isinstance(machine_id, str)
        or not machine_id
        or len(machine_id) > 200
        or any(character.isspace() for character in machine_id)
    ):
        raise RuntimeError("created Pod lacks the frozen independent placement identity")
    result.update({
        "machine_id": machine_id,
        "prior_pod_id": PRIOR_POD_ID,
        "pod_id_differs": True,
        "prior_cpu_flavor": PRIOR_CPU_FLAVOR,
        "cpu_flavor_differs": True,
    })
    return result


_original_save_evidence = controller.save_evidence


def save_replication_evidence(log: str) -> dict:
    result = _original_save_evidence(log)
    evidence = OUT / "evidence/run-output"
    host_check = _load(evidence / "CROSS-MACHINE-HOST-PREFLIGHT.json")
    clang_check = _load(evidence / "CLANG-INSTALL.json")
    runtime = _load(evidence / "RUNTIME.json")
    binding = _load(evidence / RUN_NAME / "runtime_binding.json")
    validation = _load(evidence / "REMOTE-VALIDATION.json").get(
        "cross_machine_replication", {},
    )
    if (
        host_check.get("status") != "pass"
        or host_check.get("prior_cpu_model") != PRIOR_CPU_MODEL
        or not isinstance(host_check.get("current_cpu_model"), str)
        or not host_check.get("current_cpu_model")
        or host_check.get("current_cpu_model") == PRIOR_CPU_MODEL
        or host_check.get("cpu_model_differs") is not True
        or runtime.get("cpu_model") != host_check.get("current_cpu_model")
        or runtime.get("runpod_pod_id") != host_check.get("current_pod_id")
        or runtime.get("runpod_pod_id") == PRIOR_POD_ID
        or clang_check.get("status") != "pass"
        or clang_check.get("apt_package") != CLANG_PACKAGE
        or clang_check.get("apt_package_version") != CLANG_PACKAGE_VERSION
        or binding.get("compiler_executable") != clang_check.get("compiler_executable")
        or binding.get("compiler_executable_sha256") != clang_check.get(
            "compiler_executable_sha256"
        )
        or binding.get("compiler_executable_sha256") == PRIOR_COMPILER_SHA256
        or binding.get("compiler_version") != clang_check.get("compiler_version")
        or "clang version 14.0.6" not in binding.get("compiler_version", "")
        or validation.get("host_preflight_status") != "pass"
        or validation.get("clang_install_status") != "pass"
        or validation.get("compiler_executable_sha256") != binding.get(
            "compiler_executable_sha256"
        )
    ):
        raise RuntimeError("retrieved replication evidence failed host/compiler checks")
    result["cross_machine_compiler_replication"] = {
        "prior_pod_id": PRIOR_POD_ID,
        "current_pod_id": runtime["runpod_pod_id"],
        "prior_cpu_flavor": PRIOR_CPU_FLAVOR,
        "current_cpu_flavor": PREFERRED_CPU_FLAVOR,
        "prior_cpu_model": PRIOR_CPU_MODEL,
        "current_cpu_model": runtime["cpu_model"],
        "cpu_model_differs": True,
        "prior_compiler_executable_sha256": PRIOR_COMPILER_SHA256,
        "current_compiler_executable_sha256": binding["compiler_executable_sha256"],
        "compiler_family_differs": True,
        "replication_analysis_permitted": True,
        "public_update_permitted": False,
    }
    return result


controller.OUT = OUT
controller.MANIFEST = MANIFEST
controller.AUTHORIZATION = AUTHORIZATION
controller.PROTOCOL = PROTOCOL
controller.CONTRACT = CONTRACT
controller.LOCAL_VALIDATION = LOCAL_VALIDATION
controller.REQUEST = REQUEST
controller.FREEZE = FREEZE
controller.RUN_NAME = RUN_NAME
controller.preflight = _ReplicationPreflight(controller.preflight)
controller.shared.CAMPAIGN_CAP = TOTAL_COST_CAP_USD
controller.shared.RATE_CAP = RATE_CAP_USD_PER_HOUR
controller.shared.validate_pod = validate_replication_pod
controller.transport_source_identities = transport_source_identities
controller.require_authorization = require_authorization
controller.save_evidence = save_replication_evidence
controller.__file__ = str(Path(__file__).resolve())
controller.configure_transport()


def main() -> int:
    return controller.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}), flush=True)
        raise SystemExit(2)
