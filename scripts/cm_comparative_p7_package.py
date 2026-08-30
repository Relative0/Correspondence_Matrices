#!/usr/bin/env python3
"""Build and verify a dependency-closed, non-performance P7 runner package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.evidence import publish_json
from cmbench.comparative.p7_runner import sha256, strict_json
from scripts.cm_manifest_dependency_audit import audit_manifest, imported_local_files


SCHEMA = "cm-comparative-p7-runner-package/v1"
MANIFEST_SCHEMA = "cm-comparative-p7-runner-source-manifest/v1"
MAX_FILES = 512
MAX_SOURCE_BYTES = 64 << 20
MAX_TEST_OUTPUT_BYTES = 1 << 20
LOCK_PATH = (
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/runpod-requirements.lock"
)
FOCUSED_TESTS = (
    "tests/test_cm_comparative_p7.py",
    "tests/test_cm_comparative_p7_runner.py",
    "tests/test_cm_comparative_p7_package.py",
    "tests/test_cm_comparative_corpus_freeze.py",
    "tests/test_blif_recognition.py",
    "tests/test_cm_comparative_linux_supervisor.py",
)
SEEDS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cm_normalize.py",
    LOCK_PATH,
    "cmbench/comparative/arms.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/corpus_freeze.py",
    "cmbench/comparative/evidence.py",
    "cmbench/comparative/ir.py",
    "cmbench/comparative/linux_supervisor.py",
    "cmbench/comparative/p7.py",
    "cmbench/comparative/p7_runner.py",
    "cmbench/comparative/schedule.py",
    "cmbench/recognition/blif.py",
    "scripts/cm_comparative_p7_offline_gate.py",
    "scripts/cm_comparative_p7_package.py",
    "scripts/cm_comparative_p7_runner.py",
    "scripts/cm_comparative_prepare_p6_review.py",
    "scripts/cm_manifest_dependency_audit.py",
    *FOCUSED_TESTS,
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _safe_relative(name: str) -> str:
    pure = PurePosixPath(name)
    require(
        isinstance(name, str)
        and name == pure.as_posix()
        and not pure.is_absolute()
        and ".." not in pure.parts
        and pure.parts,
        "unsafe package path",
    )
    lowered = {part.lower() for part in pure.parts}
    require(".git" not in lowered and not any(part.startswith(".env") for part in lowered),
            "secret-like package path")
    require(pure.suffix.lower() not in {".key", ".pem", ".pfx", ".db", ".sqlite", ".sqlite3"},
            "secret-like package suffix")
    return name


def _freeze_sources(freeze: dict) -> set[str]:
    rows = freeze.get("cases")
    require(isinstance(rows, list), "freeze cases")
    return {_safe_relative(row["source"]["path"]) for row in rows}


def dependency_closed_paths(project: Path, seeds: set[str]) -> list[str]:
    selected = {_safe_relative(name) for name in seeds}
    while True:
        required = set(selected)
        for name in sorted(selected):
            if not name.endswith(".py"):
                continue
            path = (project / name).resolve()
            require(path.is_relative_to(project) and path.is_file() and not path.is_symlink(),
                    "package source unavailable")
            required.update(imported_local_files(project, name, path.read_bytes()))
        require(len(required) <= MAX_FILES, "package file-count bound")
        if required == selected:
            return sorted(selected)
        selected = required


def source_manifest(project: Path, paths: list[str]) -> dict:
    rows = []
    total = 0
    for name in paths:
        path = (project / name).resolve()
        require(path.is_relative_to(project) and path.is_file() and not path.is_symlink(),
                "package source identity path")
        size = path.stat().st_size
        total += size
        rows.append({"source": name, "target": name, "bytes": size, "sha256": sha256(path)})
    require(total <= MAX_SOURCE_BYTES, "package source-byte bound")
    core = {
        "schema": MANIFEST_SCHEMA,
        "file_count": len(rows),
        "bytes": total,
        "secrets_included": False,
        "performance_measurement": False,
        "files": rows,
    }
    return {**core, "manifest_sha256": hashlib.sha256(canonical_bytes(core)).hexdigest()}


def write_zip(project: Path, paths: list[str], target: Path) -> None:
    with target.open("xb") as raw:
        with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in paths:
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, (project / name).read_bytes())


def _bounded_command(command: list[str], *, cwd: Path, timeout: int) -> dict:
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        },
    )
    require(len(completed.stdout) <= MAX_TEST_OUTPUT_BYTES and len(completed.stderr) <= MAX_TEST_OUTPUT_BYTES,
            "isolated test output bound")
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
    }


def _checksums(output: Path) -> dict:
    rows = []
    for path in sorted(output.iterdir()):
        if not path.is_file() or path.name == "checksums.json":
            continue
        rows.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {"schema": "cm-comparative-p7-runner-package-checksums/v1", "files": rows}


def build(args) -> int:
    project = args.project_root.resolve()
    freeze_path = args.freeze.resolve()
    offline = args.offline_gate.resolve()
    output = args.output.absolute()
    require(freeze_path.is_relative_to(project) and freeze_path.is_file(), "freeze path")
    require(offline.is_relative_to(project) and offline.is_dir(), "offline gate path")
    require(not output.exists() and output.parent.resolve().is_relative_to(project), "new package output required")
    freeze = strict_json(freeze_path.read_bytes(), limit=256 << 20)
    offline_paths = {
        (path.relative_to(project)).as_posix()
        for path in offline.iterdir()
        if path.is_file()
    }
    require(offline_paths == {
        (offline / name).relative_to(project).as_posix()
        for name in ("checksums.json", "dry-run.json", "execution-readiness.json", "source-manifest.json")
    }, "offline gate members")
    seeds = set(SEEDS) | _freeze_sources(freeze) | {freeze_path.relative_to(project).as_posix()} | offline_paths
    paths = dependency_closed_paths(project, seeds)
    manifest = source_manifest(project, paths)

    output.mkdir()
    publish_json(output / "source-manifest.json", manifest)
    closure = audit_manifest(project, output / "source-manifest.json")
    require(closure["complete"], "package dependency closure")
    publish_json(output / "dependency-closure.json", closure)
    bundle = output / "package.zip"
    write_zip(project, paths, bundle)

    with tempfile.TemporaryDirectory(prefix="cm-p7-package-") as temporary:
        isolated = Path(temporary)
        with zipfile.ZipFile(bundle) as archive:
            require(archive.namelist() == paths, "package ZIP member order/coverage")
            archive.extractall(isolated)
        tests = _bounded_command(
            [sys.executable, "-m", "pytest", "-q", *FOCUSED_TESTS,
             "-p", "no:cacheprovider", "--basetemp", str(isolated / "pytest-temp")],
            cwd=isolated,
            timeout=180,
        )
        offline_verify = _bounded_command(
            [sys.executable, "scripts/cm_comparative_p7_offline_gate.py", "verify",
             "--project-root", str(isolated), "--freeze", str(isolated / freeze_path.relative_to(project)),
             "--output", str(isolated / offline.relative_to(project))],
            cwd=isolated,
            timeout=180,
        )
    (output / "isolated-tests.stdout.txt").write_bytes(tests.pop("stdout"))
    (output / "isolated-tests.stderr.txt").write_bytes(tests.pop("stderr"))
    (output / "offline-verify.stdout.txt").write_bytes(offline_verify.pop("stdout"))
    (output / "offline-verify.stderr.txt").write_bytes(offline_verify.pop("stderr"))
    verification = {
        "schema": SCHEMA,
        "manifest_sha256": manifest["manifest_sha256"],
        "bundle_sha256": sha256(bundle),
        "bundle_bytes": bundle.stat().st_size,
        "source_files": manifest["file_count"],
        "source_bytes": manifest["bytes"],
        "dependency_closure_complete": closure["complete"],
        "isolated_tests": tests,
        "offline_gate_verification": offline_verify,
        "performance_measurement": False,
        "verified": tests["returncode"] == 0 and offline_verify["returncode"] == 0,
    }
    require(verification["verified"], "isolated package verification failed")
    publish_json(output / "verification.json", verification)
    publish_json(output / "checksums.json", _checksums(output))
    print(json.dumps(verification, indent=2, sort_keys=True))
    return 0


def verify(args) -> int:
    project = args.project_root.resolve()
    output = args.output.resolve()
    manifest = strict_json((output / "source-manifest.json").read_bytes(), limit=64 << 20)
    core = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    manifest_ok = manifest.get("manifest_sha256") == hashlib.sha256(canonical_bytes(core)).hexdigest()
    files_ok = all(
        (project / row["source"]).is_file()
        and (project / row["source"]).stat().st_size == row["bytes"]
        and sha256(project / row["source"]) == row["sha256"]
        for row in manifest.get("files", [])
    )
    closure = audit_manifest(project, output / "source-manifest.json")
    saved = strict_json((output / "verification.json").read_bytes(), limit=1 << 20)
    checksums = strict_json((output / "checksums.json").read_bytes(), limit=1 << 20)
    checksum_ok = all(
        set(row) == {"path", "bytes", "sha256"}
        and len(PurePosixPath(row["path"]).parts) == 1
        and (output / row["path"]).is_file()
        and (output / row["path"]).stat().st_size == row["bytes"]
        and sha256(output / row["path"]) == row["sha256"]
        for row in checksums.get("files", [])
    )
    result = {
        "schema": "cm-comparative-p7-runner-package-verification/v1",
        "manifest_verified": manifest_ok,
        "source_files_verified": files_ok,
        "dependency_closure_complete": closure["complete"],
        "bundle_sha256_matches": sha256(output / "package.zip") == saved["bundle_sha256"],
        "checksums_verified": checksum_ok,
        "saved_verification_passed": saved.get("verified") is True,
        "performance_measurement": False,
    }
    result["verified"] = all(value for key, value in result.items()
                             if key not in {"schema", "performance_measurement"})
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verified"] else 1


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    sub = value.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--project-root", type=Path, required=True)
    build_parser.add_argument("--freeze", type=Path, required=True)
    build_parser.add_argument("--offline-gate", type=Path, required=True)
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.set_defaults(func=build)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--project-root", type=Path, required=True)
    verify_parser.add_argument("--output", type=Path, required=True)
    verify_parser.set_defaults(func=verify)
    return value


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, FileNotFoundError, subprocess.TimeoutExpired, ValueError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
