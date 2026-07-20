from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from bitset_backend import bitset_to_bool_hypercube, eval_cm_node_bitset
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor


AXIS = np.array([False, True], dtype=bool)
ASSOCIATIVE_OPS = {"AND", "OR", "XOR"}
COMMUTATIVE_OPS = {"AND", "OR", "XOR", "EQV"}


def _bump(diag: Optional[Dict[str, int]], key: str, inc: int = 1) -> None:
    if diag is None:
        return
    diag[key] = int(diag.get(key, 0)) + inc


def _add_float(diag: Optional[Dict[str, Any]], key: str, inc: float) -> None:
    if diag is None:
        return
    cur = diag.get(key, 0.0)
    try:
        base = float(cur)
    except Exception:
        base = 0.0
    diag[key] = base + float(inc)


def _ir_timing_enabled(diag: Optional[Dict[str, Any]]) -> bool:
    try:
        return bool(diag is not None and int(diag.get("ir_timing_enabled", 0)) == 1)
    except Exception:
        return False


def _init_ir_compile_diagnostics(diag: Optional[Dict[str, Any]]) -> None:
    if diag is None:
        return
    diag.setdefault("ir_compile_time_s", 0.0)
    diag.setdefault("ir_compile_cache_hit", 0)
    diag.setdefault("ir_compile_cache_hits", 0)
    diag.setdefault("ir_compile_cache_misses", 0)


def _init_ir_persistent_cache_diagnostics(diag: Optional[Dict[str, Any]]) -> None:
    if diag is None:
        return
    diag.setdefault("ir_persistent_cache_hits", 0)
    diag.setdefault("ir_persistent_cache_misses", 0)
    diag.setdefault("ir_persistent_cache_size", 0)


_COMPILED_IR_CACHE_MAXSIZE = 4096
_COMPILED_IR_CACHE: "OrderedDict[Expr, CMNode]" = OrderedDict()


def clear_cm_ir_compile_cache() -> None:
    _COMPILED_IR_CACHE.clear()


_PERSISTENT_IR_CACHE_MAXSIZE = 16384
_PERSISTENT_IR_CACHE: "OrderedDict[str, CMNode]" = OrderedDict()


def clear_cm_ir_persistent_cache() -> None:
    _PERSISTENT_IR_CACHE.clear()


def cm_ir_persistent_cache_stats() -> Dict[str, int]:
    return {"ir_persistent_cache_size": int(len(_PERSISTENT_IR_CACHE))}


def _expr_var_name(expr: Any) -> str:
    name = getattr(expr, "name", None)
    if isinstance(name, str):
        return name
    i = getattr(expr, "i", None)
    if isinstance(i, int):
        return f"x{i}"
    try:
        return f"x{int(i)}"
    except Exception:
        return str(i)


def _structural_digest(e: Expr, memo: Dict[int, bytes]) -> bytes:
    """blake2b structural digest for one Expr node, memoized by ``id(e)``.

    ``memo`` must keep every hashed Expr alive for its lifetime (callers pass a dict
    scoped to a single hash/compile call, during which the Expr tree is referenced).
    """
    cached = memo.get(id(e))
    if cached is not None:
        return cached
    h = hashlib.blake2b(digest_size=16)
    if isinstance(e, Var):
        h.update(b"VAR:")
        h.update(_expr_var_name(e).encode("utf-8"))
        d = h.digest()
    elif isinstance(e, Not):
        h.update(b"NOT:")
        h.update(_structural_digest(e.a, memo))
        d = h.digest()
    elif isinstance(e, (And, Or, Xor)):
        if isinstance(e, And):
            tag = b"AND:"
            cls = And
        elif isinstance(e, Or):
            tag = b"OR:"
            cls = Or
        else:
            tag = b"XOR:"
            cls = Xor

        # Flatten associative ops, then sort child digests for commutativity.
        stack: List[Expr] = [e]
        parts: List[bytes] = []
        while stack:
            z = stack.pop()
            if isinstance(z, cls):
                stack.append(z.b)
                stack.append(z.a)
            else:
                parts.append(_structural_digest(z, memo))
        parts.sort()
        h.update(tag)
        for p in parts:
            h.update(p)
        d = h.digest()
    elif isinstance(e, Eqv):
        a = _structural_digest(e.a, memo)
        b = _structural_digest(e.b, memo)
        if b < a:
            a, b = b, a
        h.update(b"EQV:")
        h.update(a)
        h.update(b)
        d = h.digest()
    elif isinstance(e, Imp):
        h.update(b"IMP:")
        h.update(_structural_digest(e.a, memo))
        h.update(_structural_digest(e.b, memo))
        d = h.digest()
    else:
        raise TypeError(e)
    memo[id(e)] = d
    return d


def expr_structural_hash(expr: Expr) -> str:
    """Deterministic structural hash for Expr, independent of object identity.

    This hash canonicalizes associative+commutative nodes (AND/OR/XOR) by flattening and sorting
    child hashes, and canonicalizes EQV by sorting its two children. IMP preserves order.
    """
    return _structural_digest(expr, {}).hex()


def compile_expr_to_cm_ir_persistent(
    expr: Expr,
    diagnostics: Optional[Dict[str, Any]] = None,
    *,
    reuse_cache: bool = False,
) -> CMNode:
    """Compile Expr -> CM IR with persistent structural-hash caching for subtrees."""
    _init_ir_compile_diagnostics(diagnostics)
    _init_ir_persistent_cache_diagnostics(diagnostics)

    def cache_get(key: str) -> Optional[CMNode]:
        cached = _PERSISTENT_IR_CACHE.get(key)
        if cached is None:
            _bump(diagnostics, "ir_persistent_cache_misses")
            return None
        _PERSISTENT_IR_CACHE.move_to_end(key)
        _bump(diagnostics, "ir_persistent_cache_hits")
        return cached

    def cache_put(key: str, node: CMNode) -> CMNode:
        _PERSISTENT_IR_CACHE[key] = node
        _PERSISTENT_IR_CACHE.move_to_end(key)
        if len(_PERSISTENT_IR_CACHE) > _PERSISTENT_IR_CACHE_MAXSIZE:
            _PERSISTENT_IR_CACHE.popitem(last=False)
        return node

    builder = CMIRBuilder(diagnostics)
    # One digest memo shared across the whole compile: each subtree is hashed once
    # (bottom-up) instead of re-walked by every enclosing expr_structural_hash call.
    # Digest values are unchanged, so persistent-cache keys are unaffected.
    digest_memo: Dict[int, bytes] = {}

    def build(e: Expr) -> CMNode:
        key = _structural_digest(e, digest_memo).hex()
        cached = cache_get(key)
        if cached is not None:
            return cached
        if isinstance(e, Var):
            name = getattr(e, "name", None)
            node = builder.var(name if isinstance(name, str) else f"x{int(e.i)}")
        elif isinstance(e, Not):
            node = builder.negate(build(e.a))
        elif isinstance(e, And):
            node = builder.make_and((build(e.a), build(e.b)))
        elif isinstance(e, Or):
            node = builder.make_or((build(e.a), build(e.b)))
        elif isinstance(e, Xor):
            node = builder.make_xor((build(e.a), build(e.b)))
        elif isinstance(e, Imp):
            node = builder.make_imp(build(e.a), build(e.b))
        elif isinstance(e, Eqv):
            node = builder.make_eqv(build(e.a), build(e.b))
        else:
            raise TypeError(e)
        return cache_put(key, node)

    if _ir_timing_enabled(diagnostics):
        t0 = time.perf_counter()
        node = build(expr)
        _add_float(diagnostics, "ir_compile_time_s", time.perf_counter() - t0)
    else:
        node = build(expr)
    if diagnostics is not None:
        diagnostics["ir_persistent_cache_size"] = int(len(_PERSISTENT_IR_CACHE))
    return node


