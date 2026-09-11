"""Projection must count distinct selected assignments, not auxiliary models."""
from concurrent.futures import ThreadPoolExecutor
from itertools import product
import random
import unittest

from cmbench.backends.bucket_counts import BucketCNFCountPlan, CountPlanLimit
from cmbench.backends.bucket_numpy import NumpyBucketCNFCountPlan
from cmbench.backends.projected_counts import ProjectedCNFCountPlan
from cm_exprlib import Or, Var
from cm_ir import compile_expr_to_cm_ir


def oracle(clauses, names, projected, fixed=None):
    fixed = fixed or {}
    answers = set()
    for values in product((0, 1), repeat=len(names)):
        if any(values[names.index(k)] != v for k,v in fixed.items()): continue
        if all(any(values[abs(l)-1] == int(l > 0) for l in clause) for clause in clauses):
            answers.add(tuple(values[names.index(k)] for k in projected))
    return len(answers)


class ProjectedCountTests(unittest.TestCase):
    def test_expression_and_cm_ingress_preserve_projection(self):
        expr = Or(Var(0), Var(1))
        for plan in (ProjectedCNFCountPlan.from_expr(expr, ('x0','x1'), projected_names=('x0',)),
                     ProjectedCNFCountPlan.from_cm_node(compile_expr_to_cm_ir(expr), ('x0','x1'), projected_names=('x0',))):
            self.assertEqual(plan.count(), 2)
            self.assertEqual(plan.count({'x1':0}), 1)

    def test_all_three_variable_functions_and_projection_subsets(self):
        names = ('p','h','q')
        for function in range(256):
            clauses = [tuple(-(i+1) if row & (1 << i) else i+1 for i in range(3))
                       for row in range(8) if not function & (1 << row)]
            for mask in range(8):
                projected = tuple(names[i] for i in range(3) if mask & (1 << i))
                for order in ('natural','min_fill'):
                    plan = ProjectedCNFCountPlan(clauses,names,projected,order=order)
                    self.assertEqual(plan.count(),oracle(clauses,names,projected),(function,mask,order))

    def test_random_contexts_python_arrays_and_exact_brute_force(self):
        rng = random.Random(2026091191)
        for _ in range(32):
            names = tuple(f'x{i}' for i in range(6))
            clauses = [tuple(rng.choice((-1,1))*v for v in rng.sample(range(1,7),rng.randrange(1,4))) for _ in range(8)]
            projected = tuple(rng.sample(names,rng.randrange(7)))
            plan = ProjectedCNFCountPlan(clauses,names,projected)
            array = NumpyBucketCNFCountPlan(plan)
            for _ in range(8):
                fixed = {n:rng.randrange(2) for n in rng.sample(names,rng.randrange(7))}
                expected = oracle(clauses,names,projected,fixed)
                self.assertEqual(plan.count(fixed),expected)
                self.assertEqual(array.count(fixed),expected)

    def test_auxiliary_multiplicity_and_elimination_order(self):
        # p OR h has three full models but only two projected p assignments.
        for order in ('natural','min_fill'):
            plan = ProjectedCNFCountPlan(((1,2),),('p','h'),('p',),order=order)
            self.assertEqual(plan.count(),2)
            self.assertEqual(plan.count({'h':0}),1)
            self.assertEqual(plan.count({'p':1}),1)
            self.assertEqual(plan._schedule[0][0],1)
        self.assertEqual(BucketCNFCountPlan(((1,2),),('p','h')).count(),3)

    def test_empty_projection_forced_unused_and_large_exact_counts(self):
        names = tuple(f'x{i}' for i in range(180))
        projected = names[:100]
        plan = ProjectedCNFCountPlan(((101,),),names,projected)
        self.assertEqual(plan.count(),2**100)
        self.assertEqual(NumpyBucketCNFCountPlan(plan).count({'x0':0}),2**99)
        self.assertEqual(plan.count({'x100':0}),0)
        self.assertEqual(ProjectedCNFCountPlan((),names,()).count(),1)
        self.assertEqual(ProjectedCNFCountPlan(((),),names,()).count(),0)

    def test_refusal_contexts_and_shared_read_queries(self):
        with self.assertRaises(ValueError): ProjectedCNFCountPlan((),('p',),('unknown',))
        with self.assertRaises(ValueError): ProjectedCNFCountPlan((),('p',),('p','p'))
        with self.assertRaises(CountPlanLimit): ProjectedCNFCountPlan(((1,2,3),),('p','q','h'),('p',),max_width=2)
        plan = ProjectedCNFCountPlan(((1,2),(-2,3)),('p','h','q'),('q','p'))
        for fixed in ({'bad':0},{'p':2}):
            with self.assertRaises(ValueError): plan.count(fixed)
        contexts = [{},{'p':0},{'h':1},{'p':1,'q':0}]*16
        expected = [oracle(((1,2),(-2,3)),plan.basis,plan.projected_names,c) for c in contexts]
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(plan.count,contexts)),expected)


if __name__ == '__main__': unittest.main()
