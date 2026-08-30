from __future__ import annotations

import hashlib
import importlib
import json
import random
import statistics
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cmbench.expr.eval import eval_expr_assignment


def _dd_cudd_available() -> bool:
    try:
        importlib.import_module("dd.cudd")
        return True
    except Exception:
        return False

def bdd_backend_identity(manager) -> Dict[str, Any]:
    module = getattr(manager.__class__, "__module__", "")
    return {
        "package": "dd",
        "module": module,
        "class": getattr(manager.__class__, "__name__", type(manager).__name__),
        "is_cudd": module == "dd.cudd",
        "is_autoref": module == "dd.autoref",
        "cudd_available": _dd_cudd_available(),
    }

def select_dd_module(backend_preference: str):
    if backend_preference not in ("auto", "cudd", "autoref"):
        raise ValueError(f"unknown ROBDD dd backend: {backend_preference!r}")
    errors: List[str] = []
    if backend_preference in ("auto", "cudd"):
        try:
            return importlib.import_module("dd.cudd"), None
        except Exception as e:
            errors.append(f"dd.cudd: {e!r}")
            if backend_preference == "cudd":
                return None, "; ".join(errors)
    try:
        return importlib.import_module("dd.autoref"), None
    except Exception as e:
        errors.append(f"dd.autoref: {e!r}")
        return None, "; ".join(errors)

def safe_bdd_node_count(manager, root) -> Optional[int]:
    try:
        dag_size = getattr(root, "dag_size", None)
        if dag_size is not None:
            return int(dag_size() if callable(dag_size) else dag_size)
    except Exception:
        pass
    try:
        stats = manager.statistics()
        for key in ("n_nodes", "nodes", "live_nodes", "dag_size"):
            if key in stats:
                return int(stats[key])
    except Exception:
        pass
    try:
        return int(len(manager))
    except Exception:
        return None

def expr_vars_first_occurrence(expr) -> List[str]:
    seen = set()
    order: List[str] = []

    def rec(e) -> None:
        if isinstance(e, Var):
            name = f"x{e.i}"
            if name not in seen:
                seen.add(name)
                order.append(name)
            return
        if isinstance(e, Not):
            rec(e.a)
            return
        if isinstance(e, (And, Or, Xor, Imp, Eqv)):
            rec(e.a)
            rec(e.b)
            return
        raise TypeError(e)

    rec(expr)
    return order


def robdd_interaction_profile(expr, n: int) -> Tuple[List[int], List[List[int]]]:
    """Return bounded occurrence counts and cross-subtree interaction weights."""
    if type(n) is not int or not 1 <= n <= 64:
        raise ValueError("ROBDD interaction order requires 1..64 variables")
    occurrences = [0 for _ in range(n)]
    weights = [[0 for _ in range(n)] for _ in range(n)]
    supports: Dict[int, int] = {}
    active: set[int] = set()
    completed: set[int] = set()
    stack = [(expr, False)]
    while stack:
        node, done = stack.pop()
        key = id(node)
        if done:
            active.discard(key)
            completed.add(key)
            if isinstance(node, Var):
                if type(node.i) is not int or not 0 <= node.i < n:
                    raise ValueError("expression variable outside ROBDD universe")
                occurrences[node.i] += 1
                supports[key] = 1 << node.i
            elif isinstance(node, Not):
                supports[key] = supports[id(node.a)]
            elif isinstance(node, (And, Or, Xor, Imp, Eqv)):
                left, right = supports[id(node.a)], supports[id(node.b)]
                left_only, right_only = left & ~right, right & ~left
                # Interactions introduced in a small local support are more
                # informative than broad root-level co-occurrence.
                local_weight = 1 + n - (left | right).bit_count()
                while left_only:
                    low_bit = left_only & -left_only
                    i = low_bit.bit_length() - 1
                    remaining = right_only
                    while remaining:
                        high_bit = remaining & -remaining
                        j = high_bit.bit_length() - 1
                        weights[i][j] += local_weight
                        weights[j][i] += local_weight
                        remaining ^= high_bit
                    left_only ^= low_bit
                supports[key] = left | right
            else:
                raise TypeError(node)
            continue
        if key in completed:
            continue
        if key in active:
            raise ValueError("cyclic expression")
        active.add(key)
        stack.append((node, True))
        if isinstance(node, Var):
            continue
        if isinstance(node, Not):
            stack.append((node.a, False))
            continue
        if isinstance(node, (And, Or, Xor, Imp, Eqv)):
            stack.append((node.b, False))
            stack.append((node.a, False))
            continue
        raise TypeError(node)
    return occurrences, weights


