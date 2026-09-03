"""Independently verify C34 natural task-matched headroom evidence."""
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

from cm_expr_serde import expr_from_json
from cmbench.comparative.arms import semantic_sha256
from cmbench.comparative.contracts import validate_contract
from cmbench.comparative.gf2_decomposition import delivered_sha256
from cmbench.comparative.gf2_natural_headroom import (
    DECOMPOSITION_METHODS,
    TRUTH_METHODS,
    bind_manifest_cases,
    complete_partition_sha256,
    complete_partitions,
    validate_dataset_manifest,
)
from cmbench.comparative.gf2_natural_headroom_experiment import validate_schedule
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2, truth_sha256
from cmbench.recognition.portfolio import reference_bits


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def bound_path(relative: str) -> Path:
    path = ROOT.joinpath(*Path(relative).parts).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError("C34 verifier input escaped or is missing")
    return path


def write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def _median_map(rows: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    grouped: dict[tuple[str, str], list[int]] = {}
    for row in rows:
        grouped.setdefault((row["case_id"], row["method"]), []).append(
            row["timings_ns"]["task_total_ns"])
    return {key: int(statistics.median(values)) for key, values in grouped.items()}


def independent_summary(
    rows: list[dict[str, Any]], methods: tuple[str, ...], *, router_budget_ns: int,
    speedup_gate: float, case_fraction_gate: float,
) -> dict[str, Any]:
    medians = _median_map(rows)
    cases = sorted({row["case_id"] for row in rows})
    widths = {row["case_id"]: row["n_vars"] for row in rows}
    if len(medians) != len(cases) * len(methods):
        raise ValueError("C34 verifier incomplete medians")
    totals = {method: sum(medians[(case, method)] for case in cases) for method in methods}
    fixed = min(methods, key=lambda method: (totals[method], method))
    winner = {case: min(methods, key=lambda method: (medians[(case, method)], method)) for case in cases}
    oracle = {case: medians[(case, winner[case])] for case in cases}
    headroom = {case: medians[(case, fixed)] - oracle[case] for case in cases}
    oracle_total = sum(oracle.values())
    fixed_total = totals[fixed]
    by_width = {}
    width_methods = {}
    width_total = 0
    for n_vars in sorted(set(widths.values())):
        selected = [case for case in cases if widths[case] == n_vars]
        width_totals = {method: sum(medians[(case, method)] for case in selected) for method in methods}
        choice = min(methods, key=lambda method: (width_totals[method], method))
        width_methods[n_vars] = choice
        width_total += width_totals[choice]
        by_width[str(n_vars)] = {
            "cases": len(selected),
            "best_aggregate_method": choice,
            "method_total_ns": width_totals,
            "best_fixed_speedup_from_width_choice": width_totals[fixed] / width_totals[choice],
        }
    methods_summary = {}
    for method in methods:
        values = [medians[(case, method)] for case in cases]
        methods_summary[method] = {
            "aggregate_median_case_total_ns": totals[method],
            "median_case_ns": int(statistics.median(values)),
            "minimum_case_ns": min(values),
            "maximum_case_ns": max(values),
            "relative_to_best_fixed": fixed_total / totals[method],
            "per_case_wins": sum(winner[case] == method for case in cases),
        }
    covered = sum(value >= router_budget_ns for value in headroom.values()) / len(cases)
    adjusted_oracle_speedup = fixed_total / (oracle_total + router_budget_ns * len(cases))
    adjusted_width_speedup = fixed_total / (width_total + router_budget_ns * len(cases))
    return {
        "cases": len(cases),
        "measurement_rows": len(rows),
        "methods": methods_summary,
        "best_fixed_method": fixed,
        "best_fixed_total_ns": fixed_total,
        "per_case_oracle_total_ns": oracle_total,
        "per_case_oracle_speedup_over_best_fixed": fixed_total / oracle_total,
        "per_case_oracle_absolute_headroom_total_ns": fixed_total - oracle_total,
        "per_case_oracle_median_headroom_ns": int(statistics.median(headroom.values())),
        "charged_router_budget_ns_per_case": router_budget_ns,
        "budget_covered_case_fraction": covered,
        "budget_adjusted_oracle_speedup_over_best_fixed": adjusted_oracle_speedup,
        "oracle_headroom_gate": adjusted_oracle_speedup >= speedup_gate and covered >= case_fraction_gate,
        "width_rule": {
            "methods": {str(key): value for key, value in sorted(width_methods.items())},
            "total_ns": width_total,
            "raw_speedup_over_best_fixed": fixed_total / width_total,
            "budget_adjusted_speedup_over_best_fixed": adjusted_width_speedup,
            "headroom_gate": adjusted_width_speedup >= speedup_gate,
            "post_hoc_retrospective": True,
        },
        "by_width": by_width,
        "timing_is_local_and_machine_specific": True,
    }


def verify(run: Path) -> dict[str, Any]:
    run = run.resolve()
    if not run.is_relative_to(ROOT.resolve()) or not run.is_dir():
        raise ValueError("C34 run must be an existing project directory")
    destination = run / "independent_verification.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    spec = load(run / "run_spec.json")
    results = load(run / "results.json")
    manifest = load(run / "manifest.json")
    if spec.get("schema") != "crse-c34-natural-task-matched-headroom-experiment/v1":
        raise ValueError("C34 run spec schema")
    for relative, digest in manifest.get("sources", {}).items():
        if sha256(bound_path(relative)) != digest:
            raise ValueError("C34 source fingerprint changed")
    for relative, digest in manifest.get("artifacts", {}).items():
        path = run / relative
        if not path.is_file() or sha256(path) != digest:
            raise ValueError("C34 artifact fingerprint changed")

    dataset_manifest_path = bound_path(spec["dataset_manifest_path"])
    dataset_verification_path = bound_path(spec["dataset_verification_path"])
    source_path = bound_path(spec["source_dataset_path"])
    if (sha256(dataset_manifest_path) != spec["dataset_manifest_sha256"]
            or sha256(dataset_verification_path) != spec["dataset_verification_sha256"]
            or sha256(source_path) != spec["source_dataset_sha256"]):
        raise ValueError("C34 run/input binding changed")
    dataset_manifest = load(dataset_manifest_path)
    dataset_verification = load(dataset_verification_path)
    source = load(source_path)
    validate_dataset_manifest(dataset_manifest, source)
    if dataset_verification.get("status") != "verified":
        raise ValueError("C34 dataset was not independently verified")
    truth_cases = bind_manifest_cases(dataset_manifest, source, role="complete_relation")
    decomposition_cases = bind_manifest_cases(dataset_manifest, source, role="decomposition")
    case_map = {case["case_id"]: case for case in truth_cases}

    truth_oracles = load(run / "truth_oracles.json")
    decomposition_oracles = load(run / "decomposition_oracles.json")
    semantic_mismatches = 0
    for case in truth_cases:
        bits = reference_bits(expr_from_json(case["expression_v2"]), case["n_vars"])
        expected = int(case["truth_bits_hex"], 16)
        semantic_mismatches += int(
            bits != expected
            or truth_sha256(bits, case["n_vars"]) != case["truth_sha256"]
            or truth_oracles.get(case["case_id"], {}).get("truth_bits_hex") != case["truth_bits_hex"]
        )
    oracle_mismatches = 0
    for case in decomposition_cases:
        bits = int(case["truth_bits_hex"], 16)
        partitions = complete_partitions(case["n_vars"])
        analysis = analyze_exact_gf2(bits, case["n_vars"], row_partitions=partitions)
        best = analysis.best.to_dict() if analysis.best else None
        oracle = decomposition_oracles.get(case["case_id"], {})
        oracle_mismatches += int(
            not all(candidate.reconstruct() == bits for candidate in analysis.candidates)
            or oracle.get("best_artifact") != best
            or oracle.get("delivered_sha256") != delivered_sha256(best)
            or oracle.get("partitions_tested") != len(partitions)
            or oracle.get("partition_sha256") != complete_partition_sha256(case["n_vars"])
        )

    truth_contracts = load(run / "truth_contracts.json")
    decomposition_contracts = load(run / "decomposition_contracts.json")
    for case in truth_cases:
        for method in TRUTH_METHODS:
            normalized = validate_contract(truth_contracts[case["case_id"]][method])
            if normalized["task"] != "complete_relation" or normalized["kind"] != "packed_bigint":
                raise ValueError("C34 truth contract mismatch")
    for case in decomposition_cases:
        for method in DECOMPOSITION_METHODS:
            normalized = validate_contract(decomposition_contracts[case["case_id"]][method])
            if normalized["task"] != "gf2_decomposition":
                raise ValueError("C34 decomposition contract mismatch")

    truth_schedule = load_jsonl(run / "truth_schedule.jsonl")
    decomposition_schedule = load_jsonl(run / "decomposition_schedule.jsonl")
    config = spec["config"]
    validate_schedule(truth_schedule, truth_cases, TRUTH_METHODS, config["truth_blocks"])
    validate_schedule(
        decomposition_schedule, decomposition_cases, DECOMPOSITION_METHODS,
        config["decomposition_blocks"])
    schedule_maps = {
        "complete_relation": {(row["case_id"], row["block"]): row for row in truth_schedule},
        "gf2_decomposition": {(row["case_id"], row["block"]): row for row in decomposition_schedule},
    }
    truth_rows = load_jsonl(run / "truth_measurements.jsonl")
    decomposition_rows = load_jsonl(run / "decomposition_measurements.jsonl")
    if len(truth_rows) != 48 * 12 * len(TRUTH_METHODS):
        raise ValueError("C34 truth measurement cardinality")
    if len(decomposition_rows) != 15 * 6 * len(DECOMPOSITION_METHODS):
        raise ValueError("C34 decomposition measurement cardinality")
    measurement_mismatches = 0
    for row in (*truth_rows, *decomposition_rows):
        schedule = schedule_maps[row["task"]].get((row["case_id"], row["block"]))
        if schedule is None:
            measurement_mismatches += 1
            continue
        case = case_map[row["case_id"]]
        expected_method_set = TRUTH_METHODS if row["task"] == "complete_relation" else DECOMPOSITION_METHODS
        expected_artifact = (
            semantic_sha256(int(case["truth_bits_hex"], 16), case["n_vars"])
            if row["task"] == "complete_relation"
            else decomposition_oracles[row["case_id"]]["delivered_sha256"]
        )
        timing_total = sum(value for key, value in row["timings_ns"].items() if key != "task_total_ns")
        valid = (
            row["method"] in expected_method_set
            and row["status"] == "ok"
            and row["case_position"] == schedule["case_position"]
            and row["order_sha256"] == schedule["order_sha256"]
            and row["arm_position"] == schedule["method_order"].index(row["method"])
            and row["artifact_sha256"] == expected_artifact
            and row["identity"].get("exact_check_passed") is True
            and row["timings_ns"]["task_total_ns"] == timing_total
        )
        if row["task"] == "gf2_decomposition":
            valid = valid and (
                row["identity"].get("best_artifact")
                == decomposition_oracles[row["case_id"]]["best_artifact"]
                and row["identity"].get("partitions_tested") == len(complete_partitions(case["n_vars"]))
                and row["resources"].get("complete_partition_universe") is True
                and row["resources"].get("partition_sha256") == complete_partition_sha256(case["n_vars"])
            )
        measurement_mismatches += int(not valid)

    budget = spec["charged_router_budget_ns"]
    truth_summary = independent_summary(
        truth_rows,
        TRUTH_METHODS,
        router_budget_ns=budget,
        speedup_gate=config["actionable_speedup_gate"],
        case_fraction_gate=config["actionable_case_fraction"],
    )
    decomposition_summary = independent_summary(
        decomposition_rows,
        DECOMPOSITION_METHODS,
        router_budget_ns=budget,
        speedup_gate=config["actionable_speedup_gate"],
        case_fraction_gate=config["actionable_case_fraction"],
    )
    summary_mismatch = int(results.get("summary") != {
        "complete_relation": truth_summary,
        "gf2_decomposition": decomposition_summary,
    })
    controls = load(run / "functional_controls.json")
    bdd = load(run / "bdd_functional_probes.json")
    boundary_ok = (
        results.get("status") == "complete"
        and results.get("semantic_or_artifact_mismatches") == 0
        and results.get("decision", {}).get("training_performed") is False
        and results.get("decision", {}).get("learning_or_router_promotion_permitted") is False
        and results.get("decision", {}).get("production_promotion") is False
        and results.get("runpod") == {"used": False, "cost_usd": 0.0}
        and controls.get("all_passed") is True
        and controls.get("production_write") is False
        and controls.get("production_promotion") is False
        and bdd.get("status") == "passed"
        and bdd.get("performance_ranking_permitted") is False
        and len(bdd.get("rows", [])) == 8
        and all(row.get("exact_check_passed") is True for row in bdd.get("rows", []))
    )
    status = "verified" if (
        semantic_mismatches == oracle_mismatches == measurement_mismatches == summary_mismatch == 0
        and boundary_ok
    ) else "failed"
    verification = {
        "schema": "crse-c34-independent-verification/v1",
        "status": status,
        "source_files_checked": len(manifest.get("sources", {})),
        "artifact_files_checked": len(manifest.get("artifacts", {})),
        "dataset_cases_replayed": len(truth_cases),
        "decomposition_oracles_recomputed": len(decomposition_cases),
        "truth_measurements_checked": len(truth_rows),
        "decomposition_measurements_checked": len(decomposition_rows),
        "semantic_mismatches": semantic_mismatches,
        "oracle_mismatches": oracle_mismatches,
        "measurement_mismatches": measurement_mismatches,
        "summary_mismatches": summary_mismatch,
        "schedules_recomputed": True,
        "complete_partition_universe_recomputed": True,
        "training": False,
        "policy_refit": False,
        "production_write": False,
        "production_promotion": False,
        "runpod_used": False,
        "results_sha256": sha256(run / "results.json"),
        "manifest_sha256": sha256(run / "manifest.json"),
    }
    if status != "verified":
        raise RuntimeError(f"C34 independent verification failed: {verification}")
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
