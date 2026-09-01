"""Run the frozen p7-ir-b P7 W5 development shard on one Linux allocation."""

import base64
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import signal
import subprocess
import sys
import sysconfig
import time
import urllib.request
import zipfile


SHARD_ID = "p7-ir-b"
POLICY_ID = "p7-ir"
PRIMARY_CASE_IDS = [
    "development-e3-e3c-k12-impeqv_dom-tree-2-0c0e561a18d2",
    "development-e3-e3c-k12-mixed-shared-2-afa759e7785b",
    "development-e3-e3c-k12-xor_dom-shared-2-8f5e66e2839b",
    "development-e3-e3c-k16-andor_dom-shared-2-453c0065c802",
    "development-e3-e3c-k16-andor_dom-tree-2-9c22a211ecf7",
    "development-e3-e3c-k16-impeqv_dom-shared-2-edd4a53827db",
    "development-e3-e3c-k16-xor_dom-tree-2-492d4245b4d5",
    "development-e3-e3c-k8-andor_dom-shared-2-1341133d90d1",
    "development-e3-e3c-k8-impeqv_dom-shared-2-85e89aa3eda1",
    "development-e3-e3c-k8-mixed-shared-2-605da44b5374",
    "development-e3-e3c-k8-mixed-tree-2-a3c0e6c7fb43",
    "development-e3-e3c-k8-xor_dom-tree-2-54fa00575e7c",
    "development-epfl-adder-8df870a9daa9",
    "development-epfl-int2float-a195a4befab8",
    "development-epfl-mem_ctrl-a246a59df2bd",
    "development-epfl-square-36ba0c79625d",
    "regression-e3-e3c-k12-andor_dom-tree-1-361b23dec6a9",
    "regression-e3-e3c-k12-impeqv_dom-tree-1-f5fb6ea4cc57",
    "regression-e3-e3c-k12-mixed-shared-1-f2cb4225046c",
    "regression-e3-e3c-k12-xor_dom-shared-1-b5d9ccb2c9ec",
    "regression-e3-e3c-k16-andor_dom-tree-1-8134c819770c",
    "regression-e3-e3c-k16-impeqv_dom-tree-1-2a780cf7d49d",
    "regression-e3-e3c-k16-mixed-shared-1-2da3d88e96c8",
    "regression-e3-e3c-k16-xor_dom-shared-1-8b87e2a80600",
    "regression-e3-e3c-k8-andor_dom-shared-1-d2f31ca43fdc",
    "regression-e3-e3c-k8-andor_dom-tree-1-b28dbfbd470c",
    "regression-e3-e3c-k8-impeqv_dom-tree-1-3d5166db5e97",
    "regression-e3-e3c-k8-xor_dom-shared-1-9b9ee62c0196"
]
PRIMARY_BLOCKS = 8
PRIMARY_CELLS = 896
PRIMARY_FREEZE_SHA256 = "f4cfa143c5ca122ed0f2182f1dd8c86b7c472e787cbad19816f356ce5b2d2c2d"
ANCHOR_ID = "p7-ir-anchor"
ANCHOR_CASE_IDS = [
    "development-e3-e3c-k12-xor_dom-shared-2-8f5e66e2839b",
    "development-epfl-dec-ac01ccb8dc43"
]
ANCHOR_BLOCKS = 8
ANCHOR_CELLS = 64
ANCHOR_FREEZE_SHA256 = "48fcbafc857703fa0c5f928d386970ca1162848f33b550bb17d8fad3ceb239e4"
PARENT_FREEZE_SHA256 = "54ea61a38135426975a0d1fead9b24c020dc565eb3d952356640fa38062598dd"
ROOT = Path("/workspace/cm-p7-w5-p7-ir-b")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "run-output"
CAP = 32 << 20
LOCK = ROOT / (
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/runpod-requirements.lock"
)


