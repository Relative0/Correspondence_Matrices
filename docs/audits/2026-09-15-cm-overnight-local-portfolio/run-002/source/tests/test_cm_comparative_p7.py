from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cm_exprlib import And, Not, Or, Var
from cmbench.comparative.p7 import IR_ARMS, execute_ir_functional
from cmbench.recognition.blif import parse_blif


class ComparativeP7Tests(unittest.TestCase):
    def test_ir_controls_are_exact_and_memo_controls_have_identical_ir(self) -> None:
        shared = Or(Var(0), Not(Var(1)))
        expression = And(shared, shared)
        rows = [execute_ir_functional(expression, ("x0", "x1"), arm) for arm in IR_ARMS]

        self.assertEqual(len({row["semantic_sha256"] for row in rows}), 1)
        self.assertEqual(rows[0]["artifact_sha256"], rows[1]["artifact_sha256"])
        self.assertTrue(all(row["performance_measurement"] is False for row in rows))

    def test_bounded_output_metadata_detects_frozen_root_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cm-p7-") as temporary:
            path = Path(temporary) / "fixture.blif"
            path.write_text(""".model fixture
.inputs a b c d
.outputs y z
.names a b c d y
1111 1
.names a z
1 1
.end
""", encoding="utf-8")
            netlist = parse_blif(path)
            selected = netlist.bounded_metadata(
                "y", min_support=4, max_support=16, max_source_nodes=4096)
            self.assertIsNotNone(selected)
            self.assertIsNone(netlist.bounded_metadata(
                "z", min_support=4, max_support=16, max_source_nodes=4096))


if __name__ == "__main__":
    unittest.main()
