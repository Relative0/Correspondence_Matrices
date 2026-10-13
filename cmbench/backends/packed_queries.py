"""Explicit count and streaming contracts using the existing exact flat engine.

These plans do not alter global dispatch, named masks or bound-program caches.
Plans reuse compiled structure; per-query bindings are released after execution.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass

from bitset_backend import (
    FlatProgram, PreparedFlatEvaluation, _FLAT_OP_AND, compile_expr_cse,
    compile_flat,
)
from cmbench.backends.packed_mask_cache import PackedMaskCache, ordered_basis


def _fixed(basis: tuple[str, ...], values: Mapping[str, int] | None) -> dict[str, int]:
    result = dict(values or {})
    if any(name not in basis for name in result):
        raise ValueError("fixed variable is outside the declared basis")
    if any(type(value) not in (int, bool) or value not in (0, 1)
           for value in result.values()):
        raise ValueError("fixed values must be Boolean 0 or 1")
    return result


def _validate_program(program: FlatProgram, basis: tuple[str, ...]) -> None:
    if not set(program.load_vars).issubset(basis):
        raise ValueError("declared basis omits expression variables")


def _execute(program: FlatProgram, live: tuple[str, ...], fixed: Mapping[str, int],
             cache: PackedMaskCache) -> int:
    env = cache.environment(live)  # Width is guarded before full-mask allocation.
    full_mask = (1 << (1 << len(live))) - 1
    template = [0] * program.n_slots
    for slot, kind, payload in program.loads:
        if kind == "const":
            template[slot] = full_mask if payload else 0
        elif payload in fixed:
            template[slot] = full_mask if fixed[payload] else 0
        else:
            template[slot] = env[payload]
    return PreparedFlatEvaluation(program, template, full_mask, True).evaluate()


def _slice(program: FlatProgram, roots: Sequence[int]) -> FlatProgram:
    """Copy reachable instructions, compact slots, and conjoin the given roots."""
    operations = {slot: (opcode, args) for slot, opcode, args in program.ops}
    reachable: set[int] = set()
    pending = list(roots)
    while pending:
        slot = pending.pop()
        if slot in reachable:
            continue
        reachable.add(slot)
        if slot in operations:
            pending.extend(operations[slot][1])
    remap = {old: new for new, old in enumerate(sorted(reachable))}
    loads = tuple((remap[s], kind, value) for s, kind, value in program.loads if s in reachable)
    ops = [(remap[s], code, tuple(remap[a] for a in args))
           for s, code, args in program.ops if s in reachable]
    count = len(reachable)
    root = remap[roots[0]]
    if len(roots) > 1:
        root = count
        ops.append((root, _FLAT_OP_AND, tuple(remap[s] for s in roots)))
        count += 1
    return FlatProgram(count, root, loads, tuple(ops))


class IndependentCountPlan:
    """Exact conjunction counts using components with disjoint variable support.

    Decomposition is conservative and syntactic. Shared support merges components;
    fixed assignments can reduce their live widths but do not trigger repartition.
    A component wider than ``cache.max_width`` is refused before any evaluation.
    Unused declared live axes multiply the count, and count is an arbitrary int.
    """

    def __init__(self, program: FlatProgram, names: Sequence[str], *, cache: PackedMaskCache):
        self.basis = ordered_basis(names)
        _validate_program(program, self.basis)
        self.cache = cache
        operations = {slot: (code, args) for slot, code, args in program.ops}
        leaves: list[int] = []
        pending = [program.root_slot]
        seen: set[int] = set()
        while pending:
            slot = pending.pop()
            if slot in seen:
                continue
            seen.add(slot)
            if slot in operations and operations[slot][0] == _FLAT_OP_AND:
                pending.extend(reversed(operations[slot][1]))
            else:
                leaves.append(slot)
        supports = {slot: frozenset((value,)) if kind == "var" else frozenset()
                    for slot, kind, value in program.loads}
        for slot, _code, args in program.ops:
            supports[slot] = frozenset().union(*(supports[a] for a in args))
        parents = list(range(len(leaves)))

        def find(index: int) -> int:
            while parents[index] != index:
                parents[index] = parents[parents[index]]
                index = parents[index]
            return index

        owner: dict[str, int] = {}
        for index, slot in enumerate(leaves):
            for name in supports[slot]:
                if name in owner:
                    parents[find(index)] = find(owner[name])
                else:
                    owner[name] = index
        groups: dict[int, list[int]] = {}
        for index, slot in enumerate(leaves):
            groups.setdefault(find(index), []).append(slot)
        self._components = tuple(_slice(program, roots) for roots in groups.values())
        self.component_supports = tuple(frozenset(p.load_vars) for p in self._components)
        used = frozenset().union(*self.component_supports)
        self._unused = tuple(name for name in self.basis if name not in used)

    @classmethod
    def from_expr(cls, expr, names: Sequence[str], *, cache: PackedMaskCache):
        return cls(compile_expr_cse(expr, flatten=True), names, cache=cache)

    @classmethod
    def from_cm_node(cls, node, names: Sequence[str], *, cache: PackedMaskCache):
        return cls(compile_flat(node), names, cache=cache)

    def _contexts(self, fixed: Mapping[str, int] | None):
        context = _fixed(self.basis, fixed)
        live_groups = tuple(tuple(name for name in self.basis
                                  if name in support and name not in context)
                            for support in self.component_supports)
        if any(len(live) > self.cache.max_width for live in live_groups):
            raise ValueError("component live width exceeds the configured build limit")
        return context, live_groups

    def count(self, fixed: Mapping[str, int] | None = None) -> int:
        context, live_groups = self._contexts(fixed)
        result = 1 << sum(name not in context for name in self._unused)
        for program, live in zip(self._components, live_groups):
            result *= _execute(program, live, context, self.cache).bit_count()
            if not result:
                break
        return result

    def exists(self, fixed: Mapping[str, int] | None = None) -> bool:
        context, live_groups = self._contexts(fixed)
        return all(_execute(program, live, context, self.cache) != 0
                   for program, live in zip(self._components, live_groups))


@dataclass(frozen=True)
class PackedChunk:
    """Little-endian packed assignment rows; offset and valid_bits are in bits."""

    offset: int
    valid_bits: int
    data: bytes


class PackedStreamPlan:
    """Emit a complete vector in bounded chunks, in declared remaining-axis order.

    Callers must supply a total-bit limit. Chunk workspace scales with the chosen
    width and program, never the number of chunks. Consumer retention is separate.
    Byte padding occurs only for a complete output shorter than eight bits.
    """

    def __init__(self, program: FlatProgram, names: Sequence[str], *, cache: PackedMaskCache):
        self.basis = ordered_basis(names)
        _validate_program(program, self.basis)
        self.program = program
        self.cache = cache

    @classmethod
    def from_expr(cls, expr, names: Sequence[str], *, cache: PackedMaskCache):
        return cls(compile_expr_cse(expr, flatten=True), names, cache=cache)

    @classmethod
    def from_cm_node(cls, node, names: Sequence[str], *, cache: PackedMaskCache):
        return cls(compile_flat(node), names, cache=cache)

    def iter_chunks(self, *, chunk_vars: int, max_total_bits: int,
                    fixed: Mapping[str, int] | None = None) -> Iterator[PackedChunk]:
        # This outer function is deliberately not a generator: refusal is eager.
        context = _fixed(self.basis, fixed)
        if type(chunk_vars) is not int or not 3 <= chunk_vars <= self.cache.max_width:
            raise ValueError("chunk_vars must be at least 3 and within the build limit")
        if type(max_total_bits) is not int or max_total_bits < 1:
            raise ValueError("max_total_bits must be a positive integer")
        remaining = tuple(name for name in self.basis if name not in context)
        # Compare widths before constructing even a very large integer count.
        if len(remaining) >= max_total_bits.bit_length():
            raise ValueError("complete output exceeds max_total_bits")
        total_bits = 1 << len(remaining)
        width = min(chunk_vars, len(remaining))
        prefix, suffix = remaining[:len(remaining) - width], remaining[len(remaining) - width:]
        chunk_bits = 1 << width

        def chunks() -> Iterator[PackedChunk]:
            for index in range(total_bits // chunk_bits):
                for axis, name in enumerate(prefix):
                    context[name] = (index >> (len(prefix) - axis - 1)) & 1
                bits = _execute(self.program, suffix, context, self.cache)
                yield PackedChunk(index * chunk_bits, chunk_bits,
                                  bits.to_bytes((chunk_bits + 7) // 8, "little"))

        return chunks()
