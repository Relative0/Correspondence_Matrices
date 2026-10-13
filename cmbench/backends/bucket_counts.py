"""Opt-in exact CNF counts via bounded sum-product variable elimination."""
from __future__ import annotations

from itertools import combinations
from math import prod

from bitset_backend import compile_expr_cse, compile_flat, _FLAT_OP_AND, _FLAT_OP_OR, _FLAT_OP_NOT
from cmbench.backends.packed_mask_cache import ordered_basis


class CountPlanLimit(ValueError):
    """The complete plan exceeds a caller's explicit resource admission bound."""


def parse_dimacs(text, *, max_bytes=1 << 20, max_vars=2048, max_clauses=16384):
    if not isinstance(text, str) or len(text.encode('utf-8')) > max_bytes:
        raise ValueError('DIMACS input exceeds byte limit')
    header, clauses, current = None, [], []
    literals = 0
    for line in text.splitlines():
        fields = line.split()
        if not fields or fields[0] == 'c': continue
        if fields[0] == 'p':
            if header is not None or len(fields) != 4 or fields[1] != 'cnf':
                raise ValueError('invalid or duplicate DIMACS header')
            n, m = map(int, fields[2:])
            if not 0 <= n <= max_vars or not 0 <= m <= max_clauses:
                raise CountPlanLimit('DIMACS dimensions exceed limits')
            header = n, m
            continue
        if header is None: raise ValueError('DIMACS clauses precede header')
        for field in fields:
            value = int(field)
            if value == 0:
                clauses.append(tuple(current)); current = []
                if len(clauses) > header[1]: raise ValueError('too many DIMACS clauses')
            else:
                if abs(value) > header[0]: raise ValueError('DIMACS literal outside basis')
                literals += 1
                if literals > 1 << 20: raise CountPlanLimit('DIMACS literal limit exceeded')
                current.append(value)
    if header is None or current or len(clauses) != header[1]:
        raise ValueError('incomplete DIMACS input')
    return header[0], tuple(clauses)


def simplify_units(clauses):
    """Exact unit propagation; forced values remain part of the count contract."""
    clauses = tuple(clauses)
    forced = {}
    while True:
        reduced = []
        for clause in clauses:
            if any(abs(l)-1 in forced and forced[abs(l)-1] == int(l > 0) for l in clause):
                continue
            rest = tuple(l for l in clause if abs(l)-1 not in forced)
            if not rest: return (), forced, False
            reduced.append(rest)
        units = [c[0] for c in reduced if len(c) == 1]
        if not units: return tuple(sorted(set(reduced))), forced, True
        for literal in units:
            variable, value = abs(literal)-1, int(literal > 0)
            if variable in forced and forced[variable] != value: return (), forced, False
            forced[variable] = value
        clauses = reduced


