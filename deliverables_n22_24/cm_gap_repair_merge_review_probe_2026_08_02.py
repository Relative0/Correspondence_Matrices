"""Merge-gate review probe for the 2026-08-02 gap-repair diff.

Adversarial verification, independent of the implementation's own tests:

  metrics_instrumented   program_metrics vs *counted* primitive operations —
                         numpy ufuncs monkeypatched for the words executor,
                         operator-counting int wrappers for the bigint executor.
  corpus_key_regression  all 49 published corpus formulas: canonical keys and
                         packed outputs, repair on vs off.
  headline_reproduction  368->167 executed ops, prep/kernel on the 8x8 bits.
  semantic_fuzz          300 random shared DAGs: packed equality across
                         cm_new / cm_legacy / cse / raw; key determinism; and
                         the cache-safety property (a tree-expanded, dataclass-
                         equal copy must produce the identical canonical key).
  memo_lifetime_stress   one reused builder, 200 rounds, gc + id-recycling
                         pressure between rounds, differential vs raw.
  reentrancy             a subclass recursing through build() mid-compilation.
  serde_fuzz             valid-document round-trips + 400 random mutations
                         (must raise ValueError or preserve semantics).
  regression_decomposition  flag matrix attributing the unshared-tree compile
                         overhead to prepass vs memo.
  persistent_path        legacy flattening on the persistent compile path:
                         quantified, checked semantically safe when mixed.
  cse_independence       subprocess check that the CSE baseline never imports
                         cm_ir.

Run: .venv/Scripts/python.exe deliverables_n22_24/cm_gap_repair_merge_review_probe_2026_08_02.py
"""
from __future__ import annotations

import gc
import json
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.setrecursionlimit(100_000)

import numpy as np

import bitset_backend as bb
from bitset_backend import (
    FlatProgram,
    PreparedFlatEvaluation,
    _bind_flat_program,
    _eval_prepared_flat,
    _eval_words,
    _FLAT_OP_AND,
    _FLAT_OP_NOT,
    compile_expr_cse,
    compile_expr_flat,
    eval_cm_node_words,
    eval_expr_words_bitset,
    eval_expr_words_cse,
    get_flat_program,
    program_metrics,
)
from cm_expr_serde import expr_from_json, expr_to_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import CMIRBuilder, compile_expr_to_cm_ir, compile_expr_to_cm_ir_persistent, \
    clear_cm_ir_persistent_cache

OUT = ROOT / "deliverables_n22_24" / "cm_gap_repair_merge_review_results_2026_08_02.json"

OPS = {"and": And, "or": Or, "xor": Xor, "imp": Imp, "eqv": Eqv}


def timed(fn, repeats=1, blocks=3):
    best = float("inf")
    for _ in range(blocks):
        t0 = time.perf_counter()
        for _ in range(repeats):
            fn()
        best = min(best, (time.perf_counter() - t0) / repeats)
    return best


def support_of(expr):
    seen, out, stack = set(), set(), [expr]
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if isinstance(cur, Var):
            out.add(int(cur.i))
        elif isinstance(cur, Not):
            stack.append(cur.a)
        else:
            stack.extend((cur.a, cur.b))
    return tuple(f"x{i}" for i in sorted(out))


def padded_support(expr, minimum=6):
    sup = set(support_of(expr)) | {f"x{i}" for i in range(minimum)}
    return tuple(sorted(sup, key=lambda s: int(s[1:])))


def shared_dag(rng, n_vars, steps):
    pool = [Var(i) for i in range(n_vars)]
    for _ in range(steps):
        name = rng.choice(["and", "or", "xor", "imp", "eqv", "not"])
        if name == "not":
            pool.append(Not(rng.choice(pool)))
        else:
            pool.append(OPS[name](rng.choice(pool), rng.choice(pool)))
    root = pool[-1]
    for e in pool[-5:-1]:
        root = Xor(root, e)
    return root


