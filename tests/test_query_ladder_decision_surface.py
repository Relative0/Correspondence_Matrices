from __future__ import annotations

import copy
import json
import sys

import pytest

from cmbench.recognition import learning_benchmark_handoff as benchmark_handoff
from cmbench.recognition import query_ladder_decision_surface as surface
from cmbench.recognition import query_ladder_learning_freeze as query_freeze
from scripts import cm_query_ladder_decision_surface as surface_cli


ARTIFACT = (
    query_freeze.ROOT
    / "docs/recognition/runs/query-ladder-source-blind-learning-freeze-20260904-001"
)
MATERIAL_ARMS = (
    "r2_topological_liveness",
    "cse_flat_bigint",
    "native_fused_slots",
)


@pytest.fixture(scope="module")
def frozen_protocol() -> tuple[dict, str]:
    frozen = json.loads((ARTIFACT / "FREEZE.json").read_text(encoding="utf-8"))
    return frozen, query_freeze.file_sha256(ARTIFACT / "FREEZE.json")


def _evidence(frozen: dict, freeze_sha256: str) -> dict:
    arms = list(frozen["exact_task_contract"]["arms"])
    cases = frozen["cohort"]["cases"]

    def timings(scale: int) -> dict:
        result = {}
        for index, case in enumerate(cases):
            winner = MATERIAL_ARMS[index % len(MATERIAL_ARMS)]
            result[case["case_id"]] = {
                arm: [scale * (100 if arm == winner else 200)] * 16
                for arm in arms
            }
        return result

    replications = []
    for index, (identifier, scale) in enumerate(
        (("machine-a", 1), ("machine-b", 2))
    ):
        block_timings = timings(scale)
        replications.append({
            "replication_id": identifier,
            "physical_machine_sha256": ("a" if index == 0 else "b") * 64,
            "compiler_sha256": ("c" if index == 0 else "d") * 64,
            "independent_verification_sha256": (
                "e" if index == 0 else "f"
            ) * 64,
            "verification_status": "verified_complete",
            "case_set_sha256": frozen["cohort"]["case_set_sha256"],
            "block_timings_ns": block_timings,
            "block_timings_sha256": surface.digest(block_timings),
            "p95_costs_ns_per_case": {
                "feature_extraction_and_control": 1.0 * scale,
                "model_inference": 1.0 * scale,
                "exact_verification": 1.0 * scale,
                "expected_fallback": 1.0 * scale,
            },
            "p95_costs_measured_same_host": True,
            "schedule_mismatches": 0,
            "semantic_mismatches": 0,
            "source_or_artifact_mismatches": 0,
        })
    return {
        "schema": surface.EVIDENCE_SCHEMA,
        "status": "verified_complete",
        "surface_id": surface.SURFACE_ID,
        "freeze_file_sha256": freeze_sha256,
        "task_contract_sha256": query_freeze.digest(
            frozen["exact_task_contract"]
        ),
        "case_set_sha256": frozen["cohort"]["case_set_sha256"],
        "label_policy_sha256": query_freeze.digest(frozen["label_policy"]),
        "baseline_closure": {
            "status": "verified_complete",
            "sha256": "1" * 64,
            "all_relevant_exact_baselines_included": True,
        },
        "surface_independent_verification_sha256": "2" * 64,
        "prospective_cases_consumed": 0,
        "claim_boundary": {
            "development_training_eligibility_permitted": True,
            "prospective_consumption_permitted": False,
            "production_routing_permitted": False,
        },
        "replications": replications,
    }


def _refresh_replication(replication: dict) -> None:
    replication["block_timings_sha256"] = surface.digest(
        replication["block_timings_ns"]
    )


def _result_for_case(assessment: dict, case_id: str) -> dict:
    return next(
        row for row in assessment["case_results"] if row["case_id"] == case_id
    )


