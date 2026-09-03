"""Fail-closed prefreeze gate for a future architecture comparison campaign.

The prefreeze artifact binds the current exact evidence and records the future
contracts.  Functional admission and C38 exactness permit a fresh, structurally
selected comparison-corpus freeze.  The separate 1.10x oracle-headroom gate
continues to block selector fitting and neural training for the present q64
decision surface; it does not block task-matched non-neural benchmarking.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import re
from typing import Any

from .architecture_refresh_harness import validate_functional_result, validate_plan
from .contracts import canonical_bytes


SCHEMA = "cm-architecture-comparison-prefreeze/v1"
HEADROOM_SCHEMA = "cm-new-exact-surface-headroom-evidence/v1"
MINIMUM_ORACLE_HEADROOM = 1.10
_SHA256 = re.compile(r"[0-9a-f]{64}")
_COMMIT = re.compile(r"[0-9a-f]{40}")


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _validate_sha256(value: Any, label: str) -> str:
    _require(isinstance(value, str) and _SHA256.fullmatch(value), label)
    return value


def validate_new_surface_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Validate evidence that can open corpus-freeze work, never timing itself."""
    _require(isinstance(evidence, Mapping), "new-surface evidence")
    _require(
        set(evidence)
        == {
            "schema",
            "surface_id",
            "source_sha256",
            "results_sha256",
            "independent_verification_sha256",
            "exact_artifact_verified",
            "optimized_exact_baselines_included",
            "development_oracle_headroom",
            "prospective_data_consumed",
            "training_performed",
        },
        "new-surface evidence fields",
    )
    headroom = evidence["development_oracle_headroom"]
    _require(
        evidence["schema"] == HEADROOM_SCHEMA
        and isinstance(evidence["surface_id"], str)
        and evidence["surface_id"]
        and evidence["exact_artifact_verified"] is True
        and evidence["optimized_exact_baselines_included"] is True
        and type(headroom) in (int, float)
        and headroom >= MINIMUM_ORACLE_HEADROOM
        and evidence["prospective_data_consumed"] is False
        and evidence["training_performed"] is False,
        "new-surface activation gate",
    )
    for field in (
        "source_sha256",
        "results_sha256",
        "independent_verification_sha256",
    ):
        _validate_sha256(evidence[field], field)
    return dict(evidence)


def _validate_current_evidence(
    native_closure: Mapping[str, Any],
    c38_adjudication: Mapping[str, Any],
    functional_plan: Mapping[str, Any],
    functional_result: Mapping[str, Any],
) -> None:
    validate_plan(functional_plan)
    validate_functional_result(functional_result, functional_plan)
    _require(
        native_closure.get("schema")
        == "crse-native-portfolio-baseline-closure-summary/v1"
        and native_closure.get("status")
        == "verified_fixed_native_gain_zero_selector_headroom"
        and native_closure.get("summary", {}).get("oracle_speedup_over_best_fixed")
        == 1.0
        and native_closure.get("decision", {}).get(
            "selector_development_headroom_gate"
        )
        is False
        and native_closure.get("decision", {}).get(
            "prospective_confirmation_allowed"
        )
        is False
        and native_closure.get("prospective_data_consumed") is False,
        "native closure decision boundary",
    )
    _require(
        c38_adjudication.get("schema")
        == "crse-c38-c37-native-cross-machine-adjudication/v1"
        and c38_adjudication.get("status")
        == "exact_replication_passed_per_case_performance_not_confirmed"
        and c38_adjudication.get("exactness_verified_on_both") is True
        and c38_adjudication.get("all_predeclared_performance_gates_passed_on_both")
        is False
        and c38_adjudication.get("prospective_rerun_authorized") is False
        and c38_adjudication.get("selector_training_justified") is False,
        "C38 decision boundary",
    )
    _require(
        functional_result.get("timing_evidence_produced") is False
        and functional_result.get("fresh_corpus_consumed") is False
        and functional_result.get("prospective_data_consumed") is False,
        "functional-admission boundary",
    )


