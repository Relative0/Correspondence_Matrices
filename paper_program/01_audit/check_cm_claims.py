"""Bounded exhaustive checks for the 2-variable Correspondence Matrix claims.

The bit order is the manuscript's row-major order:
    (X,Y) = (1,1), (1,0), (0,1), (0,0).

This script checks finite identities only. Passing it is not a proof of any
unbounded higher-dimensional or complexity claim.
"""

from __future__ import annotations

import json
from itertools import product


ASSIGNMENTS = ((1, 1), (1, 0), (0, 1), (0, 0))


def bits(token: int) -> tuple[int, int, int, int]:
    return tuple((token >> shift) & 1 for shift in (3, 2, 1, 0))


def matrix(token: int) -> tuple[tuple[int, int], tuple[int, int]]:
    a, b, c, d = bits(token)
    return ((a, b), (c, d))


def token_of(m: tuple[tuple[int, int], tuple[int, int]]) -> int:
    a, b = m[0]
    c, d = m[1]
    return (a << 3) | (b << 2) | (c << 1) | d


def value(token: int, x: int, y: int) -> int:
    row = 0 if x else 1
    col = 0 if y else 1
    return matrix(token)[row][col]


def xor_and_contract(token: int, x: int, y: int) -> int:
    """Evaluate the displayed bra-CM-ket contraction over GF(2)."""
    x_state = (x, 1 - x)
    y_state = (y, 1 - y)
    result = 0
    for row, col in product(range(2), repeat=2):
        result ^= x_state[row] & matrix(token)[row][col] & y_state[col]
    return result


def op(phi: int, left: int, right: int) -> int:
    return value(phi, left, right)


def pointwise(phi: int, left: int, right: int) -> int:
    return token_of(
        tuple(
            tuple(op(phi, matrix(left)[r][c], matrix(right)[r][c]) for c in range(2))
            for r in range(2)
        )
    )


def transpose(token: int) -> int:
    m = matrix(token)
    return token_of(((m[0][0], m[1][0]), (m[0][1], m[1][1])))


def swap_rows(token: int) -> int:
    m = matrix(token)
    return token_of((m[1], m[0]))


def swap_columns(token: int) -> int:
    m = matrix(token)
    return token_of(((m[0][1], m[0][0]), (m[1][1], m[1][0])))


def signed_align(
    token: int, *, swap_inputs: int, negate_first: int, negate_second: int
) -> int:
    """Rewrite f(U,V) into a token over target frame (X,Y).

    `swap_inputs=0` means (U,V)=(signed X, signed Y); `swap_inputs=1`
    means (U,V)=(signed Y, signed X). Negation flags refer to U and V.
    """
    aligned = transpose(token) if swap_inputs else token
    if swap_inputs:
        if negate_first:
            aligned = swap_columns(aligned)
        if negate_second:
            aligned = swap_rows(aligned)
    else:
        if negate_first:
            aligned = swap_rows(aligned)
        if negate_second:
            aligned = swap_columns(aligned)
    return aligned


def value_in_signed_frame(
    token: int,
    x: int,
    y: int,
    *,
    swap_inputs: int,
    negate_first: int,
    negate_second: int,
) -> int:
    first, second = ((y, x) if swap_inputs else (x, y))
    if negate_first:
        first = 1 - first
    if negate_second:
        second = 1 - second
    return value(token, first, second)


def logical_matrix_valuation(token: int, x: int, y: int) -> int:
    """Value every entry of L_f(X,Y) at X=x and Y=y."""
    return token_of(
        (
            (value(token, x, y), value(token, x, 1 - y)),
            (value(token, 1 - x, y), value(token, 1 - x, 1 - y)),
        )
    )


def anf_coefficients_from_truth(token: int) -> tuple[int, int, int, int]:
    """Return ANF coefficients indexed by subset mask 00, 01, 10, 11.

    Bit 0 represents Y and bit 1 represents X. This is the Boolean subset
    Mobius transform, deliberately separate from the formula-valued LM.
    """
    coefficients = [
        value(token, (mask >> 1) & 1, mask & 1) for mask in range(4)
    ]
    for variable_bit in range(2):
        for mask in range(4):
            if mask & (1 << variable_bit):
                coefficients[mask] ^= coefficients[mask ^ (1 << variable_bit)]
    return tuple(coefficients)


