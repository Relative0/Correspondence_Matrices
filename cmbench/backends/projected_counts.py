"""Bounded exact CNF projection: count distinct selected-variable assignments."""
from cmbench.backends.bucket_counts import BucketCNFCountPlan
from cmbench.backends.packed_mask_cache import ordered_basis


class ProjectedCNFCountPlan(BucketCNFCountPlan):
    """Return |{p : there exists h such that CNF(p, h) and fixed}|.

    ``projected_names`` selects the counted variables. All other declared
    variables are existential; multiple auxiliary witnesses contribute once.
    Fixed assignments can mention either group. Empty projection returns 0/1.
    The inherited exact guards apply to the projection-constrained schedule,
    which can be wider than an unrestricted full-count schedule.
    """

    def __init__(self, clauses, names, projected_names, **limits):
        basis = ordered_basis(names)
        self.projected_names = ordered_basis(projected_names)
        if not set(self.projected_names).issubset(basis):
            raise ValueError('projected variable outside basis')
        if '_existential' in limits:
            raise ValueError('existential schedule is determined by projected_names')
        hidden = tuple(i for i, name in enumerate(basis) if name not in self.projected_names)
        super().__init__(clauses, basis, _existential=hidden, **limits)
        self.stats = {**self.stats, 'projected_variables':len(self.projected_names),
                      'existential_variables':len(hidden), 'semantics':'distinct_projected_assignments'}
