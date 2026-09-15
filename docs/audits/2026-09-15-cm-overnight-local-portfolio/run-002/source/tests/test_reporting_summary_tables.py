import pandas as pd

from cmbench.reporting.summary_tables import (
    print_expression_family_summary_table,
    print_partial_context_summary_table,
    print_summary_table,
)


def test_print_summary_table_empty_dataframe(capsys) -> None:
    print_summary_table(pd.DataFrame())
    out = capsys.readouterr().out
    assert "Summary" in out


def test_print_summary_table_minimal_normal_row(capsys) -> None:
    print_summary_table(
        pd.DataFrame(
            [
                {
                    "n_vars": 2,
                    "cm_time_s_median": 0.1,
                    "cm_parallel_time_s_median": None,
                    "bitset_time_s_median": 0.2,
                    "ratio_cm_parallel_over_cm": None,
                    "ratio_cm_parallel_over_bitset": None,
                    "numba_compile_time_s_median": None,
                    "numba_time_s_median": None,
                    "bdd_time_s_median": None,
                    "dd_time_s_median": None,
                    "sympy_time_s_median": None,
                    "bdd_sop_time_s_median": None,
                    "espresso_time_s_median": None,
                    "bdd_nodes_median": None,
                    "dd_nodes_median": None,
                    "cm_nodes_median": 3,
                    "cm_ok_all": True,
                    "cm_parallel_ok_all": None,
                    "bitset_ok_all": True,
                    "numba_ok_all": None,
                    "sympy_ok_all": None,
                    "robdd_ok_all": None,
                    "bdd_sop_ok_all": None,
                    "espresso_ok_all": None,
                    "correct_count": 1,
                    "trials": 1,
                }
            ]
        )
    )
    out = capsys.readouterr().out
    assert "Columns:" in out
    assert " 2 |" in out


def test_workload_summary_tables_handle_missing_optional_columns(capsys) -> None:
    print_partial_context_summary_table(pd.DataFrame([{"n_vars": 4, "trials": 1}]))
    print_expression_family_summary_table(pd.DataFrame([{"n_vars": 4, "trials": 1}]))
    out = capsys.readouterr().out
    assert "Partial Context Summary" in out
    assert "Expression Family Summary" in out
