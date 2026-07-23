"""Latent-fix 1 bit-exactness proof: partial/family control engines.

Verifies, over a fuzz set spanning n=8..18, that the engines newly wired into
the partial/family Bitset controls are packed-bit identical to the recursive
bigint engines they replace under --cm-flat-eval / --cm-words-eval:

  full-scope control:  eval_expr_bitset  == eval_expr_flat_bitset == eval_expr_words_bitset
  restricted control:  _eval_expr_bitset_fixed == eval_expr_flat_bitset(fixed=)
                                              == eval_expr_words_bitset(fixed=)

The scope semantics are unchanged by the fix (full recompute stays full-scope,
restricted stays restricted-scope); only the engine changes, so packed equality
of these expressions is exactly the bit-exactness claim of the fix.

Writes CM_latentfix1_engine_parity.csv next to this script; exits nonzero on
any mismatch.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bitset_backend import (
    build_bitset_env,
    eval_expr_bitset,
    eval_expr_flat_bitset,
    eval_expr_words_bitset,
)
from cm_exprlib import random_expr
from cmbench.expr.partial_contexts import _eval_expr_bitset_fixed, _partial_output_vars

OUT = Path(__file__).resolve().parent / "CM_latentfix1_engine_parity.csv"

EXPRS_PER_N = 6
CONTEXTS_PER_EXPR = 4


def main() -> int:
    rng = np.random.default_rng(20260723)
    rows = []
    failures = 0
    for n in range(8, 19):
        names = tuple(f"x{i}" for i in range(n))
        env_full = build_bitset_env(names)
        for expr_index in range(EXPRS_PER_N):
            expr = random_expr(n, rng, max_depth=6, p_unary=0.25)
            ref_full = int(eval_expr_bitset(expr, env_full))
            flat_full = int(eval_expr_flat_bitset(expr, names))
            words_full = int(eval_expr_words_bitset(expr, names))
            full_flat_eq = ref_full == flat_full
            full_words_eq = ref_full == words_full
            restricted_flat_eq = True
            restricted_words_eq = True
            for _ in range(CONTEXTS_PER_EXPR):
                k = int(rng.integers(1, n))
                fixed_idx = rng.choice(n, size=k, replace=False)
                context = {f"x{int(i)}": int(rng.integers(0, 2)) for i in fixed_idx}
                out_vars = _partial_output_vars(n, context, "remaining-vars")
                ref_bits = int(_eval_expr_bitset_fixed(expr, build_bitset_env(out_vars), context))
                flat_bits = int(eval_expr_flat_bitset(expr, tuple(out_vars), fixed=context))
                words_bits = int(eval_expr_words_bitset(expr, tuple(out_vars), fixed=context))
                restricted_flat_eq = restricted_flat_eq and (ref_bits == flat_bits)
                restricted_words_eq = restricted_words_eq and (ref_bits == words_bits)
            ok = full_flat_eq and full_words_eq and restricted_flat_eq and restricted_words_eq
            failures += 0 if ok else 1
            rows.append(
                {
                    "n_vars": n,
                    "expr_index": expr_index,
                    "contexts": CONTEXTS_PER_EXPR,
                    "full_flat_eq": full_flat_eq,
                    "full_words_eq": full_words_eq,
                    "restricted_flat_eq": restricted_flat_eq,
                    "restricted_words_eq": restricted_words_eq,
                    "all_eq": ok,
                }
            )
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    total = len(rows)
    print(f"cases={total} failures={failures} -> {OUT.name}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