def compile_expr_cached(expr: Expr, diagnostics: Optional[Dict[str, Any]] = None, *, reuse_cache: bool = False) -> CMNode:
    return compile_expr_to_cm_ir_persistent(expr, diagnostics=diagnostics, reuse_cache=reuse_cache)


def _init_final_output_diagnostics(diag: Optional[Dict[str, Any]]) -> None:
    if diag is None:
        return
    diag.setdefault("final_cm_materialization_performed", 0)
    diag.setdefault("final_cm_materialization_time_s", 0.0)
    diag.setdefault("final_truth_table_materialization_time_s", 0.0)
    diag.setdefault("final_bitset_returned", 0)
    diag.setdefault("final_output_elements", 0)
    diag.setdefault("final_output_nominal_elements", 0)
    diag.setdefault("final_output_vars_count", 0)
    diag.setdefault("final_output_reduced", 0)
    diag.setdefault("large_n_output_guard_triggered", 0)
    diag.setdefault("final_output_representation_code", -1)


def _record_final_output_diagnostics(
    diag: Optional[Dict[str, Any]],
    *,
    final_cm_materialization_performed: int,
    final_cm_materialization_time_s: float,
    final_truth_table_materialization_time_s: float,
    final_bitset_returned: int,
    final_output_elements: int,
    final_output_representation_code: int,
    final_output_nominal_elements: Optional[int] = None,
    final_output_vars_count: Optional[int] = None,
    final_output_reduced: int = 0,
    large_n_output_guard_triggered: int = 0,
) -> None:
    if diag is None:
        return
    diag["final_cm_materialization_performed"] = int(final_cm_materialization_performed)
    diag["final_cm_materialization_time_s"] = float(final_cm_materialization_time_s)
    diag["final_truth_table_materialization_time_s"] = float(final_truth_table_materialization_time_s)
    diag["final_bitset_returned"] = int(final_bitset_returned)
    diag["final_output_elements"] = int(final_output_elements)
    diag["final_output_nominal_elements"] = int(
        final_output_elements if final_output_nominal_elements is None else final_output_nominal_elements
    )
    diag["final_output_vars_count"] = int(
        0 if final_output_vars_count is None else final_output_vars_count
    )
    diag["final_output_reduced"] = int(final_output_reduced)
    diag["large_n_output_guard_triggered"] = int(large_n_output_guard_triggered)
    diag["final_output_representation_code"] = int(final_output_representation_code)


def _var_sort_key(name: str) -> Tuple[int, object]:
    if name.startswith("x") and name[1:].isdigit():
        return (0, int(name[1:]))
    if name.startswith("__pad") and name.endswith("__"):
        inner = name[5:-2]
        if inner.isdigit():
            return (2, int(inner))
    return (1, name)


def _sorted_unique_vars(names: Iterable[str]) -> Tuple[str, ...]:
    return tuple(sorted(set(names), key=_var_sort_key))


def _iter_expr_vars(expr: Expr) -> Iterable[str]:
    if isinstance(expr, Var):
        name = getattr(expr, "name", None)
        if isinstance(name, str):
            yield name
        else:
            yield f"x{int(expr.i)}"
        return
    if isinstance(expr, Not):
        yield from _iter_expr_vars(expr.a)
        return
    if isinstance(expr, (And, Or, Xor, Imp, Eqv)):
        yield from _iter_expr_vars(expr.a)
        yield from _iter_expr_vars(expr.b)
        return
    raise TypeError(expr)


@dataclass(frozen=True)
class CMNode:
    kind: str
    key: Tuple[object, ...]
    vars: Tuple[str, ...]
    const_value: Optional[int]
    op: str = ""
    args: Tuple["CMNode", ...] = ()
    var_name: str = ""

    def __hash__(self) -> int:
        # Same value the dataclass-generated __hash__ would produce, but computed once:
        # ``key``/``args`` are deep structural tuples, so the generated hash is O(subtree)
        # on every memo/set lookup. Cached lazily; __eq__ stays field-wise structural.
        h = self.__dict__.get("_cached_hash")
        if h is None:
            h = hash((self.kind, self.key, self.vars, self.const_value, self.op, self.args, self.var_name))
            object.__setattr__(self, "_cached_hash", h)
        return h