def build_prefreeze(
    *,
    source_checkpoint: str,
    native_closure: Mapping[str, Any],
    native_closure_sha256: str,
    c38_adjudication: Mapping[str, Any],
    c38_adjudication_sha256: str,
    functional_plan: Mapping[str, Any],
    functional_plan_sha256: str,
    functional_result: Mapping[str, Any],
    functional_result_sha256: str,
    new_surface_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a protocol template and current eligibility decision."""
    _require(isinstance(source_checkpoint, str) and _COMMIT.fullmatch(source_checkpoint),
             "source checkpoint commit")
    _validate_current_evidence(
        native_closure, c38_adjudication, functional_plan, functional_result
    )
    bindings = {
        "native_portfolio_closure_sha256": _validate_sha256(
            native_closure_sha256, "native closure SHA-256"
        ),
        "c38_cross_machine_adjudication_sha256": _validate_sha256(
            c38_adjudication_sha256, "C38 adjudication SHA-256"
        ),
        "functional_plan_file_sha256": _validate_sha256(
            functional_plan_sha256, "functional plan file SHA-256"
        ),
        "functional_result_file_sha256": _validate_sha256(
            functional_result_sha256, "functional result file SHA-256"
        ),
        "functional_plan_canonical_sha256": _digest(functional_plan),
        "functional_result_canonical_sha256": _digest(functional_result),
    }
    activation = (
        validate_new_surface_evidence(new_surface_evidence)
        if new_surface_evidence is not None
        else None
    )
    selector_headroom_eligible = activation is not None
    current_headroom = native_closure["summary"]["oracle_speedup_over_best_fixed"]
    result = {
        "schema": SCHEMA,
        "status": "ready_for_corpus_freeze",
        "source_checkpoint": source_checkpoint,
        "evidence_bindings": bindings,
        "eligibility": {
            "required_development_oracle_headroom": MINIMUM_ORACLE_HEADROOM,
            "current_q64_selector_oracle_headroom": current_headroom,
            "new_surface_evidence_supplied": activation is not None,
            "new_surface_evidence": activation,
            "headroom_gate_passed": selector_headroom_eligible,
            "c38_exactness_passed": True,
            "c38_all_performance_gates_passed": False,
            "functional_admission_passed": True,
        },
        "permissions": {
            "protocol_template_maintenance": True,
            "fresh_corpus_selection": True,
            "fresh_corpus_inspection": True,
            "prospective_data_consumption": False,
            "corpus_identity_freeze": True,
            "timed_local_campaign": False,
            "runpod_authorization_request": False,
            "runpod_execution": False,
            "selector_fitting": False,
            "neural_training": False,
            "production_routing_change": False,
            "website_publication": False,
        },
        "dormant_campaign_blueprint": {
            "classification": "ready_for_source_blind_freeze",
            "cohorts": {
                "observed_regression": {
                    "status": "identity_bound",
                    "dataset_sha256": native_closure["dataset"]["sha256"],
                    "selection_uses_method_outputs_or_timings": False,
                },
                "fresh_tree_like": {
                    "status": "blocked_unselected",
                    "dataset_sha256": None,
                    "selection_uses_method_outputs_or_timings": False,
                },
                "fresh_high_sharing": {
                    "status": "blocked_unselected",
                    "dataset_sha256": None,
                    "selection_uses_method_outputs_or_timings": False,
                },
            },
            "lanes": functional_plan["lanes"],
            "schedules": {
                "counterbalance_all_arm_positions": True,
                "restriction_query_counts": [1, 4, 16, 64],
                "seed": None,
                "schedule_sha256": None,
                "selection_blind_to_method_outputs_and_timings": True,
            },
            "required_measurement_fields": [
                "parse_normalization_ns",
                "representation_construction_ns",
                "compilation_ns",
                "binding_ns",
                "evaluation_ns",
                "delivery_ns",
                "serialization_ns_when_applicable",
                "cleanup_ns",
                "accounted_total_ns",
                "output_bytes",
                "peak_rss_bytes",
                "retained_bytes",
                "source_sha256",
                "runtime_identity",
                "failure_or_refusal_status",
            ],
            "publication_gates": {
                "zero_exactness_mismatches": True,
                "zero_source_or_artifact_mismatches": True,
                "retain_all_unfavorable_cells": True,
                "task_matched_artifacts_only": True,
                "cross_machine_claims_require_separate_replication": True,
                "native_single_root_minimum_case_floor": 0.95,
                "new_selector_requires_development_oracle_headroom": 1.10,
            },
        },
        "fresh_or_prospective_data_consumed": False,
        "timing_evidence_produced": False,
        "cloud_resource_created": False,
    }
    validate_prefreeze(result)
    return result


def validate_prefreeze(prefreeze: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(prefreeze, Mapping), "prefreeze artifact")
    _require(
        set(prefreeze)
        == {
            "schema",
            "status",
            "source_checkpoint",
            "evidence_bindings",
            "eligibility",
            "permissions",
            "dormant_campaign_blueprint",
            "fresh_or_prospective_data_consumed",
            "timing_evidence_produced",
            "cloud_resource_created",
        },
        "prefreeze fields",
    )
    eligibility = prefreeze["eligibility"]
    permissions = prefreeze["permissions"]
    _require(
        isinstance(eligibility, Mapping)
        and set(eligibility)
        == {
            "required_development_oracle_headroom",
            "current_q64_selector_oracle_headroom",
            "new_surface_evidence_supplied",
            "new_surface_evidence",
            "headroom_gate_passed",
            "c38_exactness_passed",
            "c38_all_performance_gates_passed",
            "functional_admission_passed",
        },
        "prefreeze eligibility fields",
    )
    permission_fields = {
        "protocol_template_maintenance",
        "fresh_corpus_selection",
        "fresh_corpus_inspection",
        "prospective_data_consumption",
        "corpus_identity_freeze",
        "timed_local_campaign",
        "runpod_authorization_request",
        "runpod_execution",
        "selector_fitting",
        "neural_training",
        "production_routing_change",
        "website_publication",
    }
    _require(
        isinstance(permissions, Mapping) and set(permissions) == permission_fields,
        "prefreeze permission fields",
    )
    bindings = prefreeze["evidence_bindings"]
    _require(
        isinstance(bindings, Mapping)
        and set(bindings)
        == {
            "native_portfolio_closure_sha256",
            "c38_cross_machine_adjudication_sha256",
            "functional_plan_file_sha256",
            "functional_result_file_sha256",
            "functional_plan_canonical_sha256",
            "functional_result_canonical_sha256",
        }
        and all(
            isinstance(value, str) and _SHA256.fullmatch(value)
            for value in bindings.values()
        )
        and isinstance(prefreeze["source_checkpoint"], str)
        and _COMMIT.fullmatch(prefreeze["source_checkpoint"]),
        "prefreeze evidence bindings",
    )
    selector_headroom_eligible = eligibility.get("new_surface_evidence_supplied") is True
    _require(
        prefreeze["schema"] == SCHEMA
        and prefreeze["status"] == "ready_for_corpus_freeze"
        and eligibility.get("headroom_gate_passed") is selector_headroom_eligible
        and eligibility.get("required_development_oracle_headroom")
        == MINIMUM_ORACLE_HEADROOM
        and eligibility.get("current_q64_selector_oracle_headroom") == 1.0
        and eligibility.get("c38_exactness_passed") is True
        and eligibility.get("c38_all_performance_gates_passed") is False
        and eligibility.get("functional_admission_passed") is True
        and prefreeze["fresh_or_prospective_data_consumed"] is False
        and prefreeze["timing_evidence_produced"] is False
        and prefreeze["cloud_resource_created"] is False,
        "prefreeze decision boundary",
    )
    if selector_headroom_eligible:
        validate_new_surface_evidence(eligibility["new_surface_evidence"])
    else:
        _require(
            eligibility.get("new_surface_evidence") is None
            and eligibility.get("current_q64_selector_oracle_headroom") == 1.0,
            "blocked headroom evidence",
        )
    _require(
        permissions.get("protocol_template_maintenance") is True
        and permissions.get("fresh_corpus_selection") is True
        and permissions.get("fresh_corpus_inspection") is True
        and permissions.get("corpus_identity_freeze") is True
        and all(
            permissions.get(field) is False
            for field in (
                "prospective_data_consumption",
                "timed_local_campaign",
                "runpod_authorization_request",
                "runpod_execution",
                "selector_fitting",
                "neural_training",
                "production_routing_change",
                "website_publication",
            )
        ),
        "prefreeze permissions",
    )
    blueprint = prefreeze["dormant_campaign_blueprint"]
    _require(
        isinstance(blueprint, Mapping)
        and set(blueprint)
        == {
            "classification",
            "cohorts",
            "lanes",
            "schedules",
            "required_measurement_fields",
            "publication_gates",
        },
        "dormant blueprint fields",
    )
    _require(
        blueprint.get("classification") == "ready_for_source_blind_freeze"
        and set(blueprint.get("lanes", {})) == {"A", "B", "C", "D"}
        and blueprint.get("schedules", {}).get("schedule_sha256") is None
        and blueprint.get("cohorts", {}).get("fresh_tree_like", {}).get(
            "dataset_sha256"
        )
        is None
        and blueprint.get("cohorts", {}).get("fresh_high_sharing", {}).get(
            "dataset_sha256"
        )
        is None,
        "dormant blueprint boundary",
    )
    return dict(prefreeze)
