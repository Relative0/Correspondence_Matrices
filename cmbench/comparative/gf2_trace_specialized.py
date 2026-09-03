"""Exact trace-specialized restriction compilation for repeated queries.

Each query symbolically restricts a validated DAG-v2 source.  Restriction
results are cached by the fixed values that are relevant to each source node,
and structurally identical restricted nodes are interned across queries with
the same residual-variable order.  Every residual-order group is then
evaluated once as a multi-root packed-bit arena.

This module is a development backend.  It does not select or promote a
production policy.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from bitset_backend import build_bitset_env

from .gf2_restricted_evaluators import RestrictedArena, compile_restricted_arena


_COMMUTATIVE = frozenset(("and", "or", "xor", "eqv"))


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class TraceArena:
    opcodes: tuple[str, ...]
    child_a: tuple[int, ...]
    child_b: tuple[int, ...]
    variable_names: tuple[str | None, ...]
    constants: tuple[int | None, ...]
    use_counts: tuple[int, ...]
    roots: tuple[int, ...]

    @property
    def node_count(self) -> int:
        return len(self.opcodes)


@dataclass(frozen=True)
class TraceGroup:
    remaining: tuple[str, ...]
    query_indices: tuple[int, ...]
    arena: TraceArena
    restriction_cache_entries: int
    distinct_restriction_signatures: int


@dataclass(frozen=True)
class TraceSpecializedPlan:
    source_node_count: int
    query_count: int
    groups: tuple[TraceGroup, ...]


class _ArenaBuilder:
    def __init__(self) -> None:
        self.opcodes: list[str] = []
        self.child_a: list[int] = []
        self.child_b: list[int] = []
        self.variable_names: list[str | None] = []
        self.constants: list[int | None] = []
        self.interned: dict[tuple[Any, ...], int] = {}

    def intern(self, opcode: str, a: int = -1, b: int = -1,
               *, variable: str | None = None, constant: int | None = None) -> int:
        if opcode in _COMMUTATIVE and b < a:
            a, b = b, a
        key = (opcode, a, b, variable, constant)
        existing = self.interned.get(key)
        if existing is not None:
            return existing
        slot = len(self.opcodes)
        self.interned[key] = slot
        self.opcodes.append(opcode)
        self.child_a.append(a)
        self.child_b.append(b)
        self.variable_names.append(variable)
        self.constants.append(constant)
        return slot

    def constant(self, value: int) -> int:
        return self.intern("const", constant=value)

    def variable(self, name: str) -> int:
        return self.intern("var", variable=name)

    def unary_not(self, value: int) -> int:
        opcode = self.opcodes[value]
        if opcode == "const":
            constant = self.constants[value]
            if constant is None:
                raise AssertionError("constant slot missing value")
            return self.constant(1 - constant)
        if opcode == "not":
            return self.child_a[value]
        return self.intern("not", value)

    def binary(self, opcode: str, left: int, right: int) -> int:
        left_constant = self.constants[left] if self.opcodes[left] == "const" else None
        right_constant = self.constants[right] if self.opcodes[right] == "const" else None
        if left_constant is not None and right_constant is not None:
            if opcode == "and":
                result = left_constant & right_constant
            elif opcode == "or":
                result = left_constant | right_constant
            elif opcode == "xor":
                result = left_constant ^ right_constant
            elif opcode == "imp":
                result = (1 - left_constant) | right_constant
            elif opcode == "eqv":
                result = 1 - (left_constant ^ right_constant)
            else:
                raise ValueError(f"unknown trace opcode: {opcode!r}")
            return self.constant(result)
        if left == right:
            return self.constant(1 if opcode in ("imp", "eqv") else 0) \
                if opcode == "xor" or opcode in ("imp", "eqv") else left
        if opcode == "and":
            if left_constant == 0 or right_constant == 0:
                return self.constant(0)
            if left_constant == 1:
                return right
            if right_constant == 1:
                return left
        elif opcode == "or":
            if left_constant == 1 or right_constant == 1:
                return self.constant(1)
            if left_constant == 0:
                return right
            if right_constant == 0:
                return left
        elif opcode == "xor":
            if left_constant == 0:
                return right
            if right_constant == 0:
                return left
            if left_constant == 1:
                return self.unary_not(right)
            if right_constant == 1:
                return self.unary_not(left)
        elif opcode == "imp":
            if left_constant == 0 or right_constant == 1:
                return self.constant(1)
            if left_constant == 1:
                return right
            if right_constant == 0:
                return self.unary_not(left)
        elif opcode == "eqv":
            if left_constant == 0:
                return self.unary_not(right)
            if right_constant == 0:
                return self.unary_not(left)
            if left_constant == 1:
                return right
            if right_constant == 1:
                return left
        else:
            raise ValueError(f"unknown trace opcode: {opcode!r}")
        return self.intern(opcode, left, right)

    def finish(self, roots: Sequence[int]) -> TraceArena:
        normalized_roots = tuple(roots)
        _require(normalized_roots, "trace arena roots")
        use_counts = [0] * len(self.opcodes)
        for opcode, left, right in zip(
            self.opcodes, self.child_a, self.child_b, strict=True
        ):
            if opcode in ("const", "var"):
                continue
            use_counts[left] += 1
            if opcode != "not":
                use_counts[right] += 1
        for root in normalized_roots:
            use_counts[root] += 1
        return TraceArena(
            opcodes=tuple(self.opcodes),
            child_a=tuple(self.child_a),
            child_b=tuple(self.child_b),
            variable_names=tuple(self.variable_names),
            constants=tuple(self.constants),
            use_counts=tuple(use_counts),
            roots=normalized_roots,
        )


def _support_masks(source: RestrictedArena) -> tuple[int, ...]:
    supports: list[int] = []
    for slot, opcode in enumerate(source.opcodes):
        if opcode == "var":
            name = source.variable_names[slot]
            if name is None:
                raise AssertionError("source variable missing name")
            support = 1 << int(name[1:])
        elif opcode == "not":
            support = supports[source.child_a[slot]]
        else:
            support = supports[source.child_a[slot]] | supports[source.child_b[slot]]
        supports.append(support)
    return tuple(supports)


def _query_assignment(query: Mapping[str, Any], n_vars: int) -> tuple[int, int, tuple[str, ...]]:
    fixed_rows = query.get("fixed")
    remaining_rows = query.get("remaining_order")
    _require(isinstance(fixed_rows, list) and isinstance(remaining_rows, list),
             "trace query fields")
    fixed_mask = value_mask = 0
    for row in fixed_rows:
        name = row.get("variable") if isinstance(row, Mapping) else None
        value = row.get("value") if isinstance(row, Mapping) else None
        _require(isinstance(name, str) and name.startswith("x")
                 and type(value) is int and value in (0, 1), "trace fixed value")
        variable = int(name[1:])
        _require(0 <= variable < n_vars and not (fixed_mask & (1 << variable)),
                 "trace fixed variable")
        fixed_mask |= 1 << variable
        value_mask |= value << variable
    remaining = tuple(remaining_rows)
    remaining_mask = sum(1 << int(name[1:]) for name in remaining)
    _require(fixed_mask and remaining and fixed_mask & remaining_mask == 0
             and fixed_mask | remaining_mask == (1 << n_vars) - 1,
             "trace query partition")
    return fixed_mask, value_mask, remaining


def compile_trace_specialized(
    document: Mapping[str, Any], trace: Sequence[Mapping[str, Any]], n_vars: int,
) -> TraceSpecializedPlan:
    """Compile a query trace to residual-order-grouped, shared multi-root arenas."""
    _require(1 <= n_vars <= 24 and 1 <= len(trace) <= 4096,
             "trace specialization bounds")
    source = compile_restricted_arena(document)
    supports = _support_masks(source)
    query_data = [_query_assignment(query, n_vars) for query in trace]
    grouped: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for index, (_fixed, _values, remaining) in enumerate(query_data):
        grouped[remaining].append(index)

    groups: list[TraceGroup] = []
    for remaining, query_indices in grouped.items():
        builder = _ArenaBuilder()
        restricted_cache: dict[tuple[int, int, int], int] = {}

        def restrict(slot: int, fixed_mask: int, value_mask: int) -> int:
            relevant = fixed_mask & supports[slot]
            key = (slot, relevant, value_mask & relevant)
            cached = restricted_cache.get(key)
            if cached is not None:
                return cached
            opcode = source.opcodes[slot]
            if opcode == "var":
                name = source.variable_names[slot]
                if name is None:
                    raise AssertionError("source variable missing name")
                variable = int(name[1:])
                result = (builder.constant((value_mask >> variable) & 1)
                          if fixed_mask & (1 << variable)
                          else builder.variable(name))
            elif opcode == "not":
                result = builder.unary_not(
                    restrict(source.child_a[slot], fixed_mask, value_mask))
            else:
                left = restrict(source.child_a[slot], fixed_mask, value_mask)
                right = restrict(source.child_b[slot], fixed_mask, value_mask)
                result = builder.binary(opcode, left, right)
            restricted_cache[key] = result
            return result

        roots = []
        for index in query_indices:
            fixed_mask, value_mask, _remaining = query_data[index]
            roots.append(restrict(source.root, fixed_mask, value_mask))
        arena = builder.finish(roots)
        groups.append(TraceGroup(
            remaining=remaining,
            query_indices=tuple(query_indices),
            arena=arena,
            restriction_cache_entries=len(restricted_cache),
            distinct_restriction_signatures=len(set(restricted_cache)),
        ))
    return TraceSpecializedPlan(
        source_node_count=source.node_count,
        query_count=len(trace),
        groups=tuple(groups),
    )


def _apply(opcode: str, left: int, right: int | None, full_mask: int) -> int:
    if opcode == "not":
        return (~left) & full_mask
    if right is None:
        raise AssertionError("binary trace node missing right operand")
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
    raise ValueError(f"unknown trace opcode: {opcode!r}")


def evaluate_trace_arena(arena: TraceArena, remaining: Sequence[str]) -> tuple[int, ...]:
    names = tuple(remaining)
    environment = build_bitset_env(names)
    full_mask = (1 << (1 << len(names))) - 1
    values: list[int | None] = [None] * arena.node_count
    remaining_uses = list(arena.use_counts)
    for slot, opcode in enumerate(arena.opcodes):
        if opcode == "const":
            constant = arena.constants[slot]
            if constant is None:
                raise AssertionError("trace constant missing value")
            value = full_mask if constant else 0
        elif opcode == "var":
            name = arena.variable_names[slot]
            if name is None or name not in environment:
                raise AssertionError("trace variable outside residual order")
            value = int(environment[name])
        else:
            left_slot = arena.child_a[slot]
            left = values[left_slot]
            if left is None:
                raise AssertionError("trace arena released live left operand")
            right_slot = arena.child_b[slot]
            right = None if opcode == "not" else values[right_slot]
            if opcode != "not" and right is None:
                raise AssertionError("trace arena released live right operand")
            value = _apply(opcode, left, right, full_mask)
            for child in ((left_slot,) if opcode == "not" else (left_slot, right_slot)):
                remaining_uses[child] -= 1
                if remaining_uses[child] == 0:
                    values[child] = None
        values[slot] = value
    outputs = []
    for root in arena.roots:
        value = values[root]
        if value is None:
            raise AssertionError("trace arena released output root")
        outputs.append(int(value))
        remaining_uses[root] -= 1
        if remaining_uses[root] == 0:
            values[root] = None
    return tuple(outputs)


def evaluate_trace_specialized(plan: TraceSpecializedPlan) -> tuple[int, ...]:
    outputs: list[int | None] = [None] * plan.query_count
    for group in plan.groups:
        values = evaluate_trace_arena(group.arena, group.remaining)
        for index, value in zip(group.query_indices, values, strict=True):
            outputs[index] = value
    if any(value is None for value in outputs):
        raise AssertionError("trace specialization omitted a query")
    return tuple(int(value) for value in outputs if value is not None)


def trace_plan_metrics(plan: TraceSpecializedPlan) -> dict[str, int]:
    return {
        "source_nodes": plan.source_node_count,
        "queries": plan.query_count,
        "residual_order_groups": len(plan.groups),
        "specialized_nodes": sum(group.arena.node_count for group in plan.groups),
        "specialized_roots": sum(len(group.arena.roots) for group in plan.groups),
        "unique_specialized_roots": sum(len(set(group.arena.roots)) for group in plan.groups),
        "restriction_cache_entries": sum(
            group.restriction_cache_entries for group in plan.groups),
        "distinct_restriction_signatures": sum(
            group.distinct_restriction_signatures for group in plan.groups),
    }
