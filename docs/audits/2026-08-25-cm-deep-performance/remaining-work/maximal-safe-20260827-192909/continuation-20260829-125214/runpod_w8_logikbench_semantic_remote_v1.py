"""Dependency-closed W8 semantic/root/oracle scout; no performance measurement."""

from __future__ import annotations

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
import zipfile


ROOT = Path("/workspace/cm-w8-logikbench-semantic-v1")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "run-output"
CAP = 32 << 20
LOCK = ROOT / (
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/runpod-requirements.lock"
)
WORKER = ROOT / "runpod_w8_logikbench_semantic_worker_v1.py"
CONVERSION = ROOT / "w8-conversion"
ADMISSION = ROOT / "W8-LOGIKBENCH-STATIC-ADMISSION.json"
ACQUISITION = ROOT / "W8-LOGIKBENCH-ACQUISITION.json"
SEMANTIC = OUT / "w8-semantic"


def emit(kind: str, **fields: object) -> None:
    print("CM_EVENT " + json.dumps({"kind": kind, **fields}, sort_keys=True), flush=True)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_command(name: str, command: list[str], timeout: float, *, cwd: Path = ROOT) -> dict:
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
        "stdout_sha256": digest(stdout.read_bytes()),
        "stderr_sha256": digest(stderr.read_bytes()),
    }
    if returncode:
        record["stderr_tail"] = stderr.read_text(errors="replace")[-3000:]
    (OUT / (name + ".json")).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if returncode:
        raise RuntimeError(name + " failed with exit code " + str(returncode))
    return record


def source_identity(manifest: dict) -> list[dict]:
    rows = []
    for expected in manifest["files"]:
        path = ROOT / PurePosixPath(expected["target"])
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("source disappeared or became linked")
        data = path.read_bytes()
        actual = {"target": expected["target"], "bytes": len(data), "sha256": digest(data)}
        if actual["bytes"] != expected["bytes"] or actual["sha256"] != expected["sha256"]:
            raise RuntimeError("source identity changed: " + expected["target"])
        rows.append(actual)
    return rows


def semantic_summary() -> dict:
    scout = json.loads((SEMANTIC / "semantic-scout.json").read_text(encoding="utf-8"))
    oracle = json.loads((SEMANTIC / "oracle-package.json").read_text(encoding="utf-8"))
    draft = json.loads((SEMANTIC / "confirmation-draft.json").read_text(encoding="utf-8"))
    rows = scout.get("rows") or []
    primary = [row for row in rows if row.get("primary_selected") is True]
    case_ids = [case.get("case_id") for case in draft.get("cases") or []]
    oracle_ids = [row.get("case_id") for row in oracle.get("rows") or []]
    errors = []
    if (
        scout.get("schema") != "cm-comparative-w8-semantic-scout/v1"
        or scout.get("performance_measurement") is not False
        or scout.get("performance_claim_permitted") is not False
        or scout.get("converted_inputs") != 64
        or scout.get("terminal_rows") != 64
        or len(rows) != 64
        or not isinstance(scout.get("unique_eligible"), int)
        or scout["unique_eligible"] < 30
        or scout.get("primary_selected") != 30
        or len(primary) != 30
    ):
        errors.append("semantic scout counts or no-timing contract mismatch")
    if any(
        row.get("status") != "eligible"
        or row.get("translation_compatible") is not True
        or row.get("translation_truth_sha256") != row.get("truth_sha256")
        or row.get("performance_measurement") is not False
        or row.get("performance_claim_permitted") is not False
        for row in primary
    ):
        errors.append("a primary case lacks exact translation/oracle agreement")
    if (
        draft.get("schema") != "cm-comparative-w8-logikbench-confirmation-draft/v1"
        or draft.get("case_count") != 30
        or len(case_ids) != len(set(case_ids))
        or len(case_ids) != 30
        or draft.get("performance_measurement") is not False
        or draft.get("performance_claim_permitted") is not False
        or oracle.get("schema") != "cm-comparative-w8-oracle-package/v1"
        or len(oracle_ids) != 30
        or case_ids != oracle_ids
    ):
        errors.append("confirmation draft or oracle package mismatch")
    if errors:
        raise RuntimeError("; ".join(errors))
    return {
        "converted_inputs": 64,
        "eligible": scout["eligible"],
        "unique_eligible": scout["unique_eligible"],
        "semantic_duplicates": scout["semantic_duplicates"],
        "primary_selected": 30,
        "case_ids_sha256": digest(json.dumps(case_ids, separators=(",", ":")).encode()),
        "semantic_scout_sha256": digest((SEMANTIC / "semantic-scout.json").read_bytes()),
        "oracle_package_sha256": digest((SEMANTIC / "oracle-package.json").read_bytes()),
        "confirmation_draft_sha256": digest((SEMANTIC / "confirmation-draft.json").read_bytes()),
        "performance_measurement": False,
        "performance_claim_permitted": False,
    }


