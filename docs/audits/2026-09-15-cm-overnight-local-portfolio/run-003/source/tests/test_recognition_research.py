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


class RoutingAblationTests(unittest.TestCase):
    def test_query_features_do_not_walk_expression(self):
        from cmbench.recognition.routing import routing_features, query_rule
        with patch("cmbench.recognition.routing.postorder", side_effect=AssertionError):
            values = routing_features(object(), 8, 8, "queries/v1")
        self.assertEqual(values[1], 3)
        self.assertEqual(sum(values), 3)
        self.assertEqual([query_rule(q) for q in (1, 2, 8, 64)], ["direct", "direct", "cse", "cse"])

    def test_depth_projection_and_schema_roundtrip(self):
        from cmbench.recognition.routing import FeatureRouter, fit_router, routing_features, project_features
        expr = Not(And(Var(0), Var(1)))
        features = extract_features(expr, 2, 8).values
        self.assertEqual(routing_features(expr, 2, 8, "queries-depth/v1"), project_features(features, "queries-depth/v1"))
        model = fit_router([features] * 4, [[1, 2, 3]] * 4, "queries/v1")
        restored = FeatureRouter.from_dict(model.to_dict())
        self.assertEqual(restored.to_dict(), model.to_dict())
        bad = model.to_dict()
        bad["feature_schema"] = "bad"
        with self.assertRaises(ValueError):
            FeatureRouter.from_dict(bad)

    def test_ablation_retains_all_models_and_bypasses_learning(self):
        config = Config(train_per_family=2, validation_per_family=1, test_per_family=1,
                        sizes=(4,), query_counts=(1, 8), rounds=1, feature_ablation=True)
        result = run_experiment(config)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(set(result["router_models"]), {"learned_queries", "learned_queries_depth"})
        self.assertIn("query_rule", result["summary"]["test"]["arms"])
        case = make_corpus(train=1, validation=1, test=1, sizes=(3,))[0]
        with patch("cmbench.recognition.experiment.extract_features", side_effect=AssertionError):
            row = _measure(case, "learned", 0, reference_bits(case.expr, 3), learned_fixture(), {}, learned_enabled=False)
        self.assertEqual(row["reason"], "learned_disabled")
        self.assertEqual(row["mismatches"], 0)
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "run_spec.json").write_text('{}')
            write_artifacts(Path(temp), result)
            self.assertEqual(json.loads((Path(temp) / "router_models.json").read_text()), result["router_models"])
            self.assertIn("run_spec.json", json.loads((Path(temp) / "manifest.json").read_text())["files_sha256"])

    def test_fingerprint_covers_nested_models(self):
        from cmbench.recognition.experiment import source_fingerprints
        sources = source_fingerprints()
        self.assertIn("cmbench/recognition/models/mlp.py", sources)
        self.assertIn("cmbench/recognition/teacher.py", sources)