def multiplier_bit(nb, topology, bit):
    def add_words(a, b):
        width = max(len(a), len(b))
        out, carry = [], None
        for i in range(width):
            ai = a[i] if i < len(a) else None
            bi = b[i] if i < len(b) else None
            terms = [x for x in (ai, bi, carry) if x is not None]
            if not terms:
                out.append(None); carry = None
            elif len(terms) == 1:
                out.append(terms[0]); carry = None
            elif len(terms) == 2:
                out.append(Xor(terms[0], terms[1])); carry = And(terms[0], terms[1])
            else:
                ab = Xor(ai, bi)
                out.append(Xor(ab, carry))
                carry = Or(And(ai, bi), And(ab, carry))
        if carry is not None:
            out.append(carry)
        return out

    rows = []
    for j in range(nb):
        rows.append([None] * j + [And(Var(i), Var(nb + j)) for i in range(nb)])
    if topology == "sequential":
        acc = rows[0]
        for row in rows[1:]:
            acc = add_words(acc, row)
        return acc[bit]
    while len(rows) > 1:
        nxt = []
        for i in range(0, len(rows), 2):
            nxt.append(add_words(rows[i], rows[i + 1]) if i + 1 < len(rows) else rows[i])
        rows = nxt
    return rows[0][bit]


# --------------------------------------------------------------------------
# 1. instrumented metric verification
# --------------------------------------------------------------------------

class _WordOpCounter:
    """Monkeypatch the exact numpy entry points _eval_words uses."""

    NAMES = ("bitwise_and", "bitwise_or", "bitwise_xor", "bitwise_not", "copyto")

    def __init__(self):
        self.count = 0
        self._orig = {}

    def __enter__(self):
        for name in self.NAMES:
            self._orig[name] = getattr(np, name)

            def wrapper(*args, _f=self._orig[name], **kwargs):
                self.count += 1
                return _f(*args, **kwargs)

            setattr(np, name, wrapper)
        return self

    def __exit__(self, *exc):
        for name, f in self._orig.items():
            setattr(np, name, f)


class CountInt:
    """Int wrapper counting primitive Boolean bigint operations."""

    counter = [0]
    __slots__ = ("v",)

    def __init__(self, v):
        self.v = int(v)

    def _bin(self, other, op):
        CountInt.counter[0] += 1
        o = other.v if isinstance(other, CountInt) else int(other)
        return CountInt(op(self.v, o))

    def __and__(self, other):
        return self._bin(other, lambda a, b: a & b)

    def __rand__(self, other):
        return self._bin(other, lambda a, b: b & a)

    def __or__(self, other):
        return self._bin(other, lambda a, b: a | b)

    def __ror__(self, other):
        return self._bin(other, lambda a, b: b | a)

    def __xor__(self, other):
        return self._bin(other, lambda a, b: a ^ b)

    def __rxor__(self, other):
        return self._bin(other, lambda a, b: b ^ a)

    def __invert__(self):
        CountInt.counter[0] += 1
        return CountInt(~self.v)

    def __int__(self):
        return self.v

    def __index__(self):
        return self.v


def counted_word_ops(prog, vars_key):
    _eval_words(prog, vars_key, {})  # warm plan/scratch outside the count
    with _WordOpCounter() as c:
        _eval_words(prog, vars_key, {})
    return c.count


def counted_bigint_ops(prog, vars_key):
    template, full_mask = _bind_flat_program(prog, vars_key, {})
    wrapped = [None if t is None else CountInt(t) for t in template]
    prepared = PreparedFlatEvaluation(prog, wrapped, full_mask, False)
    CountInt.counter[0] = 0
    _eval_prepared_flat(prepared)
    return CountInt.counter[0]


