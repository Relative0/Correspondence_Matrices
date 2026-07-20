import unittest
from types import SimpleNamespace

import numpy as np

from cm_exprlib import And, Var, eval_expr_tt
from cm_operator_difference import (
    CM_2X2,
    CM_2X2_TO_NAME,
    cm_2x2_name,
    cm_2x2_transform_correct,
    cm_complement,
    cm_contains,
    cm_feature_counts,
    cm_matrix_key,
    cm_quotient,
    cm_rotate180,
    cm_symmetric_delta,
    cm_transform_negate_both_operands,
    cm_transform_negate_expression,
    cm_transform_negate_left_operand,
    cm_transform_negate_right_operand,
    cm_transform_swap_operands,
)


class OperatorQuotientTests(unittest.TestCase):
    def test_2x2_table_is_unique_and_reverse_lookup_works(self) -> None:
        keys = [cm_matrix_key(m) for m in CM_2X2.values()]
        self.assertEqual(len(keys), 16)
        self.assertEqual(len(set(keys)), 16)
        for name, matrix in CM_2X2.items():
            self.assertEqual(CM_2X2_TO_NAME[cm_matrix_key(matrix)], name)
            self.assertEqual(cm_2x2_name(matrix), name)

    def test_paper_or_quotient_and_example(self) -> None:
        q = cm_quotient(CM_2X2["OR"], CM_2X2["AND"])
        self.assertTrue(np.array_equal(q, CM_2X2["XOR"]))
        self.assertEqual(cm_2x2_name(q), "XOR")

        reverse = cm_quotient(CM_2X2["AND"], CM_2X2["OR"])
        self.assertTrue(np.array_equal(reverse, CM_2X2["FALSE"]))
        self.assertTrue(cm_contains(CM_2X2["OR"], CM_2X2["AND"]))
        self.assertFalse(cm_contains(CM_2X2["AND"], CM_2X2["OR"]))

    def test_directionality_can_be_nonzero_both_ways(self) -> None:
        q_ab = cm_quotient(CM_2X2["OR"], CM_2X2["EQV"])
        q_ba = cm_quotient(CM_2X2["EQV"], CM_2X2["OR"])
        self.assertGreater(np.count_nonzero(q_ab), 0)
        self.assertGreater(np.count_nonzero(q_ba), 0)
        self.assertFalse(np.array_equal(q_ab, q_ba))

    def test_symmetric_delta_equals_union_of_directional_quotients(self) -> None:
        a = CM_2X2["NAND"]
        b = CM_2X2["IMP"]
        sym = cm_symmetric_delta(a, b)
        composed = np.logical_or(cm_quotient(a, b), cm_quotient(b, a))
        self.assertTrue(np.array_equal(sym, composed))

    def test_disjoint_pair_containment_and_counts(self) -> None:
        counts = cm_feature_counts(CM_2X2["AND"], CM_2X2["NOR"])
        self.assertEqual(counts["overlap_features"], 0)
        self.assertFalse(counts["a_contains_b"])
        self.assertFalse(counts["b_contains_a"])
        self.assertEqual(cm_2x2_name(cm_symmetric_delta(CM_2X2["AND"], CM_2X2["NOR"])), "EQV")

    def test_mismatched_shape_raises(self) -> None:
        with self.assertRaises(ValueError):
            cm_quotient(np.ones((2, 2), dtype=bool), np.ones((2, 4), dtype=bool))

    def test_equivalent_rewrite_semantic_vs_structural_labeling(self) -> None:
        import cm_bench

        expr_a = And(Var(0), Var(1))
        expr_b = And(Var(1), Var(0))
        self.assertTrue(np.array_equal(eval_expr_tt(expr_a, 2), eval_expr_tt(expr_b, 2)))
        struct = cm_bench.structural_hash_delta(expr_a, expr_b)
        self.assertEqual(struct["opdiff_cm_struct_status"], "prototype_feature_multiset_delta")
        self.assertGreaterEqual(struct["opdiff_cm_struct_shared_features"], 1)

    def test_all_2x2_transformations_have_valid_lookup_names(self) -> None:
        transforms = [
            cm_transform_swap_operands,
            cm_transform_negate_expression,
            cm_transform_negate_left_operand,
            cm_transform_negate_right_operand,
            cm_transform_negate_both_operands,
        ]
        for matrix in CM_2X2.values():
            for transform in transforms:
                self.assertNotEqual(cm_2x2_name(transform(matrix)), "UNKNOWN")

    def test_transpose_transformation_matches_swapped_operands(self) -> None:
        for matrix in CM_2X2.values():
            self.assertTrue(cm_2x2_transform_correct(matrix, cm_transform_swap_operands, "transpose"))
        self.assertEqual(cm_2x2_name(cm_transform_swap_operands(CM_2X2["IMP"])), "RIMP")
        self.assertEqual(cm_2x2_name(cm_transform_swap_operands(CM_2X2["OR"])), "OR")
        self.assertEqual(cm_2x2_name(cm_transform_swap_operands(CM_2X2["AND"])), "AND")

    def test_complement_transformation_matches_negated_output(self) -> None:
        for matrix in CM_2X2.values():
            self.assertTrue(cm_2x2_transform_correct(matrix, cm_transform_negate_expression, "complement"))
        self.assertTrue(np.array_equal(cm_transform_negate_expression(CM_2X2["AND"]), cm_complement(CM_2X2["AND"])))
        self.assertEqual(cm_2x2_name(cm_transform_negate_expression(CM_2X2["AND"])), "NAND")
        self.assertEqual(cm_2x2_name(cm_transform_negate_expression(CM_2X2["OR"])), "NOR")

    def test_negated_operand_transformations_match_truth_table_evaluation(self) -> None:
        for matrix in CM_2X2.values():
            self.assertTrue(
                cm_2x2_transform_correct(matrix, cm_transform_negate_left_operand, "negate_left_operand")
            )
            self.assertTrue(
                cm_2x2_transform_correct(matrix, cm_transform_negate_right_operand, "negate_right_operand")
            )
            self.assertTrue(
                cm_2x2_transform_correct(matrix, cm_transform_negate_both_operands, "negate_both_operands")
            )
        self.assertEqual(cm_2x2_name(cm_transform_negate_right_operand(CM_2X2["IMP"])), "NAND")
        self.assertTrue(np.array_equal(cm_transform_negate_both_operands(CM_2X2["OR"]), cm_rotate180(CM_2X2["OR"])))
        self.assertEqual(cm_2x2_name(cm_transform_negate_both_operands(CM_2X2["OR"])), "NAND")

    def test_cm_transform_benchmark_rows_validate_all_operators(self) -> None:
        import cm_bench

        rows = cm_bench.cm_transform_2x2_rows()
        self.assertEqual(len(rows), 16)
        for row in rows:
            for key, value in row.items():
                if key.endswith("_name"):
                    self.assertNotEqual(value, "UNKNOWN")
            self.assertTrue(row["transpose_correct"])
            self.assertTrue(row["complement_correct"])
            self.assertTrue(row["negate_left_correct"])
            self.assertTrue(row["negate_right_correct"])
            self.assertTrue(row["negate_both_correct"])

    def test_n16_dense_quotient_runs_or_reports_safe_skip(self) -> None:
        import cm_bench

        cm_bench.args = SimpleNamespace(
            operator_quotient_max_dense_n=15,
            cm_layout="balanced",
            cm_use_persistent_cache=False,
            cm_hybrid_threshold=7,
            operator_quotient_report_matrix=False,
        )
        skipped = cm_bench.dense_cm_quotient_delta(And(Var(0), Var(1)), Var(0), 16)
        self.assertEqual(skipped["dense_quotient_status"], "skipped_limit")

        cm_bench.args = SimpleNamespace(
            operator_quotient_max_dense_n=16,
            cm_layout="balanced",
            cm_use_persistent_cache=False,
            cm_hybrid_threshold=7,
            operator_quotient_report_matrix=False,
        )
        row = cm_bench.dense_cm_quotient_delta(And(Var(0), Var(1)), Var(0), 16)
        self.assertIn(row["dense_quotient_status"], {"ok", "error"})


if __name__ == "__main__":
    unittest.main()