def emit(kind, **fields):
    print("CM_EVENT " + json.dumps({"kind": kind, **fields}, sort_keys=True), flush=True)


def run_command(name, command, timeout, *, cwd=ROOT):
    started = time.monotonic()
    stdout = OUT / (name + ".stdout.txt")
    stderr = OUT / (name + ".stderr.txt")
    with stdout.open("xb") as out, stderr.open("xb") as err:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
            env={
                **os.environ,
                "OPENBLAS_NUM_THREADS": "1",
                "OMP_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
                "NUMEXPR_NUM_THREADS": "1",
                "PYTHONUNBUFFERED": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "DEBIAN_FRONTEND": "noninteractive",
            },
        )
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
            raise RuntimeError(name + " timed out")
    if stdout.stat().st_size > CAP or stderr.stat().st_size > CAP:
        raise RuntimeError(name + " output exceeded evidence cap")
    record = {
        "name": name,
        "command": command,
        "returncode": returncode,
        "wall_s": time.monotonic() - started,
        "stdout_sha256": hashlib.sha256(stdout.read_bytes()).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr.read_bytes()).hexdigest(),
    }
    if returncode:
        record["stderr_tail"] = stderr.read_text(errors="replace")[-3000:]
    with (OUT / (name + ".json")).open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    if returncode:
        raise RuntimeError(name + " failed with exit code " + str(returncode))
    return record


