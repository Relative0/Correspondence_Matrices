from cmbench.results.equivalence import skipped_equiv_result


def test_skipped_equiv_result_preserves_legacy_columns():
    expected = {
        "bitset_equiv": [
            "bitset_equiv_eval_f_time_s",
            "bitset_equiv_eval_g_time_s",
            "bitset_equiv_eval_total_time_s",
            "bitset_equiv_compare_time_s",
            "bitset_equiv_total_time_s",
            "bitset_equiv_result",
            "bitset_equiv_ok",
            "bitset_equiv_status",
            "bitset_equiv_error",
        ],
        "cm_equiv": [
            "cm_equiv_compile_f_time_s",
            "cm_equiv_compile_g_time_s",
            "cm_equiv_compile_total_time_s",
            "cm_equiv_eval_f_time_s",
            "cm_equiv_eval_g_time_s",
            "cm_equiv_eval_total_time_s",
            "cm_equiv_compare_time_s",
            "cm_equiv_total_time_s",
            "cm_equiv_result",
            "cm_equiv_ok",
            "cm_equiv_status",
            "cm_equiv_error",
        ],
        "sympy_equiv": [
            "sympy_equiv_time_s",
            "sympy_equiv_result",
            "sympy_equiv_ok",
            "sympy_equiv_status",
            "sympy_equiv_error",
        ],
    }

    for prefix, columns in expected.items():
        row = skipped_equiv_result(prefix)
        assert list(row) == columns
        assert row[f"{prefix}_status"] == "skipped"

