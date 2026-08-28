"""Small truth-table and corruption controls for the independent auditors."""

import copy
import tempfile
import unittest
from pathlib import Path

from artifact_audit import columns, replay_bdd, replay_flat, replay_nnf, scalar_cnf_vector
from source_audit import Formula, condition, joint_formula, opposing_named_units, parse_dimacs


class ArtifactAuditTests(unittest.TestCase):
    def test_columns_and_scalar_oracle(self):
        self.assertEqual(columns(3), (0b10101010, 0b11001100, 0b11110000))
        self.assertEqual(scalar_cnf_vector(((1,), (-1, 2)), 2), 0b1000)
        self.assertEqual(scalar_cnf_vector((), 2), 0b1111)
        self.assertEqual(scalar_cnf_vector(((),), 2), 0)
        self.assertEqual(scalar_cnf_vector(((1, -1, 1),), 2), 0b1111)

    def test_flat_replay_does_not_read_cached_answer(self):
        data = {"schema": "cm-flat-packed/v1", "k": 2, "n_slots": 4, "root_slot": 3,
                "loads": [[0, "var", "x0"], [1, "var", "x1"]],
                "ops": [[2, 0, [0]], [3, 1, [2, 1]]], "packed_hex": "not-valid-hex"}
        self.assertEqual(replay_flat(data), 0b0100)
        changed = copy.deepcopy(data)
        changed["ops"][1][1] = 2
        self.assertNotEqual(replay_flat(changed), replay_flat(data))

    def test_flat_rejects_bad_dependencies_and_opcodes(self):
        data = {"schema": "cm-flat-packed/v1", "k": 1, "n_slots": 2, "root_slot": 1,
                "loads": [[0, "var", "x0"]], "ops": [[1, 0, [9]]]}
        with self.assertRaises(AssertionError):
            replay_flat(data)
        data["ops"] = [[1, 19, [0]]]
        with self.assertRaises(ValueError):
            replay_flat(data)

    def test_flat_binary_and_nary_truth_tables(self):
        for opcode, expected in ((1, 0b1000), (2, 0b1110), (3, 0b0110), (4, 0b1101), (5, 0b1001)):
            data = {"schema": "cm-flat-packed/v1", "k": 2, "n_slots": 3, "root_slot": 2,
                    "loads": [[0, "var", "x0"], [1, "var", "x1"]], "ops": [[2, opcode, [0, 1]]]}
            self.assertEqual(replay_flat(data), expected)

    def test_bdd_complement_and_level_order(self):
        data = {"level_of_var": {"x1": 0, "x0": 1}, "roots": [-8], "8": [0, "F", 9], "9": [1, "F", "T"]}
        self.assertEqual(replay_bdd(data, 2), 0b0111)
        data["9"] = [0, "F", "T"]
        with self.assertRaises(AssertionError):
            replay_bdd(data, 2)

    def test_d4_documented_example_count(self):
        text = "o 1 0\no 2 0\no 3 0\nt 4 0\n3 4 -2 3 0\n3 4 2 0\n2 3 -1 0\n2 4 1 0\n1 2 0\n"
        value, metrics = replay_nnf(text, 3)
        self.assertEqual(value.bit_count(), 7)
        self.assertEqual(metrics["independent_count"], 7)
        self.assertEqual(metrics["serialized_nodes"], 4)
        self.assertEqual(metrics["serialized_edges"], 5)

    def test_nnf_and_skipped_universe_variables(self):
        text = "a 1 0\nt 2 0\n1 2 1 0\n1 2 -2 0\n"
        value, metrics = replay_nnf(text, 3)
        self.assertEqual(value, 0b00100010)
        self.assertEqual(metrics["independent_count"], 2)
        self.assertEqual(metrics["decomposable_and_nodes_checked"], 1)
        self.assertEqual(replay_nnf("t 1 0\n", 3)[0], 255)
        self.assertEqual(replay_nnf("f 1 0\n", 3)[0], 0)

    def test_nnf_rejects_nondeterminism_non_decomposability_and_corruption(self):
        invalid = [
            "o 1 0\nt 2 0\n1 2 1 0\n1 2 1 0\n",
            "a 1 0\nt 2 0\n1 2 1 0\n1 2 1 0\n",
            "o 1 0\n1 1 0\n",
            "o 1 0\n1 2 0\n",
            "o 1 1 0\nt 2 0\n1 2 0\n",
            "o 1 0\nt 2 0\n1 2 4 0\n",
        ]
        for text in invalid:
            with self.assertRaises((AssertionError, KeyError)):
                replay_nnf(text, 3)


class SourceAuditTests(unittest.TestCase):
    def test_parser_multiline_and_named_features(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.dimacs"
            path.write_text("c 1 alpha\nc 2 beta\np cnf 3 2\n1 -2\n3 0\n-3 0\n", encoding="utf-8")
            parsed = parse_dimacs(path)
            self.assertEqual(parsed.clauses, [(1, -2, 3), (-3,)])
            self.assertEqual(parsed.names, {1: "alpha", 2: "beta"})
            path.write_text("c 1 alpha\nc 2 alpha\np cnf 2 0\n", encoding="utf-8")
            with self.assertRaises(AssertionError):
                parse_dimacs(path)

    def test_joint_mapping_and_direct_refusal_certificate(self):
        left = Formula(3, [(1,), (3,)], {1: "root", 2: "left"})
        right = Formula(3, [(-2,), (-3,)], {1: "right", 2: "root"})
        clauses, mapping = joint_formula(left, right)
        self.assertEqual(mapping, [0, 4, 1, 5])
        self.assertEqual(clauses, [(1,), (3,), (-1,), (-5,)])
        certificate = opposing_named_units(left, right)
        self.assertEqual(len(certificate), 1)
        self.assertEqual(certificate[0]["feature_name"], "root")
        self.assertEqual(certificate[0]["earlier_clause_index_1based"], 1)
        self.assertEqual(certificate[0]["later_clause_index_1based"], 1)

    def test_conditioning_reorders_and_preserves_clauses(self):
        formula = Formula(3, [(1, 3), (-2, -3), (2, -1)], {1: "a", 2: "b", 3: "c"})
        product = {1: True, 2: True, 3: False}
        self.assertEqual(condition(formula, product, (2, 1)), ((2,), (1, -2)))


if __name__ == "__main__":
    unittest.main()
