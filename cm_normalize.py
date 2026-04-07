"""
cm_normalize.py (updated)
- add LRU-cached row/col bit-permutation indexers to avoid recomputing indices
- keep broadcast-based lift and bool ops
"""
from typing import Dict, List, Optional, Tuple
from functools import lru_cache
import numpy as np

def next_pow2(n: int) -> int:
    assert n > 0
    k = 1
    while k < n:
        k <<= 1
    return k

def canonical_layout(vars_all: List[str], mode: str = "balanced") -> Tuple[List[str], List[str]]:
    uniq = list(dict.fromkeys(vars_all))
    if mode == "balanced":
        if not uniq:
            return [], []
        split = max(1, (len(uniq) + 1) // 2)
        return uniq[:split], uniq[split:]
    if mode == "legacy_square":
        B = next_pow2(max(2, len(uniq)))
        pad = [f"__pad{i}__" for i in range(B - len(uniq))]
        V = uniq + pad
        R = V[: B // 2]
        C = V[B // 2 :]
        return R, C
    raise ValueError(f"Unknown canonical layout mode: {mode}")

@lru_cache(maxsize=256)
def _rows_perm_index(perm: Tuple[int, ...]) -> np.ndarray:
    r = len(perm)
    if r <= 1:
        return np.arange(1<<r, dtype=np.uint32)
    R = 1<<r
    idx = np.arange(R, dtype=np.uint32)
    new_idx = np.zeros_like(idx)
    for old_bit in range(r):
        bit = (idx >> (r-1-old_bit)) & 1
        newpos = perm[old_bit]
        new_idx |= bit << (r-1-newpos)
    return new_idx

@lru_cache(maxsize=256)
def _cols_perm_index(perm: Tuple[int, ...]) -> np.ndarray:
    c = len(perm)
    if c <= 1:
        return np.arange(1<<c, dtype=np.uint32)
    C = 1<<c
    idx = np.arange(C, dtype=np.uint32)
    new_idx = np.zeros_like(idx)
    for old_bit in range(c):
        bit = (idx >> (c-1-old_bit)) & 1
        newpos = perm[old_bit]
        new_idx |= bit << (c-1-newpos)
    return new_idx

@lru_cache(maxsize=512)
def _row_lift_meta(vars_rows: Tuple[str, ...], layout_rows: Tuple[str, ...]) -> Tuple[Tuple[int, ...], int]:
    if not vars_rows:
        return tuple(), 0
    target_positions = {v: k for k, v in enumerate([vv for vv in layout_rows if vv in vars_rows])}
    perm = tuple(target_positions[v] for v in vars_rows)
    return perm, len(target_positions)


@lru_cache(maxsize=512)
def _col_lift_meta(vars_cols: Tuple[str, ...], layout_cols: Tuple[str, ...]) -> Tuple[Tuple[int, ...], int]:
    if not vars_cols:
        return tuple(), 0
    target_positions = {v: k for k, v in enumerate([vv for vv in layout_cols if vv in vars_cols])}
    perm = tuple(target_positions[v] for v in vars_cols)
    return perm, len(target_positions)


def cm_normalize_cache_stats() -> Dict[str, int]:
    """Expose LRU cache counters for permutation/lift metadata reuse diagnostics."""
    row_perm = _rows_perm_index.cache_info()
    col_perm = _cols_perm_index.cache_info()
    row_meta = _row_lift_meta.cache_info()
    col_meta = _col_lift_meta.cache_info()
    return {
        "rows_perm_hits": int(row_perm.hits),
        "rows_perm_misses": int(row_perm.misses),
        "rows_perm_currsize": int(row_perm.currsize),
        "cols_perm_hits": int(col_perm.hits),
        "cols_perm_misses": int(col_perm.misses),
        "cols_perm_currsize": int(col_perm.currsize),
        "row_meta_hits": int(row_meta.hits),
        "row_meta_misses": int(row_meta.misses),
        "row_meta_currsize": int(row_meta.currsize),
        "col_meta_hits": int(col_meta.hits),
        "col_meta_misses": int(col_meta.misses),
        "col_meta_currsize": int(col_meta.currsize),
    }


def clear_cm_normalize_caches() -> None:
    _rows_perm_index.cache_clear()
    _cols_perm_index.cache_clear()
    _row_lift_meta.cache_clear()
    _col_lift_meta.cache_clear()

def _permute_bits_rows(M: np.ndarray, perm: List[int]) -> np.ndarray:
    rperm = tuple(perm)
    if len(rperm) <= 1:
        return M
    if all(i == p for i, p in enumerate(rperm)):
        return M
    return M[_rows_perm_index(rperm), :]

def _permute_bits_cols(M: np.ndarray, perm: List[int]) -> np.ndarray:
    cperm = tuple(perm)
    if len(cperm) <= 1:
        return M
    if all(i == p for i, p in enumerate(cperm)):
        return M
    return M[:, _cols_perm_index(cperm)]

def lift_cm(Ms: np.ndarray,
            vars_rows: List[str],
            vars_cols: List[str],
            R: List[str],
            C: List[str],
            fixed: Optional[Dict[str,int]] = None) -> np.ndarray:
    fixed = fixed or {}
    tR = tuple(R)
    tC = tuple(C)
    tRows = tuple(vars_rows)
    tCols = tuple(vars_cols)
    if vars_rows:
        perm_r, _ = _row_lift_meta(tRows, tR)
        Ms = _permute_bits_rows(Ms, list(perm_r))
    if vars_cols:
        perm_c, _ = _col_lift_meta(tCols, tC)
        Ms = _permute_bits_cols(Ms, list(perm_c))
    _, r_small = _row_lift_meta(tRows, tR)
    _, c_small = _col_lift_meta(tCols, tC)
    out = Ms.reshape((2,)*r_small + (2,)*c_small).astype(bool, copy=False)
    for i, v in enumerate(R):
        if v in vars_rows:
            pass
        elif v in fixed:
            out = np.take(out, int(fixed[v]), axis=i)
        else:
            out = np.expand_dims(out, axis=i)
            out = np.repeat(out, 2, axis=i)
    base = len(R)
    for j, v in enumerate(C):
        aj = base + j
        if v in vars_cols:
            pass
        elif v in fixed:
            out = np.take(out, int(fixed[v]), axis=aj)
        else:
            out = np.expand_dims(out, axis=aj)
            out = np.repeat(out, 2, axis=aj)
    return out.reshape(1 << len(R), 1 << len(C))

def combine_pointwise(M1: np.ndarray, M2: np.ndarray, op: str) -> np.ndarray:
    if M1.shape != M2.shape:
        raise ValueError("shapes must match")
    a = M1.astype(bool, copy=False); b = M2.astype(bool, copy=False)
    if op == "AND":  out = a & b
    elif op == "OR": out = a | b
    elif op == "XOR": out = a ^ b
    elif op == "IMP": out = (~a) | b
    elif op == "EQV": out = ~(a ^ b)
    elif op == "NAND": out = ~(a & b)
    elif op == "NOR":  out = ~(a | b)
    else: raise ValueError(op)
    return out
