"""Session-analysis checks for scientific admission and pseudo-replication."""
from copy import deepcopy
import math

import pytest

from cmbench.benchmark_contracts import SCHEMA, mechanism_attribution
from cmbench.biology_session_analysis import analyze_sessions


def row(arm="raw_factorized", instance="a", cluster="family-a", repeat=0, time=2.0,
        q=1, count="1", **extra):
    result = {"schema": SCHEMA, "arm": arm, "mechanism_attribution": mechanism_attribution(arm),
              "instance_id": instance, "cluster_id": cluster, "partition": "diagnostic",
              "environment_id": "local", "input_sha256": "a" * 64, "query_schedule_sha256": "b" * 64,
              "source_manifest_sha256": "c" * 64, "perturbation_semantics": "clamp",
              "repetition": repeat, "queries": q, "status": "ok", "memory_scope": "process_peak",
              "peak_memory_bytes": 1234, "timing_seconds": {"cold_construction": 0.0,
              "preparation": 0.0, "warm_queries": time, "total_session": time},
              "outputs": [{"count": count, "satisfiable": int(count) > 0,
                           "witness": {"x": True} if int(count) else None,
                           "witness_validated": True, "witness_backend": arm} for _ in range(q)],
              "query_plan_sha256": ["d" * 64] * q}
    result.update(extra)
    return result


def pair(instance="a", cluster="family-a", repeat=0, ratio=.5, **extra):
    return [row(instance=instance, cluster=cluster, repeat=repeat, **extra),
            row("prepared_cm_factorized", instance, cluster, repeat, time=2 * ratio, **extra)]


def test_equal_family_weighting_and_repeats_are_not_independent_models():
    rows = pair(ratio=.25) + pair("b", "family-a", ratio=1) + pair("c", "family-b", ratio=2)
    rows += [x for repeat in range(1, 20) for x in pair("b", "family-a", repeat, ratio=1)]
    result = analyze_sessions(rows)
    summary = result["comparisons"][0]["summary"]
    assert summary["measurement_pairs"] == 22
    assert summary["paired_instances"] == 3
    assert math.isclose(summary["equal_family_geometric_mean_ratio"], 1)
    assert math.isclose(summary["equal_instance_geometric_mean_ratio"], .5 ** (1 / 3))
    assert summary["phase_totals_seconds"]["baseline"]["total_session"] == 6
    assert summary["confidence_interval_95"] is None
    assert not result["heldout_acceptance"]["eligible"]


def test_order_independence_and_no_mutation():
    rows = pair() + pair("b", "family-b", ratio=2)
    original = deepcopy(rows)
    assert analyze_sessions(rows) == analyze_sessions(list(reversed(rows)))
    assert rows == original


def test_failure_and_mismatch_reporting_is_order_independent():
    rows = pair() + [row("cadical195_enumeration", count="2")]
    rows += pair("b", "family-b")
    rows[-1].update(status="timeout", failure_reason="deadline", outputs=None)
    assert analyze_sessions(rows) == analyze_sessions(list(reversed(rows)))


def test_single_repeat_single_cluster_has_no_interval_or_gate_even_if_labeled_held_out():
    result = analyze_sessions(pair(partition="held_out"))
    summary = result["comparisons"][0]["summary"]
    assert summary["single_repeat_instances"] == 1
    assert summary["leave_one_family_out"] == {}
    assert summary["confidence_interval_95"] is None
    assert result["heldout_acceptance"]["passed"] is None


@pytest.mark.parametrize("status", ["timeout", "unsupported", "resource_limit", "backend_error"])
def test_failed_cells_are_retained_and_never_imputed_as_completed_runtime(status):
    rows = pair()
    rows[1].update(status=status, failure_reason="bounded execution", outputs=None)
    result = analyze_sessions(rows)
    assert result["failures"][0]["status"] == status
    assert result["unpaired_or_failed"][0]["reason"] == "non_successful_arm"
    assert result["comparisons"][0]["summary"]["paired_instances"] == 0
    assert result["comparisons"][0]["summary"]["equal_family_geometric_mean_ratio"] is None


