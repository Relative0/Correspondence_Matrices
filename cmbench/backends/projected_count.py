"""Exact bounded projected-CNF semantics and independent local oracles."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True)
class ProjectedCNF:
    variables: int
    clauses: tuple[tuple[int, ...], ...]
    projection: tuple[int, ...]
    mode: str
    declared_support: tuple[int, ...] = ()


def parse_counting_dimacs(text: str, *, mode: str, max_bytes: int = 16 << 20,
                          max_variables: int = 2_000_000, max_clauses: int = 4_000_000) -> ProjectedCNF:
    if mode not in {"exact", "projected"}:
        raise ValueError("counting mode must be exact or projected")
    if not isinstance(text, str) or not 0 < len(text.encode("utf-8")) <= max_bytes:
        raise ValueError("DIMACS outside byte limit")
    header = None
    clauses = []
    current = []
    independent = []
    for raw in text.splitlines():
        fields = raw.split()
        if not fields:
            continue
        if fields[0] == "c":
            if len(fields) >= 3 and fields[1] in {"ind", "p"}:
                values = fields[2:]
                if fields[1] == "p":
                    if len(fields) < 4 or fields[2] != "show":
                        continue
                    values = fields[3:]
                if not values or values[-1] != "0":
                    raise ValueError("unterminated projection/support directive")
                independent.extend(int(item) for item in values[:-1])
            continue
        if fields[0] == "p":
            if header is not None or len(fields) != 4 or fields[1] != "cnf":
                raise ValueError("invalid DIMACS header")
            variables, expected = int(fields[2]), int(fields[3])
            if not 0 <= variables <= max_variables or not 0 <= expected <= max_clauses:
                raise ValueError("DIMACS dimensions exceed limits")
            header = variables, expected
            continue
        if header is None:
            raise ValueError("DIMACS clause precedes header")
        for field in fields:
            literal = int(field)
            if literal == 0:
                clauses.append(tuple(current))
                current = []
            else:
                if abs(literal) > header[0]:
                    raise ValueError("DIMACS literal outside variable range")
                current.append(literal)
    if header is None or current or len(clauses) != header[1]:
        raise ValueError("incomplete DIMACS")
    if any(value <= 0 or value > header[0] for value in independent) or len(set(independent)) != len(independent):
        raise ValueError("invalid projection/support variables")
    if mode == "projected" and not independent:
        raise ValueError("projected instance lacks projection variables")
    projection = tuple(independent) if mode == "projected" else tuple(range(1, header[0] + 1))
    return ProjectedCNF(header[0], tuple(clauses), projection, mode, tuple(independent))


def _satisfies(clauses: tuple[tuple[int, ...], ...], assignment: tuple[bool, ...]) -> bool:
    return all(any(assignment[abs(literal) - 1] == (literal > 0) for literal in clause) for clause in clauses)


def scalar_projected_count(instance: ProjectedCNF, *, max_variables: int = 20) -> int:
    if instance.variables > max_variables:
        raise ValueError("scalar oracle width exceeds limit")
    visible = set()
    for assignment in product((False, True), repeat=instance.variables):
        if _satisfies(instance.clauses, assignment):
            visible.add(tuple(assignment[index - 1] for index in instance.projection))
    return len(visible)


def pysat_projected_count(instance: ProjectedCNF, *, max_projection: int = 20,
                          max_solutions: int = 1 << 20) -> int:
    if len(instance.projection) > max_projection:
        raise ValueError("projection width exceeds local exact-enumeration limit")
    from pysat.solvers import Cadical195

    count = 0
    with Cadical195(bootstrap_with=[list(clause) for clause in instance.clauses]) as solver:
        if not instance.projection:
            return int(solver.solve())
        while solver.solve():
            model = {abs(literal): literal > 0 for literal in solver.get_model()}
            visible = tuple(model.get(variable, False) for variable in instance.projection)
            count += 1
            if count > max_solutions:
                raise ValueError("solution enumeration limit exceeded")
            solver.add_clause([-variable if value else variable
                               for variable, value in zip(instance.projection, visible)])
    return count