def robdd_interaction_order(expr, n: int) -> List[str]:
    """Greedily keep variables with strong source interactions adjacent."""
    occurrences, weights = robdd_interaction_profile(expr, n)
    degrees = [sum(row) for row in weights]
    remaining = set(range(n))
    order: List[int] = []
    while remaining:
        if not order:
            selected = max(remaining, key=lambda i: (degrees[i], occurrences[i], -i))
        else:
            selected = max(
                remaining,
                key=lambda i: (
                    sum(weights[i][chosen] for chosen in order),
                    degrees[i], occurrences[i], -i,
                ),
            )
        order.append(selected)
        remaining.remove(selected)
    return [f"x{i}" for i in order]


def robdd_variable_order(expr, n: int, policy: str, seed: Optional[int]) -> List[str]:
    names = [f"x{i}" for i in range(n)]
    if policy == "fixed":
        return names
    if policy == "expr":
        expr_order = expr_vars_first_occurrence(expr)
        present = set(expr_order)
        return expr_order + [name for name in names if name not in present]
    if policy == "interaction":
        return robdd_interaction_order(expr, n)
    if policy == "random":
        order = list(names)
        random.Random(0 if seed is None else int(seed)).shuffle(order)
        return order
    raise ValueError(f"unknown ROBDD order policy: {policy!r}")

def compact_order_repr(order: List[str]) -> str:
    txt = ",".join(order)
    if len(txt) <= 240:
        return txt
    digest = hashlib.sha256(txt.encode("utf-8")).hexdigest()[:16]
    return f"sha256:{digest};len={len(order)}"

def expr_to_dd_bdd(expr, manager, var_name_map: Mapping[str, str]):
    def xor(a, b):
        try:
            return a ^ b
        except TypeError:
            return manager.apply("xor", a, b)

    def rec(e):
        if isinstance(e, Var):
            return manager.var(var_name_map[f"x{e.i}"])
        if isinstance(e, Not):
            return ~rec(e.a)
        if isinstance(e, And):
            return rec(e.a) & rec(e.b)
        if isinstance(e, Or):
            return rec(e.a) | rec(e.b)
        if isinstance(e, Xor):
            return xor(rec(e.a), rec(e.b))
        if isinstance(e, Imp):
            return (~rec(e.a)) | rec(e.b)
        if isinstance(e, Eqv):
            return ~xor(rec(e.a), rec(e.b))
        raise TypeError(e)

    return rec(expr)

def _declare_dd_vars(manager, order: List[str]) -> None:
    try:
        manager.declare(*order)
        return
    except Exception:
        pass
    for level, name in enumerate(order):
        try:
            manager.add_var(name, level=level)
        except TypeError:
            manager.add_var(name)

def _try_collect_garbage(manager) -> None:
    try:
        manager.collect_garbage()
    except Exception:
        pass

def maybe_reorder_dd(manager, root, requested: bool, method: str) -> Dict[str, Any]:
    before = safe_bdd_node_count(manager, root)
    result = {
        "robdd_dynamic_reordering_requested": bool(requested),
        "robdd_dynamic_reordering_available": False,
        "robdd_dynamic_reordering_used": False,
        "robdd_reorder_method": method,
        "robdd_reorder_time_s": None,
        "robdd_nodes_before_reorder": before,
        "robdd_nodes_after_reorder": before,
    }
    if not requested:
        return result
    ident = bdd_backend_identity(manager)
    if not ident["is_cudd"]:
        return result
    if not hasattr(manager, "reorder") and not hasattr(manager, "configure"):
        return result
    result["robdd_dynamic_reordering_available"] = True
    t0 = time.perf_counter()
    try:
        try:
            manager.configure(reordering=True, method=method)
        except Exception:
            pass
        try:
            manager.reorder(method=method)
        except TypeError:
            manager.reorder()
        _try_collect_garbage(manager)
        result["robdd_reorder_time_s"] = time.perf_counter() - t0
        result["robdd_dynamic_reordering_used"] = True
        result["robdd_nodes_after_reorder"] = safe_bdd_node_count(manager, root)
    except Exception:
        result["robdd_reorder_time_s"] = time.perf_counter() - t0
        result["robdd_dynamic_reordering_used"] = False
        result["robdd_nodes_after_reorder"] = safe_bdd_node_count(manager, root)
    return result

