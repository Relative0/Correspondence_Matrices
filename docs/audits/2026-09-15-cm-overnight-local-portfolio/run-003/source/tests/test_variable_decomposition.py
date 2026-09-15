"""Optional PyTorch tests for variable-size exact decomposition learning."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import torch

from cmbench.recognition.decomposition_data import (
    compose_xor_factors, make_decomposition_documents, matrix_image,
    validate_decomposition_documents, xor_partition_witness,
)
from cmbench.recognition.models.mlp import canonical
from cmbench.recognition.models.variable_torch_models import (
    ARCHITECTURES, batch_graphs, build_model, load_model, parameter_count, save_model, state_sha256,
)
from cmbench.recognition.variable_decomposition_experiment import (
    Budget, VariableDecompositionConfig, batch_schedule, choose_threshold, generated_examples,
    natural_examples, train_classifier,
)
from cmbench.recognition.variable_graph_inputs import NODE_FEATURES, graph_from_document


class ExactDecompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = make_decomposition_documents(19, (3, 1, 1, 1))

    def test_pairs_have_exact_witness_or_distance_one(self):
        audit = validate_decomposition_documents(self.documents, (3, 1, 1, 1))
        self.assertEqual(audit["parent_count"], 6)
        examples = generated_examples(self.documents)
        by_parent = {}
        for example in examples:
            by_parent.setdefault(example.parent_id, []).append(example)
            witness = xor_partition_witness(example.bits, example.n_vars)
            self.assertEqual(witness is not None, bool(example.label))
            if witness is not None:
                self.assertEqual(compose_xor_factors(witness, example.n_vars), example.bits)
        for pair in by_parent.values():
            positive = next(example for example in pair if example.label)
            negative = next(example for example in pair if not example.label)
            self.assertEqual((positive.bits ^ negative.bits).bit_count(), 1)

    def test_matrix_canvas_and_graph_encode_size(self):
        document = next(row for row in self.documents if row["n_vars"] == 10)
        example = generated_examples([document])[0]
        image = matrix_image(example.bits, example.n_vars)
        self.assertEqual(image.shape, (2, 32, 32))
        self.assertEqual(int(image[1].sum()), 1024)
        graph = graph_from_document(example.document, 10)
        self.assertEqual(graph.node_features.shape[1], NODE_FEATURES)
        self.assertTrue((graph.node_features[:, -1] == 1).all())


class VariableModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)
        cls.examples = generated_examples(make_decomposition_documents(23, (2, 1, 1, 1)))

    def test_all_models_forward_inside_bound(self):
        selected = self.examples[:2]
        matrices = torch.stack([torch.from_numpy(matrix_image(example.bits, example.n_vars)) for example in selected])
        graphs = batch_graphs([graph_from_document(example.document, example.n_vars) for example in selected])
        for name in ARCHITECTURES:
            with self.subTest(name=name):
                model = build_model(name)
                self.assertGreaterEqual(parameter_count(model), 25_000)
                self.assertLessEqual(parameter_count(model), 200_000)
                logits, embedding = model(matrices if name != "variable_graph_gnn" else None,
                                          graphs if name in ("variable_graph_gnn", "variable_fused") else None)
                self.assertEqual(logits.shape, (2,))
                self.assertEqual(embedding.shape[0], 2)

    def test_training_calibration_and_safe_roundtrip(self):
        config = VariableDecompositionConfig(parent_counts=(2, 1, 1, 1), epochs=1,
                                              batch_size=4, epfl_limit=2, max_seconds=30)
        training = [example for example in self.examples if example.split == "train"]
        model, provenance = train_classifier("variable_graph_gnn", training, config.training_seeds[0],
                                             config, Budget(30), batch_schedule(len(training), config, config.training_seeds[0]))
        provenance.update({"dataset_sha256": "1" * 64, "training_ids_sha256": "2" * 64})
        threshold, accuracy = choose_threshold([0, 1, 0, 1], [.1, .9, .4, .6])
        self.assertEqual((threshold, accuracy), (.5, 1.0))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.json"
            digest = save_model(model, "variable_graph_gnn", provenance,
                                {"torch": torch.__version__, "device": "cpu", "dtype": "float32"}, path)
            name, restored, loaded, _metadata, loaded_digest = load_model(path)
            self.assertEqual((name, loaded_digest), ("variable_graph_gnn", digest))
            self.assertEqual(state_sha256(restored), loaded["final_state_sha256"])
            malformed = json.loads(path.read_text(encoding="utf-8"))
            malformed["training"]["steps"] += 1
            payload = {key: malformed[key] for key in
                       ("schema", "architecture", "parameter_count", "training", "metadata", "state")}
            malformed["payload_sha256"] = hashlib.sha256(canonical(payload)).hexdigest()
            path.write_text(json.dumps(malformed), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_model(path)

    def test_epfl_is_frozen_evaluation_only_and_currently_all_negative(self):
        examples, manifest = natural_examples(4)
        self.assertFalse(manifest["training_use"])
        self.assertFalse(manifest["threshold_selection_use"])
        self.assertEqual(manifest["natural_positive_count"], 0)
        self.assertTrue(all(example.label == 0 for example in examples))


if __name__ == "__main__":
    unittest.main()
