from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATTERY_PATH = (
    ROOT / "deliverables_n22_24" / "master_explainer_2026_08_03"
    / "use_case_benchmarks_2026-08-27" / "cm_feature_model_representation_battery.py"
)
sys.path.insert(0, str(BATTERY_PATH.parent))
SPEC = importlib.util.spec_from_file_location("cm_feature_model_representation_battery", BATTERY_PATH)
assert SPEC and SPEC.loader
battery = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = battery
SPEC.loader.exec_module(battery)

from cmbench.backends.robdd_dd import expr_to_dd_bdd  # noqa: E402
from dd import autoref  # noqa: E402


def test_synthetic_matrix_is_deterministic_complete_and_planted_satisfiable() -> None:
    cases_a = battery.load_synthetic_cases()
    cases_b = battery.load_synthetic_cases()
    assert len(cases_a) == 54
    assert [case.case_id for case in cases_a] == [case.case_id for case in cases_b]
    assert [case.residual for case in cases_a] == [case.residual for case in cases_b]
    for case in cases_a:
        assert len(case.residual) == case.k * case.metadata["clause_multiplier"]
        assert battery.scalar_residual(case.residual, case.planted_bits)
        assert case.edited_residual is not None
        assert battery.scalar_residual(case.edited_residual, case.planted_bits)


def test_packed_context_mask_matches_scalar_assignment_filter() -> None:
    for k in (4, 8):
        context = {0: True, k - 1: False}
        actual = battery.packed_context_mask(k, context)
        expected = 0
        for assignment in range(1 << k):
            if all(bool((assignment >> variable) & 1) == selected for variable, selected in context.items()):
                expected |= 1 << assignment
        assert actual == expected


def test_robdd_enumeration_preserves_external_lsb_first_assignment_order() -> None:
    residual = ((1,), (-2, 3))
    expression = battery.expression_from_residual(residual, 3)
    manager = autoref.BDD()
    manager.declare("x0", "x1", "x2")
    root = expr_to_dd_bdd(expression, manager, {"x0": "x0", "x1": "x1", "x2": "x2"})
    artifact = battery.BDDArtifact(manager, root, 0, 0, root.dag_size, ("x0", "x1", "x2"), "dd.autoref")
    assert battery.bdd_extract_enumerate(artifact, 3) == battery.cnf_bitset(residual, 3)
    assert battery.bdd_extract_naive(artifact, 3) == battery.cnf_bitset(residual, 3)


def test_synthetic_duplicate_fraction_and_one_clause_edit_contract() -> None:
    case = battery.synthetic_case(8, 64, 0.9, battery.SYNTHETIC_SEEDS[0])
    assert case.metadata["actual_duplicate_fraction"] == (len(case.residual) - len(set(case.residual))) / len(case.residual)
    assert sum(left != right for left, right in zip(case.residual, case.edited_residual)) == 1
    assert battery.cnf_bitset(case.residual, case.k) >> case.planted_bits & 1
    assert battery.cnf_bitset(case.edited_residual, case.k) >> case.planted_bits & 1
