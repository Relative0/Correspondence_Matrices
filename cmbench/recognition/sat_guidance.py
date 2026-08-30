"""Bounded exact SAT/equivalence adapter for E2/R10 guidance studies.

The guidance layer may choose a clause order, an initial phase order, or a
fresh/resident solver lifecycle.  It never proposes a Boolean answer.  SAT
answers are checked against the emitted CNF and UNSAT answers remain
authoritative only when returned by the configured complete solver.
"""
from __future__ import annotations

from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass
import hashlib
import importlib.metadata
import json
import math
import time
from typing import Any, Callable, Iterable, Sequence

from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

from .features import IneligibleExpression, postorder, structural_digest


CNF_SCHEMA = "crse-expression-cnf/v1"
MAX_SAT_VARS = 16
MAX_IDENTITY_NODES = 4096
MAX_CLAUSES = 32_768
MAX_CACHE_ENTRIES = 32
CLAUSE_ORDERS = ("source", "short_first", "long_first")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _validate_n_vars(n_vars: int) -> None:
    _require(type(n_vars) is int and 1 <= n_vars <= MAX_SAT_VARS,
             "SAT adapter requires an explicit 1..16 variable universe")


def _validate_literals(literals: Sequence[int], n_vars: int, label: str,
                       *, permit_aux: bool = False, max_var: int | None = None) -> tuple[int, ...]:

    _validate_n_vars(n_vars)
    upper = max_var if permit_aux else n_vars
    _require(isinstance(literals, (list, tuple)) and upper is not None,
             f"{label} must be a bounded literal sequence")
    _require(len(literals) <= upper, f"{label} exceeds the declared universe")
    result = tuple(literals)
    _require(all(type(literal) is int and 1 <= abs(literal) <= upper
                 for literal in result), f"{label} literal outside universe")
    _require(len({abs(literal) for literal in result}) == len(result),
             f"{label} contains duplicate or conflicting variables")
    return result


def validate_assumptions(assumptions: Sequence[int], n_vars: int) -> tuple[int, ...]:
    """Validate one complete-replacement assumption set over original variables."""
    return _validate_literals(assumptions, n_vars, "assumptions")


def validate_phases(phases: Sequence[int], n_vars: int) -> tuple[int, ...]:
    """Validate optional, nonauthoritative initial phases over original variables."""
    return _validate_literals(phases, n_vars, "phases")


@dataclass(frozen=True)
class EncodedFormula:
    task: str
    n_vars: int
    max_var: int
    output_literal: int
    clauses: tuple[tuple[int, ...], ...]
    expression_sha256: str
    clause_order: str

    def __post_init__(self) -> None:
        _validate_n_vars(self.n_vars)
        _require(self.task in {"sat", "equivalence_miter"}, "invalid CNF task")
        _require(type(self.max_var) is int and self.n_vars <= self.max_var <= 8192,
                 "invalid CNF maximum variable")
        _require(type(self.output_literal) is int
                 and 1 <= abs(self.output_literal) <= self.max_var,
                 "invalid CNF output literal")
        _require(self.clause_order in CLAUSE_ORDERS, "invalid CNF clause order")
        _require(isinstance(self.clauses, tuple)
                 and 1 <= len(self.clauses) <= MAX_CLAUSES,
                 "invalid bounded CNF clauses")
        for clause in self.clauses:
            _require(isinstance(clause, tuple) and 1 <= len(clause) <= 4,
                     "invalid bounded CNF clause")
            _require(all(type(literal) is int and 1 <= abs(literal) <= self.max_var
                         for literal in clause), "CNF literal outside universe")
        _require(type(self.expression_sha256) is str
                 and len(self.expression_sha256) == 64,
                 "invalid expression identity")

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "schema": CNF_SCHEMA, "task": self.task, "n_vars": self.n_vars,
            "max_var": self.max_var, "output_literal": self.output_literal,
            "clauses": [list(clause) for clause in self.clauses],
            "expression_sha256": self.expression_sha256,
            "clause_order": self.clause_order,
        }

    @property
    def sha256(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.semantic_dict())).hexdigest()


