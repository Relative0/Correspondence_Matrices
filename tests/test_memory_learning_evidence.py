from __future__ import annotations

import copy
import json
import sys

from cmbench.recognition import memory_learning_evidence as memory
from scripts import cm_memory_learning_evidence as memory_cli


ARMS = ["cm_ir_bigint", "native_fused_slots"]


def _measurements() -> dict:
    cases = []
    split_plan = (
        ["development_fit"] * 16
        + ["development_validation"] * 8
        + ["development_audit"] * 8
    )
    for index, split in enumerate(split_plan):
        winner = ARMS[index % 2]
        values = {
            winner: 100_000,
            ARMS[1 - index % 2]: 300_000,
        }
        cases.append({
            "case_id": f"synthetic-multiply-low-cone-{index:02d}",
            "source_group_sha256": f"{index + 1:064x}",
            "split": split,
            "measurements_by_host": {
                "machine-a": dict(values),
                "machine-b": dict(values),
            },
        })
    identities = [
        {
            "case_id": case["case_id"],
            "source_group_sha256": case["source_group_sha256"],
            "split": case["split"],
        }
        for case in cases
    ]
    return {
        "schema": memory.MEASUREMENT_SCHEMA,
        "status": "verified_complete",
        "surface_id": "synthetic-prepared-memory-v1",
        "task_contract_sha256": "a" * 64,
        "case_set_sha256": memory.digest(identities),
        "metric": {
            "name": "prepared_retained_memory",
            "unit": "bytes",
            "lifecycle": "reused",
            "optimization": "minimize",
            "resolution_floor_bytes": 65_536,
            "minimum_relative_runner_up_gap": 0.10,
        },
        "protocol": {
            "role": "source_blind_development",
            "frozen_before_targets": True,
            "source_group_split_isolated": True,
            "prospective_cases_consumed": 0,
            "exact_outputs_verified": True,
            "refused_rows_retained": True,
        },
        "arms": list(ARMS),
        "hosts": [
            {
                "replication_id": "machine-a",
                "physical_machine_sha256": "b" * 64,
                "independent_verification_sha256": "c" * 64,
            },
            {
                "replication_id": "machine-b",
                "physical_machine_sha256": "d" * 64,
                "independent_verification_sha256": "e" * 64,
            },
        ],
        "cases_sha256": memory.digest(cases),
        "cases": cases,
    }


def _neural_protocol(
    measurements: dict,
    seeds: tuple[int, ...] = (11, 23, 47),
) -> dict:
    core = {
        "schema": memory.NEURAL_PROTOCOL_SCHEMA,
        "status": "frozen_before_training_and_evaluation",
        "surface_id": measurements["surface_id"],
        "measurement_cases_sha256": measurements["cases_sha256"],
        "candidate_family_id": "synthetic-tiny-memory-regressor-v1",
        "candidate_spec_sha256": "f" * 64,
        "independent_verification_sha256": "9" * 64,
        "training_seeds": list(seeds),
        "trained_on_splits": ["development_fit"],
        "validation_targets_visible_to_fit": False,
        "audit_targets_visible_to_fit": False,
        "candidate_spec_frozen_before_training": True,
        "candidate_locked_before_audit": True,
        "all_declared_seeds_required": True,
        "prospective_cases_consumed": 0,
    }
    return {**core, "protocol_sha256": memory.digest(core)}


def _predictions(
    measurements: dict,
    *,
    reverse_evaluation: bool = False,
    candidate_kind: str = "analytical",
    training_seed: int | None = None,
    neural_protocol: dict | None = None,
) -> dict:
    rows = []
    for case in measurements["cases"]:
        predicted = dict(case["measurements_by_host"]["machine-a"])
        if reverse_evaluation and case["split"] != "development_fit":
            predicted = {
                ARMS[0]: predicted[ARMS[1]],
                ARMS[1]: predicted[ARMS[0]],
            }
        selected = min(ARMS, key=lambda arm: (predicted[arm], ARMS.index(arm)))
        rows.append({
            "case_id": case["case_id"],
            "predicted_bytes_by_arm": predicted,
            "selected_arm": selected,
        })
    result = {
        "schema": memory.PREDICTION_SCHEMA,
        "status": "development_candidate_predictions",
        "surface_id": measurements["surface_id"],
        "measurement_cases_sha256": measurements["cases_sha256"],
        "candidate_id": (
            f"synthetic-tiny-memory-regressor-seed-{training_seed}"
            if candidate_kind == "tiny_neural"
            else "synthetic-memory-control-v1"
        ),
        "candidate_kind": candidate_kind,
        "trained_on_splits": ["development_fit"],
        "validation_targets_visible_to_fit": False,
        "audit_targets_visible_to_fit": False,
        "prospective_cases_consumed": 0,
        "rows_sha256": memory.digest(rows),
        "rows": rows,
    }
    if candidate_kind == "tiny_neural":
        assert training_seed is not None and neural_protocol is not None
        result["training_seed"] = training_seed
        result["neural_protocol_sha256"] = neural_protocol["protocol_sha256"]
    return result


