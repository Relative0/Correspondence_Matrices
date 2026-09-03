"""Independently verify the restricted-evaluator development run."""
from __future__ import annotations

import argparse
from collections import Counter
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
    "restricted_r0_occurrence",
    "restricted_r1_identity_memo",
    "restricted_r2_topological_liveness",
    "flattened_cse_words",
    "cm_ir_words",
    "compiled_truth_projection",
)
OPTIMIZED_METHODS = METHODS[1:]
CHECKPOINTS = (1, 4, 16, 64)
REQUIRED_SOURCES = {
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/gf2_restricted_evaluators.py",
    "cmbench/comparative/gf2_restricted_evaluator_experiment.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "cmbench/comparative/schedule.py",
    "cmbench/recognition/yosys_wide_restriction_data.py",
    "scripts/cm_comparative_restricted_evaluator_development.py",
    "scripts/crse_restricted_evaluator_development_verify.py",
    "scripts/crse_verify_c36_wide_repeated_query_dataset.py",
    "docs/recognition/c36_wide_repeated_query_dataset.json",
    "docs/recognition/c36_wide_repeated_query_dataset_verification.json",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-research-ci.txt",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def bound_project_path(relative: str) -> Path:
    path = ROOT.joinpath(*Path(relative).parts).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError("development verifier input escaped or is missing")
    return path


def independent_profile(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("version") != 2 or not isinstance(document.get("nodes"), list):
        raise ValueError("verifier requires DAG v2")
    nodes = document["nodes"]
    root = document.get("root")
    if root != len(nodes) - 1:
        raise ValueError("verifier DAG root")
    use_counts = [0] * len(nodes)
    multiplicity = [0] * len(nodes)
    multiplicity[root] = 1
    depth = [1] * len(nodes)
    for index, node in enumerate(nodes):
        opcode = node["op"]
        if opcode == "var":
            continue
        a = node["a"]
        use_counts[a] += 1
        if opcode == "not":
            depth[index] = depth[a] + 1
        else:
            b = node["b"]
            use_counts[b] += 1
            depth[index] = max(depth[a], depth[b]) + 1
    for index in range(root, -1, -1):
        count = multiplicity[index]
        node = nodes[index]
        if node["op"] == "var":
            continue
        multiplicity[node["a"]] += count
        if node["op"] != "not":
            multiplicity[node["b"]] += count
    unique_gates = sum(node["op"] != "var" for node in nodes)
    unique_edges = sum(
        0 if node["op"] == "var" else (1 if node["op"] == "not" else 2)
        for node in nodes)
    remaining = list(use_counts)
    live = peak_live = 0
    for index, node in enumerate(nodes):
        live += 1
        peak_live = max(peak_live, live)
        if node["op"] == "var":
            continue
        children = (node["a"],) if node["op"] == "not" else (node["a"], node["b"])
        for child in children:
            remaining[child] -= 1
            if remaining[child] == 0 and child != root:
                live -= 1
    unfolded = sum(multiplicity)
    return {
        "unique_nodes": len(nodes),
        "unique_gates": unique_gates,
        "unique_child_edges": unique_edges,
        "unfolded_visits": unfolded,
        "unfolded_gate_evaluations": sum(
            multiplicity[index] for index, node in enumerate(nodes)
            if node["op"] != "var"),
        "unfolded_child_edge_visits": max(0, unfolded - 1),
        "expansion_ratio_numerator": unfolded,
        "expansion_ratio_denominator": len(nodes),
        "max_depth": max(depth),
        "r1_retained_result_slots": len(nodes),
        "r2_peak_live_result_slots": peak_live,
    }


def _performance_medians(
    rows: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str, int], int], list[str]]:
    values: dict[tuple[str, str, int], list[int]] = {}
    cases = sorted({row["case_id"] for row in rows if row["role"] == "performance"})
    for row in rows:
        if row["role"] != "performance":
            continue
        for checkpoint in CHECKPOINTS:
            values.setdefault((row["case_id"], row["method"], checkpoint), []).append(
                row["checkpoint_total_ns"][str(checkpoint)])
    medians = {key: int(statistics.median(samples)) for key, samples in values.items()}
    if len(medians) != len(cases) * len(METHODS) * len(CHECKPOINTS):
        raise ValueError("verifier incomplete performance medians")
    return medians, cases


def _subgroup(selected: list[str], medians: dict[tuple[str, str, int], int]) -> dict[str, Any]:
    totals = {method: sum(medians[(case, method, 64)] for case in selected)
              for method in METHODS}
    return {
        "cases": len(selected),
        "method_total_ns": totals,
        "best_method": min(METHODS, key=lambda method: (totals[method], method)),
        "best_optimized_method": min(
            OPTIMIZED_METHODS, key=lambda method: (totals[method], method)),
    }


