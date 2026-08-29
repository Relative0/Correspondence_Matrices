from __future__ import annotations

def print_partial_context_summary_table(df_agg) -> None:
    print("\n=== Partial Context Summary ===")
    if df_agg is None or len(df_agg) == 0:
        print("(no rows)")
        return
    cols = [
        "n_vars",
        "partial_context_count",
        "partial_context_style",
        "partial_remaining_var_count_median_median",
        "partial_bitset_full_recompute_total_s_median",
        "partial_cm_no_cache_total_s_median",
        "partial_cm_cache_total_s_median",
        "partial_robdd_total_s_median",
        "speedup_cm_cache_vs_cm_no_cache_median",
        "ratio_cm_cache_over_robdd_restrict_median",
        "trials",
    ]
    present = [c for c in cols if c in df_agg.columns]
    print(df_agg[present].to_string(index=False))


def print_expression_family_summary_table(df_agg) -> None:
    print("\n=== Expression Family Summary ===")
    if df_agg is None or len(df_agg) == 0:
        print("(no rows)")
        return
    cols = [
        "n_vars",
        "family_size",
        "family_variant_style",
        "family_reuse_ratio_median",
        "family_bitset_total_time_s_median",
        "family_cm_no_cache_total_time_s_median",
        "family_cm_cache_total_time_s_median",
        "family_robdd_build_total_time_s_median",
        "speedup_cm_cache_vs_cm_no_cache_median",
        "ratio_cm_cache_over_bitset_median",
        "trials",
    ]
    present = [c for c in cols if c in df_agg.columns]
    print(df_agg[present].to_string(index=False))


def print_operator_difference_summary_table(df_agg) -> None:
    print("\n=== Operator Difference / Quotient Summary ===")
    if df_agg is None or len(df_agg) == 0:
        print("(no rows)")
        return
    cols = [
        "n_vars",
        "operator_pair_style",
        "operator_diff_mode",
        "opdiff_bitset_total_time_s_median",
        "opdiff_robdd_total_time_s_median",
        "cm_quotient_total_time_s_median",
        "opdiff_cm_dense_total_time_s_median",
        "opdiff_cm_struct_delta_time_s_median",
        "a_minus_b_features_median",
        "b_minus_a_features_median",
        "symmetric_delta_features_median",
        "jaccard_features_median",
        "a_contains_b_all",
        "b_contains_a_all",
        "trials",
    ]
    present = [c for c in cols if c in df_agg.columns]
    print(df_agg[present].to_string(index=False))