def _refresh(measurements: dict) -> None:
    measurements["cases_sha256"] = memory.digest(measurements["cases"])


def test_stable_material_memory_surface_is_development_eligible():
    measurements = _measurements()
    result = memory.assess_decision_surface(measurements)
    assert result["status"] == "eligible_for_memory_learning_development"
    assert result["development_training_eligible"] is True
    assert result["source_groups_per_label"] == {
        "cm_ir_bigint": 16,
        "native_fused_slots": 16,
    }
    assert result["non_abstain_coverage"] == 1.0
    assert result["blockers"] == []
    assert result["training_performed"] is False
    assert result["production_routing_permitted"] is False


def test_cross_host_winner_disagreement_becomes_abstention():
    measurements = _measurements()
    case = next(
        row
        for row in measurements["cases"]
        if row["split"] == "development_validation"
    )
    case["measurements_by_host"]["machine-b"] = {
        "cm_ir_bigint": case["measurements_by_host"]["machine-a"][
            "native_fused_slots"
        ],
        "native_fused_slots": case["measurements_by_host"]["machine-a"][
            "cm_ir_bigint"
        ],
    }
    _refresh(measurements)
    result = memory.assess_decision_surface(measurements)
    label = next(
        row["label"] for row in result["labels"] if row["case_id"] == case["case_id"]
    )
    assert label == memory.ABSTAIN_LABEL
    assert result["cross_host_winner_disagreement_cases"] == [case["case_id"]]
    assert result["development_training_eligible"] is True


def test_low_material_coverage_fails_before_any_fit_boundary():
    measurements = _measurements()
    for case in measurements["cases"]:
        if case["split"] == "development_audit":
            for values in case["measurements_by_host"].values():
                values[ARMS[0]] = 100_000
                values[ARMS[1]] = 120_000
    _refresh(measurements)
    result = memory.assess_decision_surface(measurements)
    assert result["status"] == "abstained"
    assert "memory_decision_surface_split_coverage_below_0_80" in result["blockers"]
    assert result["development_training_eligible"] is False
    assert result["exact_fallback"] == "unchanged exact path"


def test_materiality_thresholds_are_inclusive_and_unit_scale_invariant():
    measurements = _measurements()
    floor = measurements["metric"]["resolution_floor_bytes"]
    best = 10 * floor
    second = 11 * floor
    for index, case in enumerate(measurements["cases"]):
        winner = ARMS[index % 2]
        values = {winner: best, ARMS[1 - index % 2]: second}
        for host_id in case["measurements_by_host"]:
            case["measurements_by_host"][host_id] = dict(values)
    _refresh(measurements)

    baseline = memory.assess_decision_surface(measurements)
    assert baseline["development_training_eligible"] is True
    assert baseline["non_abstain_coverage"] == 1.0

    scaled = copy.deepcopy(measurements)
    scaled["metric"]["resolution_floor_bytes"] *= 4
    for case in scaled["cases"]:
        for values in case["measurements_by_host"].values():
            for arm in values:
                values[arm] *= 4
    _refresh(scaled)
    replay = memory.assess_decision_surface(scaled)

    assert replay["labels"] == baseline["labels"]
    assert replay["labels_sha256"] == baseline["labels_sha256"]
    assert replay["non_abstain_coverage_by_split"] == baseline[
        "non_abstain_coverage_by_split"
    ]


