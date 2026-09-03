"""C36 unused width-11..16 cases from the pinned Yosys generator semantics."""
from __future__ import annotations

import hashlib
from typing import Any

from cm_expr_serde import expr_to_json_dag

from cmbench.comparative.contracts import canonical_bytes
from cmbench.recognition.portfolio import admit, reference_bits
from cmbench.recognition.yosys_unused_gf2_data import (
    SOURCE_COMMIT,
    SOURCE_URL,
    Candidate,
    _addertree_candidate,
    _mul_candidate,
    _muladd_candidate,
    _select_candidate,
    candidate_identity,
    scalar_bits,
)


DATASET_SCHEMA = "crse-c36-yosys-wide-restriction-dataset/v1"
WIDTHS = tuple(range(11, 17))
CASES_PER_WIDTH = 3


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def semantic_variables_wide(bits: int, n_vars: int) -> tuple[int, ...]:
    """Detect active axes directly, without the support-10 ANF materializer."""
    active = []
    for index in range(n_vars):
        block = 1 << (n_vars - 1 - index)
        mask = (1 << block) - 1
        if any(
            ((bits >> start) & mask) != ((bits >> (start + block)) & mask)
            for start in range(0, 1 << n_vars, block << 1)
        ):
            active.append(index)
    return tuple(active)


