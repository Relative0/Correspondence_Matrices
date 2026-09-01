"""Run two more unchanged C27 Linux Docker repetitions and summarize stability."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
HERE = DOCS / "c27_linux_confirmation"
MANIFEST = HERE / "c27_linux_upload_manifest.json"
BASE = HERE / "c27-docker-linux-portability-001"
RUNNER_PATH = ROOT / "scripts/crse_run_c27_docker_portability.py"
OUTPUT = HERE / "C27_DOCKER_LINUX_REPEATABILITY_20260901.json"

spec = importlib.util.spec_from_file_location("c27_docker_runner", RUNNER_PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def surface(result: dict) -> dict:
    summary = result["summary"]
    return {
        "gate": summary["support_aware_confirmation_gate"],
        "break_even_query_count": summary["support_aware_break_even_query_count"],
        "by_query_count": {
            count: {
                "aggregate": values["methods"]["support_aware_c27_advice_on"][
                    "aggregate_speedup_over_direct_screened"],
                "minimum_width": values["methods"]["support_aware_c27_advice_on"][
                    "minimum_width_speedup_over_direct_screened"],
            }
            for count, values in summary["by_query_count"].items()
        },
    }


def validate_result(run_dir: Path) -> tuple[dict, dict]:
    result = load(run_dir / "results.json")
    verification = load(run_dir / "independent_verification.json")
    if (
        result.get("status") != "complete"
        or result.get("measurement_batches") != 720
        or result.get("timed_queries") != 7560
        or result.get("memory_measurement_batches") != 24
        or result.get("semantic_or_artifact_mismatches") != 0
        or verification.get("status") != "verified"
        or verification.get("measurement_batches_checked") != 720
        or verification.get("timed_query_records_checked") != 7560
        or verification.get("summary_recomputed") is not True
        or verification.get("semantic_or_artifact_mismatches") != 0
    ):
        raise ValueError("C27 Docker repetition invariant mismatch")
    return result, verification


def run_repetition(index: int, manifest: dict) -> dict:
    directory = HERE / f"c27-docker-linux-portability-{index:03d}"
    if directory.exists():
        raise SystemExit(f"refusing to overwrite C27 Docker repetition {index:03d}")
    results = directory / "results"
    results.mkdir(parents=True)
    runner.RESULTS = results
    command_records = []
    for manifest_command, timeout in zip(manifest["commands"], [420, 180], strict=True):
        actual = ["python", *manifest_command[1:]]
        completed = runner.run(
            runner.docker_prefix() + ["sh", "-ec", runner.shell_command(actual)],
            timeout)
        command_records.append({
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
                f"C27 Docker repetition {index:03d} failed: "
                + completed["stderr"][-2000:])
    run_dir = results / manifest["run_name"]
    result, verification = validate_result(run_dir)
    output_files = [path for path in results.rglob("*") if path.is_file()]
    output_bytes = sum(path.stat().st_size for path in output_files)
    if output_bytes > manifest["result_cap_bytes"]:
        raise ValueError("C27 Docker repetition result cap exceeded")
    record = {
        "schema": "crse-c27-docker-linux-portability-repetition/v1",
        "status": "pass",
        "repetition": index,
        "scientific_scope": "same-host Linux timing repetition; not second-machine",
        "manifest_sha256": sha256(MANIFEST),
        "frozen_source_execution_sha256": sha256(BASE / "EXECUTION.json"),
        "network_during_workload": False,
        "container_root_read_only": True,
        "commands": command_records,
        "measurement_batches": 720,
        "timed_queries": 7560,
        "semantic_or_artifact_mismatches": 0,
        "independent_verification": verification["status"],
        "timing": surface(result),
        "result_files": len(output_files),
        "result_bytes": output_bytes,
        "results_sha256": sha256(run_dir / "results.json"),
        "independent_verification_sha256": sha256(
            run_dir / "independent_verification.json"),
        "training": False,
        "production_write": False,
    }
    (directory / "EXECUTION.json").write_bytes(json.dumps(
        record, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    return record


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 Docker repeatability record")
    manifest = load(MANIFEST)
    first_execution = load(BASE / "EXECUTION.json")
    first_result, _ = validate_result(
        BASE / "results" / manifest["run_name"])
    if (
        first_execution.get("status") != "pass"
        or first_execution.get("manifest_sha256") != sha256(MANIFEST)
        or first_execution.get("network_during_workload") is not False
    ):
        raise ValueError("C27 first Docker execution mismatch")
    runner.FROZEN = BASE / "frozen"
    for row in manifest["files"]:
        frozen = runner.FROZEN / row["target"]
        if frozen.stat().st_size != row["bytes"] or sha256(frozen) != row["sha256"]:
            raise ValueError(f"C27 Docker frozen source changed: {row['target']}")
    repetitions = [
        {"repetition": 1, "timing": surface(first_result),
         "execution_sha256": sha256(BASE / "EXECUTION.json")},
        run_repetition(2, manifest),
        run_repetition(3, manifest),
    ]
    surfaces = [row["timing"] for row in repetitions]
    result = {
        "schema": "crse-c27-docker-linux-repeatability/v1",
        "status": "complete",
        "scientific_scope": "three same-host Linux Docker timings; not second-machine",
        "manifest_sha256": sha256(MANIFEST),
        "runtime": first_execution["runtime"],
        "repetitions": repetitions,
        "repetition_count": 3,
        "timing_gate_passes": sum(item["gate"] is True for item in surfaces),
        "break_even_query_counts": [item["break_even_query_count"] for item in surfaces],
        "all_exact": True,
        "semantic_or_artifact_mismatches": 0,
        "network_during_workload": False,
        "second_machine_replication": False,
        "production_promotion": False,
        "training": False,
        "production_write": False,
    }
    OUTPUT.write_bytes(json.dumps(
        result, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "status": result["status"],
        "repetition_count": 3,
        "timing_gate_passes": result["timing_gate_passes"],
        "break_even_query_counts": result["break_even_query_counts"],
        "semantic_or_artifact_mismatches": 0,
        "second_machine_replication": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
