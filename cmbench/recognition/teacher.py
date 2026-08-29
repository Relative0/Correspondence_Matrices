"""Small exact CM/cofactor teacher with explicit, executable layout semantics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from cm_exprlib import Expr, Not, Var, Xor
from cmbench.output_budget import OutputBudget, decide_output_budget, estimate_explicit_output, require_output_budget

from .portfolio import admit, reference_bits

TEACHER_SCHEMA = "crse-cm-teacher/v1"
INPUT_SCHEMA = "cm-values256-valid256-msb-assignments/v1"
MAX_SUPPORT = 8


@dataclass(frozen=True)
class CMLayout:
    row_variables: tuple[int, ...]
    column_variables: tuple[int, ...]

    def __post_init__(self):
        if type(self.row_variables) is not tuple or type(self.column_variables) is not tuple:
            raise ValueError("variable partitions must be tuples")
        variables = self.variables
        if (len(variables) > MAX_SUPPORT or len(set(variables)) != len(variables)
                or any(type(v) is not int or not 0 <= v < MAX_SUPPORT for v in variables)):
            raise ValueError("invalid bounded CM partition")

    @property
    def variables(self) -> tuple[int, ...]:
        return self.row_variables + self.column_variables

    @property
    def shape(self) -> tuple[int, int]:
        return 1 << len(self.row_variables), 1 << len(self.column_variables)

    def labels(self) -> list[dict[int, int]]:
        k = len(self.variables)
        return [{v: (row >> (k - 1 - j)) & 1 for j, v in enumerate(self.variables)}
                for row in range(1 << k)]

    def to_dict(self) -> dict[str, Any]:
        return {"row_variables": list(self.row_variables), "column_variables": list(self.column_variables),
                "shape": list(self.shape), "assignment_order": "ascending-binary-first-variable-MSB",
                "packed_bit_order": "assignment-index-is-LSB-bit-index",
                "assignment_labels": [{str(k): v for k, v in label.items()} for label in self.labels()]}


@dataclass(frozen=True)
class ExactCM:
    layout: CMLayout
    bits: int

    def __post_init__(self):
        if type(self.layout) is not CMLayout:
            raise ValueError("invalid layout")
        k = len(self.layout.variables)
        require_output_budget(decide_output_budget(
            OutputBudget(max_output_vars=8, max_output_bytes=256),
            estimate_explicit_output(k, "truth_table_uint8")))
        if type(self.bits) is not int or self.bits < 0 or self.bits.bit_length() > (1 << k):
            raise ValueError("invalid bits or nonzero padding")

    @property
    def valid_mask(self) -> int:
        return (1 << (1 << len(self.layout.variables))) - 1

    def to_dict(self) -> dict[str, Any]:
        return {"schema": TEACHER_SCHEMA, "layout": self.layout.to_dict(),
                "bits_hex": hex(self.bits), "valid_mask_hex": hex(self.valid_mask)}

    def tensor(self) -> np.ndarray:
        """Fixed bounded input: truth values then valid-position mask; zero padding."""
        count = 1 << len(self.layout.variables)
        values = np.zeros(512, dtype=np.float32)
        values[:count] = [(self.bits >> i) & 1 for i in range(count)]
        values[256:256 + count] = 1
        return values

    def reorder(self, layout: CMLayout) -> ExactCM:
        if set(layout.variables) != set(self.layout.variables):
            raise ValueError("reorder must preserve variable universe")
        bits = 0
        for target_index, assignment in enumerate(layout.labels()):
            source_index = 0
            for variable in self.layout.variables:
                source_index = (source_index << 1) | assignment[variable]
            bits |= ((self.bits >> source_index) & 1) << target_index
        return ExactCM(layout, bits)

    def transpose(self) -> ExactCM:
        return self.reorder(CMLayout(self.layout.column_variables, self.layout.row_variables))

    def negate_output(self) -> ExactCM:
        return ExactCM(self.layout, self.bits ^ self.valid_mask)

    def negate_inputs(self, variables: tuple[int, ...]) -> ExactCM:
        if (type(variables) is not tuple or len(set(variables)) != len(variables)
                or any(type(v) is not int or v not in self.layout.variables for v in variables)):
            raise ValueError("invalid negated inputs")
        k = len(self.layout.variables)
        flip = sum(1 << (k - 1 - self.layout.variables.index(v)) for v in variables)
        return ExactCM(self.layout, sum(((self.bits >> (i ^ flip)) & 1) << i for i in range(1 << k)))

    def cofactor(self, fixed: Mapping[int, int]) -> ExactCM:
        if (not isinstance(fixed, Mapping) or any(type(v) is not int or v not in self.layout.variables
                or type(value) is not int or value not in (0, 1) for v, value in fixed.items())):
            raise ValueError("invalid cofactor context")
        layout = CMLayout(tuple(v for v in self.layout.row_variables if v not in fixed),
                          tuple(v for v in self.layout.column_variables if v not in fixed))
        bits = 0
        for index, partial in enumerate(layout.labels()):
            assignment = dict(partial)
            assignment.update(fixed)
            source_index = 0
            for variable in self.layout.variables:
                source_index = (source_index << 1) | assignment[variable]
            bits |= ((self.bits >> source_index) & 1) << index
        return ExactCM(layout, bits)


def teach(expr: Expr, n_vars: int) -> ExactCM:
    if type(n_vars) is not int or not 1 <= n_vars <= MAX_SUPPORT:
        raise ValueError("teacher supports at most eight variables")
    admit(expr, n_vars, 1)
    split = n_vars // 2
    return ExactCM(CMLayout(tuple(range(split)), tuple(range(split, n_vars))), reference_bits(expr, n_vars))


def affine_candidate(cm: ExactCM) -> Expr:
    """Interpolate k+1 points. This is a proposal, not an affine certificate."""
    variables = cm.layout.variables
    if not variables:
        raise ValueError("AST candidate requires a nonempty declared universe")
    constant = cm.bits & 1
    terms = [Var(v) for j, v in enumerate(variables)
             if ((cm.bits >> (1 << (len(variables) - 1 - j))) & 1) ^ constant]
    result = terms[0] if terms else Xor(Var(variables[0]), Var(variables[0]))
    for term in terms[1:]:
        result = Xor(result, term)
    return Not(result) if constant else result


def is_affine(cm: ExactCM) -> bool:
    constant = cm.bits & 1
    k = len(cm.layout.variables)
    coefficients = [((cm.bits >> (1 << (k - 1 - j))) & 1) ^ constant for j in range(k)]
    for index in range(1 << k):
        predicted = constant
        for j, coefficient in enumerate(coefficients):
            predicted ^= coefficient & ((index >> (k - 1 - j)) & 1)
        if predicted != ((cm.bits >> index) & 1):
            return False
    return True
