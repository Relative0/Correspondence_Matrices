from __future__ import annotations

import json
from pathlib import Path

import pytest

from cmbench.comparative.gf2_async_shadow_experiment import (
    ASYNC_FULL,
    ASYNC_QUARTER,
    DISABLED,
    METHODS,
    SYNCHRONOUS,
    C33Config,
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
DATASET_VERIFICATION = (
    ROOT / "docs/recognition/c27_yosys_fresh_gf2_dataset_verification.json")
C27 = ROOT / "docs/recognition/c27_support_aware_policy.json"
C22 = ROOT / "docs/recognition/c22_source_portfolio_policy.json"
C31_FINAL = (
    ROOT / "docs/recognition/c31_linux_confirmation/"
    "RUNPOD_C31_FINAL_VERIFICATION_20260901.json")
C31_ADJUDICATION = (
    ROOT / "docs/recognition/c31_linux_confirmation/"
    "C31_CROSS_MACHINE_ADJUDICATION_20260901.json")
C32_SUMMARY = (
    ROOT / "docs/recognition/"
    "learning_milestone_c32_prepared_policy_shadow_results.json")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_c33_schedule_is_fully_counterbalanced():
    schedule = build_schedule(C33Config("test-c33"))

    assert len(schedule) == 256
    assert len({
        (row["block"], row["n_vars"], row["method"]) for row in schedule
    }) == 256
    assert all(
        sum(row["method"] == method and row["arm_position"] == position
            for row in schedule) == 16
        for method in METHODS for position in range(4)
    )
    assert all(
        sum(row["n_vars"] == n_vars and row["width_position"] == position
            for row in schedule) == 16
        for n_vars in (3, 4, 5, 6) for position in range(4)
    )


def test_all_methods_serve_exact_baseline_with_expected_observation_coverage():
    selected = [case for case in load(DATASET)["cases"] if case["n_vars"] == 3][:8]
    config = C33Config("test-c33-batch", blocks=8)
    _, oracles = build_oracles(selected, config.oracle_config())
    prepared = prepare_support_policy_context(C27, C22)

    batches = {
        method: execute_shadow_batch(
            boundary_id=f"test-{method}",
            method=method,
            cases=selected,
            oracles=oracles,
            prepared_context=prepared,
        )
        for method in METHODS
    }

    assert all(batch["served_baseline_exact"] is True for batch in batches.values())
    assert batches[DISABLED]["candidate_observations"] == 0
    assert batches[SYNCHRONOUS]["candidate_observations"] == 8
    assert batches[ASYNC_FULL]["candidate_observations"] == 8
    assert batches[ASYNC_QUARTER]["candidate_observations"] == 2
    assert batches[ASYNC_FULL]["pre_ack_candidate_observations"] == 0
    assert batches[ASYNC_QUARTER]["pre_ack_candidate_observations"] == 0
    assert all(batch["served_candidate_results"] == 0 for batch in batches.values())


def test_generated_c33_evidence_recomputes_and_detects_pre_ack_mutation(tmp_path):
    output = tmp_path / "c33-generated-evidence"
    config = C33Config("test-c33-evidence", blocks=8)
    result = run_experiment(
        config,
        output=output,
        dataset_path=DATASET,
        dataset_verification_path=DATASET_VERIFICATION,
        c27_policy_path=C27,
        c22_policy_path=C22,
        c31_final_path=C31_FINAL,
        c31_adjudication_path=C31_ADJUDICATION,
        c32_summary_path=C32_SUMMARY,
        root=ROOT,
    )
    rows = load_rows(output / "measurements.jsonl")
    controls = load(output / "functional_controls.json")

    assert summarize(rows, controls, config) == result["summary"]
    changed = json.loads(json.dumps(rows))
    async_row = next(row for row in changed if row["method"] == ASYNC_FULL)
    async_row["pre_ack_candidate_observations"] = 1
    with pytest.raises(ValueError, match="before delivery"):
        summarize(changed, controls, config)
