"""Exercise explicit scalar APIs through the existing application task contract."""
import unittest
from cmbench.comparative import tasks


class ScalarTaskIntegrationTests(unittest.TestCase):
    def scenario(self, affine=False):
        return {'id':'scalar-call-site','k':5,'feature_names':[f'x{i}' for i in range(5)],
            'versions':[{'id':'base','clauses':[[1]] if affine else [[1,2],[-2,3]]},
                        {'id':'revision','clauses':[[1],[-3]] if affine else [[-1,2],[3]]}],
            'source':{'kind':'synthetic','purpose':'consumer_adapter_exactness'}}

    def test_adapters_match_existing_independent_contract_oracle(self):
        for backend in tasks.SCALAR_BACKENDS:
            scenario = self.scenario(backend == 'affine_count')
            for task in tasks.SCALAR_TASKS:
                trace = [{'version':v} if task == 'exact_count' else {'version':v,'assumptions':fixed}
                         for v,fixed in ((0,[]),(0,[-1]),(1,[3]),(0,[1,-2]))]
                expected = tasks.scalar_oracle(scenario,task,trace)
                for lifecycle in tasks.LIFECYCLES:
                    contract=tasks.task_contract(contract_id='scalar-integration',task=task,backend=backend,
                        lifecycle=lifecycle,k=5,queries=len(trace),expected_sha256=tasks.semantic_digest(task,expected))
                    result=tasks.execute_task(scenario=scenario,task=task,trace=trace,backend=backend,
                        lifecycle=lifecycle,contract=contract,case_id='adapter')
                    tasks.validate_task_result(result,contract,expected,expected_backend=backend)
                    counts=result['identity']['counters']
                    self.assertEqual(counts['flat_evaluations'],0)
                    self.assertEqual(counts['programs_built'],4 if lifecycle == 'fresh_engine' else 2)

    def test_unsupported_outputs_and_affine_inputs_are_explicitly_rejected(self):
        for backend in tasks.SCALAR_BACKENDS:
            for task in ('witness','equivalence_delta'):
                with self.assertRaisesRegex(ValueError,'output contract'):
                    tasks.task_contract(contract_id='unsupported',task=task,backend=backend,
                        lifecycle='resident_engine',k=5,queries=1,expected_sha256='0'*64)
        scenario=self.scenario(); trace=[{'version':0}]
        expected=tasks.scalar_oracle(scenario,'exact_count',trace)
        contract=tasks.task_contract(contract_id='nonaffine',task='exact_count',backend='affine_count',
            lifecycle='resident_engine',k=5,queries=1,expected_sha256=tasks.semantic_digest('exact_count',expected))
        with self.assertRaisesRegex(ValueError,'non-affine'):
            tasks.execute_task(scenario=scenario,task='exact_count',trace=trace,backend='affine_count',
                lifecycle='resident_engine',contract=contract,case_id='nonaffine')


if __name__ == '__main__': unittest.main()
