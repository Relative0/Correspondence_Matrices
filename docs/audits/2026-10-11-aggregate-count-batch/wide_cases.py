"""Small analytical BDD controls; no wide truth-table allocations."""
from itertools import product
import random

from cmbench.comparative.exact_cudd_count import exact_cudd_count


def check(manager, root, expected, label, rows):
    actual = exact_cudd_count(manager, root)
    assert actual == expected, (label, actual, expected)
    assert actual + exact_cudd_count(manager, ~root) == 1 << len(manager.vars), label
    rows.append(dict(case=label, width=len(manager.vars), count=str(actual), passed=True))


def analytical(BDD):
    rows = []
    for width in (0, 1, 2, 53, 54, 65, 100, 512, 2048):
        manager = BDD()
        manager.configure(reordering=False)
        names = tuple(f'x{i}' for i in range(width))
        manager.declare(*names)
        check(manager, manager.true, 1 << width, 'constant_true', rows)
        check(manager, manager.false, 0, 'constant_false', rows)
        if not width:
            continue
        for position in sorted({0, width//2, width-1}):
            check(manager, manager.var(names[position]), 1 << (width-1), 'skipped_levels_var_'+str(position), rows)
        active = names[:min(width, 16)]
        disjunction, conjunction = manager.false, manager.true
        for name in active:
            disjunction |= manager.var(name)
            conjunction &= manager.var(name)
        check(manager, disjunction, ((1 << len(active))-1) << (width-len(active)), 'disjunction', rows)
        check(manager, conjunction, 1 << (width-len(active)), 'conjunction', rows)
        if width >= 3:
            first, middle, last = [manager.var(names[i]) for i in (0, width//2, width-1)]
            root = (first & middle) | (~first & last)
            check(manager, root, 1 << (width-1), 'shared_mux', rows)
            check(manager, manager.apply('xor', first, last), 1 << (width-1), 'xor', rows)
            # Reordering is completed before traversal; mutation during traversal
            # remains outside the exact helper's documented contract.
            if width <= 100:
                manager.reorder({name: width-i-1 for i, name in enumerate(names)})
                check(manager, root, 1 << (width-1), 'mux_reordered', rows)
                check(manager, disjunction, ((1 << len(active))-1) << (width-len(active)), 'disjunction_reordered', rows)
            fixed = {names[0]: True, names[width//2]: True}
            restricted = manager.let(fixed, root)
            check(manager, restricted, 1 << width, 'restriction_declared_axes', rows)
            assert exact_cudd_count(manager, restricted) >> len(fixed) == 1 << (width-len(fixed))
            all_fixed = {name: True for name in names}
            assert exact_cudd_count(manager, manager.let(all_fixed, root)) >> width == 1
            all_fixed[names[width//2]] = False
            assert exact_cudd_count(manager, manager.let(all_fixed, root)) == 0
            rows.append(dict(case='all_fixed_contexts', width=width, passed=True))
            projected = manager.exist([names[-1]], manager.apply('xor', first, last))
            check(manager, projected, 1 << width, 'existential_projection_declared_axes', rows)
            assert exact_cudd_count(manager, projected) >> (width-2) == 4
    # This exact result is unrepresentable by a binary64 count.
    manager = BDD(); manager.configure(reordering=False)
    manager.declare(*(f'x{i}' for i in range(100)))
    root = manager.false
    for name in manager.vars:
        root |= manager.var(name)
    check(manager, root, (1 << 100)-1, 'full_or_precision_boundary', rows)
    check(manager, ~root, 1, 'full_or_complement', rows)
    return rows


def exhaustive(BDD):
    rows = []
    rng = random.Random(20261011)
    for case in range(24):
        width = 1 + case % 8
        names = tuple(f'x{i}' for i in range(width))
        clauses = tuple(tuple(rng.choice((-1, 1))*(rng.randrange(width)+1)
                              for _ in range(rng.randrange(4)))
                        for _ in range(rng.randrange(10)))
        satisfying = [bits for bits in product((False, True), repeat=width)
                      if all(any(bits[abs(lit)-1] == (lit > 0) for lit in clause) for clause in clauses)]
        manager = BDD(); manager.configure(reordering=False); manager.declare(*names)
        root = manager.true
        for clause in clauses:
            term = manager.false
            for literal in clause:
                var = manager.var(names[abs(literal)-1])
                term |= var if literal > 0 else ~var
            root &= term
        for reordered in (False, True):
            if reordered:
                manager.reorder({name: width-i-1 for i, name in enumerate(names)})
            check(manager, root, len(satisfying), f'exhaustive_{case}_reordered_{reordered}', rows)
            fixed = {name: bool(rng.randrange(2)) for name in names[:min(3, width)]}
            expected = sum(all(bits[names.index(name)] == value for name, value in fixed.items())
                           for bits in satisfying)
            restricted = manager.let(fixed, root)
            actual = exact_cudd_count(manager, restricted)
            assert actual % (1 << len(fixed)) == 0
            assert actual >> len(fixed) == expected
            visible = names[:min(3, width)]
            projected = manager.exist(names[len(visible):], root)
            expected = len({bits[:len(visible)] for bits in satisfying})
            assert exact_cudd_count(manager, projected) >> (width-len(visible)) == expected
            rows.append(dict(case=f'contexts_and_projection_{case}_reordered_{reordered}', width=width, passed=True))
    return rows


def integer_buckets():
    from cmbench.backends.bucket_counts import BucketCNFCountPlan
    from cmbench.backends.bucket_numpy import NumpyBucketCNFCountPlan
    rows = []
    for width in (65, 100, 512, 2048):
        names = tuple(f'x{i}' for i in range(width))
        for clauses, expected, label in [([], 1 << width, 'free'),
                                         ([(1, 2)], 3 << (width-2), 'single_clause'),
                                         ([(1,), (-2,)], 1 << (width-2), 'forced'),
                                         ([(1,), (-1,)], 0, 'contradiction')]:
            plan = BucketCNFCountPlan(clauses, names)
            array_plan = NumpyBucketCNFCountPlan(plan)
            assert plan.count() == array_plan.count() == expected
            assert plan.count({names[-1]: False}) == array_plan.count({names[-1]: False}) == expected//2
            rows.append(dict(case='bucket_'+label, width=width, count=str(expected), passed=True))
    return rows
