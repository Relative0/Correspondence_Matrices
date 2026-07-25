"""Independent Audit V4 checks for latent fixes 1, 2, 3, and 5."""
from __future__ import annotations

import csv
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import cm_bench
from bitset_backend import (
    FlatProgram, _FLAT_OP_AND, _FLAT_OP_EQV, _FLAT_OP_IMP, _FLAT_OP_NOT,
    _FLAT_OP_OR, _FLAT_OP_XOR, _eval_words, build_bitset_env,
    eval_cm_node_flat, eval_expr_bitset, eval_expr_flat_bitset,
    eval_expr_words_bitset,
)
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor, eval_expr_tt, random_expr
from cm_ir import compile_expr_to_cm_ir
from cm_remote_executor import LocalMockCMRemoteExecutor, build_remote_request
from cmbench.config import BenchmarkConfig
from cmbench.expr.partial_contexts import _eval_expr_bitset_fixed

OUT = Path(__file__).with_name("CM_v4audit_latentfix_verification.csv")
OPS = [
    (_FLAT_OP_AND, And, lambda a, b: a & b),
    (_FLAT_OP_OR, Or, lambda a, b: a | b),
    (_FLAT_OP_XOR, Xor, lambda a, b: a ^ b),
    (_FLAT_OP_NOT, Not, lambda a, _b: 1 - a),
    (_FLAT_OP_IMP, Imp, lambda a, b: (1 - a) | b),
    (_FLAT_OP_EQV, Eqv, lambda a, b: 1 - (a ^ b)),
]