def print_summary_table(agg):
    print("\n=== Summary (per n_vars) ===")
    if agg is None or len(agg) == 0:
        print("(no rows)")
        return
    if "robdd_equiv_build_total_time_s_median" in agg.columns:
        def fnum(x):
            try:
                xf = float(x)
                if xf != xf:
                    return f"{'nan':>10}"
                return f"{xf:>10.6f}"
            except Exception:
                return f"{'--':>10}"

        def fbool(x):
            if x is None:
                return "NA"
            try:
                if x != x:
                    return "NA"
            except Exception:
                pass
            return "T" if bool(x) else "F"

        print(
            "Timing policy: equivalence construction/evaluation time is reported separately from the final compare call."
        )
        print(
            "Columns: n | style | ROBDD_build | ROBDD_cmp_per | ROBDD_total | ROBDD_OK | "
            "Bitset_eval | Bitset_cmp | Bitset_total | Bitset_OK | "
            "CM_compile | CM_eval | CM_cmp | CM_total | CM_OK | SymPy_time | SymPy_OK | trials"
        )
        for _, row in agg.sort_values("n_vars").iterrows():
            trials = int(row.get("trials", 0) or 0)
            print(
                f"{int(row['n_vars']):>2} | {str(row.get('equiv_pair_style', '')):>15} | "
                f"{fnum(row.get('robdd_equiv_build_total_time_s_median'))} | "
                f"{fnum(row.get('robdd_equiv_compare_per_call_time_s_median'))} | "
                f"{fnum(row.get('robdd_equiv_total_time_s_median'))} | "
                f"{fbool(row.get('robdd_equiv_ok_all')):>8} | "
                f"{fnum(row.get('bitset_equiv_eval_total_time_s_median'))} | "
                f"{fnum(row.get('bitset_equiv_compare_time_s_median'))} | "
                f"{fnum(row.get('bitset_equiv_total_time_s_median'))} | "
                f"{fbool(row.get('bitset_equiv_ok_all')):>9} | "
                f"{fnum(row.get('cm_equiv_compile_total_time_s_median'))} | "
                f"{fnum(row.get('cm_equiv_eval_total_time_s_median'))} | "
                f"{fnum(row.get('cm_equiv_compare_time_s_median'))} | "
                f"{fnum(row.get('cm_equiv_total_time_s_median'))} | "
                f"{fbool(row.get('cm_equiv_ok_all')):>5} | "
                f"{fnum(row.get('sympy_equiv_time_s_median'))} | "
                f"{fbool(row.get('sympy_equiv_ok_all')):>8} | {trials:>6}"
            )
        return
    if "cm_layout" in agg.columns and not agg.empty:
        print(f"CM layout mode: {agg.iloc[0]['cm_layout']}")
    has_hybrid_compare = "cm_hybrid_time_s_median" in agg.columns and agg["cm_hybrid_time_s_median"].notna().any()
    has_partial_compare = (
        "cm_partial_hybrid_time_s_median" in agg.columns and agg["cm_partial_hybrid_time_s_median"].notna().any()
    )
    has_no_reinflate = (
        "cm_hybrid_no_reinflate_time_s_median" in agg.columns
        and agg["cm_hybrid_no_reinflate_time_s_median"].notna().any()
    )
    has_parallel = "cm_parallel_time_s_median" in agg.columns and agg["cm_parallel_time_s_median"].notna().any()
    has_pair_metrics = "pair_attempts_median" in agg.columns and agg["pair_attempts_median"].notna().any()
    print(
        "Timing policy: `cm_time_s`, `cm_hybrid_time_s`, `cm_partial_hybrid_time_s`, `cm_parallel_time_s`, "
        "and `bitset_time_s` are backend compute-only (TT extraction/conversion is excluded and reported separately)."
    )
    if has_pair_metrics:
        print("Pair metrics: attempts/collapses/ratio/nodes are reported for the baseline CM run when `--cm-pair` is enabled.")
    pair_header = "Pair_attempts_med | Pair_collapses_med | Pair_ratio_med | Pair_nodes_med | " if has_pair_metrics else ""
    if has_hybrid_compare or has_partial_compare or has_no_reinflate:
        header = (
            "Columns: n | CM_med_s | CM_hybrid_med_s | CM_partial_hybrid_med_s | CM_parallel_med_s | Bitset_med_s | "
            + ("CM_hybrid_no_reinflate_med_s | " if has_no_reinflate else "")
            + "CM_hybrid/CM | CM_hybrid/Bitset | CM_partial_hybrid/CM | CM_partial_hybrid/Bitset | "
            + ("NoReinflate/CM | NoReinflate/Hybrid | NoReinflate/Bitset | " if has_no_reinflate else "")
            + "CM_parallel/CM | CM_parallel/Bitset | "
            + f"{pair_header}"
            + "Numba_compile_med_s | Numba_med_s | ROBDD_med_s | dd_med_s | "
            + "Sympy_simpl_med_s | BDD_SOP_med_s | Espresso_med_s | ROBDD_nodes_med | "
            + "dd_nodes_med | CM_nodes_med | CM_OK | CM_hybrid_OK | CM_partial_hybrid_OK | CM_parallel_OK | Bitset_OK | "
            + ("CM_hybrid_no_reinflate_OK | " if has_no_reinflate else "")
            + "Numba_OK | Sympy_OK | Sympy_OK_count/trials | ROBDD_OK | BDD_SOP_OK | Espresso_OK | trials"
        )
        print(header)
    else:
        print(
            "Columns: n | CM_med_s | CM_parallel_med_s | Bitset_med_s | "
            "CM_parallel/CM | CM_parallel/Bitset | "
            f"{pair_header}"
            "Numba_compile_med_s | Numba_med_s | ROBDD_med_s | dd_med_s | "
            "Sympy_simpl_med_s | BDD_SOP_med_s | Espresso_med_s | ROBDD_nodes_med | "
            "dd_nodes_med | CM_nodes_med | CM_OK | CM_parallel_OK | Bitset_OK | "
            "Numba_OK | Sympy_OK | Sympy_OK_count/trials | ROBDD_OK | BDD_SOP_OK | Espresso_OK | trials"
        )
    for _, row in agg.sort_values("n_vars").iterrows():
        fnum = (
            lambda x: f"{x:>10.6f}"
            if isinstance(x, float) and not (x != x)
            else f"{'nan':>10}"
        )
        fint = lambda x: 0 if (x is None or (isinstance(x, float) and (x != x))) else int(x)
        fbool = lambda x: "OK" if x is True else ("--" if x is None else "NO")
        trials = int(row["trials"] or 0)
        okc = int(row.get("sympy_ok_count") or 0)
        pair_values = (
            f"{fnum(row.get('pair_attempts_median'))} | {fnum(row.get('pair_collapses_median'))} | "
            f"{fnum(row.get('pairable_ratio_median'))} | {fnum(row.get('pair_nodes_total_median'))} | "
            if has_pair_metrics
            else ""
        )
        if has_hybrid_compare or has_partial_compare or has_no_reinflate:
            no_reinflate_time = (
                f"{fnum(row.get('cm_hybrid_no_reinflate_time_s_median'))} | " if has_no_reinflate else ""
            )
            no_reinflate_ratios = (
                f"{fnum(row.get('ratio_cm_hybrid_no_reinflate_over_cm'))} | "
                f"{fnum(row.get('ratio_cm_hybrid_no_reinflate_over_cm_hybrid'))} | "
                f"{fnum(row.get('ratio_cm_hybrid_no_reinflate_over_bitset'))} | "
                if has_no_reinflate
                else ""
            )
            no_reinflate_ok = (
                f"{fbool(row.get('cm_hybrid_no_reinflate_ok_all')):>23} | " if has_no_reinflate else ""
            )
            print(
                f"{int(row['n_vars']):>2} | {fnum(row['cm_time_s_median'])} | {fnum(row['cm_hybrid_time_s_median'])} | "
                f"{fnum(row['cm_partial_hybrid_time_s_median'])} | {fnum(row['cm_parallel_time_s_median'])} | "
                f"{fnum(row['bitset_time_s_median'])} | "
                f"{no_reinflate_time}"
                f"{fnum(row['ratio_cm_hybrid_over_cm'])} | {fnum(row['ratio_cm_hybrid_over_bitset'])} | "
                f"{fnum(row['ratio_cm_partial_hybrid_over_cm'])} | {fnum(row['ratio_cm_partial_hybrid_over_bitset'])} | "
                f"{no_reinflate_ratios}"
                f"{fnum(row['ratio_cm_parallel_over_cm'])} | {fnum(row['ratio_cm_parallel_over_bitset'])} | "
                f"{pair_values}"
                f"{fnum(row['numba_compile_time_s_median'])} | {fnum(row['numba_time_s_median'])} | "
                f"{fnum(row['bdd_time_s_median'])} | {fnum(row['dd_time_s_median'])} | {fnum(row['sympy_time_s_median'])} | "
                f"{fnum(row['bdd_sop_time_s_median'])} | {fnum(row['espresso_time_s_median'])} | "
                f"{fint(row['bdd_nodes_median']):>15} | {fint(row['dd_nodes_median']):>12} | {fint(row['cm_nodes_median']):>12} | "
                f"{fbool(row.get('cm_ok_all')):>5} | {fbool(row.get('cm_hybrid_ok_all')):>12} | "
                f"{fbool(row.get('cm_partial_hybrid_ok_all')):>20} | {fbool(row.get('cm_parallel_ok_all')):>14} | "
                f"{fbool(row.get('bitset_ok_all')):>9} | "
                f"{no_reinflate_ok}"
                f"{fbool(row.get('numba_ok_all')):>8} | {fbool(row['sympy_ok_all']):>7} | {okc}/{trials:>5} | "
                f"{fbool(row.get('robdd_ok_all')):>9} | {fbool(row['bdd_sop_ok_all']):>11} | "
                f"{fbool(row['espresso_ok_all']):>11} | {trials:>6}"
            )
        else:
            print(
                f"{int(row['n_vars']):>2} | {fnum(row['cm_time_s_median'])} | {fnum(row['cm_parallel_time_s_median'])} | "
                f"{fnum(row['bitset_time_s_median'])} | {fnum(row['ratio_cm_parallel_over_cm'])} | "
                f"{fnum(row['ratio_cm_parallel_over_bitset'])} | {pair_values}"
                f"{fnum(row['numba_compile_time_s_median'])} | "
                f"{fnum(row['numba_time_s_median'])} | {fnum(row['bdd_time_s_median'])} | {fnum(row['dd_time_s_median'])} | "
                f"{fnum(row['sympy_time_s_median'])} | {fnum(row['bdd_sop_time_s_median'])} | {fnum(row['espresso_time_s_median'])} | "
                f"{fint(row['bdd_nodes_median']):>15} | {fint(row['dd_nodes_median']):>12} | {fint(row['cm_nodes_median']):>12} | "
                f"{fbool(row.get('cm_ok_all')):>5} | {fbool(row.get('cm_parallel_ok_all')):>14} | "
                f"{fbool(row.get('bitset_ok_all')):>9} | {fbool(row.get('numba_ok_all')):>8} | {fbool(row['sympy_ok_all']):>7} | "
                f"{okc}/{trials:>5} | {fbool(row.get('robdd_ok_all')):>9} | {fbool(row['bdd_sop_ok_all']):>11} | "
                f"{fbool(row['espresso_ok_all']):>11} | {trials:>6}"
            )

    if "cm_hybrid_no_reinflate_ir_compile_time_s_median" in agg.columns and agg[
        "cm_hybrid_no_reinflate_ir_compile_time_s_median"
    ].notna().any():
        def fnum_small(x):
            if x is None:
                return f"{'--':>10}"
            try:
                xf = float(x)
                if xf != xf:
                    return f"{'nan':>10}"
                return f"{xf:>10.6f}"
            except Exception:
                return f"{'--':>10}"

        print("\n=== IR Breakdown (CM_hybrid_no_reinflate medians) ===")
        print(
            "Columns: n | ir_compile | ir_intern | ir_canon | ir_rewrite | ir_live_vars | ir_other | "
            "nr_bitset_eval | nr_fallback_mat_ir | nr_tt_vector_build"
        )
        for _, row in agg.sort_values("n_vars").iterrows():
            print(
                f"{int(row['n_vars']):>2} | "
                f"{fnum_small(row.get('cm_hybrid_no_reinflate_ir_compile_time_s_median'))} | "
                f"{fnum_small(row.get('cm_hybrid_no_reinflate_ir_intern_time_s_median'))} | "
                f"{fnum_small(row.get('cm_hybrid_no_reinflate_ir_canonicalize_time_s_median'))} | "
                f"{fnum_small(row.get('cm_hybrid_no_reinflate_ir_rewrite_time_s_median'))} | "
                f"{fnum_small(row.get('cm_hybrid_no_reinflate_ir_live_vars_time_s_median'))} | "
                f"{fnum_small(row.get('cm_hybrid_no_reinflate_ir_other_time_s_median'))} | "
                f"{fnum_small(row.get('cm_hybrid_no_reinflate_nr_bitset_eval_time_s_median'))} | "
                f"{fnum_small(row.get('cm_hybrid_no_reinflate_nr_fallback_materialize_ir_time_s_median'))} | "
                f"{fnum_small(row.get('cm_hybrid_no_reinflate_nr_tt_vector_build_time_s_median'))}"
            )

    if (
        "cm_hybrid_no_reinflate_cached_exec_only_time_s_median" in agg.columns
        and agg["cm_hybrid_no_reinflate_cached_exec_only_time_s_median"].notna().any()
    ):
        def fnum_small(x):
            if x is None:
                return f"{'--':>10}"
            try:
                xf = float(x)
                if xf != xf:
                    return f"{'nan':>10}"
                return f"{xf:>10.6f}"
            except Exception:
                return f"{'--':>10}"

        print("\n=== Cached Execution (per-eval medians) ===")
        repeat = int(agg.iloc[0].get("cm_eval_repeat_median") or 0)
        if repeat:
            print(f"Repeat count: {repeat}")
        print("Columns: n | CM_hybrid_no_reinflate_cached_exec_only | Bitset_cached_exec_only | ratio_cached/bitset_cached")
        for _, row in agg.sort_values("n_vars").iterrows():
            print(
                f"{int(row['n_vars']):>2} | "
                f"{fnum_small(row.get('cm_hybrid_no_reinflate_cached_exec_only_time_s_median'))} | "
                f"{fnum_small(row.get('bitset_cached_exec_only_time_s_median'))} | "
                f"{fnum_small(row.get('ratio_cm_hybrid_no_reinflate_cached_over_bitset_cached'))}"
            )
