"""Recompute a q64 learning handoff from verified per-block exact timings.

The module is deliberately read-only.  It does not execute a benchmark, extract
features, fit a selector, or change routing.  It authenticates a normalized timing
package against the pre-label q64 freeze, applies the frozen joint-host label rule,
and constructs the v2 handoff consumed by the development fit guard.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import statistics
from typing import Any, Mapping, Sequence

from cmbench.recognition import learning_benchmark_handoff as benchmark_handoff
from cmbench.recognition import query_ladder_learning_freeze as query_freeze


EVIDENCE_SCHEMA = "crse-query-ladder-decision-surface-evidence/v1"
ASSESSMENT_SCHEMA = "crse-query-ladder-decision-surface-assessment/v1"
SURFACE_ID = "architecture_query_ladder_q64"
HEX = frozenset("0123456789abcdef")


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _hash(value: Any, label: str) -> str:
    _require(
        type(value) is str and len(value) == 64 and set(value) <= HEX,
        f"invalid SHA-256: {label}",
    )
    return value


def _finite_nonnegative_or_none(value: Any, label: str) -> float | None:
    if value is None:
        return None
    _require(
        type(value) in (int, float) and math.isfinite(value) and value >= 0,
        f"invalid nonnegative value: {label}",
    )
    return float(value)


def _frozen_lower_quantile(values: Sequence[float], probability: float) -> float:
    """Replay the lower-order-statistic quantile frozen before q64 timings."""
    _require(bool(values) and 0 <= probability <= 1, "quantile inputs")
    ordered = sorted(float(value) for value in values)
    return ordered[int(probability * (len(ordered) - 1))]


def validate_evidence(
    evidence: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> None:
    """Bind a complete normalized timing package to the frozen q64 protocol."""
    query_freeze.validate_freeze(freeze)
    _hash(freeze_file_sha256, "learning freeze file")
    _require(
        isinstance(evidence, Mapping)
        and set(evidence)
        == {
            "schema",
            "status",
            "surface_id",
            "freeze_file_sha256",
            "task_contract_sha256",
            "case_set_sha256",
            "label_policy_sha256",
            "baseline_closure",
            "surface_independent_verification_sha256",
            "prospective_cases_consumed",
            "claim_boundary",
            "replications",
        }
        and evidence.get("schema") == EVIDENCE_SCHEMA
        and evidence.get("status") in {"verified_complete", "incomplete"}
        and evidence.get("surface_id") == SURFACE_ID
        and evidence.get("freeze_file_sha256") == freeze_file_sha256
        and evidence.get("task_contract_sha256")
        == query_freeze.digest(freeze["exact_task_contract"])
        and evidence.get("case_set_sha256") == freeze["cohort"]["case_set_sha256"]
        and evidence.get("label_policy_sha256")
        == query_freeze.digest(freeze["label_policy"])
        and evidence.get("prospective_cases_consumed") == 0,
        "decision-surface evidence identity",
    )
    _hash(
        evidence["surface_independent_verification_sha256"],
        "surface independent verification",
    )
    closure = evidence["baseline_closure"]
    _require(
        isinstance(closure, Mapping)
        and set(closure)
        == {"status", "sha256", "all_relevant_exact_baselines_included"}
        and closure.get("status") in {"verified_complete", "incomplete"}
        and type(closure.get("all_relevant_exact_baselines_included")) is bool,
        "decision-surface baseline closure",
    )
    _hash(closure["sha256"], "baseline closure")
    claim = evidence["claim_boundary"]
    _require(
        isinstance(claim, Mapping)
        and set(claim)
        == {
            "development_training_eligibility_permitted",
            "prospective_consumption_permitted",
            "production_routing_permitted",
        }
        and all(type(value) is bool for value in claim.values()),
        "decision-surface claim boundary",
    )
    task = freeze["exact_task_contract"]
    arms = list(task["arms"])
    cases = freeze["cohort"]["cases"]
    case_ids = [row["case_id"] for row in cases]
    replications = evidence["replications"]
    _require(type(replications) is list and len(replications) >= 2, "surface replications")
    identifiers: set[str] = set()
    machines: set[str] = set()
    verifications: set[str] = set()
    for replication in replications:
        _require(
            isinstance(replication, Mapping)
            and set(replication)
            == {
                "replication_id",
                "physical_machine_sha256",
                "compiler_sha256",
                "independent_verification_sha256",
                "verification_status",
                "case_set_sha256",
                "block_timings_ns",
                "block_timings_sha256",
                "p95_costs_ns_per_case",
                "p95_costs_measured_same_host",
                "schedule_mismatches",
                "semantic_mismatches",
                "source_or_artifact_mismatches",
            }
            and type(replication.get("replication_id")) is str
            and bool(replication["replication_id"])
            and replication["replication_id"] not in identifiers
            and replication.get("verification_status")
            in {"verified_complete", "incomplete"}
            and replication.get("case_set_sha256") == evidence["case_set_sha256"]
            and type(replication.get("p95_costs_measured_same_host")) is bool
            and all(
                type(replication.get(name)) is int and replication[name] >= 0
                for name in (
                    "schedule_mismatches",
                    "semantic_mismatches",
                    "source_or_artifact_mismatches",
                )
            ),
            "decision-surface replication boundary",
        )
        identifiers.add(replication["replication_id"])
        machines.add(_hash(replication["physical_machine_sha256"], "physical machine"))
        _hash(replication["compiler_sha256"], "compiler")
        verifications.add(
            _hash(
                replication["independent_verification_sha256"],
                "replication independent verification",
            )
        )
        timings = replication["block_timings_ns"]
        _require(
            isinstance(timings, Mapping)
            and set(timings) == set(case_ids)
            and replication["block_timings_sha256"] == digest(timings),
            "decision-surface timing table identity",
        )
        for case_id, arm_timings in timings.items():
            _require(
                isinstance(arm_timings, Mapping)
                and set(arm_timings) == set(arms),
                f"decision-surface arm closure:{case_id}",
            )
            for arm in arms:
                blocks = arm_timings[arm]
                _require(
                    type(blocks) is list
                    and len(blocks) == task["blocks"]
                    and all(
                        type(value) in (int, float)
                        and math.isfinite(value)
                        and value > 0
                        for value in blocks
                    ),
                    f"decision-surface block closure:{case_id}:{arm}",
                )
        costs = replication["p95_costs_ns_per_case"]
        _require(
            isinstance(costs, Mapping)
            and set(costs) == set(benchmark_handoff.REQUIRED_COSTS),
            "decision-surface cost vector",
        )
        for name in benchmark_handoff.REQUIRED_COSTS:
            _finite_nonnegative_or_none(costs[name], f"cost:{name}")
    _require(
        len(machines) == len(replications)
        and len(verifications) == len(replications)
        and evidence["surface_independent_verification_sha256"] not in verifications,
        "decision-surface host or verification independence",
    )


def _host_case_result(
    arm_blocks: Mapping[str, Sequence[float]],
    arms: Sequence[str],
    label_policy: Mapping[str, Any],
) -> dict[str, Any]:
    medians = {
        arm: float(statistics.median(arm_blocks[arm]))
        for arm in arms
    }
    ranked = sorted(arms, key=lambda arm: (medians[arm], arm))
    winner, runner_up = ranked[:2]
    winner_blocks = arm_blocks[winner]
    runner_blocks = arm_blocks[runner_up]
    paired_speedups = [
        float(runner) / float(best)
        for best, runner in zip(winner_blocks, runner_blocks, strict=True)
    ]
    median_runner_up_speedup = medians[runner_up] / medians[winner]
    paired_block_wins = sum(
        float(best) < float(runner)
        for best, runner in zip(winner_blocks, runner_blocks, strict=True)
    )
    paired_block_win_fraction = paired_block_wins / len(winner_blocks)
    paired_p10_speedup = _frozen_lower_quantile(paired_speedups, 0.10)
    conditions = {
        "median_runner_up_speedup": median_runner_up_speedup
        >= label_policy["minimum_median_runner_up_speedup"],
        "paired_block_win_fraction": paired_block_win_fraction
        >= label_policy["minimum_paired_block_win_fraction"],
        "paired_p10_speedup": paired_p10_speedup
        >= label_policy["minimum_p10_paired_speedup"],
    }
    return {
        "winner": winner,
        "runner_up": runner_up,
        "medians_ns": medians,
        "median_runner_up_speedup": median_runner_up_speedup,
        "paired_block_wins": paired_block_wins,
        "paired_blocks": len(winner_blocks),
        "paired_block_win_fraction": paired_block_win_fraction,
        "paired_p10_speedup": paired_p10_speedup,
        "p10_method": "frozen_lower_order_statistic_floor_0_10_n_minus_1",
        "conditions": conditions,
        "material_label": winner if all(conditions.values()) else query_freeze.ABSTAIN_LABEL,
    }


def assess_decision_surface(
    evidence: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> dict[str, Any]:
    """Recompute host results and the frozen joint-host label table."""
    validate_evidence(evidence, freeze, freeze_file_sha256=freeze_file_sha256)
    arms = list(freeze["exact_task_contract"]["arms"])
    label_policy = freeze["label_policy"]
    frozen_by_id = {row["case_id"]: row for row in freeze["cohort"]["cases"]}
    host_results = {}
    for replication in evidence["replications"]:
        host_results[replication["replication_id"]] = {
            case_id: _host_case_result(arm_blocks, arms, label_policy)
            for case_id, arm_blocks in replication["block_timings_ns"].items()
        }
    labels = {}
    threshold_abstentions = []
    disagreements = []
    case_results = []
    for case_id in frozen_by_id:
        host_labels = {
            replication_id: results[case_id]["material_label"]
            for replication_id, results in host_results.items()
        }
        non_abstain = {
            label for label in host_labels.values()
            if label != query_freeze.ABSTAIN_LABEL
        }
        if query_freeze.ABSTAIN_LABEL in host_labels.values():
            label = query_freeze.ABSTAIN_LABEL
            threshold_abstentions.append(case_id)
            reason = "host_threshold_failure"
        elif len(non_abstain) != 1:
            label = query_freeze.ABSTAIN_LABEL
            disagreements.append(case_id)
            reason = "cross_host_winner_disagreement"
        else:
            label = next(iter(non_abstain))
            reason = "stable_material_winner"
        frozen_replay_label = query_freeze.label_from_cross_host_blocks({
            replication["replication_id"]: replication["block_timings_ns"][case_id]
            for replication in evidence["replications"]
        })
        _require(label == frozen_replay_label, "frozen q64 label replay mismatch")
        labels[case_id] = label
        case_results.append({
            "case_id": case_id,
            "source_group_sha256": frozen_by_id[case_id]["source_group_sha256"],
            "split": frozen_by_id[case_id]["split"],
            "joint_label": label,
            "joint_label_reason": reason,
            "host_results": {
                replication_id: results[case_id]
                for replication_id, results in host_results.items()
            },
        })
    non_abstain_rows = [
        row for row in case_results
        if row["joint_label"] != query_freeze.ABSTAIN_LABEL
    ]
    label_counts = Counter(row["joint_label"] for row in non_abstain_rows)
    stable_by_split = Counter(row["split"] for row in non_abstain_rows)
    split_sizes = freeze["cohort"]["source_group_counts_by_split"]
    coverage = len(non_abstain_rows) / len(case_results)
    coverage_by_split = {
        split: stable_by_split[split] / split_sizes[split]
        for split in split_sizes
    }
    blockers = []
    if evidence["status"] != "verified_complete":
        blockers.append("decision_surface_evidence_not_verified_complete")
    if evidence["baseline_closure"]["status"] != "verified_complete":
        blockers.append("decision_surface_baseline_closure_incomplete")
    if evidence["baseline_closure"]["all_relevant_exact_baselines_included"] is not True:
        blockers.append("decision_surface_exact_baselines_missing")
    if evidence["claim_boundary"]["development_training_eligibility_permitted"] is not True:
        blockers.append("decision_surface_claim_boundary_forbids_development_training")
    if (
        evidence["claim_boundary"]["prospective_consumption_permitted"] is not False
        or evidence["claim_boundary"]["production_routing_permitted"] is not False
    ):
        blockers.append("decision_surface_exceeds_development_only_scope")
    for replication in evidence["replications"]:
        identifier = replication["replication_id"]
        if (
            replication["verification_status"] != "verified_complete"
            or any(
                replication[name] != 0
                for name in (
                    "schedule_mismatches",
                    "semantic_mismatches",
                    "source_or_artifact_mismatches",
                )
            )
        ):
            blockers.append(f"decision_surface_replication_not_exact:{identifier}")
        if not replication["p95_costs_measured_same_host"]:
            blockers.append(f"decision_surface_same_host_costs_missing:{identifier}")
        if any(
            replication["p95_costs_ns_per_case"][name] is None
            for name in benchmark_handoff.REQUIRED_COSTS
        ):
            blockers.append(f"decision_surface_cost_vector_incomplete:{identifier}")
    return {
        "schema": ASSESSMENT_SCHEMA,
        "status": "verified_complete" if not blockers else "abstained",
        "surface_id": SURFACE_ID,
        "freeze_file_sha256": freeze_file_sha256,
        "task_contract_sha256": evidence["task_contract_sha256"],
        "case_set_sha256": evidence["case_set_sha256"],
        "label_policy_sha256": evidence["label_policy_sha256"],
        "label_table_sha256": digest(labels),
        "source_groups_per_label": dict(sorted(label_counts.items())),
        "source_groups_with_stable_material_winner": len(non_abstain_rows),
        "source_groups_with_stable_material_winner_by_split": {
            split: stable_by_split[split] for split in split_sizes
        },
        "cross_host_winner_disagreement_cases": sorted(disagreements),
        "threshold_abstention_cases": sorted(threshold_abstentions),
        "non_abstain_coverage": coverage,
        "non_abstain_coverage_by_split": coverage_by_split,
        "material_winner_arms": sorted(label_counts),
        "case_results_sha256": digest(case_results),
        "case_results": case_results,
        "blockers": blockers,
        "development_handoff_construction_permitted": not blockers,
        "training_performed": False,
        "prospective_cases_consumed": 0,
        "advice_enabled": False,
        "production_routing_permitted": False,
    }


def assess_decision_surface_or_abstain(
    evidence: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> dict[str, Any]:
    try:
        return assess_decision_surface(
            evidence,
            freeze,
            freeze_file_sha256=freeze_file_sha256,
        )
    except (KeyError, TypeError, ValueError):
        return {
            "schema": ASSESSMENT_SCHEMA,
            "status": "abstained",
            "blockers": ["malformed_unverified_or_freeze_mismatched_decision_surface"],
            "development_handoff_construction_permitted": False,
            "training_performed": False,
            "prospective_cases_consumed": 0,
            "advice_enabled": False,
            "production_routing_permitted": False,
        }


def _replication_economics(
    replication: Mapping[str, Any],
    arms: Sequence[str],
) -> dict[str, Any]:
    timings = replication["block_timings_ns"]
    medians = {
        case_id: {
            arm: float(statistics.median(arm_blocks[arm]))
            for arm in arms
        }
        for case_id, arm_blocks in timings.items()
    }
    fixed_sums = {
        arm: sum(values[arm] for values in medians.values())
        for arm in arms
    }
    best_fixed = min(arms, key=lambda arm: (fixed_sums[arm], arms.index(arm)))
    oracle_sum = sum(min(values.values()) for values in medians.values())
    costs = replication["p95_costs_ns_per_case"]
    charged_cost = sum(float(costs[name]) for name in benchmark_handoff.REQUIRED_COSTS)
    cases = len(medians)
    return {
        "best_fixed_method": best_fixed,
        "best_fixed_sum_ns": fixed_sums[best_fixed],
        "oracle_sum_ns": oracle_sum,
        "gross_speedup": fixed_sums[best_fixed] / oracle_sum,
        "fully_charged_speedup": (
            fixed_sums[best_fixed] / (oracle_sum + cases * charged_cost)
        ),
    }


def build_v2_handoff(
    evidence: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> dict[str, Any]:
    """Construct and replay-validate the v2 handoff; never write it to disk."""
    assessment = assess_decision_surface(
        evidence,
        freeze,
        freeze_file_sha256=freeze_file_sha256,
    )
    _require(
        assessment["development_handoff_construction_permitted"],
        "decision surface is not eligible for handoff construction",
    )
    arms = list(freeze["exact_task_contract"]["arms"])
    replications = []
    for source in evidence["replications"]:
        economics = _replication_economics(source, arms)
        replications.append({
            "replication_id": source["replication_id"],
            "physical_machine_sha256": source["physical_machine_sha256"],
            "compiler_sha256": source["compiler_sha256"],
            "independent_verification_sha256": source[
                "independent_verification_sha256"
            ],
            "verification_status": source["verification_status"],
            "case_set_sha256": evidence["case_set_sha256"],
            "label_table_sha256": assessment["label_table_sha256"],
            "complete_cases": len(freeze["cohort"]["cases"]),
            **economics,
            "p95_costs_ns_per_case": dict(source["p95_costs_ns_per_case"]),
            "p95_costs_measured_same_host": source[
                "p95_costs_measured_same_host"
            ],
            "sum_based_economics": True,
            "schedule_mismatches": source["schedule_mismatches"],
            "semantic_mismatches": source["semantic_mismatches"],
            "source_or_artifact_mismatches": source[
                "source_or_artifact_mismatches"
            ],
        })
    split_sizes = freeze["cohort"]["source_group_counts_by_split"]
    handoff = {
        "schema": benchmark_handoff.SCHEMA,
        "status": "verified_complete",
        "surface_id": SURFACE_ID,
        "task_contract_sha256": evidence["task_contract_sha256"],
        "source_checkpoint": query_freeze.digest(freeze["source_checkpoint"]),
        "source_tree": freeze["source_closure_sha256"],
        "freeze_sha256": freeze_file_sha256,
        "baseline_closure": dict(evidence["baseline_closure"]),
        "cohort": {
            "role": "source_blind_development",
            "protocol_frozen_before_labels": True,
            "source_groups": len(freeze["cohort"]["cases"]),
            "source_groups_by_split": dict(split_sizes),
            "source_groups_per_label": dict(assessment["source_groups_per_label"]),
            "cross_split_source_group_intersections": freeze["cohort"][
                "cross_split_source_group_intersections"
            ],
            "prospective_cases_consumed": 0,
            "case_set_sha256": evidence["case_set_sha256"],
            "label_table_sha256": assessment["label_table_sha256"],
        },
        "exact_methods": {
            "arms": arms,
            "refused_rows_retained": freeze["exact_task_contract"][
                "all_unfavorable_and_refused_rows_retained"
            ],
            "task_identical_exact_outputs": freeze["exact_task_contract"][
                "task_identical_exact_outputs_required"
            ],
        },
        "decision_surface": {
            "status": assessment["status"],
            "metric": "q64_accounted_total_ns",
            "lower_is_better": True,
            "label_policy_sha256": assessment["label_policy_sha256"],
            "label_table_sha256": assessment["label_table_sha256"],
            "independent_verification_sha256": evidence[
                "surface_independent_verification_sha256"
            ],
            "source_groups_with_stable_material_winner": assessment[
                "source_groups_with_stable_material_winner"
            ],
            "source_groups_with_stable_material_winner_by_split": assessment[
                "source_groups_with_stable_material_winner_by_split"
            ],
            "cross_host_winner_disagreement_source_groups": len(
                assessment["cross_host_winner_disagreement_cases"]
            ),
            "threshold_abstention_source_groups": len(
                assessment["threshold_abstention_cases"]
            ),
            "non_abstain_coverage": assessment["non_abstain_coverage"],
            "non_abstain_coverage_by_split": assessment[
                "non_abstain_coverage_by_split"
            ],
            "material_winner_arms": assessment["material_winner_arms"],
        },
        "replications": replications,
        "claim_boundary": dict(evidence["claim_boundary"]),
    }
    benchmark_handoff.validate_handoff_against_learning_freeze(
        handoff,
        freeze,
        freeze_file_sha256=freeze_file_sha256,
    )
    return handoff


def build_v2_handoff_or_abstain(
    evidence: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    try:
        handoff = build_v2_handoff(
            evidence,
            freeze,
            freeze_file_sha256=freeze_file_sha256,
        )
        return handoff, benchmark_handoff.assess_handoff(handoff)
    except (KeyError, TypeError, ValueError):
        return None, benchmark_handoff.assess_or_abstain({})
