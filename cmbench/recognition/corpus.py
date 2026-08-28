"""Generated fixtures with formula-group splits and a held-out motif family."""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

from .features import structural_digest

FAMILIES = ("mixed", "redundant", "shared", "parity", "mux")


@dataclass(frozen=True)
class Case:
    case_id: str
    family: str
    split: str
    n_vars: int
    queries: int
    expr: Expr
    digest: str
    group_digest: str


def _tree(rng: random.Random, n_vars: int, depth: int) -> Expr:
    if depth == 0 or (depth < 3 and rng.random() < 0.25):
        return Var(rng.randrange(n_vars))
    if rng.random() < 0.15:
        return Not(_tree(rng, n_vars, depth - 1))
    return rng.choice((And, Or, Xor, Imp, Eqv))(
        _tree(rng, n_vars, depth - 1), _tree(rng, n_vars, depth - 1),
    )


def generate_expr(family: str, rng: random.Random, n_vars: int) -> Expr:
    if family not in FAMILIES:
        raise ValueError("unknown family")
    expr = _tree(rng, n_vars, rng.randint(2, 4))
    if family == "mixed":
        return expr
    for _ in range(rng.randint(2, 6)):
        other = _tree(rng, n_vars, rng.randint(1, 3))
        if family == "redundant":
            # Identity/complement opportunities, not learned rewrite rules.
            expr = rng.choice((And(expr, expr), Or(expr, And(expr, other)),
                               Xor(Xor(expr, other), other), Not(Not(expr))))
        elif family == "shared":
            expr = rng.choice((And, Or, Xor))(Or(expr, other), And(expr, Not(other)))
        elif family == "parity":
            expr = rng.choice((Xor, Eqv))(expr, other)
        else:
            selector = Var(rng.randrange(n_vars))
            expr = Or(And(selector, expr), And(Not(selector), other))
    return expr


def make_corpus(
    *, seed: int = 20260828, train: int = 12, validation: int = 4, test: int = 4,
    sizes: tuple[int, ...] = (6, 8, 10), query_counts: tuple[int, ...] = (1, 8, 64),
    held_out_family: str = "mux",
) -> list[Case]:
    if held_out_family not in FAMILIES:
        raise ValueError("unknown held-out family")
    for count in (train, validation, test):
        if type(count) is not int or not 1 <= count <= 32:
            raise ValueError("each per-family split count must be in 1..32")
    if not sizes or any(type(n) is not int or not 2 <= n <= 16 for n in sizes):
        raise ValueError("sizes must contain integers in 2..16")
    if not query_counts or any(type(q) is not int or not 1 <= q <= 256 for q in query_counts):
        raise ValueError("query counts must contain integers in 1..256")
    seen: set[str] = set()
    cases = []
    # All exact/alpha-structural siblings belong to only one split, including
    # siblings with different nominal universes or query counts.
    for split, count in (("train", train), ("validation", validation),
                         ("test", test), ("family_test", test)):
        families = (held_out_family,) if split == "family_test" else tuple(
            f for f in FAMILIES if f != held_out_family
        )
        for family in families:
            salt = hashlib.sha256(f"{seed}:{split}:{family}".encode()).digest()
            rng = random.Random(int.from_bytes(salt, "big"))
            accepted = attempts = 0
            while accepted < count:
                attempts += 1
                if attempts > count * 100:
                    raise ValueError("could not generate enough distinct formula groups")
                n_vars, queries = rng.choice(sizes), rng.choice(query_counts)
                expr = generate_expr(family, rng, n_vars)
                group = structural_digest(expr, alpha_rename=True)
                if group in seen:
                    continue
                seen.add(group)
                cases.append(Case(
                    f"{split}-{family}-{accepted:03d}", family, split, n_vars,
                    queries, expr, structural_digest(expr), group,
                ))
                accepted += 1
    return cases