def test_one_byte_below_absolute_materiality_floor_abstains_that_case():
    measurements = _measurements()
    case = next(
        row for row in measurements["cases"] if row["split"] == "development_audit"
    )
    floor = measurements["metric"]["resolution_floor_bytes"]
    for values in case["measurements_by_host"].values():
        values[ARMS[0]] = 100_000
        values[ARMS[1]] = 100_000 + floor - 1
    _refresh(measurements)

    result = memory.assess_decision_surface(measurements)

    label = next(row["label"] for row in result["labels"] if row["case_id"] == case["case_id"])
    assert label == memory.ABSTAIN_LABEL
    assert result["threshold_abstention_cases"] == [case["case_id"]]


def test_perfect_memory_predictions_pass_development_metrics():
    measurements = _measurements()
    predictions = _predictions(measurements)
    result = memory.assess_candidate_predictions(predictions, measurements)
    assert result["status"] == "memory_development_signal_established"
    assert result["development_signal_established"] is True
    assert result["blockers"] == []
    for metrics in result["split_metrics"].values():
        assert metrics["material_underprediction_prevalence"] == 0.0
        assert metrics["median_overprediction_factor"] == 1.0
        assert metrics["pairwise_order_agreement"] == 1.0
        assert metrics["near_minimum_selection_prevalence"] == 1.0


def test_multiply_low_cone_wrong_order_regression_fails_closed():
    measurements = _measurements()
    predictions = _predictions(measurements, reverse_evaluation=True)
    predictions["candidate_id"] = "size-only-multiply-low-cone-regression"
    result = memory.assess_candidate_predictions(predictions, measurements)
    assert result["status"] == "memory_development_signal_rejected"
    assert result["development_signal_established"] is False
    assert any(
        blocker.startswith("memory_pairwise_ordering_failed")
        for blocker in result["blockers"]
    )
    assert any(
        blocker.startswith("memory_near_minimum_selection_failed")
        for blocker in result["blockers"]
    )
    assert result["exact_fallback"] == "unchanged exact path"


def test_tampering_or_target_leakage_abstains():
    measurements = _measurements()
    predictions = _predictions(measurements)
    tampered = copy.deepcopy(predictions)
    tampered["rows"][0]["predicted_bytes_by_arm"][ARMS[0]] += 1
    result = memory.assess_candidate_predictions_or_abstain(tampered, measurements)
    assert result["status"] == "abstained"
    assert result["development_signal_established"] is False

    predictions["audit_targets_visible_to_fit"] = True
    predictions["rows_sha256"] = memory.digest(predictions["rows"])
    result = memory.assess_candidate_predictions_or_abstain(predictions, measurements)
    assert result["status"] == "abstained"
    assert result["advice_enabled"] is False


def test_malformed_host_nan_and_candidate_kind_fields_fail_closed():
    measurements = _measurements()
    missing_host = copy.deepcopy(measurements)
    missing_host["cases"][0]["measurements_by_host"].pop("machine-b")
    _refresh(missing_host)
    assert memory.assess_decision_surface_or_abstain(missing_host)["status"] == "abstained"

    nonfinite = copy.deepcopy(measurements)
    nonfinite["cases"][0]["measurements_by_host"]["machine-a"][ARMS[0]] = float("nan")
    assert memory.assess_decision_surface_or_abstain(nonfinite)["status"] == "abstained"

    analytical = _predictions(measurements)
    analytical["training_seed"] = 11
    analytical["neural_protocol_sha256"] = "f" * 64
    assert memory.assess_candidate_predictions_or_abstain(
        analytical, measurements
    )["status"] == "abstained"


def test_neural_memory_signal_requires_every_predeclared_seed_to_pass():
    measurements = _measurements()
    protocol = _neural_protocol(measurements)
    predictions = [
        _predictions(
            measurements,
            candidate_kind="tiny_neural",
            training_seed=seed,
            neural_protocol=protocol,
        )
        for seed in reversed(protocol["training_seeds"])
    ]

    result = memory.assess_neural_seed_predictions(
        protocol,
        predictions,
        measurements,
    )

    assert result["status"] == "replicated_memory_development_signal_established"
    assert result["development_signal_established"] is True
    assert result["evaluated_training_seeds"] == [11, 23, 47]
    assert result["blockers"] == []
    assert result["neural_protocol_sha256"] == protocol["protocol_sha256"]
    assert result["candidate_spec_sha256"] == protocol["candidate_spec_sha256"]
    assert result["training_performed"] is False
    for metrics in result["worst_case_split_metrics"].values():
        assert metrics["maximum_material_underprediction_prevalence"] == 0.0
        assert metrics["minimum_pairwise_order_agreement"] == 1.0
        assert metrics["minimum_near_minimum_selection_prevalence"] == 1.0