def truth_sha256_wide(bits: int, n_vars: int) -> str:
    _require(type(n_vars) is int and n_vars in WIDTHS and type(bits) is int
             and 0 <= bits < 1 << (1 << n_vars), "invalid wide truth vector")
    return hashlib.sha256(bits.to_bytes((1 << n_vars) // 8, "little")).hexdigest()


def candidate_pool() -> tuple[Candidate, ...]:
    """Finite parameter pool fixed without consulting semantics or timings."""
    values: list[Candidate] = []
    for inputs in range(8, 13):
        values.extend((_select_candidate(inputs, False), _select_candidate(inputs, True)))
    for inputs, output_bit in ((4, 2), (6, 1), (5, 2), (8, 1)):
        values.append(_addertree_candidate(inputs, output_bit))
    for b_width in (4, 8, 16):
        for output_bit in range(5, 12):
            candidate = _mul_candidate(b_width, output_bit)
            if len(candidate.variable_specs) in WIDTHS:
                values.append(candidate)
    for b_width in (8, 16):
        for output_bit in (3, 4):
            candidate = _muladd_candidate(b_width, output_bit)
            if len(candidate.variable_specs) in WIDTHS:
                values.append(candidate)
    identities = [candidate_identity(candidate) for candidate in values]
    _require(len(identities) == len(set(identities)), "duplicate C36 candidate identity")
    return tuple(values)


def select_candidates(pool: tuple[Candidate, ...] | None = None) -> tuple[Candidate, ...]:
    """Choose three identities per width with family round-robin before semantics."""
    pool = candidate_pool() if pool is None else pool
    selected: list[Candidate] = []
    for n_vars in WIDTHS:
        group = [candidate for candidate in pool if len(candidate.variable_specs) == n_vars]
        by_family: dict[str, list[Candidate]] = {}
        for candidate in group:
            by_family.setdefault(candidate.family, []).append(candidate)
        for rows in by_family.values():
            rows.sort(key=candidate_identity)
        width_selection: list[Candidate] = []
        offset = 0
        families = sorted(by_family)
        while len(width_selection) < CASES_PER_WIDTH:
            before = len(width_selection)
            for family in families:
                if len(width_selection) == CASES_PER_WIDTH:
                    break
                if offset < len(by_family[family]):
                    width_selection.append(by_family[family][offset])
            _require(len(width_selection) > before, f"insufficient C36 width {n_vars} pool")
            offset += 1
        selected.extend(width_selection)
    _require(len(selected) == len(WIDTHS) * CASES_PER_WIDTH, "C36 selection cardinality")
    return tuple(selected)


def build_dataset(*, inventory_path: str, inventory_sha256: str,
                  prior_dataset_path: str, prior_dataset_sha256: str,
                  prior_truth_identities: set[tuple[int, str]]) -> dict[str, Any]:
    rows = []
    semantic_seen: set[tuple[int, str]] = set()
    for candidate in select_candidates():
        n_vars = len(candidate.variable_specs)
        admit(candidate.expression, n_vars, 64)
        bits = reference_bits(candidate.expression, n_vars)
        scalar = scalar_bits(candidate)
        _require(bits == scalar, "C36 independent scalar/expression oracle mismatch")
        _require(semantic_variables_wide(bits, n_vars) == tuple(range(n_vars)),
                 "C36 candidate does not use its complete declared support")
        digest = truth_sha256_wide(bits, n_vars)
        semantic = (n_vars, digest)
        _require(semantic not in prior_truth_identities and semantic not in semantic_seen,
                 "C36 prior or within-slice semantic overlap")
        semantic_seen.add(semantic)
        identity = candidate_identity(candidate)
        expression = expr_to_json_dag(candidate.expression)
        rows.append({
            "schema": DATASET_SCHEMA,
            "case_id": f"c36-{candidate.family}-{identity[:16]}",
            "split": "fresh_wide_parameter_confirmation",
            "cluster_id": candidate.family,
            "source_kind": "yosys_bench_unused_wide_generator_semantics",
            "source_repository": SOURCE_URL,
            "source_commit": SOURCE_COMMIT,
            "source_generator": candidate.source_generator,
            "family": candidate.family,
            "parameters": candidate.parameters,
            "variable_specs": [[port, bit] for port, bit in candidate.variable_specs],
            "n_vars": n_vars,
            "truth_bits_hex": format(bits, "x"),
            "truth_sha256": digest,
            "expression_v2": expression,
            "expression_v2_sha256": hashlib.sha256(canonical_bytes(expression)).hexdigest(),
            "selection_sha256": identity,
            "prior_truth_overlap": False,
            "training_use": False,
            "policy_selection_use": False,
            "fresh_confirmation": True,
        })
    rows.sort(key=lambda row: (row["n_vars"], row["case_id"]))
    document = {
        "schema": DATASET_SCHEMA,
        "status": "frozen",
        "cases": rows,
        "counts": {
            "cases": len(rows),
            "cases_per_width": CASES_PER_WIDTH,
            "by_n_vars": {str(n): sum(row["n_vars"] == n for row in rows) for n in WIDTHS},
            "families": len({row["family"] for row in rows}),
            "candidate_pool": len(candidate_pool()),
        },
        "provenance": {
            "source_repository": SOURCE_URL,
            "source_commit": SOURCE_COMMIT,
            "source_inventory": inventory_path,
            "source_inventory_sha256": inventory_sha256,
            "prior_dataset": prior_dataset_path,
            "prior_dataset_sha256": prior_dataset_sha256,
            "selection_contract": "three stable family-round-robin source identities per width/v1",
            "source_repository_reused": True,
            "parameter_and_truth_identities_fresh": True,
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
    _require(isinstance(document, dict) and document.get("schema") == DATASET_SCHEMA
             and document.get("status") == "frozen", "invalid C36 dataset envelope")
    rows = document.get("cases")
    _require(isinstance(rows, list) and len(rows) == 18, "invalid C36 case count")
    _require(document.get("counts", {}).get("by_n_vars") == {str(n): 3 for n in WIDTHS},
             "invalid C36 width balance")
    selected = select_candidates()
    expected = {(len(candidate.variable_specs), candidate_identity(candidate))
                for candidate in selected}
    observed = set()
    semantics = set()
    for row in rows:
        _require(isinstance(row, dict) and row.get("schema") == DATASET_SCHEMA
                 and row.get("split") == "fresh_wide_parameter_confirmation"
                 and row.get("source_commit") == SOURCE_COMMIT
                 and row.get("n_vars") in WIDTHS
                 and row.get("training_use") is False
                 and row.get("policy_selection_use") is False
                 and row.get("prior_truth_overlap") is False
                 and row.get("fresh_confirmation") is True,
                 "invalid C36 case boundary")
        observed.add((row["n_vars"], row["selection_sha256"]))
        semantic = (row["n_vars"], row["truth_sha256"])
        _require(semantic not in semantics, "duplicate C36 truth identity")
        semantics.add(semantic)
        from cm_expr_serde import expr_from_json
        expression = expr_from_json(row["expression_v2"])
        bits = reference_bits(expression, row["n_vars"])
        _require(bits == int(row["truth_bits_hex"], 16)
                 and truth_sha256_wide(bits, row["n_vars"]) == row["truth_sha256"]
                 and hashlib.sha256(canonical_bytes(row["expression_v2"])).hexdigest()
                 == row["expression_v2_sha256"], "changed C36 expression or truth")
    _require(observed == expected, "C36 selection identity changed")
    provenance = document.get("provenance", {})
    _require(provenance.get("source_repository_reused") is True
             and provenance.get("parameter_and_truth_identities_fresh") is True
             and provenance.get("timing_or_method_output_used") is False
             and provenance.get("network_used") is False
             and provenance.get("training_use") is False
             and provenance.get("policy_refit_allowed") is False
             and provenance.get("production_promotion") is False,
             "invalid C36 provenance boundary")
