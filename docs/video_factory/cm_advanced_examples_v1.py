"""Runnable course examples. No network, benchmark, or external mutation."""
from pathlib import Path
import itertools,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from cm_exprlib import Var,And,Or,Xor,Not
from cm_build import compile_expr_to_cm,eval_cm_boolean
from cm_build_lazy import compile_expr_to_cm_lazy
from cm_ir import compile_expr,materialize_cm,expr_structural_hash
from bitset_backend import eval_cm_node_bitset,bitset_to_bool_array

def run_examples():
    A,B,C,D=[Var(i) for i in range(4)]
    rule=Xor(And(A,B),Or(C,D))
    compiled=compile_expr(rule)
    names=['x0','x1','x2','x3']
    layouts=[(['x0','x1'],['x2','x3']),(['x0','x2'],['x1','x3']),(['x0','x3'],['x1','x2'])]
    outputs=[]
    for rows,cols in layouts:
        array=compile_expr_to_cm(rule,rows,cols,{})
        reused=materialize_cm(compiled.node,rows,cols,{})
        assert np.array_equal(array,reused)
        assert np.array_equal(array,compile_expr_to_cm_lazy(rule,rows,cols,{}))
        checks=[]
        for bits in itertools.product((0,1),repeat=4):
            assignment=dict(zip(names,bits));a,b,c,d=bits
            expected=(a&b)^(c|d)
            got=eval_cm_boolean(array,rows,cols,assignment,{})
            assert got==expected
            checks.append(dict(bits=bits,value=got))
        outputs.append(dict(rows=rows,cols=cols,matrix=array.astype(int).tolist(),checks=checks))
    packed=eval_cm_node_bitset(compiled.node,names)
    vector=bitset_to_bool_array(packed,4).astype(int).tolist()
    oracle=[(a&b)^(c|d) for a,b,c,d in itertools.product((0,1),repeat=4)]
    assert vector==oracle
    assert packed.bit_count()==sum(oracle)
    # A small policy: authenticated AND (owner OR admin) AND NOT suspended.
    auth,owner,admin,suspended=[Var(i) for i in range(4)]
    policy=And(And(auth,Or(owner,admin)),Not(suspended))
    cp=compile_expr(policy)
    pm=materialize_cm(cp.node,names[:2],names[2:],{})
    cases=[]
    for bits in itertools.product((0,1),repeat=4):
        a,o,d,s=bits;want=int(a and (o or d) and not s)
        got=eval_cm_boolean(pm,names[:2],names[2:],dict(zip(names,bits)),{})
        assert got==want;cases.append(dict(bits=bits,allow=got))
    # Same semantics need not have the same structural identity.
    left=And(A,Or(B,C));right=Or(And(A,B),And(A,C))
    same_semantics=all((a and (b or c))==((a and b) or (a and c)) for a,b,c in itertools.product((0,1),repeat=3))
    assert same_semantics
    hashes_differ=expr_structural_hash(left)!=expr_structural_hash(right)
    assert hashes_differ
    # No wall-clock performance claim: a declared hypothetical cost model.
    build_ms,direct_ms,query_ms=120,3,.5
    crossover=build_ms/(direct_ms-query_ms)
    assert crossover==48 and build_ms+49*query_ms<49*direct_ms
    return dict(layouts=outputs,packed_integer=packed,truth_vector=vector,true_count=packed.bit_count(),policy_matrix=pm.astype(int).tolist(),policy_cases=cases,policy_allowed=sum(x['allow'] for x in cases),different_structural_hashes_for_equivalent_formulas=hashes_differ,hypothetical_break_even_queries=crossover,mode='local_exhaustive_examples_no_benchmark')

if __name__=='__main__':
    result=run_examples()
    out=ROOT/'docs/video_factory/deep_series/advanced_cm_tutorial_series_v1'
    out.mkdir(exist_ok=True,parents=True)
    (out/'REPOSITORY_EXAMPLES_QA_V1.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['layouts','policy_cases']}))
