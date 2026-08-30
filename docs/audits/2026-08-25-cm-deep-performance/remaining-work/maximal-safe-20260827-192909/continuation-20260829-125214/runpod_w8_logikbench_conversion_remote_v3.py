"""Bounded W8 LogikBench conversion scout; executed only by its V3 controller."""

from __future__ import annotations

import base64
import hashlib
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
import zipfile


ROOT = Path("/workspace/cm-w8-logikbench-conversion-v3")
OUT = ROOT / "run-output"
CAP = 32 << 20
WORKER = ROOT / "runpod_w8_logikbench_conversion_worker_v3.py"
ADMISSION = ROOT / "W8-LOGIKBENCH-STATIC-ADMISSION.json"
SOURCE = ROOT / "source"
CONVERSION = OUT / "w8-conversion"


def emit(kind, **fields):
    print("CM_EVENT " + json.dumps({"kind": kind, **fields}, sort_keys=True), flush=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
        "stdout_sha256": sha256_bytes(stdout.read_bytes()),
        "stderr_sha256": sha256_bytes(stderr.read_bytes()),
    }
    if returncode:
        record["stderr_tail"] = stderr.read_text(errors="replace")[-3000:]
    (OUT / (name + ".json")).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if returncode:
        raise RuntimeError(name + " failed with exit code " + str(returncode))
    return record


def source_identity(manifest):
    rows = []
    for expected in manifest["files"]:
        path = ROOT / PurePosixPath(expected["target"])
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("source disappeared or became linked")
        data = path.read_bytes()
        actual = {"target": expected["target"], "bytes": len(data), "sha256": sha256_bytes(data)}
        if actual["bytes"] != expected["bytes"] or actual["sha256"] != expected["sha256"]:
            raise RuntimeError("source identity changed: " + expected["target"])
        rows.append(actual)
    return rows


def publish_evidence(status, error, manifest, before):
    validation = {
        "status": status,
        "error": error,
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "pid": os.getpid(),
        "source_files": len(manifest.get("files", [])),
        "source_before_sha256": sha256_bytes(json.dumps(before, sort_keys=True).encode()),
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "validation_errors": [],
    }
    try:
        after = source_identity(manifest)
        (OUT / "SOURCE-AFTER.json").write_text(
            json.dumps(after, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        validation["source_after_sha256"] = sha256_bytes(json.dumps(after, sort_keys=True).encode())
        validation["source_unchanged"] = after == before
    except Exception as exc:
        validation["source_unchanged"] = False
        validation["validation_errors"].append(
            {"section": "source-after", "error_type": type(exc).__name__, "error": str(exc)[:500]}
        )
    try:
        conversions = json.loads((CONVERSION / "conversions.json").read_text(encoding="utf-8"))
        fixtures = json.loads((CONVERSION / "fixture-summary.json").read_text(encoding="utf-8"))
        environment = json.loads((CONVERSION / "environment.json").read_text(encoding="utf-8"))
        validation["conversion_summary"] = {
            key: conversions.get(key)
            for key in (
                "attempted", "converted", "rejected", "retained_blif_bytes",
                "conversion_time_limit_seconds", "per_cluster_time_limit_seconds",
                "performance_measurement", "performance_claim_permitted",
            )
        }
        validation["fixture_summary"] = fixtures
        validation["conversion_environment"] = environment
    except Exception as exc:
        validation["validation_errors"].append(
            {"section": "conversion-evidence", "error_type": type(exc).__name__, "error": str(exc)[:500]}
        )
    (OUT / "REMOTE-VALIDATION.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    archive = io.BytesIO()
    uncompressed = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for path in sorted(OUT.rglob("*")):
            if not path.is_file():
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
    digest = sha256_bytes(data)
    chunk = 3072
    emit("evidence_start", bytes=len(data), sha256=digest,
         chunks=(len(encoded) + chunk - 1) // chunk, uncompressed_bytes=uncompressed)
    for index in range(0, len(encoded), chunk):
        print("CM_EVIDENCE %06d %s" % (index // chunk, encoded[index:index + chunk]), flush=True)
    emit("evidence_end", sha256=digest)


OUT.mkdir(parents=True, exist_ok=False)
status = "failed"
error = None
manifest = {"files": []}
before = []
try:
    bundle_path = Path(os.environ.pop("CM_BUNDLE_PATH"))
    manifest_path = Path(os.environ.pop("CM_UPLOAD_MANIFEST_PATH"))
    if (
        not bundle_path.is_file()
        or bundle_path.stat().st_size > 8 << 20
        or not manifest_path.is_file()
        or manifest_path.stat().st_size > 1 << 20
    ):
        raise RuntimeError("bounded transport files are unavailable")
    bundle = bundle_path.read_bytes()
    expected_bundle = os.environ.pop("CM_BUNDLE_SHA256")
    if sha256_bytes(bundle) != expected_bundle:
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
            if len(data) != row["bytes"] or sha256_bytes(data) != row["sha256"]:
                raise RuntimeError("uploaded source member hash mismatch: " + name)
            target = ROOT / pure
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
    before = source_identity(manifest)
    (OUT / "SOURCE-BEFORE.json").write_text(
        json.dumps(before, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
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
        "performance_measurement": False,
        "performance_claim_permitted": False,
    }
    if (
        sys.version_info[:3] != (3, 13, 15)
        or platform.machine().lower() not in ("x86_64", "amd64")
        or runtime["gil_disabled"]
        or not runtime["runpod_pod_id"]
        or len(runtime["affinity"]) != 2
    ):
        raise RuntimeError("runtime identity or allocation mismatch")
    (OUT / "RUNTIME.json").write_text(
        json.dumps(runtime, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    setup_deadline = float(os.environ.pop("CM_SETUP_DEADLINE"))
    emit("stage", name="install-yosys")
    remaining = setup_deadline - time.time()
    if remaining <= 0:
        raise RuntimeError("boot consumed setup deadline")
    run_command("apt-update", ["apt-get", "update"], min(180, remaining))
    remaining = setup_deadline - time.time()
    if remaining <= 0:
        raise RuntimeError("apt update consumed setup deadline")
    run_command(
        "apt-install-yosys",
        ["apt-get", "install", "-y", "--no-install-recommends", "yosys"],
        min(240, remaining),
    )
    remaining = setup_deadline - time.time()
    if remaining <= 0:
        raise RuntimeError("Yosys install consumed setup deadline")
    run_command("yosys-version", ["/usr/bin/yosys", "-V"], min(15, remaining))

    emit("stage", name="conversion")
    run_command(
        "conversion-worker",
        [
            sys.executable,
            str(WORKER),
            "--source-root", str(SOURCE),
            "--static-admission", str(ADMISSION),
            "--output", str(CONVERSION),
        ],
        660,
    )
    status = "complete"
except Exception as exc:
    error = type(exc).__name__ + ": " + str(exc)
    emit("failure", error=error)
finally:
    try:
        publish_evidence(status, error, manifest, before)
    except Exception as exc:
        emit("evidence_failure", error=type(exc).__name__ + ": " + str(exc))
    emit("done", status=status)