class BucketCNFCountPlan:
    """A fixed elimination schedule, exact integer factors, and private queries.

    Clauses use DIMACS literals: +/- (basis position + 1). Local table row bit i
    denotes the ith variable in the sorted scope. All resource guards run before
    any truth/count table allocation. Fixed queries do not replan or cache answers.
    """

    def __init__(self, clauses, names, *, order='min_fill', max_width=14,
                 max_cells=1 << 20, max_work=1 << 24, max_order_checks=2_000_000,
                 max_vars=2048, max_clauses=16384, _existential=()):
        limits = (max_width, max_cells, max_work, max_order_checks, max_vars, max_clauses)
        if any(type(v) is not int or v < 0 for v in limits) or max_width > 20:
            raise ValueError('limits must be nonnegative integers; max_width must be <=20')
        if order not in ('natural', 'min_fill'): raise ValueError('unknown elimination order')
        self.basis = ordered_basis(names)
        if len(self.basis) > max_vars: raise CountPlanLimit('basis width exceeds limit')
        # Internal support for ProjectedCNFCountPlan: existential variables
        # must be eliminated before any counted variable. Reversing these
        # operations can count auxiliary witnesses more than once.
        self._existential = frozenset(_existential)
        if any(type(v) is not int or not 0 <= v < len(self.basis) for v in self._existential):
            raise ValueError('existential variable outside basis')
        self._counted = frozenset(range(len(self.basis))) - self._existential
        self._positions = {name: i for i, name in enumerate(self.basis)}
        normalized, literal_count = [], 0
        for i, clause in enumerate(clauses):
            if i >= max_clauses: raise CountPlanLimit('clause count exceeds limit')
            unique = set()
            for literal in clause:
                literal_count += 1
                if literal_count > 1 << 20: raise CountPlanLimit('literal count exceeds limit')
                if type(literal) is not int or literal == 0 or abs(literal) > len(self.basis):
                    raise ValueError('clause literal lies outside basis')
                unique.add(literal)
            if not any(-v in unique for v in unique): normalized.append(tuple(sorted(unique)))
        reduced, self._forced, self._consistent = simplify_units(normalized)
        self.clauses = reduced
        scopes = [tuple(sorted(abs(l)-1 for l in c)) for c in reduced]
        if any(len(s) > max_width for s in scopes): raise CountPlanLimit('input clause width exceeds limit')
        used = set().union(*(set(s) for s in scopes))
        self._unused = frozenset(range(len(self.basis))) - used - self._forced.keys()
        graph = {v: set() for v in used}
        for scope in scopes:
            for a, b in combinations(scope, 2): graph[a].add(b); graph[b].add(a)
        pool = {i: scope for i, scope in enumerate(scopes)}
        next_id = len(pool)
        initial_cells = sum(1 << len(s) for s in scopes)
        peak_cells, live_intermediate, work, checks = initial_cells, 0, initial_cells, 0
        if initial_cells > max_cells or work > max_work: raise CountPlanLimit('initial table budget exceeded')
        schedule, width = [], 0
        while graph:
            if order == 'natural':
                variable = min(graph, key=lambda v: (v not in self._existential, v)) if self._existential else min(graph)
            else:
                scored = []
                for v, neighbors in graph.items():
                    missing = 0
                    for a, b in combinations(neighbors, 2):
                        checks += 1
                        if checks > max_order_checks: raise CountPlanLimit('ordering work exceeds limit')
                        missing += b not in graph[a]
                    scored.append((v not in self._existential, missing, len(neighbors), v))
                variable = min(scored)[-1]
            bucket = tuple(i for i, scope in pool.items() if variable in scope)
            union = tuple(sorted(set().union(*(set(pool[i]) for i in bucket))))
            width = max(width, len(union))
            if len(union) > max_width: raise CountPlanLimit('elimination width exceeds limit')
            output = tuple(v for v in union if v != variable)
            size = 1 << len(output)
            projections = tuple(tuple(union.index(v) for v in pool[i]) for i in bucket)
            work += (1 << len(union)) * (1 + sum(len(p)+1 for p in projections))
            if work > max_work: raise CountPlanLimit('elimination work exceeds limit')
            # Initial tables remain retained by the plan even after consumption.
            peak_cells = max(peak_cells, initial_cells + live_intermediate + size)
            if peak_cells > max_cells: raise CountPlanLimit('live table budget exceeded')
            schedule.append((variable, bucket, union.index(variable), projections, next_id, size))
            for i in bucket:
                if i >= len(scopes): live_intermediate -= 1 << len(pool[i])
                del pool[i]
            live_intermediate += size
            pool[next_id] = output; next_id += 1
            neighbors = graph.pop(variable)
            for a in neighbors:
                graph[a].discard(variable)
                graph[a].update(neighbors - {a})
        self._schedule, self._final = tuple(schedule), tuple(pool)
        self.stats = dict(order=order, width=width, forced_variables=len(self._forced),
                          remaining_variables=len(used), initial_cells=initial_cells,
                          peak_cells_bound=peak_cells, work_bound=work, ordering_checks=checks,
                          eliminated_variables=len(schedule))
        # Allocation deliberately follows the full schedule admission checks.
        self._tables = tuple(tuple(int(row != false_row) for row in range(1 << len(scope)))
                             for clause, scope in zip(reduced, scopes)
                             for false_row in [sum(1 << scope.index(abs(l)-1) for l in clause if l < 0)])

    @classmethod
    def from_cnf(cls, clauses, names, **limits):
        return cls(clauses, names, **limits)

    @classmethod
    def from_program(cls, program, names, **limits):
        basis = ordered_basis(names)
        positions = {n: i+1 for i, n in enumerate(basis)}
        if not set(program.load_vars).issubset(positions): raise ValueError('basis omits expression variables')
        loads = {s: (kind, value) for s, kind, value in program.loads}
        ops = {s: (op, args) for s, op, args in program.ops}
        roots, pending, seen = [], [program.root_slot], set()
        while pending:
            s = pending.pop()
            if s in seen: continue
            seen.add(s)
            if s in ops and ops[s][0] == _FLAT_OP_AND: pending.extend(ops[s][1])
            else: roots.append(s)
        clauses = []
        for root in roots:
            clause, pending, tautology = [], [root], False
            while pending:
                s = pending.pop(); negative = False
                if s in ops and ops[s][0] == _FLAT_OP_OR:
                    pending.extend(ops[s][1]); continue
                if s in ops and ops[s][0] == _FLAT_OP_NOT:
                    s = ops[s][1][0]; negative = True
                if s not in loads: raise ValueError('expression is not syntactic CNF')
                kind, value = loads[s]
                if kind == 'const':
                    tautology |= bool(value) != negative
                else: clause.append(-positions[value] if negative else positions[value])
            if not tautology: clauses.append(clause)
        return cls(clauses, basis, **limits)

    @classmethod
    def from_expr(cls, expr, names, **limits):
        return cls.from_program(compile_expr_cse(expr, flatten=True), names, **limits)

    @classmethod
    def from_cm_node(cls, node, names, **limits):
        return cls.from_program(compile_flat(node), names, **limits)

    def count(self, fixed=None):
        supplied = dict(fixed or {})
        if any(n not in self._positions for n in supplied): raise ValueError('fixed variable outside basis')
        if any(type(v) not in (int, bool) or v not in (0, 1) for v in supplied.values()):
            raise ValueError('fixed values must be Boolean')
        context = {self._positions[n]: int(v) for n, v in supplied.items()}
        if not self._consistent or any(v in context and context[v] != b for v, b in self._forced.items()):
            return 0
        tables = dict(enumerate(self._tables))
        for variable, bucket, position, projections, target, size in self._schedule:
            inputs = [tables[i] for i in bucket]
            result = [0] * size
            choices = (context[variable],) if variable in context else (0, 1)
            for row in range(size):
                low = row & ((1 << position)-1)
                high = (row >> position) << (position+1)
                total = 0
                for value in choices:
                    assignment, term = low | high | (value << position), 1
                    for table, mapping in zip(inputs, projections):
                        index = sum(((assignment >> bit) & 1) << i for i, bit in enumerate(mapping))
                        term *= table[index]
                        if not term: break
                    total += term
                result[row] = int(bool(total)) if variable in self._existential else total
            for i in bucket: del tables[i]
            tables[target] = result
        return prod(tables[i][0] for i in self._final) << len((self._unused & self._counted) - context.keys())

    def exists(self, fixed=None):
        return bool(self.count(fixed))
