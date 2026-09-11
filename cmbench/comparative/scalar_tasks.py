"""Explicit scalar-plan integration for the existing bounded task contracts."""
from cmbench.backends.affine_constraints import AffineConstraintPlan
from cmbench.backends.bucket_counts import BucketCNFCountPlan
from cmbench.backends.bucket_numpy import NumpyBucketCNFCountPlan
from cmbench.backends.factorized_counts import FactorizedCountPlan
from cmbench.backends.packed_mask_cache import PackedMaskCache
from cmbench.backends.packed_queries import IndependentCountPlan
from scripts.cm_measurement_verify import _expression


class ScalarTaskSession:
    """Reuse plans within one validated caller-owned scenario; no global router.

    This adapter is deliberately bounded by the existing task validation. It
    does not reinterpret arbitrary CNF as affine, produce witnesses or hide a
    refused plan behind an uncharged fallback.
    """

    def __init__(self, scenario, backend, lifecycle, counters):
        self.scenario, self.backend, self.lifecycle, self.counters = scenario, backend, lifecycle, counters
        self.names = tuple(f'x{i}' for i in range(scenario['k']))
        self.plans = {}
        self.cache = PackedMaskCache(max_bytes=1 << 20, max_width=8)
        if lifecycle == 'resident_engine': counters['engine_instances'] += 1

    def build(self, version):
        clauses = self.scenario['versions'][version]['clauses']
        if self.backend == 'bucket_count': plan = BucketCNFCountPlan(clauses,self.names)
        elif self.backend == 'array_count': plan = NumpyBucketCNFCountPlan.from_cnf(clauses,self.names)
        else:
            expression = _expression(clauses)
            if self.backend == 'affine_count': plan = AffineConstraintPlan.from_expr(expression,self.names)
            elif self.backend == 'factorized_count': plan = FactorizedCountPlan.from_expr(expression,self.names,cache=self.cache)
            elif self.backend == 'independent_count': plan = IndependentCountPlan.from_expr(expression,self.names,cache=self.cache)
            else: raise ValueError('unsupported scalar task backend')
        self.counters['programs_built'] += 1
        return plan

    def count(self, version, assumptions):
        fixed = {}
        for literal in assumptions:
            name, value = self.names[abs(literal)-1], int(literal > 0)
            if name in fixed and fixed[name] != value: return 0
            fixed[name] = value
        fresh = self.lifecycle == 'fresh_engine'
        if fresh: self.counters['engine_instances'] += 1
        try:
            if not fresh and version in self.plans:
                plan = self.plans[version]
                self.counters['program_cache_hits'] += 1
            else:
                plan = self.build(version)
                if not fresh: self.plans[version] = plan
            return plan.count(fixed)
        finally:
            if fresh: self.cache.clear()

    def close(self):
        self.plans.clear()
        self.cache.clear()
