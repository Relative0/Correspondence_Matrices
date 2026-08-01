"""Deep follow-up probe for the CM benchmark gap audits (2026-08-02).

Adversarial re-examination of both `CM_BENCHMARK_GAP_ANALYSIS_2026-08-01.md`
and `deliverables_n22_24/CM_GAP_AUDIT_2026-08-01.md`.

Sections (select via --sections, comma-separated, default all):
  op_accounting   Program-length vs executed-word-op accounting (deterministic).
  cse_ladder      Four-rung compiler ladder (raw / CSE / CSE+flatten / CM) with
                  preparation cost, kernel-only eval, and non-arithmetic corpora.
  builder_memo    Builder arms on shared DAGs: current, id-memo, repo persistent
                  (digest-memo), compact-key prototype; in-memory and post-JSON.
  dag_serde       Scratch versioned defs/ref serialization: sharing round-trip,
                  dangling/forward-ref rejection, v1 compat, size, compile cost.
  variance        Independent recomputation of between-formula sigma from the
                  archived raw CSVs (df-correct, biased, regression, moments).
  repeat_platform Archived pod/local gap decomposition by repeat and live_k,
                  plus a schedule (blocked vs interleaved) rerun with cache
                  counters and an additive-overhead model check.
  bdd             Exact max-ROBDD bound at n=16, adder order-sensitivity check,
                  reorder arm, and task-matched pipelines (equivalence, model
                  count, restriction batch, BDD->packed extraction).
  defects         Quantified arm asymmetries and wrapper-vs-kernel overhead on
                  corpus formulas.

Everything is scratch-only: no production module is modified. All timed
comparisons assert exact packed-bigint equality first. Deterministic program
sizes are reported separately from machine-dependent timings.

Run with the benchmark interpreter:
  .venv/Scripts/python.exe deliverables_n22_24/cm_gap_deep_followup_2026_08_02.py
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.setrecursionlimit(200_000)

import numpy as np

from bitset_backend import (
    FlatProgram,
    _FLAT_OP_AND,
    _FLAT_OP_EQV,
    _FLAT_OP_IMP,
    _FLAT_OP_NOT,
    _FLAT_OP_OR,
    _FLAT_OP_XOR,
    _build_words_env_cached,
    _eval_words,
    bitset_env_cache_stats,
    clear_words_env_cache,
    compile_expr_flat,
    eval_cm_node_words,
    eval_expr_words_bitset,
    get_flat_program,
)
from cm_expr_serde import expr_from_json, expr_to_json
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import (
    CMIRBuilder,
    clear_cm_ir_persistent_cache,
    compile_expr_to_cm_ir,
    compile_expr_to_cm_ir_persistent,
    materialize_hybrid_no_reinflate,
)

DELIVERABLES = ROOT / "deliverables_n22_24"
CORPUS = DELIVERABLES / "v4audit_corpus_2026_07_24.jsonl"
LOCAL_RAW = DELIVERABLES / "CM_v4audit_packed_eval_raw.csv"
POD_RAW = DELIVERABLES / "CM_v4audit_packed_eval_raw_runpod.csv"
OUT = DELIVERABLES / "cm_gap_deep_followup_results_2026_08_02.json"

OPS_BY_NAME = {"and": And, "or": Or, "xor": Xor, "imp": Imp, "eqv": Eqv}
OPNAME = {And: "AND", Or: "OR", Xor: "XOR", Imp: "IMP", Eqv: "EQV"}
OPCODE = {"AND": _FLAT_OP_AND, "OR": _FLAT_OP_OR, "XOR": _FLAT_OP_XOR,
          "IMP": _FLAT_OP_IMP, "EQV": _FLAT_OP_EQV, "NOT": _FLAT_OP_NOT}


# --------------------------------------------------------------------------
# generic helpers
# --------------------------------------------------------------------------

def timed(fn, repeats: int = 1, blocks: int = 5) -> float:
    samples = []
    for _ in range(blocks):
        t0 = time.perf_counter()
        for _ in range(repeats):
            fn()
        samples.append((time.perf_counter() - t0) / repeats)
    return min(samples)


def tree_occurrences(expr) -> int:
    """Unfolded tree size, computed by DP over identity (never unfolds)."""
    memo: dict[int, int] = {}

    def rec(e) -> int:
        c = memo.get(id(e))
        if c is not None:
            return c
        if isinstance(e, Var):
            c = 1
        elif isinstance(e, Not):
            c = 1 + rec(e.a)
        else:
            c = 1 + rec(e.a) + rec(e.b)
        memo[id(e)] = c
        return c

    return rec(expr)


def identity_dag_nodes(expr) -> int:
    seen = set()
    stack = [expr]
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if isinstance(cur, Not):
            stack.append(cur.a)
        elif not isinstance(cur, Var):
            stack.extend((cur.a, cur.b))
    return len(seen)


def structural_dag_nodes(expr) -> int:
    """Distinct nodes under plain syntactic interning (no assoc/comm canon)."""
    intern: dict[tuple, int] = {}
    memo: dict[int, int] = {}

    def rec(e) -> int:
        cached = memo.get(id(e))
        if cached is not None:
            return cached
        if isinstance(e, Var):
            key = ("var", int(e.i))
        elif isinstance(e, Not):
            key = ("not", rec(e.a))
        else:
            key = (OPNAME[type(e)], rec(e.a), rec(e.b))
        uid = intern.setdefault(key, len(intern))
        memo[id(e)] = uid
        return uid

    rec(expr)
    return len(intern)


def expr_support(expr) -> tuple[str, ...]:
    seen: set[int] = set()
    out: set[int] = set()
    stack = [expr]
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


def expanded_word_ops(prog: FlatProgram) -> int:
    """Number of numpy kernel invocations _eval_words actually performs.

    len(prog.ops) undercounts CM programs because CM emits n-ary AND/OR/XOR
    args that the words kernel executes as (arity-1) binary ops, and IMP/EQV
    always execute as two kernel calls.
    """
    total = 0
    for _slot, opcode, args in prog.ops:
        if opcode == _FLAT_OP_NOT:
            total += 1
        elif opcode in (_FLAT_OP_IMP, _FLAT_OP_EQV):
            total += 2
        else:
            total += max(1, len(args) - 1)
    return total


# --------------------------------------------------------------------------
# formula generators
# --------------------------------------------------------------------------

def xor_chain(k: int):
    cur = Var(0)
    for i in range(1, k):
        cur = Xor(cur, Var(i))
    return cur


def add_words(a, b):
    width = max(len(a), len(b))
    out = []
    carry = None
    for i in range(width):
        ai = a[i] if i < len(a) else None
        bi = b[i] if i < len(b) else None
        terms = [x for x in (ai, bi, carry) if x is not None]
        if not terms:
            out.append(None)
            carry = None
        elif len(terms) == 1:
            out.append(terms[0])
            carry = None
        elif len(terms) == 2:
            out.append(Xor(terms[0], terms[1]))
            carry = And(terms[0], terms[1])
        else:
            ab = Xor(ai, bi)
            out.append(Xor(ab, carry))
            carry = Or(And(ai, bi), And(ab, carry))
    if carry is not None:
        out.append(carry)
    return out


def multiplier_bits(nb: int, topology: str):
    rows = []
    for j in range(nb):
        rows.append([None] * j + [And(Var(i), Var(nb + j)) for i in range(nb)])
    if topology == "sequential":
        acc = rows[0]
        for row in rows[1:]:
            acc = add_words(acc, row)
        return acc
    if topology == "chunk3":
        # third topology: sequential inside chunks of 3 rows, then a balanced
        # combine of chunk sums — structurally between the other two
        chunks = []
        for i in range(0, len(rows), 3):
            acc = rows[i]
            for row in rows[i + 1:i + 3]:
                acc = add_words(acc, row)
            chunks.append(acc)
        rows = chunks
    while len(rows) > 1:
        nxt = []
        for i in range(0, len(rows), 2):
            nxt.append(add_words(rows[i], rows[i + 1]) if i + 1 < len(rows) else rows[i])
        rows = nxt
    return rows[0]


def shared_ladder(depth: int):
    cur = Xor(Var(0), Var(1))
    for level in range(depth):
        a = Var(2 + (2 * level) % 14)
        b = Var(2 + (2 * level + 1) % 14)
        cur = Or(And(cur, a), And(cur, b))
    return cur


def mixed_shared_dag(n_vars: int, steps: int, seed: int):
    """Non-arithmetic shared DAG with mixed operators incl. IMP/EQV/NOT."""
    rng = random.Random(seed)
    pool = [Var(i) for i in range(n_vars)]
    for _ in range(steps):
        op = rng.choice(["and", "or", "xor", "imp", "eqv", "not"])
        if op == "not":
            e = Not(rng.choice(pool))
        else:
            e = OPS_BY_NAME[op](rng.choice(pool), rng.choice(pool))
        pool.append(e)
    root = pool[-1]
    for e in pool[-6:-1]:
        root = Xor(root, e)
    return root


def cancellation_cases():
    """Semantic redundancy CSE cannot remove but CM's local rewrites can."""
    h = None
    for i in range(6):
        term = And(Var(2 * i), Var(2 * i + 1))
        h = term if h is None else Xor(h, term)
    a = Or(Var(0), And(Var(1), Var(2)))
    b = And(Var(3), Or(Var(4), Var(5)))
    p = Var(6)
    return [
        ("xor_cancel", Xor(Xor(a, h), Xor(h, b))),           # == a xor b
        ("planted_contradiction", Or(a, And(h, And(p, Not(p))))),  # == a
        ("eqv_self", And(Eqv(h, h), b)),                     # == b
    ]


