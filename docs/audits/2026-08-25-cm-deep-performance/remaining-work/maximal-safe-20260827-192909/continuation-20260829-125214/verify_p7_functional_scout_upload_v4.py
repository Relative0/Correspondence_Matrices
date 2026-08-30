"""Verify the dependency-closed upload as an isolated source tree."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V4-20260830.json"
BUNDLE = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V4-20260830.zip"
RESULT = HERE / "P7-FUNCTIONAL-SCOUT-UPLOAD-V4-LOCAL-GATE-20260830.json"
JUNIT = HERE / "P7-FUNCTIONAL-SCOUT-UPLOAD-V4-LOCAL-GATE-20260830.xml"
TESTS = [
    "tests/test_cm_comparative_p7.py",
    "tests/test_cm_comparative_p7_runner.py",
    "tests/test_cm_comparative_corpus_freeze.py",
    "tests/test_blif_recognition.py",
    "tests/test_cm_comparative_linux_supervisor.py",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = {row["target"]: row for row in manifest["files"]}
    with zipfile.ZipFile(BUNDLE) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise RuntimeError("bundle membership mismatch")
        for name in names:
            payload = archive.read(name)
            row = expected[name]
            if len(payload) != row["bytes"] or digest(payload) != row["sha256"]:
                raise RuntimeError(f"bundle member mismatch: {name}")
        with tempfile.TemporaryDirectory(prefix="cm-p7-upload-v2-") as temporary:
            root = Path(temporary)
            archive.extractall(root)
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(root)
            environment["PYTHONNOUSERSITE"] = "1"
            command = [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "-q",
                "--disable-warnings",
                "--basetemp",
                str(root / "pytest-temp"),
                "--junitxml",
                str(JUNIT),
                *TESTS,
            ]
            completed = subprocess.run(
                command,
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
    result = {
        "schema": "cm-p7-functional-scout-upload-v4-local-gate/v1",
        "isolated_source_tree": True,
        "manifest_sha256": digest(MANIFEST.read_bytes()),
        "bundle_sha256": digest(BUNDLE.read_bytes()),
        "bundle_bytes": BUNDLE.stat().st_size,
        "source_files": len(expected),
        "source_bytes": sum(row["bytes"] for row in expected.values()),
        "tests": TESTS,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "junit_sha256": digest(JUNIT.read_bytes()) if JUNIT.exists() else None,
        "passed": completed.returncode == 0,
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))
    if completed.returncode:
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
