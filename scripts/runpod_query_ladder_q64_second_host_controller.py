"""Run the authorized sealed q64 handoff once on a distinct RunPod CPU machine."""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shlex
import subprocess
import sys
import time
import uuid
import zipfile
import zlib


ROOT = Path(__file__).resolve().parents[1]
PARENT_CONTROLLER = ROOT / "scripts/runpod_architecture_query_ladder_controller.py"
spec = importlib.util.spec_from_file_location("q64_runpod_transport", PARENT_CONTROLLER)
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)
shared, base, preflight = parent.shared, parent.base, parent.preflight

RUN_DIR = (
    ROOT
    / "docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004"
)
OUT = RUN_DIR / "runpod-second-host-physical-002-002"
PRIOR_PRELAUNCH_FAILURE = (
    RUN_DIR / "runpod-second-host-physical-002-001/PRELAUNCH_FAILURE.json"
)
BUNDLE = RUN_DIR / "SECOND_HOST_SOURCE_BUNDLE_V2.zip"
HANDOFF = RUN_DIR / "SECOND_HOST_HANDOFF.json"
AUTHORIZATION = RUN_DIR / "RUNPOD_SECOND_HOST_AUTHORIZATION_20260910.json"
BOOTSTRAP = ROOT / "scripts/runpod_query_ladder_q64_bootstrap.py"
CHILD_FREEZE = RUN_DIR / "CHILD_FREEZE.json"
FIRST_PREFLIGHT = RUN_DIR / "windows-physical-001/HOST_PREFLIGHT.json"
REPLICATION_ID = "physical-002"

IMAGE_TAG = "python:3.13.15-bookworm"
IMAGE_AMD64_DIGEST = (
    "sha256:a53008522631dbcb063c4d5982aa91a00e86e51d90bbcf3513313f1a5c163af8"
)
IMAGE = f"{IMAGE_TAG}@{IMAGE_AMD64_DIGEST}"
CPU_FLAVOR = "cpu3c"
VCPU_COUNT = 2
MINIMUM_RAM_GB = 4
CONTAINER_DISK_GB = 12
RATE_CAP_USD_PER_HOUR = 0.06
STORAGE_RATE_RESERVE = 0.01
HARD_LIFETIME_SECONDS = 18_000
RECONCILIATION_SECONDS = 18_300
TOTAL_COST_CAP_USD = 0.36
RESULT_CAP_BYTES = 32 << 20
EXPECTED_BUNDLE_BYTES = 1_755_915
EXPECTED_BUNDLE_SHA256 = (
    "6baf8e95062b9b80f2dee4a5c98e16983ea0dfb2c111e681cc672e774a45671d"
)
EXPECTED_CHILD_FREEZE_SHA256 = (
    "87ca40e32b0ee33e73e557d41d7bbc01ca1a6a1940669a54470d2f8e52a18a6f"
)
FIRST_PHYSICAL_MACHINE_SHA256 = (
    "511b05dff7d58f683f4f188b4aded5bff2ad38857546ff8d238596deb34e9191"
)
COMMANDS = [
    "python3 scripts/cm_query_ladder_q64_execution.py prepare-host --run-dir "
    "docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004 "
    "--replication-id physical-002 --compiler cc",
    "python3 scripts/cm_query_ladder_q64_execution.py run-host --run-dir "
    "docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004 "
    "--replication-id physical-002 --max-seconds 14400",
    "python3 scripts/crse_verify_query_ladder_q64_execution.py --run-dir "
    "docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004 "
    "--replication-id physical-002",
]


