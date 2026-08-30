"""Execution-readiness and trivial functional gates for the frozen P7 study.

This module does not run a timing campaign.  It binds the human-readable arm
names in a P6 freeze to concrete implementations, verifies that every P7 case
has an executable input, and supplies a tiny deterministic correctness check.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from bitset_backend import (
    PreparedFlatEvaluation,
    _bind_flat_program,
    _eval_prepared_flat,
    compile_expr_cse,
    compile_expr_flat,
    eval_cm_node_flat,
)
from cm_expr_serde import expr_from_json
from cm_ir import CMIRBuilder, _BuildState, compile_expr_to_cm_ir

from cmbench.recognition.blif import parse_blif

from .arms import execute_arm, scalar_relation, semantic_sha256
from .contracts import CONTRACT_SCHEMA, canonical_bytes
from .corpus_freeze import validate_freeze, verify_sources
from .ir import cm_ir_stats, flat_program_record


READINESS_SCHEMA = "cm-comparative-p7-execution-readiness/v1"
DRY_RUN_SCHEMA = "cm-comparative-p7-offline-dry-run/v1"
IR_ARMS = {
    "cm-ir-current": "compile_expr_to_cm_ir/current-one-memo",
    "cm-ir-two-memo": "CMIRBuilder/historical-two-memo-control",
    "cm-cse-flat": "compile_expr_cse/flat",
    "cm-raw-flat": "compile_expr_flat/raw",
}
RELATION_ARMS = {
    "cm-dense": ("cm_dense", "dense_cm"),
    "cm-packed-bigint": ("cm_flat_bigint", "packed_bigint"),
    "cm-packed-words": ("cm_flat_words", "packed_words"),
    "cm-no-reinflate": ("cm_no_reinflate", "packed_bigint"),
    "cm-cse-flat": ("cse_flat", "packed_bigint"),
}
P7_POLICIES = {"p7-ir": ("ir_preparation", IR_ARMS),
               "p7-relation": ("complete_relation", RELATION_ARMS)}


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _strict_json(text: str) -> Any:
    def pairs(items):
        value = {}
        for key, item in items:
            _require(key not in value, "duplicate JSON key")
            value[key] = item
        return value

    def constant(_value):
        raise ValueError("nonfinite JSON")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def _source_path(case: Mapping[str, Any], project: Path) -> Path:
    path = (project / PurePosixPath(case["source"]["path"])).resolve()
    _require(path.is_relative_to(project) and path.is_file(), "case source unavailable")
    return path


def _jsonl_member(case: Mapping[str, Any], project: Path) -> Mapping[str, Any]:
    member_id = case["source"]["member_id"]
    matches = []
    for line in _source_path(case, project).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = _strict_json(line)
        if isinstance(record, Mapping) and record.get("id") == member_id:
            matches.append(record)
    _require(len(matches) == 1, "JSONL member identity is not unique")
    record = matches[0]
    _require(hashlib.sha256(canonical_bytes(record)).hexdigest()
             == case["source"]["member_sha256"], "JSONL member identity changed")
    return record


def load_case_expression(case: Mapping[str, Any], project_root: str | Path) -> tuple[Any, tuple[str, ...]]:
    """Load one frozen expression without running a backend or an oracle."""
    project = Path(project_root).resolve()
    kind = case["kind"]
    if kind == "expression_jsonl_member":
        record = _jsonl_member(case, project)
        document = record.get("expression_v2")
        _require(isinstance(document, Mapping), "expression_v2 member missing")
        live_k = case["strata"].get("live_k")
        _require(type(live_k) is int and 1 <= live_k <= 16, "P7 expression width outside bound")
        variable_indices = {
            node["i"] for node in document.get("nodes", [])
            if isinstance(node, Mapping) and node.get("op") == "var"
        }
        _require(variable_indices and min(variable_indices) >= 0 and max(variable_indices) < live_k,
                 "expression variable outside frozen width")
        return expr_from_json(document), tuple(f"x{index}" for index in range(live_k))
    if kind == "blif":
        strata = case["strata"]
        root = strata.get("root")
        _require(isinstance(root, str) and root, "BLIF root is not frozen")
        netlist = parse_blif(_source_path(case, project))
        metadata = netlist.bounded_metadata(
            root,
            min_support=4,
            max_support=strata.get("selection_max_support"),
            max_source_nodes=strata.get("selection_max_source_nodes"),
        )
        _require(metadata is not None, "frozen BLIF root no longer meets bounds")
        expected = {
            "root": metadata.node,
            "support": list(metadata.support),
            "live_k": len(metadata.support),
            "syntactic_support": len(metadata.support),
            "dag_nodes": metadata.source_nodes,
            "source_edges": metadata.source_edges,
            "depth": metadata.depth,
            "local_fanin": metadata.local_fanin,
            "local_cubes": metadata.local_cubes,
            "local_literals": metadata.local_literals,
        }
        _require(all(strata.get(key) == value for key, value in expected.items()),
                 "frozen BLIF cone metadata changed")
        expression, support = netlist.build_expr(root, max_identity_nodes=4096)
        _require(support == metadata.support, "BLIF translation support changed")
        return expression, tuple(f"x{index}" for index in range(len(support)))
    raise ValueError("case kind is not executable by P7")


def execution_readiness(freeze: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    """Fail closed if frozen P7 policy names or case preparation are ambiguous."""
    validate_freeze(freeze)
    project = Path(project_root).resolve()
    source_check = verify_sources(freeze, project)
    reasons: list[str] = []
    policies = {row["policy_id"]: row for row in freeze["schedule_policies"]}
    policy_rows = []
    prepared_case_ids: set[str] = set()
    for policy_id, (task, registry) in P7_POLICIES.items():
        policy = policies.get(policy_id)
        if policy is None:
            reasons.append("policy_missing:" + policy_id)
            continue
        if policy["task"] != task:
            reasons.append("policy_task_mismatch:" + policy_id)
        if policy["arms"] != list(registry):
            reasons.append("policy_arm_binding_mismatch:" + policy_id)
        eligible = [
            case for case in freeze["cases"]
            if task in case["tasks"] and case["role"] in policy["eligible_roles"]
        ]
        role_counts = {role: sum(case["role"] == role for case in eligible)
                       for role in ("regression", "development", "confirmation")}
        if not eligible:
            reasons.append("policy_has_no_cases:" + policy_id)
        for case in eligible:
            if case["case_id"] in prepared_case_ids:
                continue
            try:
                load_case_expression(case, project)
            except (KeyError, TypeError, ValueError) as exc:
                reasons.append(f"case_not_preparable:{case['case_id']}:{exc}")
            else:
                prepared_case_ids.add(case["case_id"])
        policy_rows.append({
            "policy_id": policy_id,
            "task": task,
            "arms": list(registry),
            "eligible_cases": len(eligible),
            "role_counts": role_counts,
        })
    if source_check["verified"] is not True:
        reasons.append("source_identity_verification_failed")
    return {
        "schema": READINESS_SCHEMA,
        "freeze_sha256": freeze["freeze_sha256"],
        "source_verified": source_check["verified"],
        "policies": policy_rows,
        "prepared_unique_cases": len(prepared_case_ids),
        "arm_bindings": {
            "ir_preparation": dict(IR_ARMS),
            "complete_relation": {
                arm: {"implementation": value[0], "artifact": value[1]}
                for arm, value in RELATION_ARMS.items()
            },
        },
        "performance_measurement": False,
        "reasons": sorted(set(reasons)),
        "ready_for_offline_dry_run": not reasons,
    }


def _two_memo_compile(expr: Any) -> Any:
    builder = CMIRBuilder(share_aware_flatten=True, build_memo=True)
    uid_by_id, shared_uids = builder._shared_assoc_uids(expr)
    state = _BuildState({}, set(), uid_by_id, shared_uids)
    builder._build_state = state
    try:
        return builder._build_rec(expr, state)
    finally:
        builder._build_state = None


def _execute_program(program: Any, variables: tuple[str, ...]) -> int:
    template, full_mask = _bind_flat_program(program, variables, {})
    return _eval_prepared_flat(PreparedFlatEvaluation(program, template, full_mask, False))


def _compile_ir_artifact(expr: Any, arm: str) -> tuple[Any, str]:
    """Build one declared IR artifact without evaluating its semantics."""
    _require(arm in IR_ARMS, "unknown P7 IR arm")
    if arm == "cm-ir-current":
        return compile_expr_to_cm_ir(
            expr, reuse_cache=False, persistent_cache=False, share_aware_flatten=True,
        ), "ordered_cm_ir"
    if arm == "cm-ir-two-memo":
        return _two_memo_compile(expr), "ordered_cm_ir"
    if arm == "cm-cse-flat":
        return compile_expr_cse(expr, flatten=True), "flat_program"
    return compile_expr_flat(expr), "flat_program"


def _inspect_ir_artifact(
    artifact: Any,
    kind: str,
    variables: tuple[str, ...],
) -> tuple[str, str]:
    """Return artifact and semantic identities after the measured span."""
    if kind == "ordered_cm_ir":
        record = cm_ir_stats(artifact)
        bits = eval_cm_node_flat(artifact, variables, fixed={})
        digest = record["cm_ir_signature_sha256"]
    elif kind == "flat_program":
        record = flat_program_record(artifact)
        bits = _execute_program(artifact, variables)
        digest = record["flat_program_sha256"]
    else:
        raise ValueError("unknown P7 IR artifact kind")
    return digest, semantic_sha256(bits, len(variables))


def execute_ir_functional(expr: Any, variables: tuple[str, ...], arm: str) -> dict[str, Any]:
    """Compile and evaluate one IR control with no retained clock measurements."""
    _require(arm in IR_ARMS and 1 <= len(variables) <= 8, "offline IR dry-run bound")
    if arm == "cm-ir-current":
        artifact = compile_expr_to_cm_ir(
            expr, reuse_cache=False, persistent_cache=False, share_aware_flatten=True,
        )
        record = cm_ir_stats(artifact)
        bits = eval_cm_node_flat(artifact, variables, fixed={})
        kind = "ordered_cm_ir"
        digest = record["cm_ir_signature_sha256"]
    elif arm == "cm-ir-two-memo":
        artifact = _two_memo_compile(expr)
        record = cm_ir_stats(artifact)
        bits = eval_cm_node_flat(artifact, variables, fixed={})
        kind = "ordered_cm_ir"
        digest = record["cm_ir_signature_sha256"]
    else:
        artifact = compile_expr_cse(expr, flatten=True) if arm == "cm-cse-flat" else compile_expr_flat(expr)
        record = flat_program_record(artifact)
        bits = _execute_program(artifact, variables)
        kind = "flat_program"
        digest = record["flat_program_sha256"]
    return {
        "arm": arm,
        "artifact_kind": kind,
        "artifact_sha256": digest,
        "semantic_sha256": semantic_sha256(bits, len(variables)),
        "performance_measurement": False,
    }


def execute_ir_cell(
    expr: Any,
    variables: tuple[str, ...],
    arm: str,
    *,
    clock=time.perf_counter_ns,
) -> dict[str, Any]:
    """Compile one P7 IR arm and validate semantics outside the timed span."""
    _require(arm in IR_ARMS and 1 <= len(variables) <= 16, "P7 IR cell bound")
    started = clock()
    artifact, kind = _compile_ir_artifact(expr, arm)
    finished = clock()
    _require(
        type(started) is int and type(finished) is int and 0 <= started < finished,
        "invalid P7 IR clock",
    )
    digest, semantics = _inspect_ir_artifact(artifact, kind, variables)
    return {
        "arm": arm,
        "artifact_kind": kind,
        "artifact_sha256": digest,
        "semantic_sha256": semantics,
        "timings_ns": {"task_total_wall_ns": finished - started},
        "validation_in_timed_span": False,
    }


def execute_ir_source_cell(
    case: Mapping[str, Any],
    project_root: str | Path,
    arm: str,
    *,
    clock=time.perf_counter_ns,
) -> dict[str, Any]:
    """Time source load/translation and IR construction, then validate outside."""
    started = clock()
    expression, variables = load_case_expression(case, project_root)
    _require(arm in IR_ARMS and 1 <= len(variables) <= 16, "P7 IR source-cell bound")
    artifact, kind = _compile_ir_artifact(expression, arm)
    finished = clock()
    _require(
        type(started) is int and type(finished) is int and 0 <= started < finished,
        "invalid P7 IR source-cell clock",
    )
    digest, semantics = _inspect_ir_artifact(artifact, kind, variables)
    return {
        "arm": arm,
        "artifact_kind": kind,
        "artifact_sha256": digest,
        "semantic_sha256": semantics,
        "timings_ns": {"task_total_wall_ns": finished - started},
        "validation_in_timed_span": False,
        "source_preparation_in_timed_span": True,
    }


def _relation_contract(
    arm: str,
    variables: tuple[str, ...],
    expected: str,
    *,
    lifecycle: str = "resident_engine",
) -> dict[str, Any]:
    implementation, kind = RELATION_ARMS[arm]
    return {
        "schema": CONTRACT_SCHEMA,
        "contract_id": "p7-offline-" + implementation,
        "task": "complete_relation",
        "artifact": {
            "kind": kind,
            "variable_order": list(variables),
            "output_order": list(variables),
            "fixed": [],
            "output_scope": "full",
            "restoration": "none",
            "stream": None,
        },
        "lifecycle": lifecycle,
        "queries": 1,
        "validation": {
            "oracle": "independent_scalar_assignment/v1",
            "validation_in_timed_span": False,
            "required_output_sha256": expected,
        },
    }


def offline_dry_run(freeze: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    """Run two k<=8 synthetic cases; returned records contain no durations."""
    readiness = execution_readiness(freeze, project_root)
    _require(readiness["ready_for_offline_dry_run"], "P7 execution readiness failed")
    selected = []
    for role in ("regression", "development"):
        candidates = sorted(
            (case for case in freeze["cases"]
             if case["role"] == role and case["kind"] == "expression_jsonl_member"
             and type(case["strata"].get("live_k")) is int and case["strata"]["live_k"] <= 8),
            key=lambda case: case["case_id"],
        )
        _require(candidates, "bounded synthetic dry-run case missing")
        selected.append(candidates[0])

    rows = []
    for case in selected:
        expr, variables = load_case_expression(case, project_root)
        oracle = semantic_sha256(scalar_relation(expr, variables, {}), len(variables))
        ir_rows = [execute_ir_functional(expr, variables, arm) for arm in IR_ARMS]
        _require(all(row["semantic_sha256"] == oracle for row in ir_rows), "IR semantic mismatch")
        _require(ir_rows[0]["artifact_sha256"] == ir_rows[1]["artifact_sha256"],
                 "one-memo and two-memo ordered IR mismatch")
        relation_rows = []
        for arm, (implementation, _kind) in RELATION_ARMS.items():
            result = execute_arm(
                expr=expr,
                contract=_relation_contract(arm, variables, oracle),
                case_id=case["case_id"],
                arm=implementation,
                smoke_bound=8,
                clock=iter(range(1_000_000)).__next__,
            )
            relation_rows.append({
                "arm": arm,
                "implementation": implementation,
                "semantic_sha256": result["artifact"]["sha256"],
                "status": result["status"],
                "performance_measurement": False,
            })
        _require(all(row["semantic_sha256"] == oracle for row in relation_rows),
                 "relation semantic mismatch")
        rows.append({
            "case_id": case["case_id"],
            "role": case["role"],
            "k": len(variables),
            "oracle_sha256": oracle,
            "ir": ir_rows,
            "complete_relation": relation_rows,
        })
    return {
        "schema": DRY_RUN_SCHEMA,
        "freeze_sha256": freeze["freeze_sha256"],
        "cases": rows,
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "status": "passed",
    }