def bdd_function_value(manager, root, assignment: Mapping[str, int]) -> int:
    bool_assignment = {k: bool(v) for k, v in assignment.items()}
    restricted = manager.let(bool_assignment, root)
    if restricted == manager.true:
        return 1
    if restricted == manager.false:
        return 0
    raise ValueError("BDD restriction did not reduce to a terminal")

def extract_dd_bdd_truth_table(
    manager,
    root,
    n: int,
    *,
    method: str = "all-assignments",
) -> Tuple[np.ndarray, float]:
    if method not in ("all-assignments", "vectorized-if-available"):
        raise ValueError(f"unknown ROBDD TT extraction method: {method!r}")
    names = [f"x{i}" for i in range(n)]
    out = np.empty(1 << n, dtype=np.uint8)
    t0 = time.perf_counter()
    for idx in range(1 << n):
        assignment = {name: (idx >> (n - 1 - i)) & 1 for i, name in enumerate(names)}
        out[idx] = bdd_function_value(manager, root, assignment)
    return out, time.perf_counter() - t0

def maybe_extract_dd_bdd_truth_table(
    manager,
    root,
    n: int,
    *,
    enabled: bool,
    max_n: int,
    method: str,
    tt_ref: Optional[np.ndarray],
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "robdd_tt_extract_time_s": None,
        "robdd_tt_extract_elements": None,
        "robdd_tt_extract_ok": None,
        "robdd_tt_extract_status": "skipped_flag_off",
        "robdd_extract_method": method,
        "robdd_tt_extract_error": None,
    }
    if not enabled:
        return result
    if n > int(max_n):
        result["robdd_tt_extract_status"] = "skipped_large_n"
        return result
    try:
        tt_bdd, elapsed = extract_dd_bdd_truth_table(manager, root, n, method=method)
        result["robdd_tt_extract_time_s"] = elapsed
        result["robdd_tt_extract_elements"] = int(tt_bdd.size)
        result["robdd_tt_extract_status"] = "ok"
        if tt_ref is not None:
            result["robdd_tt_extract_ok"] = bool(np.array_equal(tt_bdd, tt_ref.astype(np.uint8).reshape(-1)))
        else:
            result["robdd_tt_extract_ok"] = None
        return result
    except Exception as e:
        result["robdd_tt_extract_status"] = "error"
        result["robdd_tt_extract_error"] = repr(e)
        return result

def validate_dd_bdd_correctness(
    expr,
    n: int,
    manager,
    root,
    tt_ref: Optional[np.ndarray],
    rng: np.random.Generator,
    samples: int,
) -> Dict[str, Any]:
    names = [f"x{i}" for i in range(n)]
    if tt_ref is not None and n <= 16:
        ok = True
        for idx, bit in enumerate(tt_ref.tolist()):
            assignment = {name: (idx >> (n - 1 - i)) & 1 for i, name in enumerate(names)}
            if bdd_function_value(manager, root, assignment) != int(bit):
                ok = False
                break
        return {"robdd_ok": bool(ok), "robdd_correctness_mode": "exact_tt"}
    if samples > 0:
        ok = True
        for _ in range(samples):
            vals = rng.integers(0, 2, size=n, dtype=np.uint8)
            assignment = {name: int(vals[i]) for i, name in enumerate(names)}
            expected = eval_expr_assignment(expr, assignment)
            actual = bdd_function_value(manager, root, assignment)
            if expected != actual:
                ok = False
                break
        return {"robdd_ok": bool(ok), "robdd_correctness_mode": f"sampled_assignments:{samples}"}
    return {"robdd_ok": None, "robdd_correctness_mode": "skipped_large_n"}