def evaluate_anf(coefficients: tuple[int, ...], x: int, y: int) -> int:
    valuation_mask = (x << 1) | y
    result = 0
    for monomial_mask, coefficient in enumerate(coefficients):
        if monomial_mask & ~valuation_mask == 0:
            result ^= coefficient
    return result


def rotate_cw(token: int) -> int:
    m = matrix(token)
    return token_of(((m[1][0], m[0][0]), (m[1][1], m[0][1])))


def rotate(token: int, quarter_turns: int) -> int:
    for _ in range(quarter_turns % 4):
        token = rotate_cw(token)
    return token


def check() -> dict[str, object]:
    failures: dict[str, list[object]] = {
        "unique_representation": [],
        "xor_and_contraction": [],
        "swap_transpose": [],
        "output_negation": [],
        "right_input_negation": [],
        "left_input_negation": [],
        "both_inputs_negated": [],
        "signed_operand_alignment": [],
        "signed_alignment_fusion": [],
        "xor_xnor_impax_geometry": [],
        "xor_linearity": [],
        "same_operands_hinge": [],
        "lm_positive_valuation": [],
        "lm_general_valuation_frame": [],
        "lm_coefficient_extraction": [],
        "lm_valuation_commutes_with_fusion": [],
        "anf_mobius_round_trip": [],
        "quotient_as_boolean_difference": [],
    }

    seen = {bits(token) for token in range(16)}
    if len(seen) != 16:
        failures["unique_representation"].append(len(seen))

    xor_token = 0x6
    xnor_token = 0x9
    impax_token = 0xF
    if rotate(xnor_token, 1) != xor_token:
        failures["xor_xnor_impax_geometry"].append("clockwise_rotation")
    if rotate(xnor_token, 3) != xor_token:
        failures["xor_xnor_impax_geometry"].append("counterclockwise_rotation")
    if (xnor_token ^ 0xF) != xor_token:
        failures["xor_xnor_impax_geometry"].append("entrywise_complement")
    if (xnor_token ^ xor_token) != impax_token:
        failures["xor_xnor_impax_geometry"].append("impax_superposition")
    for x, y in ASSIGNMENTS:
        if xor_and_contract(impax_token, x, y) != 1:
            failures["xor_xnor_impax_geometry"].append(
                ("impax_tautology", x, y)
            )

    for theta in range(16):
        for x, y in ASSIGNMENTS:
            if xor_and_contract(theta, x, y) != value(theta, x, y):
                failures["xor_and_contraction"].append((theta, x, y))
            if value(theta, y, x) != value(transpose(theta), x, y):
                failures["swap_transpose"].append((theta, x, y))
            if 1 - value(theta, x, y) != value(theta ^ 0xF, x, y):
                failures["output_negation"].append((theta, x, y))
            if value(theta, x, 1 - y) != value(rotate(transpose(theta), 1), x, y):
                failures["right_input_negation"].append((theta, x, y))
            if value(theta, 1 - x, y) != value(rotate(transpose(theta), 3), x, y):
                failures["left_input_negation"].append((theta, x, y))
            if value(theta, 1 - x, 1 - y) != value(rotate(theta, 2), x, y):
                failures["both_inputs_negated"].append((theta, x, y))

            valued_lm = logical_matrix_valuation(theta, x, y)
            expected_frame = theta
            if not x:
                expected_frame = swap_rows(expected_frame)
            if not y:
                expected_frame = swap_columns(expected_frame)
            if valued_lm != expected_frame:
                failures["lm_general_valuation_frame"].append((theta, x, y))

            for row_coefficient, col_coefficient in ASSIGNMENTS:
                row_formula_value = x if row_coefficient else 1 - x
                col_formula_value = y if col_coefficient else 1 - y
                measured = xor_and_contract(
                    valued_lm, row_formula_value, col_formula_value
                )
                if measured != value(theta, row_coefficient, col_coefficient):
                    failures["lm_coefficient_extraction"].append(
                        (
                            theta,
                            x,
                            y,
                            row_coefficient,
                            col_coefficient,
                        )
                    )

        if logical_matrix_valuation(theta, 1, 1) != theta:
            failures["lm_positive_valuation"].append(theta)

        coefficients = anf_coefficients_from_truth(theta)
        for x, y in ASSIGNMENTS:
            if evaluate_anf(coefficients, x, y) != value(theta, x, y):
                failures["anf_mobius_round_trip"].append(
                    (theta, coefficients, x, y)
                )

    for left, right in product(range(16), repeat=2):
        for x, y in ASSIGNMENTS:
            if value(left ^ right, x, y) != value(left, x, y) ^ value(right, x, y):
                failures["xor_linearity"].append((left, right, x, y))
            difference = left & ((~right) & 0xF)
            if value(difference, x, y) != (value(left, x, y) and not value(right, x, y)):
                failures["quotient_as_boolean_difference"].append((left, right, x, y))

    for left, right, phi in product(range(16), repeat=3):
        combined = pointwise(phi, left, right)
        for x, y in ASSIGNMENTS:
            if value(combined, x, y) != op(phi, value(left, x, y), value(right, x, y)):
                failures["same_operands_hinge"].append((left, right, phi, x, y))
            valued_then_combined = pointwise(
                phi,
                logical_matrix_valuation(left, x, y),
                logical_matrix_valuation(right, x, y),
            )
            combined_then_valued = logical_matrix_valuation(combined, x, y)
            if valued_then_combined != combined_then_valued:
                failures["lm_valuation_commutes_with_fusion"].append(
                    (left, right, phi, x, y)
                )

    frames = tuple(product((0, 1), repeat=3))
    for theta in range(16):
        for swap_inputs, negate_first, negate_second in frames:
            aligned = signed_align(
                theta,
                swap_inputs=swap_inputs,
                negate_first=negate_first,
                negate_second=negate_second,
            )
            for x, y in ASSIGNMENTS:
                expected = value_in_signed_frame(
                    theta,
                    x,
                    y,
                    swap_inputs=swap_inputs,
                    negate_first=negate_first,
                    negate_second=negate_second,
                )
                if value(aligned, x, y) != expected:
                    failures["signed_operand_alignment"].append(
                        (
                            theta,
                            swap_inputs,
                            negate_first,
                            negate_second,
                            x,
                            y,
                        )
                    )

    for left, right, phi in product(range(16), repeat=3):
        for left_frame in frames:
            left_aligned = signed_align(
                left,
                swap_inputs=left_frame[0],
                negate_first=left_frame[1],
                negate_second=left_frame[2],
            )
            for right_frame in frames:
                right_aligned = signed_align(
                    right,
                    swap_inputs=right_frame[0],
                    negate_first=right_frame[1],
                    negate_second=right_frame[2],
                )
                fused = pointwise(phi, left_aligned, right_aligned)
                for x, y in ASSIGNMENTS:
                    expected = op(
                        phi,
                        value_in_signed_frame(
                            left,
                            x,
                            y,
                            swap_inputs=left_frame[0],
                            negate_first=left_frame[1],
                            negate_second=left_frame[2],
                        ),
                        value_in_signed_frame(
                            right,
                            x,
                            y,
                            swap_inputs=right_frame[0],
                            negate_first=right_frame[1],
                            negate_second=right_frame[2],
                        ),
                    )
                    if value(fused, x, y) != expected:
                        failures["signed_alignment_fusion"].append(
                            (left, right, phi, left_frame, right_frame, x, y)
                        )

    standard_modulo_undefined_cases = [
        (a, b) for a, b in product((0, 1), repeat=2) if b == 0
    ]
    dimensions = [
        {
            "variable_count": 2 * m,
            "square_side": 2**m,
            "truth_table_entries": 2 ** (2 * m),
            "one_hot_basis_matrices": 2 ** (2 * m),
        }
        for m in range(1, 5)
    ]

    return {
        "checked_tokens": 16,
        "checked_hinge_cases": 16**3 * 4,
        "checked_signed_alignment_cases": 16 * 8 * 4,
        "checked_signed_alignment_fusion_cases": 16**3 * 8**2 * 4,
        "checked_xor_xnor_impax_identities": 8,
        "checked_lm_fusion_valuation_cases": 16**3 * 4,
        "checked_lm_coefficient_extractions": 16 * 4 * 4,
        "checked_anf_round_trips": 16 * 4,
        "all_finite_cm_identities_passed": all(not rows for rows in failures.values()),
        "failures": failures,
        "standard_integer_modulo_is_total_on_bits": not standard_modulo_undefined_cases,
        "standard_integer_modulo_undefined_cases": standard_modulo_undefined_cases,
        "square_truth_table_reshape_counts": dimensions,
        "scope_note": "Finite exhaustive checks are not a proof of unbounded claims or runtime complexity.",
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
