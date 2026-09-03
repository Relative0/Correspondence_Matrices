"""Frozen, timing-blind C37 candidates for native exact confirmation."""
from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.gf2_wide_repeated_queries import (
    build_query_trace,
    oracle_document,
)
from cmbench.recognition.features import postorder
from cmbench.recognition.yosys_unused_gf2_data import (
    SOURCE_COMMIT,
    SOURCE_URL,
    Candidate,
    _addertree_candidate,
    _mul_candidate,
    _muladd_candidate,
    candidate_identity,
    scalar_bits,
)
from cmbench.recognition.yosys_wide_restriction_data import (
    WIDTHS,
    candidate_pool as c36_candidate_pool,
    semantic_variables_wide,
    truth_sha256_wide,
)


DATASET_SCHEMA = "crse-c37-native-exact-confirmation-dataset/v1"
CASES_PER_WIDTH = 3


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def reference_bits_unbounded(expr: Expr, n_vars: int) -> int:
    """Independent iterative NumPy oracle without the unrelated portfolio cap."""
    _require(11 <= n_vars <= 16, "C37 oracle width")
    rows = np.arange(1 << n_vars, dtype=np.uint32)
    values: dict[int, np.ndarray] = {}
    for node in postorder(expr):
        kind = type(node)
        if kind is Var:
            value = ((rows >> (n_vars - 1 - node.i)) & 1).astype(np.uint8)
        elif kind is Not:
            value = np.logical_not(values[id(node.a)])
        else:
            left, right = values[id(node.a)], values[id(node.b)]
            if kind is And:
                value = np.logical_and(left, right)
            elif kind is Or:
                value = np.logical_or(left, right)
            elif kind is Xor:
                value = np.logical_xor(left, right)
            elif kind is Imp:
                value = np.logical_or(np.logical_not(left), right)
            elif kind is Eqv:
                value = np.equal(left, right)
            else:
                raise ValueError("unsupported C37 oracle operation")
        values[id(node)] = value
    return int.from_bytes(
        np.packbits(values[id(expr)], bitorder="little").tobytes(), "little"
    )


def prospective_candidates() -> tuple[Candidate, ...]:
    """Three predeclared generator identities per width; no semantic/timing selection."""
    parameter_rows = (
        (11, _addertree_candidate(11, 0)),
        (11, _mul_candidate(3, 7)),
        (11, _muladd_candidate(3, 3)),
        (12, _addertree_candidate(12, 0)),
        (12, _mul_candidate(3, 8)),
        (12, _muladd_candidate(2, 4)),
        (13, _addertree_candidate(13, 0)),
        (13, _mul_candidate(5, 7)),
        (13, _muladd_candidate(3, 4)),
        (14, _addertree_candidate(7, 1)),
        (14, _mul_candidate(5, 8)),
        (14, _muladd_candidate(4, 4)),
        (15, _addertree_candidate(15, 0)),
        (15, _mul_candidate(7, 7)),
        (15, _muladd_candidate(5, 4)),
        (16, _addertree_candidate(4, 3)),
        (16, _mul_candidate(9, 7)),
        (16, _muladd_candidate(4, 5)),
    )
    candidates = tuple(candidate for width, candidate in parameter_rows)
    identities = [candidate_identity(candidate) for candidate in candidates]
    c36_identities = {candidate_identity(candidate) for candidate in c36_candidate_pool()}
    _require(
        len(candidates) == len(WIDTHS) * CASES_PER_WIDTH
        and len(identities) == len(set(identities))
        and not c36_identities.intersection(identities)
        and all(len(candidate.variable_specs) == width
                for (width, _), candidate in zip(parameter_rows, candidates))
        and all(sum(len(candidate.variable_specs) == width for candidate in candidates)
                == CASES_PER_WIDTH for width in WIDTHS),
        "invalid C37 candidate freeze",
    )
    return candidates