def independent_summary(
    rows: list[dict[str, Any]], profiles: dict[str, dict[str, Any]], threshold: int,
) -> dict[str, Any]:
    medians, cases = _performance_medians(rows)
    metadata = {row["case_id"]: (row["family"], row["n_vars"])
                for row in rows if row["role"] == "performance"}
    checkpoints: dict[str, Any] = {}
    for checkpoint in CHECKPOINTS:
        totals = {method: sum(medians[(case, method, checkpoint)] for case in cases)
                  for method in METHODS}
        best = min(METHODS, key=lambda method: (totals[method], method))
        optimized_best = min(
            OPTIMIZED_METHODS, key=lambda method: (totals[method], method))
        winners = {case: min(
            METHODS, key=lambda method: (medians[(case, method, checkpoint)], method))
            for case in cases}
        optimized_winners = {case: min(
            OPTIMIZED_METHODS,
            key=lambda method: (medians[(case, method, checkpoint)], method))
            for case in cases}
        oracle = sum(medians[(case, winners[case], checkpoint)] for case in cases)
        optimized_oracle = sum(
            medians[(case, optimized_winners[case], checkpoint)] for case in cases)
        checkpoints[str(checkpoint)] = {
            "method_total_ns": totals,
            "best_fixed_method": best,
            "best_optimized_fixed_method": optimized_best,
            "per_case_winners": winners,
            "per_case_optimized_winners": optimized_winners,
            "per_case_oracle_total_ns": oracle,
            "per_case_optimized_oracle_total_ns": optimized_oracle,
            "oracle_speedup_over_best_fixed": totals[best] / oracle,
            "optimized_oracle_speedup_over_best_optimized_fixed": (
                totals[optimized_best] / optimized_oracle),
            "r1_speedup_over_r0": totals[METHODS[0]] / totals[METHODS[1]],
            "r2_speedup_over_r0": totals[METHODS[0]] / totals[METHODS[2]],
            "r2_speedup_over_r1": totals[METHODS[1]] / totals[METHODS[2]],
        }
    by_width = {}
    for width in sorted({value[1] for value in metadata.values()}):
        by_width[str(width)] = _subgroup(
            [case for case in cases if metadata[case][1] == width], medians)
    by_family = {}
    for family in sorted({value[0] for value in metadata.values()}):
        by_family[family] = _subgroup(
            [case for case in cases if metadata[case][0] == family], medians)
    high = [case for case in cases if (
        profiles[case]["unfolded_visits"] > threshold * profiles[case]["unique_nodes"])]
    high_set = set(high)
    by_expansion = {
        "low_or_equal_10": _subgroup([case for case in cases if case not in high_set], medians),
        "high_over_10": _subgroup(high, medians),
        "threshold_role": "historical_descriptive_subgroup_only_not_a_policy",
    }
    memory_rows = [row for row in rows if row["role"] == "memory_profile"]
    memory = {}
    for method in METHODS:
        selected = [row for row in memory_rows if row["method"] == method]
        memory[method] = {
            "profile_sessions": len(selected),
            "max_session_sampled_peak_rss_delta_bytes": max(
                (row["resources"]["session_sampled_peak_rss_delta_bytes"] or 0)
                for row in selected),
            "max_tracemalloc_peak_bytes": max(
                row["resources"].get("tracemalloc_peak_bytes", 0) for row in selected),
            "max_process_peak_rss_bytes": max(
                (row["resources"]["process_peak_rss_bytes"] or 0) for row in selected),
        }
    final = checkpoints["64"]
    complexity_ratio = sum(profiles[case]["unfolded_visits"] for case in cases) / sum(
        profiles[case]["unique_nodes"] for case in cases)
    return {
        "cases": len(cases),
        "performance_sessions": sum(row["role"] == "performance" for row in rows),
        "memory_profile_sessions": len(memory_rows),
        "timed_queries": sum(len(row["query_measurements"]) for row in rows
                             if row["role"] == "performance"),
        "checkpoints": checkpoints,
        "by_width_at_q64": by_width,
        "by_family_at_q64": by_family,
        "by_expansion_at_q64": by_expansion,
        "memory_profiles": memory,
        "complexity": {
            "aggregate_r0_to_r1_node_evaluation_reduction": complexity_ratio,
            "all_r1_node_evaluations_bounded_by_unique_nodes": True,
            "all_r2_node_evaluations_equal_unique_nodes": True,
            "all_r2_peak_live_slots_bounded_by_unique_nodes": True,
        },
        "decision": {
            "finding_supported_by_q64_timing": final["r1_speedup_over_r0"] > 1.0,
            "fastest_repaired_direct_method": min(
                METHODS[1:3], key=lambda method: (final["method_total_ns"][method], method)),
            "best_recomputed_fixed_backend": final["best_fixed_method"],
            "best_recomputed_optimized_fixed_backend": final["best_optimized_fixed_method"],
            "optimized_per_case_oracle_speedup": (
                final["optimized_oracle_speedup_over_best_optimized_fixed"]),
            "formal_c37_or_production_promotion_permitted": False,
        },
        "timing_is_local_and_machine_specific": True,
        "memory_timing_excluded_from_performance_summary": True,
    }


