"""Optional PyTorch tests for natural-source exact decomposition learning."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import torch

from cm_exprlib import And, Or, Var, Xor
from cmbench.recognition.models.mlp import canonical
from cmbench.recognition.models.natural_torch_models import (
    ARCHITECTURES, build_model, load_model, parameter_count, save_model, state_sha256,
)
from cmbench.recognition.natural_decomposition import (
    analyze_decomposition, compose_partition_witness, interaction_edges, interaction_target,
    partition_witness, semantic_variables,
)
from cmbench.recognition.natural_decomposition_data import (
    make_natural_decomposition_documents, validate_natural_decomposition_documents,
)
from cmbench.recognition.natural_decomposition_experiment import (
    DEFAULT_SCOUT, Budget, NaturalDecompositionConfig, _batch_inputs, batch_schedule,
    examples_from_documents, forward, predicted_partition, train_model,
)
from cmbench.recognition.natural_decomposition_decoder_experiment import minimum_cut_partition
from cmbench.recognition.natural_decomposition_matched_data import (
    make_matched_natural_documents, validate_matched_documents,
)
from cmbench.recognition.portfolio import reference_bits


class ANFPartitionTests(unittest.TestCase):
    def test_discovers_permuted_exact_partition_and_rejects_cross_term(self):
        positive = Xor(And(Var(0), Var(2)), Or(Var(1), Var(3)))
        bits = reference_bits(positive, 4)
        analysis = analyze_decomposition(bits, 4)
        self.assertEqual(analysis.components, ((0, 2), (1, 3)))
        self.assertEqual(set(analysis.row_variables), {0, 2})
        self.assertEqual(compose_partition_witness(analysis.witness, 4), bits)
        negative = Xor(positive, And(Var(0), Var(1)))
        self.assertFalse(analyze_decomposition(reference_bits(negative, 4), 4).decomposable)

    def test_interaction_targets_preserve_variable_identity_and_mask(self):
        expr = Xor(And(Var(0), Var(2)), Var(1))
        bits = reference_bits(expr, 4)
        self.assertEqual(semantic_variables(bits, 4), (0, 1, 2))
        self.assertEqual(interaction_edges(bits, 4), ((0, 2),))
        labels, mask = interaction_target(bits, 4)
        self.assertEqual((len(labels), len(mask), sum(mask)), (45, 45, 6))
        self.assertIsNotNone(partition_witness(bits, 4, (0, 2)))

    def test_predicted_edge_components_produce_concrete_partition(self):
        scores = []
        for left in range(10):
            for right in range(left + 1, 10):
                scores.append(1.0 if right < 4 and {left, right} <= {0, 2} else
                              1.0 if right < 4 and {left, right} <= {1, 3} else 0.0)
        partition = predicted_partition(tuple(scores), 4)
        self.assertEqual(set(partition), {0, 2})

    def test_minimum_cut_decoder_recovers_obvious_partition(self):
        scores = []
        for left in range(10):
            for right in range(left + 1, 10):
                score = 0.0
                if right < 4:
                    score = 0.95 if ({left, right} <= {0, 2} or {left, right} <= {1, 3}) else 0.05
                scores.append(score)
        partition, cut_score = minimum_cut_partition(tuple(scores), 4)
        self.assertEqual(set(partition), {0, 2})
        self.assertAlmostEqual(cut_score, 0.05)


class NaturalDatasetAndModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)
        cls.documents, cls.provenance = make_natural_decomposition_documents(DEFAULT_SCOUT)
        cls.examples = examples_from_documents(cls.documents)

    def test_dataset_is_natural_balanced_circuit_disjoint_and_exact(self):
        audit = validate_natural_decomposition_documents(self.documents)
        self.assertEqual(audit["rows"], 188)
        self.assertEqual(audit["natural_positive_count"], 94)
        self.assertEqual(audit["circuit_overlap"], 0)
        self.assertFalse(self.provenance["external_download_performed"])
        self.assertEqual(set(audit["size_counts"]), {"4", "5", "6", "7", "8", "9", "10"})

    def test_structure_matched_pairs_are_exact_and_balanced(self):
        documents, provenance = make_matched_natural_documents(DEFAULT_SCOUT)
        audit = validate_matched_documents(documents)
        self.assertEqual((audit["rows"], audit["matched_pairs"]), (188, 94))
        self.assertEqual((audit["natural_positive_count"], audit["rows"] - audit["natural_positive_count"]), (94, 94))
        self.assertEqual(audit["same_n_vars_fraction"], 1.0)
        self.assertGreaterEqual(audit["same_variant_fraction"], 0.9)
        self.assertEqual(
            (audit["median_source_nodes_delta"], audit["median_depth_delta"], audit["median_source_edges_delta"]),
            (0.0, 0.0, 0.0),
        )
        self.assertIn("within the same circuit", provenance["matching"])

    def test_models_forward_and_training_roundtrip(self):
        selected = [example for example in self.examples if example.split == "train"][:16]
        for name in ARCHITECTURES:
            with self.subTest(name=name):
                model = build_model(name)
                logits, interactions, embedding = forward(model, name, selected[:3])
                self.assertEqual(logits.shape, (3,))
                self.assertEqual(embedding.shape[0], 3)
                self.assertIsNotNone(interactions) if name == "natural_multitask_gnn" else self.assertIsNone(interactions)
        config = NaturalDecompositionConfig(epochs=1, batch_size=8, max_seconds=30)
        model, provenance = train_model("natural_multitask_gnn", selected, config.training_seeds[0], config,
                                        Budget(30), batch_schedule(len(selected), config, config.training_seeds[0]))
        provenance.update({"dataset_sha256": "1" * 64, "training_ids_sha256": "2" * 64})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.json"
            digest = save_model(model, "natural_multitask_gnn", provenance,
                {"torch": torch.__version__, "device": "cpu", "dtype": "float32"}, path)
            name, restored, training, _metadata, loaded_digest = load_model(path)
            self.assertEqual((name, loaded_digest), ("natural_multitask_gnn", digest))
            self.assertEqual(state_sha256(restored), training["final_state_sha256"])
            malformed = json.loads(path.read_text(encoding="utf-8"))
            malformed["parameter_count"] += 1
            payload = {key: malformed[key] for key in
                       ("schema", "architecture", "parameter_count", "training", "metadata", "state")}
            malformed["payload_sha256"] = hashlib.sha256(canonical(payload)).hexdigest()
            path.write_text(json.dumps(malformed), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_model(path)


if __name__ == "__main__":
    unittest.main()
