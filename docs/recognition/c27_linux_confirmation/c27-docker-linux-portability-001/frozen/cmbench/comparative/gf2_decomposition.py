"""Task-matched F1 adapters for exact CM/GF(2) decomposition artifacts."""
from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Mapping
from typing import Any

from cmbench.recognition.gf2_decomposition import (
    ExactGF2Artifact, analyze_exact_gf2, analyze_screened_exact_gf2, truth_sha256)
from cmbench.recognition.gf2_task_dispatcher import (
    GF2DecompositionTask, compile_gf2_dispatcher, validate_gf2_dispatch_policy)

from .contracts import (
    CONTRACT_SCHEMA, RESULT_SCHEMA, canonical_bytes, contract_digest,
    validate_contract, validate_result)

ARMS = frozenset({"gf2_exhaustive", "gf2_screened", "gf2_c17_selected", "gf2_c17_advice_off"})


def delivered_document(best: dict[str, Any] | None) -> dict[str, Any]:
    return {"schema": "cm-comparative-exact-gf2-delivery/v1", "best_artifact": best}


def delivered_sha256(best: dict[str, Any] | None) -> str:
    return hashlib.sha256(canonical_bytes(delivered_document(best))).hexdigest()


def decomposition_contract(*, contract_id: str, n_vars: int,
                           required_output_sha256: str | None) -> dict[str, Any]:
    if type(n_vars) is not int or not 2 <= n_vars <= 10:
        raise ValueError("F1 GF(2) task width must be 2..10")
    contract = {
        "schema": CONTRACT_SCHEMA, "contract_id": contract_id,
        "task": "gf2_decomposition",
        "artifact": {"kind": "exact_gf2_artifact",
                     "variable_order": [f"x{index}" for index in range(n_vars)],
                     "output_order": [], "fixed": [], "output_scope": "not_applicable",
                     "restoration": "none", "stream": None},
        "lifecycle": "fresh_engine", "queries": 1,
        "validation": {"oracle": "bounded_exhaustive_best_identity/v1",
                       "validation_in_timed_span": False,
                       "required_output_sha256": required_output_sha256},
    }
    validate_contract(contract)
    return contract


def execute_decomposition_arm(
    *, bits: int, contract: Mapping[str, Any], case_id: str, arm: str,
    policy: dict[str, Any] | None = None, max_partitions: int = 64,
    materialize_budget: int = 4,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, Any]:
    normalized = validate_contract(contract)
    if normalized["task"] != "gf2_decomposition" or arm not in ARMS:
        raise ValueError("unsupported F1 GF(2) arm/task")
    n_vars = len(normalized["variable_order"])
    truth_sha256(bits, n_vars)
    if (type(max_partitions) is not int or not 1 <= max_partitions <= 64
            or type(materialize_budget) is not int or not 1 <= materialize_budget <= 4):
        raise ValueError("invalid bounded F1 GF(2) work limits")
    timings: dict[str, int] = {}
    total_started = clock()
    analysis = execution = None
    if arm == "gf2_exhaustive":
        started = clock()
        analysis = analyze_exact_gf2(bits, n_vars, max_partitions=max_partitions)
        timings["analysis_ns"] = clock() - started
        selected_arm, best = "explicit_cm_exhaustive", (analysis.best.to_dict() if analysis.best else None)
    elif arm == "gf2_screened":
        started = clock()
        analysis = analyze_screened_exact_gf2(
            bits, n_vars, max_partitions=max_partitions,
            materialize_budget=materialize_budget)
        timings["analysis_ns"] = clock() - started
        selected_arm, best = "explicit_cm_screened", (analysis.best.to_dict() if analysis.best else None)
    else:
        if policy is None:
            raise ValueError("C17 comparative arm requires a frozen policy")
        validate_gf2_dispatch_policy(policy)
        task = GF2DecompositionTask(n_vars, tuple(range(n_vars)), max_partitions,
                                    materialize_budget)
        started = clock()
        dispatcher = compile_gf2_dispatcher(
            policy, task, advice_enabled=arm == "gf2_c17_selected")
        timings["dispatch_compile_ns"] = clock() - started
        started = clock()
        execution = dispatcher.execute(bits)
        timings["dispatch_execute_ns"] = clock() - started
        selected_arm, best = execution.selected_arm, execution.best_artifact

    checked = clock()
    exact = True
    if analysis is not None:
        exact = analysis.source_sha256 == truth_sha256(bits, n_vars) and all(
            candidate.reconstruct() == bits for candidate in analysis.candidates)
    if best is not None:
        exact = exact and ExactGF2Artifact.from_dict(best).reconstruct() == bits
    timings["exact_artifact_check_ns"] = clock() - checked
    if not exact:
        raise RuntimeError("F1 GF(2) exact artifact check failed")
    delivered = canonical_bytes(delivered_document(best))
    timings["task_total_ns"] = clock() - total_started
    result = {
        "schema": RESULT_SCHEMA, "contract_sha256": contract_digest(contract),
        "case_id": case_id, "arm": arm, "status": "ok", "reason": "completed",
        "timings_ns": timings,
        "artifact": {"kind": "exact_gf2_artifact", "output_scope": "not_applicable",
                     "output_order": [], "bytes": len(delivered),
                     "sha256": hashlib.sha256(delivered).hexdigest()},
        "resources": {"max_partitions": max_partitions,
                      "materialize_budget": materialize_budget,
                      "memory_measured": False},
        "identity": {"source_sha256": truth_sha256(bits, n_vars),
                     "selected_exact_arm": selected_arm,
                     "best_artifact": best, "exact_check_passed": True,
                     "partitions_tested": (analysis.partitions_tested if analysis else execution.partitions_tested),
                     "descriptors_screened": (analysis.descriptors_screened if analysis else execution.descriptors_screened),
                     "artifacts_materialized": (analysis.artifacts_materialized if analysis else execution.artifacts_materialized)},
    }
    validate_result(result, contract)
    return result
