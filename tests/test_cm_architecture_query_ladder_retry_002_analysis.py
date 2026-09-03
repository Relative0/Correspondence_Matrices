from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
RUN = (
    EXECUTION / "runpod-architecture-query-ladder-execute-002/evidence/run-output"
    / "architecture-query-ladder-linux-gcc-20260904-002"
)
ANALYSIS = EXECUTION / "ANALYSIS.json"
MARKDOWN = EXECUTION / "VERIFIED_INTERPRETATION.md"
CONTROLLER = EXECUTION / "runpod-architecture-query-ladder-execute-002/RUN.json"
AUTHORIZATION = (
    EXECUTION / "RUNPOD_ARCHITECTURE_QUERY_LADDER_RETRY_002_EXACT_PAYLOAD_AUTHORIZED_2026_09_04.json"
)
POST_INVENTORY = EXECUTION / "POST_RUN_INVENTORY.json"
ATTEMPT_001 = (
    ROOT / "docs/recognition/architecture_query_ladder_followup_execution_20260903"
    / "ATTEMPT_001_STATUS.json"
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _analysis_module():
    path = ROOT / "scripts/cm_analyze_architecture_query_ladder.py"
    spec = importlib.util.spec_from_file_location("query_ladder_analysis_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_retry_002_evidence_is_complete_exact_and_cleaned_up() -> None:
    analysis = _load(ANALYSIS)
    verification = _load(RUN / "independent_verification.json")
    controller = _load(CONTROLLER)
    post_inventory = _load(POST_INVENTORY)

    assert analysis["status"] == "verified_interpretation_complete"
    assert analysis["inputs"]["results_sha256"] == _sha256(RUN / "results.json")
    assert analysis["inputs"]["independent_verification_sha256"] == _sha256(
        RUN / "independent_verification.json"
    )
    assert analysis["inputs"]["raw_measurements_sha256"] == _sha256(
        RUN / "raw_measurements.jsonl"
    )
    assert analysis["inputs"]["controller_sha256"] == _sha256(CONTROLLER)
    assert analysis["inputs"]["post_run_inventory_sha256"] == _sha256(POST_INVENTORY)
    assert analysis["inputs"]["attempt_001_status_sha256"] == _sha256(ATTEMPT_001)

    assert verification["status"] == "verified_complete"
    assert verification["rows_checked"] == 27_648
    assert verification["query_rows"] == {"1": 6_912, "4": 6_912, "16": 6_912, "64": 6_912}
    assert verification["counts"] == {"ok": 27_648, "refused": 0, "failed": 0}
    assert all(
        verification[field] == 0
        for field in (
            "semantic_mismatches",
            "schedule_mismatches",
            "source_or_artifact_mismatches",
            "memory_measurement_mismatches",
        )
    )

    assert controller["status"] == "complete"
    assert controller["authorization_record_sha256"] == _sha256(AUTHORIZATION)
    assert controller["cleanup"]["owned_pod_absent"] is True
    assert controller["cleanup"]["inventories"] == {"v1": [], "v2": []}
    assert post_inventory["owned_pod_absent"] is True
    assert post_inventory["inventories"] == {"v1": [], "v2": []}
    assert analysis["execution"]["estimated_compute_cost_usd"] < 0.04
    assert analysis["execution"]["combined_estimated_compute_cost_usd"] < 0.05


def test_retry_002_interpretation_preserves_cohorts_and_publication_gates() -> None:
    analysis = _load(ANALYSIS)
    queries = analysis["query_counts"]

    assert [queries[str(q)]["fixed_arm"]["best_fixed_arm"] for q in (1, 4, 16, 64)] == [
        "r2_topological_liveness",
        "r2_topological_liveness",
        "cse_flat_bigint",
        "cse_flat_bigint",
    ]

    native_q64 = queries["64"]["speedup_over_r2"]["native_fused_slots"]
    assert native_q64["case_cluster_geomean_speedup"] == pytest.approx(1.0493485581414423)
    assert native_q64["case_cluster_bootstrap_ci95_low"] == pytest.approx(0.9686135873062082)
    assert native_q64["minimum_case_speedup"] == pytest.approx(0.5671436217268969)
    assert native_q64["observed_regression"]["case_cluster_geomean_speedup"] == pytest.approx(
        1.3278464857082772
    )
    assert native_q64["fresh"]["case_cluster_geomean_speedup"] == pytest.approx(
        0.9328369083353143
    )

    cse_q64 = queries["64"]["speedup_over_r2"]["cse_flat_bigint"]
    assert cse_q64["case_cluster_geomean_speedup"] == pytest.approx(1.1003675355508402)
    assert cse_q64["candidate_case_wins"] == 54
    assert cse_q64["minimum_case_speedup"] == pytest.approx(1.0306431715124937)

    assert analysis["sampled_advantage"]["native_fused_slots"] == {
        "first_q_with_ci_low_above_one": None,
        "first_q_with_point_speedup": 64,
        "interpretation": "first observed sample only; no interpolation beyond q1/q4/q16/q64",
        "point_advantage_at_all_later_sampled_q": True,
    }
    assert analysis["sampled_advantage"]["cse_flat_bigint"]["first_q_with_point_speedup"] == 16
    assert analysis["sampled_advantage"]["cse_flat_bigint"]["first_q_with_ci_low_above_one"] == 64
    assert analysis["publication_gates"] == {
        "all_cells_have_isolated_memory_and_lifecycle_fields": True,
        "all_query_counts_separately_timed": True,
        "cross_machine_replication_passed": False,
        "exact_and_schedule_verification_passed": True,
        "native_minimum_case_floor_passed_at_every_query_count": False,
        "public_update_permitted": False,
    }


def test_retry_002_cleanup_accounting_and_render_are_reproducible() -> None:
    analysis = _load(ANALYSIS)
    raw_rows = [
        json.loads(line)
        for line in (RUN / "raw_measurements.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    cleanup_ns = sum(row["timings_ns"]["cleanup_ns"] for row in raw_rows)
    accounted_ns = sum(row["timings_ns"]["accounted_total_ns"] for row in raw_rows)

    assert cleanup_ns / 1e9 == pytest.approx(analysis["cleanup"]["retry_cleanup_seconds"])
    assert accounted_ns / 1e9 == pytest.approx(analysis["cleanup"]["retry_accounted_seconds"])
    assert cleanup_ns / accounted_ns == pytest.approx(
        analysis["cleanup"]["retry_cleanup_share_of_accounted_time"]
    )
    assert analysis["cleanup"]["retry_cleanup_share_of_accounted_time"] < 0.003
    assert all(row["cleanup_method"] == "cache_clear_then_isolated_child_exit" for row in raw_rows)
    assert all(
        row["memory_measurement"]["isolation_lifecycle_in_accounted_timing"] is False
        for row in raw_rows
    )
    assert all(row["memory_measurement"]["incremental_peak_rss_bytes"] == 0 for row in raw_rows)

    markdown = MARKDOWN.read_text(encoding="utf-8")
    assert _analysis_module().render_markdown(analysis) == markdown
    assert all(line == line.rstrip() for line in markdown.splitlines())
