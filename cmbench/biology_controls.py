"""Successor biology controls: explicit scalar oracle and parsimonious CNF.

These are comparator/correctness controls, not CM implementations. A clamp
replaces the clamped target's update equation; a condition retains it.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from cmbench.biology_bnet import BNetFunction, evaluate_bnet, require_closed_bnet
from cmbench.backends.projected_count import ProjectedCNF


def _context(functions, fixed):
    require_closed_bnet(functions)
    targets = tuple(f.target for f in functions)
    if not targets or len(set(targets)) != len(targets):
        raise ValueError("expected nonempty distinct BNet targets")
    fixed = dict(fixed or {})
    if set(fixed) - set(targets) or any(type(v) not in (bool, int) or v not in (0, 1) for v in fixed.values()):
        raise ValueError("invalid fixed target/value")
    return targets, fixed


def is_fixed_point(functions, witness, *, fixed=None, semantics="clamp"):
    targets, fixed = _context(functions, fixed)
    if semantics not in {"clamp", "condition"}:
        raise ValueError("unknown perturbation semantics")
    if set(witness) != set(targets) or any(type(v) not in (bool, int) or v not in (0, 1) for v in witness.values()):
        return False
    return (all(witness[k] == v for k, v in fixed.items()) and
            all((semantics == "clamp" and f.target in fixed) or
                evaluate_bnet(f.expression, witness) == witness[f.target] for f in functions))


@dataclass(frozen=True)
class FixedPointResult:
    count: int
    witness: dict[str, bool] | None
    backend: str


def bnet_scalar_oracle(functions, *, max_variables=20, fixed=None, semantics="clamp"):
    """Exhaustive independent truth-table oracle, with one checked witness."""
    targets, fixed = _context(functions, fixed)
    if len(targets) > max_variables:
        raise ValueError("scalar fixed-point width exceeds limit")
    if semantics not in {"clamp", "condition"}:
        raise ValueError("unknown perturbation semantics")
    count, witness = 0, None
    for values in product((False, True), repeat=len(targets)):
        candidate = dict(zip(targets, values))
        if is_fixed_point(functions, candidate, fixed=fixed, semantics=semantics):
            count += 1
            if witness is None:
                witness = candidate
    return FixedPointResult(count, witness, "bnet_scalar_oracle")


@dataclass(frozen=True)
class FixedPointCNF:
    targets: tuple[str, ...]
    variables: int
    clauses: tuple[tuple[int, ...], ...]

    def as_projected(self):
        return ProjectedCNF(self.variables, self.clauses, tuple(range(1, len(self.targets) + 1)), "projected")

    def dimacs(self):
        """No projection directives: full count equals network-state count."""
        return f"p cnf {self.variables} {len(self.clauses)}\n" + "".join(
            " ".join(map(str, c)) + " 0\n" for c in self.clauses)


def encode_fixed_points(functions: tuple[BNetFunction, ...], *, fixed=None, semantics="clamp",
                        max_nodes=2_000_000) -> FixedPointCNF:
    """Definitional iff gates give exactly one auxiliary extension per state.

    Negation uses a signed literal. Every constant/and/or auxiliary is fully
    equivalent to its children, never only an equisatisfiable implication.
    """
    targets, fixed = _context(functions, fixed)
    if semantics not in {"clamp", "condition"}:
        raise ValueError("unknown perturbation semantics")
    indices = {name: i + 1 for i, name in enumerate(targets)}
    clauses, literals = [], {}
    variables = len(targets)
    nodes = 0
    for function in functions:
        if semantics == "clamp" and function.target in fixed:
            continue
        pending = [(function.expression, False)]
        while pending:
            node, visited = pending.pop()
            key, kind = id(node), node[0]
            if key in literals:
                continue
            if not visited:
                nodes += 1
                if nodes > max_nodes:
                    raise ValueError("CNF expression node limit exceeded")
            if kind == "var":
                literals[key] = indices[node[1]]
            elif kind == "const":
                variables += 1
                literals[key] = variables
                clauses.append((variables if node[1] else -variables,))
            elif kind not in {"not", "and", "or"}:
                raise ValueError("unknown BNet expression node")
            elif not visited:
                pending.append((node, True))
                pending.extend((child, False) for child in reversed(node[1:]))
            elif kind == "not":
                literals[key] = -literals[id(node[1])]
            else:
                variables += 1
                z = variables
                children = tuple(literals[id(child)] for child in node[1:])
                if kind == "and":
                    clauses.extend((-z, child) for child in children)
                    clauses.append((z, *(-child for child in children)))
                else:
                    clauses.extend((z, -child) for child in children)
                    clauses.append((-z, *children))
                literals[key] = z
        target, root = indices[function.target], literals[id(function.expression)]
        clauses.extend(((-target, root), (target, -root)))
    clauses.extend((indices[name] if value else -indices[name],) for name, value in fixed.items())
    return FixedPointCNF(targets, variables, tuple(clauses))


def native_fixed_points(functions, *, fixed=None, semantics="clamp", max_targets=20,
                        max_solutions=1 << 20):
    """Bounded exact enumeration with the existing native CaDiCaL 1.9.5.

    This is SAT-based enumeration, not a competitive specialized #SAT solver.
    A process deadline must be supplied by the benchmark runner.
    """
    from pysat.solvers import Cadical195
    if len(functions) > max_targets or type(max_solutions) is not int or max_solutions < 1:
        raise ValueError("native enumeration bounds exceeded")
    cnf = encode_fixed_points(functions, fixed=fixed, semantics=semantics)
    count, witness = 0, None
    with Cadical195(bootstrap_with=cnf.clauses) as solver:
        # Register every original variable, including completely free targets.
        for variable in range(1, len(cnf.targets) + 1):
            solver.add_clause([variable, -variable])
        while solver.solve():
            model = {abs(v): v > 0 for v in solver.get_model()}
            candidate = {name: model[i + 1] for i, name in enumerate(cnf.targets)}
            if not is_fixed_point(functions, candidate, fixed=fixed, semantics=semantics):
                raise ValueError("native witness fails original BNet equations")
            count += 1
            if count > max_solutions:
                raise ValueError("solution enumeration limit exceeded")
            if witness is None:
                witness = candidate
            solver.add_clause([-(i + 1) if candidate[name] else i + 1 for i, name in enumerate(cnf.targets)])
    return FixedPointResult(count, witness, "cadical195_enumeration")
