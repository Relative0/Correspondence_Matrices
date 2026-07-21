from __future__ import annotations

from functools import lru_cache
from types import MappingProxyType
from typing import TYPE_CHECKING, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np

from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

if TYPE_CHECKING:
    from cm_ir import CMNode


@lru_cache(maxsize=256)
def _build_bitset_env_cached(vars_key: Tuple[str, ...]) -> Mapping[str, int]:
    n_vars = len(vars_key)
    n_rows = 1 << n_vars
    env: Dict[str, int] = {}
    if n_vars > 10:
        # The pure-Python block loop below is O(2^n) bigint shifts per variable and
        # becomes a first-touch cliff (~130 ms at n=16, ~1.5 s at n=18). Vectorize:
        # bit k of a variable's mask is that variable's value in assignment row k.
        rows = np.arange(n_rows, dtype=np.uint32)
        for v, name in enumerate(vars_key):
            bits = ((rows >> (n_vars - 1 - v)) & 1).astype(np.uint8)
            packed = np.packbits(bits, bitorder="little")
            env[name] = int.from_bytes(packed.tobytes(), "little")
    else:
        for v, name in enumerate(vars_key):
            block = 1 << (n_vars - 1 - v)
            stride = block << 1
            mask = 0
            one_block = (1 << block) - 1
            for start in range(block, n_rows, stride):
                mask |= one_block << start
            env[name] = mask
    # Freeze to prevent external mutation of cached state.
    return MappingProxyType(env)


def clear_bitset_env_cache() -> None:
    _build_bitset_env_cached.cache_clear()


def bitset_env_cache_stats() -> Dict[str, int]:
    info = _build_bitset_env_cached.cache_info()
    return {"hits": int(info.hits), "misses": int(info.misses), "size": int(info.currsize)}


def build_bitset_env(vars: Sequence[str]) -> Mapping[str, int]:
    """Build var -> truth-column bitmasks using MSB-first assignment ordering.

    Bit k corresponds to assignment row k in all_assignments_tt/eval_expr_tt.
    """
    return _build_bitset_env_cached(tuple(vars))


def eval_expr_bitset(expr: Expr, env: Mapping[str, int]) -> int:
    """Evaluate Expr to a packed truth-table bitset with width 2^n."""
    if not env:
        return 0
    n_vars = len(env)
    n_rows = 1 << n_vars
    full_mask = (1 << n_rows) - 1

    def rec(e: Expr) -> int:
        if isinstance(e, Var):
            return env[f"x{e.i}"]
        if isinstance(e, Not):
            return (~rec(e.a)) & full_mask
        if isinstance(e, And):
            return rec(e.a) & rec(e.b)
        if isinstance(e, Or):
            return rec(e.a) | rec(e.b)
        if isinstance(e, Xor):
            return rec(e.a) ^ rec(e.b)
        if isinstance(e, Imp):
            return ((~rec(e.a)) | rec(e.b)) & full_mask
        if isinstance(e, Eqv):
            return (~(rec(e.a) ^ rec(e.b))) & full_mask
        raise TypeError(e)

    return rec(expr)


def bitset_to_bool_array(bits: int, n_vars: int) -> np.ndarray:
    """Convert packed bitset to uint8 truth vector in TT row order."""
    n_rows = 1 << n_vars
    n_bytes = (n_rows + 7) // 8
    raw = bits.to_bytes(n_bytes, byteorder="little", signed=False)
    unpacked = np.unpackbits(np.frombuffer(raw, dtype=np.uint8), bitorder="little")
    return unpacked[:n_rows]


def bitset_to_bool_hypercube(bits: int, n_vars: int) -> np.ndarray:
    """Convert packed bitset to a boolean hypercube with shape ``(2,) * n_vars``."""
    return bitset_to_bool_array(bits, n_vars).astype(bool, copy=False).reshape((2,) * n_vars)


