from __future__ import annotations

import copy

import pytest

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Or, Var, Xor
from cmbench.comparative.gf2_decomposition import decomposition_contract, delivered_sha256
from cmbench.comparative.gf2_method_table import METHODS, execute_method, interaction_min_cut
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2
from cmbench.recognition.gf2_task_dispatcher import SCREENED
from cmbench.recognition.gf2_work_policy import freeze_policy
from cmbench.recognition.gf2_work_policy_compiler import compile_work_policy
from cmbench.recognition.portfolio import reference_bits


def fixture():
    expression = Xor(And(Var(0), Var(1)), Or(Var(2), Var(3)))
    bits = reference_bits(expression, 4)
    case = {"case_id": "fixture", "n_vars": 4, "truth_bits_hex": format(bits, "x"),
            "expression_v2": expr_to_json_dag(expression)}
    best = analyze_exact_gf2(bits, 4).best
    best = best.to_dict() if best else None
    contract = decomposition_contract(
        contract_id="fixture", n_vars=4, required_output_sha256=delivered_sha256(best))
    policy = freeze_policy(
        selected_candidate="test", tree={"kind": "leaf", "arm": SCREENED},
        dataset_sha256="a" * 64, calibration_sha256="b" * 64,
        development_rows=1, validation_rows=1, candidate_validation={})
    return case, best, contract, compile_work_policy(policy)


def test_every_c21_method_delivers_the_same_exact_best_artifact():
    case, best, contract, compiled = fixture()
    results = [execute_method(
        case=case, contract=contract, method=method, required_best=best,
        compiled_policy=compiled if method == "cm_compiled_screened" else None)
        for method in METHODS]
    assert {row["artifact"]["sha256"] for row in results} == {delivered_sha256(best)}
    assert all(row["identity"]["best_artifact"] == best for row in results)
    assert all(row["identity"]["exact_check_passed"] for row in results)
    assert all(row["timings_ns"]["task_total_ns"] == sum(
        value for key, value in row["timings_ns"].items() if key != "task_total_ns")
               for row in results)


def test_interaction_min_cut_is_deterministic_and_bounded():
    assert interaction_min_cut(((0, 1), (2, 3)), 4) == (0, 1)
    with pytest.raises(ValueError):
        interaction_min_cut(((0, 4),), 4)


def test_truth_or_required_artifact_tamper_is_refused():
    case, best, contract, _compiled = fixture()
    changed = copy.deepcopy(case)
    changed["truth_bits_hex"] = "0"
    with pytest.raises(RuntimeError):
        execute_method(case=changed, contract=contract, method="cm_screened", required_best=best)
    with pytest.raises(ValueError):
        execute_method(case=case, contract=contract, method="cm_screened", required_best=None)

