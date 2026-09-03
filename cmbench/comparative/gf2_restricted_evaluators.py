"""Development-only exact restricted evaluators for the post-C36 A/B study.

R0 preserves the gate-by-gate behavior of C36's occurrence-recursive helper,
with environment construction split out so setup and evaluation can be timed
separately.  R1 adds a query-local identity memo.  R2 executes the validated
serialized-DAG-v2 node table in topological order and releases a slot after
its final use.

None of these helpers is a production router or a C37 confirmation policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from typing import Any

from bitset_backend import build_bitset_env
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor


RESTRICTED_METHODS = (
    "restricted_r0_occurrence",
    "restricted_r1_identity_memo",
    "restricted_r2_topological_liveness",
)

_BINARY_TYPES = (And, Or, Xor, Imp, Eqv)
_OPS = frozenset(("var", "not", "and", "or", "xor", "imp", "eqv"))


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class PreparedRestriction:
    """One query's fixed values and packed residual-variable environment."""

    fixed: Mapping[str, int]
    remaining: tuple[str, ...]
    environment: Mapping[str, int]
    full_mask: int


@dataclass(frozen=True)
class RestrictedArena:
    """Compact topological slot arena compiled directly from DAG-v2 JSON."""

    opcodes: tuple[str, ...]
    child_a: tuple[int, ...]
    child_b: tuple[int, ...]
    variable_names: tuple[str | None, ...]
    use_counts: tuple[int, ...]
    root: int

    @property
    def node_count(self) -> int:
        return len(self.opcodes)


def prepare_restriction(
    fixed: Mapping[str, int], remaining: Sequence[str],
) -> PreparedRestriction:
    normalized_fixed = dict(fixed)
    normalized_remaining = tuple(remaining)
    _require(
        normalized_fixed
        and normalized_remaining
        and set(normalized_fixed).isdisjoint(normalized_remaining)
        and all(type(value) is int and value in (0, 1)
                for value in normalized_fixed.values()),
        "invalid restricted evaluator assignment",
    )
    environment = build_bitset_env(normalized_remaining)
    full_mask = (1 << (1 << len(normalized_remaining))) - 1
    return PreparedRestriction(
        fixed=normalized_fixed,
        remaining=normalized_remaining,
        environment=environment,
        full_mask=full_mask,
    )


def _variable_value(name: str, prepared: PreparedRestriction) -> int:
    if name in prepared.fixed:
        return prepared.full_mask if prepared.fixed[name] else 0
    try:
        return int(prepared.environment[name])
    except KeyError as exc:
        raise KeyError(f"missing live/fixed value for variable {name!r}") from exc


def _apply_unary(opcode: str, value: int, full_mask: int) -> int:
    if opcode == "not":
        return (~value) & full_mask
    raise ValueError(f"unknown restricted unary opcode: {opcode!r}")


def _apply_binary(opcode: str, left: int, right: int, full_mask: int) -> int:
    if opcode == "and":
        return left & right
    if opcode == "or":
        return left | right
    if opcode == "xor":
        return left ^ right
    if opcode == "imp":
        return ((~left) | right) & full_mask
    if opcode == "eqv":
        return (~(left ^ right)) & full_mask
    raise ValueError(f"unknown restricted binary opcode: {opcode!r}")


def eval_restricted_r0(expr: Expr, prepared: PreparedRestriction) -> int:
    """Occurrence-recursive C36 control, with setup supplied by the caller."""

    def rec(node: Expr) -> int:
        if isinstance(node, Var):
            return _variable_value(f"x{node.i}", prepared)
        if isinstance(node, Not):
            return (~rec(node.a)) & prepared.full_mask
        left, right = rec(node.a), rec(node.b)
        if isinstance(node, And):
            return left & right
        if isinstance(node, Or):
            return left | right
        if isinstance(node, Xor):
            return left ^ right
        if isinstance(node, Imp):
            return ((~left) | right) & prepared.full_mask
        if isinstance(node, Eqv):
            return (~(left ^ right)) & prepared.full_mask
        raise TypeError(node)

    return rec(expr)


