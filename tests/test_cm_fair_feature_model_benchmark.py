import json
import unittest
from scripts.cm_fair_feature_model_benchmark import Engine, columns, scalar, graph_value
from scripts.cm_fair_feature_model_verify import replay


class FairContracts(unittest.TestCase):
    def test_column_axis_order(self):
        for k in (3,8,12,16):
            full,pats=columns(k)
            self.assertEqual(full.bit_length(),1<<k)
            for v in range(k):
                for a in (0,1,(1<<k)-1,1<<v):
                    self.assertEqual((pats[v]>>a)&1,(a>>v)&1)

    def test_exact_fresh_and_structural_reload(self):
        cases=[{'k':8,'clauses':c} for c in ([],[[]],[[1,-2],[3]],[[1,2],[-1,3],[8,-3]])]
        arms=['cm','cse','cnf']
        try:
            from dd import cudd
            arms+=['cudd_fixed','cudd_sift']
        except ImportError: pass
        for case in cases:
            expected=scalar(case)
            for arm in arms:
                with self.subTest(case=case,arm=arm):
                    e=Engine(arm,case)
                    self.assertEqual(e.evaluate(),expected)
                    self.assertEqual(e.evaluate(),expected)
                    b=json.loads(json.dumps(e.bundle()))
                    self.assertEqual(replay(b),expected)
                    self.assertEqual(set(b),{'schema','arm','k','variable_universe','structure'})
                    loaded=Engine(arm,case,b)
                    self.assertEqual(loaded.evaluate(),expected)
                    if arm.startswith('cudd'):
                        self.assertEqual(graph_value(b['structure'],case['k']),expected)
                        self.assertFalse(e.configuration['reordering'])
                    loaded.close()
                    e.close()

    def test_saved_variable_order_is_not_level_identity(self):
        # x2 then x0, deliberately different from natural variable indices.
        data={'nodes':[['x0',-1,-2],['x2',-1,0]],'root':1,
              'order':['x2','x0','x1','x3','x4','x5','x6','x7']}
        case={'k':8,'clauses':[[3],[1]]}
        self.assertEqual(graph_value(data,8),scalar(case))
        try: from dd import cudd
        except ImportError: self.skipTest('native CUDD checked in Linux preflight')
        b={'structure':data}
        loaded=Engine('cudd_sift',case,b)
        self.assertEqual(loaded.evaluate(),scalar(case))
        loaded.close()

    def test_rejects_answer_cache_and_cyclic_graph(self):
        case={'k':8,'clauses':[[1,-2]]}
        b=json.loads(json.dumps(Engine('cm',case).bundle()))
        b['cached_answer']='ff'
        with self.assertRaises(AssertionError): replay(b)
        graph={'schema':'cm-fair-fm-structure/v1','arm':'cudd_sift','k':8,
            'variable_universe':[f'x{i}' for i in range(8)],
            'structure':{'nodes':[['x0',0,-2]],'root':0,'order':[f'x{i}' for i in range(8)]}}
        with self.assertRaises(AssertionError): replay(graph)


if __name__=='__main__': unittest.main()
