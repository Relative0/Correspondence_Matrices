"""Independently verify C35 natural repeated-query lifecycle evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.comparative.contracts import canonical_bytes, validate_contract
from cmbench.comparative.gf2_natural_repeated_queries import CHECKPOINTS, METHODS
from cmbench.comparative.gf2_natural_repeated_query_experiment import validate_schedule
from cmbench.recognition.portfolio import reference_bits
from scripts.crse_verify_c35_natural_repeated_query_dataset import (
    independent_output,
    independent_trace,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def bound_path(relative: str) -> Path:
    path = ROOT.joinpath(*Path(relative).parts).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError("C35 verifier input escaped or is missing")
    return path


def write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def independent_summary(rows: list[dict[str, Any]], *, speedup_gate: float,
                        case_fraction_gate: float) -> dict[str, Any]:
    checkpoint_values: dict[tuple[str, str, int], list[int]] = {}
    setup_values: dict[tuple[str, str], list[int]] = {}
    warm_values: dict[tuple[str, str], list[int]] = {}
    for row in rows:
        key = (row["case_id"], row["method"])
        identity = row["identity"]
        setup_values.setdefault(key, []).append(identity["setup_total_ns"])
        cumulative = identity["checkpoint_query_ns"]
        warm_values.setdefault(key, []).append((cumulative["64"] - cumulative["16"]) // 48)
        for checkpoint in CHECKPOINTS:
            checkpoint_values.setdefault((*key, checkpoint), []).append(
                identity["checkpoint_total_ns"][str(checkpoint)])
    medians = {key: int(statistics.median(values))
               for key, values in checkpoint_values.items()}
    setup = {key: int(statistics.median(values)) for key, values in setup_values.items()}
    warm = {key: int(statistics.median(values)) for key, values in warm_values.items()}
    cases = sorted({row["case_id"] for row in rows})
    widths = {row["case_id"]: row["n_vars"] for row in rows}
    if len(medians) != len(cases) * len(METHODS) * len(CHECKPOINTS):
        raise ValueError("C35 verifier incomplete medians")
    checkpoints = {}
    versus_cse = versus_direct = None
    for checkpoint in CHECKPOINTS:
        totals = {method: sum(medians[(case, method, checkpoint)] for case in cases)
                  for method in METHODS}
        fixed = min(METHODS, key=lambda method: (totals[method], method))
        winners = {case: min(METHODS, key=lambda method:
                             (medians[(case, method, checkpoint)], method)) for case in cases}
        cm = totals["cm_ir_restrict"]
        cse = totals["flattened_cse_restrict"]
        direct = totals["direct_ast_restrict"]
        if versus_cse is None and cm <= cse:
            versus_cse = checkpoint
        if versus_direct is None and cm <= direct:
            versus_direct = checkpoint
        checkpoints[str(checkpoint)] = {
            "best_fixed_method": fixed,
            "method_total_ns": totals,
            "cm_speedup_over_flattened_cse": cse / cm,
            "cm_speedup_over_direct_ast": direct / cm,
            "cm_speedup_over_direct_truth_cache": totals["direct_truth_cache"] / cm,
            "cm_case_win_fraction_vs_flattened_cse": sum(
                medians[(case, "cm_ir_restrict", checkpoint)]
                < medians[(case, "flattened_cse_restrict", checkpoint)] for case in cases
            ) / len(cases),
            "per_case_winners": winners,
        }
    final = checkpoints["64"]
    promotion = (final["cm_speedup_over_flattened_cse"] >= speedup_gate
                 and final["cm_speedup_over_direct_truth_cache"] >= 1.0
                 and final["cm_case_win_fraction_vs_flattened_cse"] >= case_fraction_gate)
    methods = {method: {
        "aggregate_setup_median_ns": sum(setup[(case, method)] for case in cases),
        "aggregate_warm_query_median_ns": sum(warm[(case, method)] for case in cases),
        "median_case_setup_ns": int(statistics.median(setup[(case, method)] for case in cases)),
        "median_case_warm_query_ns": int(statistics.median(warm[(case, method)] for case in cases)),
    } for method in METHODS}
    by_width = {str(widths[case]): {
        "case_id": case,
        "best_at_64": min(METHODS, key=lambda method: (medians[(case, method, 64)], method)),
        "cm_vs_flattened_cse_at_64": (medians[(case, "flattened_cse_restrict", 64)]
                                       / medians[(case, "cm_ir_restrict", 64)]),
    } for case in cases}
    return {
        "cases": len(cases), "measurement_rows": len(rows), "timed_sessions": len(rows),
        "timed_queries": len(rows) * 64, "checkpoints": checkpoints, "methods": methods,
        "cm_break_even_query_count_vs_flattened_cse": versus_cse,
        "cm_break_even_query_count_vs_direct_ast": versus_direct,
        "cm_promotion_gate": promotion,
        "cm_promotion_gate_contract": {
            "checkpoint": 64, "speedup_over_flattened_cse_minimum": speedup_gate,
            "speedup_over_direct_truth_cache_minimum": 1.0,
            "case_win_fraction_vs_flattened_cse_minimum": case_fraction_gate,
        },
        "by_width": by_width, "timing_is_local_and_machine_specific": True,
    }


def verify(run: Path) -> dict[str, Any]:
    run = run.resolve()
    if not run.is_relative_to(ROOT.resolve()) or not run.is_dir():
        raise ValueError("C35 run must be an existing project directory")
    destination = run / "independent_verification.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    spec = load(run / "run_spec.json")
    results = load(run / "results.json")
    manifest = load(run / "manifest.json")
    if spec.get("schema") != "crse-c35-natural-repeated-query-experiment/v1":
        raise ValueError("C35 run spec schema")
    for relative, digest in manifest.get("sources", {}).items():
        if sha256(bound_path(relative)) != digest:
            raise ValueError("C35 source fingerprint changed")
    for relative, digest in manifest.get("artifacts", {}).items():
        path = run / relative
        if not path.is_file() or sha256(path) != digest:
            raise ValueError("C35 artifact fingerprint changed")

    dataset = load(bound_path(spec["dataset_manifest_path"]))
    dataset_verification = load(bound_path(spec["dataset_verification_path"]))
    source = load(bound_path(spec["source_dataset_path"]))
    if (dataset_verification.get("status") != "verified"
            or dataset_verification.get("manifest_sha256") != sha256(
                bound_path(spec["dataset_manifest_path"]))):
        raise ValueError("C35 dataset verification binding")
    source_map = {case["case_id"]: case for case in source["cases"]}
    cases = []
    semantic_mismatches = trace_mismatches = oracle_mismatches = 0
    expected_outputs = {}
    for row in dataset["cases"]:
        case = source_map[row["case_id"]]
        bits = reference_bits(expr_from_json(case["expression_v2"]), case["n_vars"])
        semantic_mismatches += int(bits != int(case["truth_bits_hex"], 16))
        trace = independent_trace(case["case_id"], case["n_vars"])
        trace_mismatches += int(trace != row["trace"])
        output = independent_output(case, trace)
        digest = hashlib.sha256(canonical_bytes(output)).hexdigest()
        oracle_mismatches += int(digest != row["required_output_sha256"])
        expected_outputs[case["case_id"]] = (output, digest)
        cases.append({**case, "c35_trace": trace,
                      "c35_required_output_sha256": row["required_output_sha256"]})

    contracts = load(run / "contracts.json")
    oracles = load(run / "oracles.json")
    for case in cases:
        expected_output, digest = expected_outputs[case["case_id"]]
        oracle_mismatches += int(oracles.get(case["case_id"]) != expected_output)
        for method in METHODS:
            contract = contracts[case["case_id"]][method]
            normalized = validate_contract(contract)
            if (normalized["task"] != "partial_context" or normalized["queries"] != 64
                    or contract["validation"]["required_output_sha256"] != digest):
                raise ValueError("C35 contract mismatch")
    schedule = load_jsonl(run / "schedule.jsonl")
    validate_schedule(schedule, cases, spec["config"]["blocks"])
    schedule_map = {(row["block"], row["case_id"]): row for row in schedule}
    measurements = load_jsonl(run / "measurements.jsonl")
    measurement_mismatches = 0
    for row in measurements:
        planned = schedule_map.get((row["block"], row["case_id"]))
        expected_output, digest = expected_outputs[row["case_id"]]
        timings = row["timings_ns"]
        identity = row["identity"]
        setup = timings["input_decode_ns"] + timings["representation_ns"] + timings["compile_ns"]
        measurement_mismatches += int(
            planned is None or row["method"] not in METHODS or row["status"] != "ok"
            or row["method_position"] != planned["method_order"].index(row["method"])
            or row["order_sha256"] != planned["order_sha256"]
            or row["artifact_sha256"] != digest
            or identity["semantic_output"] != expected_output
            or identity["setup_total_ns"] != setup
            or timings["task_total_ns"] != sum(
                value for key, value in timings.items() if key != "task_total_ns")
            or any(identity["checkpoint_total_ns"][str(checkpoint)]
                   != setup + identity["checkpoint_query_ns"][str(checkpoint)]
                   + timings["cleanup_ns"] for checkpoint in CHECKPOINTS)
        )
    config = spec["config"]
    recomputed = independent_summary(
        measurements, speedup_gate=config["cm_speedup_gate"],
        case_fraction_gate=config["cm_case_fraction_gate"])
    summary_mismatches = int(recomputed != results.get("summary"))
    controls = load(run / "functional_controls.json")
    if controls.get("all_passed") is not True:
        raise ValueError("C35 functional controls")
    if any((semantic_mismatches, trace_mismatches, oracle_mismatches,
            measurement_mismatches, summary_mismatches)):
        raise RuntimeError("C35 independent verification failed")
    verification = {
        "schema": "crse-c35-independent-verification/v1", "status": "verified",
        "dataset_cases_replayed": len(cases), "queries_replayed": len(cases) * 64,
        "measurement_rows_checked": len(measurements),
        "timed_queries_checked": len(measurements) * 64,
        "contracts_checked": len(cases) * len(METHODS),
        "semantic_mismatches": 0, "trace_mismatches": 0, "oracle_mismatches": 0,
        "measurement_mismatches": 0, "summary_mismatches": 0,
        "summary_recomputed_independently": True,
        "results_sha256": sha256(run / "results.json"),
        "manifest_sha256": sha256(run / "manifest.json"),
        "production_write": False, "production_promotion": False,
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