def test_different_valid_witnesses_do_not_create_a_count_mismatch():
    rows = pair()
    rows[1]["outputs"][0]["witness"] = {"x": False}
    result = analyze_sessions(rows)
    assert result["correctness_mismatches"] == []
    assert result["comparisons"][0]["summary"]["paired_instances"] == 1


def test_count_mismatch_against_independent_control_excludes_timing_pair():
    rows = pair() + [row("cadical195_enumeration", count="2")]
    result = analyze_sessions(rows)
    assert result["correctness_mismatches"]
    assert result["unpaired_or_failed"][0]["reason"] == "correctness_mismatch"


def test_sat_disagreement_is_exposed():
    rows = pair()
    rows[1]["outputs"] = [{"count": "0", "satisfiable": False, "witness": None}]
    result = analyze_sessions(rows)
    assert {x["field"] for x in result["correctness_mismatches"][0]["differences"]} == {"count", "satisfiable"}


def test_duplicate_and_inconsistent_instance_identity_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        analyze_sessions([row(), row()])
    with pytest.raises(ValueError, match="conflicting"):
        analyze_sessions([row(), row("prepared_cm_factorized", cluster="another")])


def test_missing_arm_and_mismatched_schedule_are_not_paired():
    result = analyze_sessions([row("prepared_cm_factorized")])
    assert result["unpaired_or_failed"][0]["reason"] == "missing_raw_factorized_baseline"
    result = analyze_sessions([row()])
    assert result["unpaired_or_failed"][0]["reason"] == "missing_prepared_cm_candidate"
    rows = pair()
    rows[1]["query_schedule_sha256"] = "e" * 64
    assert analyze_sessions(rows)["unpaired_or_failed"][0]["reason"] == "unmatched_semantic_or_environment_identity"


def test_plan_identity_confounds_and_modes_are_distinct():
    rows = pair() + pair(reuse_mode="rebuild")
    canonical = row("prepared_cm_factorized", time=1, representation_mode="cm_canonical")
    canonical["query_plan_sha256"] = ["e" * 64]
    rows.append(canonical)
    result = analyze_sessions(rows)
    assert len(result["comparisons"]) == 3
    confounded = next(x for x in result["comparisons"] if x["representation_mode"] == "cm_canonical")
    assert confounded["plan_attribution_counts"] == {"preprocessing_topology_confounded": 1}
    matched = next(x for x in result["comparisons"] if x["reuse_mode"] == "retained" and x["representation_mode"] == "matched")
    assert matched["plan_attribution_counts"] == {"identical_normalized_plans_same_declared_evaluator": 1}


def test_missing_plan_identity_unresolved_and_malformed_hash_rejected():
    rows = pair()
    del rows[1]["query_plan_sha256"]
    assert analyze_sessions(rows)["comparisons"][0]["plan_attribution_counts"] == {"unresolved_missing_plan_identity": 1}
    rows[1]["query_plan_sha256"] = ["not-a-hash"]
    with pytest.raises(ValueError, match="ordered SHA-256"):
        analyze_sessions(rows)


def test_large_decimal_counts_remain_exact_and_session_sizes_do_not_pool():
    rows = pair(q=8, count=str(2 ** 1000)) + pair(q=64, count=str(2 ** 1000))
    result = analyze_sessions(rows)
    assert [x["queries"] for x in result["comparisons"]] == [8, 64]
    assert not result["correctness_mismatches"]


def test_zero_elapsed_success_is_not_an_infinite_or_zero_speedup():
    rows = pair(ratio=0)
    result = analyze_sessions(rows)
    assert result["unpaired_or_failed"][0]["reason"] == "nonpositive_total_session"


def test_empty_input_returns_explicit_empty_summary():
    result = analyze_sessions([])
    assert result["row_count"] == 0
    assert result["comparisons"] == []
    assert result["heldout_acceptance"]["passed"] is None