class _Encoder:
    def __init__(self, n_vars: int) -> None:
        _validate_n_vars(n_vars)
        self.n_vars = n_vars
        self.next_var = n_vars
        # Tautologies make the declared original universe explicit even when an
        # expression does not mention every variable.
        self.clauses: list[list[int]] = [[index, -index]
                                         for index in range(1, n_vars + 1)]
        self.literals: dict[int, int] = {}

    def fresh(self) -> int:
        self.next_var += 1
        _require(self.next_var <= 8192, "CNF auxiliary-variable bound exceeded")
        return self.next_var

    def encode(self, expr: Expr) -> int:
        try:
            nodes = postorder(expr, max_nodes=MAX_IDENTITY_NODES)
        except IneligibleExpression as exc:
            raise ValueError(str(exc)) from exc
        for node in nodes:
            kind = type(node)
            if kind is Var:
                _require(node.i < self.n_vars,
                         "expression variable outside declared universe")
                literal = node.i + 1
            elif kind is Not:
                literal = -self.literals[id(node.a)]
            else:
                a, b = self.literals[id(node.a)], self.literals[id(node.b)]
                literal = self.fresh()
                if kind is And:
                    self.clauses.extend(([-literal, a], [-literal, b],
                                         [literal, -a, -b]))
                elif kind is Or:
                    self.clauses.extend(([literal, -a], [literal, -b],
                                         [-literal, a, b]))
                elif kind is Xor:
                    self.clauses.extend(_xor_clauses(literal, a, b))
                elif kind is Imp:
                    self.clauses.extend(([literal, a], [literal, -b],
                                         [-literal, -a, b]))
                elif kind is Eqv:
                    self.clauses.extend(([literal, a, b], [literal, -a, -b],
                                         [-literal, a, -b], [-literal, -a, b]))
                else:  # postorder already rejects unsupported nodes.
                    raise ValueError("unsupported expression node")
            self.literals[id(node)] = literal
            _require(len(self.clauses) <= MAX_CLAUSES,
                     "CNF clause bound exceeded")
        return self.literals[id(expr)]


def _xor_clauses(output: int, left: int, right: int) -> tuple[list[int], ...]:
    return ([-output, -left, -right], [-output, left, right],
            [output, -left, right], [output, left, -right])


def _ordered_clauses(clauses: Iterable[Sequence[int]], policy: str) -> tuple[tuple[int, ...], ...]:
    _require(policy in CLAUSE_ORDERS, "unknown CNF clause order")
    result = [tuple(clause) for clause in clauses]
    if policy == "short_first":
        result.sort(key=lambda clause: (len(clause), tuple(abs(x) for x in clause), clause))
    elif policy == "long_first":
        result.sort(key=lambda clause: (-len(clause), tuple(abs(x) for x in clause), clause))
    return tuple(result)


def encode_expression_cnf(expr: Expr, n_vars: int, *,
                          clause_order: str = "source") -> EncodedFormula:
    """Encode ``expr == True`` with one bounded identity-DAG allocator."""
    encoder = _Encoder(n_vars)
    output = encoder.encode(expr)
    encoder.clauses.append([output])
    return EncodedFormula(
        "sat", n_vars, encoder.next_var, output,
        _ordered_clauses(encoder.clauses, clause_order),
        structural_digest(expr), clause_order)


def encode_equivalence_miter(left: Expr, right: Expr, n_vars: int, *,
                             clause_order: str = "source") -> EncodedFormula:
    """Encode ``left XOR right == True``; UNSAT therefore proves equivalence.

    A single allocator is shared by both sides.  This intentionally avoids the
    auxiliary-ID collision possible when independently produced Tseitin CNFs
    are concatenated.
    """
    encoder = _Encoder(n_vars)
    left_output = encoder.encode(left)
    right_output = encoder.encode(right)
    miter = encoder.fresh()
    encoder.clauses.extend(_xor_clauses(miter, left_output, right_output))
    encoder.clauses.append([miter])
    _require(len(encoder.clauses) <= MAX_CLAUSES, "CNF clause bound exceeded")
    identity = hashlib.sha256((structural_digest(left) + ":" +
                               structural_digest(right)).encode("ascii")).hexdigest()
    return EncodedFormula(
        "equivalence_miter", n_vars, encoder.next_var, miter,
        _ordered_clauses(encoder.clauses, clause_order), identity, clause_order)


def reorder_formula(formula: EncodedFormula, clause_order: str) -> EncodedFormula:
    """Return a semantically identical formula with an explicit clause order."""
    return EncodedFormula(
        formula.task, formula.n_vars, formula.max_var, formula.output_literal,
        _ordered_clauses(formula.clauses, clause_order),
        formula.expression_sha256, clause_order)