class CMIRBuilder:
    def __init__(self, diagnostics: Optional[Dict[str, int]] = None):
        self.diagnostics = diagnostics
        self._interned: Dict[Tuple[object, ...], CMNode] = {}

    def _maybe_time(self, *, calls_key: str, time_key: str) -> Optional[float]:
        if not _ir_timing_enabled(self.diagnostics):
            return None
        _bump(self.diagnostics, calls_key)
        return time.perf_counter()

    def _maybe_add_elapsed(self, t0: Optional[float], *, time_key: str) -> None:
        if t0 is None or self.diagnostics is None:
            return
        _add_float(self.diagnostics, time_key, time.perf_counter() - t0)

    def _intern(
        self,
        *,
        kind: str,
        key: Tuple[object, ...],
        vars: Tuple[str, ...],
        const_value: Optional[int],
        op: str = "",
        args: Tuple[CMNode, ...] = (),
        var_name: str = "",
    ) -> CMNode:
        t0 = None
        if _ir_timing_enabled(self.diagnostics):
            _bump(self.diagnostics, "ir_intern_calls")
            t0 = time.perf_counter()
        cached = self._interned.get(key)
        if cached is not None:
            _bump(self.diagnostics, "subtree_cache_hits")
            if t0 is not None:
                _add_float(self.diagnostics, "ir_intern_time_s", time.perf_counter() - t0)
            return cached
        _bump(self.diagnostics, "subtree_cache_misses")
        node = CMNode(
            kind=kind,
            key=key,
            vars=vars,
            const_value=const_value,
            op=op,
            args=args,
            var_name=var_name,
        )
        self._interned[key] = node
        if t0 is not None:
            _add_float(self.diagnostics, "ir_intern_time_s", time.perf_counter() - t0)
        return node

    def const(self, value: int) -> CMNode:
        val = int(bool(value))
        return self._intern(kind="const", key=("CONST", val), vars=tuple(), const_value=val)

    def var(self, name: str) -> CMNode:
        return self._intern(
            kind="var",
            key=("VAR", name),
            vars=(name,),
            const_value=None,
            var_name=name,
        )

    def negate(self, node: CMNode) -> CMNode:
        # Keep rewrite timing non-overlapping with interning/live-vars/canonicalization timers.
        t0 = None
        if _ir_timing_enabled(self.diagnostics):
            _bump(self.diagnostics, "ir_rewrite_calls")
            t0 = time.perf_counter()

        if node.const_value is not None:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            if t0 is not None:
                _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
            return self.const(1 - node.const_value)
        if node.kind == "not":
            _bump(self.diagnostics, "canonical_rewrites")
            if t0 is not None:
                _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
            return node.args[0]

        if t0 is not None:
            _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
        return self._intern(
            kind="not",
            key=("NOT", node.key),
            vars=node.vars,
            const_value=None,
            op="NOT",
            args=(node,),
        )

    def _live_vars_union(self, nodes: Sequence[CMNode]) -> Tuple[str, ...]:
        t0 = None
        if _ir_timing_enabled(self.diagnostics):
            _bump(self.diagnostics, "ir_live_vars_calls")
            _bump(self.diagnostics, "ir_live_vars_total_inputs", sum(len(n.vars) for n in nodes))
            t0 = time.perf_counter()
        out = _sorted_unique_vars(v for node in nodes for v in node.vars)
        if t0 is not None:
            _add_float(self.diagnostics, "ir_live_vars_time_s", time.perf_counter() - t0)
        return out

    def _live_vars_pair(self, left: CMNode, right: CMNode) -> Tuple[str, ...]:
        return self._live_vars_union((left, right))

    def _live_vars_single(self, node: CMNode) -> Tuple[str, ...]:
        return self._live_vars_union((node,))

    def _canonicalize_commutative_args(self, op: str, args: Sequence[CMNode]) -> Tuple[CMNode, ...]:
        t0 = self._maybe_time(calls_key="ir_canonicalize_calls", time_key="ir_canonicalize_time_s")
        try:
            out: List[CMNode] = []
            changed = False
            for node in args:
                if node.kind == "binary" and node.op == op and op in ASSOCIATIVE_OPS:
                    out.extend(node.args)
                    changed = True
                else:
                    out.append(node)
            sorted_out = sorted(out, key=lambda node: node.key)
            if changed or tuple(sorted_out) != tuple(args):
                _bump(self.diagnostics, "canonical_rewrites")
            return tuple(sorted_out)
        finally:
            self._maybe_add_elapsed(t0, time_key="ir_canonicalize_time_s")

    @staticmethod
    def _is_negation_of(a: CMNode, b: CMNode) -> bool:
        return (a.kind == "not" and a.args[0] == b) or (b.kind == "not" and b.args[0] == a)

    def make_and(self, args: Sequence[CMNode]) -> CMNode:
        if _ir_timing_enabled(self.diagnostics):
            _bump(self.diagnostics, "ir_rewrite_calls")
        ordered = self._canonicalize_commutative_args("AND", args)

        t0 = time.perf_counter() if _ir_timing_enabled(self.diagnostics) else None
        out: List[CMNode] = []
        seen = set()
        for node in ordered:
            if node.const_value == 0:
                _bump(self.diagnostics, "canonical_rewrites")
                _bump(self.diagnostics, "pruned_branches")
                if t0 is not None:
                    _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
                return self.const(0)
            if node.const_value == 1:
                _bump(self.diagnostics, "canonical_rewrites")
                _bump(self.diagnostics, "pruned_branches")
                continue
            if node in seen:
                _bump(self.diagnostics, "canonical_rewrites")
                continue
            if any(self._is_negation_of(node, prev) for prev in out):
                _bump(self.diagnostics, "canonical_rewrites")
                _bump(self.diagnostics, "pruned_branches")
                if t0 is not None:
                    _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
                return self.const(0)
            out.append(node)
            seen.add(node)

        if t0 is not None:
            _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)

        if not out:
            return self.const(1)
        if len(out) == 1:
            _bump(self.diagnostics, "canonical_rewrites")
            return out[0]
        live_vars = self._live_vars_union(tuple(out))
        key = ("AND",) + tuple(node.key for node in out)
        return self._intern(
            kind="binary",
            key=key,
            vars=live_vars,
            const_value=None,
            op="AND",
            args=tuple(out),
        )

    def make_or(self, args: Sequence[CMNode]) -> CMNode:
        if _ir_timing_enabled(self.diagnostics):
            _bump(self.diagnostics, "ir_rewrite_calls")
        ordered = self._canonicalize_commutative_args("OR", args)

        t0 = time.perf_counter() if _ir_timing_enabled(self.diagnostics) else None
        out: List[CMNode] = []
        seen = set()
        for node in ordered:
            if node.const_value == 1:
                _bump(self.diagnostics, "canonical_rewrites")
                _bump(self.diagnostics, "pruned_branches")
                if t0 is not None:
                    _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
                return self.const(1)
            if node.const_value == 0:
                _bump(self.diagnostics, "canonical_rewrites")
                _bump(self.diagnostics, "pruned_branches")
                continue
            if node in seen:
                _bump(self.diagnostics, "canonical_rewrites")
                continue
            if any(self._is_negation_of(node, prev) for prev in out):
                _bump(self.diagnostics, "canonical_rewrites")
                _bump(self.diagnostics, "pruned_branches")
                if t0 is not None:
                    _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
                return self.const(1)
            out.append(node)
            seen.add(node)

        if t0 is not None:
            _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)

        if not out:
            return self.const(0)
        if len(out) == 1:
            _bump(self.diagnostics, "canonical_rewrites")
            return out[0]
        live_vars = self._live_vars_union(tuple(out))
        key = ("OR",) + tuple(node.key for node in out)
        return self._intern(
            kind="binary",
            key=key,
            vars=live_vars,
            const_value=None,
            op="OR",
            args=tuple(out),
        )

    def make_xor(self, args: Sequence[CMNode]) -> CMNode:
        if _ir_timing_enabled(self.diagnostics):
            _bump(self.diagnostics, "ir_rewrite_calls")
        ordered = self._canonicalize_commutative_args("XOR", args)

        t0 = time.perf_counter() if _ir_timing_enabled(self.diagnostics) else None
        counts: Dict[CMNode, int] = {}
        parity = 0
        for node in ordered:
            if node.const_value is not None:
                parity ^= int(node.const_value)
                _bump(self.diagnostics, "canonical_rewrites")
                _bump(self.diagnostics, "pruned_branches")
                continue
            counts[node] = counts.get(node, 0) + 1

        out = [node for node in sorted(counts, key=lambda n: n.key) if (counts[node] % 2) == 1]
        if len(out) != len(counts) or any(v > 1 for v in counts.values()):
            _bump(self.diagnostics, "canonical_rewrites")

        if t0 is not None:
            _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)

        if not out:
            return self.const(parity)
        if len(out) == 1:
            if parity == 0:
                _bump(self.diagnostics, "canonical_rewrites")
                return out[0]
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return self.negate(out[0])

        live_vars = self._live_vars_union(tuple(out))
        base = self._intern(
            kind="binary",
            key=("XOR",) + tuple(node.key for node in out),
            vars=live_vars,
            const_value=None,
            op="XOR",
            args=tuple(out),
        )
        if parity == 1:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return self.negate(base)
        return base

    def make_eqv(self, left: CMNode, right: CMNode) -> CMNode:
        t0 = None
        if _ir_timing_enabled(self.diagnostics):
            _bump(self.diagnostics, "ir_rewrite_calls")
            t0 = time.perf_counter()

        if left == right:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            if t0 is not None:
                _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
            return self.const(1)
        if self._is_negation_of(left, right):
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            if t0 is not None:
                _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
            return self.const(0)
        if left.const_value == 1:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            if t0 is not None:
                _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
            return right
        if right.const_value == 1:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            if t0 is not None:
                _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
            return left
        if left.const_value == 0:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            if t0 is not None:
                _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
            return self.negate(right)
        if right.const_value == 0:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            if t0 is not None:
                _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
            return self.negate(left)
        ordered = tuple(sorted((left, right), key=lambda node: node.key))
        if ordered != (left, right):
            _bump(self.diagnostics, "canonical_rewrites")

        if t0 is not None:
            _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)

        live_vars = self._live_vars_union(ordered)
        key = ("EQV", ordered[0].key, ordered[1].key)
        return self._intern(
            kind="binary",
            key=key,
            vars=live_vars,
            const_value=None,
            op="EQV",
            args=ordered,
        )

    def make_imp(self, left: CMNode, right: CMNode) -> CMNode:
        t0 = None
        if _ir_timing_enabled(self.diagnostics):
            _bump(self.diagnostics, "ir_rewrite_calls")
            t0 = time.perf_counter()

        if left == right:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            if t0 is not None:
                _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
            return self.const(1)
        if left.const_value == 0 or right.const_value == 1:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            if t0 is not None:
                _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
            return self.const(1)
        if left.const_value == 1:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            if t0 is not None:
                _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
            return right
        if right.const_value == 0:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            if t0 is not None:
                _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
            return self.negate(left)

        if t0 is not None:
            _add_float(self.diagnostics, "ir_rewrite_time_s", time.perf_counter() - t0)
        live_vars = self._live_vars_pair(left, right)
        key = ("IMP", left.key, right.key)
        return self._intern(
            kind="binary",
            key=key,
            vars=live_vars,
            const_value=None,
            op="IMP",
            args=(left, right),
        )

    def build(self, expr: Expr) -> CMNode:
        if isinstance(expr, Var):
            name = getattr(expr, "name", None)
            if isinstance(name, str):
                return self.var(name)
            return self.var(f"x{int(expr.i)}")
        if isinstance(expr, Not):
            return self.negate(self.build(expr.a))
        if isinstance(expr, And):
            return self.make_and((self.build(expr.a), self.build(expr.b)))
        if isinstance(expr, Or):
            return self.make_or((self.build(expr.a), self.build(expr.b)))
        if isinstance(expr, Xor):
            return self.make_xor((self.build(expr.a), self.build(expr.b)))
        if isinstance(expr, Imp):
            return self.make_imp(self.build(expr.a), self.build(expr.b))
        if isinstance(expr, Eqv):
            return self.make_eqv(self.build(expr.a), self.build(expr.b))
        raise TypeError(expr)


