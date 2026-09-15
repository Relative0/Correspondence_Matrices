"""Optional PyTorch tests for direct-cut and same-pair ranking."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import torch

from cmbench.recognition.models.mlp import canonical
from cmbench.recognition.models.natural_cut_torch_models import (
    ARCHITECTURES,
    build_model,
    load_model,
    parameter_count,
    save_model,
    state_sha256,
)
from cmbench.recognition.natural_cut_experiment import (
    DEFAULT_SCOUT,
    Budget,
    NaturalCutConfig,
    cut_examples_from_documents,
    decode_direct_cut,
    forward,
    pair_schedule,
    paired_examples,
    train_model,
)
from cmbench.recognition.natural_decomposition_matched_data import make_matched_natural_documents


class NaturalCutRankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)
        documents, _provenance = make_matched_natural_documents(DEFAULT_SCOUT)
        cls.examples = cut_examples_from_documents(documents)
        cls.training_pairs = paired_examples(cls.examples, "train")

    def test_targets_and_pairs_preserve_canonical_orientation(self):
        self.assertEqual(len(paired_examples(self.examples)), 94)
        self.assertEqual(len(self.training_pairs), 48)
        for positive, negative in self.training_pairs:
            self.assertEqual((positive.base.label, negative.base.label), (1, 0))
            self.assertEqual(positive.row_target[0], 1)
            self.assertLess(sum(positive.row_target), positive.base.n_vars)
            self.assertEqual(sum(negative.row_target), 0)
            self.assertEqual(sum(positive.row_mask), positive.base.n_vars)

    def test_direct_decoder_recovers_bounded_obvious_cut(self):
        probabilities = (0.95, 0.05, 0.95, 0.05, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
        partition, nll, margin = decode_direct_cut(probabilities, 4)
        self.assertEqual(partition, (0, 2))
        self.assertGreater(margin, 0)
        self.assertLess(nll, 0.1)

    def test_models_forward_train_and_safe_roundtrip(self):
        selected = [item for pair in self.training_pairs[:3] for item in pair]
        for name in ARCHITECTURES:
            with self.subTest(name=name):
                model = build_model(name)
                logits, cuts, embedding = forward(model, name, selected)
                self.assertEqual(logits.shape, (len(selected),))
                self.assertEqual(embedding.shape[0], len(selected))
                if name == "structural_pair_ranker":
                    self.assertIsNone(cuts)
                    self.assertEqual(parameter_count(model), 18)
                else:
                    self.assertEqual(cuts.shape, (len(selected), 10))
                    self.assertLess(parameter_count(model), 150_000)

        config = NaturalCutConfig(epochs=1, batch_pairs=2, max_seconds=30)
        pairs = self.training_pairs[:4]
        model, training = train_model(
            "cut_rank_gnn",
            pairs,
            config.training_seeds[0],
            config,
            Budget(30),
            pair_schedule(len(pairs), config, config.training_seeds[0]),
        )
        training.update({"dataset_sha256": "1" * 64, "training_pair_ids_sha256": "2" * 64})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.json"
            digest = save_model(
                model,
                "cut_rank_gnn",
                training,
                {"torch": torch.__version__, "device": "cpu", "dtype": "float32"},
                path,
            )
            name, restored, loaded_training, _metadata, loaded_digest = load_model(path)
            self.assertEqual((name, loaded_digest), ("cut_rank_gnn", digest))
            self.assertEqual(loaded_training, training)
            self.assertEqual(state_sha256(restored), training["final_state_sha256"])

            malformed = json.loads(path.read_text(encoding="utf-8"))
            malformed["parameter_count"] += 1
            payload = {
                key: malformed[key]
                for key in ("schema", "architecture", "parameter_count", "training", "metadata", "state")
            }
            malformed["payload_sha256"] = hashlib.sha256(canonical(payload)).hexdigest()
            path.write_text(json.dumps(malformed), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_model(path)


if __name__ == "__main__":
    unittest.main()
