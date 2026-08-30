"""Bounded variable-size fixtures for exact balanced XOR decomposition.

For a Boolean function over an ordered variable universe, split the variables
into a row half and a column half.  The target is true exactly when its truth
matrix has the GF(2) form ``M[r,c] = g[r] xor h[c]``.  This is equivalent to
every 2x2 parity anchored at ``M[0,0]`` being zero.

The generated positives hide arbitrary (usually nonlinear) row and column
subfunctions behind split-specific XOR encodings.  Each paired negative flips
one truth-table cell, giving an exact non-member at Hamming distance one from
its positive parent.  These remain mechanism fixtures, not natural data.
"""
from __future__ import annotations

import hashlib
import json
import random
from typing import Any, Iterable

import numpy as np

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

from .features import structural_digest
from .portfolio import admit, reference_bits

SPLITS = ("train", "validation", "test", "confirmatory")
SIZES = {"train": (4, 6, 8), "validation": (8,), "test": (8,), "confirmatory": (10,)}
TEMPLATES = {
    "train": "partition-xor-dnf/v1",
    "validation": "partition-xor-cnf/v1",
    "test": "partition-not-equivalence/v1",
    "confirmatory": "partition-equivalence-negated-left/v1",
}
MAX_VARS = 10
MAX_SIDE = 1 << (MAX_VARS // 2)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def balanced_shape(n_vars: int) -> tuple[int, int]:
    if type(n_vars) is not int or not 2 <= n_vars <= MAX_VARS:
        raise ValueError("balanced decomposition requires 2..10 variables")
    row_vars = n_vars // 2
    return 1 << row_vars, 1 << (n_vars - row_vars)


def packed_sha256(bits: int, n_vars: int) -> str:
    if type(bits) is not int or bits < 0 or bits.bit_length() > (1 << n_vars):
        raise ValueError("truth vector outside declared universe")
    size = max(1, (1 << n_vars) // 8)
    return hashlib.sha256(bits.to_bytes(size, "little")).hexdigest()


def xor_partition_witness(bits: int, n_vars: int) -> dict[str, Any] | None:
    """Return canonical row/column factors, or ``None`` for a non-member."""
    rows, columns = balanced_shape(n_vars)
    if type(bits) is not int or bits < 0 or bits.bit_length() > rows * columns:
        raise ValueError("truth vector outside declared universe")
    at = lambda row, column: (bits >> (row * columns + column)) & 1
    corner = at(0, 0)
    row_factor = [at(row, 0) ^ corner for row in range(rows)]
    column_factor = [at(0, column) for column in range(columns)]
    for row in range(rows):
        for column in range(columns):
            if at(row, column) != (row_factor[row] ^ column_factor[column]):
                return None
    return {
        "partition": [n_vars // 2, n_vars - n_vars // 2],
        "row_factor_bits": sum(value << index for index, value in enumerate(row_factor)),
        "column_factor_bits": sum(value << index for index, value in enumerate(column_factor)),
        "stored_factor_bits": rows + columns,
        "full_truth_bits": rows * columns,
    }


def compose_xor_factors(witness: dict[str, Any], n_vars: int) -> int:
    rows, columns = balanced_shape(n_vars)
    if (type(witness) is not dict or witness.get("partition") != [n_vars // 2, n_vars - n_vars // 2]
            or type(witness.get("row_factor_bits")) is not int
            or type(witness.get("column_factor_bits")) is not int):
        raise ValueError("invalid balanced XOR witness")
    row_bits, column_bits = witness["row_factor_bits"], witness["column_factor_bits"]
    if row_bits < 0 or row_bits.bit_length() > rows or column_bits < 0 or column_bits.bit_length() > columns:
        raise ValueError("factor outside balanced partition")
    result = 0
    for row in range(rows):
        for column in range(columns):
            value = ((row_bits >> row) & 1) ^ ((column_bits >> column) & 1)
            result |= value << (row * columns + column)
    return result


def matrix_image(bits: int, n_vars: int) -> np.ndarray:
    """Return values and valid-mask channels in a fixed 32x32 canvas."""
    rows, columns = balanced_shape(n_vars)
    image = np.zeros((2, MAX_SIDE, MAX_SIDE), dtype=np.float32)
    for row in range(rows):
        for column in range(columns):
            image[0, row, column] = (bits >> (row * columns + column)) & 1
    image[1, :rows, :columns] = 1.0
    return image


def _all_live(bits: int, variables: Iterable[int], n_vars: int) -> bool:
    for variable in variables:
        mask = 1 << (n_vars - 1 - variable)
        if not any(((bits >> assignment) ^ (bits >> (assignment ^ mask))) & 1
                   for assignment in range(1 << n_vars) if not assignment & mask):
            return False
    return True


def _literal(variable: int, negate: bool) -> Expr:
    value: Expr = Var(variable)
    return Not(value) if negate else value


def _subfunction(variables: tuple[int, ...], mode: int, rng: random.Random, n_vars: int) -> Expr:
    """Build a deterministic-diverse subfunction and prove its stated support."""
    for attempt in range(64):
        literals = [_literal(variable, bool(rng.randrange(2))) for variable in variables]
        rng.shuffle(literals)
        choice = (mode + attempt) % 4
        value = literals[0]
        if choice == 0:
            for literal in literals[1:]:
                value = And(value, literal)
        elif choice == 1:
            for literal in literals[1:]:
                value = Or(value, literal)
        elif choice == 2:
            for literal in literals[1:]:
                value = Eqv(value, literal)
        else:
            for literal in literals[1:]:
                value = Imp(value, literal)
        if rng.randrange(2):
            value = Not(value)
        bits = reference_bits(value, n_vars)
        if _all_live(bits, variables, n_vars):
            return value
    raise ValueError("could not construct a full-support partition factor")


def _hidden_xor(left: Expr, right: Expr, split: str) -> Expr:
    if split == "train":
        return Or(And(left, Not(right)), And(Not(left), right))
    if split == "validation":
        return And(Or(left, right), Not(And(left, right)))
    if split == "test":
        return Not(Eqv(left, right))
    if split == "confirmatory":
        return Eqv(Not(left), right)
    raise ValueError("unknown split")


def _minterm(assignment: int, n_vars: int) -> Expr:
    literals = [_literal(index, not bool((assignment >> (n_vars - 1 - index)) & 1))
                for index in range(n_vars)]
    result = literals[0]
    for literal in literals[1:]:
        result = And(result, literal)
    return result


def make_decomposition_documents(seed: int, counts: tuple[int, int, int, int] = (48, 12, 12, 8),
                                 check=lambda: None) -> list[dict[str, Any]]:
    if (type(seed) is not int or not 0 <= seed < 2**32 or type(counts) is not tuple or len(counts) != 4
            or any(type(count) is not int or not 1 <= count <= limit
                   for count, limit in zip(counts, (64, 32, 32, 16)))):
        raise ValueError("invalid finite decomposition corpus bounds")
    documents: list[dict[str, Any]] = []
    semantic_seen: set[tuple[int, int]] = set()
    for split, count in zip(SPLITS, counts):
        rng = random.Random(f"{seed}:{split}:balanced-xor-decomposition/v1")
        accepted = 0
        for attempt in range(count * 400):
            check()
            if accepted == count:
                break
            n_vars = SIZES[split][accepted % len(SIZES[split])]
            cut = n_vars // 2
            left = _subfunction(tuple(range(cut)), accepted + attempt, rng, n_vars)
            right = _subfunction(tuple(range(cut, n_vars)), accepted + attempt + 1, rng, n_vars)
            positive_expr = _hidden_xor(left, right, split)
            positive_bits = reference_bits(positive_expr, n_vars)
            witness = xor_partition_witness(positive_bits, n_vars)
            if witness is None or compose_xor_factors(witness, n_vars) != positive_bits:
                raise ValueError("positive generator failed exact decomposition")
            flip_assignment = rng.randrange(1 << n_vars)
            negative_expr = Xor(positive_expr, _minterm(flip_assignment, n_vars))
            negative_bits = reference_bits(negative_expr, n_vars)
            if xor_partition_witness(negative_bits, n_vars) is not None or (positive_bits ^ negative_bits).bit_count() != 1:
                raise ValueError("negative generator failed distance-one control")
            if (n_vars, positive_bits) in semantic_seen or (n_vars, negative_bits) in semantic_seen:
                continue
            parent_id = f"{split}-{accepted:03d}"
            for label, expr, bits, exact_witness in (
                    (1, positive_expr, positive_bits, witness), (0, negative_expr, negative_bits, None)):
                semantic_seen.add((n_vars, bits))
                document = expr_to_json_dag(expr)
                documents.append({
                    "case_id": f"{parent_id}-{label}", "parent_id": parent_id, "split": split,
                    "family": "balanced_xor_decomposable" if label else "one_cell_near_decomposition",
                    "n_vars": n_vars, "label": label, "distance_to_parent": 0 if label else 1,
                    "flip_assignment": None if label else flip_assignment,
                    "source_id": f"generated:{TEMPLATES[split]}", "template": TEMPLATES[split],
                    "digest": structural_digest(expr),
                    "alpha_digest": structural_digest(expr, alpha_rename=True),
                    "semantic_sha256": packed_sha256(bits, n_vars), "witness": exact_witness,
                    "expression": document,
                })
            accepted += 1
        if accepted != count:
            raise ValueError("finite generator could not satisfy decomposition corpus request")
    validate_decomposition_documents(documents, counts=counts, check=check)
    return documents


def case_from_document(data: dict[str, Any]) -> tuple[Expr, int]:
    if type(data) is not dict or type(data.get("n_vars")) is not int:
        raise ValueError("invalid decomposition document")
    n_vars = data["n_vars"]
    expr = expr_from_json(data["expression"])
    admit(expr, n_vars, 1)
    if expr_to_json_dag(expr) != data["expression"]:
        raise ValueError("noncanonical expression document")
    return expr, reference_bits(expr, n_vars)


def validate_decomposition_documents(documents: list[dict[str, Any]], counts=None, check=lambda: None):
    if type(documents) is not list or not 8 <= len(documents) <= 288 or len(documents) % 2:
        raise ValueError("invalid decomposition dataset row bound")
    ids: set[str] = set()
    semantics: set[tuple[int, int]] = set()
    parents: dict[str, list[tuple[dict[str, Any], int]]] = {}
    split_counts = {split: 0 for split in SPLITS}
    for data in documents:
        check()
        required = {"case_id", "parent_id", "split", "family", "n_vars", "label", "distance_to_parent",
                    "flip_assignment", "source_id", "template", "digest", "alpha_digest",
                    "semantic_sha256", "witness", "expression"}
        if (type(data) is not dict or set(data) != required or data["split"] not in SPLITS
                or type(data["case_id"]) is not str or data["case_id"] in ids
                or type(data["label"]) is not int or data["label"] not in (0, 1)
                or data["n_vars"] not in SIZES[data["split"]]
                or data["template"] != TEMPLATES[data["split"]]
                or data["source_id"] != f"generated:{TEMPLATES[data['split']]}"):
            raise ValueError("invalid decomposition dataset metadata")
        ids.add(data["case_id"])
        expr, bits = case_from_document(data)
        witness = xor_partition_witness(bits, data["n_vars"])
        if (data["label"] != int(witness is not None)
                or data["family"] != ("balanced_xor_decomposable" if data["label"] else "one_cell_near_decomposition")
                or data["distance_to_parent"] != (0 if data["label"] else 1)
                or data["witness"] != witness or data["digest"] != structural_digest(expr)
                or data["alpha_digest"] != structural_digest(expr, alpha_rename=True)
                or data["semantic_sha256"] != packed_sha256(bits, data["n_vars"])):
            raise ValueError("decomposition identity, semantics, or witness disagreement")
        identity = (data["n_vars"], bits)
        if identity in semantics:
            raise ValueError("duplicate semantic function")
        semantics.add(identity)
        parents.setdefault(data["parent_id"], []).append((data, bits))
        split_counts[data["split"]] += 1
    for parent, pair in parents.items():
        if len(pair) != 2 or {item[0]["label"] for item in pair} != {0, 1}:
            raise ValueError(f"unbalanced generated pair: {parent}")
        positive = next(item for item in pair if item[0]["label"] == 1)
        negative = next(item for item in pair if item[0]["label"] == 0)
        if (positive[0]["split"] != negative[0]["split"] or positive[0]["n_vars"] != negative[0]["n_vars"]
                or (positive[1] ^ negative[1]).bit_count() != 1):
            raise ValueError("parent pair split, size, or exact distance disagreement")
    if counts is not None and split_counts != {split: 2 * count for split, count in zip(SPLITS, counts)}:
        raise ValueError("split count disagreement")
    if any(value == 0 for value in split_counts.values()):
        raise ValueError("missing required split")
    return {
        "split_counts": split_counts, "parent_count": len(parents), "semantic_functions": len(semantics),
        "exact_duplicates": 0, "target": "balanced-partition GF(2) XOR decomposition",
        "limitation": "Synthetic hidden-decomposition/distance-one mechanism pairs; not natural positives.",
    }