# --------------------------------------------------------------------------
# scratch compiler rungs (never touch production modules)
# --------------------------------------------------------------------------

def compile_cse_binary(expr) -> FlatProgram:
    """Rung 1: structural CSE, binary ops, no commutative/assoc canonicalization.

    Keys are small ints (syntactic intern ids), so dict lookups are O(1) —
    unlike the 2026-08-01 probe's nested-tuple keys, whose hashing is
    O(subtree) per lookup.
    """
    intern: dict[tuple, int] = {}
    slot_by_uid: dict[int, int] = {}
    memo: dict[int, int] = {}
    loads: list = []
    ops: list = []

    def rec(cur) -> int:
        got = memo.get(id(cur))
        if got is not None:
            return got
        if isinstance(cur, Var):
            key = ("var", int(cur.i))
            uid = intern.get(key)
            if uid is None:
                uid = intern[key] = len(intern)
                slot = len(loads) + len(ops)
                loads.append((slot, "var", f"x{cur.i}"))
                slot_by_uid[uid] = slot
        elif isinstance(cur, Not):
            child = rec(cur.a)
            key = ("NOT", child)
            uid = intern.get(key)
            if uid is None:
                uid = intern[key] = len(intern)
                slot = len(loads) + len(ops)
                ops.append((slot, _FLAT_OP_NOT, (slot_by_uid[child],)))
                slot_by_uid[uid] = slot
        else:
            left = rec(cur.a)
            right = rec(cur.b)
            opname = OPNAME[type(cur)]
            key = (opname, left, right)
            uid = intern.get(key)
            if uid is None:
                uid = intern[key] = len(intern)
                slot = len(loads) + len(ops)
                ops.append((slot, OPCODE[opname], (slot_by_uid[left], slot_by_uid[right])))
                slot_by_uid[uid] = slot
        memo[id(cur)] = uid
        return uid

    root = rec(expr)
    return FlatProgram(len(loads) + len(ops), slot_by_uid[root], tuple(loads), tuple(ops))


def compile_cse_flatten(expr) -> FlatProgram:
    """Rung 2: CSE + associative flattening + commutative arg sorting (n-ary).

    Purely syntactic: no constant folding, no duplicate/parity cancellation,
    no complement rules. AND/OR/XOR children of the same class are spliced
    (through sharing) and operand lists are sorted; EQV args are sorted;
    IMP preserves order. Duplicates are kept (removing them would be a
    semantic rewrite for XOR).
    """
    ASSOC = {"AND": And, "OR": Or, "XOR": Xor}
    intern: dict[tuple, int] = {}
    slot_by_uid: dict[int, int] = {}
    memo: dict[int, int] = {}
    flat_memo: dict[int, tuple] = {}
    loads: list = []
    ops: list = []

    def emit(key, opname, arg_uids) -> int:
        uid = intern.get(key)
        if uid is None:
            uid = intern[key] = len(intern)
            slot = len(loads) + len(ops)
            ops.append((slot, OPCODE[opname], tuple(slot_by_uid[a] for a in arg_uids)))
            slot_by_uid[uid] = slot
        return uid

    def operands(cur, cls) -> tuple:
        """Flatten the same-class spine of `cur` into processed operand uids."""
        got = flat_memo.get((id(cur), cls.__name__)) if False else None
        stack = [cur]
        out = []
        while stack:
            z = stack.pop()
            if isinstance(z, cls):
                stack.append(z.b)
                stack.append(z.a)
            else:
                out.append(rec(z))
        return tuple(out)

    def rec(cur) -> int:
        got = memo.get(id(cur))
        if got is not None:
            return got
        if isinstance(cur, Var):
            key = ("var", int(cur.i))
            uid = intern.get(key)
            if uid is None:
                uid = intern[key] = len(intern)
                slot = len(loads) + len(ops)
                loads.append((slot, "var", f"x{cur.i}"))
                slot_by_uid[uid] = slot
        elif isinstance(cur, Not):
            child = rec(cur.a)
            key = ("NOT", child)
            uid = intern.get(key)
            if uid is None:
                uid = intern[key] = len(intern)
                slot = len(loads) + len(ops)
                ops.append((slot, _FLAT_OP_NOT, (slot_by_uid[child],)))
                slot_by_uid[uid] = slot
        else:
            opname = OPNAME[type(cur)]
            if opname in ASSOC:
                arg_uids = tuple(sorted(operands(cur, type(cur))))
                key = (opname,) + arg_uids
                uid = emit(key, opname, arg_uids)
            elif opname == "EQV":
                arg_uids = tuple(sorted((rec(cur.a), rec(cur.b))))
                key = ("EQV",) + arg_uids
                uid = emit(key, "EQV", arg_uids)
            else:  # IMP: order preserved
                arg_uids = (rec(cur.a), rec(cur.b))
                key = ("IMP",) + arg_uids
                uid = emit(key, "IMP", arg_uids)
        memo[id(cur)] = uid
        return uid

    root = rec(expr)
    return FlatProgram(len(loads) + len(ops), slot_by_uid[root], tuple(loads), tuple(ops))


def compile_structural_cse_codex(expr) -> FlatProgram:
    """Verbatim re-implementation of the 2026-08-01 probe's CSE baseline
    (nested-tuple keys) — timed here only to expose its preparation cost."""
    loads = []
    ops = []
    slot_by_key = {}
    key_by_id = {}

    def rec(cur):
        prior_key = key_by_id.get(id(cur))
        if prior_key is not None:
            return slot_by_key[prior_key], prior_key
        if isinstance(cur, Var):
            key = ("var", int(cur.i))
            if key not in slot_by_key:
                slot = len(loads) + len(ops)
                loads.append((slot, "var", f"x{cur.i}"))
                slot_by_key[key] = slot
        elif isinstance(cur, Not):
            child_slot, child_key = rec(cur.a)
            key = ("NOT", child_key)
            if key not in slot_by_key:
                slot = len(loads) + len(ops)
                ops.append((slot, _FLAT_OP_NOT, (child_slot,)))
                slot_by_key[key] = slot
        else:
            left_slot, left_key = rec(cur.a)
            right_slot, right_key = rec(cur.b)
            opname = OPNAME[type(cur)]
            key = (opname, left_key, right_key)
            if key not in slot_by_key:
                slot = len(loads) + len(ops)
                ops.append((slot, OPCODE[opname], (left_slot, right_slot)))
                slot_by_key[key] = slot
        key_by_id[id(cur)] = key
        return slot_by_key[key], key

    root_slot, _ = rec(expr)
    return FlatProgram(len(loads) + len(ops), root_slot, tuple(loads), tuple(ops))


