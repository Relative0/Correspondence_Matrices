"""PySDD 1.0.6 live local moves. No truth/oracle data enters this module.

The CNF is compiled once per session. Candidate scoring uses only root size
and the certified direct partition (Phase 5B M2, unchanged).
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter_ns

from pysdd.sdd import SddManager, Vtree
from reference.hybrid_core import _write_vtree, _sdd_tree, _extract_sdd, canonical, leaves
from reference.benchmark import objective


def subtree(tree, path):
    for side in path:
        tree = tree[side]
    return tree


def replace(tree, path, value):
    if not path:
        return value
    side, *tail = path
    children = list(tree)
    children[side] = replace(children[side], tail, value)
    return tuple(children)


def target_tree(tree, path, kind):
    a, b = subtree(tree, path)
    if kind == 'swap':
        target = b, a
    elif kind == 'left':
        target = (a, b[0]), b[1]
    elif kind == 'right':
        target = a[0], (a[1], b)
    else:
        raise ValueError(kind)
    return replace(tree, path, target)


def candidates(tree):
    """Exactly Phase 5B's tuple-neighbor set/order, with operation descriptors."""
    result = []
    def visit(t, path):
        if isinstance(t, int):
            return
        kinds = ['swap']
        if not isinstance(t[0], int):
            kinds.append('right')
        if not isinstance(t[1], int):
            kinds.append('left')
        for kind in kinds:
            result.append((path, kind, target_tree(tree, path, kind)))
        visit(t[0], path + (0,))
        visit(t[1], path + (1,))
    visit(tree, ())
    return sorted(result, key=lambda x: repr(x[2]))


def score(snapshot):
    return objective('M2', snapshot, [], [], len(leaves(snapshot['tree'])))


class LiveSession:
    def __init__(self, n, clauses, tree=None, *, prepared_vtree=None, collect=True):
        start = perf_counter_ns()
        self.n = n
        self.compile_count = 1
        if prepared_vtree is None:
            if sorted(leaves(tree)) != list(range(1, n + 1)):
                raise ValueError('Expected vtree variables 1..n')
            with TemporaryDirectory(prefix='live-vtree-probe-') as tmp:
                path = Path(tmp) / 'input.vtree'
                _write_vtree(tree, path)
                vtree = Vtree.from_file(str(path).encode())
        else:
            vtree = prepared_vtree
        parsed = perf_counter_ns()
        self.manager = SddManager.from_vtree(vtree)
        self.manager.auto_gc_and_minimize_off()
        initialized = perf_counter_ns()
        root = self.manager.true()
        for clause in clauses:
            disjunction = self.manager.false()
            for lit in clause:
                disjunction = self.manager.disjoin(disjunction, self.manager.literal(lit))
            root = self.manager.conjoin(root, disjunction)
        root.ref()  # Never chain ref(): PySDD 1.0.6 actually returns None.
        self.root = root
        self.extra_roots = []
        compiled = perf_counter_ns()
        self.compile_ns = compiled - start
        self.compile_core_ns = compiled - parsed  # manager construction + CNF Apply
        self.cnf_apply_ns = compiled - initialized
        if collect:
            self.manager.garbage_collect()
        self.initial_gc_ns = perf_counter_ns() - compiled
        if collect:
            assert self.manager.dead_count() == 0

    def snapshot(self):
        # A fresh manager-owned root is essential after every rotation.
        vtree = self.manager.vtree()
        return {'tree': _sdd_tree(vtree), 'sdd_size': int(self.root.size()),
                'sdd_count': int(self.root.count()),
                'satisfiable': not self.root.is_false(),
                'direct_partition': None if self.root.is_false() else
                    canonical(_extract_sdd(self.root, vtree))}

    def move(self, path, kind, limited=0):
        # Reference every root that must survive before entering this function.
        self.manager.garbage_collect()
        assert self.manager.dead_count() == 0
        v = self.manager.vtree()
        for side in path:
            if v.is_leaf() or side not in (0, 1):
                raise ValueError('Invalid subtree path')
            v = v.left() if side == 0 else v.right()
        if v.is_leaf():
            raise ValueError('Cannot move a leaf')
        if kind == 'swap':
            operation = v.swap
        elif kind == 'left' and not v.right().is_leaf():
            # (A,(B,C)) -> ((A,B),C): call on the RIGHT CHILD.
            operation = v.right().rotate_left
        elif kind == 'right' and not v.left().is_leaf():
            # ((A,B),C) -> (A,(B,C)): call on the SUBTREE ROOT.
            operation = v.rotate_right
        else:
            raise ValueError('Invalid rotation or unknown move')
        start = perf_counter_ns()
        succeeded = operation(self.manager, limited)
        native_ns = perf_counter_ns() - start
        assert self.manager.dead_count() == 0
        return int(succeeded), native_ns

    def undo(self, path, kind):
        # An inverse is unlimited: a capped inverse may fail to restore a parent.
        inverse = {'swap': 'swap', 'left': 'right', 'right': 'left'}[kind]
        ok, ns = self.move(path, inverse, limited=0)
        if ok != 1:
            raise RuntimeError('Uncapped inverse failed; discard this session')
        return ns

    def one_round(self):
        """Score each neighbor, undo, then replay the best move; zero CNF rebuilds."""
        parent = self.snapshot()
        if not parent['satisfiable']:
            return None
        best, chosen = score(parent), None
        for path, kind, target in candidates(parent['tree']):
            ok, _ = self.move(path, kind)
            if ok != 1:
                raise RuntimeError('Uncapped candidate failed')
            try:
                candidate = self.snapshot()
                assert candidate['tree'] == target
                if score(candidate) < best:
                    best, chosen = score(candidate), (path, kind)
            finally:
                self.undo(path, kind)
            assert self.snapshot() == parent
        if chosen is not None:
            ok, _ = self.move(*chosen)
            assert ok == 1
        assert self.compile_count == 1
        return chosen

    def close(self):
        for node in self.extra_roots:
            node.deref()
        self.extra_roots.clear()
        self.root.deref()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