REMOTE_CODE = r'''
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

ROOT = Path('/workspace/cm-q64-second-host')
OUT = Path('/workspace/cm-q64-transport-output')
RUN = ROOT / 'docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004'
HOST = RUN / 'physical-002'
FIRST_MACHINE_SHA256 = '511b05dff7d58f683f4f188b4aded5bff2ad38857546ff8d238596deb34e9191'
BUNDLE_SHA256 = '6baf8e95062b9b80f2dee4a5c98e16983ea0dfb2c111e681cc672e774a45671d'
NUMPY_URL = ('https://files.pythonhosted.org/packages/1d/0f/'
             '571b2c7a3833ae419fe69ff7b479a78d313581785203cc70a8db90121b9a/'
             'numpy-2.3.2-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl')
NUMPY_SHA256 = '938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f'
CAP = 32 << 20
COMMANDS = [
    ['python3', 'scripts/cm_query_ladder_q64_execution.py', 'prepare-host',
     '--run-dir', 'docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004',
     '--replication-id', 'physical-002', '--compiler', 'cc'],
    ['python3', 'scripts/cm_query_ladder_q64_execution.py', 'run-host',
     '--run-dir', 'docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004',
     '--replication-id', 'physical-002', '--max-seconds', '14400'],
    ['python3', 'scripts/crse_verify_query_ladder_q64_execution.py',
     '--run-dir', 'docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004',
     '--replication-id', 'physical-002'],
]

def emit(kind, **fields):
    print('CM_EVENT ' + json.dumps({'kind': kind, **fields}, sort_keys=True), flush=True)

def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')

def run(name, command, timeout):
    emit('stage', name=name)
    stdout = OUT / (name + '.stdout.txt')
    stderr = OUT / (name + '.stderr.txt')
    started = time.monotonic()
    with stdout.open('xb') as out, stderr.open('xb') as err:
        process = subprocess.Popen(
            command, cwd=ROOT, stdout=out, stderr=err, start_new_session=True,
            env={**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
                 'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'},
        )
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise RuntimeError(name + ' timed out')
    record = {
        'name': name, 'command': command, 'returncode': returncode,
        'wall_seconds': time.monotonic() - started,
        'stdout_sha256': digest(stdout), 'stderr_sha256': digest(stderr),
    }
    if returncode:
        record['stderr_tail'] = stderr.read_text(errors='replace')[-3000:]
    write_json(OUT / (name + '.json'), record)
    if returncode:
        raise RuntimeError(name + ' failed with exit code ' + str(returncode))
    return record

def command_output(command):
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=20)
        return {'command': command, 'returncode': completed.returncode,
                'stdout': completed.stdout.strip(), 'stderr': completed.stderr.strip()}
    except Exception as exc:
        return {'command': command, 'error_type': type(exc).__name__}

def host_preflight():
    cpu_text = Path('/proc/cpuinfo').read_text(encoding='utf-8', errors='replace')
    cpu_model = next((line.partition(':')[2].strip() for line in cpu_text.splitlines()
                      if line.startswith('model name')), None)
    flags = next((line.partition(':')[2].strip().split() for line in cpu_text.splitlines()
                  if line.startswith('flags')), [])
    dmi = {}
    for name in ('sys_vendor', 'product_name', 'product_version', 'board_vendor'):
        path = Path('/sys/class/dmi/id') / name
        dmi[name] = path.read_text(encoding='utf-8', errors='replace').strip() if path.exists() else None
    vm_probe = command_output(['systemd-detect-virt', '--vm']) if shutil.which('systemd-detect-virt') else {
        'command': ['systemd-detect-virt', '--vm'], 'unavailable': True}
    container_probe = command_output(['systemd-detect-virt', '--container']) if shutil.which('systemd-detect-virt') else {
        'command': ['systemd-detect-virt', '--container'], 'unavailable': True}
    joined = ' '.join(value or '' for value in dmi.values()).lower()
    vm_markers = ('kvm', 'qemu', 'vmware', 'virtual machine', 'virtualbox',
                  'amazon ec2', 'google compute engine', 'openstack', 'xen')
    dmi_vm_markers = sorted(marker for marker in vm_markers if marker in joined)
    vm_probe_detected = vm_probe.get('returncode') == 0 and vm_probe.get('stdout') not in ('', 'none')
    hypervisor_flag = 'hypervisor' in flags
    boot = Path('/proc/sys/kernel/random/boot_id').read_text(encoding='utf-8').strip()
    document = {
        'schema': 'crse-query-ladder-q64-runpod-host-placement-preflight/v1',
        'status': 'pass' if not (vm_probe_detected or hypervisor_flag or dmi_vm_markers) else 'reject_vm',
        'runpod_pod_id': os.environ.get('RUNPOD_POD_ID'),
        'runpod_machine_id': os.environ.get('CM_RUNPOD_MACHINE_ID'),
        'secure_cloud_required_by_controller': True,
        'cpu_model': cpu_model,
        'logical_cpu_count': os.cpu_count(),
        'dmi': dmi,
        'vm_probe': vm_probe,
        'container_probe': container_probe,
        'container_isolation_is_not_counted_as_a_vm': True,
        'cpu_hypervisor_flag_present': hypervisor_flag,
        'dmi_vm_markers': dmi_vm_markers,
        'boot_id_sha256': hashlib.sha256(boot.encode()).hexdigest(),
    }
    if not document['runpod_pod_id'] or not document['runpod_machine_id'] or not cpu_model or not boot:
        document['status'] = 'incomplete_identity'
    write_json(OUT / 'RUNPOD_HOST_PLACEMENT_PREFLIGHT.json', document)
    if document['status'] != 'pass':
        raise RuntimeError('RunPod placement is not a verified non-VM physical host container')
    return document

def install_numpy():
    with tempfile.TemporaryDirectory(prefix='cm-q64-numpy-') as temporary:
        wheel = Path(temporary) / NUMPY_URL.rsplit('/', 1)[-1]
        request = urllib.request.Request(NUMPY_URL, headers={'User-Agent': 'cm-q64-second-host/1'})
        with urllib.request.urlopen(request, timeout=90) as response:
            data = response.read(32 << 20)
        if hashlib.sha256(data).hexdigest() != NUMPY_SHA256:
            raise RuntimeError('NumPy wheel identity mismatch')
        wheel.write_bytes(data)
        run('numpy-install', [sys.executable, '-m', 'pip', 'install', '--no-deps', str(wheel)], 180)
    import numpy
    if numpy.__version__ != '2.3.2':
        raise RuntimeError('NumPy version mismatch after installation')
    compiler = shutil.which('cc')
    if compiler is None:
        raise RuntimeError('frozen cc compiler command is unavailable')
    compiler_check = command_output([compiler, '--version'])
    if compiler_check.get('returncode') != 0 or not compiler_check.get('stdout'):
        raise RuntimeError('compiler identity unavailable')
    write_json(OUT / 'MEASUREMENT_ENVIRONMENT.json', {
        'schema': 'crse-query-ladder-q64-runpod-environment/v1',
        'python': sys.version, 'python_executable_sha256': digest(Path(sys.executable)),
        'numpy_version': numpy.__version__, 'numpy_wheel_sha256': NUMPY_SHA256,
        'compiler_path': str(Path(compiler).resolve()),
        'compiler_sha256': digest(Path(compiler).resolve()),
        'compiler_version': compiler_check['stdout'],
        'image_tag': os.environ.get('CM_IMAGE_TAG'),
        'image_digest': os.environ.get('CM_IMAGE_DIGEST'),
    })

def extract_bundle():
    bundle = Path(os.environ['CM_BUNDLE_PATH'])
    if digest(bundle) != BUNDLE_SHA256:
        raise RuntimeError('sealed V2 bundle identity mismatch')
    ROOT.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError('duplicate source bundle member')
        for info in archive.infolist():
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or '..' in pure.parts or info.is_dir():
                raise RuntimeError('unsafe source bundle member')
            target = ROOT / pure
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(archive.read(info))

def archive_evidence(status, error):
    write_json(OUT / 'REMOTE_RESULT.json', {
        'schema': 'crse-query-ladder-q64-runpod-remote-result/v1',
        'status': status, 'error': error,
        'exact_handoff_commands': [' '.join(command) for command in COMMANDS],
        'commands_completed': sum((OUT / (name + '.json')).is_file()
                                  for name in ('prepare-host', 'run-host', 'independent-verify')),
    })
    result = io.BytesIO()
    total = 0
    with zipfile.ZipFile(result, 'w', zipfile.ZIP_DEFLATED) as archive:
        groups = [(HOST, PurePosixPath('physical-002')), (OUT, PurePosixPath('transport'))]
        for source, prefix in groups:
            if not source.exists():
                continue
            for path in sorted(source.rglob('*')):
                if not path.is_file():
                    continue
                data = path.read_bytes()
                total += len(data)
                if total > CAP:
                    raise RuntimeError('uncompressed evidence exceeds cap')
                archive.writestr(str(prefix / PurePosixPath(path.relative_to(source).as_posix())), data)
    data = result.getvalue()
    if len(data) > CAP:
        raise RuntimeError('compressed evidence exceeds cap')
    encoded = base64.b64encode(data).decode('ascii')
    chunk = 3072
    emit('evidence_start', bytes=len(data), uncompressed_bytes=total,
         sha256=hashlib.sha256(data).hexdigest(), chunks=(len(encoded) + chunk - 1) // chunk)
    for index in range(0, len(encoded), chunk):
        print('CM_EVIDENCE %06d %s' % (index // chunk, encoded[index:index + chunk]), flush=True)
    emit('evidence_end', sha256=hashlib.sha256(data).hexdigest())

OUT.mkdir(parents=True, exist_ok=False)
status = 'failed'
error = None
try:
    emit('stage', name='sealed-bundle-extraction')
    extract_bundle()
    emit('stage', name='non-vm-host-preflight')
    placement = host_preflight()
    emit('stage', name='measurement-environment')
    install_numpy()
    run('prepare-host', COMMANDS[0], 900)
    host_preflight_document = json.loads((HOST / 'HOST_PREFLIGHT.json').read_text(encoding='utf-8'))
    if host_preflight_document.get('physical_machine_sha256') == FIRST_MACHINE_SHA256:
        raise RuntimeError('second-host physical identity equals first host')
    write_json(OUT / 'SECOND_HOST_IDENTITY_GATE.json', {
        'schema': 'crse-query-ladder-q64-second-host-identity-gate/v1',
        'status': 'pass',
        'first_physical_machine_sha256': FIRST_MACHINE_SHA256,
        'second_physical_machine_sha256': host_preflight_document.get('physical_machine_sha256'),
        'identities_differ': True,
        'runpod_machine_id': placement['runpod_machine_id'],
    })
    run('run-host', COMMANDS[1], 14_700)
    run('independent-verify', COMMANDS[2], 900)
    status = 'complete'
except Exception as exc:
    error = type(exc).__name__ + ': ' + str(exc)
    emit('failure', error=error)
finally:
    try:
        archive_evidence(status, error)
    except Exception as exc:
        emit('evidence_failure', error=type(exc).__name__ + ': ' + str(exc))
    emit('done', status=status)
'''


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def configure_transport() -> None:
    base.IMAGE_TAG = IMAGE_TAG
    base.IMAGE_AMD64_DIGEST = IMAGE_AMD64_DIGEST
    base.IMAGE = IMAGE
    shared.OUT = OUT
    base.OUT = OUT
    shared.BOOTSTRAP_PATH = BOOTSTRAP
    shared.CAP = RESULT_CAP_BYTES
    shared.CLEANUP_AT = HARD_LIFETIME_SECONDS
    shared.HORIZON = RECONCILIATION_SECONDS
    shared.RATE_CAP = RATE_CAP_USD_PER_HOUR
    shared.PHASE_CAP = TOTAL_COST_CAP_USD
    shared.CAMPAIGN_CAP = TOTAL_COST_CAP_USD
    shared.STORAGE_RATE_RESERVE = STORAGE_RATE_RESERVE
    for name, filename in {
        "STATE": "controller-state.json",
        "IDENTITY": "POD-IDENTITY.json",
        "READY": "watchdog-ready.json",
        "STATE_ACK": "watchdog-state-ack.json",
        "DONE": "watchdog-done.json",
        "ABORT": "abort-requested.json",
    }.items():
        setattr(shared, name, OUT / filename)


