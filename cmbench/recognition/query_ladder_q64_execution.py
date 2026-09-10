"""Append-only execution support for the frozen 72-case q64 decision surface.

This module executes exact backends only.  It never fits a model, consumes a
prospective case, or changes production routing.  Every decision-bearing cell
is launched by the CLI in a fresh process; process startup is recorded but is
outside the already-frozen ``accounted_total_ns`` boundary.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any

from cmbench.comparative import architecture_comparison_campaign as campaign
from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.gf2_native_slots import load_native_slot_library
from cmbench.comparative.gf2_wide_repeated_queries import (
    semantic_document,
    semantic_row,
)
from cmbench.recognition import query_ladder_learning_freeze as parent


ROOT = Path(__file__).resolve().parents[2]
PARENT_RELATIVE = (
    "docs/recognition/runs/"
    "query-ladder-source-blind-learning-freeze-20260904-001/FREEZE.json"
)
PARENT_FILE_SHA256 = "3cf5c2672e01aae6130282f2ea1a65de32746597a59689605a2d913a675a0692"
PARENT_CANONICAL_SHA256 = "d31f1f19d43232ece53b24c6202caec7f82d4a57d869d461e74fe75db5ea378e"
TASK_SHA256 = "64571e31193d7c4e0298ba17c2921311607d4f5ca20f7bd14aced260a29da59d"
CASE_SET_SHA256 = "9a6e978db02508d7eae3f478283140ae7bd471e10307ff7d53644c0bb63ef010"
LABEL_POLICY_SHA256 = "1251bd0e8aac0f6565f3a46e759ae7bfd482b823737472b5fdcb9d27f00f8c3a"
SOURCE_CHECKPOINT = "c4cfccd846771a4f72a1b429797b97cdb1ed3d83"

BASELINE_SCHEMA = "crse-query-ladder-q64-baseline-closure/v1"
ORACLE_SCHEMA = "crse-query-ladder-q64-independent-oracles/v1"
CHILD_SCHEMA = "crse-query-ladder-q64-child-execution-freeze/v1"
CHILD_VERIFICATION_SCHEMA = "crse-query-ladder-q64-child-freeze-verification/v1"
HOST_PREFLIGHT_SCHEMA = "crse-query-ladder-q64-host-preflight/v1"
RAW_SCHEMA = "crse-query-ladder-q64-timed-cell/v1"
HOST_RESULT_SCHEMA = "crse-query-ladder-q64-host-result/v1"
HOST_VERIFICATION_SCHEMA = "crse-query-ladder-q64-host-independent-verification/v1"
SURFACE_VERIFICATION_SCHEMA = "crse-query-ladder-q64-surface-independent-verification/v1"
BLOCKS = 16
QUERY_COUNT = 64
CELL_TIMEOUT_SECONDS = 120.0
EXPECTED_CELLS = 72 * len(parent.EXACT_ARMS) * BLOCKS

# These are the implementation/build sources for the frozen arms.  They were
# all present at SOURCE_CHECKPOINT and have no checkpoint-to-current diff.
ARM_SOURCE_PATHS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cm_normalize.py",
    "cmbench/backends/native_restriction.py",
    "cmbench/comparative/architecture_comparison_campaign.py",
    "cmbench/comparative/architecture_refresh_harness.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/gf2_native_slots.py",
    "cmbench/comparative/gf2_restricted_evaluators.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "native/cm_fused_slots/CMakeLists.txt",
    "native/cm_fused_slots/build_msvc.cmd",
    "native/cm_fused_slots/fused_slot_executor.c",
    "scripts/build_cm_fused_slots.py",
)
EXECUTION_SOURCE_PATHS = (
    "cmbench/recognition/query_ladder_learning_freeze.py",
    "cmbench/recognition/query_ladder_decision_surface.py",
    "cmbench/recognition/query_ladder_q64_execution.py",
    "scripts/cm_query_ladder_q64_execution.py",
    "scripts/crse_verify_query_ladder_q64_execution.py",
)


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def file_identity(root: Path, relative: str) -> dict[str, Any]:
    path = (root / relative).resolve()
    _require(path.is_relative_to(root) and path.is_file(), f"missing bound file: {relative}")
    return {"path": relative, "bytes": path.stat().st_size, "sha256": file_sha256(path)}


def write_json_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        stream.write("\n")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_verified_parent(root: Path = ROOT) -> dict[str, Any]:
    path = root / PARENT_RELATIVE
    _require(file_sha256(path) == PARENT_FILE_SHA256, "parent FREEZE.json byte identity")
    frozen = load_json(path)
    parent.verify_freeze(frozen, root)
    _require(frozen["freeze_sha256"] == PARENT_CANONICAL_SHA256, "parent canonical identity")
    _require(parent.digest(frozen["exact_task_contract"]) == TASK_SHA256, "task identity")
    _require(frozen["cohort"]["case_set_sha256"] == CASE_SET_SHA256, "case-set identity")
    _require(parent.digest(frozen["label_policy"]) == LABEL_POLICY_SHA256, "label-policy identity")
    _require(frozen["source_checkpoint"] == SOURCE_CHECKPOINT, "source checkpoint")
    return frozen


def arm_orders() -> list[list[str]]:
    arms = list(parent.EXACT_ARMS)
    forward = [arms[index:] + arms[:index] for index in range(len(arms))]
    reverse = list(reversed(arms))
    backward = [reverse[index:] + reverse[:index] for index in range(len(reverse))]
    orders = forward + backward
    _require(len(orders) == BLOCKS and len({tuple(row) for row in orders}) == BLOCKS,
             "counterbalanced arm orders")
    counts = {
        arm: [sum(order[position] == arm for order in orders) for position in range(len(arms))]
        for arm in arms
    }
    _require(all(values == [2] * len(arms) for values in counts.values()),
             "each arm must occupy each position twice")
    return orders


def expected_schedule(frozen: Mapping[str, Any]):
    case_ids = [row["case_id"] for row in frozen["cohort"]["cases"]]
    for block, order in enumerate(arm_orders()):
        for case_position, case_id in enumerate(case_ids):
            for arm_position, arm in enumerate(order):
                yield {
                    "block": block,
                    "case_position": case_position,
                    "case_id": case_id,
                    "arm_position": arm_position,
                    "arm": arm,
                    "arm_order": list(order),
                    "query_count": QUERY_COUNT,
                }


def _git_bytes(root: Path, checkpoint: str, relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{checkpoint}:{relative}"], cwd=root,
        check=True, capture_output=True,
    )
    return completed.stdout


def build_baseline_closure(root: Path = ROOT) -> dict[str, Any]:
    frozen = load_verified_parent(root)
    sources = []
    changed = []
    for relative in ARM_SOURCE_PATHS:
        current = file_identity(root, relative)
        checkpoint = _git_bytes(root, SOURCE_CHECKPOINT, relative)
        checkpoint_sha = hashlib.sha256(checkpoint).hexdigest()
        diff = subprocess.run(
            ["git", "diff", "--quiet", SOURCE_CHECKPOINT, "--", relative], cwd=root,
            check=False,
        )
        identical = diff.returncode == 0
        sources.append({
            **current,
            "checkpoint_git_show_sha256": checkpoint_sha,
            "git_content_identical_to_embedded_checkpoint": identical,
            "checkout_bytes_identical_to_git_show": checkpoint_sha == current["sha256"],
            "checkout_byte_difference_interpretation": (
                "none" if checkpoint_sha == current["sha256"]
                else "platform_checkout_line_ending_normalization_only"
            ),
        })
        if not identical:
            changed.append(relative)
    _require(not changed, "material frozen-arm source drift: " + ",".join(changed))
    core = {
        "schema": BASELINE_SCHEMA,
        "status": "verified_complete",
        "embedded_source_checkpoint": SOURCE_CHECKPOINT,
        "current_git_head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip(),
        "parent_freeze_file_sha256": PARENT_FILE_SHA256,
        "task_contract_sha256": TASK_SHA256,
        "case_set_sha256": CASE_SET_SHA256,
        "arms": list(frozen["exact_task_contract"]["arms"]),
        "arm_sources": sources,
        "post_freeze_inventory": [
            {
                "path": "cmbench/comparative/h2_h3_profile_gate.py",
                "disposition": "profiling instrumentation; reuses current exact operations; no new q64 arm",
            },
            {
                "path": "cmbench/comparative/h6_fresh_process_memory_gate.py",
                "disposition": "memory-only lanes; repeated-restriction lane is a subset of frozen arms",
            },
            {
                "path": "cmbench/comparative/h6_representation_estimator_candidate.py",
                "disposition": "offline representation estimator; not an exact execution arm",
            },
            {
                "path": "cmbench/comparative/independent_active_workflow_gate.py",
                "disposition": "video-truth layout task; not task-identical q64 restriction",
            },
            {
                "path": "cmbench/comparative/hardware_behavior_corpus.py",
                "disposition": "hardware revision task; not task-identical q64 restriction",
            },
        ],
        "qualifying_prior_evidence_search": {
            "identity_search_performed": True,
            "qualifying_exact_72_case_two_physical_host_package_found": False,
            "earlier_54_case_q1_q4_q16_q64_campaign_reused": False,
        },
        "all_relevant_exact_baselines_included": True,
        "timings_opened": False,
        "prospective_cases_consumed": 0,
    }
    return {**core, "closure_sha256": digest(core)}


def _eval_full_truth(document: Mapping[str, Any], n_vars: int) -> int:
    nodes = document["nodes"]
    root = document["root"]
    result = 0
    for assignment in range(1 << n_vars):
        values: list[int] = []
        for node in nodes:
            op = node["op"]
            if op == "var":
                value = (assignment >> (n_vars - 1 - node["i"])) & 1
            elif op == "not":
                value = 1 - values[node["a"]]
            else:
                left, right = values[node["a"]], values[node["b"]]
                if op == "and": value = left & right
                elif op == "or": value = left | right
                elif op == "xor": value = left ^ right
                elif op == "imp": value = (1 - left) | right
                elif op == "eqv": value = 1 - (left ^ right)
                else: raise ValueError(f"unknown oracle op: {op}")
            values.append(value)
        result |= values[root] << assignment
    return result


def _restrict_full_truth(
    bits: int, n_vars: int, fixed: Mapping[str, int], remaining: Sequence[str]
) -> int:
    remaining_indices = tuple(int(name[1:]) for name in remaining)
    fixed_indices = {int(name[1:]): value for name, value in fixed.items()}
    _require(set(remaining_indices).isdisjoint(fixed_indices), "oracle restriction overlap")
    _require(set(remaining_indices) | set(fixed_indices) == set(range(n_vars)),
             "oracle restriction partition")
    reduced = 0
    positions = {index: position for position, index in enumerate(remaining_indices)}
    for residual in range(1 << len(remaining_indices)):
        original = 0
        for index in range(n_vars):
            value = fixed_indices[index] if index in fixed_indices else (
                residual >> (len(remaining_indices) - 1 - positions[index])
            ) & 1
            original = (original << 1) | value
        reduced |= ((bits >> original) & 1) << residual
    return reduced


def build_oracles(frozen: Mapping[str, Any]) -> dict[str, Any]:
    rows = {}
    for case in frozen["cohort"]["cases"]:
        full = _eval_full_truth(case["expression_v2"], case["n_vars"])
        semantic_rows = []
        for query in case["query_trace"]:
            fixed = {item["variable"]: item["value"] for item in query["fixed"]}
            remaining = tuple(query["remaining_order"])
            reduced = _restrict_full_truth(full, case["n_vars"], fixed, remaining)
            semantic_rows.append(semantic_row(query, reduced, case["n_vars"]))
        document = semantic_document(case["case_id"], semantic_rows)
        byte_count = max(1, ((1 << case["n_vars"]) + 7) // 8)
        rows[case["case_id"]] = {
            "expression_v2_sha256": case["expression_v2_sha256"],
            "query_trace_sha256": case["query_trace_sha256"],
            "full_truth_sha256": hashlib.sha256(
                full.to_bytes(byte_count, "little")
            ).hexdigest(),
            "q64_output_sha256": digest(document),
            "query_output_sha256": [digest(row) for row in semantic_rows],
        }
    core = {
        "schema": ORACLE_SCHEMA,
        "oracle": "independent_standard_library_scalar_truth_then_restriction/v1",
        "parent_freeze_file_sha256": PARENT_FILE_SHA256,
        "case_set_sha256": CASE_SET_SHA256,
        "query_count": QUERY_COUNT,
        "cases": rows,
        "timing_evidence_produced": False,
        "prospective_cases_consumed": 0,
    }
    return {**core, "oracles_sha256": digest(core)}


def validate_oracles(oracles: Mapping[str, Any], frozen: Mapping[str, Any]) -> None:
    core = {key: oracles[key] for key in oracles if key != "oracles_sha256"}
    _require(oracles.get("schema") == ORACLE_SCHEMA, "oracle schema")
    _require(oracles.get("oracles_sha256") == digest(core), "oracle canonical identity")
    _require(oracles.get("case_set_sha256") == CASE_SET_SHA256, "oracle case-set identity")
    _require(set(oracles["cases"]) == {row["case_id"] for row in frozen["cohort"]["cases"]},
             "oracle case closure")
    _require(build_oracles(frozen) == oracles, "independent oracle replay")


def build_child_freeze(
    root: Path, run_dir: Path, baseline_path: Path, oracle_path: Path,
    native_identity: Mapping[str, Any],
) -> dict[str, Any]:
    frozen = load_verified_parent(root)
    baseline = load_json(baseline_path)
    oracles = load_json(oracle_path)
    validate_oracles(oracles, frozen)
    source_paths = (*ARM_SOURCE_PATHS, *EXECUTION_SOURCE_PATHS)
    source_closure = [file_identity(root, relative) for relative in source_paths]
    case_bindings = [
        {
            "case_id": row["case_id"],
            "n_vars": row["n_vars"],
            "expression_v2_sha256": row["expression_v2_sha256"],
            "query_trace_sha256": row["query_trace_sha256"],
            "frozen_input_sha256": digest({
                "case_id": row["case_id"], "n_vars": row["n_vars"],
                "expression_v2": row["expression_v2"], "query_trace": row["query_trace"],
            }),
        }
        for row in frozen["cohort"]["cases"]
    ]
    relative_run = run_dir.relative_to(root).as_posix()
    core = {
        "schema": CHILD_SCHEMA,
        "status": "frozen_authorized_not_executed",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "parent": {
            "path": PARENT_RELATIVE,
            "file_sha256": PARENT_FILE_SHA256,
            "canonical_sha256": PARENT_CANONICAL_SHA256,
            "task_contract_sha256": TASK_SHA256,
            "case_set_sha256": CASE_SET_SHA256,
            "label_policy_sha256": LABEL_POLICY_SHA256,
            "embedded_source_checkpoint": SOURCE_CHECKPOINT,
        },
        "baseline_closure": {
            "path": baseline_path.relative_to(root).as_posix(),
            "file_sha256": file_sha256(baseline_path),
            "canonical_sha256": baseline["closure_sha256"],
            "all_relevant_exact_baselines_included": True,
        },
        "oracles": {
            "path": oracle_path.relative_to(root).as_posix(),
            "file_sha256": file_sha256(oracle_path),
            "canonical_sha256": oracles["oracles_sha256"],
            "generated_before_timing": True,
        },
        "cases": case_bindings,
        "source_closure": source_closure,
        "source_closure_sha256": digest(source_closure),
        "initial_native_artifact": dict(native_identity),
        "native_artifact_policy": (
            "each physical host compiles from bound C/build inputs and seals its "
            "native/compiler hashes in HOST_PREFLIGHT.json before timing"
        ),
        "schedule": {
            "case_order": [row["case_id"] for row in frozen["cohort"]["cases"]],
            "arm_orders": arm_orders(),
            "blocks": BLOCKS,
            "query_count": QUERY_COUNT,
            "planned_cells_per_host": EXPECTED_CELLS,
            "construction_uses_split_features_labels_identities_or_timings": False,
            "identical_on_every_host": True,
        },
        "measurement_contract": {
            "fresh_process_per_timed_cell": True,
            "process_startup_inside_accounted_total": False,
            "accounted_stages": list(campaign.STAGES),
            "accounted_total": "sum(accounted_stages)",
            "positive_finite_accounted_total_required": True,
            "cell_timeout_seconds": CELL_TIMEOUT_SECONDS,
            "failures_refusals_timeouts_and_exit_status_retained": True,
            "failed_host_attempt_must_be_preserved_and_fully_restarted": True,
            "memory_learning_measurement_permitted": False,
        },
        "charged_cost_contract": {
            "function": "query_ladder_learning_freeze.measure_charged_cost_components",
            "batches": 21,
            "repetitions_per_case_per_batch": 1000,
            "raw_samples_retained": True,
            "same_host_as_exact_timings": True,
            "expected_fallback_computed_only_after_joint_labels": True,
        },
        "authorization": {
            "source": "user prompt attached 2026-09-09",
            "exact_q64_execution": True,
            "exact_oracle_verification": True,
            "same_host_charged_cost_measurement": True,
            "physical_machines_already_available_only": True,
            "cloud_or_runpod": False,
            "model_fit_or_training": False,
            "prospective_case_access": False,
            "production_publish_deploy_commit_push": False,
        },
        "claim_boundary": {
            "development_training_eligibility_may_be_assessed_later": True,
            "prospective_consumption_permitted": False,
            "production_routing_permitted": False,
        },
        "run_directory": relative_run,
        "prospective_cases_consumed": 0,
        "decision_timings_opened": False,
        "labels_produced": False,
        "models_trained": 0,
    }
    return {**core, "child_freeze_sha256": digest(core)}


def verify_child_freeze(root: Path, freeze_path: Path) -> dict[str, Any]:
    child = load_json(freeze_path)
    core = {key: child[key] for key in child if key != "child_freeze_sha256"}
    _require(child.get("schema") == CHILD_SCHEMA, "child freeze schema")
    _require(child.get("child_freeze_sha256") == digest(core), "child freeze identity")
    load_verified_parent(root)
    _require(child["parent"] == {
        "path": PARENT_RELATIVE, "file_sha256": PARENT_FILE_SHA256,
        "canonical_sha256": PARENT_CANONICAL_SHA256,
        "task_contract_sha256": TASK_SHA256, "case_set_sha256": CASE_SET_SHA256,
        "label_policy_sha256": LABEL_POLICY_SHA256,
        "embedded_source_checkpoint": SOURCE_CHECKPOINT,
    }, "child parent binding")
    for name in ("baseline_closure", "oracles"):
        binding = child[name]
        path = (root / binding["path"]).resolve()
        _require(path.is_relative_to(root) and file_sha256(path) == binding["file_sha256"],
                 f"child {name} file identity")
    baseline = load_json(root / child["baseline_closure"]["path"])
    _require(
        baseline.get("status") == "verified_complete"
        and baseline.get("closure_sha256") == child["baseline_closure"]["canonical_sha256"]
        and baseline.get("all_relevant_exact_baselines_included") is True,
        "child baseline closure",
    )
    oracles = load_json(root / child["oracles"]["path"])
    _require(oracles.get("oracles_sha256") == child["oracles"]["canonical_sha256"],
             "child oracle canonical identity")
    _require(child["source_closure_sha256"] == digest(child["source_closure"]),
             "child source closure identity")
    _require(all(file_identity(root, row["path"]) == row for row in child["source_closure"]),
             "child source closure drift")
    native = child["initial_native_artifact"]
    native_path = (root / native["native_library"]).resolve()
    _require(
        native_path.is_relative_to(root) and native_path.is_file()
        and file_sha256(native_path) == native["native_library_sha256"]
        and native_path.stat().st_size == native["native_library_bytes"],
        "child initial native artifact",
    )
    frozen = load_verified_parent(root)
    expected_cases = [{
        "case_id": row["case_id"], "n_vars": row["n_vars"],
        "expression_v2_sha256": row["expression_v2_sha256"],
        "query_trace_sha256": row["query_trace_sha256"],
        "frozen_input_sha256": digest({
            "case_id": row["case_id"], "n_vars": row["n_vars"],
            "expression_v2": row["expression_v2"], "query_trace": row["query_trace"],
        }),
    } for row in frozen["cohort"]["cases"]]
    _require(child["cases"] == expected_cases, "child case bindings")
    _require(child["schedule"]["arm_orders"] == arm_orders(), "child arm orders")
    _require(sum(1 for _ in expected_schedule(frozen)) == EXPECTED_CELLS,
             "child schedule cardinality")
    return {
        "schema": CHILD_VERIFICATION_SCHEMA,
        "status": "verified_frozen_authorized_not_executed",
        "child_freeze_file_sha256": file_sha256(freeze_path),
        "child_freeze_canonical_sha256": child["child_freeze_sha256"],
        "parent_identities_verified": True,
        "baseline_closure_verified": True,
        "oracle_binding_verified": True,
        "source_closure_verified": True,
        "schedule_verified": True,
        "planned_cells_per_host": EXPECTED_CELLS,
        "timing_evidence_produced": False,
        "prospective_cases_consumed": 0,
    }


def build_native(root: Path, output: Path, compiler: str = "cc") -> tuple[Path, dict[str, Any]]:
    _require(not output.exists(), "native output already exists")
    source = root / "native/cm_fused_slots/fused_slot_executor.c"
    if os.name == "nt":
        from scripts.build_cm_fused_slots import build
        library = build(output)
        candidates = sorted((root.anchor and Path(
            r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC"
        )).glob("*/bin/Hostx64/x64/cl.exe"))
        _require(bool(candidates), "MSVC compiler executable unavailable")
        executable = candidates[-1]
        version = subprocess.run(
            [str(executable)], capture_output=True, text=True, timeout=20,
        )
        version_text = (version.stdout + version.stderr).strip()
        command = ["native/cm_fused_slots/build_msvc.cmd", "vcvars64.bat",
                   source.relative_to(root).as_posix(), output.relative_to(root).as_posix()]
    else:
        resolved = shutil.which(compiler)
        _require(resolved is not None, f"compiler unavailable: {compiler}")
        executable = Path(resolved).resolve()
        version = subprocess.run([str(executable), "--version"], check=True,
                                 capture_output=True, text=True, timeout=20)
        version_text = (version.stdout + version.stderr).strip()
        output.mkdir(parents=True, exist_ok=False)
        suffix = ".dylib" if sys.platform == "darwin" else ".so"
        library = output / f"libcm_fused_slots{suffix}"
        command = [str(executable), "-std=c11", "-O3", "-Wall", "-Wextra",
                   "-Wpedantic", "-shared", "-fPIC", str(source), "-o", str(library)]
        subprocess.run(command, cwd=root, check=True, capture_output=True,
                       text=True, timeout=120)
    identity = {
        "source_sha256": file_sha256(source),
        "compiler_executable_sha256": file_sha256(executable),
        "compiler_identity_sha256": digest({
            "executable_sha256": file_sha256(executable), "version": version_text,
        }),
        "compiler_version": version_text,
        "build_command": command,
        "native_library": library.relative_to(root).as_posix(),
        "native_library_bytes": library.stat().st_size,
        "native_library_sha256": file_sha256(library),
        "platform": platform.platform(),
    }
    return library, identity


def physical_machine_identity() -> tuple[dict[str, Any], str]:
    facts = {
        "node": platform.node(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "platform": platform.platform(),
        "logical_cpu_count": os.cpu_count(),
    }
    return facts, digest(facts)


def execute_cell(
    frozen: Mapping[str, Any], oracles: Mapping[str, Any], native_path: Path,
    case_id: str, arm: str, *, clock=time.perf_counter_ns,
) -> dict[str, Any]:
    case = next(row for row in frozen["cohort"]["cases"] if row["case_id"] == case_id)
    runtime_case = {
        "case_id": case_id, "n_vars": case["n_vars"],
        "expression_v2": case["expression_v2"], "c36_trace": case["query_trace"],
    }
    native = load_native_slot_library(native_path)
    timings, outputs, resources = campaign._lane_b_outputs(runtime_case, arm, native, clock)
    started = clock()
    rows = [
        semantic_row(query, output, case["n_vars"])
        for query, output in zip(case["query_trace"], outputs, strict=True)
    ]
    document = semantic_document(case_id, rows)
    timings["delivery_ns"] = max(1, clock() - started)
    actual = digest(document)
    expected = oracles["cases"][case_id]["q64_output_sha256"]
    _require(actual == expected, f"q64 oracle mismatch: {case_id}:{arm}")
    started = clock()
    payload = canonical_bytes(document)
    timings["serialization_ns_when_applicable"] = max(1, clock() - started)
    started = clock()
    from bitset_backend import clear_bitset_env_cache, clear_words_env_cache
    clear_bitset_env_cache()
    clear_words_env_cache()
    timings["cleanup_ns"] = max(1, clock() - started)
    values = {stage: int(timings.get(stage, 0)) for stage in campaign.STAGES}
    total = sum(values.values())
    _require(total > 0, "non-positive accounted total")
    values["accounted_total_ns"] = total
    return {
        "schema": RAW_SCHEMA, "status": "ok", "reason": "completed",
        "case_id": case_id, "arm": arm, "query_count": QUERY_COUNT,
        "timings_ns": values, "output_sha256": actual,
        "output_bytes": len(payload), "exact_check_passed": True,
        "resources": dict(resources),
        "memory_learning_measurement_performed": False,
    }


def functional_preflight(
    frozen: Mapping[str, Any], oracles: Mapping[str, Any], native_path: Path,
) -> dict[str, Any]:
    class Clock:
        value = 0
        def __call__(self) -> int:
            self.value += 101
            return self.value
    rows = 0
    hashes = Counter()
    for case in frozen["cohort"]["cases"]:
        for arm in parent.EXACT_ARMS:
            row = execute_cell(frozen, oracles, native_path, case["case_id"], arm, clock=Clock())
            _require(row["exact_check_passed"], "functional exactness")
            hashes[row["output_sha256"]] += 1
            rows += 1
    _require(rows == 72 * len(parent.EXACT_ARMS), "functional preflight cardinality")
    _require(all(value == len(parent.EXACT_ARMS) for value in hashes.values()),
             "functional arm output agreement")
    return {
        "schema": "crse-query-ladder-q64-functional-preflight/v1",
        "status": "pass", "cases": 72, "arms": list(parent.EXACT_ARMS),
        "cells": rows, "unique_case_outputs": len(hashes),
        "all_arms_match_independent_oracles": True,
        "synthetic_clock_used": True, "decision_timing_evidence_produced": False,
        "schedule_cells": sum(1 for _ in expected_schedule(frozen)),
        "arm_position_counts": {
            arm: [sum(order[position] == arm for order in arm_orders())
                  for position in range(len(parent.EXACT_ARMS))]
            for arm in parent.EXACT_ARMS
        },
        "prospective_cases_consumed": 0,
    }


def host_medians_from_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, list[int]]] = {}
    for row in rows:
        if row.get("status") != "ok":
            continue
        grouped.setdefault(row["case_id"], {}).setdefault(row["arm"], []).append(
            row["timings_ns"]["accounted_total_ns"]
        )
    return {
        case_id: {arm: float(statistics.median(values)) for arm, values in by_arm.items()}
        for case_id, by_arm in grouped.items()
    }


def p95(values: Sequence[float]) -> float:
    _require(bool(values), "p95 values")
    ordered = sorted(float(value) for value in values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def verify_raw_rows(
    frozen: Mapping[str, Any], oracles: Mapping[str, Any], rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    planned = list(expected_schedule(frozen))
    schedule_mismatches = semantic_mismatches = timing_mismatches = 0
    for index, row in enumerate(rows):
        if index >= len(planned):
            schedule_mismatches += 1
            continue
        expected = planned[index]
        if any(row.get(key) != value for key, value in expected.items()):
            schedule_mismatches += 1
        if not (row.get("status") == "ok" and row.get("exact_check_passed") is True
                and row.get("output_sha256") == oracles["cases"][expected["case_id"]]["q64_output_sha256"]):
            semantic_mismatches += 1
        timings = row.get("timings_ns", {})
        if not (
            set(timings) == {*campaign.STAGES, "accounted_total_ns"}
            and all(type(timings[name]) is int and timings[name] >= 0 for name in campaign.STAGES)
            and type(timings["accounted_total_ns"]) is int
            and timings["accounted_total_ns"] > 0
            and timings["accounted_total_ns"] == sum(timings[name] for name in campaign.STAGES)
        ):
            timing_mismatches += 1
    schedule_mismatches += abs(len(planned) - len(rows))
    return {
        "expected_cells": len(planned), "completed_rows": len(rows),
        "schedule_mismatches": schedule_mismatches,
        "semantic_mismatches": semantic_mismatches,
        "timing_mismatches": timing_mismatches,
        "status": "verified_complete" if (
            len(rows) == len(planned) and schedule_mismatches == semantic_mismatches == timing_mismatches == 0
        ) else "incomplete",
    }


def finite_positive(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value > 0
