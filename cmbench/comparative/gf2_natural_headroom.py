"""C34 task-matched natural-workload adapters and corpus bindings.

The complete-relation table starts from one frozen expression-DAG document and
delivers one canonical packed truth vector.  The decomposition table starts
from that same document and delivers the deterministic best exact CM/GF(2)
artifact over the *complete* A|B partition universe.  Method-specific parsing,
compilation, execution, delivery, cleanup, and internal exact checks are
charged; the independent semantic oracle remains outside comparative timing.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import time
from collections import Counter
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from bitset_backend import (
    PreparedFlatEvaluation,
    _bind_flat_program,
    build_bitset_env,
    compile_expr_cse,
    eval_expr_bitset,
    get_flat_program,
    program_metrics,
)
from cm_expr_serde import expr_from_json
from cm_ir import compile_expr_to_cm_ir

from cmbench.recognition.gf2_decomposition import (
    ExactGF2Artifact,
    analyze_screened_exact_gf2,
    truth_sha256,
)
from cmbench.recognition.source_anf_hybrid import (
    packed_truth_bits,
    source_anf_packed,
)

from .arms import semantic_sha256
from .contracts import (
    CONTRACT_SCHEMA,
    RESULT_SCHEMA,
    canonical_bytes,
    contract_digest,
    validate_contract,
    validate_result,
)
from .gf2_decomposition import decomposition_contract, delivered_document, delivered_sha256
from .ir import cm_ir_stats


DATASET_SCHEMA = "crse-c34-natural-headroom-dataset/v1"
SOURCE_DATASET_SCHEMA = "crse-c23-yosys-unused-generator-gf2-dataset/v1"
TRUTH_METHODS = (
    "direct_ast_bitset",
    "plain_cse_bigint",
    "flattened_cse_bigint",
    "cm_ir_bigint",
    "source_packed_anf",
    "cadical_assignment_enumeration",
)
DECOMPOSITION_METHODS = (
    "flattened_cse_complete_screened",
    "cm_ir_complete_screened",
    "source_packed_anf_complete_screened",
)
DECOMPOSITION_TRUTH_METHOD = {
    "flattened_cse_complete_screened": "flattened_cse_bigint",
    "cm_ir_complete_screened": "cm_ir_bigint",
    "source_packed_anf_complete_screened": "source_packed_anf",
}
TRUTH_TIMING_FIELDS = (
    "input_decode_ns",
    "representation_ns",
    "compile_ns",
    "execute_ns",
    "deliver_ns",
    "cleanup_ns",
)
DECOMPOSITION_TIMING_FIELDS = (
    *TRUTH_TIMING_FIELDS,
    "partition_plan_ns",
    "completion_ns",
    "exact_check_ns",
    "artifact_deliver_ns",
    "wrapper_ns",
)


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage(clock: Callable[[], int], function: Callable[[], Any]) -> tuple[Any, int]:
    started = clock()
    value = function()
    elapsed = clock() - started
    _require(type(elapsed) is int and elapsed >= 0, "nonmonotonic C34 clock")
    return value, max(1, elapsed)


def _expression_sha256(document: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(document)).hexdigest()


def validate_natural_case(case: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(case, Mapping), "C34 case must be an object")
    required = {
        "case_id", "cluster_id", "family", "n_vars", "truth_bits_hex",
        "truth_sha256", "expression_v2", "expression_v2_sha256",
        "selection_sha256",
    }
    _require(required.issubset(case), "C34 case fields")
    n_vars = case["n_vars"]
    _require(type(n_vars) is int and 3 <= n_vars <= 10, "C34 width must be 3..10")
    _require(all(isinstance(case[key], str) and case[key] for key in
                 ("case_id", "cluster_id", "family", "truth_bits_hex",
                  "truth_sha256", "expression_v2_sha256", "selection_sha256")),
             "invalid C34 case identity")
    bits = int(case["truth_bits_hex"], 16)
    _require(truth_sha256(bits, n_vars) == case["truth_sha256"], "C34 truth identity")
    _require(isinstance(case["expression_v2"], Mapping)
             and _expression_sha256(case["expression_v2"]) == case["expression_v2_sha256"],
             "C34 expression identity")
    return {"case_id": case["case_id"], "n_vars": n_vars, "bits": bits}


def select_decomposition_case_ids(cases: list[dict[str, Any]]) -> tuple[str, ...]:
    """Select at most two source-parameter identities per width, before timing."""
    selected: list[str] = []
    widths = sorted({validate_natural_case(case)["n_vars"] for case in cases})
    for n_vars in widths:
        group = sorted(
            (case for case in cases if case["n_vars"] == n_vars),
            key=lambda case: (case["selection_sha256"], case["case_id"]),
        )
        _require(group, "empty C34 width stratum")
        first = group[0]
        chosen = [first]
        different = next((case for case in group[1:] if case["family"] != first["family"]), None)
        if different is not None:
            chosen.append(different)
        elif len(group) > 1:
            chosen.append(group[1])
        selected.extend(case["case_id"] for case in chosen)
    return tuple(selected)


def build_dataset_manifest(
    source_path: Path,
    source_verification_path: Path,
    *,
    source_relative: str,
    verification_relative: str,
) -> dict[str, Any]:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    verification = json.loads(source_verification_path.read_text(encoding="utf-8"))
    _require(source.get("schema") == SOURCE_DATASET_SCHEMA and source.get("status") == "frozen",
             "C34 source dataset changed")
    cases = source.get("cases")
    _require(isinstance(cases, list) and len(cases) == 48, "C34 requires the frozen 48-case source")
    _require(verification.get("status") == "verified"
             and verification.get("cases_replayed") == len(cases)
             and verification.get("timing_based_selection") is False,
             "C34 source verification changed")
    for case in cases:
        validate_natural_case(case)
    decomposition = set(select_decomposition_case_ids(cases))
    rows = [{
        "case_id": case["case_id"],
        "cluster_id": case["cluster_id"],
        "family": case["family"],
        "n_vars": case["n_vars"],
        "truth_sha256": case["truth_sha256"],
        "expression_v2_sha256": case["expression_v2_sha256"],
        "selection_sha256": case["selection_sha256"],
        "complete_relation_role": True,
        "decomposition_role": case["case_id"] in decomposition,
        "fresh_confirmation": False,
        "prior_usage": "c23_v1_previously_inspected_incomplete_decomposition_contract",
    } for case in sorted(cases, key=lambda item: item["case_id"])]
    by_width = Counter(row["n_vars"] for row in rows)
    decomposition_by_width = Counter(row["n_vars"] for row in rows if row["decomposition_role"])
    manifest = {
        "schema": DATASET_SCHEMA,
        "status": "frozen",
        "source": {
            "path": source_relative,
            "sha256": _sha256(source_path),
            "schema": source["schema"],
            "verification_path": verification_relative,
            "verification_sha256": _sha256(source_verification_path),
        },
        "selection": {
            "frozen_before_c34_timing": True,
            "timing_or_method_output_used": False,
            "training_use": False,
            "policy_selection_use": False,
            "complete_relation": "all 48 already frozen C23-v1 cases",
            "decomposition": (
                "per width, lowest source-parameter selection identity plus lowest identity "
                "from a different family when available; at most two"
            ),
            "fresh_confirmation": False,
            "evidence_role": "previously inspected natural-corpus width extension",
        },
        "counts": {
            "cases": len(rows),
            "families": len({row["family"] for row in rows}),
            "by_n_vars": {str(key): by_width[key] for key in sorted(by_width)},
            "decomposition_cases": len(decomposition),
            "decomposition_by_n_vars": {
                str(key): decomposition_by_width[key] for key in sorted(decomposition_by_width)
            },
        },
        "cases": rows,
        "provenance": {
            "source_repository": source["provenance"]["source_repository"],
            "source_commit": source["provenance"]["source_commit"],
            "source_inventory": source["provenance"]["source_inventory"],
            "source_inventory_sha256": source["provenance"]["source_inventory_sha256"],
            "network_used": False,
            "source_dataset_reused": True,
            "truth_overlap_exclusion_inherited": True,
        },
    }
    validate_dataset_manifest(manifest, source)
    return manifest


def validate_dataset_manifest(
    manifest: Mapping[str, Any], source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _require(isinstance(manifest, Mapping) and manifest.get("schema") == DATASET_SCHEMA
             and manifest.get("status") == "frozen", "C34 dataset schema/status")
    rows = manifest.get("cases")
    _require(isinstance(rows, list) and len(rows) == 48
             and len({row.get("case_id") for row in rows}) == 48, "C34 manifest cases")
    _require(set(manifest.get("counts", {}).get("by_n_vars", {})) == {str(i) for i in range(3, 11)},
             "C34 width coverage")
    decomposition = [row for row in rows if row.get("decomposition_role") is True]
    _require(len(decomposition) == 15
             and Counter(row["n_vars"] for row in decomposition)
             == Counter({3: 1, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2, 9: 2, 10: 2}),
             "C34 decomposition selection")
    _require(all(row.get("complete_relation_role") is True
                 and row.get("fresh_confirmation") is False for row in rows),
             "C34 role boundary")
    selection = manifest.get("selection", {})
    _require(selection.get("frozen_before_c34_timing") is True
             and selection.get("timing_or_method_output_used") is False
             and selection.get("training_use") is False
             and selection.get("policy_selection_use") is False
             and selection.get("fresh_confirmation") is False,
             "C34 selection boundary")
    if source is not None:
        source_cases = source.get("cases")
        _require(isinstance(source_cases, list), "C34 source cases")
        expected_ids = set(select_decomposition_case_ids(source_cases))
        _require({row["case_id"] for row in decomposition} == expected_ids,
                 "C34 decomposition selection replay")
        source_map = {row["case_id"]: row for row in source_cases}
        for row in rows:
            original = source_map.get(row["case_id"])
            _require(original is not None and all(row[key] == original[key] for key in
                     ("cluster_id", "family", "n_vars", "truth_sha256",
                      "expression_v2_sha256", "selection_sha256")),
                     "C34 source/manifest binding")
    return {"cases": len(rows), "decomposition_cases": len(decomposition)}


def bind_manifest_cases(
    manifest: Mapping[str, Any], source: Mapping[str, Any], *, role: str,
) -> list[dict[str, Any]]:
    validate_dataset_manifest(manifest, source)
    _require(role in {"complete_relation", "decomposition"}, "unknown C34 role")
    selected_ids = {
        row["case_id"] for row in manifest["cases"]
        if row[f"{role}_role"] is True
    }
    cases = [case for case in source["cases"] if case["case_id"] in selected_ids]
    _require(len(cases) == len(selected_ids), "C34 bound case cardinality")
    return sorted(cases, key=lambda case: case["case_id"])


def truth_contract(case: Mapping[str, Any], *, method: str) -> dict[str, Any]:
    normalized = validate_natural_case(case)
    _require(method in TRUTH_METHODS, "unknown C34 truth method")
    variables = [f"x{index}" for index in range(normalized["n_vars"])]
    contract = {
        "schema": CONTRACT_SCHEMA,
        "contract_id": f"c34-truth-{normalized['case_id']}-{method}",
        "task": "complete_relation",
        "artifact": {
            "kind": "packed_bigint",
            "variable_order": variables,
            "output_order": variables,
            "fixed": [],
            "output_scope": "full",
            "restoration": "none",
            "stream": None,
        },
        "lifecycle": "fresh_engine",
        "queries": 1,
        "validation": {
            "oracle": "frozen_scalar_and_numpy_expression_replay/v1",
            "validation_in_timed_span": False,
            "required_output_sha256": semantic_sha256(normalized["bits"], normalized["n_vars"]),
        },
    }
    validate_contract(contract)
    return contract


def _prepared_program(program: Any, n_vars: int) -> PreparedFlatEvaluation:
    variables = tuple(f"x{index}" for index in range(n_vars))
    template, full_mask = _bind_flat_program(program, variables, {})
    return PreparedFlatEvaluation(program, template, full_mask, False)


def _construct_truth(
    case: Mapping[str, Any],
    method: str,
    *,
    clock: Callable[[], int],
    solver_factory: Callable[..., Any] | None,
) -> tuple[int, dict[str, int], dict[str, Any]]:
    normalized = validate_natural_case(case)
    n_vars = normalized["n_vars"]
    _require(method in TRUTH_METHODS, "unknown C34 truth construction method")
    timings = {field: 0 for field in TRUTH_TIMING_FIELDS}
    resources: dict[str, Any] = {}
    expression = None
    if method != "source_packed_anf":
        expression, timings["input_decode_ns"] = _stage(
            clock, lambda: expr_from_json(case["expression_v2"]))

    if method == "direct_ast_bitset":
        environment, timings["representation_ns"] = _stage(
            clock, lambda: build_bitset_env(tuple(f"x{i}" for i in range(n_vars))))
        bits, timings["execute_ns"] = _stage(
            clock, lambda: eval_expr_bitset(expression, environment))
        resources["representation"] = "recursive_ast_bitset"
    elif method in {"plain_cse_bigint", "flattened_cse_bigint"}:
        program, timings["representation_ns"] = _stage(
            clock, lambda: compile_expr_cse(
                expression, flatten=method == "flattened_cse_bigint"))
        prepared, timings["compile_ns"] = _stage(
            clock, lambda: _prepared_program(program, n_vars))
        bits, timings["execute_ns"] = _stage(clock, prepared.evaluate)
        resources.update(program_metrics(program))
        resources["flattened"] = method == "flattened_cse_bigint"
    elif method == "cm_ir_bigint":
        node, timings["representation_ns"] = _stage(
            clock,
            lambda: compile_expr_to_cm_ir(
                expression,
                reuse_cache=False,
                persistent_cache=False,
                share_aware_flatten=True,
            ),
        )
        prepared, timings["compile_ns"] = _stage(
            clock, lambda: _prepared_program(get_flat_program(node), n_vars))
        bits, timings["execute_ns"] = _stage(clock, prepared.evaluate)
        resources["cm_ir"] = cm_ir_stats(node)
    elif method == "source_packed_anf":
        packed, timings["representation_ns"] = _stage(
            clock, lambda: source_anf_packed(case["expression_v2"], n_vars))
        polynomial, stats = packed
        bits, timings["execute_ns"] = _stage(
            clock, lambda: packed_truth_bits(polynomial, n_vars))
        resources.update({
            "anf_terms": polynomial.bit_count(),
            "anf_multiplications": stats.multiplications,
            "anf_logical_product_pairs": stats.logical_product_pairs,
        })
    else:
        from cmbench.recognition.sat_guidance import encode_expression_cnf

        formula, timings["representation_ns"] = _stage(
            clock, lambda: encode_expression_cnf(expression, n_vars))
        if solver_factory is None:
            from pysat.solvers import Cadical195

            solver_factory = Cadical195
        solver, timings["compile_ns"] = _stage(
            clock, lambda: solver_factory(bootstrap_with=formula.clauses))

        def enumerate_assignments() -> int:
            output = 0
            for assignment in range(1 << n_vars):
                assumptions = [
                    index + 1 if (assignment >> (n_vars - 1 - index)) & 1 else -(index + 1)
                    for index in range(n_vars)
                ]
                output |= int(bool(solver.solve(assumptions=assumptions))) << assignment
            return output

        bits, timings["execute_ns"] = _stage(clock, enumerate_assignments)
        _unused, timings["cleanup_ns"] = _stage(clock, solver.delete)
        resources.update({
            "adapter": "pysat.solvers.Cadical195" if solver_factory.__name__ == "Cadical195"
            else f"injected.{solver_factory.__name__}",
            "clauses": len(formula.clauses),
            "maximum_variable": formula.max_var,
            "solve_calls": 1 << n_vars,
        })
    _require(type(bits) is int, "C34 truth method did not return packed bits")
    return bits, timings, resources


def execute_truth_method(
    *,
    case: Mapping[str, Any],
    contract: Mapping[str, Any],
    method: str,
    clock: Callable[[], int] = time.perf_counter_ns,
    solver_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    normalized_case = validate_natural_case(case)
    normalized_contract = validate_contract(contract)
    _require(method in TRUTH_METHODS and normalized_contract["task"] == "complete_relation",
             "unsupported C34 truth task/method")
    _require(normalized_contract["kind"] == "packed_bigint"
             and normalized_contract["variable_order"]
             == tuple(f"x{i}" for i in range(normalized_case["n_vars"])),
             "C34 truth contract mismatch")
    expected = semantic_sha256(normalized_case["bits"], normalized_case["n_vars"])
    _require(contract["validation"]["required_output_sha256"] == expected,
             "C34 truth contract oracle mismatch")
    total_started = clock()
    bits, timings, resources = _construct_truth(
        case, method, clock=clock, solver_factory=solver_factory)
    delivered, timings["deliver_ns"] = _stage(
        clock,
        lambda: bits.to_bytes(max(1, (1 << normalized_case["n_vars"]) // 8), "little"),
    )
    elapsed = clock() - total_started
    charged = sum(timings.values())
    _require(type(elapsed) is int and elapsed >= 0, "nonmonotonic C34 truth total")
    timings["wrapper_ns"] = max(0, elapsed - charged)
    timings["task_total_ns"] = sum(timings.values())
    actual = semantic_sha256(bits, normalized_case["n_vars"])
    if bits != normalized_case["bits"] or actual != expected:
        raise RuntimeError("C34 complete-relation method failed the exact frozen oracle")
    result = {
        "schema": RESULT_SCHEMA,
        "contract_sha256": contract_digest(contract),
        "case_id": normalized_case["case_id"],
        "arm": method,
        "status": "ok",
        "reason": "completed",
        "timings_ns": timings,
        "artifact": {
            "kind": "packed_bigint",
            "output_scope": "full",
            "output_order": list(normalized_contract["output_order"]),
            "bytes": len(delivered),
            "sha256": actual,
        },
        "resources": resources,
        "identity": {
            "truth_sha256": truth_sha256(bits, normalized_case["n_vars"]),
            "expression_v2_sha256": case["expression_v2_sha256"],
            "exact_check_passed": True,
        },
    }
    validate_result(result, contract)
    return result


def complete_partitions(n_vars: int) -> tuple[tuple[int, ...], ...]:
    _require(type(n_vars) is int and 2 <= n_vars <= 10, "C34 complete partition width")
    partitions = tuple(
        (0,) + rest
        for size in range(1, n_vars)
        for rest in itertools.combinations(range(1, n_vars), size - 1)
    )
    _require(len(partitions) == (1 << (n_vars - 1)) - 1
             and len(set(partitions)) == len(partitions), "incomplete C34 partition universe")
    return partitions


def complete_partition_sha256(n_vars: int) -> str:
    return hashlib.sha256(canonical_bytes([list(row) for row in complete_partitions(n_vars)])).hexdigest()


def execute_decomposition_method(
    *,
    case: Mapping[str, Any],
    contract: Mapping[str, Any],
    method: str,
    required_best: dict[str, Any] | None,
    materialize_budget: int = 4,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, Any]:
    normalized_case = validate_natural_case(case)
    normalized_contract = validate_contract(contract)
    _require(method in DECOMPOSITION_METHODS
             and normalized_contract["task"] == "gf2_decomposition",
             "unsupported C34 decomposition task/method")
    _require(type(materialize_budget) is int and materialize_budget == 4,
             "C34 materialization budget changed")
    expected_digest = delivered_sha256(required_best)
    _require(contract["validation"]["required_output_sha256"] == expected_digest,
             "C34 decomposition contract oracle mismatch")
    total_started = clock()
    bits, truth_timings, resources = _construct_truth(
        case, DECOMPOSITION_TRUTH_METHOD[method], clock=clock, solver_factory=None)
    truth_timings["deliver_ns"] = 0
    partitions, partition_ns = _stage(clock, lambda: complete_partitions(normalized_case["n_vars"]))
    analysis, completion_ns = _stage(
        clock,
        lambda: analyze_screened_exact_gf2(
            bits,
            normalized_case["n_vars"],
            row_partitions=partitions,
            materialize_budget=materialize_budget,
        ),
    )
    best = analysis.best.to_dict() if analysis.best else None

    def exact_check() -> bool:
        exact = (
            bits == normalized_case["bits"]
            and analysis.source_sha256 == truth_sha256(normalized_case["bits"], normalized_case["n_vars"])
            and analysis.partitions_tested == len(partitions)
            and all(candidate.reconstruct() == normalized_case["bits"] for candidate in analysis.candidates)
            and best == required_best
            and delivered_sha256(best) == expected_digest
        )
        if best is not None:
            exact = exact and ExactGF2Artifact.from_dict(best).reconstruct() == normalized_case["bits"]
        return exact

    exact, exact_ns = _stage(clock, exact_check)
    if not exact:
        raise RuntimeError("C34 method failed complete exact GF(2) task completion")
    delivered, artifact_deliver_ns = _stage(
        clock, lambda: canonical_bytes(delivered_document(best)))
    timings = {
        **truth_timings,
        "partition_plan_ns": partition_ns,
        "completion_ns": completion_ns,
        "exact_check_ns": exact_ns,
        "artifact_deliver_ns": artifact_deliver_ns,
    }
    elapsed = clock() - total_started
    charged = sum(timings.values())
    _require(type(elapsed) is int and elapsed >= 0, "nonmonotonic C34 decomposition total")
    timings["wrapper_ns"] = max(0, elapsed - charged)
    timings["task_total_ns"] = sum(timings.values())
    resources.update({
        "complete_partition_universe": True,
        "partition_count": len(partitions),
        "partition_sha256": complete_partition_sha256(normalized_case["n_vars"]),
        "materialize_budget": materialize_budget,
    })
    return {
        "schema": "crse-c34-task-matched-gf2-result/v1",
        "contract_sha256": contract_digest(contract),
        "case_id": normalized_case["case_id"],
        "method": method,
        "status": "ok",
        "timings_ns": timings,
        "artifact": {
            "kind": "exact_gf2_artifact",
            "bytes": len(delivered),
            "sha256": hashlib.sha256(delivered).hexdigest(),
        },
        "identity": {
            "source_sha256": truth_sha256(bits, normalized_case["n_vars"]),
            "best_artifact": best,
            "exact_check_passed": True,
            "partitions_tested": analysis.partitions_tested,
            "descriptors_screened": analysis.descriptors_screened,
            "artifacts_materialized": analysis.artifacts_materialized,
        },
        "resources": resources,
    }


def decomposition_task_contract(
    case: Mapping[str, Any], *, method: str, required_best: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = validate_natural_case(case)
    _require(method in DECOMPOSITION_METHODS, "unknown C34 decomposition method")
    return decomposition_contract(
        contract_id=f"c34-decomposition-{normalized['case_id']}-{method}",
        n_vars=normalized["n_vars"],
        required_output_sha256=delivered_sha256(required_best),
    )


def local_backend_eligibility() -> dict[str, Any]:
    """Declare task eligibility separately from local dependency availability."""
    import importlib.util
    import shutil

    return {
        "schema": "crse-c34-method-eligibility/v1",
        "complete_relation": {
            "timed": list(TRUTH_METHODS),
            "autoref_bdd": {
                "task_eligible": True,
                "available": importlib.util.find_spec("dd.autoref") is not None,
                "timed": False,
                "reason": "fresh single-query BDD was already dominated in C21/C23; exact width probes only",
            },
            "cudd_bdd": {
                "task_eligible": True,
                "available": importlib.util.find_spec("dd.cudd") is not None,
                "timed": False,
                "reason": "local CUDD binding unavailable",
            },
            "abc_aig": {
                "task_eligible": False,
                "available": shutil.which("abc") is not None or shutil.which("yosys-abc") is not None,
                "timed": False,
                "reason": "no frozen adapter delivering the canonical complete packed truth vector",
            },
        },
        "gf2_decomposition": {
            "timed": list(DECOMPOSITION_METHODS),
            "sat": {
                "task_eligible": False,
                "available": importlib.util.find_spec("pysat") is not None,
                "timed": False,
                "reason": "SAT status/witness does not deliver the globally best exact GF(2) artifact",
            },
            "bdd_or_aig_proposal_only": {
                "task_eligible": False,
                "timed": False,
                "reason": "proposal or representation alone is not the complete best-artifact task",
            },
        },
        "production_promotion": False,
    }