configure_transport()


def require_authorization() -> dict:
    authorization = load(AUTHORIZATION)
    handoff = load(HANDOFF)
    first = load(FIRST_PREFLIGHT)
    expected = {
        "schema": "crse-query-ladder-q64-runpod-second-host-authorization/v1",
        "authorized": True,
        "authorization_scope": "one_distinct_non_vm_physical_runpod_machine_for_physical_002",
        "one_create": True,
        "no_replacement": True,
        "source_export_to_runpod_authorized": True,
        "controller_battery_launch_authorized": True,
        "replication_id": REPLICATION_ID,
        "exact_commands": COMMANDS,
        "source_bundle_bytes": EXPECTED_BUNDLE_BYTES,
        "source_bundle_sha256": EXPECTED_BUNDLE_SHA256,
        "child_freeze_file_sha256": EXPECTED_CHILD_FREEZE_SHA256,
        "first_physical_machine_sha256": FIRST_PHYSICAL_MACHINE_SHA256,
        "image": IMAGE,
        "cpu_flavor": CPU_FLAVOR,
        "vcpu_count": VCPU_COUNT,
        "minimum_ram_gb": MINIMUM_RAM_GB,
        "container_disk_gb": CONTAINER_DISK_GB,
        "pod_volume_gb": 0,
        "network_volume": False,
        "https_ports": ["8080/http"],
        "hard_lifetime_seconds": HARD_LIFETIME_SECONDS,
        "reconciliation_seconds": RECONCILIATION_SECONDS,
        "rate_cap_usd_per_hour": RATE_CAP_USD_PER_HOUR,
        "total_cost_cap_usd": TOTAL_COST_CAP_USD,
        "vm_rejected_before_handoff": True,
        "secure_cloud_required": True,
        "training": False,
        "selector_fit": False,
        "website_update": False,
        "production_write": False,
        "credentials_recorded_or_uploaded": False,
        "controller_sha256": sha256(Path(__file__).resolve()),
        "bootstrap_sha256": sha256(BOOTSTRAP),
        "handoff_sha256": sha256(HANDOFF),
        "prior_prelaunch_failure_sha256": sha256(PRIOR_PRELAUNCH_FAILURE),
    }
    if any(authorization.get(key) != value for key, value in expected.items()):
        raise RuntimeError("RunPod second-host authorization record mismatch")
    if (
        BUNDLE.stat().st_size != EXPECTED_BUNDLE_BYTES
        or sha256(BUNDLE) != EXPECTED_BUNDLE_SHA256
        or sha256(CHILD_FREEZE) != EXPECTED_CHILD_FREEZE_SHA256
        or first.get("physical_machine_sha256") != FIRST_PHYSICAL_MACHINE_SHA256
        or handoff.get("current_package", {}).get("sha256") != EXPECTED_BUNDLE_SHA256
        or handoff.get("commands", {}).get("linux_or_macos") != COMMANDS
        or load(PRIOR_PRELAUNCH_FAILURE).get("create_request_issued") is not False
        or (RUN_DIR / REPLICATION_ID).exists()
    ):
        raise RuntimeError("sealed q64 handoff precondition mismatch")
    return authorization


