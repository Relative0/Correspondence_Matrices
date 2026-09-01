from __future__ import annotations

import json
from pathlib import Path

import pytest

from cmbench.comparative.gf2_prepared_shadow_experiment import (
    DISABLED,
    ENABLED,
    C32Config,
    build_schedule,
    execute_shadow_batch,
    run_experiment,
    summarize,
)
from cmbench.comparative.gf2_table_experiment import build_oracles
from cmbench.recognition.gf2_prepared_support_context import (
    prepare_support_policy_context,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "docs/recognition/c27_yosys_fresh_gf2_dataset.json"
C27 = ROOT / "docs/recognition/c27_support_aware_policy.json"
C22 = ROOT / "docs/recognition/c22_source_portfolio_policy.json"
DATASET_VERIFICATION = (
    ROOT / "docs/recognition/c27_yosys_fresh_gf2_dataset_verification.json")
C31_FINAL = ROOT / "docs/recognition/c31_linux_confirmation/RUNPOD_C31_FINAL_VERIFICATION_20260901.json"
C31_ADJUDICATION = ROOT / "docs/recognition/c31_linux_confirmation/C31_CROSS_MACHINE_ADJUDICATION_20260901.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_c32_schedule_is_fully_counterbalanced():
    schedule = build_schedule(C32Config("test-c32"))

    assert len(schedule) == 128
    assert len({(row["block"], row["n_vars"], row["method"]) for row in schedule}) == 128
    assert all(
        sum(row["method"] == method and row["arm_position"] == position
            for row in schedule) == 32
        for method in (DISABLED, ENABLED) for position in range(2)
    )
    assert all(
        sum(row["n_vars"] == n_vars and row["width_position"] == position
            for row in schedule) == 8
        for n_vars in (3, 4, 5, 6) for position in range(4)
    )


def test_enabled_and_disabled_batches_both_serve_only_exact_baseline():
    cases = [case for case in load(DATASET)["cases"] if case["n_vars"] == 3][:8]
    config = C32Config("test-c32-batch", blocks=8)
    _, oracles = build_oracles(cases, config.oracle_config())
    prepared = prepare_support_policy_context(C27, C22)

    disabled = execute_shadow_batch(
        boundary_id="test-c32-disabled",
        method=DISABLED,
        cases=cases,
        oracles=oracles,
        prepared_context=prepared,
    )
    enabled = execute_shadow_batch(
        boundary_id="test-c32-enabled",
        method=ENABLED,
        cases=cases,
        oracles=oracles,
        prepared_context=prepared,
    )

    assert disabled["served_baseline_exact"] is True
    assert disabled["candidate_observations"] == 0
    assert enabled["served_baseline_exact"] is True
    assert enabled["candidate_observations"] == 8
    assert enabled["candidate_divergences"] == 0
    assert disabled["closed_snapshot"]["served_candidate_results"] == 0
    assert enabled["closed_snapshot"]["served_candidate_results"] == 0


def test_generated_c32_evidence_recomputes_and_divergence_fails_closed(tmp_path):
    output = tmp_path / "c32-generated-evidence"
    result = run_experiment(
        C32Config("test-c32-evidence", blocks=8),
        output=output,
        dataset_path=DATASET,
        dataset_verification_path=DATASET_VERIFICATION,
        c27_policy_path=C27,
        c22_policy_path=C22,
        c31_final_path=C31_FINAL,
        c31_adjudication_path=C31_ADJUDICATION,
        root=ROOT,
    )
    rows = load_rows(output / "measurements.jsonl")
    controls = load(output / "functional_controls.json")

    assert summarize(rows, controls) == result["summary"]
    changed = json.loads(json.dumps(rows))
    changed[0]["candidate_divergences"] = 1
    with pytest.raises(ValueError, match="measurement row"):
        summarize(changed, controls)
