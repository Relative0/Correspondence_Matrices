"""Profile one provenance-independent caller-visible CM truth-layout workflow."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from typing import Any

import numpy as np

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Or, Var, Xor
from cm_ir import (
    clear_cm_ir_alignment_cache,
    clear_cm_ir_compile_cache,
    clear_cm_ir_persistent_cache,
    compile_expr_to_cm_ir,
    materialize_cm,
)
from cm_normalize import canonical_layout, clear_cm_normalize_caches

from .contracts import canonical_bytes
from .h2_h3_profile_gate import COMPONENTS, H2_COMPONENTS, H3_COMPONENTS, _profile_once
from .ir import cm_dag_signature


SOURCE_CHECKPOINT = "43fffcfaa53aab0d2ce95ca902c11e8f23484dfe"
REVIEWED_REF = "refs/remotes/origin/codex/cm-h2-h3-h6-gates-20260908"
ORIGIN_MAIN_REF = "refs/remotes/origin/main"
SCHEMA = "cm-independent-active-workflow-freeze/v1"
RAW_SCHEMA = "cm-independent-active-workflow-profile-row/v1"
MEMORY_RAW_SCHEMA = "cm-independent-active-workflow-memory-row/v1"
SUMMARY_SCHEMA = "cm-independent-active-workflow-summary/v1"
CHECKPOINT_SCHEMA = "cm-independent-active-workflow-checkpoint/v1"
DISCOVERY_SCHEMA = "cm-independent-active-workflow-discovery/v1"
PROTOCOL = "docs/research/CM_INDEPENDENT_ACTIVE_VIDEO_TRUTH_LAYOUT_PROFILE_PROTOCOL_2026_09_08.md"
RETRY_NOTE = "docs/research/CM_INDEPENDENT_ACTIVE_VIDEO_TRUTH_LAYOUT_PROFILE_RETRY_002_2026_09_08.md"
CALLER_SOURCE = "docs/video_factory/deep_series_chapter_compiler.py"
CONTRACT_ROOT = "docs/video_factory/deep_series/episodes"
WARMUPS = 2
REPETITIONS = 7
MEMORY_REPLICATES = 3
LIFECYCLES = ("cold", "reused")
PRIMITIVES = ("expression_matrix", "representation_compare")
SOURCE_CLOSURE = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cm_normalize.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/h2_h3_profile_gate.py",
    "cmbench/comparative/h6_fresh_process_memory_gate.py",
    "cmbench/comparative/independent_active_workflow_gate.py",
    "cmbench/comparative/ir.py",
    "scripts/cm_independent_active_workflow_gate.py",
    "scripts/crse_verify_independent_active_workflow_gate.py",
    CALLER_SOURCE,
    PROTOCOL,
    RETRY_NOTE,
    "docs/research/CM_HARDWARE_BEHAVIOR_CHANGE_CORPUS_RESULT_2026_09_04.md",
    "docs/research/CM_ARCHITECTURE_AUDIT_DISPOSITION_AFTER_C38_2026_09_03.md",
    "docs/research/CM_H2_H3_CURRENT_SOURCE_PROFILE_GATE_RESULT_2026_09_08.md",
    "docs/research/CM_H6_FRESH_PROCESS_MEMORY_AND_ESTIMATOR_RESULT_2026_09_08.md",
)


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        stream.write("\n")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={root}", *args], cwd=root,
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=False,
    )
    _require(result.returncode == 0, f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def _file_record(root: Path, relative: str) -> dict[str, Any]:
    path = (root / relative).resolve()
    _require(path.is_relative_to(root) and path.is_file(), f"missing source: {relative}")
    return {"path": relative, "bytes": path.stat().st_size, "sha256": _sha256(path)}


def record_checkpoint(project_root: str | Path, original_checkout: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    original = Path(original_checkout).resolve()
    _require(_git(root, "rev-parse", "HEAD") == SOURCE_CHECKPOINT, "worktree checkpoint")
    status = _git(original, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
    reviewed = _git(root, "rev-parse", REVIEWED_REF)
    main = _git(root, "rev-parse", ORIGIN_MAIN_REF)
    ancestor = subprocess.run(
        ["git", "-c", f"safe.directory={root}", "merge-base", "--is-ancestor", reviewed, main], cwd=root,
        capture_output=True, check=False,
    ).returncode == 0
    return {
        "schema": CHECKPOINT_SCHEMA,
        "date": "2026-09-08",
        "reviewed_remote_ref": REVIEWED_REF,
        "reviewed_commit": reviewed,
        "origin_main_commit": main,
        "reviewed_merged_into_origin_main": ancestor,
        "selected_base": REVIEWED_REF if not ancestor else ORIGIN_MAIN_REF,
        "worktree_head": _git(root, "rev-parse", "HEAD"),
        "worktree_detached": _git(root, "branch", "--show-current") == "",
        "original_checkout": str(original),
        "original_head": _git(original, "rev-parse", "HEAD"),
        "original_status_paths_only": status,
        "original_dirty_entry_count": len(status),
        "original_checkout_modified": False,
        "secrets_or_file_contents_read": False,
    }


def checkpoint_to_path(project_root: str | Path, original_checkout: str | Path, output: str | Path) -> dict[str, Any]:
    value = record_checkpoint(project_root, original_checkout)
    _write_new(Path(output), value)
    return value


def _history(root: Path, relative: str) -> list[dict[str, str]]:
    raw = _git(root, "log", "--follow", "--reverse", "--date=iso-strict", "--format=%H%x09%aI%x09%s", "--", relative)
    rows = []
    for line in raw.splitlines():
        commit, date, subject = line.split("\t", 2)
        rows.append({"commit": commit, "date": date, "subject": subject})
    return rows


def _contract_occurrences(root: Path) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    contract_root = root / CONTRACT_ROOT
    for path in sorted(contract_root.rglob("executable_render_contract.json")):
        contract = _load(path)
        for index, scene in enumerate(contract.get("resolved_scenes", [])):
            primitive = scene.get("primitive")
            if primitive not in PRIMITIVES:
                continue
            data = scene["pop_scene"]["data"]
            artifact = (
                {key: data[key] for key in ("expression", "ambient_variables", "live_variables", "matrix")}
                if primitive == "expression_matrix" else data["matrix"]
            )
            relative = path.relative_to(root).as_posix()
            occurrences.append({
                "occurrence_id": f"{contract['video_id']}:{contract['chapter_id']}:{scene['scene_id']}:{primitive}",
                "video_id": contract["video_id"],
                "chapter_id": contract["chapter_id"],
                "scene_id": scene["scene_id"],
                "primitive": primitive,
                "contract_path": relative,
                "contract_file_sha256": _sha256(path),
                "contract_content_hash": contract["content_hash"],
                "source_storyboard_scene_sha256": scene["source_storyboard_scene_sha256"],
                "artifact": artifact,
                "artifact_sha256": _digest(artifact),
            })
    _require(bool(occurrences), "no active truth-layout occurrences")
    _require(len({row["occurrence_id"] for row in occurrences}) == len(occurrences), "duplicate occurrence")
    return occurrences


def build_discovery(project_root: str | Path, checkpoint_path: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    checkpoint_file = Path(checkpoint_path).resolve()
    checkpoint = _load(checkpoint_file)
    _require(checkpoint["schema"] == CHECKPOINT_SCHEMA, "checkpoint schema")
    occurrences = _contract_occurrences(root)
    contract_count = len(list((root / CONTRACT_ROOT).rglob("executable_render_contract.json")))
    active_dirty = [line for line in checkpoint["original_status_paths_only"] if "docs/video_factory/" in line.replace("\\", "/")]
    candidates = [
        {
            "candidate_id": "deep_series_truth_layout",
            "provenance": _history(root, CALLER_SOURCE),
            "active_evidence": {"tracked_chapter_contracts": contract_count, "real_call_occurrences": len(occurrences), "current_original_checkout_path_entries": len(active_dirty)},
            "inputs": "video_id and frozen four-variable foundation expression semantics",
            "outputs": "ordered exact expression/matrix data embedded in executable render contracts",
            "caller_visible_semantics": "row-major AB rows by CD columns with fixed labels and canonical contract hashes",
            "scale": {"ambient_variables": 4, "matrix_cells_per_call": 16, "occurrences": len(occurrences)},
            "reuse_pattern": "repeated chapter-scene compilation across maintained deep-series artifacts",
            "independence": "created for evidence-bound educational video production before this architecture gate",
            "admitted": True,
        },
        {
            "candidate_id": "cm_remote_worker",
            "provenance": _history(root, "cm_remote_worker.py"),
            "admitted": False,
            "exclusion": "created for optional remote CM benchmark execution; purpose is not independent of CM measurement",
        },
        {
            "candidate_id": "crse_task_computation_experiment",
            "provenance": _history(root, "cmbench/recognition/computation_experiment.py"),
            "admitted": False,
            "exclusion": "explicit benchmark/research workload selected to compare CM representations",
        },
        {
            "candidate_id": "learning_benchmark_handoff",
            "provenance": _history(root, "cmbench/recognition/learning_benchmark_handoff.py"),
            "admitted": False,
            "exclusion": "active exact contract but validates evidence and does not exercise CM construction or evaluation",
        },
        {
            "candidate_id": "hardware_and_configuration_revisions",
            "admitted": False,
            "exclusion": "H9 and earlier revision panels are binding stopped data and cannot be reopened or replaced",
        },
    ]
    core = {
        "schema": DISCOVERY_SCHEMA,
        "date": "2026-09-08",
        "checkpoint_path": checkpoint_file.relative_to(root).as_posix(),
        "checkpoint_sha256": _sha256(checkpoint_file),
        "metadata_only_before_admission": True,
        "secrets_private_databases_credentials_read": False,
        "selection_blind_to_candidate_timing_and_memory": True,
        "admission_rule": [
            "preexisting_non_benchmark_purpose", "reviewed_executable_source_and_artifact",
            "exact_inputs_outputs_order_and_hashes", "real_repetition_or_reuse",
            "independent_oracle", "no_selection_by_cm_architecture_favorability",
        ],
        "candidates": candidates,
        "admitted_workflow_id": "deep_series_truth_layout",
        "admitted_workflow_count": sum(bool(row["admitted"]) for row in candidates),
        "occurrence_count": len(occurrences),
    }
    _require(core["admitted_workflow_count"] == 1, "exactly one admitted workflow")
    return {**core, "discovery_sha256": _digest(core)}


def discovery_to_path(project_root: str | Path, checkpoint_path: str | Path, output: str | Path) -> dict[str, Any]:
    value = build_discovery(project_root, checkpoint_path)
    _write_new(Path(output), value)
    return value


def _expressions() -> dict[str, Any]:
    a, b, c, d = (Var(index) for index in range(4))
    return {
        "main": expr_to_json_dag(Xor(And(a, b), Or(c, d))),
        "ambient_control": expr_to_json_dag(Xor(And(a, b), c)),
    }


def _oracle_key(row: Mapping[str, Any]) -> str:
    cohort = "ambient_control" if row["video_id"] == "live-support-ambient" else "main"
    return f"{cohort}:{row['primitive']}"


def build_freeze(project_root: str | Path, checkpoint_path: str | Path, discovery_path: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    checkpoint_file, discovery_file = Path(checkpoint_path).resolve(), Path(discovery_path).resolve()
    checkpoint, discovery = _load(checkpoint_file), _load(discovery_file)
    _require(checkpoint["reviewed_commit"] == SOURCE_CHECKPOINT and checkpoint["selected_base"] == REVIEWED_REF, "checkpoint base")
    _require(discovery["admitted_workflow_id"] == "deep_series_truth_layout" and discovery["admitted_workflow_count"] == 1, "discovery admission")
    occurrences = _contract_occurrences(root)
    expressions = _expressions()
    for row in occurrences:
        row["cohort"] = "ambient_control" if row["video_id"] == "live-support-ambient" else "main"
        row["oracle_key"] = _oracle_key(row)
        row["low_sharing_control"] = True
        row["expression_v2"] = expressions[row["cohort"]]
    oracle_groups: dict[str, dict[str, Any]] = {}
    for row in occurrences:
        existing = oracle_groups.setdefault(row["oracle_key"], row["artifact"])
        _require(canonical_bytes(existing) == canonical_bytes(row["artifact"]), f"oracle group mismatch: {row['oracle_key']}")
    closure = [_file_record(root, relative) for relative in SOURCE_CLOSURE]
    core = {
        "schema": SCHEMA,
        "date": "2026-09-08",
        "status": "frozen_before_decision_bearing_timing_or_memory",
        "retry": {
            "attempt": 2,
            "reason": "instrumentation_only_h6_line_reader_and_handshake_adapter_correction",
            "attempt_001_freeze_sha256": _sha256(root / "docs/research/verification/cm-independent-active-workflow-2026-09-08/FREEZE_ATTEMPT_001.json"),
            "attempt_001_profile_raw_sha256": _sha256(root / "docs/research/verification/cm-independent-active-workflow-2026-09-08/RAW_ATTEMPT_001.jsonl"),
            "attempt_001_memory_raw_bytes": (root / "docs/research/verification/cm-independent-active-workflow-2026-09-08/MEMORY_RAW_ATTEMPT_001.jsonl").stat().st_size,
            "failure_record_sha256": _sha256(root / "docs/research/verification/cm-independent-active-workflow-2026-09-08/ATTEMPT_001_FAILURE.json"),
        },
        "source_checkpoint": SOURCE_CHECKPOINT,
        "source_ref": REVIEWED_REF,
        "checkpoint": {"path": checkpoint_file.relative_to(root).as_posix(), "sha256": _sha256(checkpoint_file)},
        "discovery": {"path": discovery_file.relative_to(root).as_posix(), "sha256": _sha256(discovery_file), "canonical_sha256": discovery["discovery_sha256"]},
        "workload": {
            "workflow_id": "deep_series_truth_layout",
            "occurrences": occurrences,
            "oracle_groups": oracle_groups,
            "ambient_order": ["A", "B", "C", "D"],
            "row_order": ["AB=00", "AB=01", "AB=10", "AB=11"],
            "column_order": ["CD=00", "CD=01", "CD=10", "CD=11"],
            "all_failures_refusals_zeroes_unfavorable_rows_retained": True,
        },
        "arm": {
            "name": "unchanged_current_cm_dense",
            "production_behavior_changed": False,
            "persistent_cache": False,
            "compile_cache_reuse": False,
            "native_boundary": "not_exercised_by_admitted_workflow",
        },
        "measurement": {
            "lifecycles": list(LIFECYCLES), "warmups": WARMUPS, "timing_repetitions": REPETITIONS,
            "profile_passes_per_cell": 1, "memory_replicates": MEMORY_REPLICATES,
            "memory_process": "fresh_spawn_external_h6_sampler_infrastructure_only",
            "timing_boundary": "dag_decode_through_exact_caller_artifact_canonical_serialization",
            "reused_state": "parsed_expression_compiled_cm_ir_and_layout_only_no_output_cache",
            "signed_retained_and_absolute_peak_endpoints_required": True,
        },
        "materiality_gate": {
            "minimum_cells": 6, "aggregate_share_min": 0.15, "median_cell_share_min": 0.10,
            "median_exclusive_ns_min": 50_000, "cell_prevalence_share_floor": 0.10,
            "cell_prevalence_min": 0.50, "per_cohort_aggregate_share_min": 0.10,
            "allocation_copy_peak_excess_over_output_min": 0.25,
        },
        "candidate_gate": {
            "eligible_only_if_exactly_one_component_passes": True,
            "target_end_to_end_geomean_improvement_min": 0.03,
            "target_component_improvement_min": 0.05,
            "individual_regression_max": 0.05, "low_sharing_regression_max": 0.03,
            "peak_or_retained_memory_regression_max": 0.05,
            "runtime_selector_authorized": False, "production_change_authorized": False,
        },
        "continuation": {
            "zero_components": "no_go_no_material_component",
            "multiple_components": "no_go_nonunique_material_components",
            "exactly_one_component": "candidate_eligible_requires_separate_freeze",
            "runpod_authorized": False, "h2_h3_h6_h9_reopened": False,
        },
        "expected_profile_rows": len(occurrences) * len(LIFECYCLES),
        "expected_memory_rows": len(oracle_groups) * len(LIFECYCLES) * MEMORY_REPLICATES,
        "source_closure": closure,
        "source_closure_sha256": _digest(closure),
    }
    return {**core, "freeze_sha256": _digest(core)}


def validate_freeze(freeze: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    _require(freeze.get("schema") == SCHEMA, "freeze schema")
    core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    _require(freeze.get("freeze_sha256") == _digest(core), "freeze digest")
    _require(_git(root, "rev-parse", "HEAD") == SOURCE_CHECKPOINT, "source checkpoint drift")
    for record in freeze["source_closure"]:
        _require(_file_record(root, record["path"]) == record, f"source drift: {record['path']}")
    _require(_digest(freeze["source_closure"]) == freeze["source_closure_sha256"], "closure digest")
    _require(len(freeze["workload"]["occurrences"]) * 2 == freeze["expected_profile_rows"], "profile cardinality")
    return dict(freeze)


def freeze_to_path(project_root: str | Path, checkpoint_path: str | Path, discovery_path: str | Path, output: str | Path) -> dict[str, Any]:
    value = build_freeze(project_root, checkpoint_path, discovery_path)
    _write_new(Path(output), value)
    return value


def _reset_caches() -> None:
    clear_cm_ir_alignment_cache()
    clear_cm_ir_compile_cache()
    clear_cm_ir_persistent_cache()
    clear_cm_normalize_caches()


def _prepare(row: Mapping[str, Any]) -> dict[str, Any]:
    expression = expr_from_json(row["expression_v2"])
    node = compile_expr_to_cm_ir(expression, reuse_cache=False, persistent_cache=False, share_aware_flatten=True)
    layout = canonical_layout(["x0", "x1", "x2", "x3"])
    return {"expression": expression, "node": node, "layout": layout}


def _timed(stages: dict[str, int], name: str, function: Callable[[], Any]) -> Any:
    started = time.perf_counter_ns()
    value = function()
    stages[name] = time.perf_counter_ns() - started
    return value


def _pack_dense(dense: np.ndarray) -> str:
    return "".join(str(int(value)) for value in np.asarray(dense, dtype=np.uint8).reshape(-1))


def _structure_sha(node: Any) -> str:
    return _digest(cm_dag_signature(node))


def _run_once(row: Mapping[str, Any], state: dict[str, Any] | None, instrument: bool = False) -> dict[str, Any]:
    stages: dict[str, int] = {}
    diagnostics: dict[str, Any] = {"ir_timing_enabled": 1} if instrument else {}
    if state is None:
        expression = _timed(stages, "construction_decode", lambda: expr_from_json(row["expression_v2"]))
        node = _timed(stages, "construction_cm_ir", lambda: compile_expr_to_cm_ir(
            expression, diagnostics=diagnostics, reuse_cache=False, persistent_cache=False,
            share_aware_flatten=True,
        ))
        layout = _timed(stages, "layout", lambda: canonical_layout(["x0", "x1", "x2", "x3"]))
    else:
        node, layout = state["node"], state["layout"]
        stages.update({"construction_decode": 0, "construction_cm_ir": 0, "layout": 0})
    dense = _timed(stages, "dense_materialization", lambda: materialize_cm(
        node, layout[0], layout[1], fixed={}, diagnostics=diagnostics if instrument else None,
    ))
    bits = _timed(stages, "conversion", lambda: _pack_dense(dense))
    full = _timed(stages, "delivery", lambda: {
        "expression": row["artifact"].get("expression", "(A AND B) XOR C" if row["cohort"] == "ambient_control" else "(A AND B) XOR (C OR D)"),
        "ambient_variables": ["A", "B", "C", "D"],
        "live_variables": ["A", "B", "C"] if row["cohort"] == "ambient_control" else ["A", "B", "C", "D"],
        "matrix": {"rows": 4, "columns": 4, "bits": bits,
                   "row_labels": ["AB=00", "AB=01", "AB=10", "AB=11"],
                   "column_labels": ["CD=00", "CD=01", "CD=10", "CD=11"]},
    })
    artifact = full if row["primitive"] == "expression_matrix" else full["matrix"]
    payload = _timed(stages, "serialization", lambda: canonical_bytes(artifact))
    exact = canonical_bytes(artifact) == canonical_bytes(row["artifact"])
    _require(exact, f"caller oracle mismatch: {row['occurrence_id']}")
    return {
        "stages_ns": stages, "artifact": artifact, "payload": payload,
        "output_sha256": _digest(artifact),
        "ordering_sha256": _digest({"ambient": ["A", "B", "C", "D"], "rows": full["matrix"]["row_labels"], "columns": full["matrix"]["column_labels"]}),
        "structure_sha256": _structure_sha(node), "output_bytes": len(payload),
        "required_artifact_bytes": int(dense.nbytes), "diagnostics": diagnostics,
        "anchor": (node, dense, artifact, payload),
    }


def _measure_profile_row(row: Mapping[str, Any], lifecycle: str) -> dict[str, Any]:
    def new_state() -> dict[str, Any] | None:
        if lifecycle == "cold":
            return None
        _reset_caches(); gc.collect()
        return _prepare(row)
    state = new_state()
    for _ in range(WARMUPS):
        if lifecycle == "cold": _reset_caches(); gc.collect()
        _run_once(row, state)
    trials = []
    identities = set()
    for _ in range(REPETITIONS):
        if lifecycle == "cold": _reset_caches(); gc.collect()
        result = _run_once(row, state)
        stages = {key: int(value) for key, value in result["stages_ns"].items()}
        trials.append({"stages_ns": stages, "accounted_total_ns": sum(stages.values())})
        identities.add((result["output_sha256"], result["ordering_sha256"], result["structure_sha256"]))
    profile_state = new_state()
    if lifecycle == "cold": _reset_caches(); gc.collect()
    profile_result, profile = _profile_once(lambda: _run_once(row, profile_state, True))
    identities.add((profile_result["output_sha256"], profile_result["ordering_sha256"], profile_result["structure_sha256"]))
    shares = {name: profile["exclusive_self_ns"][name] / profile["accounted_self_ns"] if profile["accounted_self_ns"] else 0.0 for name in COMPONENTS}
    identity = sorted(identities)[0]
    return {
        "schema": RAW_SCHEMA, "row_id": f"{row['occurrence_id']}:{lifecycle}",
        "occurrence_id": row["occurrence_id"], "cohort": row["cohort"],
        "primitive": row["primitive"], "lifecycle": lifecycle,
        "hypothesis_scope": ["H2", "H3"] if lifecycle == "cold" else ["H3"],
        "low_sharing_control": True, "status": "ok" if len(identities) == 1 else "mismatch",
        "exact_oracle_agreement": profile_result["output_sha256"] == row["artifact_sha256"],
        "stable_output_order_and_hashes": len(identities) == 1,
        "output_sha256": identity[0], "ordering_sha256": identity[1], "structure_sha256": identity[2],
        "output_bytes": profile_result["output_bytes"], "required_artifact_bytes": profile_result["required_artifact_bytes"],
        "raw_timing_trials": trials,
        "median_stages_ns": {name: round(statistics.median(trial["stages_ns"].get(name, 0) for trial in trials)) for name in sorted(trials[0]["stages_ns"])},
        "median_accounted_total_ns": round(statistics.median(trial["accounted_total_ns"] for trial in trials)),
        "profile": {**profile, "exclusive_share": shares},
        "instrumentation_diagnostics": profile_result["diagnostics"],
    }


def run_profile(project_root: str | Path, freeze_path: str | Path, output: str | Path) -> dict[str, Any]:
    root, freeze_file = Path(project_root).resolve(), Path(freeze_path).resolve()
    freeze = _load(freeze_file); validate_freeze(freeze, root)
    target = Path(output).resolve(); _require(target.is_relative_to(root) and not target.exists(), "new profile output")
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        for occurrence in freeze["workload"]["occurrences"]:
            for lifecycle in LIFECYCLES:
                measured = _measure_profile_row(occurrence, lifecycle)
                stream.write(json.dumps(measured, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
                stream.flush(); count += 1
                if count == 1 or count % 50 == 0 or count == freeze["expected_profile_rows"]:
                    print(f"profile rows {count}/{freeze['expected_profile_rows']}", flush=True)
    return {"rows_written": count, "raw_sha256": _sha256(target)}


def expected_memory_rows(freeze: Mapping[str, Any]):
    groups: dict[str, dict[str, Any]] = {}
    for row in freeze["workload"]["occurrences"]:
        groups.setdefault(row["oracle_key"], row)
    counts = {key: sum(row["oracle_key"] == key for row in freeze["workload"]["occurrences"]) for key in groups}
    for key, row in sorted(groups.items()):
        for lifecycle in LIFECYCLES:
            for replicate in range(MEMORY_REPLICATES):
                yield {"row_id": f"{key}:{lifecycle}:r{replicate}", "logical_id": f"{key}:{lifecycle}", "oracle_key": key,
                       "lifecycle": lifecycle, "replicate": replicate, "occurrence_count": counts[key], "representative": row}


_WORKER_ANCHOR: Any = None
_WORKER_STATE: Any = None


def _trace_snapshot() -> dict[str, int]:
    current, peak = tracemalloc.get_traced_memory()
    return {"traced_current_bytes": int(current), "traced_peak_bytes": int(peak)}


def _emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(dict(value), sort_keys=True, separators=(",", ":"), allow_nan=False), flush=True)


def worker_main(project_root: str | Path, freeze_path: str | Path, row_id: str) -> int:
    global _WORKER_ANCHOR, _WORKER_STATE
    root = Path(project_root).resolve(); freeze = _load(Path(freeze_path).resolve())
    core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    _require(freeze.get("schema") == SCHEMA and freeze.get("freeze_sha256") == _digest(core), "worker freeze")
    planned = next((row for row in expected_memory_rows(freeze) if row["row_id"] == row_id), None)
    _require(planned is not None, "unknown memory row")
    _reset_caches(); gc.collect(); tracemalloc.start(); tracemalloc.reset_peak()
    _emit({"phase": "ready", "pid": os.getpid(), **_trace_snapshot()})
    if planned["lifecycle"] == "reused":
        _require(json.loads(sys.stdin.readline())["command"] == "prepare", "prepare command")
        started = time.perf_counter_ns(); _WORKER_STATE = _prepare(planned["representative"])
        _emit({"phase": "prepared", "preparation_ns_descriptive": time.perf_counter_ns() - started, **_trace_snapshot()})
    _require(json.loads(sys.stdin.readline())["command"] == "execute", "execute command")
    tracemalloc.reset_peak(); started = time.perf_counter_ns(); results = []
    for _ in range(planned["occurrence_count"]):
        if planned["lifecycle"] == "cold": _reset_caches()
        results.append(_run_once(planned["representative"], _WORKER_STATE))
    _WORKER_ANCHOR = results
    identities = {(row["output_sha256"], row["ordering_sha256"], row["structure_sha256"]) for row in results}
    _emit({"phase": "result", "execution_ns_descriptive": time.perf_counter_ns() - started,
           "exact_oracle_agreement": all(row["output_sha256"] == planned["representative"]["artifact_sha256"] for row in results),
           "stable_output_order_and_hashes": len(identities) == 1,
           "output_sha256": sorted(identities)[0][0], "ordering_sha256": sorted(identities)[0][1],
           "structure_sha256": sorted(identities)[0][2],
           "output_bytes": sum(row["output_bytes"] for row in results),
           "required_artifact_bytes": sum(row["required_artifact_bytes"] for row in results),
           **_trace_snapshot()})
    _require(json.loads(sys.stdin.readline())["command"] == "release", "release command")
    _WORKER_ANCHOR = None; _WORKER_STATE = None; results = []
    _reset_caches(); gc.collect(); _emit({"phase": "released", **_trace_snapshot()})
    tracemalloc.stop(); return 0


def _run_memory_child(root: Path, freeze_path: Path, planned: Mapping[str, Any], python_executable: Path, worker_script: Path, timeout: float) -> dict[str, Any]:
    from .h6_fresh_process_memory_gate import (
        _ExternalProcessMetrics, _LineReader, _phase, _send, _metric_peak, _delta,
    )
    started = time.perf_counter_ns()
    process = subprocess.Popen(
        [str(python_executable), str(worker_script), "worker", "--project-root", str(root), "--freeze", str(freeze_path), "--row-id", planned["row_id"]],
        cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    metrics = None
    try:
        reader = _LineReader(process.stdout)
        ready = reader.get(timeout); _require(ready.get("phase") == "ready", "memory ready")
        metrics = _ExternalProcessMetrics(process.pid); common = metrics.sample()
        preparation_samples: list[dict[str, int]] = []; prepared = ready
        if planned["lifecycle"] == "reused":
            prepared, preparation_samples = _phase(process, reader, metrics, "prepare", "prepared", timeout)
        prepared_endpoint = metrics.sample()
        result, execution_samples = _phase(process, reader, metrics, "execute", "result", timeout)
        retained = metrics.sample()
        released, release_samples = _phase(process, reader, metrics, "release", "released", timeout)
        post_release = metrics.sample(); process.wait(timeout=timeout); stderr = process.stderr.read()
        _require(process.returncode == 0, f"memory worker exit {process.returncode}: {stderr[-1000:]}")
        samples = [*preparation_samples, *execution_samples, retained]
        memory = {
            "method": "external_controller_fresh_spawn_h6_infrastructure/v1",
            "common_baseline": common, "prepared_endpoint": prepared_endpoint,
            "retained_endpoint": retained, "post_release_endpoint": post_release,
            "preparation_sample_count": len(preparation_samples), "execution_sample_count": len(execution_samples),
            "release_sample_count": len(release_samples), "samplers_stopped": True,
            "working_set_task_peak_bytes": _metric_peak(samples, "working_set_bytes"),
            "working_set_task_peak_delta_bytes": max(0, _metric_peak(samples, "working_set_bytes") - common["working_set_bytes"]),
            "private_task_peak_bytes": _metric_peak(samples, "private_usage_bytes"),
            "private_task_peak_delta_bytes": max(0, _metric_peak(samples, "private_usage_bytes") - common["private_usage_bytes"]),
            "working_set_prepared_retained_delta_bytes": _delta(prepared_endpoint["working_set_bytes"], common["working_set_bytes"]),
            "private_prepared_retained_delta_bytes": _delta(prepared_endpoint["private_usage_bytes"], common["private_usage_bytes"]),
            "working_set_retained_delta_bytes": _delta(retained["working_set_bytes"], common["working_set_bytes"]),
            "private_retained_delta_bytes": _delta(retained["private_usage_bytes"], common["private_usage_bytes"]),
            "working_set_post_release_delta_bytes": _delta(post_release["working_set_bytes"], common["working_set_bytes"]),
            "private_post_release_delta_bytes": _delta(post_release["private_usage_bytes"], common["private_usage_bytes"]),
            "process_peak_working_set_bytes": post_release["process_peak_working_set_bytes"],
            "process_peak_pagefile_bytes": post_release["process_peak_pagefile_bytes"],
            "tracemalloc_common_bytes": int(ready["traced_current_bytes"]),
            "tracemalloc_prepared_bytes": int(prepared["traced_current_bytes"]),
            "tracemalloc_retained_bytes": int(result["traced_current_bytes"]),
            "tracemalloc_post_release_bytes": int(released["traced_current_bytes"]),
            "tracemalloc_task_peak_delta_bytes": max(0, int(result["traced_peak_bytes"]) - int(ready["traced_current_bytes"])),
            "tracemalloc_prepared_retained_delta_bytes": int(prepared["traced_current_bytes"]) - int(ready["traced_current_bytes"]),
            "tracemalloc_retained_delta_bytes": int(result["traced_current_bytes"]) - int(ready["traced_current_bytes"]),
            "tracemalloc_post_release_delta_bytes": int(released["traced_current_bytes"]) - int(ready["traced_current_bytes"]),
        }
        return {"schema": MEMORY_RAW_SCHEMA, **{key: value for key, value in planned.items() if key != "representative"},
                "status": "ok", "child_pid": int(ready["pid"]), "launcher_pid": process.pid,
                "child_exit_code": process.returncode, "spawn_lifecycle_ns_descriptive": time.perf_counter_ns() - started,
                "preparation_ns_descriptive": int(prepared.get("preparation_ns_descriptive", 0)),
                "execution_ns_descriptive": int(result["execution_ns_descriptive"]),
                "exact_oracle_agreement": bool(result["exact_oracle_agreement"]),
                "stable_output_order_and_hashes": bool(result["stable_output_order_and_hashes"]),
                "output_sha256": result["output_sha256"], "ordering_sha256": result["ordering_sha256"],
                "structure_sha256": result["structure_sha256"], "output_bytes": int(result["output_bytes"]),
                "required_artifact_bytes": int(result["required_artifact_bytes"]), "memory": memory}
    finally:
        if metrics is not None: metrics.close()
        if process.poll() is None:
            process.kill(); process.wait(timeout=5)


def run_memory(project_root: str | Path, freeze_path: str | Path, output: str | Path, python_executable: str | Path, worker_script: str | Path, timeout: float = 60.0) -> dict[str, Any]:
    root, freeze_file = Path(project_root).resolve(), Path(freeze_path).resolve()
    freeze = _load(freeze_file); validate_freeze(freeze, root)
    target = Path(output).resolve(); _require(target.is_relative_to(root) and not target.exists(), "new memory output")
    rows = list(expected_memory_rows(freeze)); _require(len(rows) == freeze["expected_memory_rows"], "memory schedule")
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        for index, planned in enumerate(rows, 1):
            result = _run_memory_child(root, freeze_file, planned, Path(python_executable).resolve(), Path(worker_script).resolve(), timeout)
            stream.write(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"); stream.flush()
            print(f"memory rows {index}/{len(rows)}", flush=True)
    return {"rows_written": len(rows), "raw_sha256": _sha256(target)}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _materiality(rows: Sequence[Mapping[str, Any]], memory_rows: Sequence[Mapping[str, Any]], freeze: Mapping[str, Any], hypothesis: str, component: str) -> dict[str, Any]:
    applicable = [row for row in rows if hypothesis in row["hypothesis_scope"]]
    gate = freeze["materiality_gate"]
    accounted = sum(row["profile"]["accounted_self_ns"] for row in applicable)
    component_total = sum(row["profile"]["exclusive_self_ns"][component] for row in applicable)
    shares = [row["profile"]["exclusive_share"][component] for row in applicable]
    cohort_shares = {}
    for cohort in ("main", "ambient_control"):
        selected = [row for row in applicable if row["cohort"] == cohort]
        denominator = sum(row["profile"]["accounted_self_ns"] for row in selected)
        cohort_shares[cohort] = sum(row["profile"]["exclusive_self_ns"][component] for row in selected) / denominator if denominator else 0.0
    peak_excess = []
    for row in memory_rows:
        peak = max(row["memory"]["working_set_task_peak_delta_bytes"], row["memory"]["private_task_peak_delta_bytes"], row["memory"]["tracemalloc_task_peak_delta_bytes"])
        required = max(1, row["required_artifact_bytes"])
        peak_excess.append((peak - required) / required)
    conditions = {
        "minimum_cells": len(applicable) >= gate["minimum_cells"],
        "aggregate_share": (component_total / accounted if accounted else 0.0) >= gate["aggregate_share_min"],
        "median_cell_share": statistics.median(shares) >= gate["median_cell_share_min"] if shares else False,
        "median_exclusive_time": statistics.median(row["profile"]["exclusive_self_ns"][component] for row in applicable) >= gate["median_exclusive_ns_min"] if applicable else False,
        "cell_prevalence": sum(value >= gate["cell_prevalence_share_floor"] for value in shares) / len(shares) >= gate["cell_prevalence_min"] if shares else False,
        "both_cohorts": all(value >= gate["per_cohort_aggregate_share_min"] for value in cohort_shares.values()),
        "allocation_copy_peak_excess": component not in {"allocation", "temporary_copies"} or (bool(peak_excess) and statistics.median(peak_excess) >= gate["allocation_copy_peak_excess_over_output_min"]),
    }
    return {"hypothesis": hypothesis, "component": component, "applicable_cells": len(applicable),
            "aggregate_exclusive_share": component_total / accounted if accounted else 0.0,
            "median_cell_share": statistics.median(shares) if shares else 0.0,
            "median_exclusive_ns": statistics.median(row["profile"]["exclusive_self_ns"][component] for row in applicable) if applicable else 0,
            "cell_prevalence": sum(value >= gate["cell_prevalence_share_floor"] for value in shares) / len(shares) if shares else 0.0,
            "cohort_aggregate_shares": cohort_shares, "conditions": conditions, "passed": all(conditions.values())}


def summarize(profile_path: str | Path, memory_path: str | Path, freeze: Mapping[str, Any]) -> dict[str, Any]:
    profile_file, memory_file = Path(profile_path).resolve(), Path(memory_path).resolve()
    rows, memory_rows = _read_jsonl(profile_file), _read_jsonl(memory_file)
    expected_profile_ids = [f"{occ['occurrence_id']}:{lifecycle}" for occ in freeze["workload"]["occurrences"] for lifecycle in LIFECYCLES]
    expected_memory = list(expected_memory_rows(freeze))
    profile_failures = [row["row_id"] for row in rows if row["status"] != "ok" or not row["exact_oracle_agreement"] or not row["stable_output_order_and_hashes"] or len(row["raw_timing_trials"]) != REPETITIONS]
    memory_failures = [row["row_id"] for row in memory_rows if row["status"] != "ok" or row["child_exit_code"] != 0 or not row["exact_oracle_agreement"] or not row["stable_output_order_and_hashes"] or not row["memory"]["samplers_stopped"] or row["memory"]["execution_sample_count"] < 1]
    pid_failures = []
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in memory_rows: grouped[row["logical_id"]].append(row)
    for key, selected in grouped.items():
        if len(selected) != MEMORY_REPLICATES or len({row["child_pid"] for row in selected}) != MEMORY_REPLICATES: pid_failures.append(key)
    schedule_valid = [row["row_id"] for row in rows] == expected_profile_ids and [row["row_id"] for row in memory_rows] == [row["row_id"] for row in expected_memory]
    materiality = [*[_materiality(rows, memory_rows, freeze, "H2", component) for component in H2_COMPONENTS],
                   *[_materiality(rows, memory_rows, freeze, "H3", component) for component in H3_COMPONENTS]]
    passing = [f"{row['hypothesis']}:{row['component']}" for row in materiality if row["passed"]]
    valid = schedule_valid and not profile_failures and not memory_failures and not pid_failures
    if not valid: decision = "stop_local_measurement_invalid"
    elif len(passing) == 0: decision = "no_go_no_material_component"
    elif len(passing) > 1: decision = "no_go_nonunique_material_components"
    else: decision = "go_one_candidate_eligible_requires_separate_freeze"
    cold = [row for row in rows if row["lifecycle"] == "cold"]
    reused = [row for row in rows if row["lifecycle"] == "reused"]
    core = {
        "schema": SUMMARY_SCHEMA, "freeze_sha256": freeze["freeze_sha256"],
        "profile_raw_sha256": _sha256(profile_file), "memory_raw_sha256": _sha256(memory_file),
        "profile_rows": len(rows), "memory_rows": len(memory_rows), "schedule_valid": schedule_valid,
        "profile_failures": profile_failures, "memory_failures": memory_failures, "fresh_pid_failures": pid_failures,
        "measurement_valid": valid, "materiality": materiality, "passing_components": passing,
        "candidate_eligible": valid and len(passing) == 1, "candidate_tested": False,
        "decision": decision,
        "timing_descriptive": {
            "cold_median_ns": statistics.median(row["median_accounted_total_ns"] for row in cold),
            "reused_median_ns": statistics.median(row["median_accounted_total_ns"] for row in reused),
        },
        "production_status": "unchanged_research_only",
        "production_behavior_changed": False, "runtime_selector_fitted_or_enabled": False,
        "runpod_authorization_request_permitted": False,
        "h2_h3_h6_h9_old_data_reopened": False,
        "environment": {"python": sys.version, "executable": sys.executable, "platform": platform.platform(), "processor": platform.processor()},
    }
    return {**core, "summary_sha256": _digest(core)}


def summary_to_path(profile_path: str | Path, memory_path: str | Path, freeze_path: str | Path, output: str | Path) -> dict[str, Any]:
    freeze = _load(Path(freeze_path)); value = summarize(profile_path, memory_path, freeze)
    _write_new(Path(output), value); return value
