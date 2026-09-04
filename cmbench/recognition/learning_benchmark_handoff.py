"""Fail-closed acceptance contract for exact-benchmark learning handoffs.

This module does not execute benchmarks or train models.  It validates a
normalized, independently verified cross-machine handoff and decides whether
development *experimentation* may be considered.  Production advice and
prospective consumption remain separate, prohibited decisions.
"""
from __future__ import annotations

from collections import Counter
import math
from typing import Any, Mapping, Sequence

from cmbench.recognition import version_history_learning_protocol as history


SCHEMA = "crse-learning-benchmark-handoff/v1"
READINESS_SCHEMA = "crse-learning-benchmark-handoff-readiness/v1"
REQUIRED_COSTS = (
    "feature_extraction_and_control",
    "model_inference",
    "exact_verification",
    "expected_fallback",
)
REQUIRED_SPLITS = tuple(history.MIN_SPLIT_SOURCE_GROUPS)
HEX = frozenset("0123456789abcdef")


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _hash(value: Any, label: str) -> str:
    _require(
        type(value) is str and len(value) == 64 and set(value) <= HEX,
        f"invalid SHA-256: {label}",
    )
    return value


def _finite_positive(value: Any, label: str) -> float:
    _require(
        type(value) in (int, float) and math.isfinite(value) and value > 0,
        f"invalid positive value: {label}",
    )
    return float(value)


def _finite_nonnegative(value: Any, label: str) -> float:
    _require(
        type(value) in (int, float) and math.isfinite(value) and value >= 0,
        f"invalid nonnegative value: {label}",
    )
    return float(value)


def replication_economics(replication: Mapping[str, Any]) -> dict[str, float]:
    best_fixed = _finite_positive(replication.get("best_fixed_sum_ns"), "best fixed")
    oracle = _finite_positive(replication.get("oracle_sum_ns"), "oracle")
    cases = replication.get("complete_cases")
    _require(type(cases) is int and cases > 0 and oracle <= best_fixed, "replication cases")
    costs = replication.get("p95_costs_ns_per_case")
    _require(isinstance(costs, Mapping) and set(costs) == set(REQUIRED_COSTS),
             "replication cost fields")
    charged_cost = sum(
        _finite_nonnegative(costs[name], f"cost:{name}") for name in REQUIRED_COSTS
    )
    return {
        "gross_speedup": best_fixed / oracle,
        "p95_total_cost_ns_per_case": charged_cost,
        "fully_charged_speedup": best_fixed / (oracle + cases * charged_cost),
    }


def _incomplete_replication_economics(
    replication: Mapping[str, Any],
) -> dict[str, float | None]:
    """Replay known economics while preserving absent charged costs as absent."""
    best_fixed = _finite_positive(replication.get("best_fixed_sum_ns"), "best fixed")
    oracle = _finite_positive(replication.get("oracle_sum_ns"), "oracle")
    cases = replication.get("complete_cases")
    _require(type(cases) is int and cases > 0 and oracle <= best_fixed, "replication cases")
    costs = replication.get("p95_costs_ns_per_case")
    _require(
        isinstance(costs, Mapping) and set(costs) == set(REQUIRED_COSTS),
        "replication cost fields",
    )
    if any(costs[name] is None for name in REQUIRED_COSTS):
        _require(
            all(
                costs[name] is None
                or (
                    type(costs[name]) in (int, float)
                    and math.isfinite(costs[name])
                    and costs[name] >= 0
                )
                for name in REQUIRED_COSTS
            ),
            "incomplete replication costs",
        )
        return {
            "gross_speedup": best_fixed / oracle,
            "p95_total_cost_ns_per_case": None,
            "fully_charged_speedup": None,
        }
    return replication_economics(replication)


