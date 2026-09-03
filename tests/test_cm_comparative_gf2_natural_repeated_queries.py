from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Or, Var, Xor
from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.gf2_natural_repeated_queries import (
    CHECKPOINTS,
    METHODS,
    bind_manifest_cases,
    build_query_trace,
    execute_session,
    oracle_document,
    restrict_full_truth,
    task_contract,
    validate_dataset_manifest,
    validate_query_trace,
)
from cmbench.comparative.gf2_natural_repeated_query_experiment import (
    C35Config,
    build_schedule,
    summarize,
    validate_schedule,
)
from cmbench.recognition.gf2_decomposition import truth_sha256
from cmbench.recognition.portfolio import reference_bits
from scripts.crse_gf2_natural_repeated_query_verify import independent_summary


ROOT = Path(__file__).resolve().parents[1]


def fixture_case() -> dict:
    expression = Xor(And(Var(0), Var(1)), Or(Var(2), Var(3)))
    bits = reference_bits(expression, 4)
    document = expr_to_json_dag(expression)
    case = {
        "case_id": "c35-fixture", "cluster_id": "fixture", "family": "fixture",
        "n_vars": 4, "truth_bits_hex": format(bits, "x"),
        "truth_sha256": truth_sha256(bits, 4), "expression_v2": document,
        "expression_v2_sha256": hashlib.sha256(canonical_bytes(document)).hexdigest(),
        "selection_sha256": "a" * 64,
    }
    trace = build_query_trace(case["case_id"], 4)
    case["c35_trace"] = trace
    case["c35_required_output_sha256"] = hashlib.sha256(
        canonical_bytes(oracle_document(case, trace))).hexdigest()
    return case


def test_c35_frozen_manifest_replays_selection_traces_and_oracles():
    manifest = json.loads((ROOT / "docs/recognition/c35_natural_repeated_query_dataset.json")
                          .read_text(encoding="utf-8"))
    source = json.loads((ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset.json")
                        .read_text(encoding="utf-8"))
    assert validate_dataset_manifest(manifest, source) == {"cases": 8, "queries": 512}
    cases = bind_manifest_cases(manifest, source)
    assert [case["n_vars"] for case in cases] == list(range(3, 11))
    changed = copy.deepcopy(manifest)
    changed["cases"][0]["trace"][0]["fixed"][0]["value"] ^= 1
    with pytest.raises(ValueError):
        validate_dataset_manifest(changed, source)


def test_c35_trace_and_truth_projection_are_msb_ordered_and_fail_closed():
    trace = build_query_trace("case", 4)
    assert validate_query_trace(trace, "case", 4) == trace
    changed = copy.deepcopy(trace)
    changed[0]["query_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        validate_query_trace(changed, "case", 4)
    # x0 XOR x1 in MSB-first order has packed truth 0b0110.
    remaining, reduced = restrict_full_truth(0b0110, 2, {"x0": 1})
    assert remaining == ("x1",)
    assert reduced == 0b01


def test_c35_all_methods_deliver_identical_relation_count_sat_and_witness():
    case = fixture_case()
    results = [execute_session(case=case, contract=task_contract(case, method), method=method)
               for method in METHODS]
    assert len({result["artifact"]["sha256"] for result in results}) == 1
    assert all(result["identity"]["exact_check_passed"] for result in results)
    assert all(set(map(int, result["identity"]["checkpoint_total_ns"])) == set(CHECKPOINTS)
               for result in results)
    assert all(result["timings_ns"]["task_total_ns"] == sum(
        value for key, value in result["timings_ns"].items() if key != "task_total_ns")
        for result in results)


def test_c35_contract_and_trace_tampering_fail_closed():
    case = fixture_case()
    contract = task_contract(case, METHODS[0])
    changed = copy.deepcopy(contract)
    changed["validation"]["required_output_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        execute_session(case=case, contract=changed, method=METHODS[0])
    with pytest.raises(ValueError):
        execute_session(case=case, contract=contract, method=METHODS[1])
    changed_case = copy.deepcopy(case)
    changed_case["c35_trace"][0]["fixed"][0]["value"] ^= 1
    with pytest.raises(ValueError):
        execute_session(case=changed_case, contract=contract, method=METHODS[0])


def test_c35_schedule_and_break_even_summary_are_deterministic():
    cases = [{"case_id": f"case-{i}", "n_vars": 3 + i} for i in range(2)]
    schedule = build_schedule(cases, 12, 17)
    assert schedule == build_schedule(cases, 12, 17)
    validate_schedule(schedule, cases, 12)
    rows = []
    base = {method: 1000 + index * 100 for index, method in enumerate(METHODS)}
    base["cm_ir_restrict"] = 900
    for block in range(12):
        for case in cases:
            for method in METHODS:
                checkpoints = {str(q): base[method] + q * (10 + block % 2) for q in CHECKPOINTS}
                rows.append({
                    "case_id": case["case_id"], "n_vars": case["n_vars"], "method": method,
                    "identity": {"setup_total_ns": base[method],
                                 "checkpoint_query_ns": {str(q): q * 10 for q in CHECKPOINTS},
                                 "checkpoint_total_ns": checkpoints},
                })
    summary = summarize(rows, speedup_gate=1.05, case_fraction_gate=0.75)
    assert independent_summary(rows, speedup_gate=1.05, case_fraction_gate=0.75) == summary
    assert summary["checkpoints"]["64"]["best_fixed_method"] == "cm_ir_restrict"
    assert summary["cm_break_even_query_count_vs_flattened_cse"] == 1
    assert summary["cm_break_even_query_count_vs_direct_ast"] == 1
    changed = copy.deepcopy(schedule)
    changed[0]["order_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        validate_schedule(changed, cases, 12)


def test_c35_config_is_frozen():
    C35Config(run_id="test").validate()
    with pytest.raises(ValueError):
        C35Config(run_id="test", blocks=6).validate()
