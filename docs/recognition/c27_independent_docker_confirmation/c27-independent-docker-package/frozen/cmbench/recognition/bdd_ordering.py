"""Bounded exact ROBDD artifacts and independent order-aware replay."""
from __future__ import annotations

from dataclasses import dataclass
import gc
import json
from typing import Any, Mapping, Sequence

from cm_exprlib import Expr

from cmbench.backends.robdd_dd import (
    _declare_dd_vars, bdd_function_value, expr_to_dd_bdd, safe_bdd_node_count,
    select_dd_module,
)


ARTIFACT_SCHEMA = "crse-exact-bdd-order-artifact/v1"
MAX_BDD_VARS = 16
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_order(order: Sequence[str], n_vars: int) -> tuple[str, ...]:
    _require(type(n_vars) is int and 1 <= n_vars <= MAX_BDD_VARS,
             "BDD artifacts require 1..16 variables")
    expected = {f"x{i}" for i in range(n_vars)}
    _require(isinstance(order, (list, tuple)) and len(order) == n_vars
             and all(type(name) is str for name in order) and set(order) == expected,
             "BDD order must be an exact variable-universe permutation")
    return tuple(order)


def _assignment_index(assignment: Mapping[str, int], n_vars: int) -> int:
    value = 0
    for index in range(n_vars):
        bit = assignment[f"x{index}"]
        _require(type(bit) in (int, bool) and int(bit) in (0, 1),
                 "BDD assignment values must be Boolean")
        value = (value << 1) | int(bit)
    return value


@dataclass
class ExactBddArtifact:
    manager: Any
    root: Any
    n_vars: int
    variable_order: tuple[str, ...]
    backend: str

    def close(self) -> None:
        """Release external root references before the pure-Python manager."""
        self.root = None
        gc.collect()
        try:
            self.manager.collect_garbage()
        except Exception:
            pass

    def __enter__(self) -> "ExactBddArtifact":
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self.close()

    @classmethod
    def build(cls, expr: Expr, n_vars: int, order: Sequence[str],
              *, backend: str = "autoref") -> "ExactBddArtifact":
        normalized_order = _validate_order(order, n_vars)
        module, error = select_dd_module(backend)
        if module is None:
            raise RuntimeError(f"BDD backend unavailable: {error}")
        manager = module.BDD()
        try:
            manager.configure(reordering=False)
        except Exception:
            pass
        _declare_dd_vars(manager, list(normalized_order))
        root = expr_to_dd_bdd(
            expr, manager, {f"x{i}": f"x{i}" for i in range(n_vars)})
        identity = getattr(manager.__class__, "__module__", "")
        return cls(manager, root, n_vars, normalized_order, identity)

    @property
    def node_count(self) -> int:
        value = safe_bdd_node_count(self.manager, self.root)
        if type(value) is not int or value < 0:
            raise ValueError("BDD backend did not expose a bounded node count")
        return value

    def truth_bits(self) -> tuple[int, ...]:
        names = [f"x{i}" for i in range(self.n_vars)]
        return tuple(bdd_function_value(
            self.manager, self.root,
            {name: (index >> (self.n_vars - 1 - position)) & 1
             for position, name in enumerate(names)})
            for index in range(1 << self.n_vars))

    def exact_count(self) -> int:
        count = self.manager.count(self.root, nvars=self.n_vars)
        _require(type(count) in (int, float) and float(count).is_integer()
                 and 0 <= int(count) <= 1 << self.n_vars,
                 "BDD count is outside the exact bounded universe")
        return int(count)

    def sat_witness(self) -> dict[str, int] | None:
        if self.root == self.manager.false:
            return None
        picked = self.manager.pick(self.root) or {}
        witness = {f"x{i}": int(bool(picked.get(f"x{i}", False)))
                   for i in range(self.n_vars)}
        _require(bdd_function_value(self.manager, self.root, witness) == 1,
                 "BDD backend returned an invalid SAT witness")
        return witness

    def restrict_truth_bits(
        self, assignment: Mapping[str, int],
    ) -> tuple[tuple[str, ...], tuple[int, ...]]:
        _require(isinstance(assignment, Mapping) and len(assignment) <= self.n_vars,
                 "invalid bounded BDD restriction")
        normalized: dict[str, bool] = {}
        for name, value in assignment.items():
            _require(name in {f"x{i}" for i in range(self.n_vars)}
                     and type(value) in (int, bool) and int(value) in (0, 1),
                     "invalid bounded BDD restriction")
            normalized[name] = bool(value)
        residual = self.manager.let(normalized, self.root)
        remaining = tuple(f"x{i}" for i in range(self.n_vars)
                          if f"x{i}" not in normalized)
        bits = []
        for index in range(1 << len(remaining)):
            values = {name: (index >> (len(remaining) - 1 - position)) & 1
                      for position, name in enumerate(remaining)}
            bits.append(bdd_function_value(self.manager, residual, values))
        return remaining, tuple(bits)

    def equivalent(self, other: Expr) -> bool:
        other_root = expr_to_dd_bdd(
            other, self.manager,
            {f"x{i}": f"x{i}" for i in range(self.n_vars)})
        try:
            difference = self.root ^ other_root
        except TypeError:
            difference = self.manager.apply("xor", self.root, other_root)
        return difference == self.manager.false

    def to_dict(self) -> dict[str, Any]:
        nodes: dict[str, list[Any]] = {}
        memo: dict[Any, Any] = {}

        def visit(node: Any) -> Any:
            if node == self.manager.false:
                return "F"
            if node == self.manager.true:
                return "T"
            if node in memo:
                return memo[node]
            if getattr(node, "negated", False):
                level, low, high = self.manager.succ(~node)
                low, high = ~low, ~high
            else:
                level, low, high = self.manager.succ(node)
            _require(type(level) is int and 0 <= level < self.n_vars
                     and low is not None and high is not None,
                     "invalid BDD node during serialization")
            low_ref, high_ref = visit(low), visit(high)
            identifier = len(nodes) + 1
            nodes[str(identifier)] = [level, low_ref, high_ref]
            memo[node] = identifier
            return identifier

        return {
            "schema": ARTIFACT_SCHEMA, "n_vars": self.n_vars,
            "variable_order": list(self.variable_order),
            "root": visit(self.root), "nodes": nodes,
        }

    def to_bytes(self) -> bytes:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"
        _require(len(payload) <= MAX_ARTIFACT_BYTES, "BDD artifact exceeds byte bound")
        return payload


