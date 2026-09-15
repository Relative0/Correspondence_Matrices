"""Optional PyTorch tests for per-variable cut learning and source controls."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import torch

from cmbench.recognition.models.mlp import canonical
from cmbench.recognition.models.natural_variable_cut_torch_models import (
    ARCHITECTURES,
    build_model,
    load_model,
    parameter_count,
    save_model,
    state_sha256,
)
from cmbench.recognition.natural_cut_experiment import (
    cut_examples_from_documents,
    pair_schedule,
    paired_examples,
)
from cmbench.recognition.natural_decomposition import partition_witness
from cmbench.recognition.natural_decomposition_experiment import DEFAULT_SCOUT, Budget
from cmbench.recognition.natural_decomposition_matched_data import make_matched_natural_documents
from cmbench.recognition.natural_variable_cut_experiment import (
    NaturalVariableCutConfig,
    equivariance_audit,
    forward,
    outputs,
    train_model,
)
from cmbench.recognition.source_interaction import (
    source_exact_interaction_edges,
    source_exact_partition,
    source_interaction_edges,
    source_partition_proposal,
)


class NaturalVariableCutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)
        documents, _provenance = make_matched_natural_documents(DEFAULT_SCOUT)
        cls.documents = documents
        cls.examples = cut_examples_from_documents(documents)
        cls.training_pairs = paired_examples(cls.examples, "train")

    def test_source_symbolic_partition_is_exact_and_overapprox_is_sound(self):
        exact_proposals = 0
        for document, example in zip(self.documents, self.examples):
            exact_edges = set(source_exact_interaction_edges(example.base.document, example.base.n_vars))
            approximate_edges = set(source_interaction_edges(example.base.document, example.base.n_vars))
            self.assertLessEqual(exact_edges, approximate_edges)
            exact = source_exact_partition(example.base.document, example.base.n_vars)
            approximate = source_partition_proposal(example.base.document, example.base.n_vars)
            self.assertEqual(exact is not None, bool(example.base.label))
            if exact is not None:
                exact_proposals += 1
                self.assertIsNotNone(partition_witness(example.base.bits, example.base.n_vars, exact))
            if approximate is not None:
                self.assertIsNotNone(partition_witness(example.base.bits, example.base.n_vars, approximate))
        self.assertEqual(exact_proposals, 94)

    def test_shared_variable_head_is_exactly_equivariant_for_nonanchor_swap(self):
        evaluation = [example for example in self.examples if example.base.split == "test"]
        for name in ARCHITECTURES:
            model = build_model(name)
            rows = equivariance_audit(model, evaluation)
            self.assertTrue(rows)
            self.assertEqual(max(row["maximum_error"] for row in rows), 0.0)
            logits, cuts, embedding = forward(model, evaluation[:3])
            self.assertEqual(logits.shape, (3,))
            self.assertEqual(cuts.shape, (3, 10))
            self.assertEqual(embedding.shape, (3, 64))
            self.assertLess(parameter_count(model), 200_000)

    def test_training_and_safe_roundtrip(self):
        config = NaturalVariableCutConfig(epochs=1, batch_pairs=2, max_seconds=30)
        pairs = self.training_pairs[:4]
        model, training = train_model(
            "variable_cut_rank_gnn", pairs, config.training_seeds[0], config, Budget(30),
            pair_schedule(len(pairs), config, config.training_seeds[0]))
        training.update({"dataset_sha256": "1" * 64, "training_pair_ids_sha256": "2" * 64})
        self.assertEqual(len(outputs(model, [item for pair in pairs for item in pair])), 8)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.json"
            digest = save_model(model, "variable_cut_rank_gnn", training,
                {"torch": torch.__version__, "device": "cpu", "dtype": "float32"}, path)
            name, restored, loaded_training, _metadata, loaded_digest = load_model(path)
            self.assertEqual((name, loaded_digest), ("variable_cut_rank_gnn", digest))
            self.assertEqual(loaded_training, training)
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
