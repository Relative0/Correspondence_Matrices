"""Bounded existential simplification with an explicit selected-variable set.

This is a research mechanism, not a router. Condition each request before
eliminating hidden variables: a later assignment to an eliminated variable
cannot safely be applied to the simplified formula.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from cmbench.backends.bucket_counts import CountPlanLimit


@dataclass(frozen=True)
class SimplifiedProjection:
    n: int
    clauses: tuple[tuple[int, ...], ...]
    projected: tuple[int, ...]
    original_variables: tuple[int, ...]
    unsatisfiable: bool
    stats: dict


def simplify_projected(n, clauses, projected, fixed=None, *, max_vars=16384,
                       max_clauses=65536, max_resolution_pairs=64,
                       max_resolvent_width=12, max_eliminations=128,
                       max_work=4000000):
    """Preserve the exact number of distinct selected assignments.

    Input literals are signed one-based integers; projection indices are
    zero-based. Fixed names use x0, x1, ... . Unit assignments remove a counted
    axis with multiplicity one. Unconstrained selected axes remain in the
    returned basis. Pure-literal and resolution elimination are hidden-only.
    Resource bounds stop optional simplification, never discard constraints.
    """
    if type(n) is not int or n < 0: raise ValueError('invalid variable count')
    if n > max_vars: raise CountPlanLimit('simplification basis exceeds limit')
    selected = tuple(projected)
    if len(set(selected)) != len(selected) or any(type(v) is not int or not 0 <= v < n for v in selected):
        raise ValueError('invalid projection')
    selected = {v+1 for v in selected}
    original = []
    for clause in clauses:
        if len(original) >= max_clauses: raise CountPlanLimit('simplification clauses exceed limit')
        row = frozenset(clause)
        if any(type(v) is not int or not 1 <= abs(v) <= n for v in row): raise ValueError('invalid literal')
        original.append(row)
    assigned = {}
    for name, value in (fixed or {}).items():
        if not isinstance(name, str) or not re.fullmatch(r'x[0-9]+', name) or type(value) not in (bool, int) or value not in (0, 1):
            raise ValueError('invalid fixed assignment')
        v = int(name[1:])+1
        if not 1 <= v <= n: raise ValueError('fixed variable outside basis')
        assigned[v] = bool(value)
    rows = set(row for row in original if not any(-v in row for v in row))
    stats = dict(input_variables=n, input_clauses=len(original), removed_tautologies=len(original)-sum(not any(-v in row for v in row) for row in original),
                 unit_assignments=0, pure_hidden=0, resolved_hidden=0, work=0, budget_stop=False)

    def finish(unsat=False):
        keep_selected = selected - assigned.keys()
        basis = sorted(keep_selected | {abs(v) for row in rows for v in row}) if not unsat else []
        indices = {v:i+1 for i,v in enumerate(basis)}
        ordered = tuple(sorted(tuple(sorted((indices[abs(v)] if v>0 else -indices[abs(v)]) for v in row)) for row in rows)) if not unsat else ((),)
        result_stats = {**stats, 'remaining_variables':len(basis), 'remaining_clauses':len(ordered),
                        'remaining_max_clause':max(map(len, ordered),default=0), 'forced_selected':len(selected & assigned.keys())}
        return SimplifiedProjection(len(basis), ordered, tuple(indices[v]-1 for v in sorted(keep_selected)) if not unsat else (),
                                    tuple(v-1 for v in basis), unsat, result_stats)

    while True:
        # Apply all known assignments before checking the optional work budget.
        conditioned = set()
        for row in rows:
            if any(abs(v) in assigned and assigned[abs(v)] == (v>0) for v in row): continue
            remainder = frozenset(v for v in row if abs(v) not in assigned)
            if not remainder:
                rows = {frozenset()}; return finish(True)
            conditioned.add(remainder)
        rows = conditioned
        stats['work'] += sum(map(len, rows))
        if stats['work'] > max_work:
            stats['budget_stop'] = True; return finish()
        units = [next(iter(row)) for row in rows if len(row)==1]
        if units:
            for literal in units:
                v=abs(literal); value=literal>0
                if v in assigned and assigned[v] != value:
                    rows={frozenset()}; return finish(True)
                if v not in assigned: stats['unit_assignments'] += 1
                assigned[v]=value
            continue
        positive, negative = {}, {}
        for row in rows:
            for literal in row:
                (positive if literal>0 else negative).setdefault(abs(literal), []).append(row)
        pure = sorted((positive.keys() ^ negative.keys()) - selected)
        if pure:
            for v in pure: assigned[v]=v in positive
            stats['pure_hidden'] += len(pure)
            continue
        if stats['resolved_hidden'] >= max_eliminations: return finish()
        candidates = sorted((len(positive[v])*len(negative[v]), len(positive[v])+len(negative[v]), v)
                            for v in positive.keys() & negative.keys() - selected
                            if len(positive[v])*len(negative[v]) <= max_resolution_pairs)
        chosen = None
        for pairs, _, v in candidates:
            if stats['work']+pairs > max_work: break
            resolvents = set(); eligible=True
            for a in positive[v]:
                for b in negative[v]:
                    row=(a-{v}) | (b-{-v}); stats['work'] += 1
                    if any(-literal in row for literal in row): continue
                    if len(row)>max_resolvent_width: eligible=False; break
                    resolvents.add(row)
                if not eligible: break
            if eligible and len(rows)-len(positive[v])-len(negative[v])+len(resolvents) <= max_clauses:
                chosen=(v,resolvents); break
        if chosen is None: return finish()
        v, resolvents = chosen
        rows = (rows-set(positive[v])-set(negative[v])) | resolvents
        stats['resolved_hidden'] += 1


def count_simplified(case, fixed, *, plan_limits=None, **simplify_limits):
    """Charge conditioning, simplification and plan construction on every call."""
    from cmbench.backends.projected_counts import ProjectedCNFCountPlan
    reduced = simplify_projected(case['n'], case['clauses'], case['projected'], fixed, **simplify_limits)
    if reduced.unsatisfiable: return 0, reduced.stats
    if not reduced.clauses: return 1 << len(reduced.projected), reduced.stats
    names = tuple(f'x{i}' for i in range(reduced.n))
    plan = ProjectedCNFCountPlan(reduced.clauses, names, tuple(names[i] for i in reduced.projected), **(plan_limits or {}))
    return plan.count({}), {**reduced.stats, 'plan':plan.stats}