@contextmanager
def authorized_host_awake_guard(role: str):
    """Prevent idle sleep with the user's explicit battery-launch override."""
    if os.name != "nt":
        raise RuntimeError("controller host wake guard is validated for Windows only")
    authorization = load(AUTHORIZATION)
    if authorization.get("controller_battery_launch_authorized") is not True:
        raise RuntimeError("battery launch has not been explicitly authorized")
    import ctypes
    from ctypes import wintypes

    class PowerStatus(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", wintypes.BYTE),
            ("BatteryFlag", wintypes.BYTE),
            ("BatteryLifePercent", wintypes.BYTE),
            ("SystemStatusFlag", wintypes.BYTE),
            ("BatteryLifeTime", wintypes.DWORD),
            ("BatteryFullLifeTime", wintypes.DWORD),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    power = PowerStatus()
    if not kernel.GetSystemPowerStatus(ctypes.byref(power)):
        raise RuntimeError("controller host power status is unavailable")
    set_state = kernel.SetThreadExecutionState
    set_state.argtypes = [wintypes.DWORD]
    set_state.restype = wintypes.DWORD
    requested = 0x80000001
    if not set_state(requested):
        raise RuntimeError("failed to establish temporary idle-sleep prevention")
    try:
        shared.write(OUT / ("HOST-AWAKE-" + role + ".json"), {
            "started_utc": preflight.utc_now(),
            "pid": os.getpid(),
            "ac_line_status": int(power.ACLineStatus),
            "battery_flag": int(power.BatteryFlag),
            "battery_life_percent": int(power.BatteryLifePercent),
            "battery_launch_explicitly_authorized": True,
            "requested_execution_state": requested,
            "persistent_power_settings_changed": False,
            "limitation": "does not prevent lid-close, explicit sleep, power loss, or network loss",
        })
        yield
    finally:
        released = bool(set_state(0x80000000))
        shared.write(OUT / ("HOST-AWAKE-RELEASED-" + role + ".json"), {
            "released_utc": preflight.utc_now(), "released": released,
            "pid": os.getpid(),
        })


def arm_watchdog():
    with (OUT / "watchdog.log").open("xb") as stream:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0
        )
        process = subprocess.Popen(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--watchdog"],
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            close_fds=True,
        )
    for _ in range(200):
        if shared.READY.exists():
            ready = load(shared.READY)
            if not ready.get("network_probe_passed") or any(ready["startup_inventories"].values()):
                raise RuntimeError("RunPod watchdog zero-pod readiness failed")
            shared.write(OUT / "WATCHDOG-PROCESS-BINDING.json", shared.bind_watchdog(process, ready))
            return process
        if process.poll() is not None:
            raise RuntimeError("RunPod watchdog exited before readiness")
        time.sleep(0.2)
    raise RuntimeError("RunPod watchdog failed to arm")


