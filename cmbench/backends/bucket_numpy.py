"""Opt-in exact object-array execution of a bounded CNF elimination plan."""
from __future__ import annotations

from math import prod

import numpy as np

from cmbench.backends.bucket_counts import BucketCNFCountPlan, CountPlanLimit


class NumpyBucketCNFCountPlan:
    """Reuse the bucket schedule with private, arbitrary-precision query arrays.

    ``max_array_cells`` bounds explicit array entries plus retained Python input
    table entries, not bytes/RSS or NumPy's internal iterator buffers. The base
    plan's width, work and ordering limits still apply. Array admission runs
    before conversion; base-plan admission precedes its own table allocation.
    """

    def __init__(self, plan, *, max_array_cells=1 << 18):
        if not isinstance(plan, BucketCNFCountPlan): raise TypeError('expected a bucket CNF plan')
        if type(max_array_cells) is not int or max_array_cells < 0:
            raise ValueError('max_array_cells must be a nonnegative integer')
        initial = plan.stats['initial_cells']
        peak, live, intermediates = 2 * initial, 0, {}
        # Schedule fields belong to BucketCNFCountPlan. Projection positions are
        # sorted union-scope axes, with axis zero the least-significant row bit.
        for _, bucket, _, _, target, size in plan._schedule:
            joint_cells = 2 * size
            # Includes joint, reduction/selection, possible flatten copy and a
            # spare full joint. Retained original tables are never discounted.
            peak = max(peak, 2 * initial + live + 4 * joint_cells)
            for i in bucket: live -= intermediates.pop(i, 0)
            intermediates[target] = size; live += size
        if peak > max_array_cells: raise CountPlanLimit('array table budget exceeded')
        self._plan = plan
        self.basis = plan.basis
        self.stats = dict(plan.stats, array_cells_bound=peak, array_dtype='object')
        self._tables = tuple(np.array(t, dtype=object) for t in plan._tables)
        for table in self._tables: table.flags.writeable = False

    @classmethod
    def from_cnf(cls, clauses, names, *, max_array_cells=1 << 18, **limits):
        return cls(BucketCNFCountPlan.from_cnf(clauses, names, **limits), max_array_cells=max_array_cells)

    @classmethod
    def from_expr(cls, expr, names, *, max_array_cells=1 << 18, **limits):
        return cls(BucketCNFCountPlan.from_expr(expr, names, **limits), max_array_cells=max_array_cells)

    @classmethod
    def from_cm_node(cls, node, names, *, max_array_cells=1 << 18, **limits):
        return cls(BucketCNFCountPlan.from_cm_node(node, names, **limits), max_array_cells=max_array_cells)

    def count(self, fixed=None):
        plan = self._plan
        supplied = dict(fixed or {})
        if any(n not in plan._positions for n in supplied): raise ValueError('fixed variable outside basis')
        if any(type(v) not in (int, bool) or v not in (0, 1) for v in supplied.values()):
            raise ValueError('fixed values must be Boolean')
        context = {plan._positions[n]: int(v) for n, v in supplied.items()}
        if not plan._consistent or any(v in context and context[v] != b for v, b in plan._forced.items()):
            return 0
        tables = dict(enumerate(self._tables))
        for variable, bucket, position, projections, target, size in plan._schedule:
            width = size.bit_length()
            joint = np.ones((2,) * width, dtype=object, order='F')
            for i, mapping in zip(bucket, projections):
                shape = tuple(2 if axis in mapping else 1 for axis in range(width))
                np.multiply(joint, tables[i].reshape(shape, order='F'), out=joint)
            if variable in context:
                # take allocates: a retained view could keep a full joint alive.
                result = np.take(joint, context[variable], axis=position)
            else:
                result = np.sum(joint, axis=position, dtype=object)
            result = np.asarray(result, dtype=object).reshape(-1, order='F')
            del joint
            for i in bucket: del tables[i]
            tables[target] = result
        return int(prod(tables[i][0] for i in plan._final)) << len(plan._unused - context.keys())

    def exists(self, fixed=None):
        return bool(self.count(fixed))
