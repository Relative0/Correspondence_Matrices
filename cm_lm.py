"""
cm_lm.py

Logical-matrix helpers for bra/ket vectors and 2x2 Correspondence Matrices (CMs).

Provides:
- bra()/ket() constructors (basis selectable)
- conversion between 2x2 CM arrays and 4-bit tokens (via cm_token)
- CM transpose/rotations (via cm_token)
- left/right application over boolean / xor / arithmetic semirings
"""

from __future__ import annotations

from typing import Dict, Literal, Union

import numpy as np

from cm_token import TOK, cm_rot180, cm_rot270, cm_rot90, cm_transpose


def bra(value: Union[int, bool], *, basis: Literal["not_first", "x_first"] = "x_first") -> np.ndarray:
    """Return 1x2 row vector for a boolean value with selectable basis.

    basis="not_first": encodes [¬X, X]
    basis="x_first": encodes [X, ¬X]
    """
    bit = int(bool(value))
    if basis == "not_first":
        return np.array([[1, 0]] if bit == 0 else [[0, 1]], dtype=np.uint8)
    if basis == "x_first":
        return np.array([[0, 1]] if bit == 0 else [[1, 0]], dtype=np.uint8)
    raise ValueError("Unknown basis; expected 'not_first' or 'x_first'")


def ket(value: Union[int, bool], *, basis: Literal["not_first", "x_first"] = "x_first") -> np.ndarray:
    """Return 2x1 column vector for a boolean value with selectable basis.

    basis="not_first": encodes [¬Y; Y]
    basis="x_first": encodes [Y; ¬Y]
    """
    bit = int(bool(value))
    if basis == "not_first":
        return np.array([[1], [0]] if bit == 0 else [[0], [1]], dtype=np.uint8)
    if basis == "x_first":
        return np.array([[0], [1]] if bit == 0 else [[1], [0]], dtype=np.uint8)
    raise ValueError("Unknown basis; expected 'not_first' or 'x_first'")


def bra_of(var_name: str, assignment: Dict[str, int], *, basis: Literal["not_first", "x_first"] = "x_first") -> np.ndarray:
    return bra(int(assignment.get(var_name, 0)), basis=basis)


def ket_of(var_name: str, assignment: Dict[str, int], *, basis: Literal["not_first", "x_first"] = "x_first") -> np.ndarray:
    return ket(int(assignment.get(var_name, 0)), basis=basis)


def cm_to_token(M: np.ndarray) -> int:
    """Encode a 2x2 CM into a 4-bit token (MSB→LSB: 11,12,21,22)."""
    if not isinstance(M, np.ndarray) or M.shape != (2, 2):
        raise ValueError("Expected a 2x2 numpy array for CM")
    a11 = int(M[0, 0]) & 1
    a12 = int(M[0, 1]) & 1
    a21 = int(M[1, 0]) & 1
    a22 = int(M[1, 1]) & 1
    return (a11 << 3) | (a12 << 2) | (a21 << 1) | a22


def token_to_cm(token: int) -> np.ndarray:
    """Decode a 4-bit token into a 2x2 uint8 matrix."""
    t = int(token) & 0xF
    return np.array([[(t >> 3) & 1, (t >> 2) & 1], [(t >> 1) & 1, t & 1]], dtype=np.uint8)


def op_to_cm(op: Union[str, int, np.ndarray]) -> np.ndarray:
    """Accept a 2x2 array, an operator name (e.g. 'AND'), or a 4-bit token."""
    if isinstance(op, np.ndarray):
        if op.shape != (2, 2):
            raise ValueError("CM array must be 2x2")
        return op.astype(np.uint8, copy=False)
    if isinstance(op, str):
        if op not in TOK:
            raise ValueError(f"Unknown operator name: {op}")
        return token_to_cm(TOK[op])
    return token_to_cm(int(op))


RotationKind = Literal["transpose", "T", "rot90", "rot180", "rot270", None]