class ExactTeacherTests(unittest.TestCase):
    def test_layout_and_all_operator_labels(self):
        from cmbench.recognition.teacher import teach
        for op in (And, Or, Xor, Imp, Eqv):
            cm = teach(op(Var(0), Var(1)), 2)
            self.assertEqual(cm.layout.labels(), [{0: 0, 1: 0}, {0: 0, 1: 1}, {0: 1, 1: 0}, {0: 1, 1: 1}])
            self.assertEqual(cm.layout.shape, (2, 2))
            self.assertEqual(cm.bits, reference_bits(op(Var(0), Var(1)), 2))
            self.assertEqual(cm.valid_mask, 15)

    def test_paper_page12_corrected_identity(self):
        from cmbench.recognition.teacher import teach
        expr = Xor(Imp(Var(0), Var(1)), Or(Var(0), Var(1)))
        self.assertEqual(teach(expr, 2).bits, teach(Not(Var(1)), 2).bits)
        self.assertNotEqual(teach(expr, 2).bits, teach(Not(Var(0)), 2).bits)

    def test_transpose_permutation_and_negated_labels(self):
        from cmbench.recognition.teacher import CMLayout, teach
        cm = teach(Imp(Var(0), Var(1)), 2)
        transposed = cm.transpose()
        self.assertEqual(transposed.layout.variables, (1, 0))
        self.assertEqual(transposed.bits, reference_bits(Imp(Var(1), Var(0)), 2))
        self.assertEqual(transposed.reorder(cm.layout), cm)
        self.assertEqual(cm.negate_inputs((0,)).bits, reference_bits(Imp(Not(Var(0)), Var(1)), 2))
        self.assertEqual(cm.negate_output().bits, reference_bits(Not(Imp(Var(0), Var(1))), 2))
        with self.assertRaises(ValueError):
            cm.reorder(CMLayout((0,), (2,)))

    def test_cofactors_keep_variable_labels(self):
        from cmbench.recognition.teacher import teach
        cm = teach(Xor(Var(0), And(Var(1), Var(2))), 3)
        partial = cm.cofactor({1: 1})
        self.assertEqual(partial.layout.variables, (0, 2))
        self.assertEqual(partial.bits, reference_bits(Xor(Var(0), Var(1)), 2))
        scalar = cm.cofactor({0: 1, 1: 0, 2: 1})
        self.assertEqual(scalar.layout.shape, (1, 1))
        self.assertEqual(scalar.bits, 1)
        with self.assertRaises(ValueError):
            cm.cofactor({1: True})

    def test_input_mask_padding_and_admission_before_reference(self):
        from cmbench.recognition.teacher import CMLayout, ExactCM, teach
        tensor = teach(Var(0), 2).tensor()
        self.assertEqual(tensor.shape, (512,))
        self.assertEqual(tensor[:4].tolist(), [0, 0, 1, 1])
        self.assertEqual(tensor[256:260].tolist(), [1, 1, 1, 1])
        self.assertEqual(float(tensor[4:256].sum() + tensor[260:].sum()), 0)
        with patch("cmbench.recognition.teacher.reference_bits", side_effect=AssertionError):
            with self.assertRaises(ValueError):
                teach(Var(0), 9)
        for layout, bits in ((CMLayout((0,), (1,)), 16), (CMLayout((), ()), -1)):
            with self.assertRaises(ValueError):
                ExactCM(layout, bits)
        with self.assertRaises(ValueError):
            CMLayout((0,), (0,))


class GraphInputContractTests(unittest.TestCase):
    def test_roles_variables_negation_and_dag_sharing_are_explicit(self):
        from cmbench.recognition.graph_inputs import EDGE_ROLES, OPS, graph_from_document
        document = {"version": 2, "nodes": [
            {"op": "var", "i": 0}, {"op": "var", "i": 1},
            {"op": "xor", "a": 0, "b": 1}, {"op": "not", "a": 2},
            {"op": "and", "a": 2, "b": 3}], "root": 4}
        graph = graph_from_document(document)
        self.assertEqual(graph.root, 4)
        self.assertEqual(graph.node_features[0, len(OPS)], 1)
        self.assertEqual(graph.node_features[1, len(OPS) + 1], 1)
        self.assertEqual(set(graph.edge_roles.tolist()), set(range(len(EDGE_ROLES))))
        self.assertEqual(graph.edge_index[0].tolist().count(2), 2)
        self.assertEqual(len(graph.node_features), len(document["nodes"]))

    def test_non_topological_graph_is_rejected_before_allocation(self):
        from cmbench.recognition.graph_inputs import graph_from_document
        invalid = {"version": 2, "nodes": [{"op": "not", "a": 0}], "root": 0}
        with self.assertRaises(ValueError):
            graph_from_document(invalid)


class NeuralModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        from cmbench.recognition.models.mlp import train_mlp
        cls.x = np.random.default_rng(42).integers(0, 2, (16, 512)).astype(np.float32)
        cls.y = np.array([0, 1] * 8, dtype=np.float32)
        cls.model = train_mlp(cls.x, cls.y, seed=17, epochs=3, batch_size=4, hidden=8)

    def test_actual_updates_seed_replay_and_training_only_preprocessing(self):
        import numpy as np
        from cmbench.recognition.models.mlp import train_mlp
        replay = train_mlp(self.x, self.y, seed=17, epochs=3, batch_size=4, hidden=8)
        self.assertEqual(self.model.to_dict(), replay.to_dict())
        self.assertTrue(self.model.training["parameters_updated"])
        self.assertEqual(self.model.training["steps"], 12)
        np.testing.assert_array_equal(self.model.mean, self.x.mean(axis=0))
        original_mean = self.model.mean.copy()
        self.model.predict(1 - self.x)
        np.testing.assert_array_equal(self.model.mean, original_mean)

    def test_save_reload_and_no_overwrite(self):
        import numpy as np
        from cmbench.recognition.models.mlp import MotifMLP
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "model.json"
            self.model.save(path)
            loaded = MotifMLP.load(path)
            np.testing.assert_array_equal(self.model.predict(self.x), loaded.predict(self.x))
            with self.assertRaises(FileExistsError):
                self.model.save(path)

    def test_loader_rejects_bad_dimensions_nonfinite_weights_and_hashes(self):
        import base64
        import hashlib
        import numpy as np
        from cmbench.recognition.models.mlp import MotifMLP, canonical
        variants = []
        bad = self.model.to_dict()
        bad["architecture"]["hidden"] = 100000000
        variants.append(bad)
        bad = self.model.to_dict()
        bad["arrays"]["w1"]["dtype"] = "object"
        variants.append(bad)
        bad = self.model.to_dict()
        raw = np.full((512, 8), np.nan, dtype="<f4").tobytes()
        bad["arrays"]["w1"].update(data_base64=base64.b64encode(raw).decode(), sha256=hashlib.sha256(raw).hexdigest())
        variants.append(bad)
        bad = self.model.to_dict()
        bad["arrays"]["w1"]["sha256"] = "0" * 64
        variants.append(bad)
        bad = self.model.to_dict()
        bad["training"]["status"] = "incomplete"
        variants.append(bad)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            for bad in variants:
                bad.pop("payload_sha256")
                bad["payload_sha256"] = hashlib.sha256(canonical(bad)).hexdigest()
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    MotifMLP.load(path)
            path.write_text('{"schema":1,"schema":2}')
            with self.assertRaises(ValueError):
                MotifMLP.load(path)
            path.write_bytes(b" " * (2 * 1024 * 1024 + 1))
            with self.assertRaises(ValueError):
                MotifMLP.load(path)

    def test_invalid_training_bounds_and_interruption(self):
        from cmbench.recognition.models.mlp import train_mlp
        for kwargs in ({"epochs": 0}, {"hidden": 1000000}, {"batch_size": 999}, {"seed": True}):
            with self.assertRaises(ValueError):
                train_mlp(self.x, self.y, **{"seed": 1, **kwargs})
        with self.assertRaises(KeyboardInterrupt):
            train_mlp(self.x, self.y, seed=1, check=lambda: (_ for _ in ()).throw(KeyboardInterrupt()))


