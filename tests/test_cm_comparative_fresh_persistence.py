"""Fresh-process persistence adapters, controls and refusal gates."""

from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from cmbench.comparative import fresh_persistence as fresh
from cmbench.comparative import persistence


def scenario() -> dict:
    return {
        "id": "fresh-persistence-k6",
        "k": 6,
        "feature_names": [f"x{i}" for i in range(6)],
        "versions": [
            {"id": "base", "clauses": [[1, -6], [-1, 6]]},
            {"id": "changed", "clauses": [[1, -6], [-1, 6], [-1]]},
        ],
        "source": {"kind": "synthetic", "purpose": "fresh_persistence_control"},
    }


class FreshPersistenceTests(unittest.TestCase):
    def test_inventory_never_substitutes_autoref_for_native_arms(self):
        inventory = fresh.capability_inventory()
        self.assertEqual(tuple(inventory), fresh.ARMS)
        self.assertTrue(inventory["autoref_bdd_control"]["portability_control"])
        self.assertFalse(inventory["autoref_bdd_control"]["native_execution"])
        self.assertEqual(inventory["cudd_zdd"]["status"], "refused")
        self.assertEqual(inventory["d4_ddnnf"]["status"], "refused")
        if inventory["cudd_bdd"]["status"] == "available":
            self.assertTrue(inventory["cudd_bdd"]["native_execution"])
            self.assertTrue(inventory["cudd_bdd"]["identity"]["native_extension"])
        else:
            self.assertFalse(inventory["cudd_bdd"]["native_execution"])

    def test_executable_local_arms_build_reload_and_independently_replay_exact(self):
        inventory = fresh.capability_inventory()
        expected = persistence.scalar_oracle(scenario())
        with tempfile.TemporaryDirectory(prefix="cm-fresh-persistence-") as directory:
            root = Path(directory)
            for arm in fresh.STANDARD_ARMS + fresh.BDD_ARMS:
                if inventory[arm]["status"] != "available":
                    continue
                with self.subTest(arm=arm):
                    artifact = (root / f"cell-{arm}.json").resolve()
                    build = fresh.build_artifact(scenario(), arm, artifact)
                    reload = fresh.query_artifact(
                        scenario(), arm, artifact, build["artifact"]["sha256"]
                    )
                    self.assertEqual(reload["rows"], expected)
                    self.assertEqual(
                        fresh.validate_artifact_semantics(
                            artifact,
                            arm=arm,
                            scenario=scenario(),
                            expected_sha256=build["artifact"]["sha256"],
                        ),
                        expected,
                    )
                    self.assertFalse(build["artifact"]["answer_cache_included"])
                    self.assertEqual(build["identity"]["native_execution"], arm == "cudd_bdd")
                    self.assertEqual(
                        build["identity"]["portability_control"], arm == "autoref_bdd_control"
                    )

    def test_bdd_artifact_tamper_and_invalid_graph_are_refused(self):
        if fresh.capability_inventory()["autoref_bdd_control"]["status"] != "available":
            self.skipTest("dd.autoref unavailable")
        with tempfile.TemporaryDirectory(prefix="cm-fresh-bdd-") as directory:
            artifact = (Path(directory) / "cell-autoref.json").resolve()
            build = fresh.build_artifact(scenario(), "autoref_bdd_control", artifact)
            payload = artifact.read_bytes()
            with self.assertRaises(ValueError):
                fresh.query_artifact(scenario(), "autoref_bdd_control", artifact, "0" * 64)
            changed = payload.replace(b'"x0": 0', b'"x0": 1', 1)
            self.assertNotEqual(changed, payload)
            with self.assertRaises(ValueError):
                fresh.independent_bdd_rows(changed, scenario())
            self.assertEqual(build["identity"]["adapter"], "dd_json_dump/v1")

    def test_contract_and_refusal_are_machine_checked(self):
        contract = fresh.fresh_contract(
            contract_id="fresh-d4", arm="d4_ddnnf", k=6, queries=2
        )
        capability = fresh.capability_inventory()["d4_ddnnf"]
        result = fresh.refused_result(
            arm="d4_ddnnf", case_id="case-00", contract=contract, capability=capability
        )
        fresh.validate_fresh_result(
            result,
            contract,
            scenario=scenario(),
            expected_rows=persistence.scalar_oracle(scenario()),
            capability=capability,
            artifact_path=None,
        )
        changed = copy.deepcopy(result)
        changed["identity"]["substitution_used"] = True
        with self.assertRaises(ValueError):
            fresh.validate_fresh_result(
                changed,
                contract,
                scenario=scenario(),
                expected_rows=persistence.scalar_oracle(scenario()),
                capability=capability,
                artifact_path=None,
            )

    def test_worker_request_refuses_extra_fields_and_refused_arms(self):
        with tempfile.TemporaryDirectory(prefix="cm-fresh-request-") as directory:
            request = {
                "schema": fresh.REQUEST_SCHEMA,
                "mode": "build",
                "arm": "cm",
                "scenario": scenario(),
                "artifact_path": str((Path(directory) / "cell-request.json").resolve()),
            }
            payload = fresh.canonical_bytes(request)
            self.assertEqual(fresh.worker_request(payload)["arm"], "cm")
            changed = dict(request, cached_answer="0xff")
            with self.assertRaises(ValueError):
                fresh.worker_request(fresh.canonical_bytes(changed))
            changed = dict(request, arm="cudd_zdd")
            with self.assertRaises(ValueError):
                fresh.worker_request(fresh.canonical_bytes(changed))


if __name__ == "__main__":
    unittest.main()