def compile_expr_to_cm_ir(
    expr: Expr,
    diagnostics: Optional[Dict[str, Any]] = None,
    *,
    reuse_cache: bool = False,
    persistent_cache: bool = False,
) -> CMNode:
    """Compile a boolean expression AST into a canonicalized, interned CM IR DAG.

    If ``reuse_cache=True``, the compiled IR may be reused across calls for identical immutable
    Expr objects. This is an explicit opt-in behavior to preserve benchmark semantics.

    If ``persistent_cache=True``, a process-level persistent cache keyed by structural hash is used.
    """
    if persistent_cache:
        return compile_expr_to_cm_ir_persistent(expr, diagnostics=diagnostics, reuse_cache=reuse_cache)
    return compile_expr_to_cm_ir_cached(expr, diagnostics=diagnostics, reuse_cache=reuse_cache)


def compile_expr_to_cm_ir_cached(
    expr: Expr,
    diagnostics: Optional[Dict[str, Any]] = None,
    *,
    reuse_cache: bool = False,
) -> CMNode:
    _init_ir_compile_diagnostics(diagnostics)
    if reuse_cache:
        if diagnostics is not None:
            diagnostics["ir_compile_cache_hit"] = 0
        cached = _COMPILED_IR_CACHE.get(expr)
        if cached is not None:
            if diagnostics is not None:
                _bump(diagnostics, "ir_compile_cache_hits")
                diagnostics["ir_compile_cache_hit"] = 1
            _COMPILED_IR_CACHE.move_to_end(expr)
            return cached
        if diagnostics is not None:
            _bump(diagnostics, "ir_compile_cache_misses")
            diagnostics["ir_compile_cache_hit"] = 0

    if _ir_timing_enabled(diagnostics):
        t0 = time.perf_counter()
        builder = CMIRBuilder(diagnostics)
        node = builder.build(expr)
        _add_float(diagnostics, "ir_compile_time_s", time.perf_counter() - t0)
    else:
        builder = CMIRBuilder(diagnostics)
        node = builder.build(expr)

    if reuse_cache:
        _COMPILED_IR_CACHE[expr] = node
        _COMPILED_IR_CACHE.move_to_end(expr)
        if len(_COMPILED_IR_CACHE) > _COMPILED_IR_CACHE_MAXSIZE:
            _COMPILED_IR_CACHE.popitem(last=False)
    return node


@dataclass(frozen=True)
class CompiledExpr:
    """Reusable compiled expression container.

    This object is safe to reuse across calls to `evaluate_compiled(...)` without recompilation.
    """

    expr_hash: str
    node: "CMNode"


def compile_expr(
    expr: Expr,
    diagnostics: Optional[Dict[str, Any]] = None,
    *,
    use_persistent_cache: bool = False,
    reuse_cache: bool = False,
) -> CompiledExpr:
    """Public reusable API: compile an Expr into CM IR (optionally using persistent caching)."""
    h = expr_structural_hash(expr)
    node = compile_expr_to_cm_ir(
        expr,
        diagnostics=diagnostics,
        reuse_cache=reuse_cache,
        persistent_cache=use_persistent_cache,
    )
    return CompiledExpr(expr_hash=h, node=node)


def evaluate_compiled(
    compiled: CompiledExpr,
    *,
    mode: str = "hybrid_no_reinflate",
    vars_all: Optional[Sequence[str]] = None,
    fixed: Optional[Dict[str, int]] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    hybrid_threshold: int = 7,
):
    """Public reusable API: evaluate a compiled expression in a chosen mode.

    Currently supports:
      - mode="hybrid_no_reinflate": returns `FinalNoReinflateResult`
    """
    if mode != "hybrid_no_reinflate":
        raise ValueError(f"unsupported mode: {mode!r}")
    vars_seq: Sequence[str] = vars_all if vars_all is not None else tuple(compiled.node.vars)
    return materialize_hybrid_no_reinflate(
        compiled.node,
        vars_seq,
        fixed=fixed,
        diagnostics=diagnostics,
        hybrid_threshold=hybrid_threshold,
    )


@lru_cache(maxsize=4096)
def _alignment_plan(source_vars: Tuple[str, ...], target_vars: Tuple[str, ...]) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    pos = {v: i for i, v in enumerate(source_vars)}
    transpose_axes = tuple(pos[v] for v in target_vars if v in pos)
    insert_positions = tuple(i for i, v in enumerate(target_vars) if v not in pos)
    return transpose_axes, insert_positions


def cm_ir_alignment_cache_stats() -> Dict[str, int]:
    info = _alignment_plan.cache_info()
    return {
        "align_plan_hits": int(info.hits),
        "align_plan_misses": int(info.misses),
        "align_plan_currsize": int(info.currsize),
    }


def clear_cm_ir_alignment_cache() -> None:
    _alignment_plan.cache_clear()


def align_to_vars(arr: np.ndarray, source_vars: Tuple[str, ...], target_vars: Tuple[str, ...]) -> np.ndarray:
    out = arr
    transpose_axes, insert_positions = _alignment_plan(source_vars, target_vars)
    if transpose_axes and transpose_axes != tuple(range(len(transpose_axes))):
        out = np.transpose(out, axes=transpose_axes)
    if insert_positions:
        if (not transpose_axes or transpose_axes == tuple(range(len(transpose_axes)))) and out.flags.c_contiguous:
            src_i = 0
            ins_i = 0
            new_shape: List[int] = []
            for axis in range(len(target_vars)):
                if ins_i < len(insert_positions) and insert_positions[ins_i] == axis:
                    new_shape.append(1)
                    ins_i += 1
                else:
                    new_shape.append(int(out.shape[src_i]) if src_i < out.ndim else 1)
                    src_i += 1
            if src_i == out.ndim:
                out = out.reshape(tuple(new_shape))
            else:
                for axis in insert_positions:
                    out = np.expand_dims(out, axis=axis)
        else:
            for axis in insert_positions:
                out = np.expand_dims(out, axis=axis)
    return out


