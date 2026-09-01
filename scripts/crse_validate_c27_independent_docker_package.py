"""Extract and execute the exact C27 independent Docker package locally."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c27_independent_docker_confirmation"
ARCHIVE = HERE / "c27-independent-docker-package.tar.gz"
OUTER_MANIFEST = HERE / "c27_independent_docker_package_manifest.json"
VALIDATION_ROOT = HERE / "c27-independent-docker-local-validation-001"
OUTPUT = HERE / "C27_INDEPENDENT_DOCKER_PACKAGE_LOCAL_VALIDATION_20260901.json"
GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if VALIDATION_ROOT.exists() or OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 independent Docker validation")
    if not GIT_BASH.is_file():
        raise SystemExit("Git Bash is required for local package validation")
    outer = load(OUTER_MANIFEST)
    if (
        outer.get("status") != "frozen"
        or outer.get("source_files") != 63
        or outer.get("source_bytes") != 1078671
        or outer.get("package_files") != 70
        or outer.get("archive_bytes") != ARCHIVE.stat().st_size
        or outer.get("archive_sha256") != sha256(ARCHIVE)
        or outer.get("network_during_workload") is not False
        or outer.get("credentials_included") is not False
    ):
        raise ValueError("C27 independent Docker outer manifest mismatch")
    VALIDATION_ROOT.mkdir(parents=True)
    with tarfile.open(ARCHIVE, "r:gz") as archive:
        archive.extractall(VALIDATION_ROOT, filter="data")
    package = VALIDATION_ROOT / "c27-independent-docker-package"
    embedded_path = package / "PACKAGE-MANIFEST.json"
    if sha256(embedded_path) != outer["embedded_manifest_sha256"]:
        raise ValueError("C27 embedded package manifest hash mismatch")
    embedded = load(embedded_path)
    for row in embedded["files"]:
        path = package / row["path"]
        if path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            raise ValueError(f"C27 independent package file mismatch: {row['path']}")
    observed = [path for path in package.rglob("*") if path.is_file()]
    if len(observed) != outer["package_files"]:
        raise ValueError("C27 extracted package file count mismatch")
    environment = os.environ.copy()
    environment["MSYS_NO_PATHCONV"] = "1"
    started = time.perf_counter()
    completed = subprocess.run(
        [str(GIT_BASH), "-lc", "./run_c27.sh same-host"],
        cwd=package, env=environment, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
    wall = time.perf_counter() - started
    if completed.returncode != 0:
        raise ValueError("C27 independent Docker launcher failed: " + completed.stderr[-3000:])
    summary = load(package / "results/PORTABILITY-SUMMARY.json")
    result_archive = package / "c27-results.tar.gz"
    if (
        summary.get("status") != "verified"
        or summary.get("evidence_scope") != "same-host"
        or summary.get("second_machine_replication") is not False
        or summary.get("measurement_batches") != 720
        or summary.get("timed_queries") != 7560
        or summary.get("memory_batches") != 24
        or summary.get("semantic_or_artifact_mismatches") != 0
        or summary.get("independent_verification") != "verified"
        or type(summary.get("support_aware_confirmation_gate")) is not bool
        or summary.get("network_during_workload") is not False
        or summary.get("production_promotion") is not False
        or result_archive.stat().st_size > outer["result_cap_bytes"]
    ):
        raise ValueError("C27 independent Docker local result mismatch")
    record = {
        "schema": "crse-c27-independent-docker-package-local-validation/v1",
        "status": "pass",
        "scientific_scope": "same-host package validation; not second-machine",
        "archive_sha256": sha256(ARCHIVE),
        "archive_bytes": ARCHIVE.stat().st_size,
        "outer_manifest_sha256": sha256(OUTER_MANIFEST),
        "embedded_manifest_sha256": sha256(embedded_path),
        "package_files": len(observed),
        "source_files": 63,
        "source_bytes": 1078671,
        "launcher_returncode": completed.returncode,
        "launcher_wall_seconds": wall,
        "launcher_stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "launcher_stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
        "launcher_stdout_bytes": len(completed.stdout.encode()),
        "launcher_stderr_bytes": len(completed.stderr.encode()),
        "result_archive_sha256": sha256(result_archive),
        "result_archive_bytes": result_archive.stat().st_size,
        "result_cap_bytes": outer["result_cap_bytes"],
        "result_summary": summary,
        "network_during_workload": False,
        "second_machine_replication": False,
        "credentials_included": False,
        "training": False,
        "production_write": False,
        "production_promotion": False,
    }
    OUTPUT.write_bytes(json.dumps(
        record, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "status": "pass", "package_files": len(observed),
        "archive_bytes": ARCHIVE.stat().st_size,
        "result_archive_bytes": result_archive.stat().st_size,
        "timing_gate": summary["support_aware_confirmation_gate"],
        "break_even": summary["support_aware_break_even_query_count"],
        "semantic_or_artifact_mismatches": 0,
        "second_machine_replication": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