def main():
    rows = []
    rng = np.random.default_rng(20260724)
    engine_failures = 0
    for n in range(8, 19):
        names = tuple(f"x{i}" for i in range(n))
        env = build_bitset_env(names)
        for case in range(4):
            expr = random_expr(n, rng, max_depth=6, p_unary=0.25)
            ref = eval_expr_bitset(expr, env)
            ok = ref == eval_expr_flat_bitset(expr, names) == eval_expr_words_bitset(expr, names)
            fixed_names = set(rng.choice(names, size=max(1, n // 3), replace=False).tolist())
            fixed = {name: int(rng.integers(0, 2)) for name in fixed_names}
            scope = tuple(name for name in names if name not in fixed)
            restricted = _eval_expr_bitset_fixed(expr, build_bitset_env(scope), fixed)
            ok = ok and restricted == eval_expr_flat_bitset(expr, scope, fixed=fixed)
            ok = ok and restricted == eval_expr_words_bitset(expr, scope, fixed=fixed)
            engine_failures += 0 if ok else 1
    rows.append({"check": "A1_engine_parity", "ok": engine_failures == 0,
                 "detail": f"44 formulas, full+restricted; failures={engine_failures}"})

    remote_failures = 0
    last = None
    for words in (False, True):
        expr = random_expr(12, rng, max_depth=5, p_unary=0.2)
        req = build_remote_request(expr, 12, hybrid_threshold=16, words_eval=words)
        clone = type(req).from_dict(req.to_dict())
        result = LocalMockCMRemoteExecutor().execute(clone)
        last = result
        expected = eval_expr_bitset(expr, build_bitset_env([f"x{i}" for i in range(12)]))
        payload = result.response.result or {}
        actual = int(payload["bits_hex"], 16)
        remote_failures += not (
            clone.words_eval is words
            and result.response.diagnostics.get("remote_words_eval") is words
            and actual == expected
        )
    stale = replace(last, response=replace(last.response, diagnostics={
        k: v for k, v in last.response.diagnostics.items() if k != "remote_words_eval"
    }))
    refused = False
    try:
        cm_bench._check_remote_words_provenance(stale, True)
    except RuntimeError:
        refused = True
    compatible = cm_bench._check_remote_words_provenance(stale, False) is stale
    rows.append({"check": "A2_remote_words", "ok": remote_failures == 0 and refused and compatible,
                 "detail": f"roundtrip_failures={remote_failures}; stale_refused={refused}; nonwords_ok={compatible}"})

    known_failures = 0
    for opcode, cls, oracle in OPS:
        expr = cls(Var(0)) if opcode == _FLAT_OP_NOT else cls(Var(0), Var(1))
        names = ("x0", "x1")
        got = eval_expr_flat_bitset(expr, names)
        expected = 0
        for idx in range(4):
            a, b = (idx >> 1) & 1, idx & 1
            expected |= oracle(a, b) << idx
        known_failures += got != expected
    bad = FlatProgram(3, 2, ((0, "var", "x0"), (1, "var", "x1")), ((2, 99, (0, 1)),))
    raised = []
    bad_expr = Eqv(Var(0), Var(1)); object.__setattr__(bad_expr, "_bitset_flat_program", bad)
    try: eval_expr_flat_bitset(bad_expr, ("x0", "x1"))
    except ValueError: raised.append("expr_flat")
    bad_node = compile_expr_to_cm_ir(Eqv(Var(0), Var(1))); object.__setattr__(bad_node, "_flat_program", bad)
    try: eval_cm_node_flat(bad_node, ("x0", "x1"))
    except ValueError: raised.append("cm_flat")
    try: _eval_words(bad, tuple(f"x{i}" for i in range(6)), {})
    except ValueError: raised.append("words")
    rows.append({"check": "A3_opcodes", "ok": known_failures == 0 and len(raised) == 3,
                 "detail": f"known_failures={known_failures}; unknown_raised={raised}"})

    # Paired guard-loop timings.  Raw observations are retained as individual rows.
    expr = random_expr(18, rng, max_depth=8, p_unary=0.25)
    names = tuple(f"x{i}" for i in range(18))
    variants = {"flat": lambda: eval_expr_flat_bitset(expr, names),
                "words": lambda: eval_expr_words_bitset(expr, names)}
    for rnd in range(7):
        for name in (variants if rnd % 2 else reversed(variants)):
            t0 = time.perf_counter()
            for _ in range(60): variants[name]()
            rows.append({"check": "A3_hot_loop_raw", "ok": True,
                         "detail": f"round={rnd}; engine={name}; us={(time.perf_counter()-t0)*1e6/60:.6f}"})

    original = cm_bench.build_bitset_env
    env_counts = {}
    expr8 = random_expr(8, rng, max_depth=4, p_unary=0.2)
    tt = eval_expr_tt(expr8, 8).astype(np.uint8)
    try:
        for mode, flat, words in (("recursive", False, False), ("flat", True, False), ("words", False, True)):
            count = [0]
            def spy(names):
                count[0] += 1
                return original(names)
            cm_bench.build_bitset_env = spy
            cfg = BenchmarkConfig(
                sizes=(8,), trials=1, seed=1, max_depth=4,
                cm_flat_eval=flat, cm_words_eval=words,
                no_numba=True, no_sympy=True, no_espresso=True, no_bdd_sop=True,
                no_dd=True, no_robdd=True, no_robdd_dd=True,
            )
            row = cm_bench.time_backends_on_expr(
                8, expr8, use_dd=False, use_espresso=False, verbose=False,
                tt_ref=tt, config=cfg,
            )
            env_counts[mode] = count[0]
            if not row["bitset_ok"]: raise AssertionError(mode)
    finally:
        cm_bench.build_bitset_env = original
    rows.append({"check": "A4_unused_env", "ok": env_counts == {"recursive": 1, "flat": 0, "words": 0},
                 "detail": str(env_counts)})

    with (Path(__file__).parent / "CM_V3AUDIT_F5_family_structure_raw.csv").open(
        newline="", encoding="utf-8"
    ) as fh:
        constants = [r for r in csv.DictReader(fh)
                     if r["family"] == "fable_claimed_all_live" and int(r["semantic_live_k"]) == 0]
    n28 = [r for r in constants if int(r["n"]) == 28 and int(r["trial"]) == 1]
    rows.append({"check": "A5_n28_constant", "ok": len(constants) == 3 and len(n28) == 1,
                 "detail": f"constants={[(r['n'],r['trial']) for r in constants]}"})

    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    failed = [r for r in rows if not r["ok"]]
    print(f"checks={len(rows)} failures={failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