def create_payload(name: str, offer: dict, token: str, created: float) -> dict:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    encoded_remote = base64.b64encode(REMOTE_CODE.encode("utf-8")).decode("ascii")
    marker = '"__CM_REMOTE_CODE_B64__"'
    if source.count(marker) != 1:
        raise RuntimeError("bootstrap remote-code marker mismatch")
    source = source.replace(marker, repr(encoded_remote))
    compressed = base64.b64encode(zlib.compress(source.encode("utf-8"), 9)).decode("ascii")
    code = "import base64,zlib;exec(zlib.decompress(base64.b64decode(" + repr(compressed) + ")))"
    start = "python -u -c " + shlex.quote(code)
    return {
        "name": name,
        "computeType": "CPU",
        "cloudType": "SECURE",
        "imageName": IMAGE,
        "cpuFlavorIds": [offer["id"]],
        "vcpuCount": VCPU_COUNT,
        "containerDiskInGb": CONTAINER_DISK_GB,
        "volumeInGb": 0,
        "volumeMountPath": "/workspace",
        "ports": ["8080/http"],
        "env": {
            "CM_BOOTSTRAP_TOKEN": token,
            "CM_PAYLOAD_SHA256": EXPECTED_BUNDLE_SHA256,
            "CM_PAYLOAD_BYTES": str(EXPECTED_BUNDLE_BYTES),
            "CM_HARD_DEADLINE": str(created + HARD_LIFETIME_SECONDS),
            "CM_IMAGE_TAG": IMAGE_TAG,
            "CM_IMAGE_DIGEST": IMAGE_AMD64_DIGEST,
        },
        "dockerEntrypoint": ["sh", "-c"],
        "dockerStartCmd": [start],
    }