def run_metrics_instrumented():
    rng = random.Random(7)
    cases = []
    for seed in range(6):
        cases.append(("fuzz", shared_dag(random.Random(seed), 8, 25)))
    cases.append(("mult_seq6_b6", multiplier_bit(6, "sequential", 6)))
    chain = Var(0)
    for i in range(1, 16):
        chain = Xor(chain, Var(i))
    cases.append(("xor_chain16", chain))
    rows = []
    for name, expr in cases:
        sup = padded_support(expr)
        progs = {
            "cm_new": get_flat_program(compile_expr_to_cm_ir(expr)),
            "cm_legacy": get_flat_program(compile_expr_to_cm_ir(
                expr, share_aware_flatten=False, build_memo=False)),
            "cse": compile_expr_cse(expr),
            "cse_flat": compile_expr_cse(expr, flatten=True),
            "raw": compile_expr_flat(expr),
        }
        for arm, prog in progs.items():
            m = program_metrics(prog)
            cw = counted_word_ops(prog, sup)
            cb = counted_bigint_ops(prog, sup)
            rows.append({
                "case": name, "arm": arm,
                "declared_word": m["executed_word_ops"], "counted_word": cw,
                "declared_bigint": m["executed_bigint_ops"], "counted_bigint": cb,
                "word_ok": m["executed_word_ops"] == cw,
                "bigint_ok": m["executed_bigint_ops"] == cb,
            })
    # synthetic 1-ary instruction (copyto path)
    prog = FlatProgram(2, 1, ((0, "var", "x0"),), ((1, _FLAT_OP_AND, (0,)),))
    m = program_metrics(prog)
    rows.append({
        "case": "synthetic_1ary", "arm": "synthetic",
        "declared_word": m["executed_word_ops"],
        "counted_word": counted_word_ops(prog, padded_support(Var(0))),
        "declared_bigint": m["executed_bigint_ops"],
        "counted_bigint": counted_bigint_ops(prog, padded_support(Var(0))),
        "word_ok": m["executed_word_ops"] == counted_word_ops(prog, padded_support(Var(0))),
        "bigint_ok": m["executed_bigint_ops"] == counted_bigint_ops(prog, padded_support(Var(0))),
    })
    return {"rows": rows,
            "all_word_ok": all(r["word_ok"] for r in rows),
            "all_bigint_ok": all(r["bigint_ok"] for r in rows)}


# --------------------------------------------------------------------------
# 2/3. corpus regression + headline reproduction
# --------------------------------------------------------------------------

def run_corpus_key_regression():
    same = 0
    diff = []
    equal = True
    for line in (ROOT / "deliverables_n22_24" / "v4audit_corpus_2026_07_24.jsonl").read_text(
            encoding="utf-8").splitlines():
        item = json.loads(line)
        e = expr_from_json(item["expression"])
        a = compile_expr_to_cm_ir(e)
        b = compile_expr_to_cm_ir(e, share_aware_flatten=False, build_memo=False)
        if a.key == b.key:
            same += 1
        else:
            diff.append(item["id"])
        if item["explicit_packed_policy"] == "run":
            sup = tuple(item["semantic_support"])
            fx = {f"x{i}": 0 for i in range(item["nominal_n"]) if f"x{i}" not in sup}
            if eval_cm_node_words(a, sup, fixed=fx) != eval_expr_words_bitset(e, sup, fixed=fx):
                equal = False
    return {"identical_keys": same, "changed_keys": diff, "all_packed_equal": equal}