def transform_cm(M: Union[np.ndarray, int, str], rotate: RotationKind) -> np.ndarray:
    A = op_to_cm(M)
    if rotate in (None,):
        return A
    t = cm_to_token(A)
    if rotate in ("transpose", "T"):
        t2 = cm_transpose(t)
    elif rotate == "rot90":
        t2 = cm_rot90(t)
    elif rotate == "rot180":
        t2 = cm_rot180(t)
    elif rotate == "rot270":
        t2 = cm_rot270(t)
    else:
        raise ValueError(f"Unknown rotate option: {rotate}")
    return token_to_cm(t2)


Semiring = Literal["bool", "arith", "xor"]


def bra_times_cm(
    B: np.ndarray,
    M: Union[np.ndarray, int, str],
    *,
    rotate: RotationKind = None,
    semiring: Semiring = "bool",
) -> np.ndarray:
    """Compute <X| Θ with optional transform of Θ."""
    if not isinstance(B, np.ndarray) or B.shape != (1, 2):
        raise ValueError("B must be a 1x2 bra vector")
    A = transform_cm(M, rotate)
    if semiring == "arith":
        return (B.astype(np.uint8, copy=False) @ A.astype(np.uint8, copy=False)).astype(np.uint8, copy=False).reshape(1, 2)
    x0 = int(B[0, 0]) & 1
    x1 = int(B[0, 1]) & 1
    a00 = int(A[0, 0]) & 1
    a01 = int(A[0, 1]) & 1
    a10 = int(A[1, 0]) & 1
    a11 = int(A[1, 1]) & 1
    if semiring == "xor":
        c0 = (x0 & a00) ^ (x1 & a10)
        c1 = (x0 & a01) ^ (x1 & a11)
    else:
        c0 = (x0 & a00) | (x1 & a10)
        c1 = (x0 & a01) | (x1 & a11)
    return np.array([[c0, c1]], dtype=np.uint8)


def cm_times_ket(
    M: Union[np.ndarray, int, str],
    K: np.ndarray,
    *,
    rotate: RotationKind = None,
    semiring: Semiring = "bool",
) -> np.ndarray:
    """Compute Θ |Y> with optional transform of Θ."""
    if not isinstance(K, np.ndarray) or K.shape != (2, 1):
        raise ValueError("K must be a 2x1 ket vector")
    A = transform_cm(M, rotate)
    if semiring == "arith":
        return (A.astype(np.uint8, copy=False) @ K.astype(np.uint8, copy=False)).astype(np.uint8, copy=False).reshape(2, 1)
    y0 = int(K[0, 0]) & 1
    y1 = int(K[1, 0]) & 1
    a00 = int(A[0, 0]) & 1
    a01 = int(A[0, 1]) & 1
    a10 = int(A[1, 0]) & 1
    a11 = int(A[1, 1]) & 1
    if semiring == "xor":
        r0 = (a00 & y0) ^ (a01 & y1)
        r1 = (a10 & y0) ^ (a11 & y1)
    else:
        r0 = (a00 & y0) | (a01 & y1)
        r1 = (a10 & y0) | (a11 & y1)
    return np.array([[r0], [r1]], dtype=np.uint8)


def bra_var_times_cm(
    var_name: str,
    assignment: Dict[str, int],
    M: Union[np.ndarray, int, str],
    *,
    rotate: RotationKind = None,
    semiring: Semiring = "bool",
    basis: Literal["not_first", "x_first"] = "x_first",
) -> np.ndarray:
    return bra_times_cm(bra_of(var_name, assignment, basis=basis), M, rotate=rotate, semiring=semiring)


def cm_times_ket_var(
    M: Union[np.ndarray, int, str],
    var_name: str,
    assignment: Dict[str, int],
    *,
    rotate: RotationKind = None,
    semiring: Semiring = "bool",
    basis: Literal["not_first", "x_first"] = "x_first",
) -> np.ndarray:
    return cm_times_ket(M, ket_of(var_name, assignment, basis=basis), rotate=rotate, semiring=semiring)


__all__ = [
    "bra",
    "ket",
    "bra_of",
    "ket_of",
    "cm_to_token",
    "token_to_cm",
    "op_to_cm",
    "transform_cm",
    "bra_times_cm",
    "cm_times_ket",
    "bra_var_times_cm",
    "cm_times_ket_var",
]

