"""Exact PySDD extraction and persistent PySAT four-corner residual solver.

Variables, CNF literals and tuple-vtree leaves are all one based.  The only
semantic information consumed by heuristic callers is certified direct blocks
and SAT defect supports; no ground-truth partition is accepted by these APIs.
"""
from __future__ import annotations

from itertools import combinations, product
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter


def canonical(partition):
    return sorted((sorted(block) for block in partition), key=lambda x: tuple(x))


def leaves(tree):
    return [tree] if isinstance(tree, int) else leaves(tree[0]) + leaves(tree[1])


def balanced_tree(variables):
    variables = list(variables)
    if len(variables) == 1:
        return variables[0]
    if not variables:
        raise ValueError("A vtree must contain at least one variable")
    mid = len(variables) // 2
    return balanced_tree(variables[:mid]), balanced_tree(variables[mid:])


def _validate(n, clauses, partition=None):
    if n < 1 or any(lit == 0 or abs(lit) > n for c in clauses for lit in c):
        raise ValueError("Expected n >= 1 and nonzero CNF literals in 1..n")
    if partition is not None:
        if any(not b for b in partition) or sorted(v for b in partition for v in b) != list(range(1, n + 1)):
            raise ValueError("Blocks must partition 1..n exactly")


def _write_vtree(tree, filename):
    records = []

    def visit(t):
        if isinstance(t, int):
            i = len(records)
            records.append(f"L {i} {t}")
            return i
        left, right = visit(t[0]), visit(t[1])
        i = len(records)
        records.append(f"I {i} {left} {right}")
        return i

    visit(tree)
    Path(filename).write_text("vtree " + str(len(records)) + "\n" + "\n".join(records) + "\n", encoding="ascii")


def _sdd_tree(vtree):
    if vtree.is_leaf():
        return int(vtree.var())
    return _sdd_tree(vtree.left()), _sdd_tree(vtree.right())


def _extract_sdd(node, vtree):
    """Normalize trimmed SDD nodes against the currently declared vtree scope."""
    scope = sorted(leaves(_sdd_tree(vtree)))
    if node.is_false():
        raise ValueError("The nonfalse-factorization contract excludes false")
    if node.is_true() or node.is_literal() or vtree.is_leaf():
        return [[v] for v in scope]
    location = node.vtree()
    if location.position() != vtree.position():
        node_scope = set(leaves(_sdd_tree(location)))
        left_scope = set(leaves(_sdd_tree(vtree.left())))
        right_scope = set(scope) - left_scope
        if node_scope <= left_scope:
            return _extract_sdd(node, vtree.left()) + [[v] for v in sorted(right_scope)]
        if node_scope <= right_scope:
            return [[v] for v in sorted(left_scope)] + _extract_sdd(node, vtree.right())
        raise AssertionError("Trimmed node does not lie in one descendant subtree")
    nonfalse = [(p, s) for p, s in node.elements() if not s.is_false()]
    if len(nonfalse) != 1:
        return [scope]
    prime, sub = nonfalse[0]
    return _extract_sdd(prime, vtree.left()) + _extract_sdd(sub, vtree.right())


def compile_extract(n, clauses, tree, minimize=False):
    """Compile an actual reduced/compressed SDD and extract certified factors.

    sdd_size is PySDD root.size(): reachable decision elements, not an emulated
    truth-table quantity. sdd_count is reachable decision nodes. A nonsingleton
    direct block is unresolved, even when the evaluation truth says it is prime.
    """
    from pysdd.sdd import SddManager, Vtree

    clauses = [tuple(c) for c in clauses]
    _validate(n, clauses)
    if sorted(leaves(tree)) != list(range(1, n + 1)):
        raise ValueError("Vtree leaves must be exactly 1..n")
    start = perf_counter()
    with TemporaryDirectory(prefix="phase5b-vtree-") as temp:
        file = Path(temp) / "input.vtree"
        _write_vtree(tree, file)
        vtree = Vtree.from_file(str(file).encode())
        manager = SddManager.from_vtree(vtree)
    manager.auto_gc_and_minimize_off()
    root = manager.true()
    for clause in clauses:
        disjunction = manager.false()
        for lit in clause:
            disjunction = manager.disjoin(disjunction, manager.literal(lit))
        root = manager.conjoin(root, disjunction)
    root.ref()
    compile_seconds = perf_counter() - start
    start = perf_counter()
    if minimize and not root.is_false():
        manager.minimize()
    minimize_seconds = perf_counter() - start if minimize else 0.0
    start = perf_counter()
    final_tree = _sdd_tree(manager.vtree())
    satisfiable = not root.is_false()
    partition = canonical(_extract_sdd(root, manager.vtree())) if satisfiable else None
    extract_seconds = perf_counter() - start
    result = {
        "satisfiable": satisfiable,
        "direct_partition": partition,
        "sdd_size": int(root.size()),
        "sdd_count": int(root.count()),
        "compile_seconds": compile_seconds,
        "minimize_seconds": minimize_seconds,
        "extract_seconds": extract_seconds,
        "tree": final_tree,
    }
    root.deref()
    return result


