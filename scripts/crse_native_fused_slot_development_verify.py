"""Independently verify one native fused-slot development run."""
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
    "projection_u16_tuple",
    "native_fused_slots",
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


def project_path(relative: str) -> Path:
    path = ROOT.joinpath(*Path(relative).parts).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError("verifier path escaped or is missing")
    return path


def write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    if not run_dir.is_relative_to(ROOT.resolve()) or not run_dir.is_dir():
        raise ValueError("run directory escaped the project")
    manifest = load(run_dir / "manifest.json")
    results = load(run_dir / "results.json")
    dataset = load(project_path(results["dataset"]["path"]))

    artifact_mismatches = sum(
        not (run_dir / name).is_file()
        or (run_dir / name).stat().st_size != identity["bytes"]
        or sha256(run_dir / name) != identity["sha256"]
        for name, identity in manifest["artifacts"].items()
    )
    source_mismatches = sum(
        project_path(relative).stat().st_size != identity["bytes"]
        or sha256(project_path(relative)) != identity["sha256"]
        for relative, identity in manifest["sources"].items()
    )
    native_path = project_path(manifest["native_library"]["path"])
    native_mismatches = int(
        native_path.stat().st_size != manifest["native_library"]["bytes"]
        or sha256(native_path) != manifest["native_library"]["sha256"]
        or manifest["native_library"]["abi_version"] != 1)

    expected: dict[str, str] = {}
    oracle_mismatches = 0
    for case in dataset["cases"]:
        trace = independent_trace(case["case_id"], case["n_vars"])
        oracle_mismatches += int(trace != case["c36_trace"])
        expected[case["case_id"]] = digest(independent_output(case, trace))
        oracle_mismatches += int(
            expected[case["case_id"]] != case["c36_required_output_sha256"])

    raw = [json.loads(line) for line in
           (run_dir / "raw_measurements.jsonl").read_text(encoding="utf-8").splitlines()
           if line.strip()]
    performance = [row for row in raw if row.get("role") == "performance"]
    memory = [row for row in raw if row.get("role") == "memory_profile"]
    structure_mismatches = int(
        len(performance) != results["config"]["blocks"] * 18 * len(METHODS)
        or len(memory) != 18 * len(METHODS)
        or tuple(results["methods"]) != METHODS)
    correctness_mismatches = 0
    native_identity_mismatches = 0
    for row in raw:
        correctness_mismatches += int(
            row.get("schema") != "crse-native-fused-slot-raw-session/v1"
            or row.get("status") != "ok"
            or row.get("method") not in METHODS
            or row.get("exact_check_passed") is not True
            or row.get("output_sha256") != expected.get(row.get("case_id"))
            or len(row.get("query_measurements", [])) != 64)
        if row.get("method") == "native_fused_slots":
            native_identity_mismatches += int(
                row["resources"].get("native_library_sha256") != sha256(native_path)
                or row["resources"].get("native_abi_version") != 1)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in performance:
        grouped[(row["case_id"], row["method"])].append(row)
    medians: dict[tuple[str, str], dict[str, int]] = {}
    balance_mismatches = 0
    for case in dataset["cases"]:
        for method in METHODS:
            sessions = grouped[(case["case_id"], method)]
            balance_mismatches += int(
                len(sessions) != results["config"]["blocks"]
                or Counter(row["method_position"] for row in sessions)
                != Counter({0: 2, 1: 2, 2: 2}))
            medians[(case["case_id"], method)] = {
                stage: int(statistics.median_low(
                    row["timings_ns"][stage] for row in sessions))
                for stage in STAGES
            }
    aggregate_mismatches = 0
    published = results["summary"]["aggregate_case_median_stage_ns"]
    for method in METHODS:
        for stage in STAGES:
            actual = sum(medians[(case["case_id"], method)][stage]
                         for case in dataset["cases"])
            aggregate_mismatches += int(actual != published[method][stage])

    failures = {
        "artifact_mismatches": artifact_mismatches,
        "source_mismatches": source_mismatches,
        "native_mismatches": native_mismatches,
        "oracle_mismatches": oracle_mismatches,
        "structure_mismatches": structure_mismatches,
        "correctness_mismatches": correctness_mismatches,
        "native_identity_mismatches": native_identity_mismatches,
        "balance_mismatches": balance_mismatches,
        "aggregate_mismatches": aggregate_mismatches,
    }
    if any(failures.values()):
        raise RuntimeError(f"native fused-slot verification failed: {failures}")
    verification = {
        "schema": "crse-native-fused-slot-independent-verification/v1",
        "status": "verified",
        "run_id": results["run_id"],
        "performance_sessions": len(performance),
        "memory_profile_sessions": len(memory),
        "queries_replayed_independently": 18 * 64,
        "raw_query_rows_checked": len(raw) * 64,
        "native_library_sha256": sha256(native_path),
        "results_sha256": sha256(run_dir / "results.json"),
        "manifest_sha256": sha256(run_dir / "manifest.json"),
        **failures,
    }
    write_new(run_dir / "independent_verification.json", verification)
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