def execute_remote(
    pod_id: str, machine_id: str, token: str, created: float, record: dict
) -> str:
    endpoint = f"https://{pod_id}-8080.proxy.runpod.net"
    raw = BUNDLE.read_bytes()
    with shared.requests.Session() as proxy:
        proxy.trust_env = False
        proxy.headers["X-CM-Token"] = token
        proxy.headers["X-CM-Machine-ID"] = machine_id
        proxy.headers["Content-Type"] = "application/octet-stream"
        consecutive_health = 0
        while time.time() < created + 300:
            try:
                health = json.loads(
                    shared.proxy_request(proxy, "GET", endpoint + "/health", timeout=5)
                )
                if health.get("service") == "cm-q64-second-host" and health.get("ready") is True:
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
            raise RuntimeError("RunPod q64 bootstrap did not remain ready")
        record["bootstrap_ready_utc"] = preflight.utc_now()
        record["health_checks_before_upload"] = consecutive_health
        accepted = json.loads(
            shared.proxy_request(
                proxy, "POST", endpoint + "/payload", data=raw,
                cap=16_384, timeout=60,
            )
        )
        if accepted.get("accepted_sha256") != EXPECTED_BUNDLE_SHA256:
            raise RuntimeError("RunPod q64 upload acknowledgement mismatch")
        record["uploaded_transport_bytes"] = len(raw)
        shared.proxy_request(proxy, "POST", endpoint + "/run", data=b"", timeout=10)
        record["worker_started_utc"] = preflight.utc_now()
        observed = None
        while time.time() < created + HARD_LIFETIME_SECONDS - 60:
            try:
                progress = json.loads(
                    shared.proxy_request(proxy, "GET", endpoint + "/progress", timeout=5)
                )
            except (shared.requests.RequestException, RuntimeError, ValueError):
                time.sleep(3)
                continue
            signature = (progress.get("stage"), progress.get("done"), progress.get("error"))
            if signature != observed:
                shared.append(OUT / "progress.jsonl", {"checked_utc": preflight.utc_now(), **progress})
                print(json.dumps({
                    "stage": progress.get("stage"), "done": progress.get("done"),
                    "error": progress.get("error"),
                }), flush=True)
                observed = signature
            if progress.get("done"):
                record["remote_progress"] = progress
                return shared.proxy_request(
                    proxy, "GET", endpoint + "/results",
                    cap=RESULT_CAP_BYTES, timeout=120,
                ).decode("utf-8")
            time.sleep(3)
    raise RuntimeError("RunPod q64 remote worker deadline exceeded")


