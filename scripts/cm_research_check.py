"""Credential-free focused checks for current research code and a frozen ZIP.

No installs, Git writes, cloud calls, benchmarks or publication. Archive
identity is verified before extraction or execution of its focused tests.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = Path("docs/research/downloads/CM-Research-2026-08-28.zip")
MANIFEST = Path("docs/research/SOURCE-SHA256.json")
ARCHIVE_SHA256 = "7e542350d13c25a81266fad8d581eb007b24367fc7f3c4b985195e02ed07369e"
SOURCE_COMMIT = "cc0e6f1721c8038573b210ced933ebbac6d68932"
BASE_SUITES = ("*website.py", "test_cm_website_navigation.py", "test_cm_research_publication.py",
               "test_cm_runpod_*.py", "test_cm_measurement_verify.py")
CURRENT_SUITES = (*BASE_SUITES, "test_cm_measurement_protocol.py", "test_cm_research_check.py",
                  "test_cm_process_supervisor.py", "test_cm_native_contracts.py", "test_cm_session_contracts.py")
SUITE_COUNTS = ("tests", "failures", "errors", "skipped", "expected_failures", "unexpected_successes")
MAX_EXPANSION = 128 << 20
MAX_MEMBER = 48 << 20
MAX_FILES = 10000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_member(name):
    path = PurePosixPath(name)
    require(name and not path.is_absolute() and "\\" not in name and path.as_posix() == name,
            "noncanonical archive path")
    for part in path.parts:
        require(part not in (".", "..") and not part.endswith((".", " ")) and
                not re.search(r'[<>:"|?*\x00-\x1f]', part), "unsafe archive path")
        require(not re.fullmatch(r"(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part),
                "reserved Windows archive name")
    return path


def archive_manifest(archive):
    """Reject ambiguous paths and oversized members before extraction."""
    members = archive.infolist()
    require(members and len(members) <= MAX_FILES, "archive member count")
    require(sum(item.file_size for item in members) <= MAX_EXPANSION, "archive expansion limit")
    names, prefixes, files = set(), set(), {}
    for item in members:
        name = item.filename[:-1] if item.is_dir() else item.filename
        path = safe_member(name)
        require(name.casefold() not in names, "duplicate/case-colliding archive path")
        names.add(name.casefold())
        mode = (item.external_attr >> 16) & 0o170000
        require(mode in (0, 0o040000, 0o100000), "nonregular archive member")
        require(not item.flag_bits & 1 and item.file_size <= MAX_MEMBER, "encrypted/oversized archive member")
        prefixes.add(path.parts[0])
        if not item.is_dir():
            require(len(path.parts) > 1, "unprefixed archive file")
            files[PurePosixPath(*path.parts[1:]).as_posix()] = item
    require(len(prefixes) == 1, "multiple archive roots")
    prefix = next(iter(prefixes))
    file_names = {name.casefold() for name in files}
    for name in files:
        require(not any(parent.as_posix().casefold() in file_names
                        for parent in PurePosixPath(name).parents), "archive file/directory collision")
    require(MANIFEST.as_posix() in files, "missing source manifest")
    manifest = json.loads(archive.read(files[MANIFEST.as_posix()]))
    require(isinstance(manifest, dict) and manifest.get("schema") == "cm-research-source/v1", "manifest schema")
    rows = manifest.get("files")
    require(isinstance(rows, list) and 0 < len(rows) < MAX_FILES, "manifest records")
    expected = {}
    for row in rows:
        require(isinstance(row, dict) and set(row) == {"path", "bytes", "sha256"}, "manifest row")
        name = row["path"]
        require(isinstance(name, str), "manifest path type")
        safe_member(name)
        require(name not in expected and name != MANIFEST.as_posix(), "duplicate/self manifest row")
        require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_MEMBER, "manifest byte count")
        require(isinstance(row["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]), "manifest SHA-256")
        expected[name] = row
    require(set(files) == set(expected) | {MANIFEST.as_posix()}, "archive membership mismatch")
    return prefix, files, expected


def verified_zip(path, expected_sha256=ARCHIVE_SHA256, source_commit=SOURCE_COMMIT):
    require(not path.is_symlink() and path.is_file(), "archive missing/linked")
    require(not any(p.is_symlink() or p.is_junction() for p in path.parents), "linked archive parent")
    with path.open("rb") as handle:
        payload = handle.read(MAX_MEMBER + 1)
    require(len(payload) <= MAX_MEMBER, "archive byte limit")
    actual = hashlib.sha256(payload).hexdigest()
    require(actual == expected_sha256, "frozen archive SHA-256 changed")
    # Import only the current publication scanner, not code from the archive.
    sys.path.insert(0, str(ROOT))
    from scripts.cm_research_publication import scan_bytes
    archive = zipfile.ZipFile(io.BytesIO(payload))
    try:
        require(archive.comment.decode("ascii") == source_commit, "archive source commit mismatch")
        prefix, files, expected = archive_manifest(archive)
        for name, item in files.items():
            data = archive.read(item)
            if name in expected:
                row = expected[name]
                require(len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
                        "archive file checksum mismatch: " + name)
            scan_bytes(name, data)
    except BaseException:
        archive.close()
        raise
    return archive, {"source_commit": source_commit, "sha256": actual, "bytes": len(payload),
                     "source_files": len(expected), "total_files": len(files), "prefix": prefix}


def verify_archive(path, expected_sha256=ARCHIVE_SHA256, source_commit=SOURCE_COMMIT):
    archive, identity = verified_zip(path, expected_sha256, source_commit)
    archive.close()
    return identity


def extract_verified(path, destination):
    require(not destination.exists(), "extraction destination must be new")
    archive, identity = verified_zip(path)
    with archive:
        destination.mkdir(parents=True)
        # Extract the same immutable bytes whose identity was verified above.
        prefix, files, _expected = archive_manifest(archive)
        for name, item in files.items():
            target = destination / prefix / name
            require(target.resolve().is_relative_to(destination.resolve()), "extraction escaped root")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as output:
                output.write(archive.read(item))
    return destination / identity["prefix"]


def offline_guard(event, _args):
    # Defense in depth for the test interpreter, not an OS/network sandbox
    # and not a claim that audit hooks propagate into child interpreters.
    if event in {"socket.connect", "socket.connect_ex", "socket.bind", "socket.getaddrinfo"}:
        raise RuntimeError("network operations are disabled in research checks")


def suite_worker(root, pattern):
    require(pattern in CURRENT_SUITES, "suite not allowlisted")
    sys.path.insert(0, str(root))
    sys.addaudithook(offline_guard)
    suite = unittest.defaultTestLoader.discover(str(root / "tests"), pattern=pattern)
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
    return {"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
            "skipped": len(result.skipped), "expected_failures": len(result.expectedFailures),
            "unexpected_successes": len(result.unexpectedSuccesses)}


def successful_suite(result):
    return (isinstance(result, dict) and set(result) == set(SUITE_COUNTS)
            and all(type(result.get(k)) is int and result[k] >= 0 for k in SUITE_COUNTS)
            and result["tests"] > 0 and all(result[k] == 0 for k in SUITE_COUNTS[1:]))


def run_suite(root, pattern):
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--suite", pattern, "--suite-root", str(root)]
    try:
        proc = subprocess.run(command, cwd=root, capture_output=True, timeout=120, check=False)
        counts = json.loads(proc.stdout)
        require(isinstance(counts, dict) and set(counts) == set(SUITE_COUNTS), "suite count schema")
        passed = proc.returncode == 0 and successful_suite(counts)
        row = {"suite": pattern, "status": "passed" if passed else "failed", **counts}
        if not passed:
            row["diagnostic"] = proc.stderr.decode("utf-8", errors="replace")[-4000:]
        return row
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired) as exc:
        return {"suite": pattern, "status": "failed", "reason": type(exc).__name__}


def check_readers(root):
    proc = subprocess.run([sys.executable, "-B", str(root / "scripts/cm_research_publication.py"),
                           "readers", "--check"], cwd=root, capture_output=True, timeout=30, check=False)
    require(proc.returncode == 0, "generated readers are stale or unavailable")
    require(json.loads(proc.stdout) == {"readers": 6, "checked": True}, "reader check response")
    return {"status": "passed", "readers": 6}


def environment():
    node = shutil.which("node")
    require(node is not None, "Node is required; JavaScript syntax checks must not silently skip")
    version = subprocess.check_output([node, "--version"], timeout=10, text=True).strip()
    return {"python": sys.version, "platform": platform.platform(), "node": version,
            "dependencies": {name: importlib.metadata.version(name) for name in
                             ("numpy", "requests", "certifi", "charset-normalizer", "idna", "urllib3")}}


def current_sources():
    # A named test/harness identity, not a claim to snapshot every dependency
    # or historical dataset. The frozen download has its separate full manifest.
    paths = {"scripts/cm_research_check.py", "scripts/cm_research_publication.py",
             "scripts/cm_measurement_verify.py", "scripts/cm_process_supervisor.py",
             "scripts/cm_native_contracts.py", "scripts/cm_session_contracts.py", "requirements-research-ci.txt",
             ".github/workflows/research-checks.yml"}
    for pattern in CURRENT_SUITES:
        paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / "tests").glob(pattern))
    result = {}
    for name in sorted(paths):
        path = ROOT / name
        require(not any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)), "linked check source")
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def check():
    before = current_sources()
    report = {"schema": "cm-research-check/v1", "environment": environment(),
              "archive_identity": verify_archive(ROOT / ARCHIVE), "current_readers": check_readers(ROOT),
              "current_suites": [], "snapshot_suites": [], "cloud_workload_started": False,
              "full_regression": False, "performance_measurement": False,
              "current_test_harness_sha256": before}
    for pattern in CURRENT_SUITES:
        row = run_suite(ROOT, pattern)
        report["current_suites"].append(row)
        print(json.dumps({"scope": "current", **row}), flush=True)
    with tempfile.TemporaryDirectory(prefix="cm-research-check-") as temporary:
        extracted = extract_verified(ROOT / ARCHIVE, Path(temporary) / "extracted")
        report["snapshot_readers"] = check_readers(extracted)
        for pattern in BASE_SUITES:
            row = run_suite(extracted, pattern)
            report["snapshot_suites"].append(row)
            print(json.dumps({"scope": "frozen_snapshot", **row}), flush=True)
    after = current_sources()
    report["changed_test_harness_files"] = sorted(name for name in set(before) | set(after) if before.get(name) != after.get(name))
    report["status"] = "passed" if not report["changed_test_harness_files"] and all(
        row["status"] == "passed" for row in report["current_suites"] + report["snapshot_suites"]) else "failed"
    return report


def report_target(path):
    target = path.absolute()
    roots = ((ROOT / "tmp").resolve(), (ROOT / "docs/research/verification").resolve())
    require(target.suffix == ".json" and any(target.resolve().is_relative_to(root) for root in roots),
            "report must be under project tmp or research verification")
    require(not target.exists(), "report already exists")
    require(not any(p.is_symlink() or p.is_junction() for p in (target, *target.parents)), "linked report path")
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--suite", choices=CURRENT_SUITES, help=argparse.SUPPRESS)
    parser.add_argument("--suite-root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.suite:
        result = suite_worker(args.suite_root.resolve(), args.suite)
        print(json.dumps(result))
        return 0 if successful_suite(result) else 1
    target = report_target(args.report) if args.report else None
    result = check()
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, allow_nan=False)
            handle.write("\n")
    print(json.dumps({"status": result["status"], "current_tests": sum(r.get("tests", 0) for r in result["current_suites"]),
                      "snapshot_tests": sum(r.get("tests", 0) for r in result["snapshot_suites"]),
                      "report": str(target) if target else None}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