def align_to_vars_with_stats(
    arr: np.ndarray, source_vars: Tuple[str, ...], target_vars: Tuple[str, ...]
) -> Tuple[np.ndarray, bool, int]:
    out = arr
    transpose_axes, insert_positions = _alignment_plan(source_vars, target_vars)
    did_transpose = False
    if transpose_axes and transpose_axes != tuple(range(len(transpose_axes))):
        out = np.transpose(out, axes=transpose_axes)
        did_transpose = True
    if insert_positions:
        if (not did_transpose) and out.flags.c_contiguous:
            src_i = 0
            ins_i = 0
            new_shape: List[int] = []
            for axis in range(len(target_vars)):
                if ins_i < len(insert_positions) and insert_positions[ins_i] == axis:
                    new_shape.append(1)
                    ins_i += 1
                else:
                    new_shape.append(int(out.shape[src_i]) if src_i < out.ndim else 1)
                    src_i += 1
            if src_i == out.ndim:
                out = out.reshape(tuple(new_shape))
            else:
                for axis in insert_positions:
                    out = np.expand_dims(out, axis=axis)
        else:
            for axis in insert_positions:
                out = np.expand_dims(out, axis=axis)
    return out, did_transpose, len(insert_positions)


def _serial_combine(left: np.ndarray, right: np.ndarray, op: str, diagnostics: Optional[Dict[str, Any]]) -> np.ndarray:
    _ = diagnostics
    if op == "AND":
        return left & right
    if op == "OR":
        return left | right
    if op == "XOR":
        return left ^ right
    if op == "IMP":
        return (~left) | right
    if op == "EQV":
        return ~(left ^ right)
    raise ValueError(op)


def _fixed_key_for_node(node: CMNode, fixed: Dict[str, int]) -> Tuple[Tuple[str, int], ...]:
    if not fixed or not node.vars:
        return tuple()
    return tuple((v, int(fixed[v])) for v in node.vars if v in fixed)


def materialize_ir(
    node: CMNode,
    *,
    fixed: Optional[Dict[str, int]] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    combine_fn: Optional[Callable[[np.ndarray, np.ndarray, str, Optional[Dict[str, Any]]], np.ndarray]] = None,
    materialize_mode: str = "partial_hybrid",
    hybrid_threshold: int = 7,
) -> Tuple[np.ndarray, Tuple[str, ...], Optional[int]]:
    res = _materialize_ir_tagged(
        node,
        fixed=fixed,
        diagnostics=diagnostics,
        combine_fn=combine_fn,
        materialize_mode=materialize_mode,
        hybrid_threshold=hybrid_threshold,
    )
    return res.arr, res.vars, res.const_value


@dataclass(frozen=True)
class _MatRes:
    arr: np.ndarray
    vars: Tuple[str, ...]
    const_value: Optional[int]
    backend: str
    boundary_source: bool = False


