from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bitset_backend import build_bitset_env, eval_expr_bitset
from cmbench.recognition.blif import parse_blif


class BlifRecognitionTests(unittest.TestCase):
    def _write(self, text: str) -> Path:
        temporary = tempfile.TemporaryDirectory(prefix="crse-blif-")
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        path = directory / "fixture.blif"
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def test_xor_parser_expression_and_independent_oracle_agree(self) -> None:
        path = self._write("""# bounded fixture
.model xor_fixture
.inputs a \\
 b
.outputs y
.names a b y
01 1
10 1
.end
""")
        netlist = parse_blif(path)
        metadata = netlist.metadata("y")
        expression, support = netlist.build_expr("y")
        packed, oracle_support = netlist.packed_value("y")

        self.assertEqual(netlist.model, "xor_fixture")
        self.assertEqual(metadata.support, ("a", "b"))
        self.assertEqual(metadata.source_nodes, 1)
        self.assertEqual(netlist.candidate_metadata(min_support=1, max_support=2,
                                                    max_source_nodes=2), [metadata])
        self.assertEqual(netlist.bounded_metadata("y", min_support=1, max_support=2,
                                                  max_source_nodes=2), metadata)
        self.assertEqual(support, oracle_support)
        self.assertEqual(eval_expr_bitset(expression, build_bitset_env(("x0", "x1"))), packed)
        self.assertEqual(packed, 0b0110)

    def test_nested_luts_constants_and_dont_cares(self) -> None:
        path = self._write(""".model nested
.inputs a b c
.outputs y
.names zero
0
.names one
1
.names a b n
1- 1
.names n c one y
1-1 1
.end
""")
        netlist = parse_blif(path)
        expression, support = netlist.build_expr("y")
        packed, oracle_support = netlist.packed_value("y")

        self.assertEqual(support, oracle_support)
        self.assertEqual(support, ("a",))
        self.assertEqual(eval_expr_bitset(expression, build_bitset_env(("x0",))), packed)
        self.assertEqual(packed, 0b10)

    def test_off_set_table_uses_complement_default(self) -> None:
        path = self._write(""".model off_set
.inputs a b
.outputs y
.names a b y
00 0
11 0
.end
""")
        netlist = parse_blif(path)
        expression, support = netlist.build_expr("y")
        packed, oracle_support = netlist.packed_value("y")

        self.assertEqual(support, oracle_support)
        self.assertEqual(eval_expr_bitset(expression, build_bitset_env(("x0", "x1"))), packed)
        self.assertEqual(packed, 0b0110)

    def test_mixed_polarity_rows_are_refused(self) -> None:
        path = self._write(""".model invalid
.inputs a b
.outputs y
.names a b y
00 0
11 1
.end
""")
        with self.assertRaisesRegex(ValueError, "mixed-polarity"):
            parse_blif(path)

    def test_cycle_is_refused_before_cone_use(self) -> None:
        path = self._write(""".model cycle
.inputs a
.outputs y
.names z y
1 1
.names y z
1 1
.end
""")
        netlist = parse_blif(path)
        with self.assertRaisesRegex(ValueError, "cyclic"):
            netlist.metadata("y")
        with self.assertRaisesRegex(ValueError, "cyclic"):
            netlist.candidate_metadata(min_support=1, max_support=2, max_source_nodes=2)
        with self.assertRaisesRegex(ValueError, "cyclic"):
            netlist.bounded_metadata("y", min_support=1, max_support=2,
                                     max_source_nodes=2)

    def test_bounded_metadata_refuses_before_full_cone_materialization(self) -> None:
        path = self._write(""".model bounded
.inputs a b c
.outputs y
.names a b n
11 1
.names n c y
11 1
.end
""")
        netlist = parse_blif(path)

        self.assertIsNone(netlist.bounded_metadata(
            "y", min_support=1, max_support=2, max_source_nodes=2))
        self.assertIsNone(netlist.bounded_metadata(
            "y", min_support=1, max_support=3, max_source_nodes=1))
        self.assertIsNone(netlist.bounded_metadata(
            "a", min_support=1, max_support=3, max_source_nodes=2))


if __name__ == "__main__":
    unittest.main()
