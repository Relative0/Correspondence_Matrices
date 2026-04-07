"""
cm_build_lazy.py (updated)
- Broadcast-only alignment in _align_to_union (insert axis of length 1, NO repeat)
- Repeat/expand only ONCE during final ambient mapping
"""
from typing import List, Dict, Tuple
import numpy as np
from cm_exprlib import Var, Not, And, Or, Xor, Imp, Eqv

AXIS = np.array([True, False], dtype=bool)  # [1,0]

def _node_from_var(name: str):
    return AXIS.copy(), [name]

def _align_to_union(arr: np.ndarray, vars_arr: List[str], union_vars: List[str]) -> np.ndarray:
    """
    Expand/permute 'arr' so its axes match 'union_vars' by NAME.
    Missing variables are inserted as size-1 axes (broadcasted later). NO repeat here.
    """
    pos = {v:i for i,v in enumerate(vars_arr)}
    out = arr
    # Bring existing axes into the relative order they appear in union_vars
    existing = [pos[v] for v in union_vars if v in pos]
    if existing and existing != list(range(len(existing))):
        out = np.transpose(out, existing + [i for i in range(out.ndim) if i not in existing])
        out_vars = [v for v in union_vars if v in pos]
        vars_arr = out_vars
        pos = {v:i for i,v in enumerate(vars_arr)}
    # Insert size-1 axes for any missing variable, at the correct position
    for i, v in enumerate(union_vars):
        if v in pos:
            cur = pos[v]
            if cur != i:
                out = np.moveaxis(out, cur, i)
                # update positions
                for k in pos:
                    if pos[k] == i:
                        pos[k] = cur
                pos[v] = i
        else:
            out = np.expand_dims(out, axis=i)  # size-1 axis; defer duplication
            for k in list(pos.keys()):
                if pos[k] >= i:
                    pos[k] += 1
    return out

def _combine_hc(arr1, vars1, arr2, vars2, op: str):
    union = list(dict.fromkeys(vars1 + vars2))
    a = _align_to_union(arr1, vars1, union)
    b = _align_to_union(arr2, vars2, union)
    if op == "AND": out = a & b
    elif op == "OR": out = a | b
    elif op == "XOR": out = a ^ b
    elif op == "IMP": out = (~a) | b
    elif op == "EQV": out = ~(a ^ b)
    else: raise ValueError(op)
    return out, union

def _compile_lazy(e):
    if isinstance(e, Var): return _node_from_var(e.name)
    if isinstance(e, Not):
        arr, vs = _compile_lazy(e.a)
        return (~arr), vs
    if isinstance(e, And):
        a, va = _compile_lazy(e.a); b, vb = _compile_lazy(e.b)
        return _combine_hc(a, va, b, vb, "AND")
    if isinstance(e, Or):
        a, va = _compile_lazy(e.a); b, vb = _compile_lazy(e.b)
        return _combine_hc(a, va, b, vb, "OR")
    if isinstance(e, Xor):
        a, va = _compile_lazy(e.a); b, vb = _compile_lazy(e.b)
        return _combine_hc(a, va, b, vb, "XOR")
    if isinstance(e, Imp):
        a, va = _compile_lazy(e.a); b, vb = _compile_lazy(e.b)
        na = (~a); na, _ = _combine_hc(na, va, b, vb, "OR")
        return na, list(dict.fromkeys(va + vb))
    if isinstance(e, Eqv):
        a, va = _compile_lazy(e.a); b, vb = _compile_lazy(e.b)
        return _combine_hc(a, va, b, vb, "EQV")
    raise TypeError(f"Unknown node {type(e)}")

def compile_expr_to_cm_lazy(e, R: List[str], C: List[str], fixed: Dict[str,int]):
    # Build hypercube
    arr, vlist = _compile_lazy(e)
    target_vars = list(R) + list(C)

    # Align to union (broadcast-only, keeps size-1 axes for missing)
    union = list(dict.fromkeys(vlist + [v for v in target_vars if v not in vlist]))
    arr = _align_to_union(arr, vlist, union); vlist = union

    # Apply fixed selections (take along those axes)
    pos = {v:i for i,v in enumerate(vlist)}
    to_take = {}
    for v, bit in (fixed or {}).items():
        if v in pos: to_take[pos[v]] = int(bit)
    for axis in sorted(to_take.keys(), reverse=True):
        arr = np.take(arr, to_take[axis], axis=axis)
        del vlist[axis]

    # Insert/permute to exactly target_vars order (still broadcast where missing)
    for i, v in enumerate(target_vars):
        if v in vlist:
            cur = vlist.index(v)
            if cur != i:
                arr = np.moveaxis(arr, cur, i)
                vlist.pop(cur); vlist.insert(i, v)
        else:
            arr = np.expand_dims(arr, axis=i)  # size-1 axis
            vlist.insert(i, v)

    # Now materialize to (2**|R|, 2**|C|) in one go
    # Expand each var axis to length 2 by repeating once at the end
    expand_shape = tuple(2 for _ in target_vars)
    arr = np.broadcast_to(arr, expand_shape)  # zero-copy view where possible
    return arr.reshape(1 << len(R), 1 << len(C)).copy()
