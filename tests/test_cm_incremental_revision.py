from collections import Counter, OrderedDict

import cm_ir
import pytest
from cmbench.comparative import incremental_revision as subject
from scripts import cm_incremental_revision_verify as verifier


def test_normalize_cnf_is_semantic_and_deterministic():
    clauses = [[2, 1, 1], [1, 2], [3, -3, 1], [-2], [-2]]
    assert subject.normalize_cnf(clauses, 3) == ((-2,), (1, 2))
    assert subject.normalize_cnf([[], [1]], 3) == ((),)
    assert subject.normalize_cnf([], 3) == ()


def test_direct_cnf_bits_uses_x0_as_least_significant_assignment_bit():
    assert subject.direct_cnf_bits(((1,),), 2) == 0b1010
    assert subject.direct_cnf_bits(((-2,),), 2) == 0b0011
    assert subject.direct_cnf_bits(((1,), (-2,)), 2) == 0b0010


def test_independent_raw_cnf_verifier_handles_duplicate_and_tautological_clauses():
    raw = [[1, 1], [2, -2, 1], [-2], [-2]]
    assert verifier.raw_cnf_bits(raw, 2) == subject.direct_cnf_bits(subject.normalize_cnf(raw, 2), 2)
    with pytest.raises(ValueError, match="duplicate JSON key"):
        verifier.strict_json('{"a":1,"a":2}')


def test_incremental_radix_reuses_unchanged_regions_and_changes_source_identity():
    layout = subject.IncrementalRadixLayout()
    earlier = subject.normalize_cnf([[1, 2], [-1, 3], [2, -3], [1]], 3)
    later = subject.normalize_cnf([[1, 2], [-1, 3], [2, -3], [-2]], 3)
    first = layout.expression(earlier, 3)
    second = layout.expression(later, 3)
    repeated = layout.expression(later, 3)
    assert first.identity != second.identity
    assert second.clause_hits >= 3
    assert second.branch_hits >= 1
    assert repeated.expression is second.expression
    assert repeated.identity == second.identity


def test_incremental_layout_lru_is_bounded_and_reports_eviction():
    layout = subject.IncrementalRadixLayout(max_entries=2)
    layout.expression(subject.normalize_cnf([[1], [2], [3]], 3), 3)
    assert len(layout.entries) <= 2
    assert layout.evictions > 0


def test_isolated_persistent_cache_restores_process_state():
    original_pool = cm_ir._PERSISTENT_IR_CACHE
    original_limit = cm_ir._PERSISTENT_IR_CACHE_MAXSIZE
    with subject.isolated_persistent_cm_cache(3) as pool:
        assert pool == OrderedDict()
        assert cm_ir._PERSISTENT_IR_CACHE is pool
        assert cm_ir._PERSISTENT_IR_CACHE_MAXSIZE == 3
    assert cm_ir._PERSISTENT_IR_CACHE is original_pool
    assert cm_ir._PERSISTENT_IR_CACHE_MAXSIZE == original_limit


def test_all_arms_return_the_same_version_delta_with_bounded_caches():
    earlier = subject.normalize_cnf([[1, 2], [-1, 3], [2, -3]], 3)
    later = subject.normalize_cnf([[1, 2], [-1, 3], [-2, -3]], 3)
    oracle = (subject.direct_cnf_bits(earlier, 3), subject.direct_cnf_bits(later, 3))
    rows = [
        subject.run_arm_pair(
            arm,
            earlier,
            later,
            3,
            oracle,
            evaluation_repetitions=2,
            expression_cache_max_entries=8,
            cm_cache_max_entries=8,
        )
        for arm in subject.ARMS
    ]
    assert all(row["exact"] for row in rows)
    assert len({row["earlier_packed_sha256"] for row in rows}) == 1
    assert len({row["later_packed_sha256"] for row in rows}) == 1
    assert len({row["changed_packed_sha256"] for row in rows}) == 1
    incremental = next(row for row in rows if row["arm"] == "cm_incremental_radix")
    assert incremental["invalidation_identity_changed"]
    assert incremental["persistent_size_after_update"] <= 8
    assert incremental["persistent_evictions_total"] > 0


def test_frozen_natural_corpus_and_split_are_source_closed():
    cases = subject.load_cases()
    assert len(cases) == 120
    assert Counter(case["split"] for case in cases) == {"development": 78, "confirmation": 42}
    assert {case["k"] for case in cases} == {8, 12, 16}
    assert {case["slice_kind"] for case in cases} == {"incidence", "hash"}
    assert len({case["transition_id"] for case in cases}) == 20


def test_one_real_case_matches_saved_artifacts_in_every_arm():
    case = subject.load_cases()[0]
    rows = subject.run_case(case, rounds=1, evaluation_repetitions=1)
    assert len(rows) == len(subject.ARMS)
    assert all(row["exact"] for row in rows)
    assert len({row["earlier_packed_sha256"] for row in rows}) == 1
    assert len({row["later_packed_sha256"] for row in rows}) == 1


def test_summary_keeps_incremental_and_current_persistent_controls_separate():
    rows = []
    timings = {
        "cm_cold": (100, 200, 100, 100),
        "cm_persistent": (50, 100, 80, 200),
        "cm_incremental_radix": (40, 80, 50, 220),
        "cse_flat": (30, 60, 40, 100),
        "raw_flat": (150, 300, 120, 90),
    }
    for case in subject.load_cases():
        change = subject.structural_change(case["earlier_residual"], case["later_residual"], case["k"])
        changed = change["normalized_clauses_added"] + change["normalized_clauses_removed"] > 0
        for arm, values in timings.items():
            rows.append({
                "case_id": case["case_id"],
                "history": case["history"],
                "split": case["split"],
                "round": 0,
                "arm": arm,
                "exact": True,
                "update_construction_ns": values[0],
                "resident_pair_construction_ns": values[1],
                "evaluation_pair_ns": values[2],
                "retained_python_bytes": values[3],
                "layout_clause_hits_update": int(arm == "cm_incremental_radix"),
                "layout_branch_hits_update": 0,
                "persistent_hits_update": int(arm == "cm_incremental_radix"),
                "invalidation_identity_changed": changed,
                "program_identity_changed": changed,
                **change,
            })
    summary = subject.summarize(rows)
    assert summary["row_count"] == 600
    assert summary["confirmation_case_count"] == 42
    assert summary["incremental_update_over_cold_cm"]["geomean"] == 0.4
    assert summary["current_persistent_update_over_cold_cm"]["geomean"] == 0.5
    assert summary["incremental_retained_over_current_persistent_cm"]["max_case_ratio"] == 1.1
    assert set(summary["current_persistent_total_over_cse_flat_by_q"]) == {
        str(q) for q in subject.QUERY_COUNTS
    }
