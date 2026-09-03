"""Independently verify C36 wider-natural repeated-query evidence."""
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

from cmbench.comparative.contracts import canonical_bytes, validate_contract
from cmbench.comparative.gf2_wide_repeated_queries import CHECKPOINTS, METHODS
from cmbench.comparative.gf2_wide_repeated_query_experiment import validate_schedule
from scripts.crse_verify_c36_wide_repeated_query_dataset import (
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
        raise ValueError("C36 verifier input escaped or is missing")
    return path


def write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def independent_summary(rows: list[dict[str, Any]], *, speedup_gate: float,
                        case_fraction_gate: float, router_budget_ns: int,
                        routing_speedup_gate: float) -> dict[str, Any]:
    """Recompute every reported statistic without calling production summarize()."""
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
    families = {row["case_id"]: row["family"] for row in rows}
    if len(medians) != len(cases) * len(METHODS) * len(CHECKPOINTS):
        raise ValueError("C36 verifier incomplete medians")

    checkpoints: dict[str, Any] = {}
    versus_cse = versus_direct = versus_projection = None
    for checkpoint in CHECKPOINTS:
        totals = {method: sum(medians[(case, method, checkpoint)] for case in cases)
                  for method in METHODS}
        fixed = min(METHODS, key=lambda method: (totals[method], method))
        winners = {case: min(METHODS, key=lambda method:
                             (medians[(case, method, checkpoint)], method))
                   for case in cases}
        oracle_total = sum(medians[(case, winners[case], checkpoint)] for case in cases)
        cm = totals["cm_ir_words"]
        cm_cse = totals["flattened_cse_words"] / cm
        cm_direct = totals["direct_ast_restrict"] / cm
        cm_projection = totals["compiled_truth_projection"] / cm
        if versus_cse is None and cm_cse >= 1:
            versus_cse = checkpoint
        if versus_direct is None and cm_direct >= 1:
            versus_direct = checkpoint
        if versus_projection is None and cm_projection >= 1:
            versus_projection = checkpoint
        checkpoints[str(checkpoint)] = {
            "best_fixed_method": fixed,
            "method_total_ns": totals,
            "cm_speedup_over_flattened_cse": cm_cse,
            "cm_speedup_over_direct_ast": cm_direct,
            "cm_speedup_over_compiled_truth_projection": cm_projection,
            "cm_case_win_fraction_vs_flattened_cse": sum(
                medians[(case, "cm_ir_words", checkpoint)]
                < medians[(case, "flattened_cse_words", checkpoint)] for case in cases
            ) / len(cases),
            "per_case_winners": winners,
            "per_case_oracle_total_ns": oracle_total,
            "per_case_oracle_speedup_over_best_fixed": totals[fixed] / oracle_total,
        }

    final = checkpoints["64"]
    promotion = (final["cm_speedup_over_flattened_cse"] >= speedup_gate
                 and final["cm_speedup_over_compiled_truth_projection"] >= 1.0
                 and final["cm_case_win_fraction_vs_flattened_cse"]
                 >= case_fraction_gate)
    methods = {method: {
        "aggregate_setup_median_ns": sum(setup[(case, method)] for case in cases),
        "aggregate_warm_query_median_ns": sum(warm[(case, method)] for case in cases),
        "median_case_setup_ns": int(statistics.median(
            setup[(case, method)] for case in cases)),
        "median_case_warm_query_ns": int(statistics.median(
            warm[(case, method)] for case in cases)),
    } for method in METHODS}

    by_width = {}
    for n_vars in sorted(set(widths.values())):
        selected = [case for case in cases if widths[case] == n_vars]
        totals = {method: sum(medians[(case, method, 64)] for case in selected)
                  for method in METHODS}
        by_width[str(n_vars)] = {
            "cases": len(selected),
            "best_at_64": min(METHODS, key=lambda method: (totals[method], method)),
            "method_total_ns_at_64": totals,
            "cm_speedup_over_flattened_cse_at_64": (
                totals["flattened_cse_words"] / totals["cm_ir_words"]),
        }

    by_family = {}
    family_rule_total = 0
    family_rule_methods = {}
    for family in sorted(set(families.values())):
        selected = [case for case in cases if families[case] == family]
        totals = {method: sum(medians[(case, method, 64)] for case in selected)
                  for method in METHODS}
        best = min(METHODS, key=lambda method: (totals[method], method))
        family_rule_methods[family] = best
        family_rule_total += totals[best]
        by_family[family] = {"cases": len(selected), "best_at_64": best,
                             "method_total_ns_at_64": totals}
    fixed_total = final["method_total_ns"][final["best_fixed_method"]]
    adjusted_family_total = family_rule_total + router_budget_ns * len(cases)
    routing = {
        "checkpoint": 64,
        "best_fixed_method": final["best_fixed_method"],
        "best_fixed_total_ns": fixed_total,
        "per_case_oracle_total_ns": final["per_case_oracle_total_ns"],
        "per_case_oracle_raw_speedup": final["per_case_oracle_speedup_over_best_fixed"],
        "family_rule_methods": family_rule_methods,
        "family_rule_total_ns": family_rule_total,
        "family_rule_raw_speedup": fixed_total / family_rule_total,
        "charged_router_budget_ns_per_case": router_budget_ns,
        "family_rule_budget_adjusted_total_ns": adjusted_family_total,
        "family_rule_budget_adjusted_speedup": fixed_total / adjusted_family_total,
        "exploratory_headroom_gate": (fixed_total / adjusted_family_total
                                      >= routing_speedup_gate),
        "selection_is_post_hoc": True,
        "training_performed": False,
        "promotion_permitted": False,
    }
    return {
        "cases": len(cases), "measurement_rows": len(rows), "timed_sessions": len(rows),
        "timed_queries": len(rows) * 64, "checkpoints": checkpoints, "methods": methods,
        "cm_break_even_query_count_vs_flattened_cse": versus_cse,
        "cm_break_even_query_count_vs_direct_ast": versus_direct,
        "cm_break_even_query_count_vs_compiled_truth_projection": versus_projection,
        "cm_promotion_gate": promotion,
        "cm_promotion_gate_contract": {
            "checkpoint": 64,
            "speedup_over_flattened_cse_minimum": speedup_gate,
            "speedup_over_compiled_truth_projection_minimum": 1.0,
            "case_win_fraction_vs_flattened_cse_minimum": case_fraction_gate,
        },
        "routing_headroom": routing,
        "by_width": by_width,
        "by_family": by_family,
        "timing_is_local_and_machine_specific": True,
    }


def verify(run: Path) -> dict[str, Any]:
    run = run.resolve()
    if not run.is_relative_to(ROOT.resolve()) or not run.is_dir():
        raise ValueError("C36 run must be an existing project directory")
    destination = run / "independent_verification.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    spec = load(run / "run_spec.json")
    results = load(run / "results.json")
    manifest = load(run / "manifest.json")
    if spec.get("schema") != "crse-c36-wide-natural-repeated-query-experiment/v1":
        raise ValueError("C36 run spec schema")
    for relative, digest in manifest.get("sources", {}).items():
        if sha256(bound_path(relative)) != digest:
            raise ValueError("C36 source fingerprint changed")
    for relative, digest in manifest.get("artifacts", {}).items():
        path = run / relative
        if not path.is_file() or sha256(path) != digest:
            raise ValueError("C36 artifact fingerprint changed")

    dataset_path = bound_path(spec["dataset_path"])
    dataset_verification_path = bound_path(spec["dataset_verification_path"])
    dataset = load(dataset_path)
    dataset_verification = load(dataset_verification_path)
    if (sha256(dataset_path) != spec["dataset_sha256"]
            or sha256(dataset_verification_path) != spec["dataset_verification_sha256"]
            or dataset_verification.get("status") != "verified"
            or dataset_verification.get("dataset_sha256") != sha256(dataset_path)):
        raise ValueError("C36 dataset verification binding")

    cases = []
    expected_outputs = {}
    trace_mismatches = oracle_mismatches = 0
    for case in dataset["cases"]:
        trace = independent_trace(case["case_id"], case["n_vars"])
        trace_mismatches += int(trace != case["c36_trace"])
        output = independent_output(case, trace)
        digest = hashlib.sha256(canonical_bytes(output)).hexdigest()
        oracle_mismatches += int(digest != case["c36_required_output_sha256"])
        expected_outputs[case["case_id"]] = (output, digest)
        cases.append(case)

    contracts = load(run / "contracts.json")
    oracles = load(run / "oracles.json")
    contract_mismatches = 0
    for case in cases:
        output, digest = expected_outputs[case["case_id"]]
        oracle_mismatches += int(oracles.get(case["case_id"]) != output)
        for method in METHODS:
            contract = contracts[case["case_id"]][method]
            normalized = validate_contract(contract)
            contract_mismatches += int(
                normalized["task"] != "partial_context"
                or normalized["queries"] != 64
                or contract["contract_id"] != f"c36:{case['case_id']}:{method}"
                or contract["validation"]["required_output_sha256"] != digest)

    config = spec["config"]
    schedule = load_jsonl(run / "schedule.jsonl")
    validate_schedule(schedule, cases, config["blocks"])
    schedule_map = {(row["block"], row["case_id"]): row for row in schedule}
    measurements = load_jsonl(run / "measurements.jsonl")
    measurement_mismatches = 0
    for row in measurements:
        planned = schedule_map.get((row["block"], row["case_id"]))
        output, digest = expected_outputs[row["case_id"]]
        timings = row["timings_ns"]
        identity = row["identity"]
        setup = timings["input_decode_ns"] + timings["representation_ns"]
        measurement_mismatches += int(
            planned is None or row["method"] not in METHODS or row["status"] != "ok"
            or row["method_position"] != planned["method_order"].index(row["method"])
            or row["order_sha256"] != planned["order_sha256"]
            or row["artifact_sha256"] != digest
            or row["artifact_bytes"] != len(canonical_bytes(output))
            or identity["semantic_output"] != output
            or identity["exact_check_passed"] is not True
            or identity["expression_v2_sha256"]
            != next(case["expression_v2_sha256"] for case in cases
                    if case["case_id"] == row["case_id"])
            or identity["setup_total_ns"] != setup
            or identity["checkpoint_query_ns"]["64"] != timings["query_total_ns"]
            or timings["task_total_ns"] != sum(
                value for key, value in timings.items() if key != "task_total_ns")
            or any(identity["checkpoint_total_ns"][str(checkpoint)]
                   != setup + identity["checkpoint_query_ns"][str(checkpoint)]
                   + timings["cleanup_ns"] for checkpoint in CHECKPOINTS)
        )

    recomputed = independent_summary(
        measurements,
        speedup_gate=config["cm_speedup_gate"],
        case_fraction_gate=config["cm_case_fraction_gate"],
        router_budget_ns=config["charged_router_budget_ns"],
        routing_speedup_gate=config["routing_speedup_gate"],
    )
    summary_mismatches = int(recomputed != results.get("summary"))
    controls = load(run / "functional_controls.json")
    probes = load(run / "external_functional_probes.json")
    control_mismatches = int(
        controls.get("all_passed") is not True
        or controls.get("training") is not False
        or controls.get("policy_refit") is not False
        or probes.get("status") != "passed"
        or any(row.get("exact_check_passed") is not True
               for group in (probes["autoref_bdd"], probes["cadical"])
               for row in group["rows"])
    )
    if any((trace_mismatches, oracle_mismatches, contract_mismatches,
            measurement_mismatches, summary_mismatches, control_mismatches)):
        raise RuntimeError("C36 independent verification failed")
    verification = {
        "schema": "crse-c36-independent-verification/v1",
        "status": "verified",
        "dataset_cases_replayed": len(cases),
        "queries_replayed": len(cases) * 64,
        "measurement_rows_checked": len(measurements),
        "timed_queries_checked": len(measurements) * 64,
        "contracts_checked": len(cases) * len(METHODS),
        "external_probe_rows_checked": (len(probes["autoref_bdd"]["rows"])
                                        + len(probes["cadical"]["rows"])),
        "trace_mismatches": 0,
        "oracle_mismatches": 0,
        "contract_mismatches": 0,
        "measurement_mismatches": 0,
        "summary_mismatches": 0,
        "control_mismatches": 0,
        "summary_recomputed_independently": True,
        "training_performed": False,
        "policy_refit": False,
        "results_sha256": sha256(run / "results.json"),
        "manifest_sha256": sha256(run / "manifest.json"),
        "production_write": False,
        "production_promotion": False,
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
