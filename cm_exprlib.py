
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Union, Sequence, Callable
import numpy as np
import itertools as it

# --------------------------
# Boolean Expression AST
# --------------------------

@dataclass(frozen=True)
class Var:
    i: int  # variable index

@dataclass(frozen=True)
class Not:
    a: 'Expr'

@dataclass(frozen=True)
class And:
    a: 'Expr'
    b: 'Expr'

@dataclass(frozen=True)
class Or:
    a: 'Expr'
    b: 'Expr'

@dataclass(frozen=True)
class Xor:
    a: 'Expr'
    b: 'Expr'

@dataclass(frozen=True)
class Imp:
    a: 'Expr'
    b: 'Expr'

@dataclass(frozen=True)
class Eqv:
    a: 'Expr'
    b: 'Expr'

Expr = Union[Var, Not, And, Or, Xor, Imp, Eqv]

# --------------------------
# Random expression builder
# --------------------------

OPS_BIN = (And, Or, Xor, Imp, Eqv)
OPS_UN = (Not,)

def random_expr(n_vars: int, rng: np.random.Generator, max_depth: int = 3, p_unary: float = 0.2) -> Expr:
    if max_depth <= 0 or (max_depth < 3 and rng.random() < 0.3):
        return Var(int(rng.integers(0, n_vars)))
    if rng.random() < p_unary:
        return Not(random_expr(n_vars, rng, max_depth-1, p_unary))
    op = rng.choice(OPS_BIN)
    return op(
        random_expr(n_vars, rng, max_depth-1, p_unary),
        random_expr(n_vars, rng, max_depth-1, p_unary),
    )

# --------------------------
# Vectorized evaluation
# --------------------------

def all_assignments_tt(n_vars: int) -> np.ndarray:
    """Return a 2^n x n uint8 matrix of assignments, MSB-first order."""
    L = 1 << n_vars
    A = np.zeros((L, n_vars), dtype=np.uint8)
    for v in range(n_vars):
        block = 1 << (n_vars - 1 - v)
        pattern = np.concatenate([np.zeros(block, dtype=np.uint8), np.ones(block, dtype=np.uint8)])
        reps = L // (2*block)
        A[:, v] = np.tile(pattern, reps)
    return A

def eval_expr_tt(expr: Expr, n_vars: int) -> np.ndarray:
    A = all_assignments_tt(n_vars)  # L x n
    def eval_rec(e: Expr) -> np.ndarray:
        if isinstance(e, Var):
            return A[:, e.i]
        if isinstance(e, Not):
            return 1 - eval_rec(e.a)
        if isinstance(e, And):
            return eval_rec(e.a) & eval_rec(e.b)
        if isinstance(e, Or):
            return eval_rec(e.a) | eval_rec(e.b)
        if isinstance(e, Xor):
            return eval_rec(e.a) ^ eval_rec(e.b)
        if isinstance(e, Imp):
            a = eval_rec(e.a); b = eval_rec(e.b)
            return ((1 - a) | b)
        if isinstance(e, Eqv):
            a = eval_rec(e.a); b = eval_rec(e.b)
            return 1 - (a ^ b)
        raise TypeError(e)
    return eval_rec(expr).astype(np.uint8)

# --------------------------
# Tseitin CNF encoding
# --------------------------

def _tseitin_cnf(expr: Expr, n_vars: int, start_id: int) -> Tuple[int, List[List[int]], int]:
    """Return (out_var, clauses) where out_var is the variable id for expr's output.
       Variable numbering: 1..n for x0..x{n-1}; fresh ids start at n+1.
       Clauses are lists of ints (positive = var, negative = negation).
    """
    next_id = [start_id]
    clauses: List[List[int]] = []

    def fresh() -> int:
        next_id[0] += 1
        return next_id[0]

    def enc(e: Expr) -> int:
        nonlocal clauses
        if isinstance(e, Var):
            return e.i + 1  # x0 -> 1
        if isinstance(e, Not):
            a = enc(e.a)
            z = fresh()
            # z <-> ~a  =>  (z -> ~a) & (~z -> a)
            # CNF: (¬z ∨ ¬a) & (z ∨ a)
            clauses.append([-z, -a])
            clauses.append([ z,  a])
            return z
        if isinstance(e, And):
            a = enc(e.a); b = enc(e.b)
            z = fresh()
            # z <-> (a & b)
            # (¬z ∨ a) (¬z ∨ b) (z ∨ ¬a ∨ ¬b)
            clauses += [[-z, a], [-z, b], [z, -a, -b]]
            return z
        if isinstance(e, Or):
            a = enc(e.a); b = enc(e.b)
            z = fresh()
            # z <-> (a | b)
            # (z ∨ ¬a) (z ∨ ¬b) (¬z ∨ a ∨ b)
            clauses += [[z, -a], [z, -b], [-z, a, b]]
            return z
        if isinstance(e, Xor):
            a = enc(e.a); b = enc(e.b)
            z = fresh()
            # z <-> a XOR b  =>  z <-> (a ∨ b) & ¬(a & b)
            # Encode directly:
            # (¬z ∨ ¬a ∨ ¬b) (¬z ∨ a ∨ b) (z ∨ ¬a ∨ b) (z ∨ a ∨ ¬b)
            clauses += [[-z, -a, -b], [-z, a, b], [z, -a, b], [z, a, -b]]
            return z
        if isinstance(e, Imp):
            a = enc(e.a); b = enc(e.b)
            z = fresh()
            # z <-> (~a | b)
            # (z ∨ a) (z ∨ ¬b) (¬z ∨ ¬a ∨ b)
            clauses += [[z, a], [z, -b], [-z, -a, b]]
            return z
        if isinstance(e, Eqv):
            a = enc(e.a); b = enc(e.b)
            z = fresh()
            # z <-> ¬(a XOR b)
            # (¬z ∨ a ∨ b) (¬z ∨ ¬a ∨ ¬b) (z ∨ a ∨ ¬b) (z ∨ ¬a ∨ b)
            clauses += [[z, a, b], [z, -a, -b], [-z, a, -b], [-z, -a, b]]
            return z
        raise TypeError(e)
    out = enc(expr)
    return out, clauses, next_id[0]

def tseitin_cnf(expr: Expr, n_vars: int) -> Tuple[int, List[List[int]]]:
    """Return a Tseitin encoding whose fresh IDs begin after the universe."""
    out, clauses, _ = _tseitin_cnf(expr, n_vars, n_vars)
    return out, clauses

def miter_equiv(expr1: Expr, expr2: Expr, n_vars: int):
    """Return CNF for (expr1 XOR expr2) == 1 (unsat means equivalent)."""
    out1, c1, next_id = _tseitin_cnf(expr1, n_vars, n_vars)
    out2, c2, next_id = _tseitin_cnf(expr2, n_vars, next_id)
    # miter: m = XOR(out1, out2) == 1
    # XOR encoding:
    m = next_id + 1
    clauses = c1 + c2
    clauses += [[-m, -out1, -out2], [-m, out1, out2], [m, -out1, out2], [m, out1, -out2]]
    # force m = 1
    clauses += [[m]]
    nvars = m
    return nvars, clauses