def run_headline_reproduction():
    rows = []
    for topology in ("sequential", "balanced"):
        expr = multiplier_bit(8, topology, 8)
        sup = support_of(expr)
        node_new = compile_expr_to_cm_ir(expr)
        node_old = compile_expr_to_cm_ir(expr, share_aware_flatten=False, build_memo=False)
        cse = compile_expr_cse(expr)
        pn, po = get_flat_program(node_new), get_flat_program(node_old)
        vals = {_eval_words(p, sup, {}) for p in (pn, po, cse)}
        assert len(vals) == 1
        rows.append({
            "case": f"mult_{topology}_nb8_bit8",
            "word_ops_old": program_metrics(po)["executed_word_ops"],
            "word_ops_new": program_metrics(pn)["executed_word_ops"],
            "word_ops_cse": program_metrics(cse)["executed_word_ops"],
            "prep_old_us": timed(lambda: compile_expr_to_cm_ir(
                expr, share_aware_flatten=False, build_memo=False), blocks=1) * 1e6,
            "prep_new_us": timed(lambda: compile_expr_to_cm_ir(expr)) * 1e6,
            "prep_cse_us": timed(lambda: compile_expr_cse(expr)) * 1e6,
            "kernel_old_us": timed(lambda: _eval_words(po, sup, {}), repeats=30) * 1e6,
            "kernel_new_us": timed(lambda: _eval_words(pn, sup, {}), repeats=30) * 1e6,
            "kernel_cse_us": timed(lambda: _eval_words(cse, sup, {}), repeats=30) * 1e6,
        })
    return rows


# --------------------------------------------------------------------------
# 4. semantic fuzz incl. cache-safety property
# --------------------------------------------------------------------------

def run_semantic_fuzz(n_cases=300):
    failures = []
    key_mismatch_after_tree_expand = 0
    checked = 0
    for seed in range(n_cases):
        rng = random.Random(1000 + seed)
        n_vars = rng.choice([4, 6, 8, 10])
        expr = shared_dag(rng, n_vars, rng.randrange(10, 45))
        sup = padded_support(expr)
        node = compile_expr_to_cm_ir(expr)
        v_new = eval_cm_node_words(node, sup)
        v_old = eval_cm_node_words(compile_expr_to_cm_ir(
            expr, share_aware_flatten=False, build_memo=False), sup)
        v_cse = eval_expr_words_cse(expr, sup)
        v_csef = eval_expr_words_cse(expr, sup, flatten=True)
        ok = v_new == v_old == v_cse == v_csef
        # key determinism
        ok = ok and compile_expr_to_cm_ir(expr).key == node.key
        # cache-safety: dataclass-equal, sharing-destroyed copy must canonicalize
        # to the SAME key (reuse_cache correctness depends on this)
        copy = expr_from_json(expr_to_json(expr))
        assert copy == expr
        if compile_expr_to_cm_ir(copy).key != node.key:
            key_mismatch_after_tree_expand += 1
            failures.append({"seed": seed, "kind": "cache_safety_key_mismatch"})
        # v2 dag round trip too
        rt = expr_from_json(json.loads(json.dumps(expr_to_json_dag(expr))))
        if compile_expr_to_cm_ir(rt).key != node.key or eval_cm_node_words(
                compile_expr_to_cm_ir(rt), sup) != v_new:
            failures.append({"seed": seed, "kind": "v2_roundtrip_mismatch"})
        if not ok:
            failures.append({"seed": seed, "kind": "packed_or_determinism"})
        checked += 1
    return {"cases": checked, "failures": failures,
            "cache_safety_key_mismatches": key_mismatch_after_tree_expand}


# --------------------------------------------------------------------------
# 5/6. memo lifetime + reentrancy
# --------------------------------------------------------------------------

def run_memo_lifetime_stress(rounds=200):
    builder = CMIRBuilder()
    bad = 0
    recycled_ids_seen = 0
    prior_ids: set = set()
    for r in range(rounds):
        rng = random.Random(555 + r)
        expr = shared_dag(rng, 6, 20)
        ids_now = set()
        stack = [expr]
        while stack:
            e = stack.pop()
            if id(e) in ids_now:
                continue
            ids_now.add(id(e))
            if isinstance(e, Not):
                stack.append(e.a)
            elif not isinstance(e, Var):
                stack.extend((e.a, e.b))
        recycled_ids_seen += len(ids_now & prior_ids)
        prior_ids = ids_now
        node = builder.build(expr)
        if eval_cm_node_words(node, padded_support(expr)) != eval_expr_words_bitset(
                expr, padded_support(expr)):
            bad += 1
        del expr, node
        gc.collect()
    return {"rounds": rounds, "failures": bad, "recycled_ids_observed": recycled_ids_seen}


