"""Task-matched exact GF(2) method adapters for the C21 comparison table."""
from __future__ import annotations

import hashlib
import itertools
import time
from collections import Counter
from collections.abc import Callable, Mapping
from typing import Any

from cm_expr_serde import expr_from_json

from cmbench.recognition.bdd_ordering import ExactBddArtifact
from cmbench.recognition.gf2_decomposition import (
    ExactGF2Artifact,
    analyze_exact_gf2,
    analyze_screened_exact_gf2,
    candidate_partitions,
    truth_sha256,
)
from cmbench.recognition.gf2_task_dispatcher import EXHAUSTIVE, SCREENED
from cmbench.recognition.gf2_work_policy_compiler import CompiledGF2WorkPolicy
from cmbench.recognition.natural_decomposition import interaction_edges
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.source_anf_hybrid import (
    packed_interaction_components,
    packed_truth_bits,
    source_anf_packed,
)
from cmbench.recognition.source_interaction import source_partition_proposal

from .contracts import canonical_bytes, validate_contract
from .gf2_decomposition import delivered_document, delivered_sha256

METHODS = (
    "cm_exhaustive",
    "cm_screened",
    "cm_compiled_screened",
    "truth_anf_min_cut",
    "source_packed_anf",
    "bdd_level_cut",
    "source_interaction_cut",
)
PROPOSAL_METHODS = frozenset({
    "truth_anf_min_cut", "source_packed_anf", "bdd_level_cut", "source_interaction_cut",
})
TIMING_FIELDS = (
    "input_decode_ns",
    "representation_ns",
    "proposal_ns",
    "policy_ns",
    "completion_ns",
    "exact_check_ns",
    "cleanup_ns",
    "wrapper_ns",
)


def _canonical_row(row: tuple[int, ...] | None, n_vars: int) -> tuple[int, ...] | None:
    if row is None:
        return None
    normalized = tuple(sorted(row))
    if (
        not normalized
        or len(normalized) == n_vars
        or len(set(normalized)) != len(normalized)
        or any(type(value) is not int or not 0 <= value < n_vars for value in normalized)
    ):
        raise ValueError("invalid C21 proposal partition")
    if 0 not in normalized:
        normalized = tuple(value for value in range(n_vars) if value not in normalized)
    return normalized


def interaction_min_cut(edges: tuple[tuple[int, int], ...], n_vars: int) -> tuple[int, ...]:
    """Return a deterministic nontrivial cut of an exact interaction graph."""
    if type(n_vars) is not int or not 2 <= n_vars <= 10:
        raise ValueError("invalid C21 interaction universe")
    edge_set = set(edges)
    if any(
        type(edge) is not tuple
        or len(edge) != 2
        or not 0 <= edge[0] < edge[1] < n_vars
        for edge in edge_set
    ):
        raise ValueError("invalid C21 interaction edge")
    candidates = []
    for size in range(1, n_vars):
        for rest in itertools.combinations(range(1, n_vars), size - 1):
            row = (0,) + rest
            row_set = set(row)
            crossing = sum((left in row_set) != (right in row_set) for left, right in edge_set)
            candidates.append((crossing, abs(n_vars - 2 * len(row)), max(len(row), n_vars - len(row)), row))
    return min(candidates)[3]


def _component_partition(
    components: tuple[tuple[int, ...], ...], n_vars: int,
) -> tuple[int, ...] | None:
    if len(components) < 2:
        return None
    candidates = []
    for count in range(1, len(components)):
        for selected_rest in itertools.combinations(range(1, len(components)), count - 1):
            selected = (0,) + selected_rest
            row = tuple(sorted(value for index in selected for value in components[index]))
            if len(row) != n_vars:
                candidates.append((abs(n_vars - 2 * len(row)), max(len(row), n_vars - len(row)), row))
    return min(candidates)[2] if candidates else None