def verify(run: Path) -> dict[str, Any]:
    run = run.resolve()
    if not run.is_relative_to(ROOT.resolve()) or not run.is_dir():
        raise ValueError("development run must be an existing project directory")
    destination = run / "independent_verification.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    required_artifacts = {
        "protocol.md", "results.json", "raw_measurements.jsonl",
        "environment.json", "manifest.json", "report.md",
    }
    if {path.name for path in run.iterdir() if path.is_file()} != required_artifacts:
        raise ValueError("unexpected pre-verification artifact layout")
    results = load(run / "results.json")
    environment = load(run / "environment.json")
    manifest = load(run / "manifest.json")
    if (
        results.get("schema") != "crse-restricted-evaluator-development/v1"
        or results.get("status") != "complete"
        or manifest.get("schema") != "crse-restricted-evaluator-manifest/v1"
    ):
        raise ValueError("development artifact schema/status")
    local_sources = manifest.get("local_sources", {})
    if not REQUIRED_SOURCES.issubset(local_sources):
        raise ValueError("development manifest is not source-closed")
    for relative, expected in local_sources.items():
        if sha256(bound_project_path(relative)) != expected:
            raise ValueError(f"development local source changed: {relative}")
    for module, record in manifest.get("native_modules", {}).items():
        path = Path(record["path"])
        if not path.is_file() or sha256(path) != record["sha256"]:
            raise ValueError(f"development native module changed: {module}")
    interpreter = manifest.get("interpreter", {})
    interpreter_path = Path(interpreter.get("path", ""))
    if not interpreter_path.is_file() or sha256(interpreter_path) != interpreter.get("sha256"):
        raise ValueError("development interpreter changed")
    for relative, expected in manifest.get("artifacts", {}).items():
        path = run / relative
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"development artifact changed: {relative}")

    dataset_path = bound_project_path(results["dataset"]["path"])
    dataset_verification_path = bound_project_path(results["dataset"]["verification_path"])
    if (
        sha256(dataset_path) != results["dataset"]["sha256"]
        or sha256(dataset_verification_path) != results["dataset"]["verification_sha256"]
        or environment["dataset"]["sha256"] != results["dataset"]["sha256"]
        or load(dataset_verification_path).get("status") != "verified"
    ):
        raise ValueError("development dataset/environment binding")
    dataset = load(dataset_path)
    cases = dataset["cases"]
    case_map = {case["case_id"]: case for case in cases}
    expected_outputs: dict[str, tuple[str, list[str]]] = {}
    recomputed_profiles: dict[str, dict[str, Any]] = {}
    trace_mismatches = oracle_mismatches = profile_mismatches = 0
    for case in cases:
        trace = independent_trace(case["case_id"], case["n_vars"])
        trace_mismatches += int(trace != case["c36_trace"])
        output = independent_output(case, trace)
        output_digest = digest(output)
        oracle_mismatches += int(output_digest != case["c36_required_output_sha256"])
        expected_outputs[case["case_id"]] = (
            output_digest, [digest(row) for row in output["rows"]])
        profile = independent_profile(case["expression_v2"])
        recomputed_profiles[case["case_id"]] = profile
        profile_mismatches += int(profile != results["structural_profiles"][case["case_id"]])

    rows = load_jsonl(run / "raw_measurements.jsonl")
    performance_rows = [row for row in rows if row.get("role") == "performance"]
    memory_rows = [row for row in rows if row.get("role") == "memory_profile"]
    config = results["config"]
    measurement_mismatches = 0
    if (
        len(performance_rows) != len(cases) * config["blocks"] * len(METHODS)
        or len(memory_rows) != len(cases) * len(METHODS)
    ):
        measurement_mismatches += 1
    expected_counts = Counter(
        (case["case_id"], method, block)
        for case in cases for method in METHODS for block in range(config["blocks"]))
    actual_counts = Counter(
        (row["case_id"], row["method"], row["block"]) for row in performance_rows)
    measurement_mismatches += int(expected_counts != actual_counts)
    memory_counts = Counter((row["case_id"], row["method"]) for row in memory_rows)
    measurement_mismatches += int(memory_counts != Counter(
        (case["case_id"], method) for case in cases for method in METHODS))

    for row in rows:
        case_id = row.get("case_id")
        method = row.get("method")
        if case_id not in case_map or method not in METHODS:
            measurement_mismatches += 1
            continue
        expected_document, expected_rows = expected_outputs[case_id]
        queries = row.get("query_measurements", [])
        timings = row.get("timings_ns", {})
        profile = recomputed_profiles[case_id]
        measurement_mismatches += int(
            row.get("schema") != "crse-restricted-evaluator-raw-session/v1"
            or row.get("status") != "ok"
            or row.get("artifact_sha256") != expected_document
            or row.get("exact_check_passed") is not True
            or row.get("structural_profile") != profile
            or len(queries) != 64
            or [query.get("query") for query in queries] != list(range(64))
            or [query.get("output_sha256") for query in queries] != expected_rows
            or any(query.get("total_ns") != query.get("restriction_setup_ns", 0)
                   + query.get("evaluation_ns", 0) + query.get("delivery_ns", 0)
                   for query in queries)
            or timings.get("query_total_ns") != sum(query["total_ns"] for query in queries)
            or timings.get("restriction_setup_ns") != sum(
                query["restriction_setup_ns"] for query in queries)
            or timings.get("evaluation_ns") != sum(query["evaluation_ns"] for query in queries)
            or timings.get("delivery_ns") != sum(query["delivery_ns"] for query in queries)
            or timings.get("accounted_total_ns") != timings.get("input_decode_ns", 0)
            + timings.get("representation_ns", 0) + timings.get("query_total_ns", 0)
            + timings.get("cleanup_ns", 0)
            or row.get("checkpoint_query_ns", {}).get("64") != timings.get("query_total_ns")
            or any(row.get("checkpoint_total_ns", {}).get(str(checkpoint))
                   != timings.get("input_decode_ns", 0) + timings.get("representation_ns", 0)
                   + row.get("checkpoint_query_ns", {}).get(str(checkpoint), 0)
                   + timings.get("cleanup_ns", 0) for checkpoint in CHECKPOINTS)
        )
        resources = row.get("resources", {})
        if method == METHODS[0]:
            measurement_mismatches += int(
                resources.get("node_evaluations") != profile["unfolded_visits"])
        elif method == METHODS[1]:
            measurement_mismatches += int(
                resources.get("node_evaluations") != profile["unique_nodes"]
                or resources.get("node_evaluations") > profile["unique_nodes"])
        elif method == METHODS[2]:
            measurement_mismatches += int(
                resources.get("node_evaluations") != profile["unique_nodes"]
                or resources.get("peak_live_result_slots")
                != profile["r2_peak_live_result_slots"]
                or resources.get("peak_live_result_slots") > profile["unique_nodes"])
        measurement_mismatches += int(
            resources.get("rss_sampling_points", 0) <= 0
            or (row["role"] == "memory_profile"
                and resources.get("tracemalloc_peak_bytes", 0) <= 0))

    recomputed = independent_summary(
        rows, recomputed_profiles, config["high_expansion_threshold"])
    summary_mismatches = int(recomputed != results.get("summary"))
    correctness_mismatches = int(results.get("correctness") != {
        "relation_mismatches": 0,
        "count_mismatches": 0,
        "sat_mismatches": 0,
        "witness_mismatches": 0,
        "canonical_delivery_mismatches": 0,
    })
    if any((trace_mismatches, oracle_mismatches, profile_mismatches,
            measurement_mismatches, summary_mismatches, correctness_mismatches)):
        raise RuntimeError(
            "restricted-evaluator independent verification failed: "
            f"trace={trace_mismatches}, oracle={oracle_mismatches}, "
            f"profile={profile_mismatches}, measurement={measurement_mismatches}, "
            f"summary={summary_mismatches}, correctness={correctness_mismatches}")
    verification = {
        "schema": "crse-restricted-evaluator-independent-verification/v1",
        "status": "verified",
        "dataset_cases_replayed": len(cases),
        "queries_replayed": len(cases) * 64,
        "performance_sessions_checked": len(performance_rows),
        "memory_profile_sessions_checked": len(memory_rows),
        "timed_query_rows_checked": len(performance_rows) * 64,
        "trace_mismatches": 0,
        "relation_mismatches": 0,
        "count_mismatches": 0,
        "sat_mismatches": 0,
        "witness_mismatches": 0,
        "canonical_delivery_mismatches": 0,
        "profile_mismatches": 0,
        "measurement_mismatches": 0,
        "summary_mismatches": 0,
        "summary_recomputed_independently": True,
        "manifest_sources_checked": len(local_sources),
        "native_modules_checked": len(manifest.get("native_modules", {})),
        "interpreter_checked": True,
        "bitset_backend_manifest_bound": "bitset_backend.py" in local_sources,
        "training_performed": False,
        "prospective_data_consumed": False,
        "production_write": False,
        "production_promotion": False,
        "results_sha256": sha256(run / "results.json"),
        "manifest_sha256": sha256(run / "manifest.json"),
    }
    write_new(destination, verification)
    return verification


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    result = verify(args.run)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