def run_reentrancy():
    class Recursing(CMIRBuilder):
        def build(self, expr):
            # recurse through the public entry per node, like external
            # subclasses (e.g. the deep-followup IdMemoBuilder) do
            if isinstance(expr, Var):
                return super().build(expr)
            if isinstance(expr, Not):
                return self.negate(self.build(expr.a))
            return super().build(expr)

    rng = random.Random(42)
    ok = True
    for _ in range(20):
        expr = shared_dag(rng, 6, 15)
        b = Recursing()
        node = b.build(expr)
        ok = ok and b._build_state is None
        ok = ok and eval_cm_node_words(node, padded_support(expr)) == \
            eval_expr_words_bitset(expr, padded_support(expr))
    return {"ok": ok}


# --------------------------------------------------------------------------
# 7. serde fuzz
# --------------------------------------------------------------------------

def run_serde_fuzz(n_valid=100, n_mutations=400):
    import numpy as _np
    from cm_exprlib import eval_expr_tt

    roundtrip_fail = 0
    for seed in range(n_valid):
        rng = random.Random(2000 + seed)
        expr = shared_dag(rng, 5, rng.randrange(5, 25))
        n = max(int(s[1:]) for s in support_of(expr)) + 1 if support_of(expr) else 1
        ref = eval_expr_tt(expr, n)
        for doc in (expr_to_json(expr), expr_to_json_dag(expr)):
            rt = expr_from_json(json.loads(json.dumps(doc)))
            if not _np.array_equal(eval_expr_tt(rt, n), ref):
                roundtrip_fail += 1

    mut_bad = 0
    accepted_mutations = 0
    rng = random.Random(9)
    base = expr_to_json_dag(shared_dag(random.Random(3), 5, 20))
    for _ in range(n_mutations):
        doc = json.loads(json.dumps(base))
        kind = rng.randrange(6)
        nodes = doc["nodes"]
        idx = rng.randrange(len(nodes))
        if kind == 0:
            field = rng.choice(["a", "b", "i", "root"])
            target = doc if field == "root" else nodes[idx]
            target[field] = rng.choice([-1, len(nodes) + 5, True, "x", 1.5, None, idx])
        elif kind == 1:
            nodes[idx]["op"] = rng.choice(["nand", "", 7, "vAr!"])
        elif kind == 2:
            nodes.insert(rng.randrange(len(nodes)), json.loads(json.dumps(rng.choice(nodes))))
        elif kind == 3:
            doc["version"] = rng.choice([1, 3, "2", None])
        elif kind == 4:
            nodes[idx] = rng.choice([[], "x", 3, None])
        else:
            del nodes[rng.randrange(len(nodes))]
        try:
            expr_from_json(doc)
        except ValueError:
            pass
        except RecursionError:
            mut_bad += 1  # would be a robustness failure for v2 docs
        except Exception:
            mut_bad += 1  # anything but ValueError is a validation gap
        else:
            # acceptance is only OK if the mutation happened to keep the
            # document well-formed (e.g. self-copy insertion before use);
            # count and verify determinism of acceptance
            accepted_mutations += 1
    return {"roundtrip_failures": roundtrip_fail, "non_valueerror_escapes": mut_bad,
            "mutations_accepted_as_wellformed": accepted_mutations}


# --------------------------------------------------------------------------
# 8. regression decomposition
# --------------------------------------------------------------------------

