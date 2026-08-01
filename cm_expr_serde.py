"""Expression serialization.

Two schemas are supported:

- **v1 (tree)** — the historical recursive ``{"op": ..., "a": {...}}`` form.
  It remains fully supported for reading and writing, but it *cannot preserve
  sharing*: a DAG serialized as a tree is expanded into one subtree per
  reference, and deserialization allocates distinct objects per occurrence.
- **v2 (defs/ref DAG)** — ``{"version": 2, "nodes": [...], "root": i}`` where
  each node's child fields are integer indices into ``nodes``. References must
  point strictly backwards (``ref < index``), which makes cycles
  unrepresentable and gives O(n) validation. Serialization is deterministic
  (iterative postorder, structural dedup), so equal expressions produce equal
  documents. Use :func:`expr_to_json_dag` to write and :func:`expr_from_json`
  (auto-detecting) to read.

Deserialization constructs only ``cm_exprlib`` dataclasses from validated
fields — no code execution, no attribute-driven construction.
"""
from __future__ import annotations

from typing import Any, List, Mapping, Tuple

from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor


_BIN_OPS = {
    "and": And,
    "or": Or,
    "xor": Xor,
    "imp": Imp,
    "eqv": Eqv,
}

EXPR_SCHEMA_VERSION_DAG = 2


def expr_to_json(expr: Expr) -> dict[str, Any]:
    """Serialize to the v1 tree schema (compatibility form; loses sharing).

    Iterative (2026-08-02 Phase A2) so deep expressions cannot raise
    RecursionError here. Shared subexpressions are emitted as aliased dict
    objects, which serialize to identical (expanded) JSON text. Note that
    ``json.dumps`` itself still recurses; very deep documents should use the
    v2 defs/ref schema (:func:`expr_to_json_dag`).
    """
    memo: dict[int, dict[str, Any]] = {}
    stack: list[tuple[Expr, bool]] = [(expr, False)]
    while stack:
        e, processed = stack.pop()
        if id(e) in memo:
            continue
        if not processed:
            stack.append((e, True))
            if isinstance(e, Var):
                pass
            elif isinstance(e, Not):
                stack.append((e.a, False))
            elif isinstance(e, tuple(_BIN_OPS.values())):
                stack.append((e.b, False))
                stack.append((e.a, False))
            else:
                raise TypeError(f"unsupported expression node: {e!r}")
            continue
        if isinstance(e, Var):
            memo[id(e)] = {"op": "var", "i": int(e.i)}
        elif isinstance(e, Not):
            memo[id(e)] = {"op": "not", "a": memo[id(e.a)]}
        else:
            for op_name, cls in _BIN_OPS.items():
                if isinstance(e, cls):
                    memo[id(e)] = {"op": op_name, "a": memo[id(e.a)], "b": memo[id(e.b)]}
                    break
    return memo[id(expr)]


def expr_to_json_dag(expr: Expr) -> dict[str, Any]:
    """Serialize to the v2 defs/ref schema, preserving (and maximizing) sharing.

    Structurally equal subexpressions are emitted once regardless of object
    identity, so the document is deterministic for a given expression value
    and contains no duplicate definitions. Iterative — safe for DAGs whose
    tree unfolding or depth would break recursion.
    """
    nodes: List[dict[str, Any]] = []
    index_by_structure: dict[Tuple[object, ...], int] = {}
    index_by_id: dict[int, int] = {}
    # Keep every visited Expr alive for the duration of this call so ids in
    # index_by_id cannot be recycled.
    alive: List[Expr] = []

    stack: List[Tuple[Expr, bool]] = [(expr, False)]
    scheduled: set = set()
    while stack:
        e, processed = stack.pop()
        if processed:
            if isinstance(e, Var):
                entry: dict[str, Any] = {"op": "var", "i": int(e.i)}
                skey: Tuple[object, ...] = ("var", int(e.i))
            elif isinstance(e, Not):
                a = index_by_id[id(e.a)]
                entry = {"op": "not", "a": a}
                skey = ("not", a)
            else:
                for op_name, cls in _BIN_OPS.items():
                    if isinstance(e, cls):
                        break
                else:
                    raise TypeError(f"unsupported expression node: {e!r}")
                a = index_by_id[id(e.a)]
                b = index_by_id[id(e.b)]
                entry = {"op": op_name, "a": a, "b": b}
                skey = (op_name, a, b)
            idx = index_by_structure.get(skey)
            if idx is None:
                idx = len(nodes)
                nodes.append(entry)
                index_by_structure[skey] = idx
            index_by_id[id(e)] = idx
            continue
        if id(e) in scheduled:
            continue
        scheduled.add(id(e))
        alive.append(e)
        stack.append((e, True))
        if isinstance(e, Var):
            pass
        elif isinstance(e, Not):
            stack.append((e.a, False))
        elif isinstance(e, (And, Or, Xor, Imp, Eqv)):
            stack.append((e.b, False))
            stack.append((e.a, False))
        else:
            raise TypeError(f"unsupported expression node: {e!r}")
    return {
        "version": EXPR_SCHEMA_VERSION_DAG,
        "nodes": nodes,
        "root": index_by_id[id(expr)],
    }