def source_identity(manifest):
    rows = []
    for expected in manifest["files"]:
        path = ROOT / PurePosixPath(expected["target"])
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("source disappeared or became linked")
        payload = path.read_bytes()
        actual = {"target": expected["target"], "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        if actual["bytes"] != expected["bytes"] or actual["sha256"] != expected["sha256"]:
            raise RuntimeError("source identity changed: " + expected["target"])
        rows.append(actual)
    return rows


def derive_w5_freeze(parent_path, case_ids, expected_sha256, partition_id):
    import copy
    from cmbench.comparative.contracts import canonical_bytes
    from cmbench.comparative.corpus_freeze import build_order_ledger, validate_freeze

    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    validate_freeze(parent)
    if parent.get("freeze_sha256") != PARENT_FREEZE_SHA256:
        raise RuntimeError("P6 parent freeze identity changed")
    selected = set(case_ids)
    if len(selected) != len(case_ids):
        raise RuntimeError("duplicate W5 selected case")
    derived = copy.deepcopy(parent)
    derived["cases"] = [case for case in parent["cases"] if case["case_id"] in selected]
    if len(derived["cases"]) != len(selected):
        raise RuntimeError("W5 selected case unavailable")
    policy = next(row for row in parent["schedule_policies"] if row["policy_id"] == POLICY_ID)
    normalized = {field: value for field, value in policy.items() if field != "order_ledger"}
    normalized["order_ledger"] = build_order_ledger(derived["cases"], normalized)
    derived["schedule_policies"] = [normalized]
    provenance = dict(derived["provenance"])
    provenance["w5_development_partition"] = {
        "schema": "cm-comparative-p7-w5-development-partition/v1",
        "parent_freeze_sha256": PARENT_FREEZE_SHA256,
        "partition_id": partition_id,
        "policy_id": POLICY_ID,
        "case_count": len(case_ids),
        "selected_case_ids_in_parent_order": case_ids,
        "selected_case_ids_sha256": hashlib.sha256(canonical_bytes(case_ids)).hexdigest(),
        "typed_feasibility_exclusion": "development-epfl-sqrt-31cdaf5d0213",
        "case_selection_uses_comparative_timing": False,
        "shard_size_uses_w4_resource_timing": True,
    }
    derived["provenance"] = provenance
    core = {field: value for field, value in derived.items() if field != "freeze_sha256"}
    derived["freeze_sha256"] = hashlib.sha256(canonical_bytes(core)).hexdigest()
    if derived["freeze_sha256"] != expected_sha256:
        raise RuntimeError("W5 derived freeze identity mismatch")
    validate_freeze(derived)
    path = OUT / (partition_id + "-FREEZE.json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(derived, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return path


def _validation_error(errors, section, exc):
    if len(errors) < 8:
        errors.append({
            "section": section,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        })


def _junit_counts(path):
    import xml.etree.ElementTree as ET

    root = ET.parse(path).getroot()
    local = lambda element: element.tag.rsplit("}", 1)[-1]
    if local(root) == "testsuite":
        suites = [root]
    else:
        suites = [element for element in root if local(element) == "testsuite"]
    metadata = {
        key: sum(int(suite.get(key, "0")) for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    cases = [element for element in root.iter() if local(element) == "testcase"]
    testcase_counts = {"tests": len(cases), "failures": 0, "errors": 0, "skipped": 0}
    for case in cases:
        children = {local(child) for child in case}
        for singular, plural in (("failure", "failures"), ("error", "errors"), ("skipped", "skipped")):
            testcase_counts[plural] += int(singular in children)
    return metadata, testcase_counts


def publish_evidence(status, error, manifest, before):
    errors = []
    validation = {
        "status": status,
        "error": error,
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "pid": os.getpid(),
        "source_files": len(manifest["files"]),
        "source_before_sha256": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
        "performance_measurement": True,
        "principal_p7_result": True,
        "w5_primary_freeze_sha256": PRIMARY_FREEZE_SHA256,
    }
    try:
        metadata, testcases = _junit_counts(OUT / "focused.xml")
        validation["junit_metadata"] = metadata
        validation["junit_testcases"] = testcases
    except Exception as exc:
        _validation_error(errors, "focused-junit", exc)
    try:
        validation["offline_verification"] = json.loads(
            (OUT / "offline-gate-verify.stdout.txt").read_text(encoding="utf-8")
        )
    except Exception as exc:
        _validation_error(errors, "offline-gate", exc)
    for name in ("primary", "diagnostic-anchor"):
        try:
            summary = json.loads((OUT / name / "summary.json").read_text(encoding="utf-8"))
            verification = json.loads((OUT / (name + "-verify.stdout.txt")).read_text(encoding="utf-8"))
            validation[name.replace("-", "_") + "_summary"] = summary
            validation[name.replace("-", "_") + "_verification"] = verification
        except Exception as exc:
            _validation_error(errors, name, exc)
    try:
        after = source_identity(manifest)
        with (OUT / "SOURCE-AFTER.json").open("x", encoding="utf-8") as stream:
            json.dump(after, stream, indent=2, sort_keys=True)
            stream.write("\n")
        validation["source_after_sha256"] = hashlib.sha256(json.dumps(after, sort_keys=True).encode()).hexdigest()
        validation["source_unchanged"] = after == before
    except Exception as exc:
        validation["source_unchanged"] = False
        _validation_error(errors, "source-after", exc)
    validation["validation_errors"] = errors
    with (OUT / "REMOTE-VALIDATION.json").open("x", encoding="utf-8") as stream:
        json.dump(validation, stream, indent=2, sort_keys=True)
        stream.write("\n")

    archive = io.BytesIO()
    uncompressed = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for path in sorted(OUT.rglob("*")):
            if not path.is_file() or "pytest-temp" in path.parts:
                continue
            data = path.read_bytes()
            uncompressed += len(data)
            if uncompressed > CAP:
                raise RuntimeError("evidence file total exceeds 32 MiB cap")
            output.writestr(path.relative_to(ROOT).as_posix(), data)
    data = archive.getvalue()
    if len(data) > CAP:
        raise RuntimeError("evidence archive exceeds 32 MiB cap")
    encoded = base64.b64encode(data).decode("ascii")
    digest = hashlib.sha256(data).hexdigest()
    chunk = 3072
    emit(
        "evidence_start",
        bytes=len(data),
        sha256=digest,
        chunks=(len(encoded) + chunk - 1) // chunk,
        uncompressed_bytes=uncompressed,
    )
    for index in range(0, len(encoded), chunk):
        print("CM_EVIDENCE %06d %s" % (index // chunk, encoded[index:index + chunk]), flush=True)
    emit("evidence_end", sha256=digest)


OUT.mkdir(parents=True, exist_ok=False)
status = "failed"
error = None
manifest = None
before = []
try:
    bundle_path = Path(os.environ.pop("CM_BUNDLE_PATH"))
    manifest_path = Path(os.environ.pop("CM_UPLOAD_MANIFEST_PATH"))
    if not bundle_path.is_file() or bundle_path.stat().st_size > 32 << 20 or not manifest_path.is_file() or manifest_path.stat().st_size > 1 << 20:
        raise RuntimeError("bounded transport files are unavailable")
    bundle = bundle_path.read_bytes()
    expected_bundle = os.environ.pop("CM_BUNDLE_SHA256")
    if hashlib.sha256(bundle).hexdigest() != expected_bundle:
        raise RuntimeError("uploaded source archive hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {row["target"]: row for row in manifest["files"]}
    if len(expected) != len(manifest["files"]):
        raise RuntimeError("duplicate upload target")
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        names = archive.namelist()
        if set(names) != set(expected) or len(names) != len(set(names)):
            raise RuntimeError("uploaded source archive member mismatch")
        for name in names:
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts:
                raise RuntimeError("unsafe uploaded source target")
            data = archive.read(name)
            row = expected[name]
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise RuntimeError("uploaded source member hash mismatch: " + name)
            target = ROOT / pure
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
    before = source_identity(manifest)
    with (OUT / "SOURCE-BEFORE.json").open("x", encoding="utf-8") as stream:
        json.dump(before, stream, indent=2, sort_keys=True)
        stream.write("\n")
    runtime = {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "logical_cpus_host_visible": os.cpu_count(),
        "affinity": sorted(os.sched_getaffinity(0)),
        "image_tag": os.environ.pop("CM_IMAGE_TAG"),
        "image_amd64_digest": os.environ.pop("CM_IMAGE_DIGEST"),
        "bundle_sha256": expected_bundle,
        "source_files": len(expected),
        "runpod_pod_id": os.environ.get("RUNPOD_POD_ID"),
        "gil_disabled": sysconfig.get_config_var("Py_GIL_DISABLED"),
        "performance_measurement": True,
        "principal_p7_result": True,
        "w5_primary_freeze_sha256": PRIMARY_FREEZE_SHA256,
    }
    if (
        sys.version_info[:3] != (3, 13, 15)
        or platform.machine().lower() not in ("x86_64", "amd64")
        or runtime["gil_disabled"]
        or not runtime["runpod_pod_id"]
        or len(runtime["affinity"]) != 2
    ):
        raise RuntimeError("runtime identity or allocation mismatch")
    with (OUT / "RUNTIME.json").open("x", encoding="utf-8") as stream:
        json.dump(runtime, stream, indent=2, sort_keys=True)
        stream.write("\n")

    setup_deadline = float(os.environ.pop("CM_SETUP_DEADLINE"))
    emit("stage", name="install-base")
    remaining = setup_deadline - time.time()
    if remaining <= 0:
        raise RuntimeError("boot consumed setup deadline")
    run_command(
        "pip-install-base",
        [sys.executable, "-m", "pip", "install", "--require-hashes", "--only-binary=:all:", "-r", str(LOCK)],
        min(300, remaining),
    )
    remaining = setup_deadline - time.time()
    if remaining <= 0:
        raise RuntimeError("base install consumed setup deadline")
    run_command("pip-check-base", [sys.executable, "-m", "pip", "check"], min(30, remaining))
    with (OUT / "BASE-DEPENDENCIES.json").open("x", encoding="utf-8") as stream:
        json.dump(
            {distribution.metadata["Name"]: distribution.version for distribution in importlib.metadata.distributions()},
            stream,
            indent=2,
            sort_keys=True,
        )
        stream.write("\n")

    emit("stage", name="focused-tests")
    run_command(
        "focused-tests",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_cm_comparative_p7.py",
            "tests/test_cm_comparative_p7_runner.py",
            "tests/test_cm_comparative_p7_package.py",
            "tests/test_cm_comparative_corpus_freeze.py",
            "tests/test_blif_recognition.py",
            "tests/test_cm_comparative_linux_supervisor.py",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(OUT / "pytest-temp"),
            "--junitxml",
            str(OUT / "focused.xml"),
        ],
        180,
    )
    emit("stage", name="offline-gate")
    run_command(
        "offline-gate-verify",
        [
            sys.executable,
            "scripts/cm_comparative_p7_offline_gate.py",
            "verify",
            "--project-root",
            str(ROOT),
            "--freeze",
            str(ROOT / "docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json"),
            "--output",
            str(ROOT / "docs/research/verification/comparative-p7-offline-gate-v6-2026-08-30"),
        ],
        180,
    )
    parent_freeze = ROOT / "docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json"
    primary_freeze = str(derive_w5_freeze(
        parent_freeze, PRIMARY_CASE_IDS, PRIMARY_FREEZE_SHA256, SHARD_ID
    ))
    anchor_freeze = str(derive_w5_freeze(
        parent_freeze, ANCHOR_CASE_IDS, ANCHOR_FREEZE_SHA256, ANCHOR_ID
    ))
    execution_deadline = float(os.environ.pop("CM_EXECUTION_DEADLINE"))
    runs = (
        ("primary", primary_freeze, PRIMARY_CASE_IDS, PRIMARY_BLOCKS, ("regression", "development")),
        ("diagnostic-anchor", anchor_freeze, ANCHOR_CASE_IDS, ANCHOR_BLOCKS, ("development",)),
    )
    for name, freeze_path, case_ids, blocks, roles in runs:
        emit("stage", name=name)
        remaining = execution_deadline - time.time()
        if remaining <= 60:
            raise RuntimeError("insufficient W5 execution horizon")
        run_command(
            name,
            [
                sys.executable, "scripts/cm_comparative_p7_runner.py", "run",
                "--project-root", str(ROOT), "--freeze", freeze_path,
                "--output", str(OUT / name), "--policy", POLICY_ID,
                "--roles", *roles, "--blocks", str(blocks),
                "--profile", "performance",
                "--timeout-seconds", "30", "--rss-stop-bytes", str(1 << 30),
            ],
            min(840, remaining),
        )
        summary = json.loads((OUT / name / "summary.json").read_text(encoding="utf-8"))
        expected_cells = PRIMARY_CELLS if name == "primary" else ANCHOR_CELLS
        if (
            summary.get("status") != "passed"
            or summary.get("reconciliation", {}).get("planned_cells") != expected_cells
            or summary.get("reconciliation", {}).get("observed_cells") != expected_cells
            or summary.get("reconciliation", {}).get("statuses") != {"ok": expected_cells}
        ):
            raise RuntimeError(name + " summary did not reconcile")
        remaining = execution_deadline - time.time()
        if remaining <= 20:
            raise RuntimeError("insufficient W5 verification horizon")
        run_command(
            name + "-verify",
            [
                sys.executable, "scripts/cm_comparative_p7_runner.py", "verify",
                "--project-root", str(ROOT), "--freeze", freeze_path,
                "--output", str(OUT / name),
            ],
            min(120, remaining),
        )
    status = "complete"
except Exception as exc:
    error = type(exc).__name__ + ": " + str(exc)
    emit("failure", error=error)
finally:
    try:
        publish_evidence(status, error, manifest or {"files": []}, before)
    except Exception as exc:
        emit("evidence_failure", error=type(exc).__name__ + ": " + str(exc))
    emit("done", status=status)
