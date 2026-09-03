"""Independently verify one projection-optimization development run."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.contracts import canonical_bytes
from scripts.crse_verify_c36_wide_repeated_query_dataset import (
    independent_output,
    independent_trace,
)


METHODS = (
    "restricted_r2_reference",
    "projection_u32_control",
    "projection_u16_tuple",
    "projection_u16_flat",
    "projection_packed_cofactor",
)
STAGES = (
    "input_decode_ns", "representation_ns", "restriction_setup_ns",
    "evaluation_ns", "delivery_ns", "query_total_ns", "cleanup_ns",
    "accounted_total_ns",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def project_path(relative: str) -> Path:
    path = ROOT.joinpath(*Path(relative).parts).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError("verifier source path escaped or is missing")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    if not run_dir.is_relative_to(ROOT.resolve()) or not run_dir.is_dir():
        raise ValueError("run directory escaped the project")
    manifest = load(run_dir / "manifest.json")
    results = load(run_dir / "results.json")
    dataset_path = project_path(results["dataset"]["path"])
    dataset = load(dataset_path)

    artifact_mismatches = 0
    for name, identity in manifest["artifacts"].items():
        path = run_dir / name
        artifact_mismatches += int(
            not path.is_file()
            or path.stat().st_size != identity["bytes"]
            or sha256(path) != identity["sha256"])
    source_mismatches = 0
    for relative, identity in manifest["sources"].items():
        path = project_path(relative)
        source_mismatches += int(
            path.stat().st_size != identity["bytes"]
            or sha256(path) != identity["sha256"])

    oracle_mismatches = 0
    expected_digests: dict[str, str] = {}
    for case in dataset["cases"]:
        trace = independent_trace(case["case_id"], case["n_vars"])
        oracle_mismatches += int(trace != case["c36_trace"])
        expected = digest(independent_output(case, trace))
        expected_digests[case["case_id"]] = expected
        oracle_mismatches += int(expected != case["c36_required_output_sha256"])

    raw = [json.loads(line) for line in
           (run_dir / "raw_measurements.jsonl").read_text(encoding="utf-8").splitlines()
           if line.strip()]
    performance = [row for row in raw if row.get("role") == "performance"]
    memory = [row for row in raw if row.get("role") == "memory_profile"]
    expected_performance = results["config"]["blocks"] * 18 * len(METHODS)
    structure_mismatches = int(
        len(performance) != expected_performance
        or len(memory) != 18 * len(METHODS)
        or set(results["methods"]) != set(METHODS))
    correctness_mismatches = 0
    for row in raw:
        correctness_mismatches += int(
            row.get("schema") != "crse-projection-optimization-raw-session/v1"
            or row.get("status") != "ok"
            or row.get("method") not in METHODS
            or row.get("output_sha256") != expected_digests.get(row.get("case_id"))
            or row.get("exact_check_passed") is not True
            or len(row.get("query_measurements", [])) != 64
            or set(row.get("checkpoint_total_ns", {})) != {"1", "4", "16", "64"})

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in performance:
        grouped[(row["case_id"], row["method"])].append(row)
    balance_mismatches = 0
    recomputed: dict[tuple[str, str], dict[str, int]] = {}
    for case in dataset["cases"]:
        case_id = case["case_id"]
        for method in METHODS:
            sessions = grouped[(case_id, method)]
            positions = Counter(row["method_position"] for row in sessions)
            balance_mismatches += int(
                len(sessions) != results["config"]["blocks"]
                or positions != Counter({position: 2 for position in range(len(METHODS))}))
            if sessions:
                recomputed[(case_id, method)] = {
                    stage: int(statistics.median_low(
                        row["timings_ns"][stage] for row in sessions))
                    for stage in STAGES
                }
    aggregate_mismatches = 0
    published = results["summary"]["aggregate_case_median_stage_ns"]
    for method in METHODS:
        for stage in STAGES:
            actual = sum(recomputed[(case["case_id"], method)][stage]
                         for case in dataset["cases"])
            aggregate_mismatches += int(actual != published[method][stage])

    index_memory_mismatches = 0
    resource_rows: dict[tuple[str, str, int | None], dict[str, Any]] = {}
    for row in raw:
        resource_rows[(row["case_id"], row["method"], row.get("block"))] = row
    for case in dataset["cases"]:
        case_id = case["case_id"]
        for block in range(results["config"]["blocks"]):
            u32 = resource_rows[(case_id, "projection_u32_control", block)]["resources"]
            u16 = resource_rows[(case_id, "projection_u16_tuple", block)]["resources"]
            flat = resource_rows[(case_id, "projection_u16_flat", block)]["resources"]
            index_memory_mismatches += int(
                u32["compiled_projection_index_bytes"]
                != 2 * u16["compiled_projection_index_bytes"]
                or u16["compiled_projection_index_bytes"]
                != flat["compiled_projection_index_bytes"]
                or u32["index_arrays"] != 64
                or u16["index_arrays"] != 64
                or flat["index_arrays"] != 1)

    failures = {
        "artifact_mismatches": artifact_mismatches,
        "source_mismatches": source_mismatches,
        "oracle_mismatches": oracle_mismatches,
        "structure_mismatches": structure_mismatches,
        "correctness_mismatches": correctness_mismatches,
        "balance_mismatches": balance_mismatches,
        "aggregate_mismatches": aggregate_mismatches,
        "index_memory_mismatches": index_memory_mismatches,
    }
    if any(failures.values()):
        raise RuntimeError(f"projection optimization verification failed: {failures}")
    verification = {
        "schema": "crse-projection-optimization-independent-verification/v1",
        "status": "verified",
        "run_id": results["run_id"],
        "performance_sessions": len(performance),
        "memory_profile_sessions": len(memory),
        "queries_replayed_independently": 18 * 64,
        "raw_query_rows_checked": len(raw) * 64,
        "results_sha256": sha256(run_dir / "results.json"),
        "manifest_sha256": sha256(run_dir / "manifest.json"),
        **failures,
    }
    write_new(run_dir / "independent_verification.json", verification)
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