def _strict_load(payload: bytes) -> dict[str, Any]:
    _require(type(payload) is bytes and 0 < len(payload) <= MAX_ARTIFACT_BYTES,
             "invalid BDD artifact byte length")

    def pairs(values):
        result = {}
        for key, value in values:
            _require(key not in result, "duplicate BDD artifact field")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("nonfinite BDD artifact number")

    try:
        data = json.loads(payload, object_pairs_hook=pairs, parse_constant=constant)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
        raise ValueError("invalid BDD artifact JSON") from exc
    _require(type(data) is dict, "BDD artifact must be an object")
    return data


def validate_bdd_artifact(payload: bytes) -> dict[str, Any]:
    data = _strict_load(payload)
    _require(set(data) == {"schema", "n_vars", "variable_order", "root", "nodes"}
             and data.get("schema") == ARTIFACT_SCHEMA,
             "invalid BDD artifact fields")
    n_vars = data["n_vars"]
    order = _validate_order(data["variable_order"], n_vars)
    nodes = data["nodes"]
    _require(type(nodes) is dict and len(nodes) <= (1 << (n_vars + 1)),
             "invalid BDD artifact node map")
    identifiers = {str(index) for index in range(1, len(nodes) + 1)}
    _require(set(nodes) == identifiers, "BDD artifact node ids are not contiguous")
    active: set[int] = set()
    reached: set[int] = set()

    def row(reference: Any, parent_level: int = -1):
        if reference in ("F", "T"):
            return None
        _require(type(reference) is int and 1 <= reference <= len(nodes),
                 "invalid BDD artifact reference")
        value = nodes[str(reference)]
        _require(type(value) is list and len(value) == 3
                 and type(value[0]) is int and parent_level < value[0] < n_vars,
                 "BDD artifact violates variable order")
        return value

    def visit(reference: Any, parent_level: int = -1) -> None:
        value = row(reference, parent_level)
        if value is None:
            return
        identifier = int(reference)
        _require(identifier not in active, "cyclic BDD artifact")
        if identifier in reached:
            return
        active.add(identifier)
        level, low, high = value
        visit(low, level)
        visit(high, level)
        active.remove(identifier)
        reached.add(identifier)

    visit(data["root"])
    _require(reached == {int(item) for item in identifiers},
             "BDD artifact contains unreachable nodes")
    return {**data, "variable_order": list(order)}


def independent_bdd_truth_bits(payload: bytes) -> tuple[int, ...]:
    data = validate_bdd_artifact(payload)
    n_vars, order, nodes, root = (
        data["n_vars"], data["variable_order"], data["nodes"], data["root"])

    def evaluate(reference: Any, assignment: Mapping[str, int]) -> int:
        while reference not in ("F", "T"):
            level, low, high = nodes[str(reference)]
            reference = high if assignment[order[level]] else low
        return int(reference == "T")

    bits = []
    for index in range(1 << n_vars):
        assignment = {f"x{i}": (index >> (n_vars - 1 - i)) & 1
                      for i in range(n_vars)}
        bits.append(evaluate(root, assignment))
    return tuple(bits)


def load_bdd_artifact(payload: bytes, *, backend: str = "autoref") -> ExactBddArtifact:
    data = validate_bdd_artifact(payload)
    module, error = select_dd_module(backend)
    if module is None:
        raise RuntimeError(f"BDD backend unavailable: {error}")
    manager = module.BDD()
    try:
        manager.configure(reordering=False)
    except Exception:
        pass
    order = tuple(data["variable_order"])
    _declare_dd_vars(manager, list(order))
    resolved: dict[Any, Any] = {"F": manager.false, "T": manager.true}
    for identifier in range(1, len(data["nodes"]) + 1):
        level, low, high = data["nodes"][str(identifier)]
        _require(low in resolved and high in resolved,
                 "BDD artifact nodes are not postordered")
        variable = manager.var(order[level])
        resolved[identifier] = manager.ite(variable, resolved[high], resolved[low])
    return ExactBddArtifact(
        manager, resolved[data["root"]], data["n_vars"], order,
        getattr(manager.__class__, "__module__", ""))
