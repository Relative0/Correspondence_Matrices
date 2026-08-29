"""Cached-real persistence pilot planning and verifier controls."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from cmbench.comparative.schedule import validate_plan
from scripts import cm_comparative_persistence_pilot as pilot


class PersistencePilotTests(unittest.TestCase):
    def test_plan_is_balanced_real_cohort_and_trace_gap_is_explicit(self):
        plan, oracles, trace_document = pilot.build_bundle()
        validate_plan(plan["schedule"])
        self.assertEqual(len(plan["scenarios"]), 8)
        self.assertEqual(len(plan["schedule"]["cells"]), 144)
        self.assertEqual(set(plan["schedule"]["contracts"]), {"cm", "cse", "cnf"})
        self.assertEqual(len(oracles["cases"]), 8)
        self.assertEqual({len(rows) for rows in oracles["cases"].values()}, {2})
        audit = trace_document["audit"]
        self.assertEqual(audit["trace_count"], 48)
        self.assertEqual(audit["natural_trace_count"], 0)
        self.assertFalse(audit["natural_claim_permitted"])

    def test_new_output_only_and_existing_output_refuse(self):
        with tempfile.TemporaryDirectory(dir=pilot.ROOT, prefix="persistence-safe-") as temporary:
            parent = Path(temporary)
            target = parent / "new-output"
            self.assertEqual(pilot._safe_output(target), target.absolute())
            with self.assertRaises(ValueError):
                pilot._safe_output(target)

    def test_verifier_detects_mutated_summary_without_rewriting_evidence(self):
        with tempfile.TemporaryDirectory(dir=pilot.ROOT, prefix="persistence-pilot-") as temporary:
            output = Path(temporary) / "evidence"
            pilot.run(output)
            before = {path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()}
            self.assertEqual(pilot.verify(output)["status"], "passed")
            after = {path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            changed = copy.deepcopy(summary)
            changed["performance_claim_permitted"] = True
            (output / "summary.json").write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(ValueError):
                pilot.verify(output)


if __name__ == "__main__":
    unittest.main()
