"""CLI-audited native persistence functional scout; executed only by its controller."""

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


ROOT = Path("/workspace/cm-native-persistence-scout")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "run-output"
CAP = 32 << 20


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
    }
    try:
        metadata, testcases = _junit_counts(OUT / "focused.xml")
        validation["junit_metadata"] = metadata
        validation["junit_testcases"] = testcases
    except Exception as exc:
        _validation_error(errors, "focused-junit", exc)
    try:
        persistence = json.loads((OUT / "native-persistence/summary.json").read_text(encoding="utf-8"))
        validation["persistence_summary"] = {key: persistence.get(key) for key in (
            "status", "case_count", "executed_arm_count", "blocks", "planned_cells",
            "cell_statuses", "arm_statuses", "executed_build_processes",
            "executed_reload_processes", "exact_relation_rows",
            "serialized_artifact_deterministic_across_blocks", "performance_measurement",
            "performance_claim_permitted",
        )}
    except Exception as exc:
        _validation_error(errors, "native-persistence", exc)
    try:
        validation["d4_build"] = json.loads((OUT / "D4-COMPILER-IDENTITY.json").read_text(encoding="utf-8"))
    except Exception as exc:
        _validation_error(errors, "d4-build", exc)
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
                raise RuntimeError("evidence file total exceeds 16 MiB cap")
            output.writestr(path.relative_to(ROOT).as_posix(), data)
    data = archive.getvalue()
    if len(data) > CAP:
        raise RuntimeError("evidence archive exceeds 16 MiB cap")
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
        [sys.executable, "-m", "pip", "install", "--require-hashes", "--only-binary=:all:", "-r", "runpod-requirements.lock"],
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

    emit("stage", name="install-native-python")
    from scripts.cm_comparative_native_scout import install_dependencies

    native_dependencies = install_dependencies(
        OUT,
        ROOT / "study/RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json",
    )
    with (OUT / "NATIVE-DEPENDENCIES.json").open("x", encoding="utf-8") as stream:
        json.dump(native_dependencies, stream, indent=2, sort_keys=True)
        stream.write("\n")

    emit("stage", name="install-build-tools")
    remaining = setup_deadline - time.time()
    if remaining <= 0:
        raise RuntimeError("pip install consumed setup deadline")
    run_command("apt-update", ["/usr/bin/apt-get", "update"], min(180, remaining))
    remaining = setup_deadline - time.time()
    if remaining <= 0:
        raise RuntimeError("apt update consumed setup deadline")
    run_command(
        "apt-install-build-tools",
        [
            "/usr/bin/apt-get", "install", "-y", "--no-install-recommends",
            "build-essential", "libboost-dev", "libgmp-dev", "zlib1g-dev",
        ],
        min(300, remaining),
    )
    run_command(
        "apt-build-versions",
        [
            "/usr/bin/dpkg-query", "-W", "-f=${binary:Package}=${Version}\\n",
            "build-essential", "g++", "gcc", "libboost-dev", "libc6-dev", "libgmp-dev", "make", "zlib1g-dev",
        ],
        30,
    )

    emit("stage", name="build-d4-ddnnf")
    remaining = setup_deadline - time.time()
    if remaining <= 0:
        raise RuntimeError("build tools consumed setup deadline")
    d4_source = ROOT / "external/d4"
    patoh_header = d4_source / "patoh/patoh.h"
    patoh_url = (
        "https://raw.githubusercontent.com/crillab/d4/"
        "333370cc1e843dd0749c1efe88516e72b5239174/patoh/patoh.h"
    )
    request = urllib.request.Request(patoh_url, headers={"User-Agent": "cm-native-persistence-v3"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200 or response.geturl() != patoh_url:
            raise RuntimeError("PaToH header response identity")
        content_length = response.headers.get("Content-Length")
        if content_length is not None and int(content_length) != 11944:
            raise RuntimeError("PaToH header content length")
        patoh_payload = response.read(11945)
    if (
        len(patoh_payload) != 11944
        or hashlib.sha256(patoh_payload).hexdigest()
        != "a403cadf44785c773cc77895294f6674b7e2c7006a29bd41b401a81e8aff443c"
        or patoh_header.exists()
    ):
        raise RuntimeError("PaToH header payload identity")
    with patoh_header.open("xb") as stream:
        stream.write(patoh_payload)
        stream.flush()
        os.fsync(stream.fileno())
    with (OUT / "PATOH-HEADER.json").open("x", encoding="utf-8") as stream:
        json.dump(
            {
                "url": patoh_url,
                "bytes": len(patoh_payload),
                "sha256": hashlib.sha256(patoh_payload).hexdigest(),
                "source_commit": "333370cc1e843dd0749c1efe88516e72b5239174",
                "public_dependency_download": True,
            },
            stream,
            indent=2,
            sort_keys=True,
        )
        stream.write("\n")
    remaining = setup_deadline - time.time()
    if remaining <= 0:
        raise RuntimeError("public dependency download consumed setup deadline")
    run_command("d4-build", ["/usr/bin/make", "-j2", "s"], min(360, remaining), cwd=d4_source)
    d4_binary = d4_source / "d4"
    if not d4_binary.is_file() or d4_binary.is_symlink():
        raise RuntimeError("d4 compiler binary unavailable after build")
    d4_payload = d4_binary.read_bytes()
    if not d4_payload.startswith(b"\x7fELF\x02\x01\x01") or len(d4_payload) > 32 << 20:
        raise RuntimeError("d4 compiler ELF identity")
    d4_sha256 = hashlib.sha256(d4_payload).hexdigest()
    d4_binary.chmod(0o700)
    os.environ["CM_D4_DDNNF_BINARY"] = str(d4_binary.resolve())
    os.environ["CM_D4_DDNNF_SHA256"] = d4_sha256
    os.environ["CM_D4_DDNNF_ALLOWED_ROOT"] = str(ROOT.resolve())
    with (OUT / "D4-COMPILER-IDENTITY.json").open("x", encoding="utf-8") as stream:
        json.dump(
            {
                "status": "passed",
                "source_repository": "https://github.com/crillab/d4.git",
                "source_commit": "333370cc1e843dd0749c1efe88516e72b5239174",
                "build_command": ["/usr/bin/make", "-j2", "s"],
                "binary": str(d4_binary.relative_to(ROOT)),
                "binary_bytes": len(d4_payload),
                "binary_sha256": d4_sha256,
                "performance_ranking_permitted": False,
            },
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
            "tests/test_cm_comparative_fresh_persistence.py",
            "tests/test_cm_comparative_fresh_persistence_native.py",
            "tests/test_cm_comparative_fresh_persistence_pilot.py",
            "tests/test_cm_comparative_linux_supervisor.py",
            "--deselect=tests/test_cm_comparative_fresh_persistence.py::FreshPersistenceTests::test_inventory_never_substitutes_autoref_for_native_arms",
            "--deselect=tests/test_cm_comparative_fresh_persistence_pilot.py::FreshPersistencePilotTests::test_plan_is_complete_balanced_and_refusal_preserving",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(OUT / "pytest-temp"),
            "--junitxml",
            str(OUT / "focused.xml"),
        ],
        180,
    )
    emit("stage", name="native-persistence")
    run_command(
        "native-persistence",
        [
            sys.executable,
            "scripts/cm_comparative_fresh_persistence_pilot.py",
            "run",
            "--output",
            str(OUT / "native-persistence"),
            "--arms",
            "cudd_zdd,d4_ddnnf",
            "--case-limit",
            "2",
            "--blocks",
            "4",
            "--cloud-run",
        ],
        600,
    )
    run_command(
        "native-persistence-verify",
        [
            sys.executable,
            "scripts/cm_comparative_fresh_persistence_pilot.py",
            "verify",
            "--output",
            str(OUT / "native-persistence"),
        ],
        120,
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