class IdMemoBuilder(CMIRBuilder):
    """Codex's proposed repair: id-keyed memo over CMIRBuilder.build."""

    def __init__(self):
        super().__init__()
        self.expr_memo = {}
        self.visits = 0

    def build(self, expr):
        cached = self.expr_memo.get(id(expr))
        if cached is not None:
            return cached
        self.visits += 1
        node = super().build(expr)
        self.expr_memo[id(expr)] = node
        return node


class CountingBuilder(CMIRBuilder):
    def __init__(self):
        super().__init__()
        self.visits = 0

    def build(self, expr):
        self.visits += 1
        return super().build(expr)


# --------------------------------------------------------------------------
# compact-key builder prototype (scratch mirror of CMIRBuilder semantics)
# --------------------------------------------------------------------------

class _CNode:
    __slots__ = ("op", "args", "var_name", "const", "uid")

    def __init__(self, op, args, var_name, const, uid):
        self.op = op            # "VAR" | "CONST" | "NOT" | "AND" | "OR" | "XOR" | "IMP" | "EQV"
        self.args = args
        self.var_name = var_name
        self.const = const
        self.uid = uid


class CompactBuilder:
    """Intern-ID prototype: same canonicalization rules as CMIRBuilder
    (flatten assoc, sort commutative, const-fold, dedupe, complement, XOR
    parity), but interning keys are tuples of small ints and commutative
    sorting is by intern uid instead of deep structural keys. The canonical
    *order* of args therefore differs from production; semantics are verified
    by packed equality."""

    def __init__(self):
        self.intern: dict[tuple, _CNode] = {}
        self.expr_memo: dict[int, _CNode] = {}
        self.visits = 0

    def _mk(self, key, op, args=(), var_name="", const=None) -> _CNode:
        node = self.intern.get(key)
        if node is None:
            node = _CNode(op, tuple(args), var_name, const, len(self.intern))
            self.intern[key] = node
        return node

    def const_(self, v: int) -> _CNode:
        return self._mk(("CONST", int(bool(v))), "CONST", const=int(bool(v)))

    def var_(self, name: str) -> _CNode:
        return self._mk(("VAR", name), "VAR", var_name=name)

    def negate(self, n: _CNode) -> _CNode:
        if n.const is not None:
            return self.const_(1 - n.const)
        if n.op == "NOT":
            return n.args[0]
        return self._mk(("NOT", n.uid), "NOT", args=(n,))

    def _flatten_sort(self, op: str, args) -> list:
        out = []
        for a in args:
            if a.op == op:
                out.extend(a.args)
            else:
                out.append(a)
        out.sort(key=lambda z: z.uid)
        return out

    def make_and_or(self, op: str, args) -> _CNode:
        absorb = 0 if op == "AND" else 1
        neutral = 1 - absorb
        out = []
        seen = set()
        negated_bases = set()
        for n in self._flatten_sort(op, args):
            if n.const is not None:
                if n.const == absorb:
                    return self.const_(absorb)
                continue
            if n.uid in seen:
                continue
            if (n.op == "NOT" and n.args[0].uid in seen) or (n.uid in negated_bases):
                return self.const_(absorb)
            out.append(n)
            seen.add(n.uid)
            if n.op == "NOT":
                negated_bases.add(n.args[0].uid)
        if not out:
            return self.const_(neutral)
        if len(out) == 1:
            return out[0]
        key = (op,) + tuple(n.uid for n in out)
        return self._mk(key, op, args=out)

    def make_xor(self, args) -> _CNode:
        counts: dict[int, _CNode] = {}
        parity = 0
        odd: dict[int, int] = {}
        for n in self._flatten_sort("XOR", args):
            if n.const is not None:
                parity ^= n.const
                continue
            odd[n.uid] = odd.get(n.uid, 0) + 1
            counts[n.uid] = n
        out = [counts[uid] for uid in sorted(odd) if odd[uid] % 2 == 1]
        if not out:
            return self.const_(parity)
        if len(out) == 1:
            return self.negate(out[0]) if parity else out[0]
        base = self._mk(("XOR",) + tuple(n.uid for n in out), "XOR", args=out)
        return self.negate(base) if parity else base

    def make_eqv(self, left: _CNode, right: _CNode) -> _CNode:
        if left is right:
            return self.const_(1)
        if (left.op == "NOT" and left.args[0] is right) or (right.op == "NOT" and right.args[0] is left):
            return self.const_(0)
        if left.const == 1:
            return right
        if right.const == 1:
            return left
        if left.const == 0:
            return self.negate(right)
        if right.const == 0:
            return self.negate(left)
        a, b = sorted((left, right), key=lambda z: z.uid)
        return self._mk(("EQV", a.uid, b.uid), "EQV", args=(a, b))

    def make_imp(self, left: _CNode, right: _CNode) -> _CNode:
        if left is right:
            return self.const_(1)
        if left.const == 0 or right.const == 1:
            return self.const_(1)
        if left.const == 1:
            return right
        if right.const == 0:
            return self.negate(left)
        return self._mk(("IMP", left.uid, right.uid), "IMP", args=(left, right))

    def build(self, expr) -> _CNode:
        cached = self.expr_memo.get(id(expr))
        if cached is not None:
            return cached
        self.visits += 1
        if isinstance(expr, Var):
            node = self.var_(f"x{int(expr.i)}")
        elif isinstance(expr, Not):
            node = self.negate(self.build(expr.a))
        elif isinstance(expr, And):
            node = self.make_and_or("AND", (self.build(expr.a), self.build(expr.b)))
        elif isinstance(expr, Or):
            node = self.make_and_or("OR", (self.build(expr.a), self.build(expr.b)))
        elif isinstance(expr, Xor):
            node = self.make_xor((self.build(expr.a), self.build(expr.b)))
        elif isinstance(expr, Imp):
            node = self.make_imp(self.build(expr.a), self.build(expr.b))
        elif isinstance(expr, Eqv):
            node = self.make_eqv(self.build(expr.a), self.build(expr.b))
        else:
            raise TypeError(expr)
        self.expr_memo[id(expr)] = node
        return node


def compact_lower(root: _CNode) -> FlatProgram:
    slot_of: dict[int, int] = {}
    loads = []
    ops = []
    stack = [(root, False)]
    while stack:
        cur, processed = stack.pop()
        if cur.uid in slot_of:
            continue
        if not processed:
            stack.append((cur, True))
            for a in cur.args:
                if a.uid not in slot_of:
                    stack.append((a, False))
            continue
        slot = len(slot_of)
        slot_of[cur.uid] = slot
        if cur.op == "CONST":
            loads.append((slot, "const", cur.const))
        elif cur.op == "VAR":
            loads.append((slot, "var", cur.var_name))
        else:
            ops.append((slot, OPCODE[cur.op], tuple(slot_of[a.uid] for a in cur.args)))
    return FlatProgram(len(slot_of), slot_of[root.uid], tuple(loads), tuple(ops))


def compile_compact(expr) -> FlatProgram:
    b = CompactBuilder()
    return compact_lower(b.build(expr))


# --------------------------------------------------------------------------
# scratch versioned defs/ref serde (Q3)
# --------------------------------------------------------------------------