def eval_cm_node_bitset(
    node: "CMNode",
    live_vars: Sequence[str],
    *,
    fixed: Optional[Mapping[str, int]] = None,
) -> int:
    """Evaluate a CM IR node to a packed truth-table bitset over ``live_vars``.

    ``live_vars`` defines the MSB-first assignment order used by the packed result.
    Variables absent from ``live_vars`` must be provided in ``fixed``.
    """
    vars_key = tuple(live_vars)
    env = build_bitset_env(vars_key)
    fixed_map = fixed or {}
    n_rows = 1 << len(vars_key)
    full_mask = (1 << n_rows) - 1
    # Memo keyed by id(node): nodes are kept alive by the DAG for the whole call, and
    # structural hashing of CMNode keys is O(subtree) — id lookup is O(1). Two
    # structurally-equal but distinct node objects only cost a memo miss, never correctness.
    memo: Dict[int, int] = {}

    def rec(cur: "CMNode") -> int:
        cached = memo.get(id(cur))
        if cached is not None:
            return cached

        if cur.kind == "const":
            out = full_mask if int(cur.const_value or 0) else 0
        elif cur.kind == "var":
            if cur.var_name in fixed_map:
                out = full_mask if int(bool(fixed_map[cur.var_name])) else 0
            else:
                try:
                    out = int(env[cur.var_name])
                except KeyError as exc:
                    raise KeyError(f"missing live/fixed value for variable {cur.var_name!r}") from exc
        elif cur.kind == "not":
            out = (~rec(cur.args[0])) & full_mask
        elif cur.op == "AND":
            out = full_mask
            for arg in cur.args:
                out &= rec(arg)
        elif cur.op == "OR":
            out = 0
            for arg in cur.args:
                out |= rec(arg)
        elif cur.op == "XOR":
            out = 0
            for arg in cur.args:
                out ^= rec(arg)
        elif cur.op == "IMP":
            left = rec(cur.args[0])
            right = rec(cur.args[1])
            out = ((~left) | right) & full_mask
        elif cur.op == "EQV":
            left = rec(cur.args[0])
            right = rec(cur.args[1])
            out = (~(left ^ right)) & full_mask
        else:
            raise TypeError(cur)

        memo[id(cur)] = out
        return out

    return rec(node)


# ---------------------------------------------------------------------------
# C1a: flat (linearized) CM-node evaluator — opt-in alternative to the
# recursive kernel above. The interned CMNode DAG is lowered ONCE into a
# linear postorder instruction list (one instruction per unique DAG node, so
# sharing is exploited at compile time and the eval loop needs no memo), and
# per-(vars_key, fixed) variable/constant masks are resolved ONCE into a
# "bound" slot template (legitimate compile-once reuse, same class as the
# build_bitset_env LRU: it stores resolved *input* masks, never outputs).
# Bit-identical to eval_cm_node_bitset by construction and by test sweep.
# ---------------------------------------------------------------------------

_FLAT_OP_NOT = 0
_FLAT_OP_AND = 1
_FLAT_OP_OR = 2
_FLAT_OP_XOR = 3
_FLAT_OP_IMP = 4
_FLAT_OP_EQV = 5

_FLAT_OPCODE = {"AND": _FLAT_OP_AND, "OR": _FLAT_OP_OR, "XOR": _FLAT_OP_XOR,
                "IMP": _FLAT_OP_IMP, "EQV": _FLAT_OP_EQV}

_FLAT_BOUND_CACHE_MAX = 64


class FlatProgram:
    """Linear postorder program lowered from a CMNode DAG.

    ``loads``: tuple of (slot, kind, payload) with kind in {"var", "const"}.
    ``ops``:   tuple of (slot, opcode, arg_slots) in dependency order.
    ``bound_cache``: {(vars_key, fixed_items): (slot_template, full_mask)} —
    small FIFO-evicted cache of resolved input masks.
    """

    __slots__ = ("n_slots", "root_slot", "loads", "ops", "bound_cache")

    def __init__(self, n_slots: int, root_slot: int, loads, ops) -> None:
        self.n_slots = n_slots
        self.root_slot = root_slot
        self.loads = loads
        self.ops = ops
        self.bound_cache: Dict[tuple, tuple] = {}