def validate_handoff(handoff: Mapping[str, Any]) -> None:
    expected = {
        "schema", "status", "surface_id", "task_contract_sha256",
        "source_checkpoint", "source_tree", "freeze_sha256",
        "baseline_closure", "cohort", "exact_methods", "replications",
        "claim_boundary",
    }
    _require(isinstance(handoff, Mapping) and set(handoff) == expected,
             "handoff fields")
    _require(
        handoff.get("schema") == SCHEMA
        and handoff.get("status") in {"verified_complete", "incomplete"}
        and type(handoff.get("surface_id")) is str
        and bool(handoff["surface_id"]),
        "handoff identity",
    )
    for name in (
        "task_contract_sha256", "source_checkpoint", "source_tree", "freeze_sha256"
    ):
        _hash(handoff.get(name), name)

    closure = handoff["baseline_closure"]
    _require(
        isinstance(closure, Mapping)
        and set(closure)
        == {"status", "sha256", "all_relevant_exact_baselines_included"}
        and closure.get("status") in {"verified_complete", "incomplete"}
        and type(closure.get("all_relevant_exact_baselines_included")) is bool,
        "baseline closure",
    )
    _hash(closure.get("sha256"), "baseline closure")

    cohort = handoff["cohort"]
    _require(
        isinstance(cohort, Mapping)
        and set(cohort)
        == {
            "role", "protocol_frozen_before_labels", "source_groups",
            "source_groups_by_split", "source_groups_per_label",
            "cross_split_source_group_intersections", "prospective_cases_consumed",
            "case_set_sha256", "label_table_sha256",
        }
        and cohort.get("role")
        in {"source_blind_development", "retrospective_development"}
        and type(cohort.get("protocol_frozen_before_labels")) is bool
        and type(cohort.get("source_groups")) is int
        and cohort["source_groups"] >= 0
        and type(cohort.get("cross_split_source_group_intersections")) is int
        and cohort["cross_split_source_group_intersections"] >= 0
        and type(cohort.get("prospective_cases_consumed")) is int
        and cohort["prospective_cases_consumed"] >= 0,
        "handoff cohort",
    )
    _hash(cohort.get("case_set_sha256"), "case set")
    _hash(cohort.get("label_table_sha256"), "label table")
    split_counts = cohort.get("source_groups_by_split")
    label_counts = cohort.get("source_groups_per_label")
    _require(
        isinstance(split_counts, Mapping)
        and set(split_counts) == set(REQUIRED_SPLITS)
        and all(type(value) is int and value >= 0 for value in split_counts.values())
        and sum(split_counts.values()) == cohort["source_groups"]
        and isinstance(label_counts, Mapping)
        and bool(label_counts)
        and all(type(name) is str and name for name in label_counts)
        and all(type(value) is int and value >= 0 for value in label_counts.values()),
        "handoff cohort accounting",
    )

    exact_methods = handoff["exact_methods"]
    _require(
        isinstance(exact_methods, Mapping)
        and set(exact_methods)
        == {"arms", "refused_rows_retained", "task_identical_exact_outputs"}
        and type(exact_methods.get("arms")) is list
        and len(exact_methods["arms"]) >= 2
        and len(set(exact_methods["arms"])) == len(exact_methods["arms"])
        and all(type(arm) is str and arm for arm in exact_methods["arms"])
        and type(exact_methods.get("refused_rows_retained")) is bool
        and type(exact_methods.get("task_identical_exact_outputs")) is bool,
        "exact method closure",
    )

    replications = handoff["replications"]
    _require(type(replications) is list and bool(replications), "replications")
    expected_replication_fields = {
        "replication_id", "physical_machine_sha256", "compiler_sha256",
        "independent_verification_sha256", "verification_status",
        "case_set_sha256", "label_table_sha256", "complete_cases",
        "best_fixed_method", "best_fixed_sum_ns", "oracle_sum_ns",
        "gross_speedup", "p95_costs_ns_per_case", "p95_costs_measured_same_host",
        "fully_charged_speedup", "sum_based_economics", "schedule_mismatches",
        "semantic_mismatches", "source_or_artifact_mismatches",
    }
    replication_ids: set[str] = set()
    for replication in replications:
        _require(
            isinstance(replication, Mapping)
            and set(replication) == expected_replication_fields
            and type(replication.get("replication_id")) is str
            and bool(replication["replication_id"])
            and replication["replication_id"] not in replication_ids
            and replication.get("verification_status")
            in {"verified_complete", "incomplete"}
            and replication.get("best_fixed_method") in exact_methods["arms"]
            and type(replication.get("p95_costs_measured_same_host")) is bool
            and type(replication.get("sum_based_economics")) is bool
            and all(
                type(replication.get(name)) is int and replication[name] >= 0
                for name in (
                    "schedule_mismatches", "semantic_mismatches",
                    "source_or_artifact_mismatches",
                )
            ),
            "replication boundary",
        )
        replication_ids.add(replication["replication_id"])
        for name in (
            "physical_machine_sha256", "compiler_sha256",
            "independent_verification_sha256", "case_set_sha256",
            "label_table_sha256",
        ):
            _hash(replication.get(name), f"replication:{name}")
        economics = _incomplete_replication_economics(replication)
        economics_match = (
            type(replication.get("gross_speedup")) is float
            and math.isclose(
                replication["gross_speedup"], economics["gross_speedup"], rel_tol=1e-15
            )
        )
        if economics["fully_charged_speedup"] is None:
            economics_match = (
                economics_match
                and handoff.get("status") == "incomplete"
                and replication.get("fully_charged_speedup") is None
            )
        else:
            economics_match = (
                economics_match
                and type(replication.get("fully_charged_speedup")) is float
                and math.isclose(
                    replication["fully_charged_speedup"],
                    economics["fully_charged_speedup"],
                    rel_tol=1e-15,
                )
            )
        _require(economics_match, "replication economics replay")

    claim = handoff["claim_boundary"]
    _require(
        isinstance(claim, Mapping)
        and set(claim)
        == {
            "development_training_eligibility_permitted",
            "prospective_consumption_permitted", "production_routing_permitted",
        }
        and all(type(value) is bool for value in claim.values()),
        "claim boundary",
    )