def literal_model(model: Sequence[int], max_var: int) -> tuple[int, ...]:
    _require(isinstance(model, (list, tuple)), "SAT model must be a literal sequence")
    values: dict[int, int] = {}
    for literal in model:
        _require(type(literal) is int and literal != 0 and abs(literal) <= max_var,
                 "SAT model literal outside CNF universe")
        variable = abs(literal)
        _require(variable not in values or values[variable] == literal,
                 "SAT model contains conflicting literals")
        values[variable] = literal
    _require(set(values) == set(range(1, max_var + 1)),
             "SAT model does not cover the explicit CNF universe")
    return tuple(values[index] for index in range(1, max_var + 1))


def verify_model(formula: EncodedFormula, model: Sequence[int],
                 assumptions: Sequence[int] = ()) -> tuple[int, ...]:
    """Independently evaluate every emitted clause and active assumption."""
    normalized = literal_model(model, formula.max_var)
    values = {abs(literal): literal > 0 for literal in normalized}
    active = validate_assumptions(assumptions, formula.n_vars)
    _require(all(values[abs(literal)] == (literal > 0) for literal in active),
             "SAT model violates active assumptions")
    for clause in formula.clauses:
        _require(any(values[abs(literal)] == (literal > 0) for literal in clause),
                 "SAT model violates emitted CNF")
    return tuple(normalized[index] for index in range(formula.n_vars))


def occurrence_phases(formula: EncodedFormula, *, reverse: bool = False) -> tuple[int, ...]:
    """Cheap deterministic original-variable polarity and activity ordering."""
    positive = [0] * (formula.n_vars + 1)
    negative = [0] * (formula.n_vars + 1)
    activity = [set() for _ in range(formula.n_vars + 1)]
    for clause_index, clause in enumerate(formula.clauses):
        if len(clause) == 2 and clause[0] == -clause[1]:
            continue
        for literal in clause:
            if abs(literal) <= formula.n_vars:
                (positive if literal > 0 else negative)[abs(literal)] += 1
                activity[abs(literal)].add(clause_index)
    variables = list(range(1, formula.n_vars + 1))
    variables.sort(key=lambda variable: (-len(activity[variable]), variable),
                   reverse=reverse)
    return tuple(variable if positive[variable] >= negative[variable] else -variable
                 for variable in variables)


def component_phases(formula: EncodedFormula) -> tuple[int, ...]:
    """Order original variables by CNF interaction component, then occurrence."""
    graph: dict[int, set[int]] = {index: set()
                                  for index in range(1, formula.n_vars + 1)}
    polarity = defaultdict(lambda: [0, 0])
    for clause in formula.clauses:
        variables = sorted({abs(literal) for literal in clause
                            if abs(literal) <= formula.n_vars})
        for literal in clause:
            if abs(literal) <= formula.n_vars:
                polarity[abs(literal)][literal < 0] += 1
        for position, variable in enumerate(variables):
            graph[variable].update(variables[:position])
            graph[variable].update(variables[position + 1:])
    components: list[list[int]] = []
    unseen = set(graph)
    while unseen:
        root = min(unseen)
        queue, component = deque([root]), []
        unseen.remove(root)
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in sorted(graph[current] & unseen):
                unseen.remove(neighbor)
                queue.append(neighbor)
        component.sort(key=lambda variable: (-len(graph[variable]), variable))
        components.append(component)
    components.sort(key=lambda group: (-len(group), group[0]))
    ordered = [variable for component in components for variable in component]
    return tuple(variable if polarity[variable][0] >= polarity[variable][1] else -variable
                 for variable in ordered)


def sat_guidance_features(formula: EncodedFormula, query_count: int) -> tuple[float, ...]:
    _require(type(query_count) is int and 1 <= query_count <= 256,
             "SAT guidance query count must be in 1..256")
    widths = [len(clause) for clause in formula.clauses]
    literals = [literal for clause in formula.clauses for literal in clause]
    negative = sum(literal < 0 for literal in literals)
    return (
        float(formula.n_vars), math.log2(len(formula.clauses)),
        math.log2(formula.max_var), sum(widths) / len(widths),
        sum(width == 1 for width in widths) / len(widths),
        negative / len(literals), math.log2(query_count),
        float(formula.task == "equivalence_miter"),
    )


SAT_FEATURE_NAMES = (
    "n_vars", "log2_clauses", "log2_cnf_vars", "mean_clause_width",
    "unit_fraction", "negative_literal_fraction", "log2_queries", "is_miter",
)


def solver_identity() -> dict[str, str]:
    return {
        "adapter": "pysat.solvers.Cadical195",
        "python_sat_version": importlib.metadata.version("python-sat"),
    }


