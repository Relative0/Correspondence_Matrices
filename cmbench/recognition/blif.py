"""Bounded parser and exact oracle for combinational single-model BLIF netlists."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from bitset_backend import build_bitset_env
from cm_exprlib import And, Expr, Not, Or, Var

from .features import IneligibleExpression, postorder


MAX_BLIF_BYTES = 16_000_000
MAX_LOGICAL_LINES = 1_000_000
MAX_INPUTS = 4096
MAX_OUTPUTS = 4096
MAX_NODES = 500_000
MAX_LUT_INPUTS = 6
MAX_CUBES = 64


def _balanced(items: list[Expr], constructor) -> Expr:
    if not items:
        raise ValueError("cannot balance an empty expression")
    level = list(items)
    while len(level) > 1:
        level = [level[index] if index + 1 == len(level)
                 else constructor(level[index], level[index + 1])
                 for index in range(0, len(level), 2)]
    return level[0]


def _logical_lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    if len(raw) > MAX_BLIF_BYTES:
        raise ValueError("BLIF file exceeds the 16 MB admission bound")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("BLIF file is not UTF-8") from exc
    result: list[str] = []
    pending = ""
    for physical in text.splitlines():
        line = physical.split("#", 1)[0].strip()
        if not line:
            continue
        pending = (pending + " " + line).strip() if pending else line
        if pending.endswith("\\"):
            pending = pending[:-1].rstrip()
            continue
        result.append(pending)
        pending = ""
        if len(result) > MAX_LOGICAL_LINES:
            raise ValueError("BLIF logical-line bound exceeded")
    if pending:
        raise ValueError("unterminated BLIF line continuation")
    return result


@dataclass(frozen=True)
class BlifNode:
    name: str
    inputs: tuple[str, ...]
    cubes: tuple[str, ...]
    cube_output: int

    @property
    def local_literals(self) -> int:
        return sum(bit in "01" for cube in self.cubes for bit in cube)


@dataclass(frozen=True)
class BlifConeMetadata:
    node: str
    support: tuple[str, ...]
    source_nodes: int
    source_edges: int
    depth: int
    local_fanin: int
    local_cubes: int
    local_literals: int


@dataclass(frozen=True)
class _Reachability:
    support: frozenset[str]
    nodes: frozenset[str]
    depth: int


class BlifNetlist:
    def __init__(self, *, source: Path, model: str, inputs: tuple[str, ...],
                 outputs: tuple[str, ...], nodes: dict[str, BlifNode]):
        self.source = source
        self.model = model
        self.inputs = inputs
        self.outputs = outputs
        self.nodes = dict(nodes)
        self._input_set = frozenset(inputs)
        self._reachability: dict[str, _Reachability] = {}

    def _reaches(self, name: str, visiting: set[str] | None = None) -> _Reachability:
        cached = self._reachability.get(name)
        if cached is not None:
            return cached
        if name in self._input_set:
            value = _Reachability(frozenset((name,)), frozenset(), 0)
            self._reachability[name] = value
            return value
        node = self.nodes.get(name)
        if node is None:
            raise ValueError(f"BLIF signal has no driver: {name}")
        visiting = set() if visiting is None else visiting
        if name in visiting:
            raise ValueError("cyclic BLIF dependency")
        visiting.add(name)
        relevant = {index for cube in node.cubes for index, bit in enumerate(cube)
                    if bit in "01"}
        support: set[str] = set()
        nodes = {name}
        depth = 1
        for index, child in enumerate(node.inputs):
            if index not in relevant:
                continue
            reached = self._reaches(child, visiting)
            support.update(reached.support)
            nodes.update(reached.nodes)
            depth = max(depth, reached.depth + 1)
        visiting.remove(name)
        value = _Reachability(frozenset(support), frozenset(nodes), depth)
        self._reachability[name] = value
        return value

    def metadata(self, name: str) -> BlifConeMetadata:
        reached = self._reaches(name)
        edge_count = 0
        for node_name in reached.nodes:
            node = self.nodes[node_name]
            relevant = {index for cube in node.cubes for index, bit in enumerate(cube)
                        if bit in "01"}
            edge_count += sum(index in relevant for index in range(len(node.inputs)))
        local = self.nodes.get(name)
        if local is None:
            raise ValueError("primary input is not an eligible BLIF cone root")
        return BlifConeMetadata(name, tuple(sorted(reached.support)), len(reached.nodes),
            edge_count, reached.depth, len(local.inputs), len(local.cubes),
            local.local_literals)

    def bounded_metadata(self, name: str, *, min_support: int = 1,
                         max_support: int = 16,
                         max_source_nodes: int = 4096) -> BlifConeMetadata | None:
        """Return exact cone metadata, or ``None`` once an admission bound is exceeded.

        Unlike :meth:`metadata`, this query never constructs transitive sets for
        every intermediate node.  It is intended for deterministic primary-
        output selection in large netlists: an oversized cone is rejected after
        visiting at most ``max_source_nodes + 1`` driven nodes.
        """
        if not 1 <= min_support <= max_support <= 16:
            raise ValueError("invalid BLIF support bounds")
        if not 1 <= max_source_nodes <= 4096:
            raise ValueError("invalid BLIF source-node bound")
        local = self.nodes.get(name)
        if local is None:
            if name in self._input_set:
                return None
            raise ValueError(f"BLIF signal has no driver: {name}")

        support: set[str] = set()
        nodes: set[str] = set()
        active: set[str] = set()
        completed: set[str] = set()
        depths: dict[str, int] = {item: 0 for item in self.inputs}
        edge_count = 0
        stack: list[tuple[str, bool]] = [(name, False)]
        while stack:
            signal, expanded = stack.pop()
            if signal in self._input_set:
                support.add(signal)
                if len(support) > max_support:
                    return None
                continue
            if signal in completed:
                continue
            node = self.nodes.get(signal)
            if node is None:
                raise ValueError(f"BLIF signal has no driver: {signal}")
            relevant = tuple(child for index, child in enumerate(node.inputs)
                             if any(cube[index] in "01" for cube in node.cubes))
            if expanded:
                active.remove(signal)
                completed.add(signal)
                depths[signal] = 1 + max((depths[child] for child in relevant), default=0)
                edge_count += len(relevant)
                continue
            if signal in active:
                raise ValueError("cyclic BLIF dependency")
            active.add(signal)
            nodes.add(signal)
            if len(nodes) > max_source_nodes:
                return None
            stack.append((signal, True))
            for child in reversed(relevant):
                if child not in completed:
                    stack.append((child, False))

        if not min_support <= len(support) <= max_support or not local.cubes:
            return None
        return BlifConeMetadata(
            name, tuple(sorted(support)), len(nodes), edge_count, depths[name],
            len(local.inputs), len(local.cubes), local.local_literals,
        )

    def candidate_metadata(self, *, min_support: int = 9, max_support: int = 12,
                           max_source_nodes: int = 256) -> list[BlifConeMetadata]:
        if not 1 <= min_support <= max_support <= 16:
            raise ValueError("invalid BLIF support bounds")
        if not 1 <= max_source_nodes <= 4096:
            raise ValueError("invalid BLIF source-node bound")
        # Full transitive support sets can be quadratic on large arithmetic
        # netlists. Saturate summaries one item past the admission bounds: an
        # admitted cone remains exact, while an oversized cone stays rejected.
        support_cap, node_cap = max_support + 1, max_source_nodes + 1
        memo: dict[str, _Reachability] = {
            name: _Reachability(frozenset((name,)), frozenset(), 0)
            for name in self.inputs}

        def bounded(root: str) -> _Reachability:
            if root in memo:
                return memo[root]
            stack: list[tuple[str, bool]] = [(root, False)]
            active: set[str] = set()
            while stack:
                name, expanded = stack.pop()
                if name in memo:
                    continue
                node = self.nodes.get(name)
                if node is None:
                    raise ValueError(f"BLIF signal has no driver: {name}")
                relevant = [child for index, child in enumerate(node.inputs)
                            if any(cube[index] in "01" for cube in node.cubes)]
                if not expanded:
                    if name in active:
                        raise ValueError("cyclic BLIF dependency")
                    active.add(name)
                    stack.append((name, True))
                    for child in reversed(relevant):
                        if child not in memo:
                            stack.append((child, False))
                    continue
                support: set[str] = set()
                nodes = {name}
                depth = 1
                for child in relevant:
                    reached = memo[child]
                    support.update(reached.support)
                    nodes.update(reached.nodes)
                    depth = max(depth, reached.depth + 1)
                    if len(support) > support_cap:
                        support = set(sorted(support)[:support_cap])
                    if len(nodes) > node_cap:
                        nodes = set(sorted(nodes)[:node_cap])
                active.remove(name)
                memo[name] = _Reachability(frozenset(support), frozenset(nodes), depth)
            return memo[root]

        result = []
        for name, local in self.nodes.items():
            reached = bounded(name)
            if (not min_support <= len(reached.support) <= max_support
                    or not 1 <= len(reached.nodes) <= max_source_nodes
                    or not 1 <= len(local.cubes) <= MAX_CUBES):
                continue
            edge_count = 0
            for node_name in reached.nodes:
                node = self.nodes[node_name]
                edge_count += sum(any(cube[index] in "01" for cube in node.cubes)
                                  for index in range(len(node.inputs)))
            result.append(BlifConeMetadata(name, tuple(sorted(reached.support)),
                len(reached.nodes), edge_count, reached.depth, len(local.inputs),
                len(local.cubes), local.local_literals))
        return result

    def build_expr(self, name: str, *, max_identity_nodes: int = 4096) -> tuple[Expr, tuple[str, ...]]:
        metadata = self.metadata(name)
        if not metadata.support:
            raise IneligibleExpression("constant BLIF cones are not admitted")
        variables = {signal: Var(index) for index, signal in enumerate(metadata.support)}
        memo: dict[str, Expr] = {}
        visiting: set[str] = set()
        anchor = variables[metadata.support[0]]
        constant_true = Or(anchor, Not(anchor))
        constant_false = And(anchor, Not(anchor))

        def build(signal: str) -> Expr:
            if signal in variables:
                return variables[signal]
            if signal in memo:
                return memo[signal]
            node = self.nodes.get(signal)
            if node is None:
                raise ValueError(f"BLIF signal has no driver: {signal}")
            if signal in visiting:
                raise ValueError("cyclic BLIF dependency")
            visiting.add(signal)
            cubes: list[Expr] = []
            for pattern in node.cubes:
                literals = []
                for bit, child in zip(pattern, node.inputs):
                    if bit == "-":
                        continue
                    value = build(child)
                    literals.append(value if bit == "1" else Not(value))
                cubes.append(_balanced(literals, And) if literals else constant_true)
            matched = _balanced(cubes, Or) if cubes else constant_false
            value = matched if node.cube_output == 1 else Not(matched)
            visiting.remove(signal)
            memo[signal] = value
            return value

        expression = build(name)
        postorder(expression, max_nodes=max_identity_nodes)
        return expression, metadata.support

    def packed_value(self, name: str) -> tuple[int, tuple[str, ...]]:
        metadata = self.metadata(name)
        if not metadata.support:
            raise IneligibleExpression("constant BLIF cones are not admitted")
        env = build_bitset_env(tuple(f"x{index}" for index in range(len(metadata.support))))
        values: dict[str, int] = {signal: env[f"x{index}"]
                                  for index, signal in enumerate(metadata.support)}
        full_mask = (1 << (1 << len(metadata.support))) - 1
        visiting: set[str] = set()

        def evaluate(signal: str) -> int:
            if signal in values:
                return values[signal]
            node = self.nodes.get(signal)
            if node is None:
                raise ValueError(f"BLIF signal has no driver: {signal}")
            if signal in visiting:
                raise ValueError("cyclic BLIF dependency")
            visiting.add(signal)
            result = 0
            for pattern in node.cubes:
                cube = full_mask
                for bit, child in zip(pattern, node.inputs):
                    if bit == "-":
                        continue
                    child_value = evaluate(child)
                    cube &= child_value if bit == "1" else (~child_value) & full_mask
                result |= cube
            if node.cube_output == 0:
                result = (~result) & full_mask
            visiting.remove(signal)
            values[signal] = result
            return result

        return evaluate(name), metadata.support


def parse_blif(path: Path) -> BlifNetlist:
    path = Path(path)
    lines = _logical_lines(path)
    model = None
    inputs: list[str] = []
    outputs: list[str] = []
    nodes: dict[str, BlifNode] = {}
    saw_end = False
    index = 0
    while index < len(lines):
        parts = lines[index].split()
        directive = parts[0]
        if directive == ".model":
            if model is not None or len(parts) != 2:
                raise ValueError("BLIF must contain one named model")
            model = parts[1]
        elif directive == ".inputs":
            if inputs or len(parts) < 2:
                raise ValueError("BLIF inputs are missing or repeated")
            inputs = parts[1:]
        elif directive == ".outputs":
            if outputs or len(parts) < 2:
                raise ValueError("BLIF outputs are missing or repeated")
            outputs = parts[1:]
        elif directive == ".names":
            if len(parts) < 2:
                raise ValueError("invalid BLIF .names declaration")
            fanins, output = tuple(parts[1:-1]), parts[-1]
            if (output in nodes or output in inputs or len(fanins) > MAX_LUT_INPUTS
                    or len(set(fanins)) != len(fanins)):
                raise ValueError("invalid or duplicate BLIF node")
            cubes: list[str] = []
            cube_output: int | None = None
            index += 1
            while index < len(lines) and not lines[index].startswith("."):
                row = lines[index].split()
                if not fanins:
                    if row not in (["0"], ["1"]):
                        raise ValueError("invalid constant BLIF truth row")
                    pattern = ""
                    output_bit = int(row[0])
                else:
                    if (len(row) != 2 or row[1] not in ("0", "1")
                            or len(row[0]) != len(fanins)
                            or any(bit not in "01-" for bit in row[0])):
                        raise ValueError("invalid BLIF truth row")
                    pattern = row[0]
                    output_bit = int(row[1])
                if cube_output is not None and cube_output != output_bit:
                    raise ValueError("mixed-polarity BLIF truth rows are not admitted")
                cube_output = output_bit
                cubes.append(pattern)
                if len(cubes) > MAX_CUBES:
                    raise ValueError("BLIF LUT cube bound exceeded")
                index += 1
            nodes[output] = BlifNode(output, fanins, tuple(cubes),
                                     1 if cube_output is None else cube_output)
            continue
        elif directive == ".end":
            if len(parts) != 1 or saw_end:
                raise ValueError("invalid BLIF end marker")
            saw_end = True
        else:
            raise ValueError(f"unsupported BLIF directive: {directive}")
        index += 1
    if (model is None or not inputs or not outputs or not saw_end
            or len(inputs) > MAX_INPUTS or len(outputs) > MAX_OUTPUTS or len(nodes) > MAX_NODES
            or len(set(inputs)) != len(inputs) or len(set(outputs)) != len(outputs)):
        raise ValueError("incomplete or oversized BLIF model")
    netlist = BlifNetlist(source=path, model=model, inputs=tuple(inputs),
                          outputs=tuple(outputs), nodes=nodes)
    for output in outputs:
        if output not in netlist.nodes and output not in netlist._input_set:
            raise ValueError(f"BLIF output has no driver: {output}")
    return netlist
