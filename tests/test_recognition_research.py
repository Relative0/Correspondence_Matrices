"""Local research tests; runnable with stdlib unittest or the project's pytest."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import math
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor, eval_expr_tt
from cmbench.recognition.corpus import FAMILIES, generate_expr, make_corpus
from cmbench.recognition.experiment import (
    BudgetExhausted, Config, _measure, run_experiment, summarize, write_artifacts,
)
from cmbench.recognition.features import (
    FEATURE_NAMES, IneligibleExpression, extract_features, postorder, structural_digest,
)
from cmbench.recognition.learning import CostTree, fit_cost_tree, load_model
from cmbench.recognition.portfolio import BACKENDS, admit, prepare, reference_bits
from scripts.cm_recognition_experiment import main


def vector(value=0.0):
    return (float(value),) + (0.0,) * (len(FEATURE_NAMES) - 1)


def learned_fixture():
    x = [vector(i) for i in range(16)]
    y = [[1, 10, 20] if i < 8 else [10, 1, 20] for i in range(16)]
    return fit_cost_tree(x, y)


class FeatureTests(unittest.TestCase):
    def test_all_operators(self):
        expr = Eqv(Imp(And(Var(0), Not(Var(1))), Or(Var(2), Var(3))), Xor(Var(0), Var(2)))
        result = extract_features(expr, 4, 8)
        self.assertEqual(len(result.values), len(FEATURE_NAMES))
        self.assertTrue(all(math.isfinite(v) for v in result.values))
        self.assertGreater(result.identity_nodes, result.structural_nodes)

    def test_deep_features_are_iterative(self):
        expr = Var(0)
        for _ in range(1800):
            expr = Not(expr)
        self.assertEqual(extract_features(expr, 2).depth, 1801)
        with self.assertRaises(IneligibleExpression):
            admit(expr, 2, 1)

    def test_shared_dag_is_not_expanded(self):
        expr = Var(0)
        for _ in range(30):
            expr = And(expr, expr)
        result = extract_features(expr, 2)
        self.assertEqual(result.identity_nodes, 31)
        self.assertEqual(result.unfolded_nodes_capped, 1_000_001)
        self.assertGreater(result.values[4], 0.4)
        with self.assertRaises(IneligibleExpression):
            admit(expr, 2, 1)

    def test_cycle_rejected(self):
        expr = Not(Var(0))
        object.__setattr__(expr, "a", expr)
        with self.assertRaises(IneligibleExpression):
            postorder(expr)

    def test_invalid_inputs(self):
        for expr, n, q in [(Var(-1), 2, 1), (Var(True), 2, 1), (Var(2), 2, 1),
                           (Var(0), 17, 1), (Var(0), 2, 0), (Var(0), True, 1), (object(), 2, 1)]:
            with self.subTest(expr_type=type(expr), n=n, q=q), self.assertRaises(IneligibleExpression):
                extract_features(expr, n, q)

    def test_node_and_reference_limits(self):
        with self.assertRaises(IneligibleExpression):
            postorder(And(Var(0), Var(1)), max_nodes=2)
        expr = Var(0)
        for i in range(80):
            expr = Imp(expr, Var(i % 16))
        with self.assertRaises(IneligibleExpression):
            admit(expr, 16, 1)

    def test_renamed_siblings_share_group(self):
        a = Or(And(Var(0), Var(1)), Var(0))
        b = Or(And(Var(8), Var(3)), Var(8))
        self.assertNotEqual(structural_digest(a), structural_digest(b))
        self.assertEqual(structural_digest(a, alpha_rename=True), structural_digest(b, alpha_rename=True))

    def test_shared_and_unshared_have_same_digest(self):
        node = Xor(Var(0), Var(1))
        self.assertEqual(structural_digest(And(node, node)),
                         structural_digest(And(Xor(Var(0), Var(1)), Xor(Var(0), Var(1)))))


class PortfolioTests(unittest.TestCase):
    def test_all_operations_match_independent_truth_table(self):
        expressions = [Var(0), Not(Var(0))]
        expressions += [op(Var(0), Var(1)) for op in (And, Or, Xor, Imp, Eqv)]
        expressions += [Xor(Var(0), Var(0)), Or(Var(0), Not(Var(0)))]
        for expr in expressions:
            tt = eval_expr_tt(expr, 3)
            expected = sum(int(bit) << i for i, bit in enumerate(tt))
            self.assertEqual(reference_bits(expr, 3), expected)
            for backend in BACKENDS:
                with self.subTest(backend=backend, expr=expr):
                    evaluate = prepare(backend, expr, 3)
                    self.assertEqual(evaluate(), expected)
                    self.assertEqual(evaluate(), expected)

    def test_generated_families_match(self):
        for family in FAMILIES:
            for seed in range(6):
                expr = generate_expr(family, random.Random(seed), 5)
                expected = reference_bits(expr, 5)
                for backend in BACKENDS:
                    with self.subTest(family=family, seed=seed, backend=backend):
                        self.assertEqual(prepare(backend, expr, 5)(), expected)

    def test_preparation_does_not_cache_on_input_ast(self):
        expr = And(Var(0), Or(Var(1), Var(2)))
        for backend in BACKENDS:
            prepare(backend, expr, 3)()
        self.assertEqual(set(expr.__dict__), {"a", "b"})

    def test_unknown_backend(self):
        with self.assertRaises(ValueError):
            prepare("shell", Var(0), 2)


class LearningTests(unittest.TestCase):
    def test_learns_cost_based_threshold_not_lookup(self):
        model = learned_fixture()
        # These fractional feature values never occurred in training.
        self.assertEqual(model.select(vector(2.5)).backend, "direct")
        self.assertEqual(model.select(vector(11.5)).backend, "cse")
        self.assertEqual(model.select(vector(11.5)).reason, "learned")
        self.assertIn("feature", model.tree)
        self.assertNotIn("expressions", model.to_dict())

    def test_changing_training_costs_changes_policy(self):
        x = [vector(i) for i in range(16)]
        changed = fit_cost_tree(x, [[20, 10, 1] for _ in x])
        self.assertEqual(changed.select(vector(11.5)).backend, "cm")

    def test_out_of_distribution_and_invalid_features_fall_back(self):
        model = learned_fixture()
        self.assertEqual(model.select(vector(100)).reason, "outside_training_range")
        self.assertEqual(model.select(vector(float("nan"))).reason, "invalid_features")
        self.assertEqual(model.select([]).backend, model.fallback)
        self.assertEqual(model.select((10**1000,) + vector()[1:]).reason, "invalid_features")

    def test_roundtrip(self):
        model = learned_fixture()
        restored = CostTree.from_dict(model.to_dict())
        self.assertEqual(restored.to_dict(), model.to_dict())
        self.assertEqual(restored.select(vector(12)), model.select(vector(12)))

    def test_loader_detaches_input(self):
        original = learned_fixture().to_dict()
        model = CostTree.from_dict(original)
        original["tree"].clear()
        self.assertIn("feature", model.tree)

    def test_reject_invalid_training_costs(self):
        for costs in ([[0, 1, 2]], [[-1, 1, 2]], [[float("inf"), 1, 2]], [[1, 2]], [[True, 1, 2]]):
            with self.subTest(costs=costs), self.assertRaises(ValueError):
                fit_cost_tree([vector()], costs)
        with self.assertRaises(ValueError):
            fit_cost_tree([], [])

    def test_reject_model_schema_and_numbers(self):
        model = learned_fixture().to_dict()
        for name, value in [("schema", "bad"), ("feature_version", True), ("features", []),
                            ("min_gain", float("nan")), ("fallback", "arbitrary-code"),
                            ("ranges", []), ("tree", {"costs": [1, -1, 2], "samples": 3})]:
            invalid = copy.deepcopy(model)
            invalid[name] = value
            with self.subTest(field=name), self.assertRaises(ValueError):
                CostTree.from_dict(invalid)
        model["unknown"] = True
        with self.assertRaises(ValueError):
            CostTree.from_dict(model)

    def test_excessive_model_depth_is_rejected(self):
        model = learned_fixture().to_dict()
        node = {"costs": [1, 2, 3], "samples": 1}
        for _ in range(4):
            node = {"feature": 0, "threshold": 1, "left": node,
                    "right": {"costs": [1, 2, 3], "samples": 1}}
        model["tree"] = node
        with self.assertRaises(ValueError):
            CostTree.from_dict(model)

    def test_bounded_file_loader(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.json"
            path.write_text(json.dumps(learned_fixture().to_dict()), encoding="utf-8")
            self.assertEqual(load_model(path).select(vector(11.5)).backend, "cse")
            for raw in ('{"a": 1, "a": 2}', '{"a": NaN}', '[' * 2000, ' ' * 65537):
                path.write_text(raw, encoding="utf-8")
                with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                    load_model(path)


class CorpusTests(unittest.TestCase):
    def test_reproducible_and_group_disjoint(self):
        kwargs = dict(train=3, validation=2, test=2, sizes=(4, 6))
        first, second = make_corpus(**kwargs), make_corpus(**kwargs)
        self.assertEqual([c.digest for c in first], [c.digest for c in second])
        self.assertEqual(len(first), len({c.group_digest for c in first}))
        self.assertTrue(all(c.family != "mux" for c in first if c.split != "family_test"))
        self.assertTrue(all(c.family == "mux" for c in first if c.split == "family_test"))

    def test_invalid_configuration(self):
        for config in (Config(rounds=0), Config(max_seconds=float("nan")),
                       Config(sizes=(40,)), Config(query_counts=(1000,)),
                       Config(train_per_family=1000), Config(held_out_family="unknown")):
            with self.subTest(config=config), self.assertRaises(ValueError):
                config.validate()


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Config(train_per_family=2, validation_per_family=1, test_per_family=1,
                            sizes=(4,), query_counts=(1, 2), rounds=1, max_seconds=30)
        cls.result = run_experiment(cls.config)

    def test_end_to_end_exact_and_frozen(self):
        result = self.result
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["semantic_mismatches"], 0)
        self.assertTrue(result["model_frozen_before_evaluation"])
        self.assertTrue(result["source_unchanged"])
        self.assertEqual(result["cache_hits_on_evaluation"], 0)
        self.assertEqual(len(result["rows"]), 8 * 3 + 9 * 6)
        self.assertEqual(result["summary"]["test"]["observed_instances"], 4)

    def test_no_speed_assertions_but_timing_is_accounted(self):
        for row in self.result["rows"]:
            self.assertGreater(row["total_ns"], 0)
            self.assertGreaterEqual(row["total_ns"], row["feature_ns"] + row["decision_ns"])

    def test_manifest_and_model_artifacts(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            write_artifacts(output, self.result)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            for name, expected in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), expected)
            self.assertEqual(load_model(output / "model.json").to_dict(), self.result["model"])
            with self.assertRaises(FileExistsError):
                write_artifacts(output, self.result)

    def test_budget_exhaustion_not_success(self):
        with patch("cmbench.recognition.experiment.Budget.check", side_effect=BudgetExhausted):
            result = run_experiment(self.config)
        self.assertEqual(result["status"], "budget_exhausted")
        self.assertIsNone(result["model"])

    def test_backend_mismatch_is_retained_and_rejected(self):
        with patch("cmbench.recognition.experiment.prepare", return_value=lambda: -1):
            result = run_experiment(self.config)
        self.assertEqual(result["status"], "backend_failure")
        self.assertGreater(result["semantic_mismatches"], 0)
        self.assertIsNone(result["model"])

    def test_all_query_outputs_checked(self):
        case = make_corpus(train=1, validation=1, test=1, sizes=(3,), query_counts=(2,))[0]
        expected = reference_bits(case.expr, case.n_vars)
        values = iter([-1, expected])
        with patch("cmbench.recognition.experiment.prepare", return_value=lambda: next(values)):
            row = _measure(case, "cse", 0, expected, None, {})
        self.assertEqual(row["mismatches"], 1)
        self.assertEqual(row["status"], "mismatch")

    def test_incomplete_rounds_not_summarized_as_success(self):
        summary = summarize(self.result["rows"], self.result["training_only_fallback"], rounds=2)
        self.assertEqual(summary["test"]["complete_baseline_instances"], 0)

    def test_paired_metrics_count_formulas_not_rounds(self):
        rows = [{"case_id": "one", "split": "test", "family": "mixed", "arm": arm,
                 "status": "ok", "total_ns": cost, "round": round_index}
                for round_index in range(3)
                for arm, cost in (("direct", 10), ("cse", 20), ("cm", 30), ("learned", 15))]
        summary = summarize(rows, "cse", 3)["test"]
        self.assertEqual(summary["observed_instances"], 1)
        self.assertEqual(summary["arms"]["learned"]["paired_instances"], 1)
        self.assertAlmostEqual(summary["arms"]["learned"]["geomean_speedup_over_fixed_train"], 4 / 3)
        self.assertAlmostEqual(summary["optimistic_oracle_speedup_over_fixed_train"], 2)

    def test_training_happens_once_before_evaluation(self):
        phases = []
        def fit(features, costs):
            self.assertTrue(phases[-1].startswith("train:"))
            self.assertEqual(len(features), 8)
            return fit_cost_tree(features, costs)
        with patch("cmbench.recognition.experiment.fit_cost_tree", side_effect=fit) as trainer:
            result = run_experiment(self.config, progress=phases.append)
        trainer.assert_called_once()
        self.assertEqual(result["status"], "complete")

    def test_source_change_invalidates_pilot(self):
        with patch("cmbench.recognition.experiment.source_fingerprints", side_effect=[{"code": "before"}, {"code": "after"}]):
            result = run_experiment(self.config)
        self.assertEqual(result["status"], "source_changed_during_run")
        self.assertFalse(result["source_unchanged"])

    def test_cache_hit_avoids_backend(self):
        case = make_corpus(train=1, validation=1, test=1, sizes=(3,), query_counts=(2,))[0]
        expected = reference_bits(case.expr, case.n_vars)
        with patch("cmbench.recognition.experiment.prepare") as backend:
            row = _measure(case, "exact_cache", 0, expected, learned_fixture(),
                           {(case.digest, case.n_vars): expected})
        backend.assert_not_called()
        self.assertTrue(row["cache_hit"])
        self.assertEqual(row["status"], "ok")

    def test_plan_does_not_run_or_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "absent"
            with patch("scripts.cm_recognition_experiment.run_experiment") as run, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--output", str(target)]), 0)
                run.assert_not_called()
            self.assertFalse(target.exists())

    def test_cli_refuses_existing_directory_before_work(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch("scripts.cm_recognition_experiment.run_experiment") as run, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--run", "--output", temporary]), 2)
                run.assert_not_called()

    def test_cli_requires_output(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--run"]), 2)


if __name__ == "__main__":
    unittest.main()
