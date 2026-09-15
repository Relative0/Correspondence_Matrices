from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.gf2_wide_repeated_queries import (
    CHECKPOINTS, METHODS, execute_session, oracle_document, project_truth_vector,
    projection_indices, restrict_full_truth, task_contract, validate_dataset,
    validate_query_trace,
)
from cmbench.comparative.gf2_wide_repeated_query_experiment import (
    C36Config, build_schedule, summarize, validate_schedule,
)
from cmbench.recognition.yosys_wide_restriction_data import (
    candidate_pool, select_candidates,
)
from scripts.crse_gf2_wide_repeated_query_verify import independent_summary


ROOT = Path(__file__).resolve().parents[1]


def dataset() -> dict:
    return json.loads((ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json")
                      .read_text(encoding="utf-8"))


def test_c36_source_selection_is_frozen_before_semantics_and_balanced():
    pool = candidate_pool()
    selected = select_candidates(pool)
    assert len(pool) == 30
    assert len(selected) == 18
    assert {n: sum(len(candidate.variable_specs) == n for candidate in selected)
            for n in range(11, 17)} == {n: 3 for n in range(11, 17)}
    assert validate_dataset(dataset()) == {"cases": 18, "queries": 1152}


def test_c36_compiled_projection_matches_independent_scalar_projection():
    case = dataset()["cases"][0]
    bits = int(case["truth_bits_hex"], 16)
    vector = np.unpackbits(np.frombuffer(bits.to_bytes((1 << case["n_vars"]) // 8, "little"),
                                         dtype=np.uint8), bitorder="little")
    for query in case["c36_trace"][:8]:
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        remaining, expected = restrict_full_truth(bits, case["n_vars"], fixed)
        plan = projection_indices(case["n_vars"], fixed, query["remaining_order"])
        assert remaining == tuple(query["remaining_order"])
        assert project_truth_vector(vector, plan) == expected


def test_c36_all_timed_methods_deliver_the_same_exact_query_document():
    case = dataset()["cases"][0]
    expected = hashlib.sha256(canonical_bytes(oracle_document(case, case["c36_trace"]))).hexdigest()
    assert expected == case["c36_required_output_sha256"]
    results = [execute_session(case=case, contract=task_contract(case, method), method=method)
               for method in METHODS]
    assert {result["artifact"]["sha256"] for result in results} == {expected}
    assert all(result["identity"]["exact_check_passed"] for result in results)
    assert all(result["timings_ns"]["task_total_ns"] == sum(
        value for key, value in result["timings_ns"].items() if key != "task_total_ns")
               for result in results)


def test_c36_trace_contract_and_oracle_tampering_fail_closed():
    case = dataset()["cases"][0]
    assert validate_query_trace(case["c36_trace"], case["case_id"], case["n_vars"])
    contract = task_contract(case, METHODS[0])
    with pytest.raises(ValueError):
        execute_session(case=case, contract=contract, method=METHODS[1])
    changed = copy.deepcopy(case)
    changed["c36_trace"][0]["fixed"][0]["value"] ^= 1
    with pytest.raises(ValueError):
        execute_session(case=changed, contract=contract, method=METHODS[0])
    wrong = copy.deepcopy(contract)
    wrong["validation"]["required_output_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        execute_session(case=case, contract=wrong, method=METHODS[0])


def test_c36_schedule_and_summary_are_deterministic():
    cases = [{"case_id": f"case-{i}", "family": f"family-{i}", "n_vars": 11 + i}
             for i in range(2)]
    schedule = build_schedule(cases, 8, 17)
    assert schedule == build_schedule(cases, 8, 17)
    validate_schedule(schedule, cases, 8)
    rows = []
    base = {method: 1000 + index * 100 for index, method in enumerate(METHODS)}
    base["cm_ir_words"] = 900
    for block in range(8):
        for case in cases:
            for method in METHODS:
                rows.append({"case_id": case["case_id"], "family": case["family"],
                             "n_vars": case["n_vars"], "method": method,
                             "identity": {"setup_total_ns": base[method],
                                 "checkpoint_query_ns": {str(q): q * 10 for q in CHECKPOINTS},
                                 "checkpoint_total_ns": {str(q): base[method] + q * 10
                                                         for q in CHECKPOINTS}}})
    summary = summarize(rows, speedup_gate=1.05, case_fraction_gate=0.75)
    verified = independent_summary(
        rows, speedup_gate=1.05, case_fraction_gate=0.75,
        router_budget_ns=123_400, routing_speedup_gate=1.05,
    )
    assert summary == verified
    assert summary["checkpoints"]["64"]["best_fixed_method"] == "cm_ir_words"
    assert summary["cm_break_even_query_count_vs_flattened_cse"] == 1
    changed = copy.deepcopy(schedule)
    changed[0]["order_sha256"] = "0" * 64
    with pytest.raises(ValueError): validate_schedule(changed, cases, 8)


def test_c36_config_is_frozen():
    C36Config(run_id="test").validate()
    with pytest.raises(ValueError): C36Config(run_id="test", blocks=4).validate()