def publish_evidence(status: str, error: str | None, manifest: dict, before: list[dict]) -> None:
    validation = {
        "status": status,
        "error": error,
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "pid": os.getpid(),
        "source_files": len(manifest.get("files", [])),
        "source_before_sha256": digest(json.dumps(before, sort_keys=True).encode()),
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "validation_errors": [],
    }
    try:
        after = source_identity(manifest)
        (OUT / "SOURCE-AFTER.json").write_text(
            json.dumps(after, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        validation["source_after_sha256"] = digest(json.dumps(after, sort_keys=True).encode())
        validation["source_unchanged"] = after == before
    except Exception as exc:
        validation["source_unchanged"] = False
        validation["validation_errors"].append({
            "section": "source-after", "error_type": type(exc).__name__, "error": str(exc)[:500]
        })
    try:
        validation["semantic_summary"] = semantic_summary()
    except Exception as exc:
        validation["validation_errors"].append({
            "section": "semantic-evidence", "error_type": type(exc).__name__, "error": str(exc)[:500]
        })
    (OUT / "REMOTE-VALIDATION.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
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
    archive_sha256 = digest(data)
    chunk = 3072
    emit("evidence_start", bytes=len(data), sha256=archive_sha256,
         chunks=(len(encoded) + chunk - 1) // chunk, uncompressed_bytes=uncompressed)
    for index in range(0, len(encoded), chunk):
        print("CM_EVIDENCE %06d %s" % (index // chunk, encoded[index:index + chunk]), flush=True)
    emit("evidence_end", sha256=archive_sha256)


OUT.mkdir(parents=True, exist_ok=False)
status = "failed"
error = None
manifest = {"files": []}
before: list[dict] = []
try:
    bundle_path = Path(os.environ.pop("CM_BUNDLE_PATH"))
    manifest_path = Path(os.environ.pop("CM_UPLOAD_MANIFEST_PATH"))
    if (
        not bundle_path.is_file() or bundle_path.stat().st_size > 8 << 20
        or not manifest_path.is_file() or manifest_path.stat().st_size > 1 << 20
    ):
        raise RuntimeError("bounded transport files are unavailable")
    bundle = bundle_path.read_bytes()
    expected_bundle = os.environ.pop("CM_BUNDLE_SHA256")
    if digest(bundle) != expected_bundle:
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
            if len(data) != row["bytes"] or digest(data) != row["sha256"]:
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
    emit("stage", name="install-base")
    remaining = setup_deadline - time.time()
    if remaining <= 0:
        raise RuntimeError("boot consumed setup deadline")
    run_command(
        "pip-install-base",
        [sys.executable, "-m", "pip", "install", "--require-hashes", "--only-binary=:all:",
         "-r", str(LOCK)],
        min(300, remaining),
    )
    remaining = setup_deadline - time.time()
    if remaining <= 0:
        raise RuntimeError("base install consumed setup deadline")
    run_command("pip-check-base", [sys.executable, "-m", "pip", "check"], min(30, remaining))
    (OUT / "BASE-DEPENDENCIES.json").write_text(
        json.dumps(
            {distribution.metadata["Name"]: distribution.version
             for distribution in importlib.metadata.distributions()},
            indent=2, sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    emit("stage", name="focused-tests")
    run_command(
        "focused-tests",
        [sys.executable, "-m", "pytest", "-q", "tests/test_blif_recognition.py",
         "-p", "no:cacheprovider", "--basetemp", str(OUT / "pytest-temp")],
        90,
    )
    emit("stage", name="semantic-root-oracle-scout")
    run_command(
        "semantic-worker",
        [sys.executable, str(WORKER), "--conversion-root", str(CONVERSION),
         "--admission", str(ADMISSION), "--acquisition", str(ACQUISITION),
         "--output", str(SEMANTIC)],
        780,
    )
    semantic_summary()
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