def compile_flat(node: "CMNode") -> FlatProgram:
    """Lower a CMNode DAG to a FlatProgram (iterative postorder, id-memoized)."""
    slot_of: Dict[int, int] = {}
    loads = []
    ops = []
    stack = [(node, False)]
    while stack:
        cur, processed = stack.pop()
        if id(cur) in slot_of:
            continue
        if not processed:
            stack.append((cur, True))
            for arg in cur.args:
                if id(arg) not in slot_of:
                    stack.append((arg, False))
            continue
        slot = len(slot_of)
        slot_of[id(cur)] = slot
        if cur.kind == "const":
            loads.append((slot, "const", int(cur.const_value or 0)))
        elif cur.kind == "var":
            loads.append((slot, "var", cur.var_name))
        elif cur.kind == "not":
            ops.append((slot, _FLAT_OP_NOT, (slot_of[id(cur.args[0])],)))
        else:
            opcode = _FLAT_OPCODE.get(cur.op)
            if opcode is None:
                raise TypeError(cur)
            ops.append((slot, opcode, tuple(slot_of[id(a)] for a in cur.args)))
    return FlatProgram(len(slot_of), slot_of[id(node)], tuple(loads), tuple(ops))


def get_flat_program(node: "CMNode") -> FlatProgram:
    """Return the node's FlatProgram, lowering and caching it on first use.

    Cached on the (frozen) node instance itself via object.__setattr__ — the
    same lifetime-correct pattern CMNode.__hash__ uses for its cached hash.
    """
    prog = node.__dict__.get("_flat_program")
    if prog is None:
        prog = compile_flat(node)
        object.__setattr__(node, "_flat_program", prog)
    return prog


def _bind_flat_program(prog: FlatProgram, vars_key: Tuple[str, ...],
                       fixed_map: Mapping[str, int]) -> tuple:
    key = (vars_key, tuple(sorted(fixed_map.items())))
    bound = prog.bound_cache.get(key)
    if bound is None:
        env = build_bitset_env(vars_key)
        full_mask = (1 << (1 << len(vars_key))) - 1
        template = [0] * prog.n_slots
        for slot, kind, payload in prog.loads:
            if kind == "const":
                template[slot] = full_mask if payload else 0
            elif payload in fixed_map:
                template[slot] = full_mask if int(bool(fixed_map[payload])) else 0
            else:
                try:
                    template[slot] = int(env[payload])
                except KeyError as exc:
                    raise KeyError(
                        f"missing live/fixed value for variable {payload!r}"
                    ) from exc
        if len(prog.bound_cache) >= _FLAT_BOUND_CACHE_MAX:
            prog.bound_cache.pop(next(iter(prog.bound_cache)))
        bound = (template, full_mask)
        prog.bound_cache[key] = bound
    return bound


def eval_cm_node_flat(
    node: "CMNode",
    live_vars: Sequence[str],
    *,
    fixed: Optional[Mapping[str, int]] = None,
) -> int:
    """Flat-program equivalent of eval_cm_node_bitset (bit-identical output)."""
    prog = get_flat_program(node)
    template, full_mask = _bind_flat_program(prog, tuple(live_vars), fixed or {})
    values = template.copy()
    for slot, opcode, arg_slots in prog.ops:
        if opcode == _FLAT_OP_AND:
            acc = values[arg_slots[0]]
            for i in arg_slots[1:]:
                acc &= values[i]
            values[slot] = acc
        elif opcode == _FLAT_OP_OR:
            acc = values[arg_slots[0]]
            for i in arg_slots[1:]:
                acc |= values[i]
            values[slot] = acc
        elif opcode == _FLAT_OP_XOR:
            acc = values[arg_slots[0]]
            for i in arg_slots[1:]:
                acc ^= values[i]
            values[slot] = acc
        elif opcode == _FLAT_OP_NOT:
            values[slot] = (~values[arg_slots[0]]) & full_mask
        elif opcode == _FLAT_OP_IMP:
            values[slot] = ((~values[arg_slots[0]]) | values[arg_slots[1]]) & full_mask
        else:  # _FLAT_OP_EQV
            values[slot] = (~(values[arg_slots[0]] ^ values[arg_slots[1]])) & full_mask
    return values[prog.root_slot]
