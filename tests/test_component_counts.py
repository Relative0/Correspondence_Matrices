from itertools import product
import random
import pytest

from cmbench.backends.bucket_counts import CountPlanLimit
from cmbench.comparative.component_counts import count_components

def exhaustive(case,fixed):
    answers=set()
    for bits in product((0,1),repeat=case['n']):
        if any(bits[int(k[1:])]!=v for k,v in fixed.items()):continue
        if all(any(bits[abs(v)-1]==(v>0) for v in c) for c in case['clauses']):
            answers.add(tuple(bits[v] for v in case['projected']))
    return len(answers)

@pytest.mark.parametrize('seed',range(8))
def test_random_projected_conditioning_matches_exhaustive(seed):
    rng=random.Random(2026091200+seed)
    for n in range(8):
        for _ in range(20):
            clauses=[[v+1 if rng.randrange(2) else -v-1 for v in rng.sample(range(n),rng.randrange(n+1))]
                     for _ in range(rng.randrange(12))]
            case=dict(n=n,clauses=clauses,projected=rng.sample(range(n),rng.randrange(n+1)))
            fixed={f'x{v}':rng.randrange(2) for v in rng.sample(range(n),rng.randrange(n+1))}
            expected=exhaustive(case,fixed)
            assert count_components(case,fixed)[0]==expected
            assert count_components(case,fixed,max_cache_entries=0)[0]==expected

def test_components_include_hidden_coupling_and_do_not_multiply_witnesses():
    case=dict(n=3,projected=[0,1],clauses=[[1,3],[2,-3]])
    assert count_components(case)[0]==3
    assert count_components(case,{'x2':1})[0]==2
    assert count_components(dict(n=2,projected=[],clauses=[[1,2]]))[0]==1

def test_large_factored_exact_count_and_free_selected_axes():
    case=dict(n=258,projected=list(range(0,258,2)),clauses=[[2*i+1,2*i+2] for i in range(128)])
    value,stats=count_components(case)
    assert value==1<<129
    assert stats['component_splits']>0
    assert count_components(case,{'x256':0})[0]==1<<128

def test_wide_clause_has_no_truth_table_width_requirement():
    case=dict(n=64,projected=list(range(64)),clauses=[list(range(1,65))])
    assert count_components(case)[0]==(1<<64)-1

def test_units_tautologies_duplicates_and_empty_formula():
    assert count_components(dict(n=3,projected=[0,1,2],clauses=[[1,-1],[2,2],[2]]))[0]==4
    assert count_components(dict(n=3,projected=[0],clauses=[[1],[-1]]))[0]==0
    assert count_components(dict(n=0,projected=[],clauses=[]))[0]==1
    assert count_components(dict(n=0,projected=[],clauses=[[]]))[0]==0

@pytest.mark.parametrize('bound', ['max_vars','max_clauses','max_literals','max_nodes','max_work','max_depth'])
def test_exhausted_limits_refuse_instead_of_returning_partial_count(bound):
    case=dict(n=3,projected=[0,1,2],clauses=[[1,2,3]])
    with pytest.raises(CountPlanLimit):count_components(case,**{bound:0})

@pytest.mark.parametrize('case,fixed',[
    (dict(n=2,projected=[0,0],clauses=[]),{}),
    (dict(n=2,projected=[True],clauses=[]),{}),
    (dict(n=2,projected=[0],clauses=[[0]]),{}),
    (dict(n=2,projected=[0],clauses=[]),{'x2':1}),
    (dict(n=2,projected=[0],clauses=[]),{'x0':2}),
])
def test_invalid_contract_is_rejected(case,fixed):
    with pytest.raises(ValueError):count_components(case,fixed)
