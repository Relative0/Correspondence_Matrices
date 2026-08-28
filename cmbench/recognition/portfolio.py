"""Task-matched exact baselines: complete packed truth vectors, MSB-first rows."""
from __future__ import annotations

from typing import Callable

import numpy as np

from bitset_backend import (
    PreparedFlatEvaluation, build_bitset_env, compile_expr_cse, compile_flat,
    eval_expr_bitset,
)
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir

from .features import Features, IneligibleExpression, extract_features, postorder

BACKENDS = ("direct", "cse", "cm")


def admit(expr: Expr, n_vars: int, queries: int) -> Features:
    features = extract_features(expr, n_vars, queries)
    # The direct baseline and CM compiler still contain recursive code. Do not
    # feed them an unbounded DAG/tree merely because feature extraction is iterative.
    if features.depth > 96 or features.unfolded_nodes_capped > 50_000:
        raise IneligibleExpression("depth or unfolded-work limit exceeded")
    if features.identity_nodes * (1 << n_vars) > 8_388_608:
        raise IneligibleExpression("reference-interpreter cell limit exceeded")
    return features


def prepare(backend: str, expr: Expr, n_vars: int) -> Callable[[], int]:
    """Fresh program per invocation; no expression/result cache and no I/O.

    The common variable-mask cache is deliberately warm in the experiment.
    Program compilation, mask lookup/binding, and execution are timed. Both CM
    and CSE use the same public bigint flat executor and identical output width.
    Callers admit inputs before entering their timing window.
    """
    if backend not in BACKENDS:
        raise ValueError("unknown backend")
    names = tuple(f"x{i}" for i in range(n_vars))
    env = build_bitset_env(names)
    if backend == "direct":
        return lambda: eval_expr_bitset(expr, env)
    if backend == "cse":
        program = compile_expr_cse(expr, flatten=True)
    else:
        node = compile_expr_to_cm_ir(
            expr, reuse_cache=False, persistent_cache=False, share_aware_flatten=True,
        )
        program = compile_flat(node)
    full_mask = (1 << (1 << n_vars)) - 1
    template = [0] * program.n_slots
    for slot, kind, payload in program.loads:
        template[slot] = (full_mask if payload else 0) if kind == "const" else env[payload]
    return PreparedFlatEvaluation(program, template, full_mask, False).evaluate


def reference_bits(expr: Expr, n_vars: int) -> int:
    """Independent NumPy operator interpreter, not a flat/CM compiler or kernel.

    This audit is outside algorithm timing for EVERY arm. The learner only
    chooses exact algorithms; it does not propose an unchecked Boolean result.
    """
    admit(expr, n_vars, 1)
    rows = np.arange(1 << n_vars, dtype=np.uint32)
    values: dict[int, np.ndarray] = {}
    for node in postorder(expr):
        kind = type(node)
        if kind is Var:
            value = ((rows >> (n_vars - 1 - node.i)) & 1).astype(np.uint8)
        elif kind is Not:
            value = np.logical_not(values[id(node.a)])
        else:
            a, b = values[id(node.a)], values[id(node.b)]
            if kind is And:
                value = np.logical_and(a, b)
            elif kind is Or:
                value = np.logical_or(a, b)
            elif kind is Xor:
                value = np.logical_xor(a, b)
            elif kind is Imp:
                value = np.logical_or(np.logical_not(a), b)
            elif kind is Eqv:
                value = np.equal(a, b)
            else:
                raise IneligibleExpression("unsupported reference operation")
        values[id(node)] = value
    return int.from_bytes(np.packbits(values[id(expr)], bitorder="little").tobytes(), "little")
