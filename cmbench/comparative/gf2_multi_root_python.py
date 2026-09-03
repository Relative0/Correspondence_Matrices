"""Exact sharing-aware Python control for related multi-root restrictions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from bitset_backend import build_bitset_env


_BINARY = frozenset({"and", "or", "xor", "imp", "eqv"})


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class PythonMultiRootArena:
    """Validated topological DAG with one or more ordered output roots."""

    nodes: tuple[tuple[str, int, int], ...]
    roots: tuple[int, ...]
    variable_count: int

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def root_count(self) -> int:
        return len(self.roots)

    def evaluate(
        self,
        fixed: Mapping[str, int],
        remaining: Sequence[str],
    ) -> tuple[int, ...]:
        remaining_order = tuple(remaining)
        _require(len(set(remaining_order)) == len(remaining_order), "duplicate remaining variable")
        _require(
            set(fixed).isdisjoint(remaining_order),
            "fixed and remaining variables overlap",
        )
        expected = {f"x{index}" for index in range(self.variable_count)}
        _require(
            set(fixed).union(remaining_order) == expected,
            "fixed and remaining variables must partition the declared universe",
        )
        _require(
            all(type(value) is int and value in (0, 1) for value in fixed.values()),
            "fixed assignment is not Boolean",
        )
        live_count = len(remaining_order)
        full_mask = (1 << (1 << live_count)) - 1
        environment = build_bitset_env(remaining_order)
        values: list[int] = []
        for opcode, a, b in self.nodes:
            if opcode == "var":
                name = f"x{a}"
                value = environment[name] if name in environment else full_mask * fixed[name]
            elif opcode == "not":
                value = (~values[a]) & full_mask
            elif opcode == "and":
                value = values[a] & values[b]
            elif opcode == "or":
                value = values[a] | values[b]
            elif opcode == "xor":
                value = values[a] ^ values[b]
            elif opcode == "imp":
                value = ((~values[a]) | values[b]) & full_mask
            elif opcode == "eqv":
                value = (~(values[a] ^ values[b])) & full_mask
            else:  # pragma: no cover - compilation rejects this path
                raise AssertionError(opcode)
            values.append(value)
        return tuple(values[root] for root in self.roots)


def compile_python_multi_root_arena(
    document: Mapping[str, Any],
    *,
    variable_count: int,
) -> PythonMultiRootArena:
    """Compile a strict v2 single- or multi-root JSON DAG without native code."""
    _require(type(variable_count) is int and 0 <= variable_count <= 24, "variable count")
    _require(isinstance(document, Mapping), "multi-root document")
    _require(document.get("version") == 2, "multi-root document version")
    raw_nodes = document.get("nodes")
    _require(isinstance(raw_nodes, list) and raw_nodes, "nonempty node list required")
    has_root = "root" in document
    has_roots = "roots" in document
    _require(has_root != has_roots, "document must contain root xor roots")
    raw_roots = [document["root"]] if has_root else document["roots"]
    _require(
        isinstance(raw_roots, list) and raw_roots,
        "nonempty ordered roots required",
    )

    nodes: list[tuple[str, int, int]] = []
    for index, row in enumerate(raw_nodes):
        _require(isinstance(row, Mapping), "node must be an object")
        opcode = row.get("op")
        if opcode == "var":
            _require(set(row) == {"op", "i"}, "variable node fields")
            variable = row["i"]
            _require(
                type(variable) is int and 0 <= variable < variable_count,
                "variable index outside universe",
            )
            nodes.append(("var", variable, -1))
        elif opcode == "not":
            _require(set(row) == {"op", "a"}, "not node fields")
            child = row["a"]
            _require(type(child) is int and 0 <= child < index, "not child order")
            nodes.append(("not", child, -1))
        elif opcode in _BINARY:
            _require(set(row) == {"op", "a", "b"}, "binary node fields")
            a, b = row["a"], row["b"]
            _require(
                type(a) is int
                and type(b) is int
                and 0 <= a < index
                and 0 <= b < index,
                "binary child order",
            )
            nodes.append((opcode, a, b))
        else:
            raise ValueError("unknown multi-root opcode")
    roots = tuple(raw_roots)
    _require(
        all(type(root) is int and 0 <= root < len(nodes) for root in roots),
        "root outside node table",
    )
    _require(len(set(roots)) == len(roots), "duplicate output root")
    return PythonMultiRootArena(tuple(nodes), roots, variable_count)


def evaluate_separate_python_roots(
    documents: Sequence[Mapping[str, Any]],
    *,
    variable_count: int,
    fixed: Mapping[str, int],
    remaining: Sequence[str],
) -> tuple[int, ...]:
    """Evaluate separately compiled roots under the same exact restriction."""
    _require(len(documents) >= 2, "separate-root control requires at least two roots")
    arenas = tuple(
        compile_python_multi_root_arena(document, variable_count=variable_count)
        for document in documents
    )
    _require(all(arena.root_count == 1 for arena in arenas), "single-root document required")
    return tuple(
        arena.evaluate(fixed, remaining)[0]
        for arena in arenas
    )
