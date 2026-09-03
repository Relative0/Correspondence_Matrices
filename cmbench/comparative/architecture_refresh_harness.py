"""Deterministic local functional admission for the post-C38 comparison refresh.

This module deliberately produces no performance evidence.  It composes the
current exact engines under the four task-matched lanes defined by the C37/C38
architecture review, verifies canonical artifacts, and fails closed before a
fresh corpus or timed campaign is permitted.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from bitset_backend import (
    bitset_to_bool_array,
    build_bitset_env,
    clear_bitset_env_cache,
    clear_words_env_cache,
    eval_cm_node_bitset,
    eval_cm_node_flat,
    eval_cm_node_words,
    eval_expr_bitset,
    eval_expr_flat_bitset,
    eval_expr_flat_cse,
    eval_expr_words_cse,
)
from cm_expr_serde import expr_from_json
from cm_exprlib import eval_expr_tt
from cm_ir import compile_expr_to_cm_ir, materialize_cm, materialize_hybrid_no_reinflate
from cm_normalize import canonical_layout

from . import persistence, tasks
from .contracts import canonical_bytes
from .gf2_multi_root import sibling_output_workloads
from .gf2_multi_root_python import compile_python_multi_root_arena
from .gf2_native_slots import (
    NativeSlotLibrary,
    compile_native_multi_root_arena,
    compile_native_slot_arena,
    load_native_slot_library,
)
from .gf2_restricted_evaluators import (
    compile_restricted_arena,
    eval_restricted_r2,
    prepare_restriction,
)
from .gf2_wide_repeated_queries import (
    oracle_document,
    project_truth_vector,
    projection_indices,
    restrict_full_truth,
    semantic_document,
    semantic_row,
    validate_dataset,
    validate_wide_case,
)


PLAN_SCHEMA = "cm-architecture-refresh-functional-plan/v1"
RESULT_SCHEMA = "cm-architecture-refresh-functional-result/v1"
MULTI_ROOT_SCHEMA = "cm-architecture-refresh-multi-root-output/v1"
QUERY_COUNTS = (1, 4, 16, 64)

LANE_A_ARMS = (
    "cm_dense_full_reinflation",
    "cm_packed_bigint",
    "cm_packed_words",
    "cm_hybrid_no_reinflate",
    "cm_ir_recursive_packed",
    "structural_cse_flat",
    "raw_flat",
    "direct_expression_bitset",
)
LANE_B_BASE_ARMS = (
    "r2_topological_liveness",
    "cm_ir_bigint",
    "cm_ir_words",
    "cse_flat_bigint",
    "cse_flat_words",
    "current_projection",
    "direct_bitset_restriction",
)
LANE_B_NATIVE_ARM = "native_fused_slots"
LANE_C_BASE_ARMS = (
    "python_sharing_union",
    "python_sharing_separate",
)
LANE_C_NATIVE_ARMS = (
    "native_union",
    "native_separate",
)


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class _DeterministicClock:
    """Monotonic test clock that prevents functional runs becoming timings."""

    def __init__(self) -> None:
        self.value = 0

    def __call__(self) -> int:
        self.value += 1
        return self.value


def build_plan(*, native_available: bool) -> dict[str, Any]:
    _require(type(native_available) is bool, "native availability flag")
    lane_b = list(LANE_B_BASE_ARMS)
    lane_c = list(LANE_C_BASE_ARMS)
    if native_available:
        lane_b.append(LANE_B_NATIVE_ARM)
        lane_c.extend(LANE_C_NATIVE_ARMS)
    plan = {
        "schema": PLAN_SCHEMA,
        "role": "local_functional_admission_only",
        "timing_permitted": False,
        "publication_claim_permitted": False,
        "fresh_corpus_permitted": False,
        "prospective_data_permitted": False,
        "selector_fitting_permitted": False,
        "lanes": {
            "A": {
                "task": "complete_explicit_relation",
                "artifact": "uint8_truth_vector_in_declared_variable_order",
                "arms": list(LANE_A_ARMS),
            },
            "B": {
                "task": "repeated_exact_restrictions",
                "artifact": "residual_relation_count_sat_witness_and_digest",
                "query_counts": list(QUERY_COUNTS),
                "arms": lane_b,
            },
            "C": {
                "task": "related_multi_root_outputs",
                "artifact": "ordered_residuals_count_sat_witness_and_digest",
                "arms": lane_c,
            },
            "D": {
                "task": "smaller_query_benefits",
                "sublanes": [*tasks.TASKS, "structural_reload"],
                "task_backends": list(tasks.BACKENDS),
                "task_lifecycles": list(tasks.LIFECYCLES),
                "persistence_backends": list(persistence.BACKENDS),
            },
        },
    }
    validate_plan(plan)
    return plan


def validate_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(plan, Mapping), "functional plan")
    _require(
        set(plan)
        == {
            "schema",
            "role",
            "timing_permitted",
            "publication_claim_permitted",
            "fresh_corpus_permitted",
            "prospective_data_permitted",
            "selector_fitting_permitted",
            "lanes",
        },
        "functional plan fields",
    )
    _require(
        plan["schema"] == PLAN_SCHEMA
        and plan["role"] == "local_functional_admission_only"
        and all(
            plan[field] is False
            for field in (
                "timing_permitted",
                "publication_claim_permitted",
                "fresh_corpus_permitted",
                "prospective_data_permitted",
                "selector_fitting_permitted",
            )
        ),
        "functional plan claim boundary",
    )
    lanes = plan["lanes"]
    _require(isinstance(lanes, Mapping) and set(lanes) == {"A", "B", "C", "D"},
             "four functional lanes required")
    _require(tuple(lanes["A"].get("arms", ())) == LANE_A_ARMS,
             "lane A arm set/order")
    _require(tuple(lanes["B"].get("query_counts", ())) == QUERY_COUNTS,
             "lane B query ladder")
    lane_b = tuple(lanes["B"].get("arms", ()))
    _require(
        lane_b in (LANE_B_BASE_ARMS, (*LANE_B_BASE_ARMS, LANE_B_NATIVE_ARM)),
        "lane B arm set/order",
    )
    lane_c = tuple(lanes["C"].get("arms", ()))
    _require(
        lane_c in (LANE_C_BASE_ARMS, (*LANE_C_BASE_ARMS, *LANE_C_NATIVE_ARMS)),
        "lane C arm set/order",
    )
    _require((LANE_B_NATIVE_ARM in lane_b) == (LANE_C_NATIVE_ARMS[0] in lane_c),
             "native lanes must be admitted together")
    _require(
        tuple(lanes["D"].get("sublanes", ())) == (*tasks.TASKS, "structural_reload")
        and tuple(lanes["D"].get("task_backends", ())) == tasks.BACKENDS
        and tuple(lanes["D"].get("task_lifecycles", ())) == tasks.LIFECYCLES
        and tuple(lanes["D"].get("persistence_backends", ())) == persistence.BACKENDS,
        "lane D task separation",
    )
    return dict(plan)


def find_native_library(project_root: str | Path) -> Path | None:
    root = Path(project_root)
    candidates = (
        root / "build/cm_fused_slots/cm_fused_slots.dll",
        root / "build/cm_fused_slots/Release/cm_fused_slots.dll",
        root
        / "docs/recognition/runs/native-fused-slot-development-20260902-002/native/cm_fused_slots.dll",
    )
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _vector_record(vector: np.ndarray) -> dict[str, Any]:
    normalized = np.asarray(vector, dtype=np.uint8).reshape(-1)
    _require(np.all((normalized == 0) | (normalized == 1)), "non-Boolean truth vector")
    payload = normalized.tobytes()
    witness = int(np.flatnonzero(normalized)[0]) if np.any(normalized) else None
    return {
        "bytes": len(payload),
        "sha256": _sha256_bytes(payload),
        "exact_count": int(normalized.sum()),
        "satisfiable": bool(np.any(normalized)),
        "canonical_witness_row": witness,
    }


def _lane_a(case: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_wide_case(case)
    n_vars = normalized["n_vars"]
    names = tuple(f"x{index}" for index in range(n_vars))
    document = case["expression_v2"]
    oracle = _vector_record(eval_expr_tt(expr_from_json(document), n_vars))
    arms: dict[str, Any] = {}

    for arm in LANE_A_ARMS:
        clear_bitset_env_cache()
        clear_words_env_cache()
        expression = expr_from_json(document)
        vector: np.ndarray
        if arm == "direct_expression_bitset":
            bits = eval_expr_bitset(expression, build_bitset_env(names))
            vector = bitset_to_bool_array(bits, n_vars)
        elif arm == "raw_flat":
            vector = bitset_to_bool_array(
                eval_expr_flat_bitset(expression, names), n_vars)
        elif arm == "structural_cse_flat":
            vector = bitset_to_bool_array(
                eval_expr_flat_cse(expression, names, flatten=True), n_vars)
        else:
            node = compile_expr_to_cm_ir(
                expression,
                reuse_cache=False,
                persistent_cache=False,
                share_aware_flatten=True,
            )
            if arm == "cm_dense_full_reinflation":
                rows, columns = canonical_layout(list(names))
                _require(tuple(rows + columns) == names, "dense CM variable order")
                vector = np.asarray(
                    materialize_cm(node, rows, columns), dtype=np.uint8
                ).reshape(-1)
            elif arm == "cm_packed_bigint":
                vector = bitset_to_bool_array(eval_cm_node_flat(node, names), n_vars)
            elif arm == "cm_packed_words":
                vector = bitset_to_bool_array(eval_cm_node_words(node, names), n_vars)
            elif arm == "cm_ir_recursive_packed":
                vector = bitset_to_bool_array(eval_cm_node_bitset(node, names), n_vars)
            elif arm == "cm_hybrid_no_reinflate":
                result = materialize_hybrid_no_reinflate(
                    node,
                    names,
                    hybrid_threshold=7,
                    allow_reduced_output=False,
                    flat_eval=True,
                )
                _require(tuple(result.output_vars) == names, "hybrid output variable order")
                if result.bits is not None:
                    vector = bitset_to_bool_array(result.bits, n_vars)
                else:
                    _require(result.tt is not None, "hybrid complete output missing")
                    vector = np.asarray(result.tt, dtype=np.uint8).reshape(-1)
            else:  # pragma: no cover - constant arm tuple is exhaustive
                raise AssertionError(arm)
        record = _vector_record(vector)
        _require(record == oracle, f"lane A exact vector mismatch: {arm}")
        arms[arm] = record
    return {
        "case_id": normalized["case_id"],
        "n_vars": n_vars,
        "variable_order": list(names),
        "oracle": oracle,
        "arms": arms,
        "all_exact": True,
    }


def _restriction_outputs(
    case: Mapping[str, Any],
    arm: str,
    trace: Sequence[Mapping[str, Any]],
    native: NativeSlotLibrary | None,
) -> tuple[int, ...]:
    n_vars = case["n_vars"]
    document = case["expression_v2"]
    query_inputs = [
        (
            {row["variable"]: row["value"] for row in query["fixed"]},
            tuple(query["remaining_order"]),
        )
        for query in trace
    ]
    clear_bitset_env_cache()
    clear_words_env_cache()
    if arm == "r2_topological_liveness":
        arena = compile_restricted_arena(document)
        return tuple(
            eval_restricted_r2(arena, prepare_restriction(fixed, remaining))
            for fixed, remaining in query_inputs
        )
    if arm in {
        "cm_ir_bigint",
        "cm_ir_words",
        "cse_flat_bigint",
        "cse_flat_words",
        "direct_bitset_restriction",
    }:
        expression = expr_from_json(document)
        if arm.startswith("cm_ir"):
            node = compile_expr_to_cm_ir(
                expression,
                reuse_cache=False,
                persistent_cache=False,
                share_aware_flatten=True,
            )
            evaluate = eval_cm_node_flat if arm.endswith("bigint") else eval_cm_node_words
            return tuple(evaluate(node, remaining, fixed=fixed)
                         for fixed, remaining in query_inputs)
        if arm == "cse_flat_bigint":
            return tuple(
                eval_expr_flat_cse(expression, remaining, fixed=fixed, flatten=True)
                for fixed, remaining in query_inputs
            )
        if arm == "cse_flat_words":
            return tuple(
                eval_expr_words_cse(expression, remaining, fixed=fixed, flatten=True)
                for fixed, remaining in query_inputs
            )
        return tuple(
            eval_expr_flat_bitset(expression, remaining, fixed=fixed)
            for fixed, remaining in query_inputs
        )
    if arm == "current_projection":
        full = bitset_to_bool_array(int(case["truth_bits_hex"], 16), n_vars)
        return tuple(
            project_truth_vector(full, projection_indices(n_vars, fixed, remaining))
            for fixed, remaining in query_inputs
        )
    if arm == LANE_B_NATIVE_ARM:
        _require(native is not None, "native restriction arm unavailable")
        arena = compile_native_slot_arena(document, native, variable_count=n_vars)
        return tuple(
            arena.evaluate(arena.prepare_bindings(fixed, remaining), len(remaining))
            for fixed, remaining in query_inputs
        )
    raise ValueError("unknown lane B arm")


def _lane_b(
    case: Mapping[str, Any], plan: Mapping[str, Any], native: NativeSlotLibrary | None
) -> dict[str, Any]:
    normalized = validate_wide_case(case)
    arms = tuple(plan["lanes"]["B"]["arms"])
    checkpoints: dict[str, Any] = {}
    full_oracle = oracle_document(case, case["c36_trace"])
    for query_count in QUERY_COUNTS:
        trace = case["c36_trace"][:query_count]
        expected = semantic_document(
            normalized["case_id"], full_oracle["rows"][:query_count]
        )
        expected_digest = _digest(expected)
        records: dict[str, Any] = {}
        for arm in arms:
            outputs = _restriction_outputs(case, arm, trace, native)
            rows = [
                semantic_row(query, int(reduced), normalized["n_vars"])
                for query, reduced in zip(trace, outputs, strict=True)
            ]
            artifact = semantic_document(normalized["case_id"], rows)
            actual_digest = _digest(artifact)
            _require(actual_digest == expected_digest,
                     f"lane B exact artifact mismatch: {arm} q{query_count}")
            records[arm] = {
                "artifact_sha256": actual_digest,
                "artifact_bytes": len(canonical_bytes(artifact)),
                "queries": query_count,
                "exact": True,
            }
        checkpoints[str(query_count)] = {
            "oracle_sha256": expected_digest,
            "arms": records,
            "all_exact": True,
        }
    return {
        "case_id": normalized["case_id"],
        "query_counts": list(QUERY_COUNTS),
        "checkpoints": checkpoints,
        "all_exact": True,
    }


def _multi_root_delivery(
    workload: Any, query: Mapping[str, Any], outputs: Sequence[int]
) -> dict[str, Any]:
    return {
        "query": query["query"],
        "query_sha256": query["query_sha256"],
        "outputs": [
            {
                "output_index": index,
                "semantic": semantic_row(query, int(value), workload.n_vars),
            }
            for index, value in enumerate(outputs)
        ],
    }


def _lane_c(plan: Mapping[str, Any], native: NativeSlotLibrary | None) -> dict[str, Any]:
    workload = sibling_output_workloads()[0]
    names = tuple(f"x{index}" for index in range(workload.n_vars))
    clear_bitset_env_cache()
    full_truths = tuple(
        eval_expr_bitset(root, build_bitset_env(names)) for root in workload.roots
    )
    oracle_rows = []
    for query in workload.trace:
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        values = tuple(
            restrict_full_truth(bits, workload.n_vars, fixed)[1]
            for bits in full_truths
        )
        oracle_rows.append(_multi_root_delivery(workload, query, values))
    oracle = {
        "schema": MULTI_ROOT_SCHEMA,
        "workload_id": workload.workload_id,
        "rows": oracle_rows,
    }
    expected_digest = _digest(oracle)
    union_document = workload.union_document
    separate_documents = workload.separate_documents
    records: dict[str, Any] = {}

    for arm in plan["lanes"]["C"]["arms"]:
        if arm == "python_sharing_union":
            arena = compile_python_multi_root_arena(
                union_document, variable_count=workload.n_vars
            )

            def evaluate(fixed: Mapping[str, int], remaining: Sequence[str]) -> tuple[int, ...]:
                return arena.evaluate(fixed, remaining)

        elif arm == "python_sharing_separate":
            arenas = tuple(
                compile_python_multi_root_arena(
                    document, variable_count=workload.n_vars
                )
                for document in separate_documents
            )

            def evaluate(fixed: Mapping[str, int], remaining: Sequence[str]) -> tuple[int, ...]:
                return tuple(item.evaluate(fixed, remaining)[0] for item in arenas)

        elif arm == "native_union":
            _require(native is not None, "native multi-root arm unavailable")
            native_union = compile_native_multi_root_arena(
                union_document, native, variable_count=workload.n_vars
            )

            def evaluate(fixed: Mapping[str, int], remaining: Sequence[str]) -> tuple[int, ...]:
                bindings = native_union.prepare_bindings(fixed, remaining)
                return native_union.evaluate(bindings, len(remaining))

        elif arm == "native_separate":
            _require(native is not None, "native separate-root arm unavailable")
            native_separate = tuple(
                compile_native_slot_arena(
                    document, native, variable_count=workload.n_vars
                )
                for document in separate_documents
            )

            def evaluate(fixed: Mapping[str, int], remaining: Sequence[str]) -> tuple[int, ...]:
                bindings = native_separate[0].prepare_bindings(fixed, remaining)
                return tuple(
                    item.evaluate(bindings, len(remaining)) for item in native_separate
                )

        else:  # pragma: no cover - validated plan is exhaustive
            raise AssertionError(arm)

        rows = []
        for query in workload.trace:
            fixed = {row["variable"]: row["value"] for row in query["fixed"]}
            remaining = tuple(query["remaining_order"])
            rows.append(_multi_root_delivery(workload, query, evaluate(fixed, remaining)))
        artifact = {
            "schema": MULTI_ROOT_SCHEMA,
            "workload_id": workload.workload_id,
            "rows": rows,
        }
        actual = _digest(artifact)
        _require(actual == expected_digest, f"lane C exact artifact mismatch: {arm}")
        records[arm] = {
            "artifact_sha256": actual,
            "artifact_bytes": len(canonical_bytes(artifact)),
            "queries": len(workload.trace),
            "outputs_per_query": len(workload.roots),
            "exact": True,
        }

    union_nodes = len(union_document["nodes"])
    separate_nodes = sum(len(document["nodes"]) for document in separate_documents)
    return {
        "workload_id": workload.workload_id,
        "n_vars": workload.n_vars,
        "root_count": len(workload.roots),
        "oracle_sha256": expected_digest,
        "structure": {
            "union_unique_nodes": union_nodes,
            "sum_separate_nodes": separate_nodes,
            "avoided_duplicate_nodes": separate_nodes - union_nodes,
        },
        "arms": records,
        "all_exact": True,
    }


def _task_scenario() -> dict[str, Any]:
    return {
        "id": "architecture-refresh-control-k6",
        "k": 6,
        "feature_names": [f"x{index}" for index in range(6)],
        "versions": [
            {"id": "base", "clauses": [[1, -6], [-1, 6]]},
            {"id": "duplicate", "clauses": [[1, -6], [-1, 6], [1, -6]]},
            {"id": "restricted", "clauses": [[1, -6], [-1, 6], [-1]]},
        ],
        "source": {"kind": "synthetic", "purpose": "functional_admission_control"},
    }


_TASK_TRACES: dict[str, list[dict[str, Any]]] = {
    "exact_count": [{"version": 0}, {"version": 1}, {"version": 2}],
    "sat_status": [
        {"version": 0, "assumptions": []},
        {"version": 2, "assumptions": [1]},
    ],
    "witness": [
        {"version": 0, "assumptions": []},
        {"version": 2, "assumptions": [1]},
    ],
    "partial_context": [
        {"version": 0, "assumptions": []},
        {"version": 0, "assumptions": [1]},
        {"version": 2, "assumptions": [1]},
        {"version": 2, "assumptions": []},
    ],
    "version_history": [
        {"version": 0, "assumptions": [-1]},
        {"version": 1, "assumptions": [-1, -6]},
        {"version": 2, "assumptions": [-1]},
        {"version": 0, "assumptions": []},
    ],
    "equivalence_delta": [
        {"before": 0, "after": 1},
        {"before": 1, "after": 2},
        {"before": 2, "after": 0},
    ],
}


class _TinySAT:
    """Bounded independent solver control; never used as performance evidence."""

    def __init__(self) -> None:
        self.clauses: list[list[int]] = []
        self.n = 0

    def add_clause(self, clause: Sequence[int]) -> None:
        self.clauses.append(list(clause))
        self.n = max(self.n, max(map(abs, clause), default=0))

    def solve(self, assumptions: Sequence[int]) -> bool:
        fixed = {abs(literal) - 1: literal > 0 for literal in assumptions}
        free = [index for index in range(self.n) if index not in fixed]
        for bits in range(1 << len(free)):
            values = {
                **fixed,
                **{
                    variable: bool((bits >> offset) & 1)
                    for offset, variable in enumerate(free)
                },
            }
            if all(
                any(values[abs(literal) - 1] == (literal > 0) for literal in clause)
                for clause in self.clauses
            ):
                return True
        return False

    def delete(self) -> None:
        return None


def _lane_d() -> dict[str, Any]:
    scenario = _task_scenario()
    task_records: dict[str, Any] = {}
    for task in tasks.TASKS:
        trace = _TASK_TRACES[task]
        expected = tasks.scalar_oracle(scenario, task, trace)
        expected_digest = tasks.semantic_digest(task, expected)
        arms: dict[str, Any] = {}
        for backend in tasks.BACKENDS:
            for lifecycle in tasks.LIFECYCLES:
                contract = tasks.task_contract(
                    contract_id=f"architecture-refresh-{task}-{backend}-{lifecycle}",
                    task=task,
                    backend=backend,
                    lifecycle=lifecycle,
                    k=scenario["k"],
                    queries=len(trace),
                    expected_sha256=expected_digest,
                )
                result = tasks.execute_task(
                    scenario=scenario,
                    task=task,
                    trace=trace,
                    backend=backend,
                    lifecycle=lifecycle,
                    contract=contract,
                    case_id=scenario["id"],
                    solver_factory=_TinySAT if backend == "sat" else None,
                    native_identity={"simulated": True, "timing_use": False}
                    if backend == "sat"
                    else None,
                    clock=_DeterministicClock(),
                )
                tasks.validate_task_result(
                    result,
                    contract,
                    expected,
                    expected_backend=backend,
                    expected_case_id=scenario["id"],
                )
                arms[f"{backend}/{lifecycle}"] = {
                    "artifact_sha256": result["artifact"]["sha256"],
                    "exact": True,
                }
        task_records[task] = {
            "oracle_sha256": expected_digest,
            "arms": arms,
            "all_exact": True,
        }

    persistence_expected = persistence.scalar_oracle(scenario)
    persistence_semantic = {
        "schema": persistence.SEMANTIC_SCHEMA,
        "task": "structural_reload",
        "rows": persistence_expected,
    }
    persistence_digest = _digest(persistence_semantic)
    persistence_arms: dict[str, Any] = {}
    for backend in persistence.BACKENDS:
        contract = persistence.persistence_contract(
            contract_id=f"architecture-refresh-structural-reload-{backend}",
            backend=backend,
            k=scenario["k"],
            queries=len(scenario["versions"]),
        )
        result = persistence.execute_persistence(
            scenario=scenario,
            backend=backend,
            contract=contract,
            case_id=scenario["id"],
            clock=_DeterministicClock(),
        )
        persistence.validate_persistence_result(
            result,
            contract,
            scenario=scenario,
            expected_rows=persistence_expected,
            expected_backend=backend,
            expected_case_id=scenario["id"],
        )
        _require(
            _digest(result["identity"]["reload_semantics"]) == persistence_digest,
            "lane D persistence semantic mismatch",
        )
        persistence_arms[backend] = {
            "semantic_sha256": persistence_digest,
            "serialized_structure_sha256": result["artifact"]["sha256"],
            "exact": True,
        }
    task_records["structural_reload"] = {
        "oracle_sha256": persistence_digest,
        "arms": persistence_arms,
        "all_exact": True,
    }
    return {"case_id": scenario["id"], "sublanes": task_records, "all_exact": True}


def run_functional_validation(
    dataset: Mapping[str, Any],
    *,
    dataset_sha256: str,
    native_library_path: str | Path | None,
) -> dict[str, Any]:
    _require(
        isinstance(dataset_sha256, str)
        and len(dataset_sha256) == 64
        and all(character in "0123456789abcdef" for character in dataset_sha256),
        "dataset SHA-256",
    )
    validate_dataset(dataset)
    _require(isinstance(dataset.get("cases"), list) and dataset["cases"],
             "functional dataset is empty")
    native = (
        load_native_slot_library(Path(native_library_path))
        if native_library_path is not None
        else None
    )
    if native is not None:
        _require(native.supports_multi_root, "native library lacks multi-root support")
    plan = build_plan(native_available=native is not None)
    case = dataset["cases"][0]
    result = {
        "schema": RESULT_SCHEMA,
        "status": "verified_functional",
        "plan_sha256": _digest(plan),
        "dataset_sha256": dataset_sha256,
        "dataset_role": "exposed_c36_development_regression_only",
        "native_identity": None
        if native is None
        else {
            "sha256": native.sha256,
            "abi_version": native.abi_version,
            "supports_multi_root": native.supports_multi_root,
        },
        "lanes": {
            "A": _lane_a(case),
            "B": _lane_b(case, plan, native),
            "C": _lane_c(plan, native),
            "D": _lane_d(),
        },
        "all_exact": True,
        "timing_evidence_produced": False,
        "performance_claim_permitted": False,
        "fresh_corpus_consumed": False,
        "prospective_data_consumed": False,
        "selector_fitted": False,
        "production_routing_changed": False,
        "next_step_permitted": "freeze_fresh_comparison_contract_only",
    }
    validate_functional_result(result, plan)
    return result


def validate_functional_result(
    result: Mapping[str, Any], plan: Mapping[str, Any]
) -> dict[str, Any]:
    validate_plan(plan)
    _require(isinstance(result, Mapping), "functional result")
    _require(
        set(result)
        == {
            "schema",
            "status",
            "plan_sha256",
            "dataset_sha256",
            "dataset_role",
            "native_identity",
            "lanes",
            "all_exact",
            "timing_evidence_produced",
            "performance_claim_permitted",
            "fresh_corpus_consumed",
            "prospective_data_consumed",
            "selector_fitted",
            "production_routing_changed",
            "next_step_permitted",
        },
        "functional result fields",
    )
    _require(
        result["schema"] == RESULT_SCHEMA
        and result["status"] == "verified_functional"
        and result["plan_sha256"] == _digest(plan)
        and result["dataset_role"] == "exposed_c36_development_regression_only"
        and result["all_exact"] is True
        and result["next_step_permitted"] == "freeze_fresh_comparison_contract_only"
        and all(
            result[field] is False
            for field in (
                "timing_evidence_produced",
                "performance_claim_permitted",
                "fresh_corpus_consumed",
                "prospective_data_consumed",
                "selector_fitted",
                "production_routing_changed",
            )
        ),
        "functional result claim boundary",
    )
    lanes = result["lanes"]
    _require(isinstance(lanes, Mapping) and set(lanes) == {"A", "B", "C", "D"},
             "functional result lanes")
    expected_a = set(plan["lanes"]["A"]["arms"])
    _require(
        lanes["A"].get("all_exact") is True
        and set(lanes["A"].get("arms", {})) == expected_a
        and all(record == lanes["A"]["oracle"] for record in lanes["A"]["arms"].values()),
        "lane A validation",
    )
    expected_b = set(plan["lanes"]["B"]["arms"])
    _require(
        lanes["B"].get("all_exact") is True
        and tuple(lanes["B"].get("query_counts", ())) == QUERY_COUNTS
        and set(lanes["B"].get("checkpoints", {})) == {str(item) for item in QUERY_COUNTS},
        "lane B validation",
    )
    for checkpoint in lanes["B"]["checkpoints"].values():
        _require(
            checkpoint.get("all_exact") is True
            and set(checkpoint.get("arms", {})) == expected_b
            and all(
                row.get("exact") is True
                and row.get("artifact_sha256") == checkpoint["oracle_sha256"]
                for row in checkpoint["arms"].values()
            ),
            "lane B checkpoint validation",
        )
    expected_c = set(plan["lanes"]["C"]["arms"])
    _require(
        lanes["C"].get("all_exact") is True
        and set(lanes["C"].get("arms", {})) == expected_c
        and lanes["C"].get("structure", {}).get("avoided_duplicate_nodes", -1) >= 0
        and all(
            row.get("exact") is True
            and row.get("artifact_sha256") == lanes["C"]["oracle_sha256"]
            for row in lanes["C"]["arms"].values()
        ),
        "lane C validation",
    )
    expected_d = set(plan["lanes"]["D"]["sublanes"])
    _require(
        lanes["D"].get("all_exact") is True
        and set(lanes["D"].get("sublanes", {})) == expected_d
        and all(row.get("all_exact") is True for row in lanes["D"]["sublanes"].values()),
        "lane D validation",
    )
    native_expected = LANE_B_NATIVE_ARM in expected_b
    _require(
        (result["native_identity"] is not None) == native_expected,
        "native result/plan mismatch",
    )
    return dict(result)
