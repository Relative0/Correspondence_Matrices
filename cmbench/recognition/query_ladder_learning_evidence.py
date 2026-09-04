"""Authenticate completed query-ladder rows for the development learning gate.

This module is deliberately read-only with respect to benchmark artifacts.  It
replays sum-based q64 economics from the two independently verified raw result
sets and normalizes the result for ``learning_benchmark_handoff``.  It neither
executes a benchmark nor fits a selector.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping

from cmbench.recognition import version_history_learning_protocol as history


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "crse-query-ladder-learning-evidence/v1"
SURFACE_ID = "architecture_query_ladder_q64"
QUERY_COUNT = 64
EXPECTED_REPEATS = 16
DEFAULT_CROSS_ANALYSIS = (
    ROOT
    / "docs/recognition/architecture_query_ladder_cross_machine_execution_20260904"
    / "CROSS_MACHINE_ANALYSIS.json"
)
DEFAULT_CROSS_VERIFICATION = DEFAULT_CROSS_ANALYSIS.parent / "LOCAL_INDEPENDENT_VERIFICATION.json"
DEFAULT_CROSS_INVENTORY = DEFAULT_CROSS_ANALYSIS.parent / "POST_RUN_INVENTORY.json"
DEFAULT_PRIOR_ANALYSIS = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
    / "ANALYSIS.json"
)
DEFAULT_FREEZE = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_retry_002_freeze_20260904"
    / "FREEZE.json"
)
DEFAULT_PRIOR_VERIFICATION = (
    DEFAULT_PRIOR_ANALYSIS.parent
    / "runpod-architecture-query-ladder-execute-002/evidence/run-output"
    / "architecture-query-ladder-linux-gcc-20260904-002/independent_verification.json"
)
DEFAULT_PRIOR_RAW = DEFAULT_PRIOR_VERIFICATION.parent / "raw_measurements.jsonl"
DEFAULT_CROSS_RAW = (
    DEFAULT_CROSS_ANALYSIS.parent
    / "runpod-architecture-query-ladder-cross-machine-execute-001/evidence/run-output"
    / "architecture-query-ladder-linux-clang-20260904-003/raw_measurements.jsonl"
)


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256(value: Any, label: str) -> str:
    _require(
        type(value) is str
        and len(value) == 64
        and set(value) <= set("0123456789abcdef"),
        f"invalid SHA-256: {label}",
    )
    return value


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    _require(resolved.is_relative_to(ROOT) and resolved.is_file(), "JSON input path")
    _require(0 < resolved.stat().st_size <= 32 * 1024 * 1024, "JSON input size")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), "JSON input object")
    return value


def _relative(path: Path) -> str:
    resolved = path.resolve()
    _require(resolved.is_relative_to(ROOT), "input outside repository")
    return resolved.relative_to(ROOT).as_posix()


def _verified_zero_mismatches(value: Mapping[str, Any], label: str) -> None:
    _require(value.get("status") == "verified_complete", f"{label} verification status")
    for name in (
        "schedule_mismatches",
        "semantic_mismatches",
        "source_or_artifact_mismatches",
    ):
        _require(value.get(name) == 0, f"{label} {name}")


def _summarize_raw(
    path: Path,
    *,
    expected_sha256: str,
    expected_arms: tuple[str, ...],
) -> dict[str, Any]:
    _require(file_sha256(path) == expected_sha256, "raw measurement hash mismatch")
    cells: dict[tuple[str, str], list[int]] = defaultdict(list)
    outputs: dict[str, set[tuple[str, int]]] = defaultdict(set)
    seen: set[tuple[int, str, str]] = set()
    q64_rows = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("query_count") != QUERY_COUNT:
                continue
            q64_rows += 1
            _require(
                row.get("schema") == "cm-architecture-query-ladder-timed-cell/v1"
                and row.get("status") == "ok"
                and row.get("exact_check_passed") is True,
                "unverified q64 row",
            )
            case_id = row.get("case_id")
            arm = row.get("arm")
            block = row.get("block")
            _require(
                type(case_id) is str
                and arm in expected_arms
                and type(block) is int
                and 0 <= block < EXPECTED_REPEATS,
                "q64 row identity",
            )
            # The arm order rotates by block.  Its exact sequence is already
            # bound by the verified benchmark; require only a complete
            # permutation here so this replay cannot silently drop an arm.
            arm_order = row.get("arm_order")
            _require(
                isinstance(arm_order, list)
                and len(arm_order) == len(expected_arms)
                and set(arm_order) == set(expected_arms),
                "q64 arm order",
            )
            identity = (block, case_id, arm)
            _require(identity not in seen, "duplicate q64 row")
            seen.add(identity)
            timing = row.get("timings_ns", {}).get("accounted_total_ns")
            _require(type(timing) is int and timing > 0, "q64 accounted timing")
            output_sha = row.get("output_sha256")
            output_bytes = row.get("output_bytes")
            _require(
                type(output_sha) is str
                and len(output_sha) == 64
                and type(output_bytes) is int
                and output_bytes >= 0,
                "q64 output identity",
            )
            cells[(case_id, arm)].append(timing)
            outputs[case_id].add((output_sha, output_bytes))

    cases = sorted({case_id for case_id, _ in cells})
    _require(cases and q64_rows == len(cases) * len(expected_arms) * EXPECTED_REPEATS,
             "q64 row closure")
    _require(
        all(len(values) == EXPECTED_REPEATS for values in cells.values())
        and len(cells) == len(cases) * len(expected_arms),
        "q64 cell closure",
    )
    _require(all(len(values) == 1 for values in outputs.values()), "q64 output mismatch")

    medians = {key: statistics.median(values) for key, values in cells.items()}
    fixed_sums = {
        arm: sum(medians[(case_id, arm)] for case_id in cases)
        for arm in expected_arms
    }
    best_fixed = min(expected_arms, key=lambda arm: fixed_sums[arm])
    labels = {
        case_id: min(expected_arms, key=lambda arm: medians[(case_id, arm)])
        for case_id in cases
    }
    oracle_sum = sum(medians[(case_id, labels[case_id])] for case_id in cases)
    best_sum = fixed_sums[best_fixed]
    gross = best_sum / oracle_sum
    return {
        "raw_path": _relative(path),
        "raw_sha256": expected_sha256,
        "q64_rows": q64_rows,
        "complete_cases": len(cases),
        "repeats_per_case_arm": EXPECTED_REPEATS,
        "case_set": cases,
        "case_set_sha256": canonical_sha256(cases),
        "output_table_sha256": canonical_sha256({
            case_id: sorted(outputs[case_id])[0] for case_id in cases
        }),
        "best_fixed_method": best_fixed,
        "fixed_method_sums_ns": fixed_sums,
        "best_fixed_sum_ns": best_sum,
        "oracle_sum_ns": oracle_sum,
        "gross_speedup": gross,
        "maximum_total_cost_ns_per_case_preserving_1_10": (
            best_sum / history.DEVELOPMENT_HEADROOM_GATE - oracle_sum
        ) / len(cases),
        "oracle_labels": labels,
        "oracle_label_counts": dict(sorted(Counter(labels.values()).items())),
        "label_table_sha256": canonical_sha256(labels),
    }


def build_evidence(
    *,
    cross_analysis_path: Path = DEFAULT_CROSS_ANALYSIS,
    cross_verification_path: Path = DEFAULT_CROSS_VERIFICATION,
    cross_inventory_path: Path = DEFAULT_CROSS_INVENTORY,
    prior_analysis_path: Path = DEFAULT_PRIOR_ANALYSIS,
    freeze_path: Path = DEFAULT_FREEZE,
    prior_verification_path: Path = DEFAULT_PRIOR_VERIFICATION,
    prior_raw_path: Path = DEFAULT_PRIOR_RAW,
    cross_raw_path: Path = DEFAULT_CROSS_RAW,
) -> dict[str, Any]:
    """Replay verified q64 rows and return gross-only learning evidence."""
    cross_analysis = _read_json(cross_analysis_path)
    cross_verification = _read_json(cross_verification_path)
    prior_analysis = _read_json(prior_analysis_path)
    freeze = _read_json(freeze_path)
    prior_verification = _read_json(prior_verification_path)

    _require(
        cross_analysis.get("schema")
        == "cm-architecture-query-ladder-cross-machine-analysis/v1"
        and cross_analysis.get("status")
        == "verified_cross_machine_interpretation_complete",
        "cross-machine analysis status",
    )
    cross_inputs = cross_analysis.get("inputs", {})
    _require(
        file_sha256(cross_verification_path)
        == cross_inputs.get("local_independent_verification_sha256")
        and file_sha256(cross_inventory_path)
        == cross_inputs.get("post_run_inventory_sha256")
        and file_sha256(prior_analysis_path) == cross_inputs.get("prior_analysis_sha256"),
        "cross-machine input binding",
    )
    _verified_zero_mismatches(cross_verification, "cross-machine")
    _verified_zero_mismatches(prior_analysis.get("verification", {}), "prior")
    _verified_zero_mismatches(prior_verification, "prior independent")
    _require(
        file_sha256(prior_verification_path)
        == prior_analysis.get("inputs", {}).get("independent_verification_sha256"),
        "prior independent verification binding",
    )

    task = cross_analysis.get("task_contract", {})
    arms = tuple(task.get("arms", ()))
    _require(
        len(arms) >= 2
        and len(set(arms)) == len(arms)
        and QUERY_COUNT in task.get("query_counts", ())
        and task.get("same_frozen_schedule_artifact_and_oracles") is True,
        "cross-machine task contract",
    )
    _require(
        file_sha256(freeze_path) == task.get("freeze_sha256")
        and freeze.get("schema") == "cm-architecture-query-ladder-freeze/v1"
        and tuple(freeze.get("schedule", {}).get("arms", ())) == arms
        and freeze.get("schedule", {}).get("blocks") == EXPECTED_REPEATS,
        "query-ladder freeze binding",
    )
    prior_host = _summarize_raw(
        prior_raw_path,
        expected_sha256=prior_analysis["inputs"]["raw_measurements_sha256"],
        expected_arms=arms,
    )
    cross_host = _summarize_raw(
        cross_raw_path,
        expected_sha256=cross_verification["raw_measurements_sha256"],
        expected_arms=arms,
    )
    _require(
        prior_host["case_set"] == cross_host["case_set"]
        and prior_host["output_table_sha256"] == cross_host["output_table_sha256"],
        "cross-host exact task mismatch",
    )

    analysis_hosts = cross_analysis.get("hosts", {})
    host_specs = (
        (
            "gcc_epyc_9655",
            prior_host,
            prior_verification,
            prior_verification_path,
        ),
        (
            "clang_epyc_9575f",
            cross_host,
            cross_verification,
            cross_verification_path,
        ),
    )
    hosts: dict[str, Any] = {}
    for host_id, summary, verification, verification_path in host_specs:
        host = analysis_hosts.get(host_id, {})
        _require(host, f"missing analyzed host: {host_id}")
        _sha256(host.get("compiler_executable_sha256"), f"compiler:{host_id}")
        hosts[host_id] = {
            "physical_machine_sha256": canonical_sha256({
                "cpu_flavor": host.get("cpu_flavor"),
                "cpu_model": host.get("cpu_model"),
                "platform": host.get("platform"),
            }),
            "compiler_sha256": host.get("compiler_executable_sha256"),
            "independent_verification_path": _relative(verification_path),
            "independent_verification_sha256": file_sha256(verification_path),
            "verification_status": verification.get("status"),
            **{key: value for key, value in summary.items() if key not in {
                "case_set", "oracle_labels"
            }},
        }

    prior_labels = prior_host["oracle_labels"]
    cross_labels = cross_host["oracle_labels"]
    disagreements = {
        case_id: [prior_labels[case_id], cross_labels[case_id]]
        for case_id in prior_labels
        if prior_labels[case_id] != cross_labels[case_id]
    }
    minimum_gross = min(host["gross_speedup"] for host in hosts.values())
    claim = cross_analysis.get("claim_boundary", {})
    blockers = []
    if disagreements:
        blockers.append("oracle_labels_not_stable_across_hosts")
    blockers.extend((
        "learning_protocol_not_frozen_before_labels",
        "learning_split_not_frozen_before_labels",
        "fully_charged_cost_vector_incomplete",
        "same_host_recognition_timing_missing",
    ))
    if claim.get("selector_or_neural_claim_permitted") is not True:
        blockers.append("benchmark_claim_boundary_forbids_learning")

    evidence = {
        "schema": SCHEMA,
        "status": "verified_gross_only_training_abstained",
        "surface_id": SURFACE_ID,
        "query_count": QUERY_COUNT,
        "development_headroom_gate": history.DEVELOPMENT_HEADROOM_GATE,
        "input_bindings": {
            "cross_analysis_path": _relative(cross_analysis_path),
            "cross_analysis_sha256": file_sha256(cross_analysis_path),
            "cross_verification_path": _relative(cross_verification_path),
            "cross_verification_sha256": file_sha256(cross_verification_path),
            "cross_inventory_path": _relative(cross_inventory_path),
            "cross_inventory_sha256": file_sha256(cross_inventory_path),
            "prior_analysis_path": _relative(prior_analysis_path),
            "prior_analysis_sha256": file_sha256(prior_analysis_path),
            "freeze_path": _relative(freeze_path),
            "freeze_file_sha256": file_sha256(freeze_path),
            "prior_verification_path": _relative(prior_verification_path),
            "prior_verification_sha256": file_sha256(prior_verification_path),
            "freeze_sha256": task.get("freeze_sha256"),
            "source_checkpoint_sha256": canonical_sha256(
                freeze.get("source_checkpoint")
            ),
            "source_tree_sha256": freeze.get("source_closure_sha256"),
            "task_contract_sha256": canonical_sha256(task),
        },
        "exact_methods": list(arms),
        "hosts": hosts,
        "cross_host": {
            "complete_cases": len(prior_labels),
            "case_set_sha256": prior_host["case_set_sha256"],
            "output_table_sha256": prior_host["output_table_sha256"],
            "label_agreement_cases": len(prior_labels) - len(disagreements),
            "label_disagreement_cases": len(disagreements),
            "labels_identical": not disagreements,
            "disagreements": disagreements,
            "minimum_gross_speedup": minimum_gross,
            "gross_headroom_at_least_1_10_on_both_hosts": (
                minimum_gross >= history.DEVELOPMENT_HEADROOM_GATE
            ),
        },
        "cost_accounting": {
            "p95_costs_measured_same_host": False,
            "required_costs_ns_per_case": {
                "feature_extraction_and_control": None,
                "model_inference": None,
                "exact_verification": None,
                "expected_fallback": None,
            },
            "fully_charged_speedup": None,
        },
        "claim_boundary": {
            "cross_machine_replication_complete": claim.get(
                "separate_host_and_compiler_replication_complete"
            ) is True,
            "selector_or_neural_claim_permitted": claim.get(
                "selector_or_neural_claim_permitted"
            ) is True,
            "production_routing_permitted": claim.get(
                "production_routing_change_permitted"
            ) is True,
        },
        "blockers": blockers,
        "decision": {
            "development_training_eligible": False,
            "training_performed": False,
            "prospective_data_consumed": False,
            "advice_enabled": False,
            "complete_abstention": True,
            "exact_fallback": "unchanged exact path",
            "production_routing_permitted": False,
        },
    }
    validate_evidence(evidence)
    return evidence


def validate_evidence(evidence: Mapping[str, Any]) -> None:
    _require(
        evidence.get("schema") == SCHEMA
        and evidence.get("status") == "verified_gross_only_training_abstained"
        and evidence.get("surface_id") == SURFACE_ID
        and evidence.get("query_count") == QUERY_COUNT,
        "learning evidence identity",
    )
    hosts = evidence.get("hosts")
    _require(isinstance(hosts, Mapping) and len(hosts) == 2, "learning evidence hosts")
    for host in hosts.values():
        _require(
            host.get("verification_status") == "verified_complete"
            and host.get("q64_rows") == 6912
            and host.get("complete_cases") == 54
            and host.get("repeats_per_case_arm") == EXPECTED_REPEATS
            and math.isclose(
                host.get("gross_speedup"),
                host.get("best_fixed_sum_ns") / host.get("oracle_sum_ns"),
                rel_tol=1e-15,
            ),
            "learning evidence host economics",
        )
    cross = evidence.get("cross_host", {})
    minimum = min(host["gross_speedup"] for host in hosts.values())
    _require(
        math.isclose(cross.get("minimum_gross_speedup"), minimum, rel_tol=1e-15)
        and cross.get("gross_headroom_at_least_1_10_on_both_hosts")
        is (minimum >= history.DEVELOPMENT_HEADROOM_GATE)
        and cross.get("label_agreement_cases") + cross.get("label_disagreement_cases")
        == cross.get("complete_cases")
        and cross.get("labels_identical")
        is (cross.get("label_disagreement_cases") == 0),
        "learning evidence cross-host replay",
    )
    costs = evidence.get("cost_accounting", {})
    required_costs = costs.get("required_costs_ns_per_case", {})
    _require(
        costs.get("p95_costs_measured_same_host") is False
        and costs.get("fully_charged_speedup") is None
        and set(required_costs)
        == {
            "feature_extraction_and_control",
            "model_inference",
            "exact_verification",
            "expected_fallback",
        }
        and all(value is None for value in required_costs.values()),
        "learning evidence cost boundary",
    )
    decision = evidence.get("decision", {})
    _require(
        evidence.get("blockers")
        and decision.get("development_training_eligible") is False
        and decision.get("training_performed") is False
        and decision.get("prospective_data_consumed") is False
        and decision.get("advice_enabled") is False
        and decision.get("complete_abstention") is True
        and decision.get("exact_fallback") == "unchanged exact path"
        and decision.get("production_routing_permitted") is False,
        "learning evidence decision boundary",
    )


def normalize_incomplete_handoff(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Convert verified gross-only evidence into the generic handoff schema."""
    validate_evidence(evidence)
    hosts = evidence["hosts"]
    host_items = list(hosts.items())
    cohort_label_hash = host_items[0][1]["label_table_sha256"]
    label_counts = host_items[0][1]["oracle_label_counts"]
    replications = []
    for host_id, host in host_items:
        replications.append({
            "replication_id": host_id,
            "physical_machine_sha256": host["physical_machine_sha256"],
            "compiler_sha256": host["compiler_sha256"],
            "independent_verification_sha256": host[
                "independent_verification_sha256"
            ],
            "verification_status": host["verification_status"],
            "case_set_sha256": host["case_set_sha256"],
            "label_table_sha256": host["label_table_sha256"],
            "complete_cases": host["complete_cases"],
            "best_fixed_method": host["best_fixed_method"],
            "best_fixed_sum_ns": host["best_fixed_sum_ns"],
            "oracle_sum_ns": host["oracle_sum_ns"],
            "gross_speedup": host["gross_speedup"],
            "p95_costs_ns_per_case": dict(
                evidence["cost_accounting"]["required_costs_ns_per_case"]
            ),
            "p95_costs_measured_same_host": False,
            "fully_charged_speedup": None,
            "sum_based_economics": True,
            "schedule_mismatches": 0,
            "semantic_mismatches": 0,
            "source_or_artifact_mismatches": 0,
        })
    bindings = evidence["input_bindings"]
    return {
        "schema": "crse-learning-benchmark-handoff/v1",
        "status": "incomplete",
        "surface_id": evidence["surface_id"],
        "task_contract_sha256": bindings["task_contract_sha256"],
        "source_checkpoint": bindings["source_checkpoint_sha256"],
        "source_tree": bindings["source_tree_sha256"],
        "freeze_sha256": bindings["freeze_sha256"],
        "baseline_closure": {
            "status": "verified_complete",
            "sha256": canonical_sha256(evidence["exact_methods"]),
            "all_relevant_exact_baselines_included": True,
        },
        "cohort": {
            "role": "retrospective_development",
            "protocol_frozen_before_labels": False,
            "source_groups": evidence["cross_host"]["complete_cases"],
            "source_groups_by_split": {
                "development_fit": evidence["cross_host"]["complete_cases"],
                "development_validation": 0,
                "development_audit": 0,
            },
            "source_groups_per_label": dict(label_counts),
            "cross_split_source_group_intersections": 0,
            "prospective_cases_consumed": 0,
            "case_set_sha256": evidence["cross_host"]["case_set_sha256"],
            "label_table_sha256": cohort_label_hash,
        },
        "exact_methods": {
            "arms": list(evidence["exact_methods"]),
            "refused_rows_retained": True,
            "task_identical_exact_outputs": True,
        },
        "replications": replications,
        "claim_boundary": {
            "development_training_eligibility_permitted": False,
            "prospective_consumption_permitted": False,
            "production_routing_permitted": False,
        },
    }