def eval_restricted_r1(expr: Expr, prepared: PreparedRestriction) -> int:
    """Evaluate every reachable Expr object identity once for this query."""
    memo: dict[int, int] = {}

    def rec(node: Expr) -> int:
        key = id(node)
        try:
            return memo[key]
        except KeyError:
            pass
        if isinstance(node, Var):
            result = _variable_value(f"x{node.i}", prepared)
        elif isinstance(node, Not):
            result = (~rec(node.a)) & prepared.full_mask
        elif isinstance(node, _BINARY_TYPES):
            left, right = rec(node.a), rec(node.b)
            if isinstance(node, And):
                result = left & right
            elif isinstance(node, Or):
                result = left | right
            elif isinstance(node, Xor):
                result = left ^ right
            elif isinstance(node, Imp):
                result = ((~left) | right) & prepared.full_mask
            else:
                result = (~(left ^ right)) & prepared.full_mask
        else:
            raise TypeError(node)
        memo[key] = result
        return result

    return rec(expr)


def compile_restricted_arena(document: Mapping[str, Any]) -> RestrictedArena:
    """Compile a validated-style DAG-v2 document without rebuilding CSE."""
    _require(isinstance(document, Mapping) and document.get("version") == 2,
             "restricted arena requires expression DAG v2")
    nodes = document.get("nodes")
    root = document.get("root")
    _require(isinstance(nodes, list) and nodes, "restricted arena nodes")
    _require(type(root) is int and root == len(nodes) - 1,
             "restricted arena requires reachable topological root")
    opcodes: list[str] = []
    child_a: list[int] = []
    child_b: list[int] = []
    variable_names: list[str | None] = []
    use_counts = [0] * len(nodes)
    for index, node in enumerate(nodes):
        _require(isinstance(node, Mapping), f"restricted arena node {index}")
        opcode = str(node.get("op", "")).lower()
        _require(opcode in _OPS, f"restricted arena opcode {opcode!r}")
        if opcode == "var":
            variable = node.get("i")
            _require(type(variable) is int and variable >= 0,
                     f"restricted arena variable at {index}")
            a = b = -1
            variable_name: str | None = f"x{variable}"
        else:
            a = node.get("a")
            _require(type(a) is int and 0 <= a < index,
                     f"restricted arena child a at {index}")
            use_counts[a] += 1
            if opcode == "not":
                b = -1
            else:
                b = node.get("b")
                _require(type(b) is int and 0 <= b < index,
                         f"restricted arena child b at {index}")
                use_counts[b] += 1
            variable_name = None
        opcodes.append(opcode)
        child_a.append(a)
        child_b.append(b)
        variable_names.append(variable_name)
    return RestrictedArena(
        opcodes=tuple(opcodes),
        child_a=tuple(child_a),
        child_b=tuple(child_b),
        variable_names=tuple(variable_names),
        use_counts=tuple(use_counts),
        root=root,
    )


def eval_restricted_r2(arena: RestrictedArena, prepared: PreparedRestriction) -> int:
    """Execute a topological arena and release inputs at their final use."""
    values: list[int | None] = [None] * arena.node_count
    remaining_uses = list(arena.use_counts)
    for slot, opcode in enumerate(arena.opcodes):
        if opcode == "var":
            name = arena.variable_names[slot]
            if name is None:
                raise AssertionError("variable slot missing name")
            result = _variable_value(name, prepared)
        else:
            a_slot = arena.child_a[slot]
            a_value = values[a_slot]
            if a_value is None:
                raise AssertionError("restricted arena released a live operand")
            if opcode == "not":
                result = _apply_unary(opcode, a_value, prepared.full_mask)
                children = (a_slot,)
            else:
                b_slot = arena.child_b[slot]
                b_value = values[b_slot]
                if b_value is None:
                    raise AssertionError("restricted arena released a live operand")
                result = _apply_binary(opcode, a_value, b_value, prepared.full_mask)
                children = (a_slot, b_slot)
        values[slot] = result
        if opcode != "var":
            for child in children:
                remaining_uses[child] -= 1
                if remaining_uses[child] == 0 and child != arena.root:
                    values[child] = None
    result = values[arena.root]
    if result is None:
        raise AssertionError("restricted arena released its root")
    return int(result)


