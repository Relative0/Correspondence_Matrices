from __future__ import annotations

from typing import Tuple

import numpy as np

from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

try:
    from numba import njit

    HAS_NUMBA = True
except Exception:  # pragma: no cover - optional dependency
    HAS_NUMBA = False
    njit = None


OP_VAR = 0
OP_NOT = 1
OP_AND = 2
OP_OR = 3
OP_XOR = 4
OP_IMP = 5
OP_EQV = 6


def flatten_expr_numba(expr: Expr) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Encode Expr as a postorder stack program: opcode, arg0, arg1 arrays."""
    opcodes = []
    arg0 = []
    arg1 = []

    def emit(e: Expr) -> None:
        if isinstance(e, Var):
            opcodes.append(OP_VAR)
            arg0.append(int(e.i))
            arg1.append(-1)
            return
        if isinstance(e, Not):
            emit(e.a)
            opcodes.append(OP_NOT)
            arg0.append(-1)
            arg1.append(-1)
            return
        if isinstance(e, And):
            emit(e.a)
            emit(e.b)
            opcodes.append(OP_AND)
            arg0.append(-1)
            arg1.append(-1)
            return
        if isinstance(e, Or):
            emit(e.a)
            emit(e.b)
            opcodes.append(OP_OR)
            arg0.append(-1)
            arg1.append(-1)
            return
        if isinstance(e, Xor):
            emit(e.a)
            emit(e.b)
            opcodes.append(OP_XOR)
            arg0.append(-1)
            arg1.append(-1)
            return
        if isinstance(e, Imp):
            emit(e.a)
            emit(e.b)
            opcodes.append(OP_IMP)
            arg0.append(-1)
            arg1.append(-1)
            return
        if isinstance(e, Eqv):
            emit(e.a)
            emit(e.b)
            opcodes.append(OP_EQV)
            arg0.append(-1)
            arg1.append(-1)
            return
        raise TypeError(e)

    emit(expr)
    return (
        np.asarray(opcodes, dtype=np.int16),
        np.asarray(arg0, dtype=np.int32),
        np.asarray(arg1, dtype=np.int32),
    )


if HAS_NUMBA:

    @njit(cache=True)
    def _eval_program_numba(
        opcodes: np.ndarray, arg0: np.ndarray, arg1: np.ndarray, var_matrix: np.ndarray
    ) -> np.ndarray:
        n_rows = var_matrix.shape[0]
        n_ops = opcodes.shape[0]
        out = np.empty(n_rows, dtype=np.uint8)
        stack = np.empty(n_ops, dtype=np.uint8)

        for r in range(n_rows):
            sp = 0
            for i in range(n_ops):
                op = opcodes[i]
                if op == OP_VAR:
                    stack[sp] = var_matrix[r, arg0[i]]
                    sp += 1
                elif op == OP_NOT:
                    stack[sp - 1] = 1 - stack[sp - 1]
                else:
                    b = stack[sp - 1]
                    a = stack[sp - 2]
                    sp -= 1
                    if op == OP_AND:
                        stack[sp - 1] = a & b
                    elif op == OP_OR:
                        stack[sp - 1] = a | b
                    elif op == OP_XOR:
                        stack[sp - 1] = a ^ b
                    elif op == OP_IMP:
                        stack[sp - 1] = (1 - a) | b
                    else:  # OP_EQV
                        stack[sp - 1] = 1 - (a ^ b)
            out[r] = stack[0]
        return out

else:

    def _eval_program_numba(
        opcodes: np.ndarray, arg0: np.ndarray, arg1: np.ndarray, var_matrix: np.ndarray
    ) -> np.ndarray:
        raise RuntimeError("numba is not available")


def eval_expr_numba(
    expr_struct: Tuple[np.ndarray, np.ndarray, np.ndarray], var_matrix: np.ndarray
) -> np.ndarray:
    """Evaluate flattened expression with numba core."""
    opcodes, arg0, arg1 = expr_struct
    return _eval_program_numba(opcodes, arg0, arg1, var_matrix)


def warmup_numba(n_vars: int) -> None:
    """Trigger one-time JIT compilation on a tiny input matrix."""
    if not HAS_NUMBA:
        return
    dummy = np.zeros((1, n_vars), dtype=np.uint8)
    expr_struct = (
        np.asarray([OP_VAR], dtype=np.int16),
        np.asarray([0], dtype=np.int32),
        np.asarray([-1], dtype=np.int32),
    )
    _eval_program_numba(expr_struct[0], expr_struct[1], expr_struct[2], dummy)