def expr_to_json_v2(expr, dedupe: str = "identity") -> dict:
    """Versioned defs/ref serialization. `dedupe` = 'identity' emits one def
    per identity-shared object; 'structural' merges syntactically equal nodes
    (recovering sharing that fresh Var()/And() construction loses)."""
    nodes: list = []
    by_identity: dict[int, int] = {}
    by_structure: dict[tuple, int] = {}
    structural = dedupe == "structural"

    def rec(e) -> int:
        got = by_identity.get(id(e))
        if got is not None:
            return got
        if isinstance(e, Var):
            entry = {"op": "var", "i": int(e.i)}
            skey = ("var", int(e.i))
        elif isinstance(e, Not):
            a = rec(e.a)
            entry = {"op": "not", "a": a}
            skey = ("not", a)
        else:
            a = rec(e.a)
            b = rec(e.b)
            opname = OPNAME[type(e)].lower()
            entry = {"op": opname, "a": a, "b": b}
            skey = (opname, a, b)
        if structural:
            idx = by_structure.get(skey)
            if idx is None:
                idx = len(nodes)
                nodes.append(entry)
                by_structure[skey] = idx
        else:
            idx = len(nodes)
            nodes.append(entry)
        by_identity[id(e)] = idx
        return idx

    root = rec(expr)
    return {"version": 2, "nodes": nodes, "root": root}


def expr_from_json_v2(doc):
    """Accepts v2 defs/ref docs and falls back to the v1 tree schema.

    Refs must point strictly backwards (ref < own index), which makes cycles
    unrepresentable; dangling/forward/out-of-range refs raise ValueError."""
    if not isinstance(doc, dict):
        raise ValueError("expression document must be an object")
    if "version" not in doc and "op" in doc:
        return expr_from_json(doc)  # v1 tree compatibility
    if doc.get("version") != 2:
        raise ValueError(f"unsupported expression schema version: {doc.get('version')!r}")
    nodes_json = doc.get("nodes")
    if not isinstance(nodes_json, list) or not nodes_json:
        raise ValueError("v2 document must contain a non-empty 'nodes' list")
    built: list = []
    for idx, entry in enumerate(nodes_json):
        op = str(entry.get("op", "")).lower()

        def ref(field):
            v = entry.get(field)
            if not isinstance(v, int) or isinstance(v, bool) or not (0 <= v < idx):
                raise ValueError(
                    f"node {idx}: ref {field}={v!r} must be an int in [0, {idx}) "
                    "(forward/dangling refs rejected; cycles unrepresentable)")
            return built[v]

        if op == "var":
            built.append(Var(int(entry["i"])))
        elif op == "not":
            built.append(Not(ref("a")))
        elif op in OPS_BY_NAME:
            built.append(OPS_BY_NAME[op](ref("a"), ref("b")))
        else:
            raise ValueError(f"node {idx}: unsupported op {op!r}")
    root = doc.get("root")
    if not isinstance(root, int) or isinstance(root, bool) or not (0 <= root < len(built)):
        raise ValueError(f"root={root!r} out of range")
    return built[root]


# --------------------------------------------------------------------------
# section: op_accounting + cse_ladder
# --------------------------------------------------------------------------

def ladder_cases():
    cases = []
    cases.append(("xor_chain_k16", xor_chain(16)))
    for topology in ("sequential", "balanced", "chunk3"):
        for nb, bits in ((4, (3, 4)), (6, (5, 6)), (8, (6, 7, 8))):
            outs = multiplier_bits(nb, topology)
            for bit in bits:
                if bit < len(outs) and outs[bit] is not None:
                    cases.append((f"mult_{topology}_nb{nb}_bit{bit}", outs[bit]))
    cases.append(("shared_ladder_d8", shared_ladder(8)))
    for steps, seed in ((30, 1), (60, 2)):
        cases.append((f"mixed_dag_s{steps}_seed{seed}", mixed_shared_dag(12, steps, seed)))
    for name, e in cancellation_cases():
        cases.append((f"cancel_{name}", e))
    return cases