def arena_structural_profile(arena: RestrictedArena) -> dict[str, Any]:
    """Return exact unique, unfolded, gate, edge, depth, and liveness counts."""
    multiplicity = [0] * arena.node_count
    multiplicity[arena.root] = 1
    for slot in range(arena.root, -1, -1):
        count = multiplicity[slot]
        opcode = arena.opcodes[slot]
        if opcode == "var":
            continue
        multiplicity[arena.child_a[slot]] += count
        if opcode != "not":
            multiplicity[arena.child_b[slot]] += count
    unique_nodes = arena.node_count
    unique_gates = sum(opcode != "var" for opcode in arena.opcodes)
    unfolded_visits = sum(multiplicity)
    unfolded_gate_evaluations = sum(
        multiplicity[slot]
        for slot, opcode in enumerate(arena.opcodes)
        if opcode != "var"
    )
    unique_child_edges = sum(
        0 if opcode == "var" else (1 if opcode == "not" else 2)
        for opcode in arena.opcodes
    )
    depth = [1] * arena.node_count
    for slot, opcode in enumerate(arena.opcodes):
        if opcode == "not":
            depth[slot] = depth[arena.child_a[slot]] + 1
        elif opcode != "var":
            depth[slot] = max(depth[arena.child_a[slot]], depth[arena.child_b[slot]]) + 1

    remaining_uses = list(arena.use_counts)
    live = peak_live = 0
    for slot, opcode in enumerate(arena.opcodes):
        live += 1
        peak_live = max(peak_live, live)
        if opcode == "var":
            continue
        children = (arena.child_a[slot],) if opcode == "not" else (
            arena.child_a[slot], arena.child_b[slot])
        for child in children:
            remaining_uses[child] -= 1
            if remaining_uses[child] == 0 and child != arena.root:
                live -= 1
    return {
        "unique_nodes": unique_nodes,
        "unique_gates": unique_gates,
        "unique_child_edges": unique_child_edges,
        "unfolded_visits": unfolded_visits,
        "unfolded_gate_evaluations": unfolded_gate_evaluations,
        "unfolded_child_edge_visits": max(0, unfolded_visits - 1),
        "expansion_ratio_numerator": unfolded_visits,
        "expansion_ratio_denominator": unique_nodes,
        "max_depth": max(depth),
        "r1_retained_result_slots": unique_nodes,
        "r2_peak_live_result_slots": peak_live,
    }


def method_work_counters(method: str, profile: Mapping[str, Any]) -> dict[str, int]:
    """Deterministic complexity counters, independent of wall-clock timing."""
    if method == RESTRICTED_METHODS[0]:
        return {
            "node_evaluations": int(profile["unfolded_visits"]),
            "primitive_gate_evaluations": int(profile["unfolded_gate_evaluations"]),
            "child_edge_visits": int(profile["unfolded_child_edge_visits"]),
            "retained_result_slots": 0,
            "peak_live_result_slots": 0,
        }
    if method == RESTRICTED_METHODS[1]:
        return {
            "node_evaluations": int(profile["unique_nodes"]),
            "primitive_gate_evaluations": int(profile["unique_gates"]),
            "child_edge_visits": int(profile["unique_child_edges"]),
            "retained_result_slots": int(profile["r1_retained_result_slots"]),
            "peak_live_result_slots": int(profile["r1_retained_result_slots"]),
        }
    if method == RESTRICTED_METHODS[2]:
        return {
            "node_evaluations": int(profile["unique_nodes"]),
            "primitive_gate_evaluations": int(profile["unique_gates"]),
            "child_edge_visits": int(profile["unique_child_edges"]),
            "retained_result_slots": 0,
            "peak_live_result_slots": int(profile["r2_peak_live_result_slots"]),
        }
    raise ValueError(f"unknown restricted evaluator: {method!r}")
