from __future__ import annotations

import json

import pytest

from scripts import cm_overnight_local_portfolio as campaign


def test_portfolio_group_classification():
    assert campaign.portfolio_group("tests/test_cm_epfl_context_pilot.py") == "hardware"
    assert campaign.portfolio_group("tests/test_feature_mapping.py") == "feature_models"
    assert campaign.portfolio_group("tests/test_gf2_decomposition.py") == "affine"
    assert campaign.portfolio_group("tests/test_projected_counts.py") == "exact_controls"
    assert campaign.portfolio_group("tests/test_packed_stream_io.py") == "lifecycle"


def test_small_plan_is_bound_and_valid():
    path = "tests/test_cm_overnight_local_portfolio.py"
    plan = campaign.build_plan([path])
    assert plan["coverage"] == {"core_and_synthetic": 1}
    assert plan["cells"][0]["path"] == path
    campaign.validate_plan(plan)


def test_partial_verification_checks_log_and_junit_hashes(tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    plan = campaign.build_plan(["tests/test_cm_overnight_local_portfolio.py"])
    campaign.write_new(output / "PLAN.json", plan)
    row = {
        "schema": campaign.ROW_SCHEMA,
        "cell_id": plan["cells"][0]["cell_id"],
        "path": plan["cells"][0]["path"],
        "input_sha256": plan["cells"][0]["input_sha256"],
        "group": plan["cells"][0]["group"],
        "priority": plan["cells"][0]["priority"],
        "status": "passed",
        "reason": "pytest_passed",
        "completed_utc": campaign.utc_now(),
        "supervisor": {"cleanup_verified": True},
        "logs": {},
        "junit": None,
    }
    campaign.append_row(output / "ledger.jsonl", row)
    result = campaign.verify(output, require_complete=False)
    assert result == {"status": "passed", "rows": 1, "cells": 1, "complete": True}
    assert json.loads((output / "PLAN.json").read_text())["plan_sha256"]


def test_execution_lock_refuses_concurrent_controller(tmp_path):
    with campaign.execution_lock(tmp_path):
        with pytest.raises(RuntimeError, match="already locked"):
            with campaign.execution_lock(tmp_path):
                pass
    assert not (tmp_path / "EXECUTION.lock").exists()
