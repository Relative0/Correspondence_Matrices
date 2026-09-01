from __future__ import annotations

import copy
import hashlib
import unittest

from cmbench.comparative.contracts import canonical_bytes
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.yosys_unused_gf2_data import (
    SOURCE_GENERATORS,
    admitted_rows,
    candidates,
    dataset_document,
    scalar_bits,
    validate_dataset,
)


class YosysUnusedGf2DataTests(unittest.TestCase):
    def test_scalar_oracles_match_expression_lowerings(self) -> None:
        checked = 0
        for candidate in candidates():
            n_vars = len(candidate.variable_specs)
            if 3 <= n_vars <= 10:
                self.assertEqual(reference_bits(candidate.expression, n_vars), scalar_bits(candidate))
                checked += 1
        self.assertGreaterEqual(checked, 250)

    def test_fresh_selection_is_bounded_and_family_diverse(self) -> None:
        rows, rejected = admitted_rows(set())
        document = dataset_document(rows, rejected, "inventory.json", "0" * 64, 48)
        validate_dataset(document)
        self.assertEqual(len(document["cases"]), 48)
        self.assertGreaterEqual(document["counts"]["families"], 7)
        self.assertTrue({row["source_generator"] for row in document["cases"]}
                        <= set(SOURCE_GENERATORS))
        self.assertTrue(all(row["fresh_confirmation"] for row in document["cases"]))

    def test_dataset_tampering_is_rejected(self) -> None:
        rows, rejected = admitted_rows(set())
        document = dataset_document(rows, rejected, "inventory.json", "0" * 64, 32)
        tampered = copy.deepcopy(document)
        tampered["cases"][0]["expression_v2_sha256"] = hashlib.sha256(
            canonical_bytes({"tampered": True})
        ).hexdigest()
        with self.assertRaises(ValueError):
            validate_dataset(tampered)


if __name__ == "__main__":
    unittest.main()
