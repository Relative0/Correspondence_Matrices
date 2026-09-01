"""Run the frozen C27 package in a network-disabled local Linux container."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c27_linux_confirmation"
MANIFEST = HERE / "c27_linux_upload_manifest.json"
OUTPUT = HERE / "c27-docker-linux-portability-001"
FROZEN = OUTPUT / "frozen"
RESULTS = OUTPUT / "results"
STAGING = OUTPUT / "STAGING.json"
RECORD = OUTPUT / "EXECUTION.json"
IMAGE = "crse-c27-linux:python3.13.15-numpy2.3.2"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], timeout: int) -> dict:
    started = time.perf_counter()
    completed = subprocess.run(
        command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=timeout)
    return {
        "returncode": completed.returncode,
        "wall_seconds": time.perf_counter() - started,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def docker_prefix() -> list[str]:
    return [
        "docker", "run", "--rm", "--network", "none", "--cpus", "2",
        "--memory", "4g", "--pids-limit", "256", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--env", "PYTHONDONTWRITEBYTECODE=1",
        "--env", "OPENBLAS_NUM_THREADS=1", "--env", "OMP_NUM_THREADS=1",
        "--env", "MKL_NUM_THREADS=1", "--env", "NUMEXPR_NUM_THREADS=1",
        "--mount", f"type=bind,source={FROZEN.resolve()},target=/frozen,readonly",
        "--mount", f"type=bind,source={RESULTS.resolve()},target=/output",
        "--tmpfs", "/work:rw,exec,nosuid,size=268435456",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=67108864",
        IMAGE,
    ]


def shell_command(arguments: list[str]) -> str:
    quoted = " ".join("'" + value.replace("'", "'\\''") + "'" for value in arguments)
    return (
        "cp -a /frozen/. /work/; "
        "ln -s /output /work/run-output; "
        "cd /work; exec " + quoted
    )


def main() -> int:
    if RECORD.exists():
        raise SystemExit("refusing to overwrite C27 Docker execution")
    if any(RESULTS.iterdir()):
        raise SystemExit("refusing nonempty C27 Docker result directory")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    staging = json.loads(STAGING.read_text(encoding="utf-8"))
    if (
        staging.get("status") != "staged"
        or staging.get("manifest_sha256") != sha256(MANIFEST)
        or staging.get("source_files") != 63
        or staging.get("source_bytes") != 1078671
        or staging.get("network_during_workload") is not False
    ):
        raise ValueError("C27 Docker staging mismatch")
    for row in manifest["files"]:
        path = FROZEN / row["target"]
        if path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            raise ValueError(f"C27 Docker frozen source changed: {row['target']}")
    inspected = run([
        "docker", "image", "inspect", IMAGE, "--format",
        "{{json .}}",
    ], 30)
    if inspected["returncode"] != 0:
        raise ValueError("C27 Docker image inspection failed: " + inspected["stderr"])
    image = json.loads(inspected["stdout"])
    probe = run(docker_prefix() + [
        "python", "-B", "-c",
        "import json,numpy,platform; print(json.dumps({"
        "'python':platform.python_version(),'numpy':numpy.__version__,"
        "'system':platform.system(),'machine':platform.machine()}))",
    ], 60)
    if probe["returncode"] != 0:
        raise ValueError("C27 Docker runtime probe failed: " + probe["stderr"])
    runtime = json.loads(probe["stdout"])
    if runtime != {
        "python": "3.13.15", "numpy": "2.3.2",
        "system": "Linux", "machine": "x86_64",
    }:
        raise ValueError("C27 Docker runtime identity mismatch: " + probe["stdout"])
    commands = []
    timeouts = [420, 180]
    for manifest_command, timeout in zip(manifest["commands"], timeouts, strict=True):
        actual = ["python", *manifest_command[1:]]
        completed = run(
            docker_prefix() + ["sh", "-ec", shell_command(actual)], timeout)
        commands.append({
            "command": manifest_command,
            "returncode": completed["returncode"],
            "wall_seconds": completed["wall_seconds"],
            "stdout_sha256": hashlib.sha256(completed["stdout"].encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(completed["stderr"].encode()).hexdigest(),
            "stdout_bytes": len(completed["stdout"].encode()),
            "stderr_bytes": len(completed["stderr"].encode()),
        })
        if completed["returncode"] != 0:
            raise ValueError(
                "C27 Docker command failed: " + completed["stderr"][-2000:])
    run_dir = RESULTS / manifest["run_name"]
    result = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    verification = json.loads(
        (run_dir / "independent_verification.json").read_text(encoding="utf-8"))
    invariants = {
        "result_complete": result.get("status") == "complete",
        "measurement_batches": result.get("measurement_batches") == 720,
        "timed_queries": result.get("timed_queries") == 7560,
        "memory_batches": result.get("memory_measurement_batches") == 24,
        "fallback_controls": result.get("fallback_controls") == 48,
        "selected_path_controls": result.get("selected_path_controls") == 48,
        "refusal_controls": result.get("refusal_controls") == 10,
        "semantic_exactness": result.get("semantic_or_artifact_mismatches") == 0,
        "verification_status": verification.get("status") == "verified",
        "verified_batches": verification.get("measurement_batches_checked") == 720,
        "verified_queries": verification.get("timed_query_records_checked") == 7560,
        "verified_exactness": verification.get("semantic_or_artifact_mismatches") == 0,
    }
    if not all(invariants.values()):
        raise ValueError("C27 Docker scientific invariant failed: " + json.dumps(invariants))
    for row in manifest["files"]:
        path = FROZEN / row["target"]
        if path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            raise ValueError(f"C27 Docker source mutated: {row['target']}")
    output_files = [path for path in RESULTS.rglob("*") if path.is_file()]
    output_bytes = sum(path.stat().st_size for path in output_files)
    if output_bytes > manifest["result_cap_bytes"]:
        raise ValueError("C27 Docker result cap exceeded")
    record = {
        "schema": "crse-c27-docker-linux-portability-execution/v1",
        "status": "pass",
        "scientific_scope": "same-host Linux OS/container portability; not second-machine",
        "manifest_sha256": sha256(MANIFEST),
        "source_files": 63,
        "source_bytes": 1078671,
        "frozen_sources_unchanged_after_run": True,
        "docker_image": IMAGE,
        "docker_image_id": image["Id"],
        "docker_os": image["Os"],
        "docker_architecture": image["Architecture"],
        "runtime": runtime,
        "network_during_workload": False,
        "container_root_read_only": True,
        "vcpu_limit": 2,
        "memory_limit_gb": 4,
        "commands": commands,
        "invariants": invariants,
        "support_aware_confirmation_gate": result["summary"][
            "support_aware_confirmation_gate"],
        "support_aware_break_even_query_count": result["summary"][
            "support_aware_break_even_query_count"],
        "semantic_or_artifact_mismatches": 0,
        "independent_verification": "verified",
        "result_files": len(output_files),
        "result_bytes": output_bytes,
        "result_cap_bytes": manifest["result_cap_bytes"],
        "results_sha256": sha256(run_dir / "results.json"),
        "independent_verification_sha256": sha256(
            run_dir / "independent_verification.json"),
        "training": False,
        "production_write": False,
        "credentials_included": False,
    }
    RECORD.write_bytes(json.dumps(
        record, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "status": "pass", "runtime": runtime,
        "support_aware_confirmation_gate": record["support_aware_confirmation_gate"],
        "break_even": record["support_aware_break_even_query_count"],
        "result_files": record["result_files"],
        "result_bytes": record["result_bytes"],
        "scientific_scope": record["scientific_scope"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
