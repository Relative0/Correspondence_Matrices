"""Source-bound four-lane architecture comparison campaign.

The parent freeze selected cases and balanced arm orders without observing new
truths or timings.  This module is the execution layer: it resolves every
frozen identity, builds independent exact oracles, records bounded refusals,
and executes the frozen schedules.  Oracle generation and local smoke runs are
not performance evidence; only ``run_campaign`` emits timed rows.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import gc
import hashlib
import importlib.metadata
import importlib.util
import itertools
import json
import os
from pathlib import Path
import platform
import random
import sys
import time
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
    get_expr_cse_program,
    get_expr_flat_program,
    get_flat_program,
)
from cm_expr_serde import expr_from_json
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor, all_assignments_tt
from cm_ir import compile_expr_to_cm_ir, materialize_cm, materialize_hybrid_no_reinflate
from cm_normalize import canonical_layout

from . import persistence, tasks
from .architecture_comparison_freeze import verify_freeze
from .architecture_refresh_harness import (
    LANE_B_NATIVE_ARM,
    _TASK_TRACES,
    _TinySAT,
    _task_scenario,
)
from .contracts import canonical_bytes
from .gf2_multi_root import MultiRootWorkload, prospective_sibling_output_workloads
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
    project_truth_vector,
    projection_indices,
    semantic_document as restriction_document,
    semantic_row as restriction_row,
)


ORACLE_SCHEMA = "cm-architecture-comparison-oracles/v1"
RAW_SCHEMA = "cm-architecture-comparison-timed-cell/v1"
RESULT_SCHEMA = "cm-architecture-comparison-campaign-result/v1"
MULTI_SCHEMA = "cm-architecture-comparison-multi-root-output/v1"
MAX_COMPLETE_LIVE_VARS = 16
MAX_TASK_VARS = 8
RUNPOD_SAT_VERSION = "1.9.dev15"
QUERY_COUNTS = (1, 4, 16, 64)
STAGES = (
    "parse_normalization_ns",
    "representation_construction_ns",
    "compilation_ns",
    "binding_ns",
    "evaluation_ns",
    "delivery_ns",
    "serialization_ns_when_applicable",
    "cleanup_ns",
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


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        stream.write("\n")


def _rss_bytes() -> int | None:
    if os.name != "nt":
        try:
            import resource
            maximum = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            return maximum if sys.platform == "darwin" else maximum * 1024
        except (ImportError, OSError, ValueError):
            pass
    try:
        import psutil
        return int(psutil.Process().memory_info().rss)
    except (ImportError, OSError):
        return None


def build_query_trace(case_id: str, n_vars: int) -> list[dict[str, Any]]:
    """C36-compatible deterministic q64 trace, extended down to frozen k=8."""
    _require(isinstance(case_id, str) and case_id and 2 <= n_vars <= 16, "trace identity")
    live_widths = (6, 8, 10)
    rows: list[dict[str, Any]] = []
    for query in range(64):
        seed = hashlib.sha256(f"c36:{case_id}:{query}".encode("ascii")).digest()
        live_count = min(n_vars - 1, live_widths[seed[0] % len(live_widths)])
        ordered = sorted(
            range(n_vars), key=lambda index: hashlib.sha256(seed + bytes([index])).digest()
        )
        fixed_indices = set(ordered[: n_vars - live_count])
        fixed = [
            {
                "variable": f"x{index}",
                "value": (seed[1 + offset] >> (index % 8)) & 1,
            }
            for offset, index in enumerate(sorted(fixed_indices))
        ]
        row = {
            "query": query,
            "fixed": fixed,
            "remaining_order": [
                f"x{index}" for index in range(n_vars) if index not in fixed_indices
            ],
        }
        row["query_sha256"] = _digest(row)
        rows.append(row)
    return rows


def _oracle_bits(
    document: Mapping[str, Any], live_names: Sequence[str], fixed: Mapping[str, int]
) -> int:
    """Independent vectorized AST oracle over an explicitly ordered live support."""
    expression = expr_from_json(document)
    names = tuple(live_names)
    _require(len(set(names)) == len(names) <= MAX_COMPLETE_LIVE_VARS, "oracle support")
    assignments = all_assignments_tt(len(names))
    columns = {name: assignments[:, index] for index, name in enumerate(names)}
    constants = {
        name: np.full(1 << len(names), value, dtype=np.uint8)
        for name, value in fixed.items()
    }
    memo: dict[int, np.ndarray] = {}

    def evaluate(node: Expr) -> np.ndarray:
        identity = id(node)
        if identity in memo:
            return memo[identity]
        if isinstance(node, Var):
            name = f"x{node.i}"
            value = columns[name] if name in columns else constants[name]
        elif isinstance(node, Not):
            value = 1 - evaluate(node.a)
        elif isinstance(node, And):
            value = evaluate(node.a) & evaluate(node.b)
        elif isinstance(node, Or):
            value = evaluate(node.a) | evaluate(node.b)
        elif isinstance(node, Xor):
            value = evaluate(node.a) ^ evaluate(node.b)
        elif isinstance(node, Imp):
            value = (1 - evaluate(node.a)) | evaluate(node.b)
        elif isinstance(node, Eqv):
            value = 1 - (evaluate(node.a) ^ evaluate(node.b))
        else:  # pragma: no cover - Expr union is exhaustive
            raise TypeError(node)
        memo[identity] = value
        return value

    packed = np.packbits(evaluate(expression).astype(np.uint8), bitorder="little")
    return int.from_bytes(packed.tobytes(), "little")


def _truth_record(bits: int, n_vars: int) -> dict[str, Any]:
    byte_count = max(1, ((1 << n_vars) + 7) // 8)
    payload = bits.to_bytes(byte_count, "little")
    witness = (bits & -bits).bit_length() - 1 if bits else None
    return {
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "exact_count": bits.bit_count(),
        "satisfiable": bool(bits),
        "canonical_witness_row": witness,
    }


def _eval_expr_bitset_fixed(
    expression: Expr, live_names: Sequence[str], fixed: Mapping[str, int],
    env: Mapping[str, int] | None = None,
) -> int:
    """Identity-memoized direct AST execution with a separate fixed universe."""
    bitset_env = dict(env) if env is not None else build_bitset_env(tuple(live_names))
    full_mask = (1 << (1 << len(live_names))) - 1
    memo: dict[int, int] = {}

    def evaluate(node: Expr) -> int:
        identity = id(node)
        if identity in memo:
            return memo[identity]
        if isinstance(node, Var):
            name = f"x{node.i}"
            value = bitset_env[name] if name in bitset_env else full_mask if fixed[name] else 0
        elif isinstance(node, Not):
            value = (~evaluate(node.a)) & full_mask
        elif isinstance(node, And):
            value = evaluate(node.a) & evaluate(node.b)
        elif isinstance(node, Or):
            value = evaluate(node.a) | evaluate(node.b)
        elif isinstance(node, Xor):
            value = evaluate(node.a) ^ evaluate(node.b)
        elif isinstance(node, Imp):
            value = ((~evaluate(node.a)) | evaluate(node.b)) & full_mask
        elif isinstance(node, Eqv):
            value = (~(evaluate(node.a) ^ evaluate(node.b))) & full_mask
        else:  # pragma: no cover - Expr union is exhaustive
            raise TypeError(node)
        memo[identity] = value
        return value

    return evaluate(expression)


def _public_case(row: Mapping[str, Any]) -> dict[str, Any]:
    support = tuple(row["semantic_support"])
    fixed = {
        f"x{index}": 0
        for index in range(row["nominal_n"])
        if f"x{index}" not in support
    }
    return {
        "case_id": row["id"],
        "family": row["family"],
        "n_vars": len(support),
        "nominal_n": row["nominal_n"],
        "variable_order": list(support),
        "fixed": fixed,
        "expression_v2": row["expression"],
        "source": "public_complete_relation_regression",
    }


def _fresh_case(row: Mapping[str, Any]) -> dict[str, Any]:
    n_vars = row["n_vars"]
    return {
        "case_id": row["case_id"],
        "family": row["family"],
        "n_vars": n_vars,
        "nominal_n": n_vars,
        "variable_order": [f"x{index}" for index in range(n_vars)],
        "fixed": {},
        "expression_v2": row["expression_v2"],
        "source": "fresh_frozen",
    }


def _scenario_trace(scenario: Mapping[str, Any], task: str) -> list[dict[str, Any]]:
    if scenario["id"] == "architecture-refresh-control-k6":
        return [dict(row) for row in _TASK_TRACES[task]]
    versions = len(scenario["versions"])
    k = scenario["k"]
    if task == "exact_count":
        return [{"version": version} for version in range(versions)]
    if task == "equivalence_delta":
        return [
            {"before": version, "after": (version + 1) % versions}
            for version in range(versions)
        ]
    rows = []
    assumption_sets = ([], [1], [-1], [k], [-k])
    for version in range(versions):
        for assumptions in assumption_sets:
            rows.append({"version": version, "assumptions": list(assumptions)})
    return rows


def _bits_to_cnf(bits: int, k: int) -> list[list[int]]:
    """Deterministic bounded CNF from maximal cubes of false assignments."""
    _require(1 <= k <= MAX_TASK_VARS, "CNF adapter width")
    universe = (1 << (1 << k)) - 1
    false_rows = universe ^ bits
    if false_rows == 0:
        return []
    if bits == 0:
        return [[]]
    valid: list[tuple[tuple[int, ...], int]] = []
    for pattern in itertools.product((-1, 0, 1), repeat=k):
        if all(value == -1 for value in pattern):
            continue
        covered = 0
        for assignment in range(1 << k):
            if all(
                value == -1
                or ((assignment >> (k - 1 - index)) & 1) == value
                for index, value in enumerate(pattern)
            ):
                covered |= 1 << assignment
        if covered and covered & ~false_rows == 0:
            valid.append((pattern, covered))
    maximal = []
    for pattern, covered in valid:
        if any(
            other_covered != covered
            and covered & ~other_covered == 0
            and other_covered.bit_count() > covered.bit_count()
            for _, other_covered in valid
        ):
            continue
        maximal.append((pattern, covered))
    uncovered = false_rows
    selected: list[tuple[int, ...]] = []
    while uncovered:
        choices = [
            (-(covered & uncovered).bit_count(), sum(value != -1 for value in pattern), pattern, covered)
            for pattern, covered in maximal
            if covered & uncovered
        ]
        _require(bool(choices), "CNF cube cover stalled")
        _, _, pattern, covered = min(choices)
        selected.append(pattern)
        uncovered &= ~covered
    clauses = [
        [
            -(index + 1) if value == 1 else index + 1
            for index, value in enumerate(pattern)
            if value != -1
        ]
        for pattern in selected
    ]
    _require(len(clauses) <= 128, "CNF adapter exceeds bounded clause contract")
    return clauses


def _history_scenario(row: Mapping[str, Any]) -> dict[str, Any]:
    k = row["n_vars"]
    _require(k <= MAX_TASK_VARS, "history outside bounded task contract")
    names = [f"x{index}" for index in range(k)]
    versions = []
    for version_id, field in (("source", "source_expression_v2"), ("edited", "edited_expression_v2")):
        bits = _oracle_bits(row[field], names, {})
        versions.append({"id": version_id, "clauses": _bits_to_cnf(bits, k)})
    scenario = {
        "id": row["case_id"],
        "k": k,
        "feature_names": names,
        "versions": versions,
        "source": {
            "kind": "synthetic",
            "purpose": "frozen_expression_history_exact_cnf_adapter",
        },
    }
    tasks.sessions.validate_scenario(scenario)
    return scenario


def resolve_catalog(project_root: str | Path, freeze: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(project_root).resolve()
    public_rows = [
        json.loads(line)
        for line in (
            root / freeze["observed_regression_bindings"]
            ["public_complete_relation_regression"]["path"]
        ).read_text(encoding="utf-8").splitlines()
        if line
    ]
    fresh_rows = freeze["fresh_corpus"]["single_root_cases"]
    lane_a = {_public_case(row)["case_id"]: _public_case(row) for row in public_rows}
    lane_a.update({_fresh_case(row)["case_id"]: _fresh_case(row) for row in fresh_rows})

    c36 = _load(
        root / freeze["observed_regression_bindings"]["repeated_restriction_regression"]["path"]
    )
    lane_b = {row["case_id"]: dict(row) for row in c36["cases"]}
    for row in fresh_rows:
        case = _fresh_case(row)
        bits = _oracle_bits(case["expression_v2"], case["variable_order"], {})
        lane_b[case["case_id"]] = {
            **case,
            "truth_bits_hex": format(bits, "x"),
            "c36_trace": build_query_trace(case["case_id"], case["n_vars"]),
        }

    observed_workloads = {row.workload_id: row for row in prospective_sibling_output_workloads()}
    lane_c: dict[str, MultiRootWorkload] = dict(observed_workloads)
    for row in freeze["fresh_corpus"]["multi_root_cases"]:
        lane_c[row["case_id"]] = MultiRootWorkload(
            row["case_id"], row["family"], row["n_vars"],
            tuple(expr_from_json(document) for document in row["separate_documents"]),
        )

    histories = {row["case_id"]: dict(row) for row in freeze["fresh_corpus"]["history_pairs"]}
    lane_d: dict[str, Any] = {"architecture-refresh-control-k6": _task_scenario()}
    for case_id, row in histories.items():
        lane_d[case_id] = (
            _history_scenario(row)
            if row["n_vars"] <= MAX_TASK_VARS
            else {"id": case_id, "k": row["n_vars"], "refusal": "task_width_gt_8"}
        )

    expected = freeze["schedules"]
    _require(set(lane_a) == set(expected["A"]["case_order"]), "lane A resolution")
    _require(set(lane_b) == set(expected["B"]["case_order"]), "lane B resolution")
    _require(set(lane_c) == set(expected["C"]["case_order"]), "lane C resolution")
    _require(set(lane_d) == set(expected["D"]["case_order"]), "lane D resolution")
    return {"A": lane_a, "B": lane_b, "C": lane_c, "D": lane_d}


def _restricted_oracle(case: Mapping[str, Any], query_count: int) -> dict[str, Any]:
    n_vars = case["n_vars"]
    bits = int(case["truth_bits_hex"], 16)
    rows = []
    for query in case["c36_trace"][:query_count]:
        fixed = {item["variable"]: item["value"] for item in query["fixed"]}
        remaining = tuple(query["remaining_order"])
        reduced = _restrict_bits(bits, n_vars, fixed, remaining)
        rows.append(restriction_row(query, reduced, n_vars))
    return restriction_document(case["case_id"], rows)


def _restrict_bits(
    bits: int, n_vars: int, fixed: Mapping[str, int], remaining: Sequence[str]
) -> int:
    remaining_indices = tuple(int(name[1:]) for name in remaining)
    fixed_indices = {int(name[1:]): value for name, value in fixed.items()}
    _require(
        set(remaining_indices).isdisjoint(fixed_indices)
        and set(remaining_indices) | set(fixed_indices) == set(range(n_vars)),
        "restriction partition",
    )
    reduced = 0
    for residual in range(1 << len(remaining_indices)):
        original = 0
        for index in range(n_vars):
            if index in fixed_indices:
                value = fixed_indices[index]
            else:
                position = remaining_indices.index(index)
                value = (residual >> (len(remaining_indices) - 1 - position)) & 1
            original = (original << 1) | value
        reduced |= ((bits >> original) & 1) << residual
    return reduced


def _multi_oracle(workload: MultiRootWorkload) -> dict[str, Any]:
    names = tuple(f"x{index}" for index in range(workload.n_vars))
    full = tuple(_oracle_bits(document, names, {}) for document in workload.separate_documents)
    rows = []
    trace = build_query_trace(workload.workload_id, workload.n_vars)
    for query in trace:
        fixed = {item["variable"]: item["value"] for item in query["fixed"]}
        remaining = tuple(query["remaining_order"])
        outputs = [
            {
                "output_index": index,
                "semantic": restriction_row(
                    query, _restrict_bits(bits, workload.n_vars, fixed, remaining), workload.n_vars
                ),
            }
            for index, bits in enumerate(full)
        ]
        rows.append(
            {"query": query["query"], "query_sha256": query["query_sha256"], "outputs": outputs}
        )
    return {"schema": MULTI_SCHEMA, "workload_id": workload.workload_id, "rows": rows}


def build_oracles(project_root: str | Path, freeze: Mapping[str, Any]) -> dict[str, Any]:
    catalog = resolve_catalog(project_root, freeze)
    lane_a: dict[str, Any] = {}
    for case_id, case in catalog["A"].items():
        if case["n_vars"] > MAX_COMPLETE_LIVE_VARS:
            lane_a[case_id] = {
                "status": "refused",
                "reason": "complete_relation_live_width_gt_16",
                "n_vars": case["n_vars"],
            }
            continue
        bits = _oracle_bits(case["expression_v2"], case["variable_order"], case["fixed"])
        lane_a[case_id] = {"status": "runnable", "truth": _truth_record(bits, case["n_vars"])}

    lane_b = {
        case_id: {
            "status": "runnable",
            "trace_sha256": _digest(case["c36_trace"]),
            "checkpoints": {
                str(count): _digest(_restricted_oracle(case, count)) for count in QUERY_COUNTS
            },
        }
        for case_id, case in catalog["B"].items()
    }
    lane_c = {
        case_id: {
            "status": "runnable",
            "trace_sha256": _digest(build_query_trace(case_id, workload.n_vars)),
            "output_sha256": _digest(_multi_oracle(workload)),
        }
        for case_id, workload in catalog["C"].items()
    }
    lane_d: dict[str, Any] = {}
    for case_id, scenario in catalog["D"].items():
        if "refusal" in scenario:
            lane_d[case_id] = {
                "status": "refused", "reason": scenario["refusal"], "k": scenario["k"]
            }
            continue
        task_rows = {}
        for task in tasks.TASKS:
            trace = _scenario_trace(scenario, task)
            expected = tasks.scalar_oracle(scenario, task, trace)
            task_rows[task] = {
                "trace": trace,
                "output_sha256": tasks.semantic_digest(task, expected),
            }
        persistence_rows = persistence.scalar_oracle(scenario)
        task_rows["structural_reload"] = {
            "trace": [{"version": index} for index in range(len(scenario["versions"]))],
            "output_sha256": _digest(
                {"schema": persistence.SEMANTIC_SCHEMA, "task": "structural_reload", "rows": persistence_rows}
            ),
        }
        lane_d[case_id] = {
            "status": "runnable",
            "scenario_sha256": _digest(scenario),
            "sublanes": task_rows,
        }
    core = {
        "schema": ORACLE_SCHEMA,
        "parent_freeze_sha256": freeze["freeze_sha256"],
        "policy": {
            "complete_relation_max_live_vars": MAX_COMPLETE_LIVE_VARS,
            "smaller_task_max_vars": MAX_TASK_VARS,
            "refused_cases_retained_in_schedule": True,
            "oracle_selection_influence": False,
            "method_timings_observed": False,
        },
        "lanes": {"A": lane_a, "B": lane_b, "C": lane_c, "D": lane_d},
        "timing_evidence_produced": False,
    }
    return {**core, "oracles_sha256": _digest(core)}


def validate_oracles(
    oracles: Mapping[str, Any], project_root: str | Path, freeze: Mapping[str, Any]
) -> dict[str, Any]:
    _require(oracles.get("schema") == ORACLE_SCHEMA, "oracle schema")
    core = {key: oracles[key] for key in oracles if key != "oracles_sha256"}
    _require(oracles.get("oracles_sha256") == _digest(core), "oracle identity")
    replay = build_oracles(project_root, freeze)
    _require(canonical_bytes(replay) == canonical_bytes(oracles), "oracle replay")
    return dict(oracles)


def _stage_timer(clock: Callable[[], int], function: Callable[[], Any]) -> tuple[int, Any]:
    started = clock()
    value = function()
    return max(1, clock() - started), value


def _row(
    *, lane: str, case_id: str, arm: str, status: str, reason: str,
    timings: Mapping[str, int], output_sha256: str | None, output_bytes: int,
    exact: bool, resources: Mapping[str, Any], extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    values = {stage: int(timings.get(stage, 0)) for stage in STAGES}
    values["accounted_total_ns"] = sum(values.values())
    return {
        "schema": RAW_SCHEMA,
        "lane": lane,
        "case_id": case_id,
        "arm": arm,
        "status": status,
        "reason": reason,
        "timings_ns": values,
        "output_sha256": output_sha256,
        "output_bytes": output_bytes,
        "exact_check_passed": exact,
        "peak_rss_bytes": _rss_bytes(),
        "retained_bytes": int(resources.get("retained_bytes", 0)),
        "resources": dict(resources),
        **dict(extra or {}),
    }


def execute_lane_a(
    case: Mapping[str, Any], arm: str, oracle: Mapping[str, Any],
    *, clock: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, Any]:
    if oracle["status"] == "refused":
        return _row(
            lane="A", case_id=case["case_id"], arm=arm, status="refused",
            reason=oracle["reason"], timings={}, output_sha256=None, output_bytes=0,
            exact=False, resources={"n_vars": case["n_vars"]},
        )
    clear_bitset_env_cache()
    clear_words_env_cache()
    timings: dict[str, int] = {}
    timings["parse_normalization_ns"], expression = _stage_timer(
        clock, lambda: expr_from_json(case["expression_v2"])
    )
    node = program = env = layout = None

    def construct() -> None:
        nonlocal node, program
        if arm.startswith("cm_"):
            node = compile_expr_to_cm_ir(
                expression, reuse_cache=False, persistent_cache=False, share_aware_flatten=True
            )
            if arm in {"cm_packed_bigint", "cm_packed_words"}:
                program = get_flat_program(node)
        elif arm == "structural_cse_flat":
            program = get_expr_cse_program(expression, flatten=True)
        elif arm == "raw_flat":
            program = get_expr_flat_program(expression)

    timings["representation_construction_ns"], _ = _stage_timer(clock, construct)
    timings["compilation_ns"] = 0

    def bind() -> None:
        nonlocal env, layout
        if arm == "direct_expression_bitset":
            env = build_bitset_env(case["variable_order"])
        elif arm == "cm_dense_full_reinflation":
            layout = canonical_layout(list(case["variable_order"]))

    timings["binding_ns"], _ = _stage_timer(clock, bind)

    def evaluate() -> int:
        if arm == "direct_expression_bitset":
            return _eval_expr_bitset_fixed(
                expression, case["variable_order"], case["fixed"], env
            )
        if arm == "raw_flat":
            return eval_expr_flat_bitset(expression, case["variable_order"], fixed=case["fixed"])
        if arm == "structural_cse_flat":
            return eval_expr_flat_cse(
                expression, case["variable_order"], fixed=case["fixed"], flatten=True
            )
        if arm == "cm_dense_full_reinflation":
            dense = materialize_cm(node, layout[0], layout[1], fixed=case["fixed"])
            packed = np.packbits(np.asarray(dense, dtype=np.uint8).reshape(-1), bitorder="little")
            return int.from_bytes(packed.tobytes(), "little")
        if arm == "cm_packed_bigint":
            return int(eval_cm_node_flat(node, case["variable_order"], fixed=case["fixed"]))
        if arm == "cm_packed_words":
            return int(eval_cm_node_words(node, case["variable_order"], fixed=case["fixed"]))
        if arm == "cm_ir_recursive_packed":
            return int(eval_cm_node_bitset(node, case["variable_order"], fixed=case["fixed"]))
        if arm == "cm_hybrid_no_reinflate":
            result = materialize_hybrid_no_reinflate(
                node, case["variable_order"], fixed=dict(case["fixed"]),
                hybrid_threshold=7, allow_reduced_output=False, flat_eval=True,
            )
            if result.bits is not None:
                return int(result.bits)
            packed = np.packbits(np.asarray(result.tt, dtype=np.uint8).reshape(-1), bitorder="little")
            return int.from_bytes(packed.tobytes(), "little")
        raise ValueError("unknown lane A arm")

    timings["evaluation_ns"], bits = _stage_timer(clock, evaluate)
    timings["delivery_ns"], record = _stage_timer(clock, lambda: _truth_record(bits, case["n_vars"]))
    timings["serialization_ns_when_applicable"], _ = _stage_timer(clock, lambda: canonical_bytes(record))
    timings["cleanup_ns"], _ = _stage_timer(clock, gc.collect)
    exact = record == oracle["truth"]
    _require(exact, f"lane A oracle mismatch: {case['case_id']} {arm}")
    return _row(
        lane="A", case_id=case["case_id"], arm=arm, status="ok", reason="completed",
        timings=timings, output_sha256=record["sha256"], output_bytes=record["bytes"],
        exact=True, resources={"n_vars": case["n_vars"], "nominal_n": case["nominal_n"]},
    )


def _lane_b_outputs(
    case: Mapping[str, Any], arm: str, native: NativeSlotLibrary | None,
    clock: Callable[[], int],
) -> tuple[dict[str, int], tuple[int, ...], dict[str, Any]]:
    timings: dict[str, int] = {}
    trace = case["c36_trace"]
    timings["parse_normalization_ns"], expression = _stage_timer(
        clock, lambda: expr_from_json(case["expression_v2"])
    )
    arena = node = program = truth_vector = native_arena = None

    def construct() -> None:
        nonlocal arena, node, program, truth_vector, native_arena
        if arm == "r2_topological_liveness":
            arena = compile_restricted_arena(case["expression_v2"])
        elif arm.startswith("cm_ir"):
            node = compile_expr_to_cm_ir(
                expression, reuse_cache=False, persistent_cache=False, share_aware_flatten=True
            )
            program = get_flat_program(node)
        elif arm.startswith("cse_flat"):
            program = get_expr_cse_program(expression, flatten=True)
        elif arm == "current_projection":
            names = tuple(f"x{index}" for index in range(case["n_vars"]))
            truth_vector = bitset_to_bool_array(
                eval_expr_bitset(expression, build_bitset_env(names)), case["n_vars"]
            )
        elif arm == LANE_B_NATIVE_ARM:
            _require(native is not None, "native lane B arm unavailable")
            native_arena = compile_native_slot_arena(
                case["expression_v2"], native, variable_count=case["n_vars"]
            )

    timings["representation_construction_ns"], _ = _stage_timer(clock, construct)
    timings["compilation_ns"] = 0
    query_inputs: list[tuple[dict[str, int], tuple[str, ...]]] = []
    plans: list[Any] = []

    def bind() -> None:
        for query in trace:
            fixed = {item["variable"]: item["value"] for item in query["fixed"]}
            remaining = tuple(query["remaining_order"])
            query_inputs.append((fixed, remaining))
            if arm == "r2_topological_liveness":
                plans.append(prepare_restriction(fixed, remaining))
            elif arm == "current_projection":
                plans.append(projection_indices(case["n_vars"], fixed, remaining))
            elif arm == LANE_B_NATIVE_ARM:
                plans.append(native_arena.prepare_bindings(fixed, remaining))

    timings["binding_ns"], _ = _stage_timer(clock, bind)

    def evaluate() -> tuple[int, ...]:
        if arm == "r2_topological_liveness":
            return tuple(eval_restricted_r2(arena, plan) for plan in plans)
        if arm == "cm_ir_bigint":
            return tuple(eval_cm_node_flat(node, remaining, fixed=fixed) for fixed, remaining in query_inputs)
        if arm == "cm_ir_words":
            return tuple(eval_cm_node_words(node, remaining, fixed=fixed) for fixed, remaining in query_inputs)
        if arm == "cse_flat_bigint":
            return tuple(eval_expr_flat_cse(expression, remaining, fixed=fixed, flatten=True) for fixed, remaining in query_inputs)
        if arm == "cse_flat_words":
            return tuple(eval_expr_words_cse(expression, remaining, fixed=fixed, flatten=True) for fixed, remaining in query_inputs)
        if arm == "current_projection":
            return tuple(project_truth_vector(truth_vector, plan) for plan in plans)
        if arm == "direct_bitset_restriction":
            return tuple(eval_expr_flat_bitset(expression, remaining, fixed=fixed) for fixed, remaining in query_inputs)
        if arm == LANE_B_NATIVE_ARM:
            return tuple(native_arena.evaluate(plan, len(remaining)) for plan, (_, remaining) in zip(plans, query_inputs, strict=True))
        raise ValueError("unknown lane B arm")

    timings["evaluation_ns"], outputs = _stage_timer(clock, evaluate)
    resources = {
        "n_vars": case["n_vars"],
        "queries": len(trace),
        "retained_bytes": 0,
    }
    return timings, tuple(int(value) for value in outputs), resources


def execute_lane_b(
    case: Mapping[str, Any], arm: str, oracle: Mapping[str, Any],
    native: NativeSlotLibrary | None, *, clock: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, Any]:
    clear_bitset_env_cache()
    clear_words_env_cache()
    timings, outputs, resources = _lane_b_outputs(case, arm, native, clock)

    def deliver() -> tuple[dict[str, Any], dict[str, str]]:
        rows = [
            restriction_row(query, output, case["n_vars"])
            for query, output in zip(case["c36_trace"], outputs, strict=True)
        ]
        documents = {
            str(count): restriction_document(case["case_id"], rows[:count])
            for count in QUERY_COUNTS
        }
        return documents["64"], {key: _digest(value) for key, value in documents.items()}

    timings["delivery_ns"], (document, checkpoints) = _stage_timer(clock, deliver)
    _require(checkpoints == oracle["checkpoints"], f"lane B oracle mismatch: {case['case_id']} {arm}")
    timings["serialization_ns_when_applicable"], payload = _stage_timer(
        clock, lambda: canonical_bytes(document)
    )
    timings["cleanup_ns"], _ = _stage_timer(clock, gc.collect)
    return _row(
        lane="B", case_id=case["case_id"], arm=arm, status="ok", reason="completed",
        timings=timings, output_sha256=checkpoints["64"], output_bytes=len(payload),
        exact=True, resources=resources, extra={"checkpoint_output_sha256": checkpoints},
    )


def execute_lane_c(
    workload: MultiRootWorkload, arm: str, oracle: Mapping[str, Any],
    native: NativeSlotLibrary | None, *, clock: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, Any]:
    clear_bitset_env_cache()
    clear_words_env_cache()
    timings: dict[str, int] = {}
    timings["parse_normalization_ns"], documents = _stage_timer(
        clock, lambda: (workload.union_document, workload.separate_documents)
    )
    evaluator: Callable[[Mapping[str, int], Sequence[str]], tuple[int, ...]] | None
    native_arena = None
    native_arenas: tuple[Any, ...] = ()

    def construct() -> Callable[[Mapping[str, int], Sequence[str]], tuple[int, ...]] | None:
        nonlocal native_arena, native_arenas
        if arm == "python_sharing_union":
            arena = compile_python_multi_root_arena(documents[0], variable_count=workload.n_vars)
            return lambda fixed, remaining: arena.evaluate(fixed, remaining)
        if arm == "python_sharing_separate":
            arenas = tuple(
                compile_python_multi_root_arena(document, variable_count=workload.n_vars)
                for document in documents[1]
            )
            return lambda fixed, remaining: tuple(
                arena.evaluate(fixed, remaining)[0] for arena in arenas
            )
        if arm == "native_union":
            _require(native is not None, "native lane C arm unavailable")
            native_arena = compile_native_multi_root_arena(
                documents[0], native, variable_count=workload.n_vars
            )
            return None
        if arm == "native_separate":
            _require(native is not None, "native lane C arm unavailable")
            native_arenas = tuple(
                compile_native_slot_arena(document, native, variable_count=workload.n_vars)
                for document in documents[1]
            )
            return None
        raise ValueError("unknown lane C arm")

    timings["representation_construction_ns"], evaluator = _stage_timer(clock, construct)
    timings["compilation_ns"] = 0
    trace = build_query_trace(workload.workload_id, workload.n_vars)
    query_inputs: list[tuple[dict[str, int], tuple[str, ...]]] = []
    native_bindings: list[Any] = []

    def bind() -> None:
        for query in trace:
            fixed = {item["variable"]: item["value"] for item in query["fixed"]}
            remaining = tuple(query["remaining_order"])
            query_inputs.append((fixed, remaining))
            if arm == "native_union":
                native_bindings.append(native_arena.prepare_bindings(fixed, remaining))
            elif arm == "native_separate":
                native_bindings.append(native_arenas[0].prepare_bindings(fixed, remaining))

    timings["binding_ns"], _ = _stage_timer(clock, bind)

    def evaluate_all() -> tuple[tuple[int, ...], ...]:
        if arm == "native_union":
            return tuple(
                native_arena.evaluate(plan, len(remaining))
                for plan, (_, remaining) in zip(native_bindings, query_inputs, strict=True)
            )
        if arm == "native_separate":
            return tuple(
                tuple(current.evaluate(plan, len(remaining)) for current in native_arenas)
                for plan, (_, remaining) in zip(native_bindings, query_inputs, strict=True)
            )
        _require(evaluator is not None, "lane C evaluator unavailable")
        return tuple(evaluator(fixed, remaining) for fixed, remaining in query_inputs)

    timings["evaluation_ns"], values = _stage_timer(
        clock, evaluate_all
    )

    def deliver() -> dict[str, Any]:
        rows = []
        for query, outputs in zip(trace, values, strict=True):
            rows.append({
                "query": query["query"],
                "query_sha256": query["query_sha256"],
                "outputs": [
                    {
                        "output_index": index,
                        "semantic": restriction_row(query, int(value), workload.n_vars),
                    }
                    for index, value in enumerate(outputs)
                ],
            })
        return {"schema": MULTI_SCHEMA, "workload_id": workload.workload_id, "rows": rows}

    timings["delivery_ns"], document = _stage_timer(clock, deliver)
    actual = _digest(document)
    _require(actual == oracle["output_sha256"], f"lane C oracle mismatch: {workload.workload_id} {arm}")
    timings["serialization_ns_when_applicable"], payload = _stage_timer(clock, lambda: canonical_bytes(document))
    timings["cleanup_ns"], _ = _stage_timer(clock, gc.collect)
    return _row(
        lane="C", case_id=workload.workload_id, arm=arm, status="ok", reason="completed",
        timings=timings, output_sha256=actual, output_bytes=len(payload), exact=True,
        resources={
            "n_vars": workload.n_vars,
            "roots": len(workload.roots),
            "union_nodes": len(documents[0]["nodes"]),
            "sum_separate_nodes": sum(len(document["nodes"]) for document in documents[1]),
        },
    )


def execute_lane_d(
    scenario: Mapping[str, Any], sublane: str, arm: str, oracle: Mapping[str, Any],
    *, clock: Callable[[], int] = time.perf_counter_ns,
    functional_sat: bool = False,
) -> dict[str, Any]:
    case_id = scenario["id"]
    if oracle["status"] == "refused":
        return _row(
            lane="D", case_id=case_id, arm=arm, status="refused", reason=oracle["reason"],
            timings={}, output_sha256=None, output_bytes=0, exact=False,
            resources={"k": oracle["k"]}, extra={"sublane": sublane},
        )
    target = oracle["sublanes"][sublane]
    if sublane == "structural_reload":
        contract = persistence.persistence_contract(
            contract_id=f"architecture-comparison:{case_id}:{sublane}:{arm}",
            backend=arm, k=scenario["k"], queries=len(scenario["versions"]),
        )
        result = persistence.execute_persistence(
            scenario=scenario, backend=arm, contract=contract, case_id=case_id, clock=clock
        )
        expected = persistence.scalar_oracle(scenario)
        persistence.validate_persistence_result(
            result, contract, scenario=scenario, expected_rows=expected,
            expected_backend=arm, expected_case_id=case_id,
        )
        actual = _digest(result["identity"]["reload_semantics"])
        _require(actual == target["output_sha256"], "lane D persistence oracle mismatch")
        task_ns = int(result["timings_ns"]["task_total_ns"])
        timings = {"evaluation_ns": task_ns}
        output_bytes = int(result["artifact"]["bytes"])
        resources = {
            "k": scenario["k"],
            "counters": result["identity"]["counters"],
            "native_identity": result["identity"].get("native_identity"),
        }
    else:
        backend, lifecycle = arm.split("/", 1)
        trace = target["trace"]
        contract = tasks.task_contract(
            contract_id=f"architecture-comparison:{case_id}:{sublane}:{arm}",
            task=sublane, backend=backend, lifecycle=lifecycle, k=scenario["k"],
            queries=len(trace), expected_sha256=target["output_sha256"],
        )
        solver_factory = None
        native_identity = None
        if backend == "sat" and functional_sat:
            solver_factory = _TinySAT
            native_identity = {"simulated": True, "timing_use": False}
        elif backend == "sat":
            _require(
                importlib.metadata.version("python-sat") == RUNPOD_SAT_VERSION,
                "frozen RunPod SAT distribution version unavailable",
            )
            extension = importlib.util.find_spec("pysolvers")
            _require(extension is not None and extension.origin, "pysolvers extension unavailable")
            extension_path = Path(extension.origin).resolve()
            from pysat.solvers import Cadical195
            solver_factory = Cadical195
            native_identity = {
                "distribution": "python-sat",
                "version": RUNPOD_SAT_VERSION,
                "adapter": "pysat.Cadical195",
                "binding_file": extension_path.name,
                "binding_bytes": extension_path.stat().st_size,
                "binding_sha256": _sha256(extension_path),
            }
        result = tasks.execute_task(
            scenario=scenario, task=sublane, trace=trace, backend=backend,
            lifecycle=lifecycle, contract=contract, case_id=case_id,
            solver_factory=solver_factory,
            native_identity=native_identity,
            clock=clock,
        )
        expected = tasks.scalar_oracle(scenario, sublane, trace)
        tasks.validate_task_result(
            result, contract, expected, expected_backend=backend, expected_case_id=case_id
        )
        actual = result["artifact"]["sha256"]
        _require(actual == target["output_sha256"], "lane D task oracle mismatch")
        timings = {"evaluation_ns": int(result["timings_ns"]["task_total_ns"])}
        output_bytes = int(result["artifact"]["bytes"])
        resources = {
            "k": scenario["k"],
            "counters": result["identity"]["counters"],
            "native_identity": result["identity"].get("native_identity"),
        }
    return _row(
        lane="D", case_id=case_id, arm=arm, status="ok", reason="completed",
        timings=timings, output_sha256=actual, output_bytes=output_bytes, exact=True,
        resources=resources, extra={"sublane": sublane},
    )


class _DeterministicClock:
    def __init__(self) -> None:
        self.value = 0

    def __call__(self) -> int:
        self.value += 1
        return self.value


def functional_smoke(
    project_root: str | Path, freeze: Mapping[str, Any], oracles: Mapping[str, Any],
    native_library_path: str | Path,
) -> dict[str, Any]:
    """Exercise every arm once with a synthetic clock; emit no timing evidence."""
    catalog = resolve_catalog(project_root, freeze)
    native = load_native_slot_library(Path(native_library_path))
    selections: dict[str, Any] = {}
    a_id = next(case_id for case_id in freeze["schedules"]["A"]["case_order"] if oracles["lanes"]["A"][case_id]["status"] == "runnable" and catalog["A"][case_id]["n_vars"] == 8)
    selections["A"] = [
        execute_lane_a(catalog["A"][a_id], arm, oracles["lanes"]["A"][a_id], clock=_DeterministicClock())
        for arm in freeze["schedules"]["A"]["arms"]
    ]
    b_id = next(case_id for case_id in freeze["schedules"]["B"]["case_order"] if catalog["B"][case_id]["n_vars"] == 8)
    selections["B"] = [
        execute_lane_b(catalog["B"][b_id], arm, oracles["lanes"]["B"][b_id], native, clock=_DeterministicClock())
        for arm in freeze["schedules"]["B"]["arms"]
    ]
    c_id = next(case_id for case_id in freeze["schedules"]["C"]["case_order"] if catalog["C"][case_id].n_vars == 8)
    selections["C"] = [
        execute_lane_c(catalog["C"][c_id], arm, oracles["lanes"]["C"][c_id], native, clock=_DeterministicClock())
        for arm in freeze["schedules"]["C"]["arms"]
    ]
    d_id = "architecture-refresh-control-k6"
    selections["D"] = []
    for sublane, schedule in freeze["schedules"]["D"]["task_sublanes"].items():
        for backend in schedule["arms"]:
            for lifecycle in freeze["schedules"]["D"]["task_lifecycles"]:
                selections["D"].append(execute_lane_d(
                    catalog["D"][d_id], sublane, f"{backend}/{lifecycle}",
                    oracles["lanes"]["D"][d_id], clock=_DeterministicClock(), functional_sat=True,
                ))
    for backend in freeze["schedules"]["D"]["structural_reload"]["arms"]:
        selections["D"].append(execute_lane_d(
            catalog["D"][d_id], "structural_reload", backend,
            oracles["lanes"]["D"][d_id], clock=_DeterministicClock(),
        ))
    rows = sum((list(value) for value in selections.values()), [])
    _require(all(row["status"] == "ok" and row["exact_check_passed"] for row in rows), "functional smoke")
    return {
        "schema": "cm-architecture-comparison-functional-smoke/v1",
        "status": "pass",
        "parent_freeze_sha256": freeze["freeze_sha256"],
        "oracles_sha256": oracles["oracles_sha256"],
        "native_library_sha256": native.sha256,
        "rows_checked": len(rows),
        "rows_by_lane": {lane: len(value) for lane, value in selections.items()},
        "timing_evidence_produced": False,
        "synthetic_clock_used": True,
        "all_exact": True,
    }


def _environment() -> dict[str, Any]:
    return {
        "python": sys.version,
        "python_executable": sys.executable,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "processor": platform.processor(),
    }


def run_campaign(
    *, project_root: str | Path, freeze_path: str | Path, oracles_path: str | Path,
    native_library_path: str | Path, output_dir: str | Path, max_seconds: float = 1200.0,
) -> dict[str, Any]:
    """Run the complete frozen schedule.  The caller must enforce authorization."""
    root = Path(project_root).resolve()
    output = Path(output_dir).resolve()
    _require(output.is_relative_to(root) and not output.exists(), "new in-project output required")
    freeze = _load(Path(freeze_path))
    verify_freeze(freeze, root)
    oracles = _load(Path(oracles_path))
    validate_oracles(oracles, root, freeze)
    native = load_native_slot_library(Path(native_library_path))
    catalog = resolve_catalog(root, freeze)
    output.mkdir(parents=True)
    raw_path = output / "raw_measurements.jsonl"
    counts = {"ok": 0, "refused": 0, "failed": 0}
    lane_counts = {lane: 0 for lane in "ABCD"}
    started = time.perf_counter()

    def emit(row: dict[str, Any], stream: Any, extra: Mapping[str, Any]) -> None:
        row.update(extra)
        stream.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        lane_counts[row["lane"]] += 1

    with raw_path.open("x", encoding="utf-8", newline="\n") as stream:
        for lane in "ABC":
            schedule = freeze["schedules"][lane]
            for block, order in enumerate(schedule["arm_orders"]):
                for case_position, case_id in enumerate(schedule["case_order"]):
                    for arm_position, arm in enumerate(order):
                        if time.perf_counter() - started > max_seconds:
                            raise TimeoutError("architecture comparison exceeded wall bound")
                        if lane == "A":
                            row = execute_lane_a(catalog[lane][case_id], arm, oracles["lanes"][lane][case_id])
                        elif lane == "B":
                            row = execute_lane_b(catalog[lane][case_id], arm, oracles["lanes"][lane][case_id], native)
                        else:
                            row = execute_lane_c(catalog[lane][case_id], arm, oracles["lanes"][lane][case_id], native)
                        emit(row, stream, {
                            "block": block, "case_position": case_position,
                            "arm_position": arm_position, "arm_order": list(order),
                        })
        lane = "D"
        for sublane, schedule in freeze["schedules"][lane]["task_sublanes"].items():
            for block, order in enumerate(schedule["arm_orders"]):
                for case_position, case_id in enumerate(schedule["case_order"]):
                    for backend_position, backend in enumerate(order):
                        if time.perf_counter() - started > max_seconds:
                            raise TimeoutError("architecture comparison exceeded wall bound")
                        # Eight counterbalance blocks give every backend four
                        # observations under each lifecycle without doubling
                        # the parent's frozen planned-cell count.
                        lifecycle = freeze["schedules"][lane]["task_lifecycles"][block % 2]
                        arm = f"{backend}/{lifecycle}"
                        row = execute_lane_d(
                            catalog[lane][case_id], sublane, arm, oracles["lanes"][lane][case_id]
                        )
                        emit(row, stream, {
                            "block": block, "case_position": case_position,
                            "arm_position": backend_position, "arm_order": list(order),
                            "lifecycle_assignment": "block_parity_balanced",
                        })
        schedule = freeze["schedules"][lane]["structural_reload"]
        for block, order in enumerate(schedule["arm_orders"]):
            for case_position, case_id in enumerate(schedule["case_order"]):
                for arm_position, arm in enumerate(order):
                    row = execute_lane_d(
                        catalog[lane][case_id], "structural_reload", arm,
                        oracles["lanes"][lane][case_id],
                    )
                    emit(row, stream, {
                        "block": block, "case_position": case_position,
                        "arm_position": arm_position, "arm_order": list(order),
                    })
    expected = sum(
        freeze["schedules"][lane]["planned_cells"] for lane in "ABC"
    ) + sum(
        schedule["planned_cells"]
        for schedule in freeze["schedules"]["D"]["task_sublanes"].values()
    ) + freeze["schedules"]["D"]["structural_reload"]["planned_cells"]
    _require(sum(counts.values()) == expected, "campaign cell cardinality")
    result = {
        "schema": RESULT_SCHEMA,
        "status": "complete",
        "freeze_sha256": _sha256(Path(freeze_path)),
        "parent_freeze_canonical_sha256": freeze["freeze_sha256"],
        "oracles_file_sha256": _sha256(Path(oracles_path)),
        "oracles_canonical_sha256": oracles["oracles_sha256"],
        "native_library_sha256": native.sha256,
        "counts": counts,
        "lane_rows": lane_counts,
        "expected_rows": expected,
        "raw_measurements_sha256": _sha256(raw_path),
        "elapsed_seconds": time.perf_counter() - started,
        "environment": _environment(),
        "decision": {
            "performance_interpretation_deferred_to_independent_verifier": True,
            "selector_fitted": False,
            "neural_training": False,
            "production_routing_changed": False,
            "website_updated": False,
        },
    }
    _write_json(output / "results.json", result)
    return result
