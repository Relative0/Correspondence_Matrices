import json
import random
import tempfile
import unittest
from pathlib import Path

from cm_exprlib import And, Or, Var, Xor
from cmbench.recognition.gf2_decomposition import (
    ExactGF2Artifact, analyze_exact_gf2, analyze_screened_exact_gf2,
    cofactor_artifacts, gf2_rank_factor, kronecker_artifacts, rank_artifact,
    screen_partition, truth_sha256, xor_component_artifact,
)
from cmbench.recognition.natural_decomposition import partitioned_bits
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.gf2_decomposition_experiment import make_gf2_controls


def permute_bits(bits, n_vars, order):
    result = 0
    for target in range(1 << n_vars):
        source = 0
        for target_variable, source_variable in enumerate(order):
            value = (target >> (n_vars - 1 - target_variable)) & 1
            source |= value << (n_vars - 1 - source_variable)
        result |= ((bits >> source) & 1) << target
    return result


def negate_inputs_bits(bits, n_vars, variables):
    flip = sum(1 << (n_vars - 1 - variable) for variable in variables)
    return sum(((bits >> (assignment ^ flip)) & 1) << assignment
               for assignment in range(1 << n_vars))


def from_matrix(arranged, n_vars, row_variables):
    row = tuple(row_variables)
    column = tuple(value for value in range(n_vars) if value not in row)
    rows, columns = 1 << len(row), 1 << len(column)
    bits = 0
    for r in range(rows):
        for c in range(columns):
            assignment = 0
            for local, variable in enumerate(row):
                assignment |= ((r >> (len(row) - 1 - local)) & 1) << (n_vars - 1 - variable)
            for local, variable in enumerate(column):
                assignment |= ((c >> (len(column) - 1 - local)) & 1) << (n_vars - 1 - variable)
            bits |= ((arranged >> (r * columns + c)) & 1) << assignment
    return bits


