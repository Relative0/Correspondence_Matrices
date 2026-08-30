"""Fail-closed Linux isolated-cell runner for the frozen P7 development study."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import linux_supervisor, p7
from .arms import execute_arm, scalar_relation, semantic_sha256
from .contracts import RESULT_STATUSES, canonical_bytes
from .corpus_freeze import validate_freeze, verify_sources
from .evidence import append_record


PLAN_SCHEMA = "cm-comparative-p7-isolated-plan/v2"
REQUEST_SCHEMA = "cm-comparative-p7-isolated-request/v2"
WORKER_SCHEMA = "cm-comparative-p7-isolated-worker/v2"
SUMMARY_SCHEMA = "cm-comparative-p7-isolated-summary/v2"
SOURCE_SCHEMA = "cm-comparative-p7-isolated-source-identity/v2"
ENVIRONMENT_SCHEMA = "cm-comparative-p7-isolated-environment/v1"
ORACLE_RECORD_SCHEMA = "cm-comparative-p7-oracle-record/v1"
ORACLE_PACKAGE_SCHEMA = "cm-comparative-p7-oracle-package/v1"
SEGMENT = re.compile(r"segment-(\d{6})\.jsonl")
MAX_REQUEST_BYTES = 64 << 10
MAX_WORKER_BYTES = 1 << 20
P7_POLICIES = frozenset(p7.P7_POLICIES)
SHA256 = re.compile(r"[0-9a-f]{64}")
ORACLE_GENERATOR_PATHS = (
    "cm_exprlib.py",
    "cmbench/comparative/arms.py",
    "cmbench/recognition/blif.py",
    "cmbench/recognition/features.py",
)


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def strict_json(payload: bytes, *, limit: int) -> Any:
    require(isinstance(payload, bytes) and 0 < len(payload) <= limit, "bounded JSON payload required")

    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "duplicate JSON key")
            value[key] = item
        return value

    def constant(_value):
        raise ValueError("nonfinite JSON")

    try:
        return json.loads(payload, object_pairs_hook=pairs, parse_constant=constant)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("invalid JSON payload") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _case_digest(case: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(case)).hexdigest()


def record_sha256(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def limits_record(limits: linux_supervisor.Limits) -> dict[str, Any]:
    limits.validate()
    return {
        "timeout_seconds": limits.timeout_seconds,
        "rss_stop_bytes": limits.rss_stop_bytes,
        "processes": limits.processes,
        "input_bytes": limits.input_bytes,
        "stdout_bytes": limits.stdout_bytes,
        "stderr_bytes": limits.stderr_bytes,
        "sample_seconds": limits.sample_seconds,
    }


def limits_from_record(record: Mapping[str, Any]) -> linux_supervisor.Limits:
    expected = {
        "timeout_seconds", "rss_stop_bytes", "processes", "input_bytes",
        "stdout_bytes", "stderr_bytes", "sample_seconds",
    }
    require(isinstance(record, Mapping) and set(record) == expected, "resource limit fields")
    value = linux_supervisor.Limits(**dict(record))
    value.validate()
    return value


def arm_configuration(policy_id: str, arm: str) -> dict[str, Any]:
    require(policy_id in P7_POLICIES and arm in p7.P7_POLICIES[policy_id][1], "unknown P7 arm configuration")
    if policy_id == "p7-ir":
        kind = "ordered_cm_ir" if arm.startswith("cm-ir-") else "flat_program"
        implementation: Any = p7.IR_ARMS[arm]
    else:
        implementation, kind = p7.RELATION_ARMS[arm]
    return {
        "schema": "cm-comparative-p7-arm-configuration/v1",
        "policy_id": policy_id,
        "arm": arm,
        "implementation": implementation,
        "artifact_kind": kind,
        "lifecycle": "fresh_process",
        "source_preparation_charged": True,
        "answer_cache": "none",
    }


def output_contract(policy_id: str, arm: str) -> dict[str, Any]:
    configuration = arm_configuration(policy_id, arm)
    return {
        "schema": "cm-comparative-p7-output-contract/v1",
        "task": p7.P7_POLICIES[policy_id][0],
        "artifact_kind": configuration["artifact_kind"],
        "output_scope": "full",
        "lifecycle": "fresh_process",
        "validation_in_timed_span": False,
    }


def build_plan(
    freeze: Mapping[str, Any],
    *,
    policy_id: str,
    roles: Sequence[str],
    blocks: int,
    worker_source_manifest_sha256: str,
    resource_limits: Mapping[str, Any],
    case_limit: int | None = None,
    profile: str = "functional",
    _validate: bool = True,
) -> dict[str, Any]:
    """Select an order-preserving bounded shard from the immutable P6 ledger."""
    validate_freeze(freeze)
    require(isinstance(worker_source_manifest_sha256, str) and SHA256.fullmatch(worker_source_manifest_sha256),
            "worker source manifest identity")
    frozen_limits = limits_record(limits_from_record(resource_limits))
    resource_profile_sha256 = record_sha256(frozen_limits)
    require(policy_id in P7_POLICIES, "only frozen P7 policies are executable")
    policies = {row["policy_id"]: row for row in freeze["schedule_policies"]}
    policy = policies[policy_id]
    task, bindings = p7.P7_POLICIES[policy_id]
    require(policy["task"] == task and policy["arms"] == list(bindings), "P7 binding changed")
    selected_roles = tuple(roles)
    require(
        selected_roles
        and len(set(selected_roles)) == len(selected_roles)
        and set(selected_roles).issubset(policy["eligible_roles"]),
        "invalid P7 roles",
    )
    require(type(blocks) is int and 1 <= blocks <= policy["maximum_blocks"], "invalid block bound")
    performance = profile == "performance"
    require(profile in {"functional", "performance"}, "invalid runner profile")
    cycle = 2 * len(policy["arms"])
    if performance:
        require(
            policy["minimum_blocks"] <= blocks <= policy["maximum_blocks"]
            and blocks % cycle == 0,
            "performance blocks must contain complete frozen counterbalance cycles",
        )
    require(case_limit is None or type(case_limit) is int and 1 <= case_limit <= 10_000, "invalid case limit")
    cases = {row["case_id"]: row for row in freeze["cases"]}
    eligible = {
        case_id for case_id, case in cases.items()
        if case["role"] in selected_roles and task in case["tasks"]
    }
    ordered: list[str] = []
    for row in policy["order_ledger"]:
        if row["case_id"] in eligible and row["case_id"] not in ordered:
            ordered.append(row["case_id"])
    if case_limit is not None:
        ordered = ordered[:case_limit]
    require(ordered, "P7 selection has no cases")
    selected = set(ordered)
    schedule_rows = [
        row for row in policy["order_ledger"]
        if row["case_id"] in selected and row["block"] < blocks
    ]
    require(len(schedule_rows) == len(ordered) * blocks, "frozen order-ledger coverage mismatch")
    cells: list[dict[str, Any]] = []
    seen_case_blocks: set[tuple[str, int]] = set()
    case_positions = {case_id: position for position, case_id in enumerate(ordered)}
    for schedule_position, row in enumerate(schedule_rows):
        case = cases[row["case_id"]]
        key = (row["case_id"], row["block"])
        require(key not in seen_case_blocks, "duplicate frozen case/block")
        seen_case_blocks.add(key)
        require(
            row["policy_id"] == policy_id
            and row["task"] == task
            and row["cluster_id"] == case["cluster_id"]
            and row["arm_order"] and set(row["arm_order"]) == set(policy["arms"]),
            "frozen order row changed",
        )
        for arm_position, arm in enumerate(row["arm_order"]):
            configuration = arm_configuration(policy_id, arm)
            contract = output_contract(policy_id, arm)
            core = {
                "freeze_sha256": freeze["freeze_sha256"],
                "worker_source_manifest_sha256": worker_source_manifest_sha256,
                "policy_id": policy_id,
                "task": task,
                "case_id": row["case_id"],
                "cluster_id": case["cluster_id"],
                "role": case["role"],
                "case_sha256": _case_digest(case),
                "source_path": case["source"]["path"],
                "source_sha256": case["source"]["sha256"],
                "source_member_sha256": case["source"].get("member_sha256"),
                "configuration_sha256": record_sha256(configuration),
                "output_contract_sha256": record_sha256(contract),
                "lifecycle": "fresh_process",
                "affinity_class": "one-admitted-cpu",
                "resource_limit_profile_sha256": resource_profile_sha256,
                "block": row["block"],
                "case_position": case_positions[row["case_id"]],
                "schedule_position": schedule_position,
                "arm": arm,
                "arm_position": arm_position,
                "order_sha256": row["order_sha256"],
                "conditional_extension": row["conditional_extension"],
            }
            cells.append({**core, "cell_id": hashlib.sha256(canonical_bytes(core)).hexdigest()})
    core_plan = {
        "schema": PLAN_SCHEMA,
        "freeze_sha256": freeze["freeze_sha256"],
        "policy_id": policy_id,
        "task": task,
        "roles": list(selected_roles),
        "profile": profile,
        "performance_measurement": performance,
        "blocks": blocks,
        "worker_source_manifest_sha256": worker_source_manifest_sha256,
        "resource_limits": frozen_limits,
        "resource_limit_profile_sha256": resource_profile_sha256,
        "arms": list(policy["arms"]),
        "case_ids": ordered,
        "cells": cells,
    }
    plan = {**core_plan, "plan_sha256": hashlib.sha256(canonical_bytes(core_plan)).hexdigest()}
    if _validate:
        validate_plan(plan, freeze)
    return plan


def validate_plan(plan: Mapping[str, Any], freeze: Mapping[str, Any]) -> None:
    expected = {
        "schema", "freeze_sha256", "policy_id", "task", "roles", "profile",
        "performance_measurement", "blocks", "worker_source_manifest_sha256",
        "resource_limits", "resource_limit_profile_sha256", "arms", "case_ids",
        "cells", "plan_sha256",
    }
    require(isinstance(plan, Mapping) and set(plan) == expected and plan["schema"] == PLAN_SCHEMA, "plan fields")
    core = {key: plan[key] for key in expected if key != "plan_sha256"}
    require(plan["plan_sha256"] == hashlib.sha256(canonical_bytes(core)).hexdigest(), "plan identity")
    # Avoid recursive reconstruction; validate every frozen identity directly.
    require(plan["freeze_sha256"] == freeze["freeze_sha256"], "freeze identity")
    require(isinstance(plan["worker_source_manifest_sha256"], str)
            and SHA256.fullmatch(plan["worker_source_manifest_sha256"]), "worker source identity")
    limits = limits_record(limits_from_record(plan["resource_limits"]))
    require(plan["resource_limit_profile_sha256"] == record_sha256(limits), "resource profile identity")
    require(plan["policy_id"] in P7_POLICIES and plan["task"] == p7.P7_POLICIES[plan["policy_id"]][0], "plan policy")
    require(plan["performance_measurement"] is (plan["profile"] == "performance"), "profile flag")
    ids = []
    for cell in plan["cells"]:
        require(isinstance(cell, Mapping) and set(cell) == {
            "freeze_sha256", "worker_source_manifest_sha256", "policy_id", "task", "case_id",
            "cluster_id", "role", "case_sha256", "source_path", "source_sha256", "source_member_sha256",
            "configuration_sha256", "output_contract_sha256", "lifecycle", "affinity_class",
            "resource_limit_profile_sha256", "block", "case_position", "schedule_position",
            "arm", "arm_position", "order_sha256", "conditional_extension", "cell_id",
        }, "cell fields")
        core_cell = {key: cell[key] for key in cell if key != "cell_id"}
        require(cell["cell_id"] == hashlib.sha256(canonical_bytes(core_cell)).hexdigest(), "cell identity")
        require(cell["case_id"] in plan["case_ids"] and cell["arm"] in plan["arms"], "cell membership")
        ids.append(cell["cell_id"])
    require(ids and len(ids) == len(set(ids)), "cell cardinality")
    expected_plan = build_plan(
        freeze,
        policy_id=plan["policy_id"],
        roles=plan["roles"],
        blocks=plan["blocks"],
        worker_source_manifest_sha256=plan["worker_source_manifest_sha256"],
        resource_limits=plan["resource_limits"],
        case_limit=len(plan["case_ids"]),
        profile=plan["profile"],
        _validate=False,
    )
    require(dict(plan) == expected_plan, "plan differs from frozen order ledger")


def oracle_package(
    plan: Mapping[str, Any],
    freeze: Mapping[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    """Build source-bound independent scalar/BLIF oracle records."""
    generator_files = []
    for name in ORACLE_GENERATOR_PATHS:
        path = (project_root / name).resolve()
        require(path.is_relative_to(project_root.resolve()) and path.is_file() and not path.is_symlink(),
                "oracle generator source unavailable")
        generator_files.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    generator_sha256 = record_sha256({"files": generator_files})
    cases = {row["case_id"]: row for row in freeze["cases"]}
    output = []
    for case_id in plan["case_ids"]:
        case = cases[case_id]
        expression, variables = p7.load_case_expression(case, project_root)
        relation = scalar_relation(expression, variables, {})
        core = {
            "schema": ORACLE_RECORD_SCHEMA,
            "case_id": case_id,
            "case_sha256": _case_digest(case),
            "source_path": case["source"]["path"],
            "source_sha256": case["source"]["sha256"],
            "source_member_sha256": case["source"].get("member_sha256"),
            "root": case["strata"].get("root"),
            "support": case["strata"].get("support"),
            "width": len(variables),
            "encoding": "little_endian_assignment_bits/v1",
            "result_sha256": semantic_sha256(relation, len(variables)),
            "generator_source_sha256": generator_sha256,
        }
        output.append({**core, "record_sha256": record_sha256(core)})
    core_package = {
        "schema": ORACLE_PACKAGE_SCHEMA,
        "freeze_sha256": plan["freeze_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "generator_files": generator_files,
        "generator_source_sha256": generator_sha256,
        "calculated_outside_cell_processes": True,
        "cases": output,
    }
    return {**core_package, "oracle_package_sha256": record_sha256(core_package)}


def validate_oracle_package(
    package: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    expected = {
        "schema", "freeze_sha256", "plan_sha256", "generator_files",
        "generator_source_sha256", "calculated_outside_cell_processes", "cases",
        "oracle_package_sha256",
    }
    require(isinstance(package, Mapping) and set(package) == expected
            and package["schema"] == ORACLE_PACKAGE_SCHEMA, "oracle package fields")
    core = {key: package[key] for key in expected if key != "oracle_package_sha256"}
    require(package["oracle_package_sha256"] == record_sha256(core), "oracle package identity")
    require(package["freeze_sha256"] == plan["freeze_sha256"]
            and package["plan_sha256"] == plan["plan_sha256"], "oracle plan identity")
    require(package["calculated_outside_cell_processes"] is True, "oracle separation")
    require(isinstance(package["generator_source_sha256"], str)
            and SHA256.fullmatch(package["generator_source_sha256"]), "oracle generator identity")
    rows: dict[str, dict[str, Any]] = {}
    expected_fields = {
        "schema", "case_id", "case_sha256", "source_path", "source_sha256",
        "source_member_sha256", "root", "support", "width", "encoding",
        "result_sha256", "generator_source_sha256", "record_sha256",
    }
    for value in package["cases"]:
        require(isinstance(value, Mapping) and set(value) == expected_fields
                and value["schema"] == ORACLE_RECORD_SCHEMA, "oracle record fields")
        core_record = {key: value[key] for key in expected_fields if key != "record_sha256"}
        require(value["record_sha256"] == record_sha256(core_record), "oracle record identity")
        require(value["generator_source_sha256"] == package["generator_source_sha256"],
                "oracle generator mismatch")
        require(isinstance(value["result_sha256"], str) and SHA256.fullmatch(value["result_sha256"]),
                "oracle result identity")
        require(value["case_id"] not in rows, "duplicate oracle case")
        rows[value["case_id"]] = dict(value)
    require(set(rows) == set(plan["case_ids"]), "oracle case coverage")
    return rows


def request_for(plan: Mapping[str, Any], cell: Mapping[str, Any], oracle: Mapping[str, Any]) -> dict[str, Any]:
    require(oracle.get("case_id") == cell["case_id"], "oracle/cell case mismatch")
    request = {
        "schema": REQUEST_SCHEMA,
        "freeze_sha256": plan["freeze_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "worker_source_manifest_sha256": plan["worker_source_manifest_sha256"],
        "cell": dict(cell),
        "oracle_record_sha256": oracle["record_sha256"],
        "oracle_result_sha256": oracle["result_sha256"],
        "performance_measurement": plan["performance_measurement"],
    }
    require(len(canonical_bytes(request)) <= MAX_REQUEST_BYTES, "worker request bound")
    return request


def _pin_worker() -> list[int]:
    if not hasattr(os, "sched_getaffinity") or not hasattr(os, "sched_setaffinity"):
        return []
    available = sorted(os.sched_getaffinity(0))
    require(available, "empty worker affinity")
    os.sched_setaffinity(0, {available[0]})
    return sorted(os.sched_getaffinity(0))


def execute_worker(
    request: Mapping[str, Any],
    freeze: Mapping[str, Any],
    project_root: Path,
    *,
    clock=time.perf_counter_ns,
) -> dict[str, Any]:
    validate_freeze(freeze)
    expected = {
        "schema", "freeze_sha256", "plan_sha256", "worker_source_manifest_sha256",
        "cell", "oracle_record_sha256", "oracle_result_sha256", "performance_measurement",
    }
    require(isinstance(request, Mapping) and set(request) == expected and request["schema"] == REQUEST_SCHEMA, "request fields")
    require(request["freeze_sha256"] == freeze["freeze_sha256"], "request freeze identity")
    cell = request["cell"]
    require(isinstance(cell, Mapping) and isinstance(cell.get("cell_id"), str), "request cell")
    require(request["worker_source_manifest_sha256"] == cell.get("worker_source_manifest_sha256"),
            "request worker source identity")
    core_cell = {key: cell[key] for key in cell if key != "cell_id"}
    require(cell["cell_id"] == record_sha256(core_cell), "request cell identity")
    require(cell.get("freeze_sha256") == freeze["freeze_sha256"], "request cell freeze")
    require(cell.get("policy_id") in P7_POLICIES, "request policy")
    task, bindings = p7.P7_POLICIES[cell["policy_id"]]
    require(cell.get("task") == task and cell.get("arm") in bindings, "request task/arm")
    require(cell.get("configuration_sha256") == record_sha256(arm_configuration(cell["policy_id"], cell["arm"])),
            "request arm configuration")
    require(cell.get("output_contract_sha256") == record_sha256(output_contract(cell["policy_id"], cell["arm"])),
            "request output contract")
    require(cell.get("lifecycle") == "fresh_process" and cell.get("affinity_class") == "one-admitted-cpu",
            "request execution class")
    cases = [row for row in freeze["cases"] if row["case_id"] == cell["case_id"]]
    require(len(cases) == 1 and task in cases[0]["tasks"], "request case")
    require(cell.get("case_sha256") == _case_digest(cases[0])
            and cell.get("source_path") == cases[0]["source"]["path"]
            and cell.get("source_sha256") == cases[0]["source"]["sha256"]
            and cell.get("source_member_sha256") == cases[0]["source"].get("member_sha256"),
            "request source identity")
    require(isinstance(request["oracle_record_sha256"], str) and SHA256.fullmatch(request["oracle_record_sha256"])
            and isinstance(request["oracle_result_sha256"], str) and SHA256.fullmatch(request["oracle_result_sha256"]),
            "request oracle identity")
    affinity = _pin_worker()
    if task == "ir_preparation":
        result = p7.execute_ir_source_cell(cases[0], project_root, cell["arm"], clock=clock)
    else:
        started = clock()
        expression, variables = p7.load_case_expression(cases[0], project_root)
        implementation, _artifact = p7.RELATION_ARMS[cell["arm"]]
        result_row = execute_arm(
            expr=expression,
            contract=p7._relation_contract(
                cell["arm"], variables, request["oracle_result_sha256"], lifecycle="fresh_process",
            ),
            case_id=cell["case_id"],
            arm=implementation,
            smoke_bound=16,
            clock=clock,
        )
        finished = clock()
        require(type(started) is int and type(finished) is int and 0 <= started < finished,
                "invalid P7 relation source-cell clock")
        result = {
            "arm": cell["arm"],
            "artifact_kind": result_row["artifact"]["kind"],
            "artifact_sha256": result_row["artifact"]["sha256"],
            "semantic_sha256": result_row["artifact"]["sha256"],
            "timings_ns": {
                **result_row["timings_ns"],
                "backend_task_total_wall_ns": result_row["timings_ns"]["task_total_ns"],
                "task_total_wall_ns": finished - started,
            },
            "validation_in_timed_span": False,
            "source_preparation_in_timed_span": True,
        }
    return {
        "schema": WORKER_SCHEMA,
        "cell_id": cell["cell_id"],
        "policy_id": cell["policy_id"],
        "task": task,
        "case_id": cell["case_id"],
        "arm": cell["arm"],
        "status": "ok",
        "artifact_kind": result["artifact_kind"],
        "artifact_sha256": result["artifact_sha256"],
        "semantic_sha256": result["semantic_sha256"],
        "timings_ns": result["timings_ns"],
        "validation_in_timed_span": False,
        "source_preparation_in_timed_span": result["source_preparation_in_timed_span"],
        "performance_measurement": request["performance_measurement"],
        "environment": {"pid": os.getpid(), "affinity": affinity},
    }


def validate_worker(
    payload: bytes,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    result = strict_json(payload, limit=MAX_WORKER_BYTES)
    expected = {
        "schema", "cell_id", "policy_id", "task", "case_id", "arm", "status",
        "artifact_kind", "artifact_sha256", "semantic_sha256", "timings_ns",
        "validation_in_timed_span", "source_preparation_in_timed_span",
        "performance_measurement", "environment",
    }
    require(isinstance(result, Mapping) and set(result) == expected and result["schema"] == WORKER_SCHEMA, "worker fields")
    cell = request["cell"]
    for key in ("cell_id", "policy_id", "task", "case_id", "arm"):
        require(result[key] == cell[key], "worker identity mismatch")
    require(result["performance_measurement"] is request["performance_measurement"], "worker profile mismatch")
    require(result["status"] == "ok" and result["validation_in_timed_span"] is False
            and result["source_preparation_in_timed_span"] is True, "worker status")
    duration = result["timings_ns"].get("task_total_wall_ns") if isinstance(result["timings_ns"], Mapping) else None
    require(type(duration) is int and duration > 0, "worker duration")
    for key in ("artifact_sha256", "semantic_sha256"):
        value = result[key]
        require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), "worker digest")
    return dict(result)


def execute_cell(
    *,
    plan: Mapping[str, Any],
    cell: Mapping[str, Any],
    oracle: Mapping[str, Any],
    python: Path,
    worker_program: Path,
    project_root: Path,
    freeze_path: Path,
    limits: linux_supervisor.Limits,
    supervise: Callable[..., Any] = linux_supervisor.run,
) -> tuple[dict[str, Any], dict[str, Any]]:
    require(record_sha256(limits_record(limits)) == cell["resource_limit_profile_sha256"],
            "supervisor limits differ from frozen cell")
    request = request_for(plan, cell, oracle)
    request_bytes = canonical_bytes(request)
    request_sha = hashlib.sha256(request_bytes).hexdigest()
    supervised = supervise(
        [str(python.resolve()), "-B", str(worker_program.resolve()), "worker",
         "--project-root", str(project_root.resolve()), "--freeze", str(freeze_path.resolve())],
        input=request_bytes,
        cwd=project_root,
        limits=limits,
    )
    status = supervised.status
    reason = supervised.reason
    worker = None
    if status == "ok":
        try:
            worker = validate_worker(supervised.stdout, request)
        except ValueError as exc:
            status, reason = "error", "invalid_worker_output:" + str(exc)
        else:
            if worker["semantic_sha256"] != oracle["result_sha256"]:
                status, reason = "mismatch", "outside_span_scalar_oracle_mismatch"
    resources = dict(supervised.resources)
    if resources.get("cleanup_verified") is not True or resources.get("streams_closed") is not True:
        status, reason = "error", "cleanup_or_streams_unverified"
    require(status in RESULT_STATUSES, "unknown supervisor result")
    result = {
        "status": status,
        "reason": reason,
        "worker": worker,
        "timings_ns": {
            "task_total_wall_ns": worker["timings_ns"]["task_total_wall_ns"] if worker else None,
            "fresh_process_controller_wall_ns": supervised.wall_ns,
        },
        "process_tree_peak_rss_bytes": resources.get("peak_sampled_tree_rss_bytes"),
        "resources": resources,
        "returncode": supervised.returncode,
        "stdout_sha256": hashlib.sha256(supervised.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(supervised.stderr).hexdigest(),
        "outside_span_validation": True,
        "performance_measurement": plan["performance_measurement"],
    }
    return result, {"request": request, "request_sha256": request_sha}


def new_segment(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    indices = []
    for path in directory.iterdir():
        match = SEGMENT.fullmatch(path.name)
        require(match is not None and path.is_file(), "unexpected ledger segment entry")
        indices.append(int(match.group(1)))
    expected = list(range(len(indices)))
    require(sorted(indices) == expected, "ledger segments are not contiguous")
    path = directory / f"segment-{len(indices):06}.jsonl"
    path.touch(exist_ok=False)
    return path


def read_segments(directory: Path) -> dict[str, Any]:
    require(directory.is_dir(), "ledger segment directory missing")
    paths = sorted(directory.iterdir())
    require(paths and all(SEGMENT.fullmatch(path.name) and path.is_file() for path in paths), "invalid ledger segments")
    histories: dict[str, list[dict[str, Any]]] = {}
    partial_tails = []
    for path_position, path in enumerate(paths):
        raw = path.read_bytes()
        lines = raw.splitlines()
        for index, line in enumerate(lines):
            try:
                row = strict_json(line, limit=MAX_WORKER_BYTES)
            except ValueError:
                require(
                    path_position == len(paths) - 1
                    and index == len(lines) - 1
                    and not raw.endswith(b"\n"),
                    "corrupt complete ledger record",
                )
                partial_tails.append(path.name)
                break
            require(isinstance(row, Mapping) and isinstance(row.get("cell_id"), str), "ledger row")
            require(type(row.get("attempt")) is int and row["attempt"] >= 1, "ledger attempt")
            require(row.get("status") in RESULT_STATUSES | {"running"}, "ledger status")
            history = histories.setdefault(row["cell_id"], [])
            if not history:
                require(row["status"] == "running" and row["attempt"] == 1, "first ledger transition")
            else:
                prior = history[-1]
                if prior["status"] == "running":
                    require(row["status"] != "running" and row["attempt"] == prior["attempt"], "terminal ledger transition")
                    require(row.get("request_sha256") == prior.get("request_sha256"), "request identity changed")
                else:
                    require(
                        prior.get("reason") == "interrupted_before_terminal_evidence"
                        and row["status"] == "running"
                        and row["attempt"] == prior["attempt"] + 1,
                        "unexpected cell retry",
                    )
            history.append(dict(row))
    latest = {cell: rows[-1] for cell, rows in histories.items()}
    return {"histories": histories, "latest": latest, "partial_tail_segments": partial_tails}


def recover_interrupted(state: Mapping[str, Any], segment: Path) -> list[str]:
    recovered = []
    for cell_id, row in sorted(state["latest"].items()):
        if row["status"] == "running":
            append_record(segment, {
                "cell_id": cell_id,
                "request_sha256": row["request_sha256"],
                "attempt": row["attempt"],
                "status": "error",
                "reason": "interrupted_before_terminal_evidence",
            })
            recovered.append(cell_id)
    return recovered


def reconcile(plan: Mapping[str, Any], state: Mapping[str, Any]) -> dict[str, Any]:
    planned = {row["cell_id"] for row in plan["cells"]}
    latest = state["latest"]
    observed = set(latest)
    statuses: dict[str, int] = {}
    for row in latest.values():
        statuses[row["status"]] = statuses.get(row["status"], 0) + 1
    return {
        "planned_cells": len(planned),
        "observed_cells": len(observed),
        "missing_cells": sorted(planned - observed),
        "unexpected_cells": sorted(observed - planned),
        "running_cells": sorted(cell for cell, row in latest.items() if row["status"] == "running"),
        "partial_tail_segments": state["partial_tail_segments"],
        "statuses": dict(sorted(statuses.items())),
        "complete": planned == observed and not any(row["status"] == "running" for row in latest.values()),
    }


def validate_state(
    plan: Mapping[str, Any],
    state: Mapping[str, Any],
    oracle_package_record: Mapping[str, Any],
) -> None:
    oracles = validate_oracle_package(oracle_package_record, plan)
    cells = {row["cell_id"]: row for row in plan["cells"]}
    require(set(state["latest"]).issubset(cells), "ledger contains unexpected cells")
    require(set(oracles) == set(plan["case_ids"]), "oracle case coverage")
    for cell_id, history in state["histories"].items():
        cell = cells[cell_id]
        expected_request = request_for(plan, cell, oracles[cell["case_id"]])
        expected_sha = hashlib.sha256(canonical_bytes(expected_request)).hexdigest()
        for row in history:
            require(row.get("request_sha256") == expected_sha, "ledger request identity")
            if row["status"] == "running" or row.get("reason") == "interrupted_before_terminal_evidence":
                continue
            result = row.get("result")
            require(isinstance(result, Mapping) and result.get("status") == row["status"], "terminal result identity")
            resources = result.get("resources")
            require(
                isinstance(resources, Mapping)
                and resources.get("cleanup_verified") is True
                and resources.get("streams_closed") is True,
                "terminal cleanup evidence",
            )
            require(result.get("outside_span_validation") is True, "outside-span validation evidence")
            require(result.get("performance_measurement") is plan["performance_measurement"], "performance flag")
            if row["status"] == "ok":
                worker = result.get("worker")
                require(
                    isinstance(worker, Mapping)
                    and worker.get("cell_id") == cell_id
                    and worker.get("semantic_sha256") == oracles[cell["case_id"]]["result_sha256"],
                    "successful cell semantic identity",
                )
                timings = result.get("timings_ns")
                require(
                    isinstance(timings, Mapping)
                    and type(timings.get("task_total_wall_ns")) is int
                    and timings["task_total_wall_ns"] > 0
                    and type(timings.get("fresh_process_controller_wall_ns")) is int
                    and timings["fresh_process_controller_wall_ns"] > 0,
                    "successful cell timing evidence",
                )
                require(
                    type(result.get("process_tree_peak_rss_bytes")) is int
                    and result["process_tree_peak_rss_bytes"] > 0
                    and resources.get("whole_tree_rss_measured") is True,
                    "successful cell RSS evidence",
                )


def source_identity(project_root: Path, freeze: Mapping[str, Any], code_paths: Sequence[str]) -> dict[str, Any]:
    verify = verify_sources(freeze, project_root)
    require(verify["verified"] is True, "frozen corpus source identity failed")
    names = set(code_paths)
    names.update(case["source"]["path"] for case in freeze["cases"])
    rows = []
    for name in sorted(names):
        path = (project_root / name).resolve()
        require(path.is_relative_to(project_root) and path.is_file() and not path.is_symlink(), "source identity path")
        rows.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {"schema": SOURCE_SCHEMA, "freeze_sha256": freeze["freeze_sha256"], "files": rows}


def verify_cell_sources(
    project_root: Path,
    cell: Mapping[str, Any],
    code_paths: Sequence[str],
    source_before: Mapping[str, Any],
) -> None:
    """Recheck executable code plus the active case source between cells."""
    project = project_root.resolve()
    rows = source_before.get("files") if isinstance(source_before, Mapping) else None
    require(isinstance(rows, list), "source-before files")
    baseline = {row.get("path"): row for row in rows if isinstance(row, Mapping)}
    require(len(baseline) == len(rows), "source-before path identity")
    names = set(code_paths)
    names.add(cell["source_path"])
    for name in names:
        path = (project / name).resolve()
        require(path.is_relative_to(project) and path.is_file() and not path.is_symlink(),
                "cell source identity path")
        expected = baseline.get(name)
        require(isinstance(expected, Mapping), "cell source missing from baseline")
        require(path.stat().st_size == expected.get("bytes") and sha256(path) == expected.get("sha256"),
                "cell source changed")
    require(baseline[cell["source_path"]]["sha256"] == cell["source_sha256"],
            "cell source differs from frozen case")


def environment_identity() -> dict[str, Any]:
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else []
    return {
        "schema": ENVIRONMENT_SCHEMA,
        "python": sys.version,
        "executable": str(Path(sys.executable).resolve()),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "logical_cpus": os.cpu_count(),
        "affinity": affinity,
        "linux_supervisor_available": linux_supervisor.platform_supported(),
    }


def summary(
    plan: Mapping[str, Any],
    state: Mapping[str, Any],
    oracle_package_record: Mapping[str, Any],
    *,
    source_unchanged: bool,
) -> dict[str, Any]:
    validate_state(plan, state, oracle_package_record)
    reconciliation = reconcile(plan, state)
    ok = reconciliation["complete"] and reconciliation["statuses"] == {"ok": len(plan["cells"])}
    return {
        "schema": SUMMARY_SCHEMA,
        "freeze_sha256": plan["freeze_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "policy_id": plan["policy_id"],
        "profile": plan["profile"],
        "performance_measurement": plan["performance_measurement"],
        "performance_claim_permitted": bool(plan["performance_measurement"] and ok and source_unchanged),
        "source_unchanged": source_unchanged,
        "reconciliation": reconciliation,
        "status": "passed" if ok and source_unchanged else "failed",
    }