def _empty_robdd_dd_result(
    *,
    backend_preference: str,
    order_policy: str,
    order_seed: Optional[int],
    order_sweeps: int,
    dynamic_reordering: bool,
    reorder_method: str,
    status: str,
    error: Optional[str],
    selection_objective: str = "composite",
) -> Dict[str, Any]:
    return {
        "robdd_build_time_s": None,
        "robdd_reorder_time_s": None,
        "robdd_total_build_plus_reorder_time_s": None,
        "robdd_node_count": None,
        "robdd_backend": None,
        "robdd_backend_module": None,
        "robdd_backend_class": None,
        "robdd_is_cudd": False,
        "robdd_is_autoref": False,
        "robdd_cudd_available": _dd_cudd_available(),
        "robdd_backend_preference": backend_preference,
        "robdd_order_policy": order_policy,
        "robdd_order_seed": order_seed,
        "robdd_order_sweeps": order_sweeps,
        "robdd_order_used": None,
        "robdd_best_time_s": None,
        "robdd_fastest_build_time_s": None,
        "robdd_smallest_node_build_time_s": None,
        "robdd_selected_build_time_s": None,
        "robdd_selected_query_time_s": None,
        "robdd_selected_build_plus_query_time_s": None,
        "robdd_selected_trial_index": None,
        "robdd_selection_objective": selection_objective,
        "robdd_selection_tiebreak": "nodes,build_time,trial_index",
        "robdd_order_trials_json": "[]",
        "robdd_order_generation_time_s": None,
        "robdd_order_search_time_s": None,
        "robdd_all_in_search_time_s": None,
        "robdd_median_time_s": None,
        "robdd_worst_time_s": None,
        "robdd_best_nodes": None,
        "robdd_median_nodes": None,
        "robdd_worst_nodes": None,
        "robdd_dynamic_reordering_requested": bool(dynamic_reordering),
        "robdd_dynamic_reordering_available": False,
        "robdd_dynamic_reordering_used": False,
        "robdd_reorder_method": reorder_method,
        "robdd_nodes_before_reorder": None,
        "robdd_nodes_after_reorder": None,
        "robdd_status": status,
        "robdd_error": error,
        "robdd_tt_extract_time_s": None,
        "robdd_tt_extract_elements": None,
        "robdd_tt_extract_ok": None,
        "robdd_total_build_plus_extract_time_s": None,
        "robdd_tt_extract_status": "skipped_flag_off",
        "robdd_extract_method": None,
        "robdd_tt_extract_error": None,
        "robdd_ok": None,
        "robdd_correctness_mode": None,
    }