def _bdd_level_partition(artifact: ExactBddArtifact) -> tuple[int, ...]:
    document = artifact.to_dict()
    counts = Counter(row[0] for row in document["nodes"].values())
    target = max(1, artifact.n_vars // 2)
    selected = tuple(sorted(range(artifact.n_vars), key=lambda value: (-counts[value], value))[:target])
    return _canonical_row(selected, artifact.n_vars)  # type: ignore[return-value]


def _ordered_partitions(
    bits: int, n_vars: int, max_partitions: int, proposal: tuple[int, ...] | None,
) -> tuple[tuple[int, ...], ...]:
    base = candidate_partitions(bits, n_vars, max_partitions)
    proposal = _canonical_row(proposal, n_vars)
    if proposal is None:
        return base
    return (proposal,) + tuple(row for row in base if row != proposal)


def _packed_tuple(bits: tuple[int, ...]) -> int:
    return sum(value << index for index, value in enumerate(bits))


def execute_method(
    *,
    case: Mapping[str, Any],
    contract: Mapping[str, Any],
    method: str,
    required_best: dict[str, Any] | None,
    compiled_policy: CompiledGF2WorkPolicy | None = None,
    max_partitions: int = 64,
    materialize_budget: int = 4,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, Any]:
    normalized = validate_contract(contract)
    if normalized["task"] != "gf2_decomposition" or method not in METHODS:
        raise ValueError("unsupported C21 task or method")
    n_vars = len(normalized["variable_order"])
    if (
        case.get("n_vars") != n_vars
        or type(case.get("truth_bits_hex")) is not str
        or type(case.get("expression_v2")) is not dict
        or type(max_partitions) is not int
        or not 1 <= max_partitions <= 64
        or type(materialize_budget) is not int
        or not 1 <= materialize_budget <= 4
    ):
        raise ValueError("invalid bounded C21 method input")
    frozen_bits = int(case["truth_bits_hex"], 16)
    truth_sha256(frozen_bits, n_vars)
    required_digest = delivered_sha256(required_best)
    if contract["validation"]["required_output_sha256"] != required_digest:
        raise ValueError("C21 contract does not bind the exhaustive-best artifact")

    timings = {field: 0 for field in TIMING_FIELDS}
    total_started = clock()
    proposal: tuple[int, ...] | None = None
    proposal_details: dict[str, Any] = {"status": "not_applicable", "row_variables": None}
    resources: dict[str, Any] = {"max_partitions": max_partitions, "materialize_budget": materialize_budget}
    bdd: ExactBddArtifact | None = None

    if method == "source_packed_anf":
        started = clock()
        polynomial, stats = source_anf_packed(case["expression_v2"], n_vars)
        bits = packed_truth_bits(polynomial, n_vars)
        timings["representation_ns"] = max(1, clock() - started)
        started = clock()
        components = packed_interaction_components(polynomial, n_vars)
        proposal = _component_partition(components, n_vars)
        timings["proposal_ns"] = max(1, clock() - started)
        resources.update({"anf_terms": polynomial.bit_count(), "anf_multiplications": stats.multiplications,
                          "anf_logical_product_pairs": stats.logical_product_pairs})
    elif method == "bdd_level_cut":
        started = clock()
        expression = expr_from_json(case["expression_v2"])
        timings["input_decode_ns"] = max(1, clock() - started)
        started = clock()
        bdd = ExactBddArtifact.build(
            expression, n_vars, [f"x{index}" for index in range(n_vars)], backend="autoref")
        bits = _packed_tuple(bdd.truth_bits())
        timings["representation_ns"] = max(1, clock() - started)
        started = clock()
        proposal = _bdd_level_partition(bdd)
        timings["proposal_ns"] = max(1, clock() - started)
        resources["bdd_nodes"] = bdd.node_count
    else:
        if method == "source_interaction_cut":
            started = clock()
            proposal = source_partition_proposal(case["expression_v2"], n_vars)
            timings["proposal_ns"] = max(1, clock() - started)
        started = clock()
        expression = expr_from_json(case["expression_v2"])
        timings["input_decode_ns"] = max(1, clock() - started)
        started = clock()
        bits = reference_bits(expression, n_vars)
        timings["representation_ns"] = max(1, clock() - started)
        if method == "truth_anf_min_cut":
            started = clock()
            proposal = interaction_min_cut(interaction_edges(bits, n_vars), n_vars)
            timings["proposal_ns"] = max(1, clock() - started)

    if method == "cm_compiled_screened":
        if compiled_policy is None:
            raise ValueError("C21 compiled method requires a frozen compiled policy")
        started = clock()
        selected_arm = compiled_policy.select(bits, n_vars)
        timings["policy_ns"] = max(1, clock() - started)
    else:
        selected_arm = EXHAUSTIVE if method == "cm_exhaustive" else SCREENED

    if method in PROPOSAL_METHODS:
        proposal = _canonical_row(proposal, n_vars)
        proposal_details = {
            "status": "proposed" if proposal is not None else "abstained",
            "row_variables": list(proposal) if proposal is not None else None,
        }
    partitions = _ordered_partitions(bits, n_vars, max_partitions, proposal)
    started = clock()
    if selected_arm == EXHAUSTIVE:
        analysis = analyze_exact_gf2(bits, n_vars, row_partitions=partitions)
    elif selected_arm == SCREENED:
        analysis = analyze_screened_exact_gf2(
            bits, n_vars, row_partitions=partitions, materialize_budget=materialize_budget)
    else:
        raise ValueError("C21 compiled policy selected an unknown exact arm")
    timings["completion_ns"] = max(1, clock() - started)
    best = analysis.best.to_dict() if analysis.best else None

    started = clock()
    exact = (
        bits == frozen_bits
        and analysis.source_sha256 == truth_sha256(frozen_bits, n_vars)
        and all(candidate.reconstruct() == frozen_bits for candidate in analysis.candidates)
        and best == required_best
        and delivered_sha256(best) == required_digest
    )
    if best is not None:
        exact = exact and ExactGF2Artifact.from_dict(best).reconstruct() == frozen_bits
    timings["exact_check_ns"] = max(1, clock() - started)
    if not exact:
        raise RuntimeError("C21 method failed exact task completion")
    if bdd is not None:
        started = clock()
        bdd.close()
        timings["cleanup_ns"] = max(1, clock() - started)

    elapsed = max(1, clock() - total_started)
    charged = sum(timings[field] for field in TIMING_FIELDS if field != "wrapper_ns")
    timings["wrapper_ns"] = max(0, elapsed - charged)
    timings["task_total_ns"] = sum(timings.values())
    delivered = canonical_bytes(delivered_document(best))
    return {
        "schema": "crse-c21-task-matched-gf2-method-result/v1",
        "case_id": case["case_id"],
        "method": method,
        "status": "ok",
        "selected_exact_arm": selected_arm,
        "proposal": proposal_details,
        "timings_ns": timings,
        "artifact": {"kind": "exact_gf2_artifact", "bytes": len(delivered),
                     "sha256": hashlib.sha256(delivered).hexdigest()},
        "identity": {"source_sha256": truth_sha256(frozen_bits, n_vars),
                     "best_artifact": best, "exact_check_passed": True,
                     "partitions_tested": analysis.partitions_tested,
                     "descriptors_screened": analysis.descriptors_screened,
                     "artifacts_materialized": analysis.artifacts_materialized},
        "resources": resources,
    }