def expr_from_json(data: Mapping[str, Any]) -> Expr:
    """Deserialize either schema. v2 is detected by its ``version`` field;
    documents without one are treated as v1 trees."""
    if not isinstance(data, Mapping):
        raise ValueError("expression document must be an object")
    if "version" in data:
        version = data.get("version")
        if version == EXPR_SCHEMA_VERSION_DAG:
            return _expr_from_json_dag(data)
        raise ValueError(f"unsupported expression schema version: {version!r}")
    return _expr_from_json_tree(data)


def _expr_from_json_tree(data: Mapping[str, Any]) -> Expr:
    """Iterative v1 tree deserializer (2026-08-02 Phase A2).

    Depth is bounded only by memory, never by the interpreter recursion
    limit; adversarially deep or malformed documents fail with ValueError.
    Aliased sub-documents deserialize once and produce shared Expr objects
    (a superset of the old behavior, which could never observe aliasing
    from ``json.loads`` output).
    """
    built: dict[int, Expr] = {}
    stack: list[tuple[Mapping[str, Any], bool]] = [(_expect_mapping(data, "root"), False)]
    while stack:
        node, processed = stack.pop()
        if id(node) in built:
            continue
        op = str(node.get("op", "")).lower()
        if not processed:
            stack.append((node, True))
            if op == "var":
                pass
            elif op == "not":
                stack.append((_expect_mapping(node.get("a"), "a"), False))
            elif op in _BIN_OPS:
                stack.append((_expect_mapping(node.get("b"), "b"), False))
                stack.append((_expect_mapping(node.get("a"), "a"), False))
            else:
                raise ValueError(f"unsupported expression op: {op!r}")
            continue
        if op == "var":
            built[id(node)] = Var(int(node["i"]))
        elif op == "not":
            built[id(node)] = Not(built[id(node["a"])])
        else:
            built[id(node)] = _BIN_OPS[op](built[id(node["a"])], built[id(node["b"])])
    return built[id(data)]


def _expr_from_json_dag(data: Mapping[str, Any]) -> Expr:
    nodes_json = data.get("nodes")
    if not isinstance(nodes_json, list) or not nodes_json:
        raise ValueError("v2 document must contain a non-empty 'nodes' list")
    built: List[Expr] = []
    seen_structure: set = set()
    for idx, entry in enumerate(nodes_json):
        if not isinstance(entry, Mapping):
            raise ValueError(f"node {idx}: definition must be an object")
        op = str(entry.get("op", "")).lower()

        def ref(field: str) -> Expr:
            value = entry.get(field)
            # bool is an int subclass; reject it explicitly.
            if not isinstance(value, int) or isinstance(value, bool) or not (0 <= value < idx):
                raise ValueError(
                    f"node {idx}: ref {field}={value!r} must be an integer in [0, {idx}) "
                    "(forward, self, and dangling references are rejected; "
                    "cycles are unrepresentable)"
                )
            return built[value]

        if op == "var":
            i = entry.get("i")
            if not isinstance(i, int) or isinstance(i, bool) or i < 0:
                raise ValueError(f"node {idx}: var index i={i!r} must be a non-negative integer")
            built.append(Var(i))
            skey: Tuple[object, ...] = ("var", i)
        elif op == "not":
            built.append(Not(ref("a")))
            skey = ("not", entry.get("a"))
        elif op in _BIN_OPS:
            built.append(_BIN_OPS[op](ref("a"), ref("b")))
            skey = (op, entry.get("a"), entry.get("b"))
        else:
            raise ValueError(f"node {idx}: unsupported expression op: {op!r}")
        if skey in seen_structure:
            raise ValueError(f"node {idx}: duplicate definition {skey!r} (documents must be deduplicated)")
        seen_structure.add(skey)
    root = data.get("root")
    if not isinstance(root, int) or isinstance(root, bool) or not (0 <= root < len(built)):
        raise ValueError(f"root={root!r} out of range [0, {len(built)})")
    return built[root]


def _expect_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"expression field {field!r} must be an object")
    return value