def run_robdd_dd_backend(
    expr,
    n: int,
    *,
    backend_preference: str = "auto",
    order_policy: str = "fixed",
    dynamic_reordering: bool = False,
    reorder_method: str = "sift",
    order_seed: Optional[int] = None,
    order_sweeps: int = 1,
    selection_objective: str = "composite",
    query_assignments: Optional[Sequence[Mapping[str, int]]] = None,
    tt_ref: Optional[np.ndarray] = None,
    correctness_rng: Optional[np.random.Generator] = None,
    correctness_samples: int = 0,
    measure_tt_extract: bool = False,
    tt_extract_method: str = "all-assignments",
    tt_extract_max_n: int = 16,
) -> Dict[str, Any]:
    if order_policy not in ("fixed", "expr", "interaction", "random", "best-of-k"):
        raise ValueError(f"unknown ROBDD order policy: {order_policy!r}")
    sweeps = max(1, int(order_sweeps)) if order_policy == "best-of-k" else 1
    if selection_objective not in (
            "composite", "min_nodes", "min_build_time", "build_plus_query"):
        raise ValueError(f"unknown ROBDD selection objective: {selection_objective!r}")
    if query_assignments is None:
        query_assignments = ()
    if (not isinstance(query_assignments, Sequence) or len(query_assignments) > 256
            or any(not isinstance(assignment, Mapping) for assignment in query_assignments)):
        raise ValueError("ROBDD query assignments must be a bounded sequence")
    dd_module, error = select_dd_module(backend_preference)
    if dd_module is None:
        return _empty_robdd_dd_result(
            backend_preference=backend_preference,
            order_policy=order_policy,
            order_seed=order_seed,
            order_sweeps=sweeps,
            dynamic_reordering=dynamic_reordering,
            reorder_method=reorder_method,
            status="unavailable",
            error=error,
            selection_objective=selection_objective,
        )

    names = [f"x{i}" for i in range(n)]
    var_name_map = {name: name for name in names}
    trials: List[Dict[str, Any]] = []
    base_seed = 0 if order_seed is None else int(order_seed)
    search_started = time.perf_counter()
    order_generation_total = 0.0
    for sweep in range(sweeps):
        trial_started = time.perf_counter()
        effective_policy = "random" if order_policy == "best-of-k" else order_policy
        effective_seed = base_seed + sweep if effective_policy == "random" else order_seed
        order_started = time.perf_counter()
        order = robdd_variable_order(expr, n, effective_policy, effective_seed)
        order_generation_time = time.perf_counter() - order_started
        order_generation_total += order_generation_time
        try:
            manager = dd_module.BDD()
            _declare_dd_vars(manager, order)
            t0 = time.perf_counter()
            root = expr_to_dd_bdd(expr, manager, var_name_map)
            build_time = time.perf_counter() - t0
            node_count = safe_bdd_node_count(manager, root)
            reorder_result = maybe_reorder_dd(manager, root, dynamic_reordering, reorder_method)
            final_nodes = reorder_result.get("robdd_nodes_after_reorder")
            if final_nodes is None:
                final_nodes = node_count
            total_time = build_time + float(reorder_result.get("robdd_reorder_time_s") or 0.0)
            rng = correctness_rng if correctness_rng is not None else np.random.default_rng(0)
            check = validate_dd_bdd_correctness(
                expr,
                n,
                manager,
                root,
                tt_ref,
                rng,
                correctness_samples,
            )
            query_started = time.perf_counter()
            query_digest = 0
            for assignment in query_assignments:
                normalized = {}
                for name, value in assignment.items():
                    if name not in var_name_map or type(value) not in (int, bool) or int(value) not in (0, 1):
                        raise ValueError("invalid bounded ROBDD query assignment")
                    normalized[name] = bool(value)
                restricted = manager.let(normalized, root)
                count = safe_bdd_node_count(manager, restricted)
                query_digest ^= int(count or 0)
                query_digest ^= int(restricted == manager.true) << 1
                query_digest ^= int(restricted == manager.false) << 2
            query_time = time.perf_counter() - query_started
            ident = bdd_backend_identity(manager)
            trials.append(
                {
                    "manager": manager,
                    "root": root,
                    "order": order,
                    "build_time": build_time,
                    "node_count": final_nodes,
                    "nodes_before_reorder": reorder_result.get("robdd_nodes_before_reorder"),
                    "total_time": total_time,
                    "query_time": query_time,
                    "build_plus_query_time": total_time + query_time,
                    "query_digest": query_digest,
                    "reorder": reorder_result,
                    "identity": ident,
                    "check": check,
                    "status": "ok",
                    "error": None,
                    "trial_index": sweep,
                    "effective_seed": effective_seed,
                    "order_generation_time": order_generation_time,
                    "trial_total_time": time.perf_counter() - trial_started,
                }
            )
        except Exception as e:
            trials.append(
                {
                    "manager": None,
                    "root": None,
                    "order": order,
                    "build_time": None,
                    "node_count": None,
                    "nodes_before_reorder": None,
                    "total_time": None,
                    "query_time": None,
                    "build_plus_query_time": None,
                    "query_digest": None,
                    "reorder": maybe_reorder_dd(None, None, False, reorder_method) if False else {},
                    "identity": None,
                    "check": {"robdd_ok": False, "robdd_correctness_mode": "build_failed"},
                    "status": "error",
                    "error": repr(e),
                    "trial_index": sweep,
                    "effective_seed": effective_seed,
                    "order_generation_time": order_generation_time,
                    "trial_total_time": time.perf_counter() - trial_started,
                }
            )
    search_time = time.perf_counter() - search_started

    ok_trials = [t for t in trials if t["status"] == "ok" and t["build_time"] is not None]
    if not ok_trials:
        first_error = next((t["error"] for t in trials if t.get("error")), error)
        return _empty_robdd_dd_result(
            backend_preference=backend_preference,
            order_policy=order_policy,
            order_seed=order_seed,
            order_sweeps=sweeps,
            dynamic_reordering=dynamic_reordering,
            reorder_method=reorder_method,
            status="error",
            error=first_error,
            selection_objective=selection_objective,
        )
    if selection_objective == "build_plus_query":
        selection_key = lambda t: (
            float(t["build_plus_query_time"]), int(t["trial_index"]))
        tiebreak = "build_plus_query_time,trial_index"
    elif selection_objective == "min_build_time":
        selection_key = lambda t: (float(t["build_time"]), int(t["trial_index"]))
        tiebreak = "build_time,trial_index"
    elif selection_objective == "min_nodes":
        selection_key = lambda t: (float(t["node_count"] or 10**30), int(t["trial_index"]))
        tiebreak = "nodes,trial_index"
    else:
        selection_key = lambda t: (
            float(t["node_count"] or 10**30),
            float(t["build_time"]),
            int(t["trial_index"]),
        )
        tiebreak = "nodes,build_time,trial_index"
    best = min(ok_trials, key=selection_key)
    fastest = min(ok_trials, key=lambda t: (float(t["build_time"]), int(t["trial_index"])))
    smallest_nodes = min(
        ok_trials,
        key=lambda t: (float(t["node_count"] or 10**30), float(t["build_time"]), int(t["trial_index"])),
    )
    times = sorted(float(t["build_time"]) for t in ok_trials)
    nodes = sorted(int(t["node_count"]) for t in ok_trials if t["node_count"] is not None)
    ident = best["identity"] or {}
    reorder_result = best["reorder"]
    extract = maybe_extract_dd_bdd_truth_table(
        best["manager"],
        best["root"],
        n,
        enabled=measure_tt_extract,
        max_n=tt_extract_max_n,
        method=tt_extract_method,
        tt_ref=tt_ref,
    )
    build_plus_reorder = best["total_time"]
    extract_time = extract.get("robdd_tt_extract_time_s")
    build_plus_extract = (
        float(build_plus_reorder) + float(extract_time)
        if build_plus_reorder is not None and extract_time is not None
        else None
    )
    return {
        "robdd_build_time_s": best["build_time"],
        "robdd_reorder_time_s": reorder_result.get("robdd_reorder_time_s"),
        "robdd_total_build_plus_reorder_time_s": best["total_time"],
        "robdd_node_count": best["node_count"],
        "robdd_backend": "dd.cudd" if ident.get("is_cudd") else ("dd.autoref" if ident.get("is_autoref") else ident.get("module")),
        "robdd_backend_module": ident.get("module"),
        "robdd_backend_class": ident.get("class"),
        "robdd_is_cudd": bool(ident.get("is_cudd")),
        "robdd_is_autoref": bool(ident.get("is_autoref")),
        "robdd_cudd_available": bool(ident.get("cudd_available")),
        "robdd_backend_preference": backend_preference,
        "robdd_order_policy": order_policy,
        "robdd_order_seed": order_seed,
        "robdd_order_sweeps": sweeps,
        "robdd_order_used": compact_order_repr(best["order"]),
        "robdd_best_time_s": min(times) if times else None,
        # Compatibility: robdd_best_time_s retains its historical meaning
        # (minimum isolated build interval). New names below are authoritative.
        "robdd_fastest_build_time_s": fastest["build_time"],
        "robdd_smallest_node_build_time_s": smallest_nodes["build_time"],
        "robdd_selected_build_time_s": best["build_time"],
        "robdd_selected_query_time_s": best["query_time"],
        "robdd_selected_build_plus_query_time_s": best["build_plus_query_time"],
        "robdd_selected_trial_index": best["trial_index"],
        "robdd_selection_objective": selection_objective,
        "robdd_selection_tiebreak": tiebreak,
        "robdd_order_generation_time_s": order_generation_total,
        "robdd_order_search_time_s": search_time,
        "robdd_all_in_search_time_s": search_time,
        "robdd_order_trials_json": json.dumps(
            [
                {
                    "trial_index": t["trial_index"],
                    "effective_seed": t["effective_seed"],
                    "order": compact_order_repr(t["order"]),
                    "order_generation_time_s": t["order_generation_time"],
                    "build_time_s": t["build_time"],
                    "query_time_s": t["query_time"],
                    "build_plus_query_time_s": t["build_plus_query_time"],
                    "query_digest": t["query_digest"],
                    "reorder_time_s": t.get("reorder", {}).get("robdd_reorder_time_s"),
                    "trial_total_time_s": t["trial_total_time"],
                    "node_count": t["node_count"],
                    "status": t["status"],
                    "error": t["error"],
                    "correctness_ok": t.get("check", {}).get("robdd_ok"),
                    "correctness_mode": t.get("check", {}).get("robdd_correctness_mode"),
                }
                for t in trials
            ],
            sort_keys=True,
            separators=(",", ":"),
        ),
        "robdd_median_time_s": statistics.median(times) if times else None,
        "robdd_worst_time_s": max(times) if times else None,
        "robdd_best_nodes": min(nodes) if nodes else None,
        "robdd_median_nodes": statistics.median(nodes) if nodes else None,
        "robdd_worst_nodes": max(nodes) if nodes else None,
        "robdd_dynamic_reordering_requested": reorder_result.get("robdd_dynamic_reordering_requested", False),
        "robdd_dynamic_reordering_available": reorder_result.get("robdd_dynamic_reordering_available", False),
        "robdd_dynamic_reordering_used": reorder_result.get("robdd_dynamic_reordering_used", False),
        "robdd_reorder_method": reorder_result.get("robdd_reorder_method", reorder_method),
        "robdd_nodes_before_reorder": reorder_result.get("robdd_nodes_before_reorder"),
        "robdd_nodes_after_reorder": reorder_result.get("robdd_nodes_after_reorder"),
        "robdd_status": "ok",
        "robdd_error": None,
        **extract,
        "robdd_total_build_plus_extract_time_s": build_plus_extract,
        "robdd_ok": best["check"].get("robdd_ok"),
        "robdd_correctness_mode": best["check"].get("robdd_correctness_mode"),
    }

