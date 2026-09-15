import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cm_expr_serde import expr_from_json
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.source_anf_hybrid import (
    ProductCache,
    packed_monomials,
    packed_truth_bits,
    source_anf_packed,
    source_packed_partition,
)
from cmbench.recognition.source_interaction import source_anf_monomials, source_exact_partition
from cmbench.recognition.yosys_human_decomposition_data import (
    CASES_PER_LABEL_PER_SPLIT,
    FIXTURE_ROOT,
    SOURCE_COMMIT,
    SOURCE_MANIFEST,
    SPLITS,
    make_yosys_human_documents,
)
from cmbench.recognition.yosys_source_anf_experiment import (
    YosysSourceAnfConfig,
    document_truth_bits,
    run_yosys_source_anf_experiment,
)


class YosysSourceAnfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents, cls.provenance = make_yosys_human_documents()

    def test_source_fixture_is_pinned_and_exact(self):
        manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["upstream_commit"], SOURCE_COMMIT)
        self.assertEqual(manifest["license"], "ISC")
        self.assertFalse(self.provenance["network_access_performed"])
        self.assertFalse(self.provenance["source_checkout_modified"])
        for row in manifest["files"]:
            actual = hashlib.sha256((FIXTURE_ROOT / row["fixture_path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, row["sha256"])

    def test_dataset_is_balanced_sealed_and_unique(self):
        self.assertEqual(len(self.documents), 4 * CASES_PER_LABEL_PER_SPLIT)
        for split in SPLITS:
            for label in (0, 1):
                self.assertEqual(
                    sum(row["split"] == split and row["label"] == label for row in self.documents),
                    CASES_PER_LABEL_PER_SPLIT,
                )
        self.assertEqual(len({row["semantic_sha256"] for row in self.documents}), len(self.documents))
        self.assertEqual(len({row["alpha_sha256"] for row in self.documents}), len(self.documents))
        self.assertTrue(all(row["training_use"] is False for row in self.documents))

    def test_all_exact_paths_reconstruct_the_independent_oracle(self):
        cache = ProductCache(1024)
        for row in self.documents:
            document, n_vars = row["expression_v2"], row["n_vars"]
            reference = reference_bits(expr_from_json(document), n_vars)
            polynomial, _stats = source_anf_packed(document, n_vars)
            self.assertEqual(document_truth_bits(document, n_vars), reference)
            self.assertEqual(packed_truth_bits(polynomial, n_vars), reference)
            self.assertEqual(packed_monomials(polynomial, n_vars), source_anf_monomials(document, n_vars))
            expected = source_exact_partition(document, n_vars)
            self.assertEqual(source_packed_partition(document, n_vars)[0], expected)
            self.assertEqual(source_packed_partition(document, n_vars, cache=cache)[0], expected)

    def test_bounded_run_writes_complete_artifact_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            result = run_yosys_source_anf_experiment(
                YosysSourceAnfConfig(repetitions=5, max_seconds=120), output, progress=lambda _: None
            )
            self.assertEqual(result["status"], "complete")
            self.assertTrue(result["criteria"]["exact"])
            self.assertEqual(result["semantic_mismatches"], 0)
            self.assertIn("historical_source_unchanged", result["retained_c6"])
            self.assertIn("historical_source_changes", result["retained_c6"])
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {"run_spec.json", "dataset.json", "dataset_provenance.json", "benchmark_raw.jsonl",
                 "summary.json", "report.md", "manifest.json"},
            )


if __name__ == "__main__":
    unittest.main()