def _default_solver_factory() -> Any:
    from pysat.solvers import Cadical195
    return Cadical195()


@dataclass(frozen=True)
class SatAnswer:
    satisfiable: bool
    witness: tuple[int, ...] | None
    core: tuple[int, ...] | None
    solve_ns: int
    verification_ns: int
    solver_authoritative: bool
    assumptions: tuple[int, ...]
    phases: tuple[int, ...]


class ExactSatSession:
    """One resident complete solver over exactly one immutable CNF digest."""

    def __init__(self, formula: EncodedFormula,
                 solver_factory: Callable[[], Any] = _default_solver_factory) -> None:
        self.formula = formula
        self.formula_sha256 = formula.sha256
        self._factory = solver_factory
        started = time.perf_counter_ns()
        self._solver = solver_factory()
        try:
            for clause in formula.clauses:
                self._solver.add_clause(list(clause))
        except Exception:
            self._solver.delete()
            raise
        self.build_ns = time.perf_counter_ns() - started
        self.solve_calls = 0
        self.closed = False

    def __enter__(self) -> "ExactSatSession":
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self.close()

    def close(self) -> None:
        if not self.closed:
            self._solver.delete()
            self.closed = True

    def solve(self, assumptions: Sequence[int] = (), phases: Sequence[int] = (),
              *, verify_core: bool = True) -> SatAnswer:
        _require(not self.closed, "SAT session is closed")
        active = validate_assumptions(assumptions, self.formula.n_vars)
        hints = validate_phases(phases, self.formula.n_vars)
        started = time.perf_counter_ns()
        if hints:
            self._solver.set_phases(list(hints))
        answer = self._solver.solve(assumptions=list(active))
        solve_ns = time.perf_counter_ns() - started
        self.solve_calls += 1
        _require(type(answer) is bool, "complete SAT solver returned unknown")
        checked = time.perf_counter_ns()
        if answer:
            witness = verify_model(self.formula, self._solver.get_model(), active)
            core = None
        else:
            witness = None
            raw_core = self._solver.get_core()
            if raw_core is None:
                raw_core = []
            _require(isinstance(raw_core, list)
                     and all(type(literal) is int and literal in active
                             for literal in raw_core)
                     and len(set(raw_core)) == len(raw_core),
                     "SAT core is not a subset of active assumptions")
            core = tuple(raw_core)
            if verify_core:
                verifier = self._factory()
                try:
                    for clause in self.formula.clauses:
                        verifier.add_clause(list(clause))
                    confirmation = verifier.solve(assumptions=list(core))
                    _require(confirmation is False,
                             "trusted solver did not confirm the returned UNSAT core")
                finally:
                    verifier.delete()
        verification_ns = time.perf_counter_ns() - checked
        return SatAnswer(answer, witness, core, solve_ns, verification_ns, True,
                         active, hints)


class VersionedSatSessionCache:
    """Exact-digest session reuse with explicit logical-version invalidation."""

    def __init__(self, capacity: int = 8,
                 solver_factory: Callable[[], Any] = _default_solver_factory) -> None:
        _require(type(capacity) is int and 1 <= capacity <= MAX_CACHE_ENTRIES,
                 "invalid SAT session-cache capacity")
        self.capacity = capacity
        self._factory = solver_factory
        self._sessions: OrderedDict[str, ExactSatSession] = OrderedDict()
        self._versions: dict[str, str] = {}
        self.hits = self.misses = self.invalidations = self.evictions = 0

    def acquire(self, version: str, formula: EncodedFormula) -> tuple[ExactSatSession, str]:
        _require(type(version) is str and 1 <= len(version) <= 128,
                 "invalid SAT logical version")
        digest = formula.sha256
        previous = self._versions.get(version)
        if previous is not None and previous != digest:
            self.invalidations += 1
        self._versions[version] = digest
        session = self._sessions.get(digest)
        if session is not None:
            self.hits += 1
            self._sessions.move_to_end(digest)
            return session, "exact_digest_hit"
        self.misses += 1
        session = ExactSatSession(formula, self._factory)
        self._sessions[digest] = session
        if len(self._sessions) > self.capacity:
            _, evicted = self._sessions.popitem(last=False)
            evicted.close()
            self.evictions += 1
        return session, "compiled_miss"

    def close(self) -> None:
        for session in self._sessions.values():
            session.close()
        self._sessions.clear()
        self._versions.clear()

    def __enter__(self) -> "VersionedSatSessionCache":
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self.close()