def build_dataset(*, freeze_path: str, freeze_sha256: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    semantics: set[tuple[int, str]] = set()
    for candidate in prospective_candidates():
        n_vars = len(candidate.variable_specs)
        expression_bits = reference_bits_unbounded(candidate.expression, n_vars)
        scalar = scalar_bits(candidate)
        _require(expression_bits == scalar, "C37 scalar/expression oracle mismatch")
        _require(
            semantic_variables_wide(scalar, n_vars) == tuple(range(n_vars)),
            "C37 candidate lacks complete declared support",
        )
        truth_sha = truth_sha256_wide(scalar, n_vars)
        semantic = (n_vars, truth_sha)
        _require(semantic not in semantics, "C37 duplicate truth identity")
        semantics.add(semantic)
        identity = candidate_identity(candidate)
        expression = expr_to_json_dag(candidate.expression)
        case = {
            "schema": DATASET_SCHEMA,
            "case_id": f"c37-{candidate.family}-{identity[:16]}",
            "split": "prospective_native_exact_confirmation",
            "cluster_id": candidate.family,
            "source_kind": "yosys_bench_unused_parameter_generator_semantics",
            "source_repository": SOURCE_URL,
            "source_commit": SOURCE_COMMIT,
            "source_generator": candidate.source_generator,
            "family": candidate.family,
            "parameters": candidate.parameters,
            "variable_specs": [[port, bit] for port, bit in candidate.variable_specs],
            "n_vars": n_vars,
            "truth_bits_hex": format(scalar, "x"),
            "truth_sha256": truth_sha,
            "expression_v2": expression,
            "expression_v2_sha256": hashlib.sha256(canonical_bytes(expression)).hexdigest(),
            "selection_sha256": identity,
            "c36_overlap": False,
            "training_use": False,
            "policy_selection_use": False,
            "fresh_confirmation": True,
        }
        trace = build_query_trace(case["case_id"], n_vars)
        case["c36_trace"] = trace
        case["c36_trace_sha256"] = hashlib.sha256(canonical_bytes(trace)).hexdigest()
        case["c36_required_output_sha256"] = hashlib.sha256(
            canonical_bytes(oracle_document(case, trace))
        ).hexdigest()
        rows.append(case)
    rows.sort(key=lambda row: (row["n_vars"], row["family"], row["case_id"]))
    document = {
        "schema": DATASET_SCHEMA,
        "status": "frozen",
        "cases": rows,
        "counts": {
            "cases": len(rows),
            "cases_per_width": CASES_PER_WIDTH,
            "by_n_vars": {str(width): sum(row["n_vars"] == width for row in rows)
                          for width in WIDTHS},
            "families": len({row["family"] for row in rows}),
        },
        "query_contract": {
            "queries_per_case": 64,
            "live_widths": [6, 8, 10],
            "selection_uses_outputs_or_timings": False,
            "compatibility_field_prefix": "c36",
        },
        "provenance": {
            "freeze_path": freeze_path,
            "freeze_sha256": freeze_sha256,
            "selection_contract": "three fixed arithmetic-generator parameter rows per width/v1",
            "parameter_and_truth_identities_fresh_vs_c36": True,
            "timing_or_method_output_used": False,
            "network_used": False,
            "training_use": False,
            "policy_refit_allowed": False,
            "production_promotion": False,
        },
    }
    validate_dataset(document)
    return document


def validate_dataset(document: dict[str, Any]) -> None:
    _require(document.get("schema") == DATASET_SCHEMA and document.get("status") == "frozen",
             "invalid C37 dataset envelope")
    rows = document.get("cases")
    _require(isinstance(rows, list) and len(rows) == 18, "invalid C37 case count")
    expected = {(len(candidate.variable_specs), candidate_identity(candidate))
                for candidate in prospective_candidates()}
    observed: set[tuple[int, str]] = set()
    semantics: set[tuple[int, str]] = set()
    for row in rows:
        _require(
            row.get("schema") == DATASET_SCHEMA
            and row.get("split") == "prospective_native_exact_confirmation"
            and row.get("source_commit") == SOURCE_COMMIT
            and row.get("fresh_confirmation") is True
            and row.get("training_use") is False
            and row.get("policy_selection_use") is False
            and row.get("c36_overlap") is False,
            "invalid C37 case boundary",
        )
        observed.add((row["n_vars"], row["selection_sha256"]))
        semantic = (row["n_vars"], row["truth_sha256"])
        _require(semantic not in semantics, "duplicate C37 semantic identity")
        semantics.add(semantic)
        expression = expr_from_json(row["expression_v2"])
        bits = reference_bits_unbounded(expression, row["n_vars"])
        trace = build_query_trace(row["case_id"], row["n_vars"])
        _require(
            bits == int(row["truth_bits_hex"], 16)
            and truth_sha256_wide(bits, row["n_vars"]) == row["truth_sha256"]
            and hashlib.sha256(canonical_bytes(row["expression_v2"])).hexdigest()
            == row["expression_v2_sha256"]
            and row.get("c36_trace") == trace
            and row.get("c36_trace_sha256")
            == hashlib.sha256(canonical_bytes(trace)).hexdigest()
            and row.get("c36_required_output_sha256")
            == hashlib.sha256(canonical_bytes(oracle_document(row, trace))).hexdigest(),
            "changed C37 expression, truth, trace, or output contract",
        )
    provenance = document.get("provenance", {})
    _require(
        observed == expected
        and document.get("counts", {}).get("by_n_vars")
        == {str(width): CASES_PER_WIDTH for width in WIDTHS}
        and provenance.get("parameter_and_truth_identities_fresh_vs_c36") is True
        and provenance.get("timing_or_method_output_used") is False
        and provenance.get("network_used") is False
        and provenance.get("training_use") is False
        and provenance.get("policy_refit_allowed") is False
        and provenance.get("production_promotion") is False,
        "invalid C37 selection or provenance boundary",
    )
