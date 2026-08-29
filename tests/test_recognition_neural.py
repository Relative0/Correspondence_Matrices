"""Optional PyTorch tests; run with .venv-crse-neural, not the NumPy-only venv."""
from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

import torch

from cmbench.recognition.graph_inputs import EDGE_ROLES, OPS, graph_from_document
from cmbench.recognition.models.torch_models import (
    ARCHITECTURES, batch_graphs, build_model, load_model, parameter_count, save_model, state_sha256,
)
from cmbench.recognition.models.mlp import canonical
from cmbench.recognition.motif_data import make_motif_documents
from cmbench.recognition.neural_experiment import (
    Budget, NeuralConfig, _batch_schedule, _generated_examples, equivalent_variant,
    load_epfl_examples, train_classifier, train_retrieval,
)
from cmbench.recognition.teacher import teach


class GraphInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = make_motif_documents(7, (2, 1, 1, 1))

    def test_graph_preserves_roles_variable_identity_negation_and_sharing(self):
        document = self.documents[0]["expression"]
        graph = graph_from_document(document)
        self.assertEqual(graph.node_features.shape[1], len(OPS) + 8)
        self.assertTrue(set(graph.edge_roles.tolist()) <= set(range(len(EDGE_ROLES))))
        for index, node in enumerate(document["nodes"]):
            if node["op"] == "var":
                self.assertEqual(graph.node_features[index, len(OPS) + node["i"]], 1)
        expected_edges = sum(0 if node["op"] == "var" else 1 if node["op"] == "not" else 2
                             for node in document["nodes"])
        self.assertEqual(graph.edge_index.shape[1], expected_edges)
        referenced = graph.edge_index[0].tolist()
        self.assertTrue(any(referenced.count(node) > 1 for node in set(referenced)))

    def test_equivalence_augmentation_is_exact_and_structurally_new(self):
        document = self.documents[-1]
        example = _generated_examples([document])[0]
        variant = equivalent_variant(example, 0)
        self.assertEqual(teach(example.expr, 8).bits, teach(variant.expr, 8).bits)
        self.assertNotEqual(example.document, variant.document)


class TorchModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)
        cls.documents = make_motif_documents(11, (2, 1, 1, 1))
        cls.examples = _generated_examples(cls.documents)

    def test_all_architectures_are_in_approved_band_and_forward(self):
        selected = self.examples[:2]
        matrices = torch.stack([torch.from_numpy(teach(example.expr, 8).tensor()) for example in selected])
        graphs = batch_graphs([graph_from_document(example.document) for example in selected])
        for name in ARCHITECTURES:
            with self.subTest(name=name):
                model = build_model(name)
                self.assertGreaterEqual(parameter_count(model), 50_000)
                self.assertLessEqual(parameter_count(model), 250_000)
                logits, embedding = model(matrices if name in ("matrix_mlp", "matrix_cnn", "fused") else None,
                                          graphs if name in ("graph_gnn", "fused", "graph_retrieval") else None)
                self.assertEqual(embedding.shape[0], 2)
                self.assertIsNone(logits) if name == "graph_retrieval" else self.assertEqual(logits.shape, (2,))

    def test_actual_training_updates_and_safe_roundtrip(self):
        config = NeuralConfig(parent_counts=(2, 1, 1, 1), epochs=1, retrieval_epochs=1,
                              batch_size=4, max_seconds=30)
        training = [example for example in self.examples if example.split == "train"]
        schedule = _batch_schedule(len(training), config, config.training_seeds[0], 1)
        model, provenance = train_classifier("graph_gnn", training, config.training_seeds[0],
                                             config, Budget(30), schedule)
        self.assertTrue(provenance["parameters_updated"])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.json"
            provenance["final_state_sha256"] = state_sha256(model)
            provenance.update({"dataset_sha256": "1" * 64, "training_ids_sha256": "2" * 64})
            expected_metadata = {"torch": torch.__version__, "device": "cpu", "dtype": "float32",
                                 "graph_memory_bytes": 1}
            digest = save_model(model, "graph_gnn", provenance, expected_metadata, path)
            name, restored, loaded_training, metadata, loaded_digest = load_model(path)
            self.assertEqual((name, loaded_digest, metadata), ("graph_gnn", digest, expected_metadata))
            self.assertEqual(state_sha256(restored), loaded_training["final_state_sha256"])
            tampered = json.loads(path.read_text(encoding="utf-8"))
            tampered["parameter_count"] += 1
            path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_model(path)
            malformed = json.loads(json.dumps(tampered))
            malformed["parameter_count"] -= 1
            malformed["training"]["steps"] += 1
            payload = {key: malformed[key] for key in
                       ("schema", "architecture", "parameter_count", "training", "metadata", "state")}
            malformed["payload_sha256"] = hashlib.sha256(canonical(payload)).hexdigest()
            path.write_text(json.dumps(malformed), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_model(path)

    def test_contrastive_training_updates(self):
        config = NeuralConfig(parent_counts=(2, 1, 1, 1), epochs=1, retrieval_epochs=1,
                              batch_size=4, max_seconds=30)
        training = [example for example in self.examples if example.split == "train"]
        variants = [equivalent_variant(example, index) for index, example in enumerate(training)]
        schedule = _batch_schedule(len(training), config, config.training_seeds[0], 1)
        _model, provenance = train_retrieval(training, variants, config.training_seeds[0],
                                             config, Budget(30), schedule)
        self.assertTrue(provenance["parameters_updated"])

    def test_frozen_epfl_selection_is_local_provenance_checked_and_eval_only(self):
        examples, manifest = load_epfl_examples(4)
        self.assertEqual(len(examples), 4)
        self.assertFalse(manifest["training_use"])
        self.assertEqual(len({example.source_id for example in examples}), 4)
        self.assertTrue(all(teach(example.expr, 8).bits == example.bits for example in examples))
        self.assertTrue(all(len(graph_from_document(example.document).node_features) >= 1 for example in examples))


if __name__ == "__main__":
    unittest.main()