def test_raw_blocks_build_an_eligible_v2_handoff(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    evidence = _evidence(frozen, freeze_sha256)
    assessment = surface.assess_decision_surface(
        evidence,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert assessment["status"] == "verified_complete"
    assert assessment["source_groups_per_label"] == {
        "cse_flat_bigint": 24,
        "native_fused_slots": 24,
        "r2_topological_liveness": 24,
    }
    assert assessment["non_abstain_coverage"] == 1.0
    assert assessment["threshold_abstention_cases"] == []
    assert assessment["cross_host_winner_disagreement_cases"] == []

    handoff = surface.build_v2_handoff(
        evidence,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert handoff["schema"] == benchmark_handoff.SCHEMA
    readiness = benchmark_handoff.assess_frozen_handoff_or_abstain(
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert readiness["status"] == "eligible_for_development_experiment_design"
    assert readiness["development_training_eligible"] is True
    assert readiness["minimum_fully_charged_speedup"] > 1.10
    assert readiness["training_performed"] is False
    assert readiness["production_routing_permitted"] is False


def test_frozen_materiality_boundaries_are_inclusive(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    evidence = _evidence(frozen, freeze_sha256)
    case_id = frozen["cohort"]["cases"][0]["case_id"]
    winner = MATERIAL_ARMS[0]
    runner = "cm_ir_bigint"
    for replication in evidence["replications"]:
        scale = 1 if replication["replication_id"] == "machine-a" else 2
        values = replication["block_timings_ns"][case_id]
        values[winner] = [100 * scale] * 16
        values[runner] = ([100 * scale] * 4) + ([103 * scale] * 12)
        _refresh_replication(replication)
    assessment = surface.assess_decision_surface(
        evidence,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    row = _result_for_case(assessment, case_id)
    assert row["joint_label"] == winner
    for result in row["host_results"].values():
        assert result["median_runner_up_speedup"] == pytest.approx(1.03)
        assert result["paired_block_win_fraction"] == pytest.approx(0.75)
        assert result["paired_p10_speedup"] == pytest.approx(1.0)
        assert all(result["conditions"].values())


def test_one_block_below_win_fraction_forces_abstention(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    evidence = _evidence(frozen, freeze_sha256)
    case_id = frozen["cohort"]["cases"][0]["case_id"]
    winner = MATERIAL_ARMS[0]
    runner = "cm_ir_bigint"
    for replication in evidence["replications"]:
        scale = 1 if replication["replication_id"] == "machine-a" else 2
        values = replication["block_timings_ns"][case_id]
        values[winner] = [100 * scale] * 16
        values[runner] = ([100 * scale] * 5) + ([103 * scale] * 11)
        _refresh_replication(replication)
    assessment = surface.assess_decision_surface(
        evidence,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    row = _result_for_case(assessment, case_id)
    assert row["joint_label"] == query_freeze.ABSTAIN_LABEL
    assert row["joint_label_reason"] == "host_threshold_failure"
    assert case_id in assessment["threshold_abstention_cases"]


def test_p10_replays_the_frozen_lower_order_statistic_not_interpolation(
    frozen_protocol,
):
    frozen, freeze_sha256 = frozen_protocol
    evidence = _evidence(frozen, freeze_sha256)
    case_id = frozen["cohort"]["cases"][0]["case_id"]
    winner = MATERIAL_ARMS[0]
    runner = "cm_ir_bigint"
    for replication in evidence["replications"]:
        scale = 1 if replication["replication_id"] == "machine-a" else 2
        values = replication["block_timings_ns"][case_id]
        values[winner] = [100 * scale] * 16
        values[runner] = ([99 * scale] * 2) + ([104 * scale] * 14)
        _refresh_replication(replication)

    assessment = surface.assess_decision_surface(
        evidence,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    row = _result_for_case(assessment, case_id)

    assert row["joint_label"] == query_freeze.ABSTAIN_LABEL
    for result in row["host_results"].values():
        assert result["median_runner_up_speedup"] == pytest.approx(1.04)
        assert result["paired_block_win_fraction"] == pytest.approx(0.875)
        assert result["paired_p10_speedup"] == pytest.approx(0.99)
        assert result["p10_method"].startswith("frozen_lower_order_statistic")


def test_cross_host_winner_flip_forces_abstention(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    evidence = _evidence(frozen, freeze_sha256)
    case_id = frozen["cohort"]["cases"][0]["case_id"]
    values = evidence["replications"][1]["block_timings_ns"][case_id]
    original_winner = MATERIAL_ARMS[0]
    other = "cm_ir_bigint"
    values[original_winner] = [400] * 16
    values[other] = [200] * 16
    _refresh_replication(evidence["replications"][1])
    assessment = surface.assess_decision_surface(
        evidence,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    row = _result_for_case(assessment, case_id)
    assert row["joint_label"] == query_freeze.ABSTAIN_LABEL
    assert row["joint_label_reason"] == "cross_host_winner_disagreement"
    assert assessment["cross_host_winner_disagreement_cases"] == [case_id]


def test_mapping_order_and_uniform_host_scale_do_not_change_labels(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    evidence = _evidence(frozen, freeze_sha256)
    baseline = surface.assess_decision_surface(
        evidence,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    changed = copy.deepcopy(evidence)
    host = changed["replications"][1]
    host["block_timings_ns"] = {
        case_id: dict(reversed(list(values.items())))
        for case_id, values in reversed(list(host["block_timings_ns"].items()))
    }
    for values in host["block_timings_ns"].values():
        for arm in values:
            values[arm] = [value * 3 for value in values[arm]]
    for name in host["p95_costs_ns_per_case"]:
        host["p95_costs_ns_per_case"][name] *= 3
    _refresh_replication(host)
    replay = surface.assess_decision_surface(
        changed,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert replay["label_table_sha256"] == baseline["label_table_sha256"]
    assert replay["source_groups_per_label"] == baseline["source_groups_per_label"]


@pytest.mark.parametrize("failure", ["digest", "missing_arm", "nan"])
def test_malformed_or_tampered_raw_timing_tables_fail_closed(
    frozen_protocol,
    failure,
):
    frozen, freeze_sha256 = frozen_protocol
    evidence = _evidence(frozen, freeze_sha256)
    replication = evidence["replications"][0]
    case_id = frozen["cohort"]["cases"][0]["case_id"]
    if failure == "digest":
        replication["block_timings_ns"][case_id][MATERIAL_ARMS[0]][0] += 1
    elif failure == "missing_arm":
        del replication["block_timings_ns"][case_id]["cm_ir_words"]
        _refresh_replication(replication)
    else:
        replication["block_timings_ns"][case_id][MATERIAL_ARMS[0]][0] = float("nan")
    result = surface.assess_decision_surface_or_abstain(
        evidence,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert result["status"] == "abstained"
    assert result["development_handoff_construction_permitted"] is False
    assert result["training_performed"] is False


def test_single_material_winner_arm_cannot_reach_fitting(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    evidence = _evidence(frozen, freeze_sha256)
    for replication in evidence["replications"]:
        scale = 1 if replication["replication_id"] == "machine-a" else 2
        for values in replication["block_timings_ns"].values():
            for arm in values:
                values[arm] = [scale * (100 if arm == MATERIAL_ARMS[0] else 200)] * 16
        _refresh_replication(replication)
    handoff = surface.build_v2_handoff(
        evidence,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    readiness = benchmark_handoff.assess_frozen_handoff_or_abstain(
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert "fewer_than_two_material_winner_arms" in readiness["blockers"]
    assert readiness["development_training_eligible"] is False


def test_read_only_cli_replays_and_emits_handoff(
    frozen_protocol,
    monkeypatch,
    capsys,
):
    frozen, freeze_sha256 = frozen_protocol
    evidence = _evidence(frozen, freeze_sha256)
    documents = {"evidence.json": evidence, "freeze.json": frozen}
    monkeypatch.setattr(
        surface_cli,
        "_read_json",
        lambda path: documents[path.name],
    )
    monkeypatch.setattr(query_freeze, "file_sha256", lambda _path: freeze_sha256)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cm_query_ladder_decision_surface.py",
            "--evidence",
            "evidence.json",
            "--freeze",
            "freeze.json",
        ],
    )
    assert surface_cli.main() == 0
    assert json.loads(capsys.readouterr().out)[
        "development_handoff_construction_permitted"
    ] is True

    sys.argv.append("--emit-handoff")
    assert surface_cli.main() == 0
    emitted = json.loads(capsys.readouterr().out)
    assert emitted["handoff"]["schema"] == benchmark_handoff.SCHEMA
    assert emitted["readiness"]["development_training_eligible"] is True