def assess_handoff(handoff: Mapping[str, Any]) -> dict[str, Any]:
    validate_handoff(handoff)
    blockers: list[str] = []
    closure = handoff["baseline_closure"]
    cohort = handoff["cohort"]
    exact = handoff["exact_methods"]
    replications: Sequence[Mapping[str, Any]] = handoff["replications"]
    claim = handoff["claim_boundary"]

    def block(condition: bool, code: str) -> None:
        if condition:
            blockers.append(code)

    block(handoff["status"] != "verified_complete", "handoff_not_verified_complete")
    block(
        closure["status"] != "verified_complete"
        or closure["all_relevant_exact_baselines_included"] is not True,
        "exact_baseline_closure_incomplete",
    )
    block(
        cohort["role"] != "source_blind_development",
        "cohort_is_retrospective_not_source_blind",
    )
    block(not cohort["protocol_frozen_before_labels"], "protocol_not_frozen_before_labels")
    block(
        cohort["cross_split_source_group_intersections"] != 0,
        "source_group_split_leakage",
    )
    block(
        any(
            cohort["source_groups_by_split"][name] < minimum
            for name, minimum in history.MIN_SPLIT_SOURCE_GROUPS.items()
        ),
        "insufficient_source_groups_by_split",
    )
    label_counts = cohort["source_groups_per_label"]
    block(
        len(label_counts) < 2
        or any(value < history.MIN_SOURCE_GROUPS_PER_LABEL for value in label_counts.values()),
        "insufficient_source_groups_per_label",
    )
    block(cohort["prospective_cases_consumed"] != 0, "prospective_data_consumed_early")
    block(
        exact["refused_rows_retained"] is not True
        or exact["task_identical_exact_outputs"] is not True,
        "exact_task_or_refusal_closure_incomplete",
    )
    block(len(replications) < 2, "fewer_than_two_replications")
    block(
        len({row["physical_machine_sha256"] for row in replications}) < 2,
        "physical_machines_not_distinct",
    )
    block(
        any(row["case_set_sha256"] != cohort["case_set_sha256"] for row in replications),
        "replication_case_set_mismatch",
    )
    block(
        any(row["label_table_sha256"] != cohort["label_table_sha256"] for row in replications),
        "replication_label_table_mismatch",
    )
    charged_speedups: list[float] = []
    gross_speedups: list[float] = []
    for row in replications:
        prefix = row["replication_id"]
        block(
            row["verification_status"] != "verified_complete"
            or any(
                row[name] != 0 for name in (
                    "schedule_mismatches", "semantic_mismatches",
                    "source_or_artifact_mismatches",
                )
            ),
            f"replication_not_exact:{prefix}",
        )
        block(not row["sum_based_economics"], f"sum_based_economics_missing:{prefix}")
        block(
            not row["p95_costs_measured_same_host"],
            f"same_host_p95_costs_missing:{prefix}",
        )
        economics = _incomplete_replication_economics(row)
        gross_speedups.append(economics["gross_speedup"])
        if economics["fully_charged_speedup"] is not None:
            charged_speedups.append(economics["fully_charged_speedup"])
        else:
            block(True, f"fully_charged_cost_vector_incomplete:{prefix}")
        block(
            economics["gross_speedup"] < history.DEVELOPMENT_HEADROOM_GATE,
            f"gross_headroom_below_1_10:{prefix}",
        )
        if economics["fully_charged_speedup"] is not None:
            block(
                economics["fully_charged_speedup"] < history.DEVELOPMENT_HEADROOM_GATE,
                f"charged_headroom_below_1_10:{prefix}",
            )
    block(
        claim["development_training_eligibility_permitted"] is not True,
        "benchmark_claim_boundary_forbids_development_training",
    )
    block(
        claim["prospective_consumption_permitted"] is not False
        or claim["production_routing_permitted"] is not False,
        "handoff_exceeds_development_only_scope",
    )
    eligible = not blockers
    return {
        "schema": READINESS_SCHEMA,
        "status": "eligible_for_development_experiment_design" if eligible else "abstained",
        "surface_id": handoff["surface_id"],
        "development_headroom_gate": history.DEVELOPMENT_HEADROOM_GATE,
        "replications": len(replications),
        "distinct_physical_machines": len({
            row["physical_machine_sha256"] for row in replications
        }),
        "minimum_gross_speedup": min(gross_speedups),
        "minimum_fully_charged_speedup": (
            min(charged_speedups) if len(charged_speedups) == len(replications) else None
        ),
        "blockers": blockers,
        "development_training_eligible": eligible,
        "training_performed": False,
        "prospective_data_consumption_permitted": False,
        "advice_enabled": False,
        "complete_abstention": not eligible,
        "exact_fallback": "unchanged exact path",
        "production_routing_permitted": False,
    }


