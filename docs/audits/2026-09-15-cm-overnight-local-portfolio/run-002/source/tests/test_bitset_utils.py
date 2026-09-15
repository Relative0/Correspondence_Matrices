from cm_exprlib import And, Var, Xor
from cmbench.backends.bitset_utils import bitset_equivalence_check


def test_bitset_equivalence_identical_expressions() -> None:
    expr = And(Var(0), Var(1))
    row = bitset_equivalence_check(expr, expr, 2, expected=True)
    assert row["bitset_equiv_status"] == "ok"
    assert row["bitset_equiv_result"] is True
    assert row["bitset_equiv_ok"] is True


def test_bitset_equivalence_near_miss_expression() -> None:
    expr = And(Var(0), Var(1))
    row = bitset_equivalence_check(expr, Xor(expr, Var(0)), 2, expected=False)
    assert row["bitset_equiv_status"] == "ok"
    assert row["bitset_equiv_result"] is False
    assert row["bitset_equiv_ok"] is True


def test_bitset_equivalence_expected_field_detects_mismatch() -> None:
    expr = And(Var(0), Var(1))
    row = bitset_equivalence_check(expr, Xor(expr, Var(0)), 2, expected=True)
    assert row["bitset_equiv_result"] is False
    assert row["bitset_equiv_ok"] is False


def test_bitset_equivalence_error_schema() -> None:
    row = bitset_equivalence_check(object(), object(), 2, expected=True)
    expected = {
        "bitset_equiv_eval_f_time_s",
        "bitset_equiv_eval_g_time_s",
        "bitset_equiv_eval_total_time_s",
        "bitset_equiv_compare_time_s",
        "bitset_equiv_total_time_s",
        "bitset_equiv_result",
        "bitset_equiv_ok",
        "bitset_equiv_status",
        "bitset_equiv_error",
    }
    assert expected <= set(row)
    assert row["bitset_equiv_status"] == "error"
    assert row["bitset_equiv_error"]
