"""Structural serialization/reload correctness and tamper controls."""

from __future__ import annotations

import copy
import unittest

from cmbench.comparative import persistence


def scenario() -> dict:
    return {
        "id": "persistence-k6",
        "k": 6,
        "feature_names": [f"x{i}" for i in range(6)],
        "versions": [
            {"id": "base", "clauses": [[1, -6], [-1, 6]]},
            {"id": "duplicate", "clauses": [[1, -6], [-1, 6], [1, -6]]},
            {"id": "changed", "clauses": [[1, -6], [-1, 6], [-1]]},
        ],
        "source": {"kind": "synthetic", "purpose": "persistence_control"},
    }


class PersistenceTests(unittest.TestCase):
    def run_backend(self, backend: str):
        expected = persistence.scalar_oracle(scenario())
        contract = persistence.persistence_contract(
            contract_id=f"reload-{backend}", backend=backend, k=6, queries=3
        )
        result = persistence.execute_persistence(
            scenario=scenario(), backend=backend, contract=contract, case_id="persistence-k6"
        )
        persistence.validate_persistence_result(
            result,
            contract,
            scenario=scenario(),
            expected_rows=expected,
            expected_backend=backend,
            expected_case_id="persistence-k6",
        )
        return contract, result

    def test_all_backends_reload_exact_complete_relations_without_answer_cache(self):
        outputs = []
        for backend in persistence.BACKENDS:
            with self.subTest(backend=backend):
                _contract, result = self.run_backend(backend)
                identity = result["identity"]
                self.assertFalse(identity["answer_cache_included"])
                self.assertFalse(identity["output_cache_used"])
                self.assertEqual(identity["counters"]["programs_built"], 0 if backend == "cnf" else 3)
                outputs.append(identity["reload_semantics"])
        self.assertTrue(all(output == outputs[0] for output in outputs[1:]))
        self.assertEqual(
            [row["satisfying_assignments"] for row in outputs[0]["rows"]], [32, 32, 16]
        )

    def test_bundle_round_trip_is_canonical_and_reconstructs_new_objects(self):
        for backend in persistence.BACKENDS:
            with self.subTest(backend=backend):
                bundle, _counts = persistence.build_bundle(scenario(), backend)
                payload = persistence.canonical_bytes(bundle)
                decoded = persistence.decode_bundle(payload, scenario=scenario(), expected_backend=backend)
                loaded = persistence.validate_bundle(decoded, scenario=scenario(), expected_backend=backend)
                self.assertEqual(len(loaded), 3)
                self.assertIsNot(decoded, bundle)
                with self.assertRaises(ValueError):
                    persistence.decode_bundle(
                        payload + b"\n", scenario=scenario(), expected_backend=backend
                    )

    def test_direct_cnf_refuses_literal_answer_and_cross_representation_mutations(self):
        bundle, counts = persistence.build_bundle(scenario(), "cnf")
        self.assertEqual(counts, persistence._counter_record())
        self.assertEqual(bundle["schema"], persistence.CNF_BUNDLE_SCHEMA)
        mutations = []
        changed = copy.deepcopy(bundle)
        changed["versions"][0]["clauses"][0][0] = 7
        mutations.append(changed)
        changed = copy.deepcopy(bundle)
        changed["versions"][0]["cached_answer"] = "0xff"
        mutations.append(changed)
        changed = copy.deepcopy(bundle)
        changed["schema"] = persistence.FLAT_BUNDLE_SCHEMA
        mutations.append(changed)
        for item in mutations:
            with self.subTest(item=item), self.assertRaises(ValueError):
                persistence.validate_bundle(item, scenario=scenario(), expected_backend="cnf")

    def test_bundle_refuses_answer_cache_identity_order_and_structure_mutations(self):
        bundle, _counts = persistence.build_bundle(scenario(), "cse")
        mutations = []
        changed = copy.deepcopy(bundle)
        changed["answer_cache_included"] = True
        mutations.append(changed)
        changed = copy.deepcopy(bundle)
        changed["scenario_sha256"] = "0" * 64
        mutations.append(changed)
        changed = copy.deepcopy(bundle)
        changed["versions"].reverse()
        mutations.append(changed)
        changed = copy.deepcopy(bundle)
        changed["versions"][0]["program"]["root_slot"] = 99999
        mutations.append(changed)
        changed = copy.deepcopy(bundle)
        changed["versions"][0]["program"]["cached_answer"] = "0xff"
        mutations.append(changed)
        for item in mutations:
            with self.subTest(item=item), self.assertRaises(ValueError):
                persistence.validate_bundle(item, scenario=scenario(), expected_backend="cse")

    def test_result_refuses_changed_semantics_artifact_and_claims(self):
        contract, result = self.run_backend("cm")
        expected = persistence.scalar_oracle(scenario())
        mutations = []
        changed = copy.deepcopy(result)
        changed["identity"]["reload_semantics"]["rows"][0]["relation_hex"] = "0x0"
        mutations.append(changed)
        changed = copy.deepcopy(result)
        changed["artifact"]["sha256"] = "0" * 64
        mutations.append(changed)
        changed = copy.deepcopy(result)
        changed["identity"]["performance_claim_permitted"] = True
        mutations.append(changed)
        changed = copy.deepcopy(result)
        changed["identity"]["serialized_bundle"]["answer_cache_included"] = True
        mutations.append(changed)
        for item in mutations:
            with self.subTest(item=item), self.assertRaises(ValueError):
                persistence.validate_persistence_result(
                    item,
                    contract,
                    scenario=scenario(),
                    expected_rows=expected,
                    expected_backend="cm",
                    expected_case_id="persistence-k6",
                )

    def test_contract_refuses_cross_backend_or_wrong_lifecycle(self):
        contract = persistence.persistence_contract(
            contract_id="reload-cm", backend="cm", k=6, queries=3
        )
        changed = copy.deepcopy(contract)
        changed["lifecycle"] = "resident_engine"
        with self.assertRaises(ValueError):
            persistence.execute_persistence(
                scenario=scenario(), backend="cm", contract=changed, case_id="persistence-k6"
            )
        with self.assertRaises(ValueError):
            persistence.execute_persistence(
                scenario=scenario(), backend="sat", contract=contract, case_id="persistence-k6"
            )


if __name__ == "__main__":
    unittest.main()
