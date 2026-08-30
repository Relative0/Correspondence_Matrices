"""Exact bounded correspondence-matrix decomposition over GF(2).

Every accepted artifact stores an explicit variable order and factor payload,
then reconstructs the complete truth vector before its digest is accepted.
The analyzer proposes compression only; it never substitutes an unchecked
value for the source function.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .natural_decomposition import interaction_components, partitioned_bits
from .proved_rules import canonical

SCHEMA = "crse-exact-cm-gf2-artifact/v1"
MAX_VARS = 10
KINDS = ("xor_components", "gf2_rank", "cofactor_blocks", "kronecker")


def truth_sha256(bits: int, n_vars: int) -> str:
    _validate_bits(bits, n_vars)
    return hashlib.sha256(bits.to_bytes(max(1, (1 << n_vars) // 8), "little")).hexdigest()


def _validate_bits(bits: int, n_vars: int) -> None:
    if (type(n_vars) is not int or not 2 <= n_vars <= MAX_VARS or type(bits) is not int
            or bits < 0 or bits.bit_length() > (1 << n_vars)):
        raise ValueError("invalid bounded GF(2) truth vector")


def _partition(row_variables: Iterable[int], n_vars: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    row = tuple(row_variables)
    if (not row or len(row) == n_vars or len(set(row)) != len(row)
            or any(type(value) is not int or not 0 <= value < n_vars for value in row)):
        raise ValueError("invalid GF(2) matrix partition")
    column = tuple(value for value in range(n_vars) if value not in row)
    return row, column


def _unpartition(arranged: int, n_vars: int, row_variables: Iterable[int]) -> int:
    row, column = _partition(row_variables, n_vars)
    rows, columns = 1 << len(row), 1 << len(column)
    if type(arranged) is not int or arranged < 0 or arranged.bit_length() > rows * columns:
        raise ValueError("invalid arranged GF(2) matrix")
    result = 0
    for row_assignment in range(rows):
        for column_assignment in range(columns):
            original = 0
            for local, variable in enumerate(row):
                original |= ((row_assignment >> (len(row) - 1 - local)) & 1) << (n_vars - 1 - variable)
            for local, variable in enumerate(column):
                original |= ((column_assignment >> (len(column) - 1 - local)) & 1) << (n_vars - 1 - variable)
            result |= ((arranged >> (row_assignment * columns + column_assignment)) & 1) << original
    return result


def gf2_rank_factor(rows: Iterable[int], width: int) -> tuple[int, tuple[int, ...], tuple[int, ...]]:
    """Return rank, row coefficients U, and basis rows V with U*V exact."""
    values = tuple(rows)
    if (type(width) is not int or not 1 <= width <= 512 or not values
            or any(type(row) is not int or row < 0 or row.bit_length() > width for row in values)):
        raise ValueError("invalid GF(2) matrix rows")
    basis: list[int] = []
    pivot_to_index: dict[int, int] = {}
    coefficients = []
    for row in values:
        residual, coefficient = row, 0
        for pivot in sorted(pivot_to_index, reverse=True):
            if residual & (1 << pivot):
                index = pivot_to_index[pivot]
                residual ^= basis[index]
                coefficient ^= 1 << index
        if residual:
            pivot = residual.bit_length() - 1
            index = len(basis)
            pivot_to_index[pivot] = index
            basis.append(residual)
            coefficient ^= 1 << index
        coefficients.append(coefficient)
    for row, coefficient in zip(values, coefficients):
        reconstructed = 0
        for index, basis_row in enumerate(basis):
            if coefficient & (1 << index):
                reconstructed ^= basis_row
        if reconstructed != row:
            raise RuntimeError("GF(2) elimination recomposition failed")
    return len(basis), tuple(coefficients), tuple(basis)


def _matrix_rows(arranged: int, rows: int, columns: int) -> tuple[int, ...]:
    mask = (1 << columns) - 1
    return tuple((arranged >> (index * columns)) & mask for index in range(rows))


def _matrix_columns(arranged: int, rows: int, columns: int) -> tuple[int, ...]:
    return tuple(sum(((arranged >> (row * columns + column)) & 1) << row
                     for row in range(rows)) for column in range(columns))


def _compose_xor(payload: dict[str, Any], n_vars: int) -> int:
    result = 0
    factors = payload.get("factors")
    constant = payload.get("constant")
    if type(constant) is not int or constant not in (0, 1) or type(factors) is not list:
        raise ValueError("invalid XOR-component payload")
    for assignment in range(1 << n_vars):
        value = constant
        seen = set()
        for factor in factors:
            if type(factor) is not dict or set(factor) != {"variables", "variable_mask", "bits_hex"}:
                raise ValueError("invalid XOR factor")
            variables = factor["variables"]
            if (type(variables) is not list or not variables or any(type(v) is not int for v in variables)
                    or variables != sorted(variables) or set(variables) & seen
                    or factor["variable_mask"] != sum(1 << v for v in variables)):
                raise ValueError("invalid XOR factor variables")
            seen.update(variables)
            local = 0
            for variable in variables:
                local = (local << 1) | ((assignment >> (n_vars - 1 - variable)) & 1)
            bits = int(factor["bits_hex"], 16)
            if bits < 0 or bits.bit_length() > (1 << len(variables)):
                raise ValueError("invalid XOR factor bits")
            value ^= (bits >> local) & 1
        if seen != set(range(n_vars)):
            raise ValueError("XOR factors do not cover the variable universe")
        result |= value << assignment
    return result


def _compose_rank(payload: dict[str, Any], n_vars: int, row_variables: tuple[int, ...]) -> int:
    required = {"rank", "row_coefficients", "basis_rows", "matrix_shape"}
    if type(payload) is not dict or set(payload) != required:
        raise ValueError("invalid GF(2)-rank payload")
    rows, columns = payload["matrix_shape"]
    rank = payload["rank"]
    coefficients, basis = payload["row_coefficients"], payload["basis_rows"]
    if (rows != 1 << len(row_variables) or columns != 1 << (n_vars - len(row_variables))
            or type(rank) is not int or rank <= 0 or type(coefficients) is not list
            or type(basis) is not list or len(coefficients) != rows or len(basis) != rank):
        raise ValueError("invalid GF(2)-rank dimensions")
    matrix = 0
    for row_index, coefficient in enumerate(coefficients):
        if type(coefficient) is not int or coefficient < 0 or coefficient.bit_length() > rank:
            raise ValueError("invalid GF(2) coefficient")
        value = 0
        for index, basis_row in enumerate(basis):
            if type(basis_row) is not int or basis_row < 0 or basis_row.bit_length() > columns:
                raise ValueError("invalid GF(2) basis row")
            if coefficient & (1 << index):
                value ^= basis_row
        matrix |= value << (row_index * columns)
    return _unpartition(matrix, n_vars, row_variables)


def _compose_cofactor(payload: dict[str, Any], n_vars: int, row_variables: tuple[int, ...]) -> int:
    required = {"orientation", "representatives", "references", "matrix_shape"}
    if type(payload) is not dict or set(payload) != required:
        raise ValueError("invalid cofactor payload")
    rows, columns = payload["matrix_shape"]
    orientation = payload["orientation"]
    representatives, references = payload["representatives"], payload["references"]
    if (rows != 1 << len(row_variables) or columns != 1 << (n_vars - len(row_variables))
            or orientation not in {"rows", "columns"} or type(representatives) is not list
            or not representatives or type(references) is not list):
        raise ValueError("invalid cofactor dimensions")
    width, count = (columns, rows) if orientation == "rows" else (rows, columns)
    if len(references) != count:
        raise ValueError("invalid cofactor reference count")
    patterns = []
    mask = (1 << width) - 1
    for reference in references:
        if (type(reference) is not list or len(reference) != 2 or type(reference[0]) is not int
                or not 0 <= reference[0] < len(representatives) or type(reference[1]) is not int
                or reference[1] not in (0, 1)):
            raise ValueError("invalid cofactor reference")
        representative = representatives[reference[0]]
        if type(representative) is not int or representative < 0 or representative.bit_length() > width:
            raise ValueError("invalid cofactor representative")
        patterns.append(representative ^ (mask if reference[1] else 0))
    matrix = 0
    if orientation == "rows":
        for row, pattern in enumerate(patterns):
            matrix |= pattern << (row * columns)
    else:
        for column, pattern in enumerate(patterns):
            for row in range(rows):
                matrix |= ((pattern >> row) & 1) << (row * columns + column)
    return _unpartition(matrix, n_vars, row_variables)


def _compose_kronecker(payload: dict[str, Any], n_vars: int, row_variables: tuple[int, ...]) -> int:
    required = {"matrix_shape", "left_shape", "right_shape", "left_bits", "right_bits"}
    if type(payload) is not dict or set(payload) != required:
        raise ValueError("invalid Kronecker payload")
    rows, columns = payload["matrix_shape"]
    left_rows, left_columns = payload["left_shape"]
    right_rows, right_columns = payload["right_shape"]
    left, right = payload["left_bits"], payload["right_bits"]
    if (rows != left_rows * right_rows or columns != left_columns * right_columns
            or rows != 1 << len(row_variables) or columns != 1 << (n_vars - len(row_variables))
            or any(type(value) is not int or value <= 0 for value in
                   (left_rows, left_columns, right_rows, right_columns))
            or type(left) is not int or type(right) is not int or left < 0 or right < 0
            or left.bit_length() > left_rows * left_columns
            or right.bit_length() > right_rows * right_columns):
        raise ValueError("invalid Kronecker factor dimensions")
    matrix = 0
    for lr in range(left_rows):
        for lc in range(left_columns):
            if not ((left >> (lr * left_columns + lc)) & 1):
                continue
            for rr in range(right_rows):
                for rc in range(right_columns):
                    value = (right >> (rr * right_columns + rc)) & 1
                    row, column = lr * right_rows + rr, lc * right_columns + rc
                    matrix |= value << (row * columns + column)
    return _unpartition(matrix, n_vars, row_variables)


@dataclass(frozen=True)
class ExactGF2Artifact:
    document: dict[str, Any]

    @property
    def digest(self) -> str:
        return self.document["payload_sha256"]

    @property
    def kind(self) -> str:
        return self.document["kind"]

    def reconstruct(self) -> int:
        kind, n_vars = self.kind, self.document["n_vars"]
        row = tuple(self.document["row_variables"])
        if kind == "xor_components":
            return _compose_xor(self.document["payload"], n_vars)
        if kind == "gf2_rank":
            return _compose_rank(self.document["payload"], n_vars, row)
        if kind == "cofactor_blocks":
            return _compose_cofactor(self.document["payload"], n_vars, row)
        if kind == "kronecker":
            return _compose_kronecker(self.document["payload"], n_vars, row)
        raise ValueError("unknown GF(2) artifact kind")

    def to_dict(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.document, allow_nan=False))

    @classmethod
    def from_dict(cls, data: Any) -> "ExactGF2Artifact":
        keys = {"schema", "kind", "n_vars", "variable_order", "row_variables",
                "column_variables", "row_mask", "column_mask", "full_truth_bits",
                "factor_bits", "compression_ratio", "source_sha256", "payload",
                "payload_sha256"}
        if type(data) is not dict or set(data) != keys:
            raise ValueError("invalid GF(2) artifact fields")
        payload = {key: data[key] for key in keys - {"payload_sha256"}}
        n_vars, kind = data["n_vars"], data["kind"]
        if (data["schema"] != SCHEMA or kind not in KINDS or type(n_vars) is not int
                or not 2 <= n_vars <= MAX_VARS or data["variable_order"] != list(range(n_vars))
                or data["full_truth_bits"] != 1 << n_vars
                or type(data["factor_bits"]) is not int or data["factor_bits"] <= 0
                or data["compression_ratio"] != (1 << n_vars) / data["factor_bits"]
                or hashlib.sha256(canonical(payload)).hexdigest() != data["payload_sha256"]):
            raise ValueError("invalid GF(2) artifact identity")
        row, column = tuple(data["row_variables"]), tuple(data["column_variables"])
        if kind == "xor_components":
            if row or column or data["row_mask"] or data["column_mask"]:
                raise ValueError("XOR-component artifact must use factor-local masks")
        else:
            expected_row, expected_column = _partition(row, n_vars)
            if (column != expected_column or data["row_mask"] != sum(1 << value for value in row)
                    or data["column_mask"] != sum(1 << value for value in column)):
                raise ValueError("GF(2) artifact partition identity mismatch")
        artifact = cls(json.loads(json.dumps(data, allow_nan=False)))
        if truth_sha256(artifact.reconstruct(), n_vars) != data["source_sha256"]:
            raise ValueError("GF(2) artifact exact reconstruction failed")
        return artifact

    def save(self, path: Path) -> None:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(self.document, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")

    @classmethod
    def load(cls, path: Path, *, max_bytes: int = 2_000_000) -> "ExactGF2Artifact":
        raw = path.read_bytes()
        if len(raw) > max_bytes:
            raise ValueError("GF(2) artifact exceeds size bound")
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate GF(2) artifact key")
                result[key] = value
            return result
        return cls.from_dict(json.loads(raw, object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite GF(2) value"))))


def _artifact(kind: str, bits: int, n_vars: int, factor_bits: int, payload: dict[str, Any],
              row_variables: Iterable[int] = ()) -> ExactGF2Artifact:
    row = tuple(row_variables)
    column = tuple(value for value in range(n_vars) if value not in row) if row else ()
    body = {"schema": SCHEMA, "kind": kind, "n_vars": n_vars,
            "variable_order": list(range(n_vars)), "row_variables": list(row),
            "column_variables": list(column), "row_mask": sum(1 << value for value in row),
            "column_mask": sum(1 << value for value in column),
            "full_truth_bits": 1 << n_vars, "factor_bits": factor_bits,
            "compression_ratio": (1 << n_vars) / factor_bits,
            "source_sha256": truth_sha256(bits, n_vars), "payload": payload}
    return ExactGF2Artifact.from_dict({**body,
        "payload_sha256": hashlib.sha256(canonical(body)).hexdigest()})


def xor_component_artifact(bits: int, n_vars: int) -> ExactGF2Artifact | None:
    _validate_bits(bits, n_vars)
    components = interaction_components(bits, n_vars)
    if len(components) < 2:
        return None
    constant = bits & 1
    factors = []
    for component in components:
        local_bits = 0
        for local in range(1 << len(component)):
            assignment = 0
            for index, variable in enumerate(component):
                assignment |= ((local >> (len(component) - 1 - index)) & 1) << (n_vars - 1 - variable)
            local_bits |= (((bits >> assignment) & 1) ^ constant) << local
        factors.append({"variables": list(component),
                        "variable_mask": sum(1 << value for value in component),
                        "bits_hex": hex(local_bits)})
    factor_bits = 1 + sum(1 << len(component) for component in components)
    artifact = _artifact("xor_components", bits, n_vars, factor_bits,
                         {"constant": constant, "factors": factors})
    return artifact if factor_bits < 1 << n_vars else None


def rank_artifact(bits: int, n_vars: int, row_variables: Iterable[int]) -> ExactGF2Artifact | None:
    _validate_bits(bits, n_vars)
    row, _column = _partition(row_variables, n_vars)
    arranged, row_count, column_count = partitioned_bits(bits, n_vars, row)
    rows, columns = 1 << row_count, 1 << column_count
    rank, coefficients, basis = gf2_rank_factor(_matrix_rows(arranged, rows, columns), columns)
    if rank == 0:
        return None
    factor_bits = rank * (rows + columns)
    if factor_bits >= rows * columns:
        return None
    return _artifact("gf2_rank", bits, n_vars, factor_bits,
                     {"rank": rank, "row_coefficients": list(coefficients),
                      "basis_rows": list(basis), "matrix_shape": [rows, columns]}, row)


def cofactor_artifacts(bits: int, n_vars: int, row_variables: Iterable[int]) -> tuple[ExactGF2Artifact, ...]:
    _validate_bits(bits, n_vars)
    row, _column = _partition(row_variables, n_vars)
    arranged, row_count, column_count = partitioned_bits(bits, n_vars, row)
    rows, columns = 1 << row_count, 1 << column_count
    result = []
    for orientation, patterns, width in (
            ("rows", _matrix_rows(arranged, rows, columns), columns),
            ("columns", _matrix_columns(arranged, rows, columns), rows)):
        mask = (1 << width) - 1
        representatives: list[int] = []
        index_by_canonical: dict[int, int] = {}
        references = []
        for pattern in patterns:
            canonical_pattern = min(pattern, pattern ^ mask)
            index = index_by_canonical.get(canonical_pattern)
            if index is None:
                index = len(representatives)
                index_by_canonical[canonical_pattern] = index
                representatives.append(canonical_pattern)
            references.append([index, int(pattern != canonical_pattern)])
        index_bits = max(1, math.ceil(math.log2(max(1, len(representatives)))))
        factor_bits = len(representatives) * width + len(patterns) * (index_bits + 1)
        if factor_bits < rows * columns and len(representatives) < len(patterns):
            result.append(_artifact("cofactor_blocks", bits, n_vars, factor_bits,
                {"orientation": orientation, "representatives": representatives,
                 "references": references, "matrix_shape": [rows, columns]}, row))
    return tuple(result)


def kronecker_artifacts(bits: int, n_vars: int, row_variables: Iterable[int]) -> tuple[ExactGF2Artifact, ...]:
    _validate_bits(bits, n_vars)
    row, _column = _partition(row_variables, n_vars)
    arranged, row_count, column_count = partitioned_bits(bits, n_vars, row)
    rows, columns = 1 << row_count, 1 << column_count
    result = []
    for left_row_bits in range(1, row_count):
        for left_column_bits in range(1, column_count):
            left_rows, left_columns = 1 << left_row_bits, 1 << left_column_bits
            right_rows, right_columns = rows // left_rows, columns // left_columns
            blocks = []
            for left_row in range(left_rows):
                for left_column in range(left_columns):
                    block = 0
                    for right_row in range(right_rows):
                        for right_column in range(right_columns):
                            source_row = left_row * right_rows + right_row
                            source_column = left_column * right_columns + right_column
                            block |= ((arranged >> (source_row * columns + source_column)) & 1) << (
                                right_row * right_columns + right_column)
                    blocks.append(block)
            right = next((block for block in blocks if block), 0)
            if not right or any(block not in (0, right) for block in blocks):
                continue
            left = sum(int(block == right) << index for index, block in enumerate(blocks))
            factor_bits = left_rows * left_columns + right_rows * right_columns
            if factor_bits < rows * columns:
                result.append(_artifact("kronecker", bits, n_vars, factor_bits,
                    {"matrix_shape": [rows, columns],
                     "left_shape": [left_rows, left_columns],
                     "right_shape": [right_rows, right_columns],
                     "left_bits": left, "right_bits": right}, row))
    return tuple(result)


@dataclass(frozen=True)
class ExactGF2Analysis:
    n_vars: int
    source_sha256: str
    partitions_tested: int
    candidates: tuple[ExactGF2Artifact, ...]

    @property
    def best(self) -> ExactGF2Artifact | None:
        return min(self.candidates, key=lambda item: (item.document["factor_bits"], item.kind,
                   item.document["row_variables"])) if self.candidates else None

    @property
    def kinds(self) -> tuple[str, ...]:
        return tuple(sorted({candidate.kind for candidate in self.candidates}))


def candidate_partitions(bits: int, n_vars: int, max_partitions: int = 64) -> tuple[tuple[int, ...], ...]:
    _validate_bits(bits, n_vars)
    if type(max_partitions) is not int or not 1 <= max_partitions <= 256:
        raise ValueError("invalid GF(2) partition bound")
    candidates = set()
    components = interaction_components(bits, n_vars)
    if len(components) > 1:
        candidates.add(tuple(components[0]))
    for variable in range(n_vars):
        candidates.add((variable,))
    target = n_vars // 2
    balanced = []
    for size in sorted(range(1, n_vars), key=lambda value: (abs(value - target), value)):
        for row in itertools.combinations(range(n_vars), size):
            # A|B and B|A carry the same rank information; keep the side with x0.
            if 0 in row:
                balanced.append(row)
    ordered = sorted(candidates, key=lambda row: (abs(len(row) - target), row))
    ordered += [row for row in balanced if row not in candidates]
    return tuple(ordered[:max_partitions])


def analyze_exact_gf2(bits: int, n_vars: int, *,
                      row_partitions: Iterable[Iterable[int]] | None = None,
                      max_partitions: int = 64) -> ExactGF2Analysis:
    _validate_bits(bits, n_vars)
    partitions = (candidate_partitions(bits, n_vars, max_partitions) if row_partitions is None
                  else tuple(tuple(row) for row in row_partitions))
    if not partitions:
        raise ValueError("GF(2) analyzer requires at least one partition")
    candidates = []
    xor = xor_component_artifact(bits, n_vars)
    if xor is not None:
        candidates.append(xor)
    seen = {candidate.digest for candidate in candidates}
    for row in partitions:
        for candidate in ((rank_artifact(bits, n_vars, row),)
                          + cofactor_artifacts(bits, n_vars, row)
                          + kronecker_artifacts(bits, n_vars, row)):
            if candidate is not None and candidate.digest not in seen:
                if candidate.reconstruct() != bits:
                    raise RuntimeError("GF(2) candidate escaped exact reconstruction")
                candidates.append(candidate)
                seen.add(candidate.digest)
    candidates.sort(key=lambda item: (item.document["factor_bits"], item.kind,
                                      item.document["row_variables"], item.digest))
    return ExactGF2Analysis(n_vars, truth_sha256(bits, n_vars), len(partitions), tuple(candidates))
