from __future__ import annotations

from typing import Callable, Dict, Tuple

import numpy as np


CM_2X2: Dict[str, np.ndarray] = {
    "TRUE": np.array([[1, 1], [1, 1]], dtype=bool),
    "FALSE": np.array([[0, 0], [0, 0]], dtype=bool),
    "EQV": np.array([[1, 0], [0, 1]], dtype=bool),
    "XOR": np.array([[0, 1], [1, 0]], dtype=bool),
    "AND": np.array([[1, 0], [0, 0]], dtype=bool),
    "NOR": np.array([[0, 0], [0, 1]], dtype=bool),
    "X_AND_NOT_Y": np.array([[0, 1], [0, 0]], dtype=bool),
    "NOT_X_AND_Y": np.array([[0, 0], [1, 0]], dtype=bool),
    "IMP": np.array([[1, 0], [1, 1]], dtype=bool),
    "RIMP": np.array([[1, 1], [0, 1]], dtype=bool),
    "OR": np.array([[1, 1], [1, 0]], dtype=bool),
    "NAND": np.array([[0, 1], [1, 1]], dtype=bool),
    "R": np.array([[1, 0], [1, 0]], dtype=bool),
    "NOT_R": np.array([[0, 1], [0, 1]], dtype=bool),
    "L": np.array([[1, 1], [0, 0]], dtype=bool),
    "NOT_L": np.array([[0, 0], [1, 1]], dtype=bool),
}


def cm_bool_array(x) -> np.ndarray:
    return np.asarray(x, dtype=bool)


def cm_matrix_key(a: np.ndarray) -> Tuple[Tuple[int, ...], ...]:
    arr = cm_bool_array(a)
    return tuple(tuple(int(v) for v in row) for row in arr.astype(np.uint8).tolist())


CM_2X2_TO_NAME = {cm_matrix_key(v): k for k, v in CM_2X2.items()}


def cm_complement(a: np.ndarray) -> np.ndarray:
    return np.logical_not(cm_bool_array(a))


def cm_transpose(a: np.ndarray) -> np.ndarray:
    return cm_bool_array(a).T


def cm_rotate90(a: np.ndarray) -> np.ndarray:
    return np.rot90(cm_bool_array(a), k=-1)


def cm_rotate180(a: np.ndarray) -> np.ndarray:
    return np.rot90(cm_bool_array(a), k=2)


def cm_rotate270(a: np.ndarray) -> np.ndarray:
    return np.rot90(cm_bool_array(a), k=1)


def cm_transform_swap_operands(a: np.ndarray) -> np.ndarray:
    return cm_transpose(a)


def cm_transform_negate_expression(a: np.ndarray) -> np.ndarray:
    return cm_complement(a)


def cm_transform_negate_right_operand(a: np.ndarray) -> np.ndarray:
    return cm_rotate90(cm_transpose(a))


def cm_transform_negate_left_operand(a: np.ndarray) -> np.ndarray:
    return cm_rotate270(cm_transpose(a))


def cm_transform_negate_both_operands(a: np.ndarray) -> np.ndarray:
    return cm_rotate180(a)


def _require_same_shape(a: np.ndarray, b: np.ndarray, op_name: str) -> None:
    if a.shape != b.shape:
        raise ValueError(f"CM {op_name} requires same shape / same basis")


def cm_quotient(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Directional CM quotient A \\ B = A & ~B on an aligned basis."""
    aa = cm_bool_array(a)
    bb = cm_bool_array(b)
    _require_same_shape(aa, bb, "quotient")
    return np.logical_and(aa, np.logical_not(bb))


def cm_symmetric_delta(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Feature symmetric difference on an aligned basis."""
    aa = cm_bool_array(a)
    bb = cm_bool_array(b)
    _require_same_shape(aa, bb, "symmetric delta")
    return np.logical_xor(aa, bb)


def cm_overlap(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    aa = cm_bool_array(a)
    bb = cm_bool_array(b)
    _require_same_shape(aa, bb, "overlap")
    return np.logical_and(aa, bb)


def cm_contains(container: np.ndarray, contained: np.ndarray) -> bool:
    """Return True iff every positive feature of contained is present in container."""
    return not bool(np.any(cm_quotient(contained, container)))


def cm_feature_counts(a: np.ndarray, b: np.ndarray) -> dict:
    aa = cm_bool_array(a)
    bb = cm_bool_array(b)
    _require_same_shape(aa, bb, "feature count")
    q_ab = cm_quotient(aa, bb)
    q_ba = cm_quotient(bb, aa)
    overlap = cm_overlap(aa, bb)
    sym = cm_symmetric_delta(aa, bb)
    overlap_count = int(np.count_nonzero(overlap))
    union_count = int(np.count_nonzero(np.logical_or(aa, bb)))
    return {
        "features_a": int(np.count_nonzero(aa)),
        "features_b": int(np.count_nonzero(bb)),
        "overlap_features": overlap_count,
        "a_minus_b_features": int(np.count_nonzero(q_ab)),
        "b_minus_a_features": int(np.count_nonzero(q_ba)),
        "symmetric_delta_features": int(np.count_nonzero(sym)),
        "a_contains_b": bool(cm_contains(aa, bb)),
        "b_contains_a": bool(cm_contains(bb, aa)),
        "jaccard_features": float(overlap_count / union_count) if union_count else 1.0,
    }


def cm_2x2_name(a: np.ndarray) -> str:
    return CM_2X2_TO_NAME.get(cm_matrix_key(a), "UNKNOWN")


def cm_2x2_eval(a: np.ndarray, x: bool, y: bool) -> bool:
    arr = cm_bool_array(a)
    if arr.shape != (2, 2):
        raise ValueError("2x2 operator evaluation requires a 2x2 matrix")
    return bool(arr[0 if x else 1, 0 if y else 1])


def cm_2x2_transform_correct(a: np.ndarray, transform: Callable[[np.ndarray], np.ndarray], kind: str) -> bool:
    transformed = transform(a)
    for x in (False, True):
        for y in (False, True):
            got = cm_2x2_eval(transformed, x, y)
            if kind == "transpose":
                expected = cm_2x2_eval(a, y, x)
            elif kind == "complement":
                expected = not cm_2x2_eval(a, x, y)
            elif kind == "negate_left_operand":
                expected = cm_2x2_eval(a, not x, y)
            elif kind == "negate_right_operand":
                expected = cm_2x2_eval(a, x, not y)
            elif kind == "negate_both_operands":
                expected = cm_2x2_eval(a, not x, not y)
            else:
                raise ValueError(f"unknown 2x2 transform correctness kind: {kind!r}")
            if got != expected:
                return False
    return True
