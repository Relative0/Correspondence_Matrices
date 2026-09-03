from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Or, Var, Xor
from cmbench.comparative.gf2_natural_headroom import (
    DECOMPOSITION_METHODS,
    TRUTH_METHODS,
    build_dataset_manifest,
    complete_partitions,
    decomposition_task_contract,
    execute_decomposition_method,
    execute_truth_method,
    local_backend_eligibility,
    select_decomposition_case_ids,
    truth_contract,
    validate_dataset_manifest,
)
from cmbench.comparative.gf2_natural_headroom_experiment import (
    C34Config,
    build_schedule,
    summarize_task,
    validate_schedule,
)
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2, truth_sha256
from cmbench.recognition.portfolio import reference_bits
from cmbench.comparative.contracts import canonical_bytes
from scripts.crse_gf2_natural_headroom_verify import independent_summary


ROOT = Path(__file__).resolve().parents[1]


def fixture_case():
    expression = Xor(And(Var(0), Var(1)), Or(Var(2), Var(3)))
    bits = reference_bits(expression, 4)
    document = expr_to_json_dag(expression)
    import hashlib

    return {
        "case_id": "c34-fixture",
        "cluster_id": "fixture",
        "family": "fixture",
        "n_vars": 4,
        "truth_bits_hex": format(bits, "x"),
        "truth_sha256": truth_sha256(bits, 4),
        "expression_v2": document,
        "expression_v2_sha256": hashlib.sha256(canonical_bytes(document)).hexdigest(),
        "selection_sha256": "a" * 64,
    }


def test_c34_manifest_replays_source_roles_and_selection(tmp_path):
    source = ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset.json"
    verification = ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset_verification.json"
    manifest = build_dataset_manifest(
        source,
        verification,
        source_relative="docs/recognition/c23_yosys_fresh_gf2_dataset.json",
        verification_relative="docs/recognition/c23_yosys_fresh_gf2_dataset_verification.json",
    )
    document = json.loads(source.read_text(encoding="utf-8"))
    assert validate_dataset_manifest(manifest, document) == {"cases": 48, "decomposition_cases": 15}
    assert {row["case_id"] for row in manifest["cases"] if row["decomposition_role"]} == \
        set(select_decomposition_case_ids(document["cases"]))
    changed = copy.deepcopy(manifest)
    changed["cases"][0]["truth_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        validate_dataset_manifest(changed, document)


def test_every_truth_method_delivers_the_same_canonical_complete_relation():
    case = fixture_case()
    results = [execute_truth_method(
        case=case,
        contract=truth_contract(case, method=method),
        method=method,
    ) for method in TRUTH_METHODS]
    assert len({row["artifact"]["sha256"] for row in results}) == 1
    assert all(row["identity"]["exact_check_passed"] for row in results)
    assert all(row["artifact"]["kind"] == "packed_bigint" for row in results)
    assert all(row["timings_ns"]["task_total_ns"] == sum(
        value for key, value in row["timings_ns"].items() if key != "task_total_ns")
               for row in results)


def test_every_decomposition_method_uses_the_complete_universe_and_global_best():
    case = fixture_case()
    bits = int(case["truth_bits_hex"], 16)
    partitions = complete_partitions(case["n_vars"])
    oracle = analyze_exact_gf2(bits, case["n_vars"], row_partitions=partitions)
    best = oracle.best.to_dict() if oracle.best else None
    results = [execute_decomposition_method(
        case=case,
        contract=decomposition_task_contract(case, method=method, required_best=best),
        method=method,
        required_best=best,
    ) for method in DECOMPOSITION_METHODS]
    assert len(partitions) == 7
    assert len({row["artifact"]["sha256"] for row in results}) == 1
    assert all(row["identity"]["best_artifact"] == best for row in results)
    assert all(row["identity"]["partitions_tested"] == len(partitions) for row in results)
    assert all(row["resources"]["complete_partition_universe"] for row in results)


def test_truth_best_and_task_contract_tampering_fail_closed():
    case = fixture_case()
    contract = truth_contract(case, method="direct_ast_bitset")
    changed = copy.deepcopy(contract)
    changed["validation"]["required_output_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        execute_truth_method(case=case, contract=changed, method="direct_ast_bitset")
    changed_case = copy.deepcopy(case)
    changed_case["truth_bits_hex"] = "0"
    with pytest.raises(ValueError):
        execute_truth_method(case=changed_case, contract=contract, method="direct_ast_bitset")

    bits = int(case["truth_bits_hex"], 16)
    oracle = analyze_exact_gf2(bits, 4, row_partitions=complete_partitions(4))
    best = oracle.best.to_dict() if oracle.best else None
    decomposition_contract = decomposition_task_contract(
        case, method=DECOMPOSITION_METHODS[0], required_best=best)
    with pytest.raises(ValueError):
        execute_decomposition_method(
            case=case,
            contract=decomposition_contract,
            method=DECOMPOSITION_METHODS[0],
            required_best=None,
        )


def test_c34_schedule_and_headroom_summary_are_deterministic():
    cases = [
        {"case_id": f"case-{index}", "cluster_id": f"cluster-{index}", "n_vars": 3 + index}
        for index in range(3)
    ]
    methods = ("a", "b", "c")
    rows = build_schedule(cases, methods, 6, 17, "complete_relation")
    assert rows == build_schedule(cases, methods, 6, 17, "complete_relation")
    validate_schedule(rows, cases, methods, 6)
    measurements = []
    times = {"a": (1000, 1100, 1200), "b": (900, 1300, 1000), "c": (1200, 900, 1300)}
    for block in range(6):
        for index, case in enumerate(cases):
            for method in methods:
                measurements.append({
                    "case_id": case["case_id"],
                    "n_vars": case["n_vars"],
                    "method": method,
                    "timings_ns": {"task_total_ns": times[method][index] + block % 2},
                })
    summary = summarize_task(
        measurements,
        methods,
        router_budget_ns=100,
        actionable_speedup_gate=1.05,
        actionable_case_fraction=0.75,
    )
    assert summary["cases"] == 3
    assert summary["best_fixed_method"] == "b"
    assert summary["per_case_oracle_speedup_over_best_fixed"] > 1
    assert summary["width_rule"]["post_hoc_retrospective"] is True
    assert independent_summary(
        measurements,
        methods,
        router_budget_ns=100,
        speedup_gate=1.05,
        case_fraction_gate=0.75,
    ) == summary
    changed = copy.deepcopy(rows)
    changed[0]["order_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        validate_schedule(changed, cases, methods, 6)


def test_c34_frozen_config_and_backend_eligibility_boundary():
    C34Config(run_id="test").validate()
    with pytest.raises(ValueError):
        C34Config(run_id="test", truth_blocks=6).validate()
    eligibility = local_backend_eligibility()
    assert eligibility["complete_relation"]["autoref_bdd"]["timed"] is False
    assert eligibility["gf2_decomposition"]["sat"]["task_eligible"] is False
    assert eligibility["production_promotion"] is False
