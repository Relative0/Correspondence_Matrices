"""Run scoped producer/auditor regression checks from a hashed source snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from artifact_audit import BASE, REPO, finalize, require, sha, snapshot, write_json


def run(output: Path, pytest_library: Path) -> int:
    require(not output.exists(), f"refusing to overwrite {output}")
    output.mkdir(parents=True)
    observed = snapshot(output)
    frozen = output / "source_snapshot"
    tests = (
        "tests/conftest.py", "tests/test_cm_feature_model_history_pilot.py",
        "tests/test_cm_feature_model_representation_battery.py", "tests/test_cm_feature_model_version_delta.py",
    )
    extras = tests + ("cmbench/__init__.py", "cmbench/backends/__init__.py", "cmbench/expr/__init__.py", "cm_normalize.py")
    for relative in extras:
        path = REPO / relative
        require(path.is_file(), f"missing scoped regression source: {relative}")
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        require(sha(path) == digest, f"source changed during read: {relative}")
        target = frozen / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        require(not target.exists(), f"unexpected duplicate snapshot path: {target}")
        target.write_bytes(content)
        observed["files"].append({"path": str(path), "relative_path": relative, "sha256": digest,
                                  "bytes": len(content), "mtime_ns": path.stat().st_mtime_ns})
    write_json(output / "source-observed-before.json", observed)
    audit_dir = (BASE / "independence_audit_2026_08_27").relative_to(REPO).as_posix()
    args = ["-q", "-p", "no:cacheprovider", f"--basetemp={output / 'pytest-tmp'}",
            f"--junitxml={output / 'junit.xml'}", *tests[1:], f"{audit_dir}/test_auditors.py"]
    # pytest is pure Python and is already installed globally. Append its site
    # directory after the virtualenv so native NumPy/PySAT still come from venv.
    launcher = (
        f"import sys; sys.path.insert(0, {str(frozen)!r}); sys.path.append({str(pytest_library)!r}); "
        "import pytest,numpy,pysat; "
        "print('pytest',pytest.__version__,pytest.__file__); "
        "print('numpy',numpy.__version__,numpy.__file__); "
        "print('pysat',pysat.__version__,pysat.__file__); "
        f"raise SystemExit(pytest.main({args!r}))"
    )
    environment = dict(os.environ)
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run([sys.executable, "-c", launcher], cwd=frozen, env=environment,
                             capture_output=True, text=True, timeout=300)
    (output / "pytest.log").write_text(process.stdout + process.stderr, encoding="utf-8")
    unchanged = all(sha(frozen / row["relative_path"]) == row["sha256"] for row in observed["files"])
    require(unchanged, "frozen regression source changed")
    result = {"schema": "cm-fm-frozen-regression/v1", "status": "passed" if process.returncode == 0 else "failed",
              "returncode": process.returncode, "python": sys.version, "interpreter": sys.executable,
              "pytest_library_appended": str(pytest_library), "source_snapshot_unchanged": unchanged,
              "scope": "three feature-model producer test files plus the complete independent-auditor tests",
              "full_repository_suite_run": False, "historical_timing_code_reconstructed": False}
    write_json(output / "summary.json", result)
    finalize(output, observed, [])
    print(process.stdout + process.stderr)
    print(json.dumps(result, indent=2))
    return process.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pytest-library", type=Path, required=True)
    arguments = parser.parse_args()
    raise SystemExit(run(arguments.output.resolve(), arguments.pytest_library.resolve()))
