import unittest

import numpy as np

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import random_expr
from cmbench.recognition.adaptive_exact_dispatcher import (
    adaptive_exact_partition, adaptive_exact_partition_fast,
)
from cmbench.recognition.exact_dispatcher import (
    ARMS, LINEAR_FEATURES, O1_FEATURES, POLICY_SCHEMA, cheap_feature_values,
    extract_dispatch_features, fit_greedy_tree, select_document, select_from_values,
    tree_stats, validate_policy,
)
from cmbench.recognition.yosys_human_decomposition_data import make_yosys_human_documents
from cmbench.recognition.yosys_composed_holdout_data import make_yosys_composed_holdout
from cmbench.recognition.yosys_composed_holdout2_data import make_yosys_composed_holdout2
from cmbench.recognition.natural_decomposition import canonical_partition
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.source_anf_hybrid import ProductCache
from cmbench.recognition.source_interaction import (
    MAX_PRODUCT_PAIRS, source_anf_monomials, source_anf_prefix_with_sentinel,
    source_exact_partition,
)
from cmbench.recognition.staged_exact_dispatcher import (
    SetProductBudgetExceeded, source_set_partition_guarded, staged_exact_partition,
)
from cmbench.recognition.task_guarded_dispatcher import (
    ExactTaskContract, compile_task_guard, current_platform_identity,
    freeze_task_guard_policy, select_task_arm, validate_policy as validate_task_policy,
)


class ExactDispatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents, _provenance = make_yosys_human_documents()

    def test_features_are_bounded_and_o1_subset_agrees(self):
        for row in self.documents:
            features = extract_dispatch_features(row["expression_v2"], row["n_vars"])
            values = features.to_dict()
            self.assertEqual(set(values), set(LINEAR_FEATURES))
            self.assertEqual(values["n_vars"], row["n_vars"])
            self.assertEqual(values["root_support"], row["n_vars"])
            self.assertGreaterEqual(values["nodes"], row["n_vars"])
            o1 = cheap_feature_values(row["expression_v2"], row["n_vars"], O1_FEATURES)
            self.assertEqual({name: values[name] for name in O1_FEATURES}, o1)

    def test_greedy_tree_is_deterministic_and_selects_expected_regions(self):
        rows = []
        for index in range(12):
            costs = {arm: 1000 for arm in ARMS}
            costs["set_source_anf" if index < 6 else "cached_packed_source_anf"] = 10
            rows.append({"features": {name: (index if name == "nodes" else 1)
                                      for name in LINEAR_FEATURES}, "costs": costs})
        first = fit_greedy_tree(rows, features=O1_FEATURES, max_depth=1, min_leaf=2)
        second = fit_greedy_tree(rows, features=O1_FEATURES, max_depth=1, min_leaf=2)
        self.assertEqual(first, second)
        tree, loss = first
        self.assertEqual(loss, 120)
        self.assertEqual(select_from_values(tree, {"n_vars": 1, "nodes": 2}), "set_source_anf")
        self.assertEqual(select_from_values(tree, {"n_vars": 1, "nodes": 10}),
                         "cached_packed_source_anf")

    def test_frozen_policy_validates_and_selects_without_labels(self):
        tree = {"kind": "split", "feature": "nodes", "threshold": 20.5,
                "training_rows": 10,
                "leq": {"kind": "leaf", "arm": "set_source_anf", "training_rows": 5},
                "gt": {"kind": "leaf", "arm": "bitset_truth_vector_anf", "training_rows": 5}}
        policy = {"schema": POLICY_SCHEMA, "arms": list(ARMS), "tree": tree,
            "tree_stats": tree_stats(tree),
            "training_use": {"train": True, "validation": True, "test": False,
                             "confirmatory": False, "c7_sealed_a": False, "c7_sealed_b": False}}
        validate_policy(policy)
        row = self.documents[0]
        arm, values = select_document(policy, row["expression_v2"], row["n_vars"])
        self.assertIn(arm, ARMS)
        self.assertEqual(set(values), {"n_vars", "nodes"})

    def test_staged_guard_preserves_exact_set_or_packed_partition(self):
        for row in self.documents:
            expected = source_exact_partition(row["expression_v2"], row["n_vars"])
            full, stats = source_set_partition_guarded(
                row["expression_v2"], row["n_vars"], product_pair_budget=8_000_000)
            self.assertEqual(full, expected)
            self.assertIsNone(stats.fallback_reason)
            staged, path, set_stats, packed_stats = staged_exact_partition(
                row["expression_v2"], row["n_vars"], product_pair_budget=0,
                cache=ProductCache(1024))
            self.assertEqual(staged, expected)
            self.assertIn(path, {"set_source_anf", "cached_packed_source_anf"})
            if path == "cached_packed_source_anf":
                self.assertEqual(set_stats.fallback_reason, "product_pair_budget")
                self.assertIsNotNone(packed_stats)

    def test_adaptive_one_pass_preserves_exact_partition(self):
        paths = set()
        for budget in (0, 64, 1024, 8_000_000):
            cache = ProductCache(1024)
            for row in self.documents:
                expected = source_exact_partition(row["expression_v2"], row["n_vars"])
                partition, path, instrumentation = adaptive_exact_partition(
                    row["expression_v2"], row["n_vars"],
                    product_pair_budget=budget, cache=cache,
                )
                self.assertEqual(partition, expected)
                self.assertIn(path, {"set_source_anf", "adaptive_set_to_packed"})
                self.assertEqual(
                    instrumentation.final_representation,
                    "set" if path == "set_source_anf" else "packed",
                )
                paths.add(path)
        self.assertEqual(paths, {"set_source_anf", "adaptive_set_to_packed"})

    def test_c13_generated_expressions_match_independent_truth_through_four_variables(self):
        rng = np.random.default_rng(20260830)
        budgets = (0, 1, 4095, 4096, MAX_PRODUCT_PAIRS)
        for n_vars in range(2, 5):
            for _case in range(24):
                expression = random_expr(n_vars, rng, max_depth=5, p_unary=.2)
                document = expr_to_json_dag(expression)
                expected = canonical_partition(reference_bits(expression, n_vars), n_vars)
                expected_row = expected[0] if expected is not None else None
                self.assertEqual(source_exact_partition(document, n_vars), expected_row)
                for budget in budgets:
                    actual, _path = adaptive_exact_partition_fast(
                        document, n_vars, product_pair_budget=budget,
                        cache=ProductCache(64))
                    self.assertEqual(actual, expected_row)

    def test_c13_budget_boundaries_prefix_reuse_and_measurement_switch(self):
        row = max(self.documents, key=lambda item: len(item["expression_v2"]["nodes"]))
        document, n_vars = row["expression_v2"], row["n_vars"]
        expected = source_exact_partition(document, n_vars)
        for budget in (0, 1, 4095, 4096, MAX_PRODUCT_PAIRS):
            measured, measured_path, instrumentation = adaptive_exact_partition(
                document, n_vars, product_pair_budget=budget,
                cache=ProductCache(1024))
            fast, fast_path = adaptive_exact_partition_fast(
                document, n_vars, product_pair_budget=budget,
                cache=ProductCache(1024))
            prefix = source_anf_prefix_with_sentinel(
                document, n_vars, product_pair_budget=budget, measure=True)
            unmeasured_prefix = source_anf_prefix_with_sentinel(
                document, n_vars, product_pair_budget=budget, measure=False)
            self.assertEqual((measured, measured_path), (fast, fast_path))
            self.assertEqual(measured, expected)
            self.assertLessEqual(prefix.executed_product_pairs, budget)
            self.assertIsNotNone(prefix.instrumentation)
            self.assertIsNone(unmeasured_prefix.instrumentation)
            self.assertEqual(prefix.switch_node, unmeasured_prefix.switch_node)
            self.assertEqual(prefix.executed_product_pairs,
                             unmeasured_prefix.executed_product_pairs)
            self.assertEqual(instrumentation.switch_node, prefix.switch_node)
            self.assertEqual(instrumentation.converted_polynomials,
                             len(prefix.polynomials) if prefix.switch_node is not None else 0)
        full = source_anf_prefix_with_sentinel(
            document, n_vars, product_pair_budget=MAX_PRODUCT_PAIRS)
        self.assertIsNone(full.switch_node)
        self.assertEqual(tuple(sorted(full.polynomials[full.root])),
                         source_anf_monomials(document, n_vars))

    def test_c14_task_policy_abstention_and_global_disable(self):
        identity = current_platform_identity()
        policy = freeze_task_guard_policy(identity)
        validate_task_policy(policy)
        self.assertEqual(select_task_arm(
            policy, ExactTaskContract("throughput"), n_vars=8,
            identity=identity).selected_arm, "set_no_sentinel")
        self.assertEqual(select_task_arm(
            policy, ExactTaskContract("latency_sensitive"), n_vars=8,
            identity=identity).selected_arm, "sentinel_fast")
        insufficient = select_task_arm(
            policy, ExactTaskContract("repeated_query", 1), n_vars=8,
            identity=identity)
        self.assertTrue(insufficient.abstained)
        self.assertEqual(insufficient.reason, "insufficient_expected_reuse")
        self.assertEqual(select_task_arm(
            policy, ExactTaskContract("repeated_query", 2), n_vars=8,
            identity=identity).selected_arm, "sentinel_fast")
        mismatch = {**identity, "machine": identity["machine"] + "-other"}
        self.assertEqual(select_task_arm(
            policy, ExactTaskContract("latency_sensitive"), n_vars=8,
            identity=mismatch).reason, "platform_calibration_mismatch")
        linux_identity = {
            "system": "Linux", "machine": "x86_64",
            "python_implementation": "CPython", "python_version": "3.13.15",
        }
        linux = select_task_arm(
            policy, ExactTaskContract("latency_sensitive"), n_vars=8,
            identity=linux_identity)
        self.assertTrue(linux.abstained)
        self.assertEqual(linux.selected_arm, "set_no_sentinel")
        self.assertEqual(linux.reason, "platform_calibration_mismatch")
        self.assertEqual(select_task_arm(
            policy, ExactTaskContract("not-supported"), n_vars=8,
            identity=identity).reason, "unsupported_task")
        self.assertFalse(select_task_arm(
            policy, ExactTaskContract("latency_sensitive"), n_vars=11,
            identity=identity).admitted)
        disabled = select_task_arm(
            policy, ExactTaskContract("latency_sensitive"), n_vars=8,
            identity=identity, advice_enabled=False)
        self.assertEqual(disabled.selected_arm, "set_no_sentinel")
        self.assertEqual(disabled.reason, "advice_globally_disabled")

    def test_c14_compiled_shadow_preserves_exact_result(self):
        row = self.documents[0]
        identity = current_platform_identity()
        policy = freeze_task_guard_policy(identity)
        expected = source_exact_partition(row["expression_v2"], row["n_vars"])
        latency = compile_task_guard(
            policy, ExactTaskContract("latency_sensitive"),
            n_vars=row["n_vars"], identity=identity, shadow=True)
        result = latency.execute(row["expression_v2"])
        self.assertEqual(result.partition, expected)
        self.assertTrue(result.shadow_partition_match)
        self.assertGreaterEqual(result.production_ns, 0)
        self.assertGreaterEqual(result.shadow_ns, 0)
        disabled = compile_task_guard(
            policy, ExactTaskContract("latency_sensitive"),
            n_vars=row["n_vars"], identity=identity,
            advice_enabled=False, shadow=False)
        disabled_result = disabled.execute(row["expression_v2"])
        self.assertEqual(disabled_result.partition, expected)
        self.assertEqual(disabled_result.selected_arm, "set_source_anf")
        self.assertEqual(disabled_result.decision_reason, "advice_globally_disabled")

    def test_c11_holdout_is_balanced_and_disjoint_from_c7(self):
        documents, provenance = make_yosys_composed_holdout()
        self.assertEqual(len(documents), 40)
        self.assertEqual(provenance["audit"]["c7_semantic_overlap"], 0)
        self.assertEqual(provenance["audit"]["c7_alpha_overlap"], 0)
        self.assertEqual(provenance["audit"]["source_kind_counts"], {
            "disjoint_xor_of_generator_outputs": 20,
            "unused_raw_generator_output": 20,
        })

    def test_c12_holdout_is_balanced_and_disjoint_from_prior_source_data(self):
        documents, provenance = make_yosys_composed_holdout2()
        self.assertEqual(len(documents), 40)
        self.assertEqual(provenance["audit"]["prior_semantic_overlap"], 0)
        self.assertEqual(provenance["audit"]["prior_alpha_overlap"], 0)


if __name__ == "__main__":
    unittest.main()
