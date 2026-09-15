from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from cmbench.backends.affine_constraints import AffineConstraintPlan
from scripts import cm_benchmark_core_screen as screen


ROOT = Path(__file__).resolve().parents[1]
ADMISSION = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign/prelaunch-008/ADMISSION_LEDGER.json"
EVIDENCE_REQUIRED = pytest.mark.skipif(
    not ADMISSION.exists(),
    reason="frozen campaign evidence is excluded from the source-only integration",
)


@EVIDENCE_REQUIRED
def test_frozen_plan_is_deterministic_balanced_and_pre_outcome():
    first = screen.build_plan(ADMISSION)
    second = screen.build_plan(ADMISSION)
    first.pop("created_utc")
    second.pop("created_utc")
    first.pop("plan_sha256")
    second.pop("plan_sha256")
    assert first == second
    plan = screen.build_plan(ADMISSION)
    screen.validate_plan(plan)
    assert len(plan["cells"]) == 192
    counts = {}
    for cell in plan["cells"]:
        counts[cell["lane"]] = counts.get(cell["lane"], 0) + 1
    assert counts == {
        "exact_count": 48,
        "projected_count": 24,
        "biology_fixed_points": 72,
        "affine_solution_count": 48,
    }
    biology = [row for row in plan["cases"] if row["lane"] == "biology_fixed_points"]
    assert len({row["path"] for row in biology}) == 12
    assert all(row["metadata"]["functions"] <= 16 for row in biology)
    exact = [row for row in plan["cases"] if row["lane"] == "exact_count"]
    assert all(row["metadata"]["declared_support_variables"] == 0 for row in exact)


@EVIDENCE_REQUIRED
def test_plan_digest_and_cell_identity_fail_closed():
    plan = screen.build_plan(ADMISSION)
    changed = copy.deepcopy(plan)
    changed["cells"][0]["arm"] = "injected"
    with pytest.raises(ValueError, match="plan digest"):
        screen.validate_plan(changed)


def test_sparse_affine_independent_baseline_matches_packed_plan():
    names = ("a", "b", "c", "d")
    rows = (0b0011, 0b0110, 0b1100)
    for rhs in ((0, 0, 0), (1, 0, 1), (1, 1, 1)):
        assert screen.sparse_affine_count(rows, rhs, 4) == AffineConstraintPlan(rows, rhs, names).count()
    contradiction_rows = (0b0011, 0b0011)
    contradiction_rhs = (0, 1)
    assert screen.sparse_affine_count(contradiction_rows, contradiction_rhs, 4) == 0


def test_summary_keeps_unpaired_projection_out_of_speedup_claims():
    plan = {"plan_sha256": "a" * 64}
    rows = [
        {"lane": "affine_solution_count", "case_id": "a", "repetition": 0,
         "arm": "cm_packed_elimination", "status": "ok", "wall_ns": 10, "value_sha256": "v"},
        {"lane": "affine_solution_count", "case_id": "a", "repetition": 0,
         "arm": "sparse_set_elimination", "status": "ok", "wall_ns": 20, "value_sha256": "v"},
        {"lane": "projected_count", "case_id": "p", "repetition": 0,
         "arm": "ganak_projected", "status": "ok", "wall_ns": 5, "value_sha256": "p"},
    ]
    summary = screen._summarize(plan, rows)
    assert summary["comparisons"]["affine_solution_count"]["median_ratio"] == 2
    assert "projected_count" not in summary["comparisons"]
    assert "no CM speedup claim" in summary["projected_count_claim_boundary"]


def test_execute_exercises_biology_scalar_and_both_affine_arms(tmp_path):
    biology = tmp_path / "inputs/biological_functions/tiny.bnet"
    biology.parent.mkdir(parents=True)
    biology.write_text("targets,factors\na, a\n", encoding="utf-8")
    biology_case = {
        "case_id": "biology-tiny",
        "path": "inputs/biological_functions/tiny.bnet",
        "input_sha256": screen.digest(biology),
    }
    biology_result = screen.execute({
        "root": str(tmp_path),
        "case": biology_case,
        "cell": {"lane": "biology_fixed_points", "arm": "bnet_cm_scalar"},
    })
    assert biology_result["status"] == "ok"
    assert biology_result["value"] == "2"

    affine = tmp_path / "inputs/affine/tiny.alist"
    affine.parent.mkdir(parents=True)
    affine.write_text("2 1\n1 2\n1 1\n2\n1\n1\n1 2\n", encoding="utf-8")
    affine_case = {
        "case_id": "affine-tiny",
        "path": "inputs/affine/tiny.alist",
        "input_sha256": screen.digest(affine),
    }
    values = []
    for arm in ("cm_packed_elimination", "sparse_set_elimination"):
        result = screen.execute({
            "root": str(tmp_path),
            "case": affine_case,
            "cell": {"lane": "affine_solution_count", "arm": arm},
        })
        assert result["status"] == "ok"
        values.append(result["value"])
    assert values == ["2", "2"]
