"""Independently verify one native multi-root development run."""
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

from bitset_backend import build_bitset_env, eval_expr_bitset
from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.gf2_multi_root import sibling_output_workloads
from cmbench.comparative.gf2_wide_repeated_queries import restrict_full_truth, semantic_row


METHODS = ("native_separate_roots", "native_union_roots")
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


def independent_digest(workload: Any) -> str:
    names = tuple(f"x{index}" for index in range(workload.n_vars))
    full_truths = tuple(eval_expr_bitset(root, build_bitset_env(names))
                        for root in workload.roots)
    rows = []
    for query in workload.trace:
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        values = tuple(restrict_full_truth(bits, workload.n_vars, fixed)[1]
                       for bits in full_truths)
        rows.append({
            "query": query["query"],
            "query_sha256": query["query_sha256"],
            "outputs": [
                {"output_index": index,
                 "semantic": semantic_row(query, value, workload.n_vars)}
                for index, value in enumerate(values)
            ],
        })
    return digest({
        "schema": "crse-native-multi-root-output/v1",
        "workload_id": workload.workload_id,
        "rows": rows,
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    if not run_dir.is_relative_to(ROOT.resolve()) or not run_dir.is_dir():
        raise ValueError("run directory escaped the project")
    manifest = load(run_dir / "manifest.json")
    results = load(run_dir / "results.json")
    published_workloads = load(run_dir / "workloads.json")

    artifact_mismatches = sum(
        not (run_dir / name).is_file()
        or (run_dir / name).stat().st_size != identity["bytes"]
        or sha256(run_dir / name) != identity["sha256"]
        for name, identity in manifest["artifacts"].items())
    source_mismatches = sum(
        project_path(relative).stat().st_size != identity["bytes"]
        or sha256(project_path(relative)) != identity["sha256"]
        for relative, identity in manifest["sources"].items())

    workloads = sibling_output_workloads()
    expected = {workload.workload_id: independent_digest(workload)
                for workload in workloads}
    workload_mismatches = 0
    published_by_id = {row["workload_id"]: row
                       for row in published_workloads["workloads"]}
    for workload in workloads:
        row = published_by_id.get(workload.workload_id, {})
        separate_nodes = sum(len(document["nodes"])
                             for document in workload.separate_documents)
        union_nodes = len(workload.union_document["nodes"])
        workload_mismatches += int(
            row.get("union_document") != workload.union_document
            or row.get("required_output_sha256") != expected[workload.workload_id]
            or row.get("sum_separate_nodes") != separate_nodes
            or row.get("union_nodes") != union_nodes
            or union_nodes >= separate_nodes)

    raw = [json.loads(line) for line in
           (run_dir / "raw_measurements.jsonl").read_text(encoding="utf-8").splitlines()
           if line.strip()]
    performance = [row for row in raw if row.get("role") == "performance"]
    memory = [row for row in raw if row.get("role") == "memory_profile"]
    structure_mismatches = int(
        len(performance) != results["config"]["blocks"] * 6 * 2
        or len(memory) != 6 * 2
        or tuple(results["methods"]) != METHODS)
    correctness_mismatches = 0
    native_identity_mismatches = 0
    native_sha = results["native_library"]["sha256"]
    for row in raw:
        correctness_mismatches += int(
            row.get("schema") != "crse-native-multi-root-raw-session/v1"
            or row.get("status") != "ok"
            or row.get("method") not in METHODS
            or row.get("exact_check_passed") is not True
            or row.get("output_sha256") != expected.get(row.get("workload_id"))
            or len(row.get("query_measurements", [])) != 64)
        native_identity_mismatches += int(
            row.get("resources", {}).get("native_library_sha256") != native_sha
            or row.get("resources", {}).get("native_abi_version") != 1)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in performance:
        grouped[(row["workload_id"], row["method"])].append(row)
    medians: dict[tuple[str, str], dict[str, int]] = {}
    balance_mismatches = 0
    for workload in workloads:
        for method in METHODS:
            sessions = grouped[(workload.workload_id, method)]
            balance_mismatches += int(
                len(sessions) != results["config"]["blocks"]
                or Counter(row["method_position"] for row in sessions)
                != Counter({0: 10, 1: 10}))
            medians[(workload.workload_id, method)] = {
                stage: int(statistics.median_low(
                    row["timings_ns"][stage] for row in sessions))
                for stage in STAGES
            }
    aggregate_mismatches = 0
    published = results["summary"]["aggregate_workload_median_stage_ns"]
    for method in METHODS:
        for stage in STAGES:
            actual = sum(medians[(workload.workload_id, method)][stage]
                         for workload in workloads)
            aggregate_mismatches += int(actual != published[method][stage])

    failures = {
        "artifact_mismatches": artifact_mismatches,
        "source_mismatches": source_mismatches,
        "workload_mismatches": workload_mismatches,
        "structure_mismatches": structure_mismatches,
        "correctness_mismatches": correctness_mismatches,
        "native_identity_mismatches": native_identity_mismatches,
        "balance_mismatches": balance_mismatches,
        "aggregate_mismatches": aggregate_mismatches,
    }
    if any(failures.values()):
        raise RuntimeError(f"native multi-root verification failed: {failures}")
    verification = {
        "schema": "crse-native-multi-root-independent-verification/v1",
        "status": "verified",
        "run_id": results["run_id"],
        "performance_sessions": len(performance),
        "memory_profile_sessions": len(memory),
        "workloads_replayed": len(workloads),
        "output_query_rows_replayed": len(workloads) * 64 * 3,
        "raw_output_query_rows_checked": len(raw) * 64 * 3,
        "native_library_sha256": native_sha,
        "results_sha256": sha256(run_dir / "results.json"),
        "manifest_sha256": sha256(run_dir / "manifest.json"),
        **failures,
    }
    write_new(run_dir / "independent_verification.json", verification)
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