def assess_or_abstain(handoff: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return assess_handoff(handoff)
    except (KeyError, TypeError, ValueError):
        return {
            "schema": READINESS_SCHEMA,
            "status": "abstained",
            "blockers": ["malformed_or_unverified_handoff"],
            "development_training_eligible": False,
            "training_performed": False,
            "prospective_data_consumption_permitted": False,
            "advice_enabled": False,
            "complete_abstention": True,
            "exact_fallback": "unchanged exact path",
            "production_routing_permitted": False,
        }


def validate_handoff_against_learning_freeze(
    handoff: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> None:
    """Bind a future q64 handoff to its pre-label source-blind freeze."""
    from cmbench.recognition import query_ladder_learning_freeze as query_freeze

    validate_handoff(handoff)
    query_freeze.validate_freeze(freeze)
    _hash(freeze_file_sha256, "learning freeze file")
    _require(
        handoff["surface_id"] == "architecture_query_ladder_q64",
        "learning freeze surface",
    )
    _require(
        handoff["freeze_sha256"] == freeze_file_sha256
        and handoff["task_contract_sha256"]
        == query_freeze.digest(freeze["exact_task_contract"])
        and handoff["source_checkpoint"]
        == query_freeze.digest(freeze["source_checkpoint"])
        and handoff["source_tree"] == freeze["source_closure_sha256"],
        "learning freeze identity binding",
    )
    cohort = handoff["cohort"]
    frozen_cohort = freeze["cohort"]
    _require(
        cohort["role"] == "source_blind_development"
        and cohort["protocol_frozen_before_labels"] is True
        and cohort["source_groups"] == frozen_cohort["source_groups"]
        and cohort["source_groups_by_split"]
        == frozen_cohort["source_group_counts_by_split"]
        and cohort["cross_split_source_group_intersections"] == 0
        and cohort["prospective_cases_consumed"] == 0
        and cohort["case_set_sha256"] == frozen_cohort["case_set_sha256"],
        "learning freeze cohort binding",
    )
    _require(
        handoff["exact_methods"]["arms"] == freeze["exact_task_contract"]["arms"]
        and handoff["exact_methods"]["refused_rows_retained"] is True
        and handoff["exact_methods"]["task_identical_exact_outputs"] is True,
        "learning freeze exact method binding",
    )


def assess_frozen_handoff_or_abstain(
    handoff: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> dict[str, Any]:
    try:
        validate_handoff_against_learning_freeze(
            handoff,
            freeze,
            freeze_file_sha256=freeze_file_sha256,
        )
        return assess_handoff(handoff)
    except (KeyError, TypeError, ValueError):
        return {
            "schema": READINESS_SCHEMA,
            "status": "abstained",
            "blockers": ["malformed_unverified_or_freeze_mismatched_handoff"],
            "development_training_eligible": False,
            "training_performed": False,
            "prospective_data_consumption_permitted": False,
            "advice_enabled": False,
            "complete_abstention": True,
            "exact_fallback": "unchanged exact path",
            "production_routing_permitted": False,
        }


def assess_query_ladder_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize completed q64 evidence and feed it through this same gate."""
    from cmbench.recognition import query_ladder_learning_evidence as query_evidence

    query_evidence.validate_evidence(evidence)
    result = assess_handoff(query_evidence.normalize_incomplete_handoff(evidence))
    return {
        **result,
        "evidence_schema": evidence["schema"],
        "query_count": evidence["query_count"],
        "cross_host_label_agreement_cases": evidence["cross_host"][
            "label_agreement_cases"
        ],
        "cross_host_label_disagreement_cases": evidence["cross_host"][
            "label_disagreement_cases"
        ],
        "gross_headroom_at_least_1_10_on_both_hosts": evidence["cross_host"][
            "gross_headroom_at_least_1_10_on_both_hosts"
        ],
        "per_host_maximum_total_cost_ns_per_case_preserving_1_10": {
            host_id: host[
                "maximum_total_cost_ns_per_case_preserving_1_10"
            ]
            for host_id, host in evidence["hosts"].items()
        },
    }


def current_evidence_readiness(assessment: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize blockers from the current verified protocol assessment."""
    history.validate_assessment(assessment)
    gates = assessment["gates"]
    query = assessment["query_ladder_input"]["summary"]
    blockers: list[str] = []
    if not gates["minimum_split_sizes"]:
        blockers.append("insufficient_source_groups_by_split")
    if not gates["minimum_label_support"]:
        blockers.append("insufficient_source_groups_per_label")
    if not gates["protocol_precommitted_before_current_labels"]:
        blockers.append("protocol_not_frozen_before_current_labels")
    if not gates["query_ladder_sum_based_charged_headroom_available"]:
        blockers.append("query_ladder_sum_based_charged_headroom_missing")
    if not gates["query_ladder_cross_machine_replication_complete"]:
        blockers.append("query_ladder_cross_machine_replication_missing")
    if not gates["query_ladder_selector_or_neural_claim_permitted"]:
        blockers.append("query_ladder_claim_boundary_forbids_learning")
    if not gates["all_recognition_verification_and_fallback_costs_measured"]:
        blockers.append("fully_charged_cost_vector_incomplete")
    if not gates["timing_host_matches_exact_benchmark_host"]:
        blockers.append("recognition_timing_host_mismatch")
    return {
        "schema": READINESS_SCHEMA,
        "status": "abstained",
        "surface_id": history.SURFACE_ID,
        "verified_version_history_gross_speedup": assessment["economics"][
            "verified_gross_speedup"
        ],
        "query_ladder_q64_geomean_oracle_regret": query[
            "q64_best_fixed_case_median_geomean_slowdown_to_oracle"
        ],
        "query_ladder_metric_is_sum_based_charged_headroom": query[
            "metric_is_sum_based_charged_headroom"
        ],
        "blockers": blockers,
        "development_training_eligible": False,
        "training_performed": False,
        "prospective_data_consumption_permitted": False,
        "advice_enabled": False,
        "complete_abstention": True,
        "exact_fallback": "unchanged exact path",
        "production_routing_permitted": False,
    }