def save_evidence(log: str) -> dict:
    lines = log.splitlines()
    starts = [
        json.loads(line[9:]) for line in lines
        if line.startswith("CM_EVENT ") and '"kind": "evidence_start"' in line
    ]
    ends = [
        json.loads(line[9:]) for line in lines
        if line.startswith("CM_EVENT ") and '"kind": "evidence_end"' in line
    ]
    chunks = {}
    for line in lines:
        if line.startswith("CM_EVIDENCE "):
            _, number, data = line.split(" ", 2)
            chunks[int(number)] = data
    if not starts or not ends:
        raise RuntimeError("RunPod q64 complete evidence markers absent")
    start = starts[-1]
    if set(chunks) != set(range(start["chunks"])):
        raise RuntimeError("RunPod q64 evidence chunks incomplete")
    data = base64.b64decode(
        "".join(chunks[index] for index in range(start["chunks"])), validate=True
    )
    if (
        len(data) != start["bytes"]
        or len(data) > RESULT_CAP_BYTES
        or hashlib.sha256(data).hexdigest() != start["sha256"]
        or ends[-1].get("sha256") != start["sha256"]
    ):
        raise RuntimeError("RunPod q64 evidence archive integrity failure")
    with (OUT / "evidence.zip").open("xb") as stream:
        stream.write(data)
    evidence = OUT / "evidence"
    evidence.mkdir(exist_ok=False)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if sum(info.file_size for info in infos) + len(data) > RESULT_CAP_BYTES:
            raise RuntimeError("RunPod q64 collected evidence exceeds cap")
        for info in infos:
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or ".." in pure.parts or info.is_dir():
                raise RuntimeError("unsafe RunPod q64 evidence path")
            target = evidence / pure
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(archive.read(info))
    (OUT / "container.log").write_text(
        "\n".join(line for line in lines if not line.startswith("CM_EVIDENCE ")) + "\n",
        encoding="utf-8",
    )
    remote = load(evidence / "transport/REMOTE_RESULT.json")
    source_host = evidence / REPLICATION_ID
    if source_host.exists():
        target_host = RUN_DIR / REPLICATION_ID
        target_host.mkdir(exist_ok=False)
        for source in sorted(source_host.rglob("*")):
            if not source.is_file():
                continue
            target = target_host / source.relative_to(source_host)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(source.read_bytes())
    result = {
        "archive_sha256": start["sha256"],
        "archive_bytes": len(data),
        "uncompressed_bytes": start["uncompressed_bytes"],
        "remote_status": remote.get("status"),
        "remote_error": remote.get("error"),
        "host_directory_retrieved": source_host.exists(),
    }
    if remote.get("status") == "complete":
        host = RUN_DIR / REPLICATION_ID
        verification = load(host / "INDEPENDENT_VERIFICATION.json")
        host_result = load(host / "RESULT.json")
        host_preflight = load(host / "HOST_PREFLIGHT.json")
        placement = load(evidence / "transport/RUNPOD_HOST_PLACEMENT_PREFLIGHT.json")
        gate = load(evidence / "transport/SECOND_HOST_IDENTITY_GATE.json")
        if (
            verification.get("status") != "verified_complete"
            or verification.get("rows_checked") != 9_216
            or any(verification.get(key) != 0 for key in (
                "semantic_mismatches", "schedule_mismatches",
                "source_or_artifact_mismatches", "charged_cost_mismatches",
            ))
            or host_result.get("status") != "complete"
            or host_result.get("completed_rows") != 9_216
            or host_result.get("counts") != {
                "ok": 9_216, "failed": 0, "timeout": 0, "refused": 0,
            }
            or host_preflight.get("physical_machine_sha256") == FIRST_PHYSICAL_MACHINE_SHA256
            or placement.get("status") != "pass"
            or placement.get("runpod_machine_id") != gate.get("runpod_machine_id")
            or gate.get("identities_differ") is not True
        ):
            raise RuntimeError("retrieved RunPod q64 host failed frozen checks")
        result.update({
            "verification_status": verification["status"],
            "rows_checked": verification["rows_checked"],
            "physical_machine_sha256": host_preflight["physical_machine_sha256"],
            "compiler_identity_sha256": host_preflight["native"]["compiler_identity_sha256"],
            "non_vm_placement_status": placement["status"],
            "runpod_machine_id": placement["runpod_machine_id"],
        })
    return result