class FourCornerSession:
    """One fixed Tseitin CNF and one persistent assumption-capable solver.

    The logical construction follows the archived Phase 4 controlled encoder;
    this self-contained reimplementation adds conditional clone equalities for
    support shrinking. All four CNF outputs are equivalences, not implications.
    """

    def __init__(self, n, clauses, solver_name="g4"):
        from pysat.solvers import Solver

        _validate(n, clauses)
        start = perf_counter()
        self.n = n
        self.cnf = []
        self.nvars = 0
        self.sat_calls = 0
        self.sat_seconds = 0.0
        self.selectors = {v: self.new() for v in range(1, n + 1)}
        self.clone = {(v, k): self.new() for v in range(1, n + 1) for k in (0, 1)}
        self.equality = {v: self.new() for v in range(1, n + 1)}
        mux = {}
        for v in range(1, n + 1):
            x0, x1, sel, eq = self.clone[v, 0], self.clone[v, 1], self.selectors[v], self.equality[v]
            self.cnf.extend([[-eq, -x0, x1], [-eq, x0, -x1]])
            for ij, a, b in [((0, 1), x0, x1), ((1, 0), x1, x0)]:
                out = self.new()
                self.cnf.extend([[-sel, -out, a], [-sel, out, -a], [sel, -out, b], [sel, out, -b]])
                mux[v, ij] = out
        self.corner = {}
        for i, j in product((0, 1), repeat=2):
            clause_outputs = []
            for clause in clauses:
                mapped = []
                for lit in clause:
                    v = abs(lit)
                    x = self.clone[v, i] if i == j else mux[v, (i, j)]
                    mapped.append(x if lit > 0 else -x)
                out = self.new()
                self.cnf.append([-out] + mapped)
                self.cnf.extend([[-lit, out] for lit in mapped])
                clause_outputs.append(out)
            self.corner[i, j] = self.and_equiv(clause_outputs)
        p = self.and_equiv([self.corner[0, 0], self.corner[1, 1]])
        q = self.and_equiv([self.corner[0, 1], self.corner[1, 0]])
        self.cnf.extend([[p, q], [-p, -q]])
        self.solver = Solver(name=solver_name, bootstrap_with=self.cnf)
        self.setup_seconds = perf_counter() - start

    def new(self):
        self.nvars += 1
        return self.nvars

    def and_equiv(self, ins):
        out = self.new()
        self.cnf.extend([[-out, x] for x in ins])
        self.cnf.append([out] + [-x for x in ins])
        return out

    def query(self, cut, equal=()):
        cut = set(cut)
        if not cut or len(cut) == self.n or not cut <= set(range(1, self.n + 1)):
            raise ValueError("A cut must be nontrivial")
        assumptions = [s if v in cut else -s for v, s in self.selectors.items()]
        assumptions.extend(self.equality[v] for v in sorted(equal))
        start = perf_counter()
        sat = self.solver.solve(assumptions=assumptions)
        self.sat_seconds += perf_counter() - start
        self.sat_calls += 1
        return set(self.solver.get_model()) if sat else None

    def support(self, model, cut):
        cut = set(cut)
        different = {v for v in range(1, self.n + 1) if (self.clone[v, 0] in model) != (self.clone[v, 1] in model)}
        return different & cut, different - cut

    def witness(self, cut, shrink=True):
        model = self.query(cut)
        if model is None:
            return None
        cut = set(cut)
        U, W = self.support(model, cut)
        initial_width = len(U | W)
        equality_unsat_cores = []
        if shrink:
            support = U | W
            for v in sorted(support):
                if v not in support:
                    continue
                equal = set(range(1, self.n + 1)) - support | {v}
                candidate = self.query(cut, equal)
                if candidate is not None:
                    model = candidate
                    U, W = self.support(model, cut)
                    support = U | W
                else:
                    core = set(self.solver.get_core() or [])
                    equality_unsat_cores.append({"attempted_coordinate": v, "equality_coordinates": [w for w, e in self.equality.items() if e in core]})
            U, W = self.support(model, cut)
        assert U and W
        return {
            "cut": sorted(cut), "U": sorted(U), "W": sorted(W),
            "initial_width": initial_width, "final_width": len(U | W),
            "singleton_must_link": [next(iter(U)), next(iter(W))] if len(U) == len(W) == 1 else None,
            "x0": [int(self.clone[v, 0] in model) for v in range(1, self.n + 1)],
            "x1": [int(self.clone[v, 1] in model) for v in range(1, self.n + 1)],
            "corners": [int(self.corner[i, j] in model) for i, j in product((0, 1), repeat=2)],
            "equality_unsat_cores": equality_unsat_cores,
        }

    def stats(self):
        stats = self.solver.accum_stats()
        return {"sat_calls": self.sat_calls, "sat_seconds": self.sat_seconds,
                "sat_setup_seconds": self.setup_seconds, "encoded_variables": self.nvars,
                "encoded_clauses": len(self.cnf),
                **{k: int(stats.get(k, 0)) for k in ("conflicts", "decisions", "propagations", "restarts")}}

    def close(self):
        self.solver.delete()