def _materialize_ir_tagged(
    node: CMNode,
    *,
    fixed: Optional[Dict[str, int]] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    combine_fn: Optional[Callable[[np.ndarray, np.ndarray, str, Optional[Dict[str, Any]]], np.ndarray]] = None,
    materialize_mode: str = "partial_hybrid",
    hybrid_threshold: int = 7,
) -> _MatRes:
    fixed_map = fixed or {}
    combine = combine_fn or _serial_combine
    memo: Dict[Tuple[CMNode, Tuple[Tuple[str, int], ...], bool], _MatRes] = {}

    if materialize_mode not in {"hybrid", "partial_hybrid", "numpy"}:
        raise ValueError(f"Unknown materialize_mode: {materialize_mode}")
    if hybrid_threshold < 0:
        raise ValueError("hybrid_threshold must be >= 0")
    if diagnostics is not None:
        diagnostics.setdefault("hybrid_depth_max", 0)
        diagnostics.setdefault("full_collapse_occurred", 0)
        diagnostics.setdefault("boundary_bitset_eval_time_s", 0.0)
        diagnostics.setdefault("boundary_bitset_to_hypercube_time_s", 0.0)
        diagnostics.setdefault("boundary_align_time_s", 0.0)
        diagnostics.setdefault("boundary_dispatch_time_s", 0.0)
        diagnostics.setdefault("boundary_bitset_eval_calls", 0)
        diagnostics.setdefault("boundary_bitset_to_hypercube_calls", 0)
        diagnostics.setdefault("boundary_elements_converted", 0)
        diagnostics.setdefault("boundary_align_calls", 0)
        diagnostics.setdefault("boundary_align_transpose_calls", 0)
        diagnostics.setdefault("boundary_align_insert_axes_total", 0)
        diagnostics.setdefault("boundary_bitset_const_fastpath_calls", 0)

    def materialize_bitset(cur: CMNode, live_vars: Tuple[str, ...], live_k: int) -> _MatRes:
        t_dispatch0 = time.perf_counter()
        _bump(diagnostics, "boundary_bitset_eval_calls")
        t_eval0 = time.perf_counter()
        bits = eval_cm_node_bitset(cur, live_vars, fixed=fixed_map)
        t_eval1 = time.perf_counter()
        _add_float(diagnostics, "boundary_bitset_eval_time_s", t_eval1 - t_eval0)
        if live_k == 0:
            const_value = int(bool(bits & 1))
            _bump(diagnostics, "boundary_bitset_const_fastpath_calls")
            t_dispatch1 = time.perf_counter()
            _add_float(diagnostics, "boundary_dispatch_time_s", (t_dispatch1 - t_dispatch0) - (t_eval1 - t_eval0))
            return _MatRes(
                arr=np.array(bool(const_value), dtype=bool),
                vars=tuple(),
                const_value=const_value,
                backend="bitset",
                boundary_source=False,
            )

        full_mask = (1 << (1 << live_k)) - 1
        if bits == 0:
            _bump(diagnostics, "boundary_bitset_const_fastpath_calls")
            t_dispatch1 = time.perf_counter()
            _add_float(diagnostics, "boundary_dispatch_time_s", (t_dispatch1 - t_dispatch0) - (t_eval1 - t_eval0))
            return _MatRes(
                arr=np.array(False, dtype=bool),
                vars=tuple(),
                const_value=0,
                backend="bitset",
                boundary_source=False,
            )
        if bits == full_mask:
            _bump(diagnostics, "boundary_bitset_const_fastpath_calls")
            t_dispatch1 = time.perf_counter()
            _add_float(diagnostics, "boundary_dispatch_time_s", (t_dispatch1 - t_dispatch0) - (t_eval1 - t_eval0))
            return _MatRes(
                arr=np.array(True, dtype=bool),
                vars=tuple(),
                const_value=1,
                backend="bitset",
                boundary_source=False,
            )

        _bump(diagnostics, "boundary_bitset_to_hypercube_calls")
        _bump(diagnostics, "boundary_elements_converted", 1 << live_k)
        t_conv0 = time.perf_counter()
        arr = bitset_to_bool_hypercube(bits, live_k)
        t_conv1 = time.perf_counter()
        _add_float(diagnostics, "boundary_bitset_to_hypercube_time_s", t_conv1 - t_conv0)

        t_dispatch1 = time.perf_counter()
        _add_float(
            diagnostics,
            "boundary_dispatch_time_s",
            (t_dispatch1 - t_dispatch0) - (t_eval1 - t_eval0) - (t_conv1 - t_conv0),
        )
        return _MatRes(
            arr=arr,
            vars=live_vars,
            const_value=None,
            backend="bitset",
            boundary_source=True,
        )

    def finalize(
        cur: CMNode,
        key: Tuple[CMNode, Tuple[Tuple[str, int], ...], bool],
        out: _MatRes,
        *,
        backend: str,
        live_k: int,
        depth: int,
        full_collapse: bool = False,
    ) -> _MatRes:
        memo[key] = out
        _bump(diagnostics, "materializations")
        _bump(diagnostics, f"{backend}_materializations")
        _bump(diagnostics, f"{backend}_nodes")
        _bump(diagnostics, "materialization_live_vars_total", live_k)
        if diagnostics is not None:
            diagnostics["live_vars_max"] = max(int(diagnostics.get("live_vars_max", 0)), len(out.vars))
            if backend == "bitset":
                diagnostics["hybrid_depth_max"] = max(int(diagnostics.get("hybrid_depth_max", 0)), depth)
            if full_collapse:
                diagnostics["full_collapse_occurred"] = 1
        return out

    def _align_for_combine(piece: _MatRes, target_vars: Tuple[str, ...]) -> np.ndarray:
        if piece.boundary_source and piece.const_value is None:
            t0 = time.perf_counter()
            out, did_transpose, inserted = align_to_vars_with_stats(piece.arr, piece.vars, target_vars)
            t1 = time.perf_counter()
            _add_float(diagnostics, "boundary_align_time_s", t1 - t0)
            _bump(diagnostics, "boundary_align_calls")
            if did_transpose:
                _bump(diagnostics, "boundary_align_transpose_calls")
            _bump(diagnostics, "boundary_align_insert_axes_total", inserted)
            return out
        return align_to_vars(piece.arr, piece.vars, target_vars)

    def rec(cur: CMNode, *, depth: int, allow_bitset_collapse: bool) -> _MatRes:
        key = (cur, _fixed_key_for_node(cur, fixed_map), allow_bitset_collapse)
        cached = memo.get(key)
        if cached is not None:
            _bump(diagnostics, "materialization_cache_hits")
            _bump(diagnostics, "decision_cache_hit")
            if diagnostics is not None and cached.backend == "bitset":
                diagnostics["hybrid_depth_max"] = max(int(diagnostics.get("hybrid_depth_max", 0)), depth)
            return cached

        live_vars = cur.vars if not fixed_map else tuple(v for v in cur.vars if v not in fixed_map)
        live_k = len(live_vars)
        use_bitset = False
        if materialize_mode == "hybrid":
            use_bitset = allow_bitset_collapse and live_k <= hybrid_threshold
        elif materialize_mode == "partial_hybrid":
            use_bitset = allow_bitset_collapse and live_k <= hybrid_threshold

        if materialize_mode == "numpy":
            _bump(diagnostics, "decision_numpy_mode_forced")
        elif materialize_mode == "partial_hybrid" and depth == 0 and (live_k <= hybrid_threshold):
            _bump(diagnostics, "decision_numpy_root_forced")

        if (not use_bitset) and allow_bitset_collapse and (live_k > hybrid_threshold):
            _bump(diagnostics, "decision_numpy_k_gt_threshold")

        if use_bitset:
            _bump(diagnostics, "decision_bitset_k_le_threshold")
            if len(cur.vars) > hybrid_threshold and live_k <= hybrid_threshold:
                _bump(diagnostics, "decision_bitset_fixed_var_reduction_helped")
            out = materialize_bitset(cur, live_vars, live_k)
            return finalize(
                cur,
                key,
                out,
                backend="bitset",
                live_k=live_k,
                depth=depth,
                full_collapse=(depth == 0),
            )

        if cur.kind == "const":
            out = _MatRes(np.array(bool(cur.const_value), dtype=bool), tuple(), cur.const_value, "numpy", False)
        elif cur.kind == "var":
            if cur.var_name in fixed_map:
                bit = int(bool(fixed_map[cur.var_name]))
                out = _MatRes(np.array(bool(bit), dtype=bool), tuple(), bit, "numpy", False)
            else:
                out = _MatRes(AXIS.copy(), (cur.var_name,), None, "numpy", False)
        elif cur.kind == "not":
            child = rec(
                cur.args[0],
                depth=depth + 1,
                allow_bitset_collapse=(materialize_mode == "partial_hybrid"),
            )
            if child.const_value is not None:
                out = _MatRes(
                    np.array(bool(1 - child.const_value), dtype=bool),
                    tuple(),
                    int(1 - child.const_value),
                    "numpy",
                    False,
                )
            else:
                out = _MatRes(
                    np.logical_not(child.arr),
                    child.vars,
                    None,
                    "numpy",
                    bool(child.boundary_source),
                )
        else:
            pieces = [
                rec(
                    arg,
                    depth=depth + 1,
                    allow_bitset_collapse=(materialize_mode == "partial_hybrid"),
                )
                for arg in cur.args
            ]

            if cur.op == "AND":
                for piece in pieces:
                    if piece.const_value == 0:
                        _bump(diagnostics, "pruned_branches")
                        out = _MatRes(np.array(False, dtype=bool), tuple(), 0, "numpy", False)
                        break
                else:
                    kept = [p for p in pieces if p.const_value != 1]
                    if len(kept) != len(pieces):
                        _bump(diagnostics, "pruned_branches", len(pieces) - len(kept))
                    if not kept:
                        out = _MatRes(np.array(True, dtype=bool), tuple(), 1, "numpy", False)
                    elif len(kept) == 1:
                        out = kept[0]
                    else:
                        acc = _align_for_combine(kept[0], live_vars)
                        for piece in kept[1:]:
                            acc = combine(acc, _align_for_combine(piece, live_vars), "AND", diagnostics)
                        out = _MatRes(acc, live_vars, None, "numpy", False)
            elif cur.op == "OR":
                for piece in pieces:
                    if piece.const_value == 1:
                        _bump(diagnostics, "pruned_branches")
                        out = _MatRes(np.array(True, dtype=bool), tuple(), 1, "numpy", False)
                        break
                else:
                    kept = [p for p in pieces if p.const_value != 0]
                    if len(kept) != len(pieces):
                        _bump(diagnostics, "pruned_branches", len(pieces) - len(kept))
                    if not kept:
                        out = _MatRes(np.array(False, dtype=bool), tuple(), 0, "numpy", False)
                    elif len(kept) == 1:
                        out = kept[0]
                    else:
                        acc = _align_for_combine(kept[0], live_vars)
                        for piece in kept[1:]:
                            acc = combine(acc, _align_for_combine(piece, live_vars), "OR", diagnostics)
                        out = _MatRes(acc, live_vars, None, "numpy", False)
            elif cur.op == "XOR":
                parity = 0
                kept = []
                for piece in pieces:
                    if piece.const_value is None:
                        kept.append(piece)
                    else:
                        _bump(diagnostics, "pruned_branches")
                        parity ^= int(piece.const_value)
                if not kept:
                    out = _MatRes(np.array(bool(parity), dtype=bool), tuple(), parity, "numpy", False)
                elif len(kept) == 1 and parity == 0:
                    out = kept[0]
                else:
                    acc = _align_for_combine(kept[0], live_vars)
                    for piece in kept[1:]:
                        acc = combine(acc, _align_for_combine(piece, live_vars), "XOR", diagnostics)
                    if parity == 1:
                        acc = np.logical_not(acc)
                    out = _MatRes(acc, live_vars, None, "numpy", False)
            elif cur.op == "EQV":
                left = pieces[0]
                right = pieces[1]
                if left.const_value is not None or right.const_value is not None:
                    _bump(diagnostics, "pruned_branches")
                if left.const_value == 1:
                    out = right
                elif right.const_value == 1:
                    out = left
                elif left.const_value == 0:
                    if right.const_value is not None:
                        out = _MatRes(
                            np.array(bool(1 - right.const_value), dtype=bool),
                            tuple(),
                            int(1 - right.const_value),
                            "numpy",
                            False,
                        )
                    else:
                        out = _MatRes(np.logical_not(right.arr), right.vars, None, "numpy", bool(right.boundary_source))
                elif right.const_value == 0:
                    if left.const_value is not None:
                        out = _MatRes(
                            np.array(bool(1 - left.const_value), dtype=bool),
                            tuple(),
                            int(1 - left.const_value),
                            "numpy",
                            False,
                        )
                    else:
                        out = _MatRes(np.logical_not(left.arr), left.vars, None, "numpy", bool(left.boundary_source))
                else:
                    out = _MatRes(
                        combine(
                            _align_for_combine(left, live_vars),
                            _align_for_combine(right, live_vars),
                            "EQV",
                            diagnostics,
                        ),
                        live_vars,
                        None,
                        "numpy",
                        False,
                    )
            elif cur.op == "IMP":
                left = pieces[0]
                right = pieces[1]
                if left.const_value is not None or right.const_value is not None:
                    _bump(diagnostics, "pruned_branches")
                if left.const_value == 0 or right.const_value == 1:
                    out = _MatRes(np.array(True, dtype=bool), tuple(), 1, "numpy", False)
                elif left.const_value == 1:
                    out = right
                elif right.const_value == 0:
                    if left.const_value is not None:
                        out = _MatRes(
                            np.array(bool(1 - left.const_value), dtype=bool),
                            tuple(),
                            int(1 - left.const_value),
                            "numpy",
                            False,
                        )
                    else:
                        out = _MatRes(np.logical_not(left.arr), left.vars, None, "numpy", bool(left.boundary_source))
                else:
                    out = _MatRes(
                        combine(
                            _align_for_combine(left, live_vars),
                            _align_for_combine(right, live_vars),
                            "IMP",
                            diagnostics,
                        ),
                        live_vars,
                        None,
                        "numpy",
                        False,
                    )
            else:
                raise ValueError(cur.op)

        return finalize(cur, key, out, backend="numpy", live_k=live_k, depth=depth)

    return rec(node, depth=0, allow_bitset_collapse=(materialize_mode == "hybrid"))