def _empty_robdd_equiv_result(
    *,
    backend_preference: str,
    order_policy: str,
    order_seed: Optional[int],
    order_sweeps: int,
    dynamic_reordering: bool,
    reorder_method: str,
    compare_repeat: int,
    status: str,
    error: Optional[str],
) -> Dict[str, Any]:
    return {
        "robdd_equiv_build_f_time_s": None,
        "robdd_equiv_build_g_time_s": None,
        "robdd_equiv_build_total_time_s": None,
        "robdd_equiv_compare_time_s": None,
        "robdd_equiv_compare_repeat": int(compare_repeat),
        "robdd_equiv_compare_per_call_time_s": None,
        "robdd_equiv_total_time_s": None,
        "robdd_equiv_result": None,
        "robdd_equiv_ok": None,
        "robdd_equiv_status": status,
        "robdd_equiv_error": error,
        "robdd_equiv_nodes_f": None,
        "robdd_equiv_nodes_g": None,
        "robdd_equiv_nodes_manager": None,
        "robdd_equiv_backend": None,
        "robdd_equiv_backend_module": None,
        "robdd_equiv_backend_class": None,
        "robdd_equiv_backend_preference": backend_preference,
        "robdd_equiv_order_policy": order_policy,
        "robdd_equiv_order_seed": order_seed,
        "robdd_equiv_order_sweeps": order_sweeps,
        "robdd_equiv_order_used": None,
        "robdd_equiv_reorder_requested": bool(dynamic_reordering),
        "robdd_equiv_reorder_used": False,
        "robdd_equiv_reorder_method": reorder_method,
    }