class VerifiedProposalTests(unittest.TestCase):
    def setUp(self):
        from cmbench.recognition.contracts import Task
        self.task = Task(2)
        self.original = Or(And(Var(0), Not(Var(1))), And(Not(Var(0)), Var(1)))

    def check(self, candidate, **kwargs):
        from cmbench.recognition.contracts import Proposal, RequestBudget, check_proposal
        proposal = Proposal(structural_digest(self.original), candidate, "learned", "test/v1", 0.99)
        return check_proposal(self.original, proposal, self.task, RequestBudget(self.task), **kwargs)

    def test_acceptance_and_wrong_near_match_rejection(self):
        accepted = self.check(Xor(Var(0), Var(1)))
        self.assertTrue(accepted.accepted)
        self.assertIsNotNone(accepted.evidence)
        rejected = self.check(Or(Var(0), Var(1)))
        self.assertFalse(rejected.accepted)
        self.assertEqual(rejected.reason, "semantic_mismatch")
        self.assertEqual(reference_bits(self.original, 2), 6)

    def test_cycle_and_stale_proposals(self):
        from cmbench.recognition.contracts import Proposal, RequestBudget, check_proposal
        candidate = Xor(Var(0), Var(1))
        self.assertEqual(self.check(candidate, visited=frozenset({structural_digest(candidate)})).reason, "cycle_or_redundant")
        stale = Proposal("0" * 64, candidate, "learned", "test/v1", 1)
        self.assertEqual(check_proposal(self.original, stale, self.task, RequestBudget(self.task)).reason, "stale_or_malformed_proposal")

    def test_timeout_cannot_accept_a_proof(self):
        from cmbench.recognition.contracts import RequestBudget
        with patch.object(RequestBudget, "check", side_effect=TimeoutError):
            checked = self.check(Xor(Var(0), Var(1)))
        self.assertFalse(checked.accepted)
        self.assertEqual(checked.reason, "verification_timeout")

    def test_advice_bypass_never_calls_model(self):
        from cmbench.recognition.contracts import Task
        from cmbench.recognition.motif_experiment import MotifConfig, measure_motif
        from cmbench.recognition.corpus import Case
        from unittest.mock import Mock
        self.task = Task(2, learned_enabled=False)
        self.assertEqual(self.check(Xor(Var(0), Var(1))).reason, "learned_disabled")
        case = Case("bypass", "affine", "test", 2, 1, self.original, structural_digest(self.original), "group")
        model = Mock()
        row = measure_motif(case, 1, "mlp", model, None, MotifConfig(learned_enabled=False))
        model.score.assert_not_called()
        self.assertEqual(row["mismatches"], 0)
        self.assertEqual(row["reason"], "learned_disabled")

    def test_unavailable_backend_is_not_silently_substituted(self):
        from cmbench.recognition.motif_experiment import MotifConfig, measure_motif
        with self.assertRaises(ValueError):
            measure_motif(None, 1, "missing_native_solver", None, None, MotifConfig())


class MotifExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cmbench.recognition.motif_data import make_motif_documents
        cls.documents = make_motif_documents(72, (2, 1, 1, 1))

    def config(self):
        from cmbench.recognition.motif_experiment import MotifConfig
        return MotifConfig(data_seed=72, training_seeds=(4,), parent_counts=(2, 1, 1, 1),
                           epochs=2, batch_size=4, hidden=8, rounds=1)

    def test_deterministic_data_and_split_leakage_rejection(self):
        from cmbench.recognition.motif_data import make_motif_documents, validate_documents
        self.assertEqual(self.documents, make_motif_documents(72, (2, 1, 1, 1)))
        bad = copy.deepcopy(self.documents)
        bad[0]["split"] = "test"
        with self.assertRaises(ValueError):
            validate_documents(bad)
        bad = copy.deepcopy(self.documents)
        bad[0]["label"] ^= 1
        with self.assertRaises(ValueError):
            validate_documents(bad)

    def test_bounded_dag_refuses_cycles_and_unsafe_operations(self):
        from cmbench.recognition.motif_data import decode_bounded_dag
        for dag in ({"version": 2, "nodes": [{"op": "not", "a": 0}], "root": 0},
                    {"version": 2, "nodes": [{"op": "import", "a": 0, "b": 0}], "root": 0}):
            with self.assertRaises(ValueError):
                decode_bounded_dag(dag)

    def test_complete_pipeline_hashes_accounting_and_phases(self):
        import hashlib
        from cmbench.recognition.motif_experiment import run_motif_experiment
        from scripts.crse_learning_verify import verify_run
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "run"
            result = run_motif_experiment(self.config(), output, progress=lambda s: None)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["semantic_mismatches"], 0)
            self.assertTrue(result["model_cards"][0]["training"]["parameters_updated"])
            self.assertEqual(result["model_cards"][0]["training"]["rows"], 4)
            manifest = json.loads((output / "manifest.json").read_text())
            for name, digest in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), digest)
            for row in result["rows"]:
                for field in ("feature_ns", "inference_ns", "candidate_ns", "verification_ns", "build_ns", "kernel_ns", "conversion_ns", "model_load_ns", "audit_ns"):
                    self.assertGreaterEqual(row[field], 0)
                self.assertGreater(row["total_ns"], 0)
                if row["accepted"]:
                    self.assertEqual(json.loads(row["trace_json"])["proof_scope"], "this instance only, not a rule over metavariables")
            evaluated = run_motif_experiment(self.config(), Path(temp) / "eval", phase="evaluate", input_dir=output, progress=lambda s: None)
            self.assertEqual(evaluated["status"], "complete")
            self.assertEqual(evaluated["dataset_sha256"], result["dataset_sha256"])
            self.assertEqual(verify_run(output)["status"], "verified")
            with (output / "raw.csv").open("a", encoding="utf-8") as handle:
                handle.write("tampered\n")
            with self.assertRaises(ValueError):
                verify_run(output)
            with self.assertRaises(FileExistsError):
                run_motif_experiment(self.config(), output, progress=lambda s: None)

    def test_interrupted_and_budget_runs_are_retained_incomplete(self):
        from cmbench.recognition.motif_experiment import run_motif_experiment
        with tempfile.TemporaryDirectory() as temp:
            for name, error in (("interrupt", KeyboardInterrupt), ("budget", BudgetExhausted)):
                output = Path(temp) / name
                with patch("cmbench.recognition.motif_experiment.train_mlp", side_effect=error):
                    result = run_motif_experiment(self.config(), output, progress=lambda s: None)
                self.assertNotEqual(result["status"], "complete")
                self.assertTrue((output / "manifest.json").exists())
                self.assertFalse((output / "model_index.json").exists())

    def test_cli_preview_and_network_free_defaults(self):
        from scripts.cm_recognition_learning import main as learning_main
        with tempfile.TemporaryDirectory() as temp, patch("socket.socket", side_effect=AssertionError):
            output = Path(temp) / "absent"
            with patch("scripts.cm_recognition_learning.run_motif_experiment") as run, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(learning_main(["--output", str(output)]), 0)
                run.assert_not_called()
            self.assertFalse(output.exists())