def materialize_cm(
    node: CMNode,
    R: Sequence[str],
    C: Sequence[str],
    fixed: Optional[Dict[str, int]] = None,
    *,
    diagnostics: Optional[Dict[str, Any]] = None,
    combine_fn: Optional[Callable[[np.ndarray, np.ndarray, str, Optional[Dict[str, Any]]], np.ndarray]] = None,
    materialize_mode: str = "partial_hybrid",
    hybrid_threshold: int = 7,
) -> np.ndarray:
    # Stable, benchmark-friendly final-output diagnostics (representation_code=0 for dense CM matrix).
    _init_final_output_diagnostics(diagnostics)
    target_vars = tuple(list(R) + list(C))
    res = _materialize_ir_tagged(
        node,
        fixed=fixed,
        diagnostics=diagnostics,
        combine_fn=combine_fn,
        materialize_mode=materialize_mode,
        hybrid_threshold=hybrid_threshold,
    )
    arr, live_vars, const_value = res.arr, res.vars, res.const_value
    if const_value is not None:
        arr = np.array(bool(const_value), dtype=bool)
        live_vars = tuple()

    if res.boundary_source and const_value is None and diagnostics is not None:
        t_final0 = time.perf_counter()
        arr, did_transpose, inserted = align_to_vars_with_stats(arr, live_vars, target_vars)
        _bump(diagnostics, "boundary_align_calls")
        if did_transpose:
            _bump(diagnostics, "boundary_align_transpose_calls")
        _bump(diagnostics, "boundary_align_insert_axes_total", inserted)
        expand_shape = tuple(2 for _ in target_vars)
        arr = np.broadcast_to(arr, expand_shape)
        out = arr.reshape(1 << len(R), 1 << len(C)).copy()
        t_final1 = time.perf_counter()
        _add_float(diagnostics, "boundary_align_time_s", t_final1 - t_final0)
        _record_final_output_diagnostics(
            diagnostics,
            final_cm_materialization_performed=1,
            final_cm_materialization_time_s=(t_final1 - t_final0),
            final_truth_table_materialization_time_s=0.0,
            final_bitset_returned=0,
            final_output_elements=(1 << len(target_vars)),
            final_output_representation_code=0,
            final_output_vars_count=len(target_vars),
        )
        return out

    t_final0 = time.perf_counter()
    arr = align_to_vars(arr, live_vars, target_vars)
    expand_shape = tuple(2 for _ in target_vars)
    arr = np.broadcast_to(arr, expand_shape)
    out = arr.reshape(1 << len(R), 1 << len(C)).copy()
    t_final1 = time.perf_counter()
    _record_final_output_diagnostics(
        diagnostics,
        final_cm_materialization_performed=1,
        final_cm_materialization_time_s=(t_final1 - t_final0),
        final_truth_table_materialization_time_s=0.0,
        final_bitset_returned=0,
        final_output_elements=(1 << len(target_vars)),
        final_output_representation_code=0,
        final_output_vars_count=len(target_vars),
    )
    return out


@dataclass(frozen=True)
class FinalNoReinflateResult:
    """Result for the explicit no-reinflation hybrid path.

    Representation code mapping:
      1: truth-table vector (1D uint8) in MSB-first ``vars_all`` order
      2: packed bitset (Python int) in MSB-first ``vars_all`` order
      3: reduced packed bitset over ``output_vars``
      4: reduced truth-table vector over ``output_vars``
    """

    final_output_representation_code: int
    bits: Optional[int] = None
    tt: Optional[np.ndarray] = None
    output_vars: Tuple[str, ...] = tuple()