def robdd_equivalence_check(
    expr_f,
    expr_g,
    n: int,
    *,
    backend: str = "auto",
    order_policy: str = "fixed",
    dynamic_reordering: bool = False,
    reorder_method: str = "sift",
    order_seed: Optional[int] = None,
    order_sweeps: int = 1,
    compare_repeat: int = 1000,
    expected: Optional[bool] = None,
) -> Dict[str, Any]:
    if order_policy not in ("fixed", "expr", "interaction", "random", "best-of-k"):
        raise ValueError(f"unknown ROBDD order policy: {order_policy!r}")
    repeat = max(1, int(compare_repeat))
    sweeps = max(1, int(order_sweeps)) if order_policy == "best-of-k" else 1
    dd_module, error = select_dd_module(backend)
    if dd_module is None:
        return _empty_robdd_equiv_result(
            backend_preference=backend,
            order_policy=order_policy,
            order_seed=order_seed,
            order_sweeps=sweeps,
            dynamic_reordering=dynamic_reordering,
            reorder_method=reorder_method,
            compare_repeat=repeat,
            status="unavailable",
            error=error,
        )

    names = [f"x{i}" for i in range(n)]
    var_name_map = {name: name for name in names}
    base_seed = 0 if order_seed is None else int(order_seed)
    trials: List[Dict[str, Any]] = []
    combined_expr = And(expr_f, expr_g)

    for sweep in range(sweeps):
        effective_policy = "random" if order_policy == "best-of-k" else order_policy
        effective_seed = base_seed + sweep if effective_policy == "random" else order_seed
        order = robdd_variable_order(combined_expr, n, effective_policy, effective_seed)
        try:
            manager = dd_module.BDD()
            _declare_dd_vars(manager, order)
            t0 = time.perf_counter()
            root_f = expr_to_dd_bdd(expr_f, manager, var_name_map)
            build_f = time.perf_counter() - t0
            nodes_f = safe_bdd_node_count(manager, root_f)
            t1 = time.perf_counter()
            root_g = expr_to_dd_bdd(expr_g, manager, var_name_map)
            build_g = time.perf_counter() - t1
            reorder_result = maybe_reorder_dd(manager, root_f, dynamic_reordering, reorder_method)
            nodes_g = safe_bdd_node_count(manager, root_g)
            nodes_manager = safe_bdd_node_count(manager, root_f)
            t2 = time.perf_counter()
            result = False
            for _ in range(repeat):
                result = bool(root_f == root_g)
            compare_time = time.perf_counter() - t2
            ident = bdd_backend_identity(manager)
            build_total = build_f + build_g + float(reorder_result.get("robdd_reorder_time_s") or 0.0)
            total = build_total + compare_time
            trials.append(
                {
                    "status": "ok",
                    "error": None,
                    "order": order,
                    "manager": manager,
                    "build_f": build_f,
                    "build_g": build_g,
                    "build_total": build_total,
                    "compare_time": compare_time,
                    "total": total,
                    "result": result,
                    "nodes_f": nodes_f,
                    "nodes_g": nodes_g,
                    "nodes_manager": nodes_manager,
                    "reorder": reorder_result,
                    "identity": ident,
                }
            )
        except Exception as e:
            trials.append({"status": "error", "error": repr(e), "order": order})

    ok_trials = [t for t in trials if t.get("status") == "ok"]
    if not ok_trials:
        first_error = next((t.get("error") for t in trials if t.get("error")), error)
        return _empty_robdd_equiv_result(
            backend_preference=backend,
            order_policy=order_policy,
            order_seed=order_seed,
            order_sweeps=sweeps,
            dynamic_reordering=dynamic_reordering,
            reorder_method=reorder_method,
            compare_repeat=repeat,
            status="error",
            error=first_error,
        )
    best = min(ok_trials, key=lambda t: (float(t.get("nodes_manager") or 10**30), float(t["build_total"])))
    ident = best["identity"] or {}
    reorder_result = best["reorder"]
    result = bool(best["result"])
    return {
        "robdd_equiv_build_f_time_s": best["build_f"],
        "robdd_equiv_build_g_time_s": best["build_g"],
        "robdd_equiv_build_total_time_s": best["build_total"],
        "robdd_equiv_compare_time_s": best["compare_time"],
        "robdd_equiv_compare_repeat": repeat,
        "robdd_equiv_compare_per_call_time_s": float(best["compare_time"]) / repeat,
        "robdd_equiv_total_time_s": best["total"],
        "robdd_equiv_result": result,
        "robdd_equiv_ok": (result == bool(expected)) if expected is not None else None,
        "robdd_equiv_status": "ok",
        "robdd_equiv_error": None,
        "robdd_equiv_nodes_f": best["nodes_f"],
        "robdd_equiv_nodes_g": best["nodes_g"],
        "robdd_equiv_nodes_manager": best["nodes_manager"],
        "robdd_equiv_backend": "dd.cudd" if ident.get("is_cudd") else ("dd.autoref" if ident.get("is_autoref") else ident.get("module")),
        "robdd_equiv_backend_module": ident.get("module"),
        "robdd_equiv_backend_class": ident.get("class"),
        "robdd_equiv_backend_preference": backend,
        "robdd_equiv_order_policy": order_policy,
        "robdd_equiv_order_seed": order_seed,
        "robdd_equiv_order_sweeps": sweeps,
        "robdd_equiv_order_used": compact_order_repr(best["order"]),
        "robdd_equiv_reorder_requested": reorder_result.get("robdd_dynamic_reordering_requested", False),
        "robdd_equiv_reorder_used": reorder_result.get("robdd_dynamic_reordering_used", False),
        "robdd_equiv_reorder_method": reorder_result.get("robdd_reorder_method", reorder_method),
    }