def run_cse_ladder():
    rows = []
    for name, expr in ladder_cases():
        support = expr_support(expr)
        if len(support) < 6:
            support = tuple(sorted(set(support) | {f"x{i}" for i in range(6)},
                                   key=lambda s: int(s[1:])))
        tree = tree_occurrences(expr)
        raw_feasible = tree <= 90_000
        node = compile_expr_to_cm_ir(expr)
        cm_prog = get_flat_program(node)
        cse_prog = compile_cse_binary(expr)
        cseflat_prog = compile_cse_flatten(expr)
        raw_prog = compile_expr_flat(expr) if raw_feasible else None

        fixed: dict = {}
        vals = {
            "cm": _eval_words(cm_prog, support, fixed),
            "cse": _eval_words(cse_prog, support, fixed),
            "cse_flat": _eval_words(cseflat_prog, support, fixed),
        }
        if raw_prog is not None:
            vals["raw"] = _eval_words(raw_prog, support, fixed)
        ref = vals["cm"]
        if any(v != ref for v in vals.values()):
            raise AssertionError(f"packed mismatch in {name}")

        def ops_pair(p):
            return (len(p.ops), expanded_word_ops(p)) if p is not None else (None, None)

        row = {
            "case": name,
            "support_k": len(support),
            "tree_occurrences": tree,
            "identity_dag_nodes": identity_dag_nodes(expr),
            "structural_dag_nodes": structural_dag_nodes(expr),
            "packed_equal": True,
        }
        for arm, prog in (("cm", cm_prog), ("raw", raw_prog),
                          ("cse", cse_prog), ("cse_flat", cseflat_prog)):
            n_ops, n_word = ops_pair(prog)
            row[f"{arm}_ops"] = n_ops
            row[f"{arm}_word_ops"] = n_word

        # preparation cost (fresh state each call)
        row["prep_cm_compile_us"] = timed(lambda: compile_expr_to_cm_ir(expr), blocks=3) * 1e6
        row["prep_cse_us"] = timed(lambda: compile_cse_binary(expr), blocks=3) * 1e6
        row["prep_cse_flat_us"] = timed(lambda: compile_cse_flatten(expr), blocks=3) * 1e6
        row["prep_cse_codexkeys_us"] = timed(lambda: compile_structural_cse_codex(expr), blocks=3) * 1e6
        if raw_feasible:
            row["prep_raw_us"] = timed(lambda: compile_expr_flat(expr), blocks=3) * 1e6

        # kernel-only eval, identical call shape for every arm
        big = max(len(cm_prog.ops), len(cse_prog.ops))
        repeats = max(3, min(200, 20_000 // max(1, big)))
        row["eval_repeats"] = repeats
        row["eval_cm_us"] = timed(lambda: _eval_words(cm_prog, support, fixed), repeats=repeats) * 1e6
        row["eval_cse_us"] = timed(lambda: _eval_words(cse_prog, support, fixed), repeats=repeats) * 1e6
        row["eval_cse_flat_us"] = timed(lambda: _eval_words(cseflat_prog, support, fixed), repeats=repeats) * 1e6
        if raw_prog is not None and len(raw_prog.ops) <= 40_000:
            raw_repeats = max(1, min(repeats, 20_000 // max(1, len(raw_prog.ops))))
            row["eval_raw_us"] = timed(lambda: _eval_words(raw_prog, support, fixed),
                                       repeats=raw_repeats, blocks=3) * 1e6
        rows.append(row)
    return rows


# --------------------------------------------------------------------------
# section: builder_memo
# --------------------------------------------------------------------------

def run_builder_memo():
    cases = []
    for depth in (4, 6, 8, 10, 11):
        cases.append((f"shared_ladder_d{depth}", shared_ladder(depth)))
    cases.append(("mult_sequential_nb6_bit6", multiplier_bits(6, "sequential")[6]))
    cases.append(("mult_sequential_nb8_bit8", multiplier_bits(8, "sequential")[8]))

    rows = []
    for name, expr in cases:
        support = expr_support(expr)
        tree = tree_occurrences(expr)
        slow = tree > 20_000
        blocks = 1 if slow else 3
        rt = expr_from_json(expr_to_json(expr))  # tree JSON round-trip

        row = {
            "case": name,
            "support_k": len(support),
            "tree_occurrences": tree,
            "identity_dag_nodes_memory": identity_dag_nodes(expr),
            "identity_dag_nodes_after_tree_json": identity_dag_nodes(rt),
            "structural_dag_nodes": structural_dag_nodes(expr),
        }

        # reference value
        ref_node = compile_expr_to_cm_ir(expr)
        ref = eval_cm_node_words(ref_node, support, fixed={})
        row["cm_ops"] = len(get_flat_program(ref_node).ops)

        def check(node) -> bool:
            return eval_cm_node_words(node, support, fixed={}) == ref

        def check_prog(prog) -> bool:
            return _eval_words(prog, support, {}) == ref

        # --- in-memory shared DAG arms
        row["mem_current_us"] = timed(lambda: compile_expr_to_cm_ir(expr), blocks=blocks) * 1e6
        cb = CountingBuilder(); cb.build(expr)
        row["mem_current_visits"] = cb.visits

        row["mem_idmemo_us"] = timed(lambda: IdMemoBuilder().build(expr), blocks=blocks) * 1e6
        ib = IdMemoBuilder(); n_ib = ib.build(expr)
        row["mem_idmemo_visits"] = ib.visits
        row["mem_idmemo_ok"] = check(n_ib)

        def persistent_cold():
            clear_cm_ir_persistent_cache()
            return compile_expr_to_cm_ir_persistent(expr)
        row["mem_persistent_cold_us"] = timed(persistent_cold, blocks=blocks) * 1e6
        clear_cm_ir_persistent_cache()
        n_p = compile_expr_to_cm_ir_persistent(expr)
        row["mem_persistent_ok"] = check(n_p)
        row["mem_persistent_warm_us"] = timed(
            lambda: compile_expr_to_cm_ir_persistent(expr), blocks=blocks) * 1e6
        clear_cm_ir_persistent_cache()

        row["mem_compact_us"] = timed(lambda: compile_compact(expr), blocks=blocks) * 1e6
        comp_b = CompactBuilder(); comp_prog = compact_lower(comp_b.build(expr))
        row["mem_compact_visits"] = comp_b.visits
        row["mem_compact_ops"] = len(comp_prog.ops)
        row["mem_compact_ok"] = check_prog(comp_prog)

        # --- after tree-JSON round-trip (sharing destroyed)
        row["json_current_us"] = timed(lambda: compile_expr_to_cm_ir(rt), blocks=blocks) * 1e6
        row["json_idmemo_us"] = timed(lambda: IdMemoBuilder().build(rt), blocks=blocks) * 1e6

        def persistent_cold_rt():
            clear_cm_ir_persistent_cache()
            return compile_expr_to_cm_ir_persistent(rt)
        row["json_persistent_cold_us"] = timed(persistent_cold_rt, blocks=blocks) * 1e6
        clear_cm_ir_persistent_cache()
        n_prt = compile_expr_to_cm_ir_persistent(rt)
        row["json_persistent_ok"] = check(n_prt)
        clear_cm_ir_persistent_cache()

        row["json_compact_us"] = timed(lambda: compile_compact(rt), blocks=blocks) * 1e6
        row["json_compact_ok"] = check_prog(compile_compact(rt))
        rows.append(row)
    return rows


# --------------------------------------------------------------------------
# section: dag_serde
# --------------------------------------------------------------------------

def run_dag_serde():
    out: dict = {"rejection_tests": [], "roundtrip": [], "sizes": []}

    # rejection tests
    def expect_error(label, doc):
        try:
            expr_from_json_v2(doc)
        except ValueError as exc:
            out["rejection_tests"].append({"case": label, "rejected": True, "error": str(exc)[:120]})
        else:
            out["rejection_tests"].append({"case": label, "rejected": False})

    expect_error("forward_ref(cycle-shaped)", {
        "version": 2, "root": 1,
        "nodes": [{"op": "not", "a": 1}, {"op": "and", "a": 0, "b": 0}]})
    expect_error("dangling_ref", {
        "version": 2, "root": 0,
        "nodes": [{"op": "and", "a": 5, "b": 0}]})
    expect_error("self_ref", {
        "version": 2, "root": 0, "nodes": [{"op": "not", "a": 0}]})
    expect_error("bad_root", {
        "version": 2, "root": 9, "nodes": [{"op": "var", "i": 0}]})
    expect_error("bad_version", {"version": 3, "nodes": [], "root": 0})

    # v1 compatibility
    v1_doc = expr_to_json(shared_ladder(3))
    e_v1 = expr_from_json_v2(v1_doc)
    out["v1_compat_ok"] = (
        eval_expr_words_bitset(e_v1, tuple(f"x{i}" for i in range(16)))
        == eval_expr_words_bitset(shared_ladder(3), tuple(f"x{i}" for i in range(16))))

    for name, expr in (("shared_ladder_d10", shared_ladder(10)),
                       ("mult_sequential_nb7_bit7", multiplier_bits(7, "sequential")[7]),
                       ("mixed_dag_s60_seed2", mixed_shared_dag(12, 60, 2))):
        support = expr_support(expr)
        tree = tree_occurrences(expr)
        doc_id = expr_to_json_v2(expr, dedupe="identity")
        doc_st = expr_to_json_v2(expr, dedupe="structural")
        rt_id = expr_from_json_v2(json.loads(json.dumps(doc_id)))
        rt_st = expr_from_json_v2(json.loads(json.dumps(doc_st)))
        ref = eval_expr_words_bitset_safe(expr, support)
        out["roundtrip"].append({
            "case": name,
            "tree_occurrences": tree,
            "identity_dag_nodes": identity_dag_nodes(expr),
            "v2_identity_defs": len(doc_id["nodes"]),
            "v2_structural_defs": len(doc_st["nodes"]),
            "identity_dag_after_v2_identity": identity_dag_nodes(rt_id),
            "identity_dag_after_v2_structural": identity_dag_nodes(rt_st),
            "identity_dag_after_v1_tree": None if tree > 90_000 else identity_dag_nodes(
                expr_from_json(expr_to_json(expr))),
            "semantics_ok": (
                eval_expr_words_bitset_safe(rt_id, support) == ref
                and eval_expr_words_bitset_safe(rt_st, support) == ref),
            "compile_idmemo_after_v2_us": timed(
                lambda: IdMemoBuilder().build(rt_st), blocks=3) * 1e6,
            "compile_current_after_v2_us": timed(
                lambda: compile_expr_to_cm_ir(rt_st), blocks=1) * 1e6,
        })
        v1_bytes = None
        if tree <= 90_000:
            v1_bytes = len(json.dumps(expr_to_json(expr)))
        out["sizes"].append({
            "case": name,
            "v1_tree_bytes": v1_bytes,
            "v2_identity_bytes": len(json.dumps(doc_id)),
            "v2_structural_bytes": len(json.dumps(doc_st)),
        })
    return out


def eval_expr_words_bitset_safe(expr, support):
    # raw-tree evaluation is infeasible on huge unfoldings; go through the
    # structural-CSE program instead (already proven bit-identical above).
    if tree_occurrences(expr) > 90_000:
        return _eval_words(compile_cse_binary(expr), tuple(support), {})
    return eval_expr_words_bitset(expr, tuple(support))


# --------------------------------------------------------------------------
# section: variance (written independently of the 2026-08-01 probe)
# --------------------------------------------------------------------------

# chi-square quantiles (df -> (chi2_0.025, chi2_0.975)), standard table values
_CHI2 = {10: (3.247, 20.483), 19: (8.907, 32.852)}


def run_variance():
    out = []
    for path in (LOCAL_RAW, POD_RAW):
        with path.open(newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r["status"] == "ok"]
        sparse = [r for r in rows if r["family"] == "sparse_depth4"]
        per_formula: dict[str, list[float]] = defaultdict(list)
        live_k: dict[str, int] = {}
        for r in sparse:
            per_formula[r["id"]].append(math.log(float(r["paired_ratio"])))
            live_k[r["id"]] = int(r["live_k"])

        stats = {}
        for fid, logs in per_formula.items():
            stats[fid] = {
                "median": statistics.median(logs),
                "mean": statistics.mean(logs),
                "within_var": statistics.variance(logs),
                "rounds": len(logs),
                "live_k": live_k[fid],
            }

        cells: dict[int, list[str]] = defaultdict(list)
        for fid, s in stats.items():
            cells[s["live_k"]].append(fid)

        ss_median = 0.0
        ss_mean = 0.0
        df = 0
        noise_terms = []
        for k, fids in cells.items():
            if len(fids) < 2:
                continue
            med_center = statistics.mean(stats[f]["median"] for f in fids)
            mean_center = statistics.mean(stats[f]["mean"] for f in fids)
            ss_median += sum((stats[f]["median"] - med_center) ** 2 for f in fids)
            ss_mean += sum((stats[f]["mean"] - mean_center) ** 2 for f in fids)
            df += len(fids) - 1
            noise_terms.extend(stats[f]["within_var"] / stats[f]["rounds"] for f in fids)

        n_all = len(stats)
        s2 = ss_median / df
        sigma_df = math.sqrt(s2)
        lo_q, hi_q = _CHI2[df]
        # OLS of per-formula median on live_k over all 21 formulas (uses
        # singleton cells at the price of a linearity assumption)
        xs = [stats[f]["live_k"] for f in stats]
        ys = [stats[f]["median"] for f in stats]
        xbar, ybar = statistics.mean(xs), statistics.mean(ys)
        sxx = sum((x - xbar) ** 2 for x in xs)
        beta = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / sxx
        alpha = ybar - beta * xbar
        resid_ss = sum((y - (alpha + beta * x)) ** 2 for x, y in zip(xs, ys))
        df_reg = n_all - 2
        sigma_reg = math.sqrt(resid_ss / df_reg)
        lo_rq, hi_rq = _CHI2[df_reg]

        noise = statistics.mean(noise_terms)
        sigma_latent = math.sqrt(max(0.0, s2 - noise))

        def n_for(delta_pct, sigma):
            delta = math.log(1 + delta_pct / 100.0)
            n = ((1.959964 + 0.841621) * sigma / delta) ** 2
            return math.ceil(n) + 2  # +2 ~ small-sample t correction

        out.append({
            "file": path.name,
            "formulas": n_all,
            "cell_sizes": {str(k): len(v) for k, v in sorted(cells.items())},
            "residual_df": df,
            "sigma_within_cell_df_correct_median": sigma_df,
            "sigma_within_cell_df_correct_mean": math.sqrt(ss_mean / df),
            "sigma_divide_by_21_reproduction": math.sqrt(ss_median / n_all),
            "sigma_df_correct_CI95": [
                math.sqrt(df * s2 / hi_q), math.sqrt(df * s2 / lo_q)],
            "sigma_regression_on_live_k": sigma_reg,
            "sigma_regression_CI95": [
                math.sqrt(df_reg * sigma_reg ** 2 / hi_rq),
                math.sqrt(df_reg * sigma_reg ** 2 / lo_rq)],
            "regression_slope_per_live_k": beta,
            "mean_within_formula_noise_var_of_median_proxy": noise,
            "sigma_latent_moment_corrected": sigma_latent,
            "sample_sizes": {
                f"{eff}pct_sigma{sig}": n_for(eff, sig)
                for eff in (3, 5, 8)
                for sig in (0.065, 0.09, 0.10, 0.12, 0.15)
            },
        })
    return out


# --------------------------------------------------------------------------
# section: repeat_platform
# --------------------------------------------------------------------------

def run_repeat_platform(schedule_passes: int = 100):
    def load(path):
        with path.open(newline="", encoding="utf-8") as fh:
            return [r for r in csv.DictReader(fh) if r["status"] == "ok"]

    local = load(LOCAL_RAW)
    pod = load(POD_RAW)

    def per_formula(rows):
        acc = defaultdict(list)
        meta = {}
        for r in rows:
            acc[r["id"]].append(float(r["paired_ratio"]))
            meta[r["id"]] = {
                "live_k": int(r["live_k"]),
                "repeat": int(r["repeat"]),
                "bitset_us": float(r["bitset_us"]),
                "cm_us": float(r["cm_us"]),
            }
        return {fid: statistics.median(v) for fid, v in acc.items()}, meta

    l_med, l_meta = per_formula(local)
    p_med, _ = per_formula(pod)
    joined = []
    for fid in l_med:
        if fid not in p_med:
            continue
        joined.append({
            "id": fid,
            "live_k": l_meta[fid]["live_k"],
            "local_repeat": l_meta[fid]["repeat"],
            "local_ratio": l_med[fid],
            "pod_ratio": p_med[fid],
            "gap": p_med[fid] / l_med[fid],
            "local_bitset_us": l_meta[fid]["bitset_us"],
        })

    def geomean(vals):
        return math.exp(statistics.mean(math.log(v) for v in vals))

    by_repeat = defaultdict(list)
    by_livek = defaultdict(list)
    for j in joined:
        by_repeat[j["local_repeat"]].append(j["gap"])
        by_livek[j["live_k"]].append(j["gap"])

    # confound check: repeat was assigned by measured speed, so repeat group
    # is a proxy for formula cost. Correlate log(gap) with log(local bitset us).
    lg = [math.log(j["gap"]) for j in joined]
    lb = [math.log(j["local_bitset_us"]) for j in joined]
    mg, mb = statistics.mean(lg), statistics.mean(lb)
    corr = (sum((a - mg) * (b - mb) for a, b in zip(lg, lb))
            / math.sqrt(sum((a - mg) ** 2 for a in lg) * sum((b - mb) ** 2 for b in lb)))

    archived = {
        "n_joined_formulas": len(joined),
        "gap_geomean_all": geomean([j["gap"] for j in joined]),
        "gap_geomean_by_local_repeat": {str(k): geomean(v) for k, v in sorted(by_repeat.items())},
        "repeat_group_sizes": {str(k): len(v) for k, v in sorted(by_repeat.items())},
        "gap_geomean_by_live_k": {str(k): geomean(v) for k, v in sorted(by_livek.items())},
        "corr_log_gap_vs_log_local_bitset_us": corr,
        "mean_bitset_us_by_repeat": {
            str(k): statistics.mean(j["local_bitset_us"] for j in joined if j["local_repeat"] == k)
            for k in sorted(by_repeat)},
    }

    # ---- schedule rerun: blocked vs interleaved, formula identity controlled
    corpus = [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines()]
    chosen = {}
    for item in corpus:
        if item["explicit_packed_policy"] != "run":
            continue
        k = item["semantic_live_k"]
        if k not in chosen:
            chosen[k] = item
    items = [chosen[k] for k in sorted(chosen)]

    prepared = []
    for item in items:
        expr = expr_from_json(item["expression"])
        support = tuple(item["semantic_support"])
        fixed = {f"x{i}": 0 for i in range(item["nominal_n"]) if f"x{i}" not in support}
        node = compile_expr_to_cm_ir(expr)
        if eval_cm_node_words(node, support, fixed=fixed) != eval_expr_words_bitset(expr, support, fixed=fixed):
            raise AssertionError(item["id"])
        prepared.append((item, node, expr, support, fixed))

    def blocked():
        rows = []
        for item, node, expr, support, fixed in prepared:
            ratios = []
            for rnd in range(4):
                if rnd % 2:
                    cm = timed(lambda: eval_cm_node_words(node, support, fixed=fixed), 100, blocks=1)
                    bs = timed(lambda: eval_expr_words_bitset(expr, support, fixed=fixed), 100, blocks=1)
                else:
                    bs = timed(lambda: eval_expr_words_bitset(expr, support, fixed=fixed), 100, blocks=1)
                    cm = timed(lambda: eval_cm_node_words(node, support, fixed=fixed), 100, blocks=1)
                ratios.append(cm / bs)
            rows.append({"id": item["id"], "live_k": item["semantic_live_k"],
                         "ratio": statistics.median(ratios)})
        return rows

    def interleaved():
        tot_cm = defaultdict(float)
        tot_bs = defaultdict(float)
        for p in range(schedule_passes):
            for item, node, expr, support, fixed in prepared:
                if p % 2:
                    t0 = time.perf_counter(); eval_cm_node_words(node, support, fixed=fixed)
                    t1 = time.perf_counter(); eval_expr_words_bitset(expr, support, fixed=fixed)
                    t2 = time.perf_counter()
                    tot_cm[item["id"]] += t1 - t0; tot_bs[item["id"]] += t2 - t1
                else:
                    t0 = time.perf_counter(); eval_expr_words_bitset(expr, support, fixed=fixed)
                    t1 = time.perf_counter(); eval_cm_node_words(node, support, fixed=fixed)
                    t2 = time.perf_counter()
                    tot_bs[item["id"]] += t1 - t0; tot_cm[item["id"]] += t2 - t1
        return [{"id": item["id"], "live_k": item["semantic_live_k"],
                 "ratio": tot_cm[item["id"]] / tot_bs[item["id"]],
                 "cm_us": tot_cm[item["id"]] / schedule_passes * 1e6,
                 "bs_us": tot_bs[item["id"]] / schedule_passes * 1e6}
                for item, *_ in prepared]

    clear_words_env_cache()
    env0 = bitset_env_cache_stats()
    words0 = _build_words_env_cached.cache_info()
    blocked_rows = blocked()
    words_after_blocked = _build_words_env_cached.cache_info()
    inter_rows = interleaved()
    words_after_inter = _build_words_env_cached.cache_info()
    env1 = bitset_env_cache_stats()

    # direct measurement of the per-miss words-env rebuild cost at k=16
    key16 = tuple(f"x{i}" for i in range(16))
    def rebuild16():
        _build_words_env_cached.cache_clear()
        _build_words_env_cached(key16)
    env_rebuild_us = timed(rebuild16, blocks=5) * 1e6

    paired = {b["id"]: (b["ratio"],) for b in blocked_rows}
    for r in inter_rows:
        paired[r["id"]] += (r["ratio"],)

    schedule = {
        "n_formulas": len(prepared),
        "passes": schedule_passes,
        "blocked_geomean_ratio": math.exp(statistics.mean(
            math.log(b["ratio"]) for b in blocked_rows)),
        "interleaved_geomean_ratio": math.exp(statistics.mean(
            math.log(r["ratio"]) for r in inter_rows)),
        "per_formula": [
            {"id": fid, "blocked": v[0], "interleaved": v[1]}
            for fid, v in paired.items()],
        "words_env_cache": {
            "after_blocked": {"hits": words_after_blocked.hits, "misses": words_after_blocked.misses},
            "after_interleaved": {"hits": words_after_inter.hits - words_after_blocked.hits,
                                  "misses": words_after_inter.misses - words_after_blocked.misses},
        },
        "bitset_env_cache_start": env0,
        "bitset_env_cache_end": env1,
        "words_env_rebuild_k16_us": env_rebuild_us,
        "interleaved_rows": inter_rows,
    }
    return {"archived": archived, "schedule": schedule}


# --------------------------------------------------------------------------
# section: bdd
# --------------------------------------------------------------------------

def exact_max_robdd_nodes(n: int) -> int:
    total = 2  # terminals
    for i in range(1, n + 1):
        below = n - i
        width = min(1 << (i - 1), (1 << (1 << (below + 1))) - (1 << (1 << below)))
        total += width
    return total


def ripple_carry_out(m: int, interleave: bool):
    """Carry-out of an m-bit ripple adder. Variable indices chosen so that the
    natural x0..x{2m-1} declaration order is 'blocked' (a0..a{m-1}, b0..b{m-1})
    or 'interleaved' (a0,b0,a1,b1,...)."""
    def a(i):
        return Var(2 * i if interleave else i)

    def b(i):
        return Var(2 * i + 1 if interleave else m + i)

    carry = And(a(0), b(0))
    for i in range(1, m):
        s = Xor(a(i), b(i))
        carry = Or(And(a(i), b(i)), And(s, carry))
    return carry


def bdd_packed_from_pick_iter(bdd, root, names):
    """Packed truth table (env row order: pos p of vars_key is bit n-1-p of the
    row index) from cube enumeration; O(#minterms) expansion."""
    n = len(names)
    pos = {name: i for i, name in enumerate(names)}
    bits = 0
    for cube in bdd.pick_iter(root, care_vars=names):
        fixed_row = 0
        free = []
        for name in names:
            if name in cube:
                if cube[name]:
                    fixed_row |= 1 << (n - 1 - pos[name])
            else:
                free.append(1 << (n - 1 - pos[name]))
        for mask_bits in range(1 << len(free)):
            row = fixed_row
            for j, fv in enumerate(free):
                if (mask_bits >> j) & 1:
                    row |= fv
            bits |= 1 << row
    return bits


def run_bdd():
    from dd import autoref

    out: dict = {}
    out["exact_max_robdd_nodes"] = {str(n): exact_max_robdd_nodes(n) for n in (8, 12, 16, 20)}

    # adder order sensitivity, analytic check
    adder = []
    for m in (8, 10):
        row = {"m": m}
        for label, interleave in (("blocked", False), ("interleaved", True)):
            bdd = autoref.BDD()
            names = [f"x{i}" for i in range(2 * m)]
            bdd.declare(*names)
            from cmbench.backends.robdd_dd import expr_to_dd_bdd, safe_bdd_node_count
            root = expr_to_dd_bdd(ripple_carry_out(m, interleave), bdd, {n: n for n in names})
            row[f"{label}_nodes"] = safe_bdd_node_count(bdd, root)
        row["analytic_blocked"] = 2 ** (m + 1) - 1
        row["analytic_interleaved"] = 3 * m
        adder.append(row)
    out["adder_order_sensitivity"] = adder

    # spot-reproduce Codex node counts + a reorder (sifting) arm at nb=8
    from cmbench.backends.robdd_dd import expr_to_dd_bdd, safe_bdd_node_count
    spot = []
    bits8 = multiplier_bits(8, "balanced")
    for bit in (7, 9, 10, 11):
        entry = {"nb": 8, "bit": bit}
        for order_name, order in (
                ("blocked", [f"x{i}" for i in range(16)]),
                ("interleaved", [f"x{i + o}" for i in range(8) for o in (0, 8)])):
            bdd = autoref.BDD()
            bdd.declare(*order)
            root = expr_to_dd_bdd(bits8[bit], bdd, {n: n for n in order})
            entry[f"{order_name}_nodes"] = safe_bdd_node_count(bdd, root)
            if order_name == "blocked":
                t0 = time.perf_counter()
                bdd.collect_garbage()
                autoref.reorder(bdd)
                entry["reorder_time_ms"] = (time.perf_counter() - t0) * 1e3
                entry["after_sifting_nodes"] = safe_bdd_node_count(bdd, root)
        spot.append(entry)
    out["mult8_spot_nodes"] = spot

    # task-matched pipelines
    pipelines = []
    for nb in (6, 8):
        n = 2 * nb
        names = [f"x{i + o}" for i in range(nb) for o in (0, nb)]  # interleaved
        support = tuple(f"x{i}" for i in range(n))
        seq = multiplier_bits(nb, "sequential")[nb]
        bal = multiplier_bits(nb, "balanced")[nb]

        # CM pipeline pieces
        t0 = time.perf_counter()
        node_seq = compile_expr_to_cm_ir(seq)
        node_bal = compile_expr_to_cm_ir(bal)
        cm_compile_ms = (time.perf_counter() - t0) * 1e3
        t0 = time.perf_counter()
        v_seq = eval_cm_node_words(node_seq, support, fixed={})
        v_bal = eval_cm_node_words(node_bal, support, fixed={})
        cm_eval_ms = (time.perf_counter() - t0) * 1e3
        cm_equal = v_seq == v_bal

        # BDD pipeline pieces (dd.autoref: pure-Python upper bound on build)
        bdd = autoref.BDD()
        bdd.declare(*names)
        t0 = time.perf_counter()
        r_seq = expr_to_dd_bdd(seq, bdd, {nm: nm for nm in names})
        bdd_build_seq_ms = (time.perf_counter() - t0) * 1e3
        t0 = time.perf_counter()
        r_bal = expr_to_dd_bdd(bal, bdd, {nm: nm for nm in names})
        bdd_build_bal_ms = (time.perf_counter() - t0) * 1e3
        t0 = time.perf_counter()
        bdd_equal = r_seq == r_bal
        bdd_equal_ms = (time.perf_counter() - t0) * 1e3

        # model count
        t0 = time.perf_counter()
        cm_count = v_seq.bit_count()
        cm_count_ms = (time.perf_counter() - t0) * 1e3
        t0 = time.perf_counter()
        bdd_count = int(bdd.count(r_seq, nvars=n))
        bdd_count_ms = (time.perf_counter() - t0) * 1e3

        # restriction batch: 32 random 4-var partial assignments -> model count
        rng = random.Random(7)
        fixed_names = [f"x{i}" for i in range(4)]
        rest_support = tuple(nm for nm in support if nm not in fixed_names)
        assignments = [{nm: rng.randint(0, 1) for nm in fixed_names} for _ in range(32)]
        t0 = time.perf_counter()
        cm_rest = [eval_cm_node_words(node_seq, rest_support, fixed=asg).bit_count()
                   for asg in assignments]
        cm_restrict_ms = (time.perf_counter() - t0) * 1e3
        t0 = time.perf_counter()
        bdd_rest = [int(bdd.count(bdd.let({k: bool(v) for k, v in asg.items()}, r_seq),
                                  nvars=n - 4)) for asg in assignments]
        bdd_restrict_ms = (time.perf_counter() - t0) * 1e3

        entry = {
            "nb": nb, "n_vars": n,
            "cm_compile_both_ms": cm_compile_ms,
            "cm_eval_both_ms": cm_eval_ms,
            "cm_equivalence_ok": cm_equal,
            "bdd_build_seq_ms": bdd_build_seq_ms,
            "bdd_build_bal_ms": bdd_build_bal_ms,
            "bdd_equivalence_ms": bdd_equal_ms,
            "bdd_equivalence_ok": bool(bdd_equal),
            "model_count_agree": cm_count == bdd_count,
            "cm_count_ms": cm_count_ms, "bdd_count_ms": bdd_count_ms,
            "restrict_agree": cm_rest == bdd_rest,
            "cm_restrict_batch32_ms": cm_restrict_ms,
            "bdd_restrict_batch32_ms": bdd_restrict_ms,
        }
        if nb == 6:
            # packed extraction from the BDD, checked bit-exact against CM.
            # NB: CM's packed row order is defined over sorted support
            # x0..x11, so extract against that order.
            t0 = time.perf_counter()
            packed = bdd_packed_from_pick_iter(bdd, r_seq, list(support))
            entry["bdd_to_packed_ms"] = (time.perf_counter() - t0) * 1e3
            entry["bdd_to_packed_equal"] = packed == v_seq
            entry["cm_packed_eval_ms"] = timed(
                lambda: eval_cm_node_words(node_seq, support, fixed={}), repeats=20) * 1e3
        pipelines.append(entry)
    out["pipelines"] = pipelines
    return out


# --------------------------------------------------------------------------
# section: defects
# --------------------------------------------------------------------------

def run_defects():
    out: dict = {}

    # (a) arm asymmetry in the 2026-08-01 CSE-vs-CM eval comparison:
    # eval_cm_node_words wrapper vs bare _eval_words on the same program.
    expr = multiplier_bits(8, "sequential")[8]
    support = expr_support(expr)
    node = compile_expr_to_cm_ir(expr)
    prog = get_flat_program(node)
    wrapper = timed(lambda: eval_cm_node_words(node, support, fixed={}), repeats=20) * 1e6
    bare = timed(lambda: _eval_words(prog, support, {}), repeats=20) * 1e6
    out["cm_arm_wrapper_vs_bare_us"] = {"eval_cm_node_words": wrapper, "_eval_words": bare,
                                        "overhead_us": wrapper - bare}

    # (b) identity-DAG overcount from fresh Var()/And() construction in the
    # Codex multiplier generator (their dag_nodes is identity-based).
    cases = []
    for topology in ("sequential", "balanced"):
        e = multiplier_bits(8, topology)[8]
        cases.append({"case": f"mult_{topology}_nb8_bit8",
                      "identity_dag_nodes": identity_dag_nodes(e),
                      "structural_dag_nodes": structural_dag_nodes(e)})
    out["identity_vs_structural_dag"] = cases

    # (c) wrapper-vs-kernel mixing in the published C1 arms, quantified on the
    # three controlled corpus formulas.
    corpus = [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines()]
    rows = []
    for item in corpus:
        if not item["family"].startswith("controlled_live"):
            continue
        if item["nominal_n"] != 20:
            continue
        expr_c = expr_from_json(item["expression"])
        support_c = tuple(item["semantic_support"])
        fixed_c = {f"x{i}": 0 for i in range(item["nominal_n"]) if f"x{i}" not in support_c}
        node_c = compile_expr_to_cm_ir(expr_c)

        def harness_arm():
            return materialize_hybrid_no_reinflate(
                node_c, support_c, fixed=fixed_c, hybrid_threshold=16,
                allow_reduced_output=False, max_full_output_vars=16,
                flat_eval=True, words_eval=True)

        kernel = timed(lambda: eval_cm_node_words(node_c, support_c, fixed=fixed_c),
                       repeats=100, blocks=5) * 1e6
        wrapperized = timed(harness_arm, repeats=100, blocks=5) * 1e6
        bs = timed(lambda: eval_expr_words_bitset(expr_c, support_c, fixed=fixed_c),
                   repeats=100, blocks=5) * 1e6
        rows.append({"id": item["id"], "live_k": item["semantic_live_k"],
                     "cm_kernel_us": kernel, "cm_harness_arm_us": wrapperized,
                     "bitset_arm_us": bs,
                     "wrapper_overhead_us": wrapperized - kernel,
                     "ratio_harness": wrapperized / bs,
                     "ratio_kernel": kernel / bs})
    out["wrapper_vs_kernel_controlled"] = rows
    return out


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

SECTIONS = {
    "cse_ladder": run_cse_ladder,
    "builder_memo": run_builder_memo,
    "dag_serde": run_dag_serde,
    "variance": run_variance,
    "repeat_platform": run_repeat_platform,
    "bdd": run_bdd,
    "defects": run_defects,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sections", default="all")
    args = parser.parse_args()
    wanted = list(SECTIONS) if args.sections == "all" else args.sections.split(",")

    if OUT.exists():
        results = json.loads(OUT.read_text(encoding="utf-8"))
    else:
        results = {}
    results.setdefault("_meta", {})["interpreter"] = sys.version
    results["_meta"]["numpy"] = np.__version__

    for name in wanted:
        fn = SECTIONS[name]
        print(f"[{time.strftime('%H:%M:%S')}] running {name} ...", flush=True)
        t0 = time.perf_counter()
        results[name] = fn()
        print(f"  done in {time.perf_counter() - t0:.1f}s", flush=True)
        OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