class OfflineProviderAndRegisterTests(unittest.TestCase):
    def test_safe_fake_dsl_still_requires_exact_acceptance(self):
        from cm_expr_serde import expr_to_json_dag
        from cmbench.recognition.contracts import Task, RequestBudget, check_proposal
        from cmbench.recognition.offline_proposals import FakeOfflineProvider, parse_offline_proposal
        original = Not(Not(Var(0)))
        response = json.dumps({"schema": "crse-bool-dsl/v1", "expression": expr_to_json_dag(Var(0))})
        provider = FakeOfflineProvider((response,))
        with patch("socket.socket", side_effect=AssertionError):
            proposal = parse_offline_proposal(provider.propose("bounded prompt"), structural_digest(original), Task(2))
        self.assertTrue(check_proposal(original, proposal, Task(2), RequestBudget(Task(2))).accepted)
        with self.assertRaises(ValueError):
            provider.propose("second call")

    def test_malformed_unsafe_and_oversized_dsl(self):
        from cmbench.recognition.contracts import Task
        from cmbench.recognition.offline_proposals import parse_offline_proposal
        for text in ("import os", '{"schema":"crse-bool-dsl/v1","shell":"anything"}', "{" * 4000, "x" * 4097):
            with self.assertRaises(ValueError):
                parse_offline_proposal(text, "0" * 64, Task(2))

    def test_register_preserves_all_tracks_and_application_families(self):
        root = Path(__file__).resolve().parents[1]
        register = json.loads((root / "docs/recognition/experiment_register.json").read_text(encoding="utf-8"))
        self.assertEqual([t["id"] for t in register["tracks"]], [f"R{i:02d}" for i in range(1, 19)])
        self.assertEqual(len(register["applications"]), 8)
        required = {"hypothesis", "input_output_contract", "representation", "models_and_deterministic_controls",
                    "exact_checker", "source_data", "dependencies", "next_experiment", "results", "resource_needs", "status"}
        for track in register["tracks"]:
            self.assertTrue(required <= set(track))
            self.assertIn(track["status"], register["allowed_statuses"])
            self.assertIn("PyTorch 2.10.0+cpu (isolated optional environment)",
                          track["dependencies"]["available"])
        r12 = next(track for track in register["tracks"] if track["id"] == "R12")
        self.assertTrue(any(result.get("report") == "LEARNING_MILESTONE_C_2026_08_29.md"
                            for result in r12["results"]))
        self.assertIn("directional quotient", register["transformation_inventory"])


if __name__ == "__main__":
    unittest.main()
