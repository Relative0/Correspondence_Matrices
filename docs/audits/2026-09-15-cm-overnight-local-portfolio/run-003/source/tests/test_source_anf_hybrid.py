"""Tests for packed and budgeted exact source-DAG ANF."""
from __future__ import annotations

import copy
import random
import unittest

from cmbench.recognition.natural_decomposition import analyze_decomposition
from cmbench.recognition.natural_decomposition_experiment import DEFAULT_SCOUT
from cmbench.recognition.natural_decomposition_matched_data import make_matched_natural_documents
from cmbench.recognition.natural_source_anf_experiment import _execute
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.source_anf_hybrid import (
    ProductCache,
    multiply_packed,
    packed_monomials,
    packed_truth_bits,
    source_anf_packed,
    source_hybrid_partition,
    source_packed_partition,
    subset_zeta,
)
from cmbench.recognition.source_interaction import source_anf_monomials
from cm_expr_serde import expr_from_json


def naive_product(left: int, right: int, n_vars: int) -> int:
    result = 0
    for first in packed_monomials(left, n_vars):
        for second in packed_monomials(right, n_vars):
            result ^= 1 << (first | second)
    return result


class SourceAnfHybridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents, _provenance = make_matched_natural_documents(DEFAULT_SCOUT)

    def test_subset_transform_and_or_convolution_are_exact(self):
        generator = random.Random(20260830)
        for n_vars in range(2, 8):
            limit = 1 << (1 << n_vars)
            for _ in range(20):
                left = generator.randrange(limit)
                right = generator.randrange(limit)
                self.assertEqual(subset_zeta(subset_zeta(left, n_vars), n_vars), left)
                self.assertEqual(multiply_packed(left, right, n_vars), naive_product(left, right, n_vars))

    def test_packed_source_matches_set_source_and_truth_on_frozen_cases(self):
        for row in self.documents:
            polynomial, stats = source_anf_packed(row["expression_v2"], row["n_vars"])
            self.assertEqual(packed_monomials(polynomial, row["n_vars"]),
                             source_anf_monomials(row["expression_v2"], row["n_vars"]))
            bits = reference_bits(expr_from_json(row["expression_v2"]), row["n_vars"])
            self.assertEqual(packed_truth_bits(polynomial, row["n_vars"]), bits)
            partition, _ = source_packed_partition(row["expression_v2"], row["n_vars"])
            self.assertEqual(partition, analyze_decomposition(bits, row["n_vars"]).row_variables)
            self.assertLessEqual(stats.peak_polynomial_bytes, 1 << (row["n_vars"] - 3))

    def test_cache_and_budget_fallback_preserve_exact_partition(self):
        row = next(item for item in self.documents if item["label"] == 1)
        cache = ProductCache(64)
        first, first_stats = source_packed_partition(row["expression_v2"], row["n_vars"], cache=cache)
        second, second_stats = source_packed_partition(row["expression_v2"], row["n_vars"], cache=cache)
        self.assertEqual(first, second)
        self.assertGreater(second_stats.cache_hits, 0)
        self.assertGreater(second_stats.cache_saved_product_pairs, 0)
        fallback, method, stats = source_hybrid_partition(
            row["expression_v2"], row["n_vars"], cache=ProductCache(0), product_pair_budget=0
        )
        self.assertEqual(method, "truth_vector_anf_fallback")
        self.assertEqual(fallback, first)
        self.assertEqual(stats.fallback_reason, "product_pair_budget")

        without_retained_witness = copy.deepcopy(row)
        without_retained_witness["witness"] = None
        measured = _execute(
            "budgeted_hybrid", without_retained_witness, ProductCache(0), gate=0
        )
        self.assertEqual(measured["path"], "truth_vector_anf_fallback")
        self.assertTrue(measured["accepted"])


if __name__ == "__main__":
    unittest.main()