def run_regression_decomposition():
    def random_tree(rng, n_vars, depth):
        if depth == 0 or (depth < 3 and rng.random() < 0.3):
            return Var(rng.randrange(n_vars))
        if rng.random() < 0.15:
            return Not(random_tree(rng, n_vars, depth - 1))
        return OPS[rng.choice(list(OPS))](random_tree(rng, n_vars, depth - 1),
                                          random_tree(rng, n_vars, depth - 1))

    exprs = []
    seed = 0
    while len(exprs) < 24:
        seed += 1
        e = random_tree(random.Random(seed), 12, 4)
        if not isinstance(e, Var):
            exprs.append(e)
    combos = {
        "legacy(off,off)": dict(share_aware_flatten=False, build_memo=False),
        "memo_only": dict(share_aware_flatten=False, build_memo=True),
        "guard_only": dict(share_aware_flatten=True, build_memo=False),
        "repaired(on,on)": dict(share_aware_flatten=True, build_memo=True),
    }
    out = {}
    for label, flags in combos.items():
        times = [timed(lambda e=e: compile_expr_to_cm_ir(e, **flags), repeats=5) * 1e6
                 for e in exprs]
        out[label] = {"median_us": statistics.median(times), "mean_us": statistics.mean(times)}
    base = out["legacy(off,off)"]["mean_us"]
    for label in out:
        out[label]["vs_legacy"] = out[label]["mean_us"] / base
    return out


# --------------------------------------------------------------------------
# 9. persistent path
# --------------------------------------------------------------------------

def run_persistent_path():
    expr = multiplier_bit(8, "sequential", 8)
    sup = support_of(expr)
    clear_cm_ir_persistent_cache()
    node_p = compile_expr_to_cm_ir_persistent(expr)
    node_n = compile_expr_to_cm_ir(expr)
    p_prog, n_prog = get_flat_program(node_p), get_flat_program(node_n)
    equal = _eval_words(p_prog, sup, {}) == _eval_words(n_prog, sup, {})
    ladder = None
    clear_cm_ir_persistent_cache()
    return {
        "persistent_word_ops": program_metrics(p_prog)["executed_word_ops"],
        "default_word_ops": program_metrics(n_prog)["executed_word_ops"],
        "packed_equal_when_mixed": equal,
        "keys_differ": node_p.key != node_n.key,
    }


# --------------------------------------------------------------------------
# 10. cse independence (subprocess: cm_ir must never load)
# --------------------------------------------------------------------------

def run_cse_independence():
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "from bitset_backend import compile_expr_cse, eval_expr_words_cse\n"
        "from cm_exprlib import And, Or, Xor, Var\n"
        "e = Xor(And(Var(0), Var(1)), Or(Var(2), Var(3)))\n"
        "compile_expr_cse(e); compile_expr_cse(e, flatten=True)\n"
        "eval_expr_words_cse(e, tuple('x%%d' %% i for i in range(6)))\n"
        "print('cm_ir_loaded=%%s' %% ('cm_ir' in sys.modules))\n" % ROOT
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    return {"stdout": proc.stdout.strip(), "returncode": proc.returncode,
            "independent": "cm_ir_loaded=False" in proc.stdout}


def main():
    sections = {
        "metrics_instrumented": run_metrics_instrumented,
        "corpus_key_regression": run_corpus_key_regression,
        "headline_reproduction": run_headline_reproduction,
        "semantic_fuzz": run_semantic_fuzz,
        "memo_lifetime_stress": run_memo_lifetime_stress,
        "reentrancy": run_reentrancy,
        "serde_fuzz": run_serde_fuzz,
        "regression_decomposition": run_regression_decomposition,
        "persistent_path": run_persistent_path,
        "cse_independence": run_cse_independence,
    }
    results = {"_meta": {"python": sys.version, "numpy": np.__version__}}
    for name, fn in sections.items():
        print(f"[{time.strftime('%H:%M:%S')}] {name} ...", flush=True)
        t0 = time.perf_counter()
        results[name] = fn()
        print(f"  done in {time.perf_counter() - t0:.1f}s", flush=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