def least_common_coarsening(n, *partitions):
    parent = list(range(n + 1))

    def find(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    for partition in partitions:
        _validate(n, [], partition)
        for block in partition:
            for v in block[1:]:
                parent[find(v)] = find(block[0])
    groups = {}
    for v in range(1, n + 1):
        groups.setdefault(find(v), []).append(v)
    return canonical(groups.values())


def exact_refine(n, clauses, direct_partition, carrier=None, solver_name="g4"):
    """Refine certified direct blocks exactly, then apply the carrier LCC.

    Outside blocks stay on the complement side of each global query. This is
    exact because these are independently certified AND factors and f is
    nonfalse. The caller must not supply an arbitrary uncertified partition.
    """
    _validate(n, clauses, direct_partition)
    if carrier is not None:
        _validate(n, [], carrier)
    start = perf_counter()
    nonsingleton = [b for b in direct_partition if len(b) > 1]
    if not nonsingleton:
        semantic = canonical(direct_partition)
        final = least_common_coarsening(n, semantic, carrier) if carrier is not None else semantic
        return {"partition": final, "semantic_partition": semantic, "sat_calls": 0,
                "sat_seconds": 0.0, "sat_setup_seconds": 0.0, "encoded_variables": 0,
                "encoded_clauses": 0, "conflicts": 0, "decisions": 0,
                "propagations": 0, "restarts": 0, "residual_seconds": perf_counter() - start}
    session = FourCornerSession(n, clauses, solver_name)

    def refine(block):
        if len(block) == 1:
            return [block]
        # Every unordered nontrivial bipartition appears once, with block[0]
        # on the left. Small-cardinality first is a fixed, semantic-free rule.
        for r in range(len(block) - 1):
            for extra in combinations(block[1:], r):
                cut = {block[0], *extra}
                if session.query(cut) is None:
                    return refine(sorted(cut)) + refine([v for v in block if v not in cut])
        return [block]

    try:
        semantic = canonical(b for block in direct_partition for b in refine(sorted(block)))
        final = least_common_coarsening(n, semantic, carrier) if carrier is not None else semantic
        stats = session.stats()
    finally:
        session.close()
    return {"partition": final, "semantic_partition": semantic,
            **stats, "residual_seconds": perf_counter() - start}


def probe_defects(n, clauses, cuts, shrink=True, solver_name="g4"):
    start = perf_counter()
    session = FourCornerSession(n, clauses, solver_name)
    try:
        witnesses = []
        separable_cuts = []
        for cut in cuts:
            witness = session.witness(cut, shrink)
            if witness is None:
                separable_cuts.append(sorted(cut))
            else:
                witnesses.append(witness)
        stats = session.stats()
    finally:
        session.close()
    return {"witnesses": witnesses, "hyperedges": witnesses,
            "separable_cuts": separable_cuts, **stats,
            "defect_seconds": perf_counter() - start}


def brute_partition(n, clauses):
    """Independent exhaustive-model baseline: EVALUATION/ORACLE ONLY."""
    models = [bits for bits in product((0, 1), repeat=n)
              if all(any(bool(bits[abs(lit) - 1]) == (lit > 0) for lit in c) for c in clauses)]
    if not models:
        return None

    def refine(variables, relation):
        if len(variables) == 1:
            return [variables]
        for r in range(len(variables) - 1):
            for extra in combinations(range(1, len(variables)), r):
                left = (0, *extra)
                right = tuple(i for i in range(len(variables)) if i not in left)
                lp = {tuple(row[i] for i in left) for row in relation}
                rp = {tuple(row[i] for i in right) for row in relation}
                if len(relation) == len(lp) * len(rp):
                    return refine([variables[i] for i in left], lp) + refine([variables[i] for i in right], rp)
        return [variables]

    return canonical(refine(list(range(1, n + 1)), set(models)))
