from __future__ import annotations

import json
from pathlib import Path

from cmbench.comparative.gf2_native_portfolio_experiment import (
    METHODS,
    NativePortfolioConfig,
    execute_portfolio_session,
    summarize,
)
from cmbench.comparative.gf2_native_slots import load_native_slot_library
from cmbench.comparative.gf2_projection_optimization_experiment import _digest
from cmbench.comparative.gf2_wide_repeated_queries import oracle_document
from scripts.crse_native_portfolio_development_verify import verify_run


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json"
LIBRARY = (
    ROOT / "docs/recognition/runs/native-fused-slot-development-20260902-002"
    / "native/cm_fused_slots.dll"
)
RUN = ROOT / "docs/recognition/runs/native-portfolio-development-20260903-001"


def test_portfolio_closes_the_known_exact_engine_surface() -> None:
    assert NativePortfolioConfig("test").blocks == 2 * len(METHODS)
    assert METHODS == (
        "r2_per_query",
        "cse_bigint",
        "cse_words",
        "cm_ir_bigint",
        "cm_ir_words",
        "projection_u16_tuple",
        "native_fused_slots",
    )


def test_all_portfolio_arms_match_one_exposed_case() -> None:
    if not LIBRARY.is_file():
        return
    library = load_native_slot_library(LIBRARY)
    case = json.loads(DATASET.read_text(encoding="utf-8"))["cases"][0]
    expected = _digest(oracle_document(case, case["c36_trace"]))
    rows = []
    for method in METHODS:
        row = execute_portfolio_session(
            case=case, method=method, library=library,
            expected_digest=expected)
        assert row["output_sha256"] == expected
        row.update({
            "block": 0, "case_position": 0, "method_position": METHODS.index(method),
            "method_order": list(METHODS),
        })
        rows.append(row)
        memory = dict(row)
        memory["role"] = "memory_profile"
        memory["resources"] = {
            **row["resources"], "tracemalloc_peak_bytes": 1,
        }
        rows.append(memory)
    summary = summarize(rows, [case])
    assert summary["cases"] == 1
    assert sum(summary["per_case_winner_counts"].values()) == 1
    assert summary["oracle_speedup_over_best_fixed"] == 1.0


def test_retained_native_portfolio_artifact_replays_read_only() -> None:
    result = verify_run(RUN)
    assert result["status"] == "verified"
    assert result["queries_replayed_independently"] == 18 * 64
    assert result["source_mismatches"] == 0
