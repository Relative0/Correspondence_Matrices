"""Deterministic source-blind freeze for the architecture comparison campaign."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import random
import re
from typing import Any

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor
from cmbench.recognition.features import extract_features, structural_digest

from .architecture_refresh_harness import build_plan, validate_plan
from .comparison_prefreeze import validate_prefreeze
from .contracts import canonical_bytes
from .gf2_multi_root import expressions_to_multi_root_dag
from .schedule import balanced_orders


SCHEMA = "cm-architecture-comparison-freeze/v1"
SEED = 2_026_090_303
WIDTHS = (8, 11, 14)
FAMILIES = ("andor", "xor_eqv", "mixed")
SHAPES = ("tree", "high_sharing")
REPLICATES = 2
QUERY_COUNTS = (1, 4, 16, 64)
SHA256 = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")

OBSERVED_SOURCES = {
    "public_complete_relation_regression":
        "deliverables_n22_24/v4audit_corpus_2026_07_24.jsonl",
    "repeated_restriction_regression":
        "docs/recognition/c36_wide_repeated_query_dataset.json",
    "related_root_regression":
        "docs/recognition/c37_native_exact_confirmation_dataset.json",
    "smaller_task_functional_control":
        "docs/recognition/runs/architecture-refresh-harness-development-20260903-001/RESULT.json",
}

SOURCE_CLOSURE_PATHS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cm_normalize.py",
    "cmbench/comparative/architecture_comparison_freeze.py",
    "cmbench/comparative/architecture_refresh_harness.py",
    "cmbench/comparative/arms.py",
    "cmbench/comparative/comparison_prefreeze.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/gf2_multi_root.py",
    "cmbench/comparative/gf2_multi_root_python.py",
    "cmbench/comparative/gf2_native_slots.py",
    "cmbench/comparative/gf2_restricted_evaluators.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "cmbench/comparative/persistence.py",
    "cmbench/comparative/tasks.py",
    "cmbench/backends/native_restriction.py",
    "native/cm_fused_slots/fused_slot_executor.c",
    "scripts/crse_prepare_architecture_comparison_freeze.py",
    "scripts/crse_verify_architecture_comparison_freeze.py",
)


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _file_identity(root: Path, relative: str) -> dict[str, Any]:
    path = (root / relative).resolve()
    _require(path.is_relative_to(root) and path.is_file(), f"missing source: {relative}")
    payload = path.read_bytes()
    return {"path": relative, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _rng(*parts: object) -> random.Random:
    payload = ":".join(str(part) for part in (SEED, *parts)).encode("ascii")
    return random.Random(int.from_bytes(hashlib.sha256(payload).digest(), "big"))


def _operators(family: str) -> tuple[type, ...]:
    if family == "andor":
        return (And, Or)
    if family == "xor_eqv":
        return (Xor, Eqv)
    if family == "mixed":
        return (And, Or, Xor, Imp, Eqv)
    raise ValueError("unknown fresh structural family")


def _balanced_tree(n_vars: int, family: str, rng: random.Random) -> Expr:
    variables = list(range(n_vars))
    rng.shuffle(variables)
    level: list[Expr] = [Var(index) for index in variables]
    operators = _operators(family)
    while len(level) > 1:
        next_level: list[Expr] = []
        for offset in range(0, len(level), 2):
            if offset + 1 == len(level):
                next_level.append(level[offset])
                continue
            left, right = level[offset], level[offset + 1]
            if rng.randrange(7) == 0:
                left = Not(left)
            if rng.randrange(11) == 0:
                right = Not(right)
            next_level.append(rng.choice(operators)(left, right))
        level = next_level
    return level[0]


def _fresh_expression(n_vars: int, family: str, shape: str, replicate: int) -> Expr:
    rng = _rng("single", n_vars, family, shape, replicate)
    base = _balanced_tree(n_vars, family, rng)
    if shape == "tree":
        return base
    if shape != "high_sharing":
        raise ValueError("unknown fresh structural shape")
    tail = _balanced_tree(n_vars, family, rng)
    operators = _operators(family)
    left = operators[replicate % len(operators)](base, tail)
    right = operators[(replicate + 1) % len(operators)](base, Not(tail))
    return operators[(replicate + 2) % len(operators)](left, right)


def _case_record(n_vars: int, family: str, shape: str, replicate: int) -> dict[str, Any]:
    expression = _fresh_expression(n_vars, family, shape, replicate)
    document = expr_to_json_dag(expression)
    features = extract_features(expression, n_vars, queries=max(QUERY_COUNTS))
    case_id = f"fresh-{shape.replace('_', '-')}-{family.replace('_', '-')}-k{n_vars}-r{replicate}"
    return {
        "case_id": case_id,
        "cluster_id": case_id,
        "n_vars": n_vars,
        "family": family,
        "shape": shape,
        "replicate": replicate,
        "expression_v2": document,
        "expression_v2_sha256": _digest(document),
        "structural_digest": structural_digest(expression),
        "alpha_structural_digest": structural_digest(expression, alpha_rename=True),
        "structural_selection": {
            "identity_nodes": features.identity_nodes,
            "structural_nodes": features.structural_nodes,
            "depth": features.depth,
            "unfolded_nodes_capped": features.unfolded_nodes_capped,
            "sharing_fraction": features.values[4],
        },
    }


def generate_fresh_single_cases() -> list[dict[str, Any]]:
    cases = [
        _case_record(n_vars, family, shape, replicate)
        for n_vars in WIDTHS
        for family in FAMILIES
        for shape in SHAPES
        for replicate in range(REPLICATES)
    ]
    _require(len({row["case_id"] for row in cases}) == len(cases), "fresh case IDs")
    _require(
        len({row["alpha_structural_digest"] for row in cases}) == len(cases),
        "fresh alpha-structural duplicates",
    )
    _require(
        all(
            (row["structural_selection"]["sharing_fraction"] == 0.0)
            == (row["shape"] == "tree")
            for row in cases
        ),
        "fresh shape contract",
    )
    return cases


def _multi_root_record(n_vars: int, replicate: int) -> dict[str, Any]:
    base = _fresh_expression(n_vars, "mixed", "high_sharing", replicate)
    roots = (
        And(base, Var(0)),
        Or(base, Var(n_vars - 1)),
        Xor(base, Not(Var(n_vars // 2))),
    )
    union = expressions_to_multi_root_dag(roots)
    separate = [expr_to_json_dag(root) for root in roots]
    case_id = f"fresh-related-roots-mixed-k{n_vars}-r{replicate}"
    return {
        "case_id": case_id,
        "cluster_id": case_id,
        "n_vars": n_vars,
        "family": "mixed_related_roots",
        "roots": len(roots),
        "union_document": union,
        "union_document_sha256": _digest(union),
        "separate_documents": separate,
        "separate_document_sha256": [_digest(document) for document in separate],
        "union_nodes": len(union["nodes"]),
        "sum_separate_nodes": sum(len(document["nodes"]) for document in separate),
    }


def generate_fresh_multi_root_cases() -> list[dict[str, Any]]:
    cases = [
        _multi_root_record(n_vars, replicate)
        for n_vars in WIDTHS
        for replicate in range(REPLICATES)
    ]
    _require(
        all(row["union_nodes"] < row["sum_separate_nodes"] for row in cases),
        "fresh multi-root sharing contract",
    )
    return cases


def generate_fresh_history_pairs(single_cases: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected = [row for row in single_cases if row["family"] == "mixed" and row["shape"] == "tree"]
    pairs = []
    for row in selected:
        source = expr_from_json(row["expression_v2"])
        edited = Xor(source, Var((row["n_vars"] // 2 + row["replicate"]) % row["n_vars"]))
        edited_document = expr_to_json_dag(edited)
        pairs.append({
            "case_id": "history-" + row["case_id"],
            "cluster_id": row["cluster_id"],
            "n_vars": row["n_vars"],
            "source_expression_v2": row["expression_v2"],
            "source_expression_v2_sha256": row["expression_v2_sha256"],
            "edited_expression_v2": edited_document,
            "edited_expression_v2_sha256": _digest(edited_document),
            "edit_kind": "append_xor_literal",
        })
    return pairs


def _load_observed(root: Path) -> tuple[dict[str, Any], set[str]]:
    bindings = {}
    prior_structural: set[str] = set()

    public_path = root / OBSERVED_SOURCES["public_complete_relation_regression"]
    public_rows = [json.loads(line) for line in public_path.read_text(encoding="utf-8").splitlines() if line]
    public_ids = [row["id"] for row in public_rows]
    for row in public_rows:
        prior_structural.add(structural_digest(expr_from_json(row["expression"]), alpha_rename=True))

    c36_path = root / OBSERVED_SOURCES["repeated_restriction_regression"]
    c36 = json.loads(c36_path.read_text(encoding="utf-8"))
    c36_ids = [row["case_id"] for row in c36["cases"]]
    for row in c36["cases"]:
        prior_structural.add(
            structural_digest(expr_from_json(row["expression_v2"]), alpha_rename=True)
        )

    c37_path = root / OBSERVED_SOURCES["related_root_regression"]
    c37 = json.loads(c37_path.read_text(encoding="utf-8"))
    c37_ids = [row["workload_id"] for row in c37["multi_root"]["workloads"]]

    functional_path = root / OBSERVED_SOURCES["smaller_task_functional_control"]
    functional = json.loads(functional_path.read_text(encoding="utf-8"))
    functional_ids = [functional["lanes"]["D"]["case_id"]]

    identity_rows = {
        "public_complete_relation_regression": public_ids,
        "repeated_restriction_regression": c36_ids,
        "related_root_regression": c37_ids,
        "smaller_task_functional_control": functional_ids,
    }
    for name, relative in OBSERVED_SOURCES.items():
        binding = _file_identity(root, relative)
        binding.update({
            "case_count": len(identity_rows[name]),
            "case_ids": identity_rows[name],
            "case_ids_sha256": _digest(identity_rows[name]),
            "role": "observed_regression",
        })
        bindings[name] = binding
    return bindings, prior_structural


def _schedule(case_ids: Sequence[str], arms: Sequence[str], seed_label: str) -> dict[str, Any]:
    ordered = list(case_ids)
    _rng("schedule", seed_label).shuffle(ordered)
    orders = [list(row) for row in balanced_orders(tuple(arms))]
    schedule = {
        "case_order": ordered,
        "case_order_sha256": _digest(ordered),
        "arms": list(arms),
        "arm_orders": orders,
        "blocks": len(orders),
        "counterbalance_all_arm_positions": True,
        "seed": SEED,
        "selection_blind_to_method_outputs_and_timings": True,
        "planned_cells": len(ordered) * len(orders) * len(arms),
    }
    schedule["schedule_sha256"] = _digest(schedule)
    return schedule


def _source_closure(root: Path) -> list[dict[str, Any]]:
    return [_file_identity(root, relative) for relative in SOURCE_CLOSURE_PATHS]


def build_freeze(*, project_root: str | Path, source_checkpoint: str) -> dict[str, Any]:
    root = Path(project_root).resolve()
    _require(COMMIT.fullmatch(source_checkpoint) is not None, "source checkpoint")
    prefreeze_path = root / "docs/recognition/architecture_comparison_prefreeze_20260903/PREFREEZE.json"
    prefreeze = json.loads(prefreeze_path.read_text(encoding="utf-8"))
    validate_prefreeze(prefreeze)
    _require(prefreeze["status"] == "ready_for_corpus_freeze", "prefreeze decision")

    observed, prior_structural = _load_observed(root)
    single = generate_fresh_single_cases()
    _require(
        not prior_structural.intersection(row["alpha_structural_digest"] for row in single),
        "fresh corpus overlaps observed structural identities",
    )
    multi_root = generate_fresh_multi_root_cases()
    histories = generate_fresh_history_pairs(single)
    plan = build_plan(native_available=True)
    validate_plan(plan)

    lane_a_cases = observed["public_complete_relation_regression"]["case_ids"] + [
        row["case_id"] for row in single
    ]
    lane_b_cases = observed["repeated_restriction_regression"]["case_ids"] + [
        row["case_id"] for row in single
    ]
    lane_c_cases = observed["related_root_regression"]["case_ids"] + [
        row["case_id"] for row in multi_root
    ]
    lane_d_cases = observed["smaller_task_functional_control"]["case_ids"] + [
        row["case_id"] for row in histories
    ]
    schedules = {
        "A": _schedule(lane_a_cases, plan["lanes"]["A"]["arms"], "lane-a"),
        "B": {
            **_schedule(lane_b_cases, plan["lanes"]["B"]["arms"], "lane-b"),
            "query_counts": list(QUERY_COUNTS),
        },
        "C": _schedule(lane_c_cases, plan["lanes"]["C"]["arms"], "lane-c"),
        "D": {
            "case_order": lane_d_cases,
            "task_lifecycles": plan["lanes"]["D"]["task_lifecycles"],
            "task_sublanes": {
                task: _schedule(
                    lane_d_cases,
                    plan["lanes"]["D"]["task_backends"],
                    "lane-d-" + task,
                )
                for task in plan["lanes"]["D"]["sublanes"]
                if task != "structural_reload"
            },
            "structural_reload": _schedule(
                lane_d_cases,
                plan["lanes"]["D"]["persistence_backends"],
                "lane-d-structural-reload",
            ),
        },
    }
    source_closure = _source_closure(root)
    core = {
        "schema": SCHEMA,
        "status": "frozen_not_authorized",
        "date": "2026-09-03",
        "source_checkpoint": source_checkpoint,
        "prefreeze_sha256": hashlib.sha256(prefreeze_path.read_bytes()).hexdigest(),
        "source_closure": source_closure,
        "source_closure_sha256": _digest(source_closure),
        "observed_regression_bindings": observed,
        "fresh_corpus": {
            "generator": "architecture_comparison_freeze/v1",
            "seed": SEED,
            "widths": list(WIDTHS),
            "families": list(FAMILIES),
            "shapes": list(SHAPES),
            "replicates": REPLICATES,
            "single_root_cases": single,
            "multi_root_cases": multi_root,
            "history_pairs": histories,
            "selection_inputs": [
                "seed",
                "declared widths/families/shapes",
                "identity-DAG node count",
                "depth",
                "sharing fraction",
                "prior alpha-structural identities",
            ],
            "truth_outputs_inspected": False,
            "method_outputs_inspected": False,
            "method_timings_inspected": False,
            "fresh_alpha_structural_overlap_count": 0,
        },
        "arm_configurations": plan["lanes"],
        "schedules": schedules,
        "measurement_fields": prefreeze["dormant_campaign_blueprint"]["required_measurement_fields"],
        "publication_gates": {
            **prefreeze["dormant_campaign_blueprint"]["publication_gates"],
            "historical_1_472x_retained_as_windows_only": True,
            "no_universal_winner_headline": True,
            "new_contracts_receive_separate_sections": True,
            "selector_or_neural_claims_prohibited": True,
        },
        "permissions": {
            "source_identity_freeze_complete": True,
            "local_functional_replay": True,
            "fresh_truth_oracle_generation": False,
            "timed_local_campaign": False,
            "runpod_authorization_request": False,
            "runpod_execution": False,
            "selector_fitting": False,
            "neural_training": False,
            "production_routing_change": False,
            "website_publication": False,
        },
        "timing_evidence_produced": False,
        "cloud_resource_created": False,
    }
    freeze = {**core, "freeze_sha256": _digest(core)}
    validate_freeze(freeze)
    return freeze


def validate_freeze(freeze: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "schema", "status", "date", "source_checkpoint", "prefreeze_sha256",
        "source_closure", "source_closure_sha256", "observed_regression_bindings",
        "fresh_corpus", "arm_configurations", "schedules", "measurement_fields",
        "publication_gates", "permissions", "timing_evidence_produced",
        "cloud_resource_created", "freeze_sha256",
    }
    _require(isinstance(freeze, Mapping) and set(freeze) == expected, "freeze fields")
    core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    _require(
        freeze["schema"] == SCHEMA
        and freeze["status"] == "frozen_not_authorized"
        and COMMIT.fullmatch(freeze["source_checkpoint"]) is not None
        and SHA256.fullmatch(freeze["prefreeze_sha256"]) is not None
        and freeze["freeze_sha256"] == _digest(core)
        and freeze["source_closure_sha256"] == _digest(freeze["source_closure"]),
        "freeze identity",
    )
    source_paths = [row.get("path") for row in freeze["source_closure"]]
    _require(source_paths == list(SOURCE_CLOSURE_PATHS), "source closure paths")
    _require(
        all(
            set(row) == {"path", "bytes", "sha256"}
            and type(row["bytes"]) is int
            and row["bytes"] > 0
            and SHA256.fullmatch(row["sha256"]) is not None
            for row in freeze["source_closure"]
        ),
        "source closure records",
    )
    fresh = freeze["fresh_corpus"]
    _require(
        fresh.get("seed") == SEED
        and fresh.get("widths") == list(WIDTHS)
        and fresh.get("families") == list(FAMILIES)
        and fresh.get("shapes") == list(SHAPES)
        and fresh.get("replicates") == REPLICATES
        and fresh.get("truth_outputs_inspected") is False
        and fresh.get("method_outputs_inspected") is False
        and fresh.get("method_timings_inspected") is False
        and fresh.get("fresh_alpha_structural_overlap_count") == 0,
        "fresh selection boundary",
    )
    single = fresh.get("single_root_cases")
    _require(
        isinstance(single, list)
        and len(single) == len(WIDTHS) * len(FAMILIES) * len(SHAPES) * REPLICATES
        and single == generate_fresh_single_cases(),
        "fresh single-root replay",
    )
    _require(fresh.get("multi_root_cases") == generate_fresh_multi_root_cases(), "fresh multi-root replay")
    _require(fresh.get("history_pairs") == generate_fresh_history_pairs(single), "fresh history replay")
    plan = build_plan(native_available=True)
    _require(freeze["arm_configurations"] == plan["lanes"], "arm configurations")
    for lane in ("A", "B", "C"):
        schedule = freeze["schedules"][lane]
        _require(
            schedule["arm_orders"] == [list(row) for row in balanced_orders(schedule["arms"])]
            and schedule["blocks"] == len(schedule["arm_orders"])
            and schedule["counterbalance_all_arm_positions"] is True
            and schedule["selection_blind_to_method_outputs_and_timings"] is True,
            f"lane {lane} schedule",
        )
    permissions = freeze["permissions"]
    _require(
        permissions.get("source_identity_freeze_complete") is True
        and permissions.get("local_functional_replay") is True
        and all(
            permissions.get(field) is False
            for field in (
                "fresh_truth_oracle_generation", "timed_local_campaign",
                "runpod_authorization_request", "runpod_execution", "selector_fitting",
                "neural_training", "production_routing_change", "website_publication",
            )
        )
        and freeze["timing_evidence_produced"] is False
        and freeze["cloud_resource_created"] is False,
        "freeze permissions",
    )
    return dict(freeze)


def verify_freeze(freeze: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    validate_freeze(freeze)
    root = Path(project_root).resolve()
    observed, prior_structural = _load_observed(root)
    source_match = all(_file_identity(root, row["path"]) == row for row in freeze["source_closure"])
    observed_match = observed == freeze["observed_regression_bindings"]
    fresh = freeze["fresh_corpus"]["single_root_cases"]
    fresh_no_overlap = not prior_structural.intersection(
        row["alpha_structural_digest"] for row in fresh
    )
    replay = build_freeze(project_root=root, source_checkpoint=freeze["source_checkpoint"])
    result = {
        "schema": "cm-architecture-comparison-freeze-verification/v1",
        "status": "verified_frozen_not_authorized",
        "freeze_sha256": freeze["freeze_sha256"],
        "source_closure_match": source_match,
        "observed_bindings_match": observed_match,
        "fresh_structural_overlap_count": 0 if fresh_no_overlap else 1,
        "replay_byte_identical": canonical_bytes(replay) == canonical_bytes(freeze),
        "fresh_truth_outputs_inspected": False,
        "method_timings_inspected": False,
        "timing_evidence_produced": False,
        "cloud_resource_created": False,
    }
    _require(
        source_match and observed_match and fresh_no_overlap and result["replay_byte_identical"],
        "freeze verification",
    )
    return result
