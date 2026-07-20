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
