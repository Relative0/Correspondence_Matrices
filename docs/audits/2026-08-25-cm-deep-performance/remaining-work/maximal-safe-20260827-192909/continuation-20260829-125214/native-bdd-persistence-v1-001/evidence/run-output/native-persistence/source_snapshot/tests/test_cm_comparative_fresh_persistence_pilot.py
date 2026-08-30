"""Fresh-process persistence pilot planning and real supervision smoke."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from cmbench.comparative import fresh_persistence as fresh
from cmbench.comparative import persistence
from cmbench.comparative.schedule import validate_plan
from scripts import cm_comparative_fresh_persistence_pilot as pilot
from scripts.cm_benchmark_provenance import capture_source_snapshot


class FreshPersistencePilotTests(unittest.TestCase):
    def test_plan_is_complete_balanced_and_refusal_preserving(self):
        plan, oracles = pilot.build_bundle()
        validate_plan(plan["schedule"])
        self.assertEqual(len(plan["scenarios"]), 8)
        blocks = 2 * len(plan["execution_arms"])
        self.assertEqual(len(plan["schedule"]["cells"]), 8 * len(plan["execution_arms"]) * blocks)
        self.assertEqual(set(plan["schedule"]["contracts"]), set(plan["execution_arms"]))
        self.assertEqual(set(plan["capabilities"]), set(fresh.ARMS))
        self.assertEqual({len(rows) for rows in oracles["cases"].values()}, {2})
        self.assertFalse(plan["performance_claim_permitted"])
        self.assertEqual(plan["capabilities"]["cudd_zdd"]["status"], "refused")
        self.assertEqual(plan["capabilities"]["d4_ddnnf"]["status"], "refused")
        self.assertEqual(set(plan["admissions"]), set(plan["refused_arms"]))
        self.assertTrue(all(row["status"] == "refused" for row in plan["admissions"].values()))

    def test_functional_profile_bounds_arms_cases_and_blocks(self):
        plan, oracles = pilot.build_bundle(
            arm_filter=("cm", "cse"), case_limit=2, blocks_override=4
        )
        validate_plan(plan["schedule"])
        self.assertEqual(plan["execution_arms"], ["cm", "cse"])
        self.assertEqual(len(plan["scenarios"]), 2)
        self.assertEqual(len(oracles["cases"]), 2)
        self.assertEqual(plan["schedule"]["blocks"], 4)
        self.assertEqual(len(plan["schedule"]["cells"]), 16)
        self.assertEqual(plan["functional_profile"], {
            "arm_filter": ["cm", "cse"], "case_limit": 2, "blocks": 4
        })
        self.assertEqual(set(plan["excluded_arms"]), set(fresh.ARMS) - {"cm", "cse"})

    def test_supervised_cell_uses_distinct_owned_processes(self):
        plan, oracles = pilot.build_bundle()
        arm = "autoref_bdd_control"
        if plan["capabilities"][arm]["status"] != "available":
            self.skipTest("dd.autoref unavailable")
        cell = next(item for item in plan["schedule"]["cells"] if item["arm"] == arm)
        with tempfile.TemporaryDirectory(dir=pilot.ROOT, prefix="fresh-persistence-cell-") as directory:
            output = Path(directory)
            (output / "artifacts").mkdir()
            capture_source_snapshot(pilot.ROOT, output / "source_snapshot", pilot.SOURCES)
            result, artifact = pilot.execute_cell(
                cell=cell,
                scenario=plan["scenarios"][cell["case_id"]],
                contract=plan["schedule"]["contracts"][arm],
                capability=plan["capabilities"][arm],
                output=output,
                frozen_script=output / "source_snapshot/scripts/cm_comparative_fresh_persistence_pilot.py",
            )
            fresh.validate_fresh_result(
                result,
                plan["schedule"]["contracts"][arm],
                scenario=plan["scenarios"][cell["case_id"]],
                expected_rows=oracles["cases"][cell["case_id"]],
                capability=plan["capabilities"][arm],
                artifact_path=artifact,
            )
            self.assertNotEqual(
                result["identity"]["build_worker"]["pid"],
                result["identity"]["reload_worker"]["pid"],
            )
            self.assertFalse(result["resources"]["memory_ranking_permitted"])
            self.assertEqual(
                result["identity"]["reload_worker"]["rows"],
                persistence.scalar_oracle(plan["scenarios"][cell["case_id"]]),
            )

    def test_new_output_gate_refuses_existing_path(self):
        with tempfile.TemporaryDirectory(dir=pilot.ROOT, prefix="fresh-persistence-safe-") as directory:
            target = Path(directory) / "new-output"
            self.assertEqual(pilot._safe_output(target), target.absolute())
            with self.assertRaises(ValueError):
                pilot._safe_output(target)


if __name__ == "__main__":
    unittest.main()
