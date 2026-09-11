from itertools import product
import random

import pytest

from cmbench.comparative.projected_simplify import simplify_projected, count_simplified


def brute(n, clauses, selected, fixed=None):
    answers=set()
    for values in product((0,1),repeat=n):
        if any(values[int(k[1:])]!=v for k,v in (fixed or {}).items()):continue
        if all(any(values[abs(v)-1]==(v>0) for v in clause) for clause in clauses):
            answers.add(tuple(values[i] for i in selected))
    return len(answers)


@pytest.mark.parametrize('seed',range(12))
def test_simplification_matches_exhaustive_projection_and_conditioning(seed):
    rng=random.Random(seed)
    for n in range(1,8):
        for _ in range(12):
            clauses=[[v+1 if rng.randrange(2) else -v-1 for v in rng.sample(range(n),rng.randrange(0,min(n,4)+1))] for _ in range(rng.randrange(0,12))]
            selected=rng.sample(range(n),rng.randrange(n+1))
            fixed={f'x{v}':rng.randrange(2) for v in rng.sample(range(n),rng.randrange(min(n,3)+1))}
            case=dict(n=n,clauses=clauses,projected=selected)
            expected=brute(n,clauses,selected,fixed)
            reduced=simplify_projected(n,clauses,selected,fixed)
            assert brute(reduced.n,reduced.clauses,reduced.projected)==expected
            assert count_simplified(case,fixed)[0]==expected


def test_hidden_multiple_witnesses_do_not_multiply_count():
    case=dict(n=4,clauses=[[1,2],[-1,3]],projected=[0,3])
    assert count_simplified(case,{})[0]==4
    assert count_simplified(case,{'x1':0,'x2':0})[0]==0
    assert count_simplified(case,{'x0':1})[0]==2


def test_resolution_eliminates_only_hidden_axes_and_preserves_free_selected_axes():
    case=dict(n=4,clauses=[[1,2],[-1,3]],projected=[1,2,3])
    reduced=simplify_projected(**case)
    assert reduced.stats['resolved_hidden']==1
    assert count_simplified(case,{})[0]==6
    assert count_simplified(case,{},max_work=0)[0]==6


def test_empty_projection_and_inconsistent_units():
    assert count_simplified(dict(n=3,clauses=[],projected=[]),{})[0]==1
    assert count_simplified(dict(n=3,clauses=[[1],[-1]],projected=[]),{})[0]==0


def test_invalid_projection_and_assignments_are_rejected():
    with pytest.raises(ValueError):simplify_projected(3,[],[1,1])
    with pytest.raises(ValueError):simplify_projected(3,[[0]],[1])
    with pytest.raises(ValueError):simplify_projected(3,[],[1],{'x3':0})