class ExactGF2DecompositionTests(unittest.TestCase):
    def test_rank_factor_exact(self):
        rows = (0b10101, 0b00111, 0b10010, 0b00000, 0b10101)
        rank, coefficients, basis = gf2_rank_factor(rows, 5)
        self.assertEqual(rank, 2)
        for row, coefficient in zip(rows, coefficients):
            value = 0
            for index, basis_row in enumerate(basis):
                if coefficient & (1 << index):
                    value ^= basis_row
            self.assertEqual(value, row)

    def test_recursive_disjoint_xor_artifact_and_permutation(self):
        expression = Xor(And(Var(0), Var(1)), Or(Var(2), Var(3)))
        bits = reference_bits(expression, 4)
        artifact = xor_component_artifact(bits, 4)
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact.reconstruct(), bits)
        permuted = permute_bits(bits, 4, (2, 0, 3, 1))
        replay = xor_component_artifact(permuted, 4)
        self.assertIsNotNone(replay)
        self.assertEqual(replay.reconstruct(), permuted)

    def test_rank_one_tensor_input_output_negation_and_transpose_orientation(self):
        # U=[1,0,1,1], V=[1,1,0,1], M=U outer V over GF(2).
        u, v, arranged = 0b1101, 0b1011, 0
        for row in range(4):
            for column in range(4):
                arranged |= (((u >> row) & 1) & ((v >> column) & 1)) << (row * 4 + column)
        bits = from_matrix(arranged, 4, (0, 1))
        rank = rank_artifact(bits, 4, (0, 1))
        self.assertIsNotNone(rank)
        self.assertEqual(rank.document["payload"]["rank"], 1)
        self.assertEqual(rank.reconstruct(), bits)
        transposed = from_matrix(sum(((arranged >> (r * 4 + c)) & 1) << (c * 4 + r)
                                     for r in range(4) for c in range(4)), 4, (0, 1))
        transpose_rank = rank_artifact(transposed, 4, (0, 1))
        self.assertIsNotNone(transpose_rank)
        self.assertEqual(transpose_rank.reconstruct(), transposed)
        negated = bits ^ ((1 << 16) - 1)
        analysis = analyze_exact_gf2(negated, 4, row_partitions=((0, 1),))
        self.assertTrue(all(candidate.reconstruct() == negated for candidate in analysis.candidates))
        input_negated = negate_inputs_bits(bits, 4, (0, 3))
        input_analysis = analyze_exact_gf2(input_negated, 4, row_partitions=((0, 1),))
        self.assertTrue(input_analysis.candidates)
        self.assertTrue(all(candidate.reconstruct() == input_negated
                            for candidate in input_analysis.candidates))

    def test_complement_cofactor_blocks_and_kronecker(self):
        rows = (0b00110101, 0b11001010, 0b01010110, 0b10101001,
                0b00110101, 0b11001010, 0b01010110, 0b10101001)
        arranged = sum(row << (index * 8) for index, row in enumerate(rows))
        bits = from_matrix(arranged, 6, (0, 1, 2))
        cofactors = cofactor_artifacts(bits, 6, (0, 1, 2))
        self.assertTrue(cofactors)
        self.assertTrue(all(item.reconstruct() == bits for item in cofactors))

        left, right = 0b1001, 0b1110
        kron = 0
        for lr in range(2):
            for lc in range(2):
                for rr in range(2):
                    for rc in range(2):
                        value = ((left >> (lr * 2 + lc)) & 1) & ((right >> (rr * 2 + rc)) & 1)
                        kron |= value << ((lr * 2 + rr) * 4 + lc * 2 + rc)
        kron_bits = from_matrix(kron, 4, (0, 1))
        artifacts = kronecker_artifacts(kron_bits, 4, (0, 1))
        self.assertTrue(artifacts)
        self.assertTrue(all(item.reconstruct() == kron_bits for item in artifacts))

    def test_dense_incompressible_negative_and_strict_artifact_reload(self):
        rng = random.Random(20260830)
        dense = None
        for _ in range(64):
            candidate = rng.getrandbits(256)
            analysis = analyze_exact_gf2(candidate, 8, max_partitions=32)
            if not analysis.candidates:
                dense = candidate
                break
        self.assertIsNotNone(dense)
        expression = Xor(And(Var(0), Var(1)), And(Var(2), Var(3)))
        artifact = xor_component_artifact(reference_bits(expression, 4), 4)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.json"
            artifact.save(path)
            loaded = ExactGF2Artifact.load(path)
            self.assertEqual(loaded.reconstruct(), artifact.reconstruct())
            changed = json.loads(path.read_text(encoding="utf-8"))
            changed["source_sha256"] = truth_sha256(0, 4)
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(ValueError):
                ExactGF2Artifact.load(path)

    def test_frozen_structured_and_dense_controls(self):
        controls = make_gf2_controls(20260830)
        self.assertEqual(len(controls), 12)
        for control in controls:
            analysis = analyze_exact_gf2(control["bits"], control["n_vars"],
                row_partitions=control["row_partitions"] if control["row_partitions"] else None,
                max_partitions=32)
            if control["required_kind"] is None:
                self.assertFalse(analysis.candidates)
            else:
                self.assertIn(control["required_kind"], analysis.kinds)

    def test_screened_tail_matches_exhaustive_best(self):
        controls = make_gf2_controls(20260830)
        for control in controls:
            kwargs = ({"row_partitions": control["row_partitions"]}
                      if control["row_partitions"] else {"max_partitions": 32})
            exhaustive = analyze_exact_gf2(control["bits"], control["n_vars"], **kwargs)
            screened = analyze_screened_exact_gf2(
                control["bits"], control["n_vars"], materialize_budget=4, **kwargs
            )
            self.assertEqual(
                screened.best.to_dict() if screened.best else None,
                exhaustive.best.to_dict() if exhaustive.best else None,
            )
            self.assertTrue(all(candidate.reconstruct() == control["bits"]
                                for candidate in screened.candidates))
            self.assertLessEqual(screened.artifacts_materialized, 5)  # XOR plus four descriptors.

    def test_partition_screen_is_not_an_accepted_artifact(self):
        bits = reference_bits(Xor(And(Var(0), Var(1)), Or(Var(2), Var(3))), 4)
        descriptors = screen_partition(bits, 4, (0, 1))
        self.assertTrue(descriptors)
        self.assertFalse(any(isinstance(item, ExactGF2Artifact) for item in descriptors))
        self.assertTrue(all(item.materialize(bits, 4).reconstruct() == bits
                            for item in descriptors))
        with self.assertRaises(ValueError):
            analyze_screened_exact_gf2(bits, 4, materialize_budget=0)


if __name__ == "__main__":
    unittest.main()