def run() -> int:
    record = {
        "schema": "crse-query-ladder-q64-runpod-controller-result/v1",
        "started_utc": preflight.utc_now(),
        "status": "preflight",
        "creation_attempted": False,
        "creation_uncertain": False,
        "pod_created": False,
        "automatic_replacement_queued": False,
    }
    state = client = None
    try:
        authorization = require_authorization()
        record["authorization_record_sha256"] = sha256(AUTHORIZATION)
        record["authorization_recorded_utc"] = authorization.get("recorded_utc")
        ready = preflight.check()
        offer = next(
            (row for row in ready.get("offers", [])
             if row.get("id") == CPU_FLAVOR and row.get("eligible") is True),
            None,
        )
        rate = float(offer["rate_usd_per_hour"]) if offer else float("nan")
        projected = (rate + STORAGE_RATE_RESERVE) * HARD_LIFETIME_SECONDS / 3600
        ready["q64_second_host_gate"] = {
            "selected_cpu_flavor": CPU_FLAVOR,
            "rate_usd_per_hour": rate,
            "projected_hard_lifetime_cost_usd": projected,
            "total_cost_cap_usd": TOTAL_COST_CAP_USD,
            "zero_existing_pods": not any(ready.get("inventories", {}).values()),
            "ready": bool(
                offer is not None
                and math.isfinite(rate)
                and 0 < rate <= RATE_CAP_USD_PER_HOUR
                and projected <= TOTAL_COST_CAP_USD
                and not any(ready.get("inventories", {}).values())
                and ready.get("credit_sufficient") is True
                and ready.get("spend_limit_sufficient") is True
            ),
        }
        shared.write(OUT / "PREFLIGHT.json", ready)
        if not ready["q64_second_host_gate"]["ready"]:
            raise RuntimeError("RunPod q64 account/resource/budget preflight failed")
        watchdog = arm_watchdog()
        client = preflight.session()
        if any(shared.inventories(client).values()):
            raise RuntimeError("zero-pod baseline changed before q64 second-host creation")
        created = time.time()
        state = {
            "name": "cm-c7-linux-" + uuid.uuid4().hex[:12],
            "created_epoch": created,
            "cleanup_epoch": created + HARD_LIFETIME_SECONDS,
            "horizon_epoch": created + RECONCILIATION_SECONDS,
        }
        token = secrets.token_urlsafe(32)
        body = create_payload(state["name"], offer, token, created)
        shared.write(OUT / "TRANSPORT-FREEZE.json", {
            "schema": "crse-query-ladder-q64-runpod-transport-freeze/v1",
            "controller_sha256": sha256(Path(__file__).resolve()),
            "bootstrap_sha256": sha256(BOOTSTRAP),
            "authorization_sha256": sha256(AUTHORIZATION),
            "handoff_sha256": sha256(HANDOFF),
            "child_freeze_sha256": sha256(CHILD_FREEZE),
            "source_bundle_sha256": sha256(BUNDLE),
            "source_bundle_bytes": BUNDLE.stat().st_size,
            "remote_program_sha256": hashlib.sha256(REMOTE_CODE.encode()).hexdigest(),
            "image": IMAGE,
            "exact_commands": COMMANDS,
            "credentials_recorded_or_uploaded": False,
        })
        shared.write(shared.STATE, state)
        shared.confirm_watchdog(watchdog, state)
        record.update({
            "creation_attempted": True,
            "creation_uncertain": True,
            "creation_request_utc": preflight.utc_now(),
            "creation_endpoint": preflight.V1 + "/pods",
            "name": state["name"],
            "selected_cpu": offer["id"],
            "quoted_rate_usd_per_hour": offer["rate_usd_per_hour"],
        })
        print(json.dumps({
            "action": "create_one_cpu_pod", "name": state["name"],
            "cpu": offer["id"], "rate": offer["rate_usd_per_hour"],
        }), flush=True)
        response = client.post(
            preflight.V1 + "/pods", json=body, timeout=(10, 50), allow_redirects=False
        )
        record["creation_http_status"] = response.status_code
        if response.status_code not in (200, 201):
            record["creation_uncertain"] = not 400 <= response.status_code < 500
            raise RuntimeError("RunPod q64 pod creation failed HTTP " + str(response.status_code))
        pod = response.json()
        pod = pod.get("pod", pod)
        pod_id = pod.get("id")
        if not isinstance(pod_id, str) or not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
            raise RuntimeError("RunPod q64 creation response has no valid pod ID")
        shared.write(shared.IDENTITY, {
            "pod_id": pod_id, "name": state["name"],
            "recorded_utc": preflight.utc_now(), "source": "this create response",
        })
        record.update({"pod_id": pod_id, "pod_created": True, "creation_uncertain": False})
        pod = shared.actual_pod(client, pod_id)
        machine_id = pod.get("machineId") or (pod.get("machine") or {}).get("id")
        if not isinstance(machine_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", machine_id):
            raise RuntimeError("created RunPod lacks a distinct physical placement identity")
        shared.write(OUT / "POD-RESOURCE-CHECK.json", {
            "checked_utc": preflight.utc_now(),
            "response_fields": sorted(pod),
            "pod": {key: pod.get(key) for key in (
                "id", "name", "machineId", "image", "imageName", "computeType",
                "cloudType", "cloud", "verified_v2_cloud", "cpuFlavorId", "vcpuCount",
                "memoryInGb", "costPerHr", "containerDiskInGb", "volumeInGb",
                "volumeMountPath", "ports",
            )},
            "machine_secure_cloud": (pod.get("machine") or {}).get("secureCloud"),
            "network_volume_present": bool(pod.get("networkVolume")),
        })
        record["actual_resources"] = shared.validate_pod(pod, state, offer)
        record["actual_resources"]["runpod_machine_id"] = machine_id
        record["evidence"] = save_evidence(
            execute_remote(pod_id, machine_id, token, created, record)
        )
        if record["evidence"].get("remote_status") != "complete":
            raise RuntimeError("RunPod q64 remote handoff did not complete")
        record["status"] = "complete"
    except Exception as exc:
        record["status"] = "failed"
        record["error_type"] = type(exc).__name__
        if isinstance(exc, (RuntimeError, ValueError, OSError)):
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
                        "finished_utc": preflight.utc_now(),
                        "owned_pod_absent_verified": True,
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
            rate = record.get("actual_resources", {}).get("rate_usd_per_hour")
            record["estimated_compute_cost_usd"] = (
                rate * record["elapsed_since_create_s"] / 3600 if rate else None
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
    with authorized_host_awake_guard(
        "q64-second-host-watchdog" if args.watchdog else "q64-second-host-controller"
    ):
        return shared.watchdog() if args.watchdog else run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}), flush=True)
        raise SystemExit(2)