def materialize_hybrid_no_reinflate(
    node: CMNode,
    vars_all: Sequence[str],
    fixed: Optional[Dict[str, int]] = None,
    *,
    diagnostics: Optional[Dict[str, Any]] = None,
    hybrid_threshold: int = 7,
    allow_reduced_output: bool = False,
    max_full_output_vars: Optional[int] = None,
) -> FinalNoReinflateResult:
    """Hybrid materialization that avoids dense CM reinflation.

    If the live variable count is <= ``hybrid_threshold`` we return a packed bitset directly.
    Otherwise we fall back to NumPy IR materialization and only produce a 1D TT vector
    (never a 2D dense CM matrix).
    """
    profile = diagnostics is not None and bool(diagnostics.get("cached_exec_profile_enabled", 0))
    t_total0 = time.perf_counter() if profile else None
    profile_base = (
        {
            "cached_exec_fixed_handling_time_s": float(diagnostics.get("cached_exec_fixed_handling_time_s", 0.0)),
            "cached_exec_var_order_time_s": float(diagnostics.get("cached_exec_var_order_time_s", 0.0)),
            "cached_exec_bitset_eval_time_s": float(diagnostics.get("cached_exec_bitset_eval_time_s", 0.0)),
            "cached_exec_result_wrap_time_s": float(diagnostics.get("cached_exec_result_wrap_time_s", 0.0)),
        }
        if profile and diagnostics is not None
        else {}
    )
    _init_final_output_diagnostics(diagnostics)
    if profile:
        _bump(diagnostics, "cached_exec_evaluations")

    t_fixed0 = time.perf_counter() if profile else None
    fixed_map = fixed or {}
    if t_fixed0 is not None:
        _add_float(diagnostics, "cached_exec_fixed_handling_time_s", time.perf_counter() - t_fixed0)

    t_vars0 = time.perf_counter() if profile else None
    vars_key = tuple(vars_all)
    live_vars = node.vars if not fixed_map else tuple(v for v in node.vars if v not in fixed_map)
    live_k = len(live_vars)
    n = len(vars_key)
    nominal_out_elems = 1 << n
    guard_full_output = max_full_output_vars is not None and n > int(max_full_output_vars)
    use_reduced_output = bool(allow_reduced_output and guard_full_output)
    output_vars = live_vars if use_reduced_output else vars_key
    output_k = len(output_vars)
    out_elems = 1 << output_k
    if t_vars0 is not None:
        _add_float(diagnostics, "cached_exec_var_order_time_s", time.perf_counter() - t_vars0)

    if hybrid_threshold < 0:
        raise ValueError("hybrid_threshold must be >= 0")
    if guard_full_output and not allow_reduced_output:
        raise ValueError(
            f"refusing to materialize full no-reinflate output for {n} variables; "
            "pass allow_reduced_output=True for structural large-n validation"
        )
    if use_reduced_output and max_full_output_vars is not None and output_k > int(max_full_output_vars):
        raise ValueError(
            f"refusing to materialize reduced no-reinflate output for {output_k} live variables; "
            f"max_full_output_vars={int(max_full_output_vars)}"
        )

    if live_k <= hybrid_threshold:
        t_eval0 = time.perf_counter() if _ir_timing_enabled(diagnostics) else None
        t_profile_eval0 = time.perf_counter() if profile else None
        bits = eval_cm_node_bitset(node, output_vars, fixed=fixed_map)
        if t_profile_eval0 is not None:
            _bump(diagnostics, "cached_exec_bitset_eval_calls")
            _add_float(diagnostics, "cached_exec_bitset_eval_time_s", time.perf_counter() - t_profile_eval0)
        if t_eval0 is not None:
            _bump(diagnostics, "nr_bitset_eval_calls")
            _add_float(diagnostics, "nr_bitset_eval_time_s", time.perf_counter() - t_eval0)
        t_wrap0 = time.perf_counter() if profile else None
        _record_final_output_diagnostics(
            diagnostics,
            final_cm_materialization_performed=0,
            final_cm_materialization_time_s=0.0,
            final_truth_table_materialization_time_s=0.0,
            final_bitset_returned=1,
            final_output_elements=out_elems,
            final_output_representation_code=3 if use_reduced_output else 2,
            final_output_nominal_elements=nominal_out_elems,
            final_output_vars_count=output_k,
            final_output_reduced=1 if use_reduced_output else 0,
            large_n_output_guard_triggered=1 if guard_full_output else 0,
        )
        result = FinalNoReinflateResult(
            final_output_representation_code=3 if use_reduced_output else 2,
            bits=bits,
            tt=None,
            output_vars=output_vars,
        )
        if profile:
            _bump(diagnostics, "cached_exec_result_wrap_count")
            _bump(diagnostics, "cached_exec_packed_bitset_return_count")
            if use_reduced_output:
                _bump(diagnostics, "cached_exec_reduced_output_count")
            if t_wrap0 is not None:
                _add_float(diagnostics, "cached_exec_result_wrap_time_s", time.perf_counter() - t_wrap0)
            if t_total0 is not None:
                elapsed = time.perf_counter() - t_total0
                _add_float(diagnostics, "cached_exec_total_time_s", elapsed)
                known = (
                    float(diagnostics.get("cached_exec_fixed_handling_time_s", 0.0))
                    - profile_base["cached_exec_fixed_handling_time_s"]
                    + float(diagnostics.get("cached_exec_var_order_time_s", 0.0))
                    - profile_base["cached_exec_var_order_time_s"]
                    + float(diagnostics.get("cached_exec_bitset_eval_time_s", 0.0))
                    - profile_base["cached_exec_bitset_eval_time_s"]
                    + float(diagnostics.get("cached_exec_result_wrap_time_s", 0.0))
                    - profile_base["cached_exec_result_wrap_time_s"]
                )
                dispatch = max(0.0, elapsed - known)
                _add_float(diagnostics, "cached_exec_dispatch_time_s", dispatch)
                _add_float(diagnostics, "cached_exec_other_time_s", 0.0)
        return result

    t_fallback0 = time.perf_counter() if _ir_timing_enabled(diagnostics) else None
    if profile:
        _bump(diagnostics, "cached_exec_fallback_to_tt_vector_count")
    arr, live_vars, const_value = materialize_ir(
        node,
        fixed=fixed_map,
        diagnostics=diagnostics,
        materialize_mode="hybrid",
        hybrid_threshold=hybrid_threshold,
    )
    if t_fallback0 is not None:
        _add_float(diagnostics, "nr_fallback_materialize_ir_time_s", time.perf_counter() - t_fallback0)
    if const_value is not None:
        arr = np.array(bool(const_value), dtype=bool)
        live_vars = tuple()

    t_mat0 = time.perf_counter() if _ir_timing_enabled(diagnostics) else None
    target_vars = output_vars if use_reduced_output else vars_key
    aligned = align_to_vars(arr, live_vars, target_vars)
    full = np.broadcast_to(aligned, (2,) * len(target_vars))
    tt = full.reshape(-1).astype(np.uint8, copy=False)
    t_mat1 = time.perf_counter() if t_mat0 is not None else None
    if t_mat0 is not None and t_mat1 is not None:
        _add_float(diagnostics, "nr_tt_vector_build_time_s", t_mat1 - t_mat0)
    t_wrap0 = time.perf_counter() if profile else None
    _record_final_output_diagnostics(
        diagnostics,
        final_cm_materialization_performed=0,
        final_cm_materialization_time_s=0.0,
        final_truth_table_materialization_time_s=(t_mat1 - t_mat0) if (t_mat0 is not None and t_mat1 is not None) else 0.0,
        final_bitset_returned=0,
        final_output_elements=out_elems,
        final_output_representation_code=4 if use_reduced_output else 1,
        final_output_nominal_elements=nominal_out_elems,
        final_output_vars_count=output_k,
        final_output_reduced=1 if use_reduced_output else 0,
        large_n_output_guard_triggered=1 if guard_full_output else 0,
    )
    result = FinalNoReinflateResult(
        final_output_representation_code=4 if use_reduced_output else 1,
        bits=None,
        tt=tt,
        output_vars=target_vars,
    )
    if profile:
        _bump(diagnostics, "cached_exec_result_wrap_count")
        if use_reduced_output:
            _bump(diagnostics, "cached_exec_reduced_output_count")
        if t_wrap0 is not None:
            _add_float(diagnostics, "cached_exec_result_wrap_time_s", time.perf_counter() - t_wrap0)
        if t_total0 is not None:
            elapsed = time.perf_counter() - t_total0
            _add_float(diagnostics, "cached_exec_total_time_s", elapsed)
            known = (
                float(diagnostics.get("cached_exec_fixed_handling_time_s", 0.0))
                - profile_base["cached_exec_fixed_handling_time_s"]
                + float(diagnostics.get("cached_exec_var_order_time_s", 0.0))
                - profile_base["cached_exec_var_order_time_s"]
                + float(diagnostics.get("cached_exec_bitset_eval_time_s", 0.0))
                - profile_base["cached_exec_bitset_eval_time_s"]
                + float(diagnostics.get("cached_exec_result_wrap_time_s", 0.0))
                - profile_base["cached_exec_result_wrap_time_s"]
            )
            dispatch = max(0.0, elapsed - known)
            _add_float(diagnostics, "cached_exec_dispatch_time_s", dispatch)
            _add_float(diagnostics, "cached_exec_other_time_s", 0.0)
    return result


def expr_vars(expr: Expr) -> List[str]:
    return list(_sorted_unique_vars(_iter_expr_vars(expr)))
