"""The independent recurrence and native projection oracle need their own checks."""
from itertools import product
import pytest
from scripts.cm_next_count_campaign import analytic, runner
from tests.test_projected_counts import oracle


def cases():
    for m in (1, 3):
        for family in ('independent_aux','adjacent_exclusion','hidden_star'):
            star = family == 'hidden_star'
            clauses = [(i+1,m+1) if star else (2*i+1,2*i+2) for i in range(m)]
            if family == 'adjacent_exclusion': clauses += [(-2*i-1,-2*i-3) for i in range(m-1)]
            yield dict(n=m+1 if star else 2*m, projected=list(range(m)) if star else list(range(0,2*m,2)),
                       clauses=clauses, family=family)


def test_recurrence_against_enumeration_for_every_partial_context():
    for case in cases():
        basis = tuple(f'x{i}' for i in range(case['n']))
        for mode in ('full','projected'):
            selected = tuple(basis[i] for i in case['projected']) if mode == 'projected' else basis
            for state in product((None,0,1), repeat=case['n']):
                fixed = {n:v for n,v in zip(basis,state) if v is not None}
                assert analytic(case,mode,fixed) == oracle(case['clauses'],basis,selected,fixed)


def test_native_projected_oracle_accounts_for_fixed_and_unused_variables():
    pytest.importorskip('dd.cudd')
    case = dict(n=4, clauses=[(1,2),(-2,3)], projected=[0,2,3])
    basis = tuple(f'x{i}' for i in range(case['n']))
    for mode in ('full','projected'):
        selected = tuple(basis[i] for i in case['projected']) if mode == 'projected' else basis
        for method in ('cudd_natural','cudd_dynamic'):
            count, _ = runner(case,mode,method)
            for state in product((None,0,1), repeat=4):
                fixed = {n:v for n,v in zip(basis,state) if v is not None}
                assert count(fixed) == oracle(case['clauses'],basis,selected,fixed)