def test_one_failed_neural_seed_rejects_the_replicated_memory_signal():
    measurements = _measurements()
    protocol = _neural_protocol(measurements)
    predictions = [
        _predictions(
            measurements,
            reverse_evaluation=seed == 47,
            candidate_kind="tiny_neural",
            training_seed=seed,
            neural_protocol=protocol,
        )
        for seed in protocol["training_seeds"]
    ]

    result = memory.assess_neural_seed_predictions(
        protocol,
        predictions,
        measurements,
    )

    assert result["status"] == "replicated_memory_development_signal_rejected"
    assert result["development_signal_established"] is False
    assert any(blocker.startswith("seed_failed:47:") for blocker in result["blockers"])
    for metrics in result["worst_case_split_metrics"].values():
        assert metrics["minimum_pairwise_order_agreement"] == 0.0
        assert metrics["minimum_near_minimum_selection_prevalence"] == 0.0


def test_neural_seed_schedule_protocol_and_single_seed_paths_fail_closed():
    measurements = _measurements()
    protocol = _neural_protocol(measurements)
    predictions = [
        _predictions(
            measurements,
            candidate_kind="tiny_neural",
            training_seed=seed,
            neural_protocol=protocol,
        )
        for seed in protocol["training_seeds"]
    ]

    result = memory.assess_candidate_predictions_or_abstain(
        predictions[0], measurements
    )
    assert result["status"] == "abstained"

    duplicate = copy.deepcopy(predictions)
    duplicate[2]["training_seed"] = 23
    result = memory.assess_neural_seed_predictions_or_abstain(
        protocol, duplicate, measurements
    )
    assert result["status"] == "abstained"

    incomplete = predictions[:2]
    result = memory.assess_neural_seed_predictions_or_abstain(
        protocol, incomplete, measurements
    )
    assert result["status"] == "abstained"

    mismatched = copy.deepcopy(predictions)
    mismatched[2]["neural_protocol_sha256"] = "0" * 64
    result = memory.assess_neural_seed_predictions_or_abstain(
        protocol, mismatched, measurements
    )
    assert result["status"] == "abstained"

    tampered_protocol = copy.deepcopy(protocol)
    tampered_protocol["candidate_spec_sha256"] = "1" * 64
    result = memory.assess_neural_seed_predictions_or_abstain(
        tampered_protocol, predictions, measurements
    )
    assert result["status"] == "abstained"
    assert result["production_routing_permitted"] is False


def test_read_only_cli_assesses_surface_and_predictions(monkeypatch, capsys):
    measurements = _measurements()
    predictions = _predictions(measurements)
    documents = {
        "measurements.json": measurements,
        "predictions.json": predictions,
    }
    monkeypatch.setattr(
        memory_cli,
        "_read_json",
        lambda path: documents[path.name],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cm_memory_learning_evidence.py",
            "--measurements",
            "measurements.json",
        ],
    )
    assert memory_cli.main() == 0
    assert json.loads(capsys.readouterr().out)["development_training_eligible"] is True

    sys.argv.extend(["--predictions", "predictions.json"])
    assert memory_cli.main() == 0
    assert json.loads(capsys.readouterr().out)["development_signal_established"] is True


def test_read_only_cli_assesses_all_neural_seeds_together(monkeypatch, capsys):
    measurements = _measurements()
    protocol = _neural_protocol(measurements)
    predictions = {
        f"seed-{seed}.json": _predictions(
            measurements,
            candidate_kind="tiny_neural",
            training_seed=seed,
            neural_protocol=protocol,
        )
        for seed in protocol["training_seeds"]
    }
    documents = {
        "measurements.json": measurements,
        "protocol.json": protocol,
        **predictions,
    }
    monkeypatch.setattr(memory_cli, "_read_json", lambda path: documents[path.name])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cm_memory_learning_evidence.py",
            "--measurements",
            "measurements.json",
            "--neural-protocol",
            "protocol.json",
            "--neural-predictions",
            "seed-47.json",
            "seed-11.json",
            "seed-23.json",
        ],
    )

    assert memory_cli.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "replicated_memory_development_signal_established"
    assert result["evaluated_training_seeds"] == [11, 23, 47]
