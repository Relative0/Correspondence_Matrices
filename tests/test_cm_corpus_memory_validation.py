import hashlib
import json
from pathlib import Path

import pytest

from scripts.cm_corpus_memory_validation import (
    EXPECTED_CALLS,
    EXPECTED_CASES,
    EXPECTED_JOBS,
    canonical_sha256,
    compile_scalar_dag,
    evaluation_context,
    freeze_selection,
    load_selection,
    make_jobs,
    parse_proc_status,
    scalar_oracle_sha256,
    summarize,
    validate_child_job,
)


def _all_ops_document():
    return {
        "version": 2,
        "nodes": [
            {"op": "var", "i": 0},
            {"op": "var", "i": 1},
            {"op": "not", "a": 1},
            {"op": "and", "a": 0, "b": 2},
            {"op": "or", "a": 0, "b": 1},
            {"op": "xor", "a": 3, "b": 4},
            {"op": "imp", "a": 3, "b": 4},
            {"op": "eqv", "a": 5, "b": 6},
        ],
        "root": 7,
    }


def test_scalar_oracle_covers_all_ops_and_msb_assignment_order():
    document = _all_ops_document()
    assert compile_scalar_dag(document)[2] == (0, 1)
    assert scalar_oracle_sha256(document, ("x0", "x1"), {}) == hashlib.sha256(bytes([0b1010])).hexdigest()
    assert scalar_oracle_sha256(document, ("x0",), {"x1": 0}) == hashlib.sha256(bytes([0])).hexdigest()


def test_scalar_oracle_refuses_noncanonical_or_incomplete_inputs():
    document = _all_ops_document()
    bad_root = {**document, "root": 6}
    with pytest.raises(ValueError, match="root"):
        compile_scalar_dag(bad_root)
    with pytest.raises(ValueError, match="exactly cover"):
        scalar_oracle_sha256(document, ("x0",), {})


def test_epfl_context_reverses_live_axes_and_fixes_dead_syntactic_input():
    document = {
        "version": 2,
        "nodes": [
            {"op": "var", "i": 0},
            {"op": "var", "i": 1},
            {"op": "not", "a": 1},
            {"op": "and", "a": 1, "b": 2},
            {"op": "xor", "a": 0, "b": 3},
        ],
        "root": 4,
    }
    record = {
        "expression_v2": document,
        "sem_support_size": 1,
        "synt_support_size": 2,
        "synt_support_inputs": ["a", "b"],
        "sem_support_inputs": ["a"],
    }
    variables, fixed = evaluation_context("epfl", record)
    assert variables == ("x0",)
    assert fixed == {"x1": 0}
    assert scalar_oracle_sha256(document, variables, fixed) == hashlib.sha256(bytes([0b10])).hexdigest()
    assert scalar_oracle_sha256(document, ("x1", "x0"), {}) == hashlib.sha256(bytes([0b1010])).hexdigest()


def test_proc_status_parser_keeps_rss_and_hwm_separate():
    parsed = parse_proc_status("Name:\tpython\nVmHWM:\t 123 kB\nVmRSS:\t 100 kB\n")
    assert parsed == {"rss_bytes": 100 * 1024, "hwm_bytes": 123 * 1024}
    with pytest.raises(ValueError, match="malformed VmRSS"):
        parse_proc_status("VmRSS: 12 MB\n")


def test_frozen_selection_is_balanced_and_outcome_independent():
    manifest = freeze_selection()
    assert manifest["schema"] == "cm-corpus-memory-selection/v1"
    assert len(manifest["cases"]) == EXPECTED_CASES
    assert manifest["execution"]["planned_jobs"] == EXPECTED_JOBS
    assert manifest["execution"]["planned_calls"] == EXPECTED_CALLS
    roles = [case["role"] for case in manifest["cases"]]
    assert roles.count("calibration-corpus") == 17
    assert roles.count("heldout-corpus") == 18
    dead_axis = [case for case in manifest["cases"] if case["syntactic_k"] > case["k"]]
    assert [(case["corpus"], case["k"], case["syntactic_k"]) for case in dead_axis] == [("epfl", 10, 11)]


def test_selection_round_trip_and_planned_grid(tmp_path: Path):
    manifest = freeze_selection()
    path = tmp_path / "selection.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    loaded, records = load_selection(path)
    oracles = {case["case_id"]: {"live_output_sha256": "0" * 64} for case in loaded["cases"]}
    jobs = make_jobs(loaded, records, oracles)
    assert len(jobs) == EXPECTED_JOBS
    assert sum(job["repetitions"] for job in jobs) == EXPECTED_CALLS
    assert all(canonical_sha256(job["record"]) == job["record_sha256"] for job in jobs)


def test_selection_rejects_corpus_hash_drift(tmp_path: Path):
    manifest = freeze_selection()
    manifest["corpora"]["bx1"]["sha256"] = "0" * 64
    path = tmp_path / "selection.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="corpus hash/size mismatch"):
        load_selection(path)


def test_child_gate_refuses_local_execution(monkeypatch):
    monkeypatch.setattr("scripts.cm_corpus_memory_validation.sys.platform", "win32")
    monkeypatch.delenv("RUNPOD_POD_ID", raising=False)
    with pytest.raises(ValueError, match="Runpod Linux"):
        validate_child_job({})


def test_summary_does_not_claim_calibration_or_real_workload():
    rows = [
        {
            "status": "ok", "exact": True, "role": "heldout-corpus", "schedule": "cold",
            "representation": "dense", "candidate": {"temporary_bytes": 120},
            "legacy_estimate": 80, "tracemalloc_peak_bytes": 100,
        }
    ]
    rss = [{"sampled_rss_peak_bytes": 1000, "kernel_hwm_peak_bytes_observed": 1200}]
    result = summarize(rows, rss, {"case": {"frozen_truth_sha256": "a" * 64}})
    assert result["calibration_performed"] is False
    assert result["production_estimator_accepted"] is False
    assert result["real_workload_compatibility"].startswith("not measured")
