from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
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


class CMIRBuilder:
    def __init__(self, diagnostics: Optional[Dict[str, int]] = None):
        self.diagnostics = diagnostics
        self._interned: Dict[Tuple[object, ...], CMNode] = {}

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
        cached = self._interned.get(key)
        if cached is not None:
            _bump(self.diagnostics, "subtree_cache_hits")
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
        if node.const_value is not None:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return self.const(1 - node.const_value)
        if node.kind == "not":
            _bump(self.diagnostics, "canonical_rewrites")
            return node.args[0]
        return self._intern(
            kind="not",
            key=("NOT", node.key),
            vars=node.vars,
            const_value=None,
            op="NOT",
            args=(node,),
        )

    @staticmethod
    def _is_negation_of(a: CMNode, b: CMNode) -> bool:
        return (a.kind == "not" and a.args[0] == b) or (b.kind == "not" and b.args[0] == a)

    def _canonicalize_commutative_args(self, op: str, args: Sequence[CMNode]) -> Tuple[CMNode, ...]:
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

    def make_and(self, args: Sequence[CMNode]) -> CMNode:
        ordered = self._canonicalize_commutative_args("AND", args)
        out: List[CMNode] = []
        seen = set()
        for node in ordered:
            if node.const_value == 0:
                _bump(self.diagnostics, "canonical_rewrites")
                _bump(self.diagnostics, "pruned_branches")
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
                return self.const(0)
            out.append(node)
            seen.add(node)
        if not out:
            return self.const(1)
        if len(out) == 1:
            _bump(self.diagnostics, "canonical_rewrites")
            return out[0]
        live_vars = _sorted_unique_vars(v for node in out for v in node.vars)
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
        ordered = self._canonicalize_commutative_args("OR", args)
        out: List[CMNode] = []
        seen = set()
        for node in ordered:
            if node.const_value == 1:
                _bump(self.diagnostics, "canonical_rewrites")
                _bump(self.diagnostics, "pruned_branches")
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
                return self.const(1)
            out.append(node)
            seen.add(node)
        if not out:
            return self.const(0)
        if len(out) == 1:
            _bump(self.diagnostics, "canonical_rewrites")
            return out[0]
        live_vars = _sorted_unique_vars(v for node in out for v in node.vars)
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
        ordered = self._canonicalize_commutative_args("XOR", args)
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
        if not out:
            return self.const(parity)
        if len(out) == 1:
            if parity == 0:
                _bump(self.diagnostics, "canonical_rewrites")
                return out[0]
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return self.negate(out[0])

        live_vars = _sorted_unique_vars(v for node in out for v in node.vars)
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
        if left == right:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return self.const(1)
        if self._is_negation_of(left, right):
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return self.const(0)
        if left.const_value == 1:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return right
        if right.const_value == 1:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return left
        if left.const_value == 0:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return self.negate(right)
        if right.const_value == 0:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return self.negate(left)
        ordered = tuple(sorted((left, right), key=lambda node: node.key))
        if ordered != (left, right):
            _bump(self.diagnostics, "canonical_rewrites")
        live_vars = _sorted_unique_vars(v for node in ordered for v in node.vars)
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
        if left == right:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return self.const(1)
        if left.const_value == 0 or right.const_value == 1:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return self.const(1)
        if left.const_value == 1:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return right
        if right.const_value == 0:
            _bump(self.diagnostics, "canonical_rewrites")
            _bump(self.diagnostics, "pruned_branches")
            return self.negate(left)
        live_vars = _sorted_unique_vars(v for node in (left, right) for v in node.vars)
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


def compile_expr_to_cm_ir(expr: Expr, diagnostics: Optional[Dict[str, int]] = None) -> CMNode:
    builder = CMIRBuilder(diagnostics)
    return builder.build(expr)


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

        live_vars = tuple(v for v in cur.vars if v not in fixed_map)
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
        t0 = time.perf_counter()
        arr, did_transpose, inserted = align_to_vars_with_stats(arr, live_vars, target_vars)
        _bump(diagnostics, "boundary_align_calls")
        if did_transpose:
            _bump(diagnostics, "boundary_align_transpose_calls")
        _bump(diagnostics, "boundary_align_insert_axes_total", inserted)
        expand_shape = tuple(2 for _ in target_vars)
        arr = np.broadcast_to(arr, expand_shape)
        out = arr.reshape(1 << len(R), 1 << len(C)).copy()
        t1 = time.perf_counter()
        _add_float(diagnostics, "boundary_align_time_s", t1 - t0)
        return out

    arr = align_to_vars(arr, live_vars, target_vars)
    expand_shape = tuple(2 for _ in target_vars)
    arr = np.broadcast_to(arr, expand_shape)
    return arr.reshape(1 << len(R), 1 << len(C)).copy()


def expr_vars(expr: Expr) -> List[str]:
    return list(_sorted_unique_vars(_iter_expr_vars(expr)))
