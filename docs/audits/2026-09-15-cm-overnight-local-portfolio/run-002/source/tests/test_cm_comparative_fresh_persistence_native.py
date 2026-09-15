"""Producer-independent checks for native persistence artifact dialects."""

from __future__ import annotations

import copy
import hashlib
import unittest

from cmbench.comparative import fresh_persistence as fresh
from cmbench.comparative import persistence
from cmbench.comparative.contracts import canonical_bytes


def scenario() -> dict:
    return {
        "id": "native-artifact-k2",
        "k": 2,
        "feature_names": ["x0", "x1"],
        "versions": [
            {"id": "x0-false", "clauses": [[-1]]},
            {"id": "x0-true-x1-false", "clauses": [[1], [-2]]},
        ],
        "source": {"kind": "synthetic", "purpose": "native_artifact_control"},
    }


def zdd_graph() -> dict:
    return {
        "schema": fresh.ZDD_SCHEMA,
        "k": 2,
        "level_of_var": {"x0": 0, "x1": 1},
        "roots": {"v000": 1, "v001": 2},
        "nodes": {
            "1": [1, "T", "T"],
            "2": [0, "F", "T"],
        },
    }


def ddnnf_bundle() -> dict:
    texts = [
        "o 1 0\nt 2 0\n1 2 -1 0\n",
        "o 1 0\nt 2 0\n1 2 1 -2 0\n",
    ]
    return {
        "schema": fresh.D4_SCHEMA,
        "k": 2,
        "variable_order": ["x0", "x1"],
        "versions": [
            {"id": row["id"], "nnf": text, "sha256": hashlib.sha256(text.encode("ascii")).hexdigest()}
            for row, text in zip(scenario()["versions"], texts)
        ],
    }


class NativePersistenceDialectTests(unittest.TestCase):
    def test_zdd_graph_replays_exact_without_native_module(self):
        self.assertEqual(
            fresh.independent_zdd_rows(canonical_bytes(zdd_graph()), scenario()),
            persistence.scalar_oracle(scenario()),
        )

    def test_zdd_graph_refuses_cycles_order_errors_and_unreachable_nodes(self):
        for changed in (
            {**zdd_graph(), "nodes": {"1": [1, 1, "T"], "2": [0, "F", "T"]}},
            {**zdd_graph(), "nodes": {"1": [0, 2, "T"], "2": [0, "F", "T"]}},
            {**zdd_graph(), "roots": {"v000": 1, "v001": 1}},
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    fresh.independent_zdd_rows(canonical_bytes(changed), scenario())

    def test_d4_arc_literal_bundle_replays_exact_without_d4(self):
        self.assertEqual(
            fresh.independent_ddnnf_rows(canonical_bytes(ddnnf_bundle()), scenario()),
            persistence.scalar_oracle(scenario()),
        )

    def test_d4_bundle_refuses_hash_tamper_cycle_and_nondeterminism(self):
        tampered = copy.deepcopy(ddnnf_bundle())
        tampered["versions"][0]["sha256"] = "0" * 64
        cyclic = copy.deepcopy(ddnnf_bundle())
        text = "o 1 0\n1 1 0\n"
        cyclic["versions"][0].update(nnf=text, sha256=hashlib.sha256(text.encode("ascii")).hexdigest())
        nondeterministic = copy.deepcopy(ddnnf_bundle())
        text = "o 1 0\nt 2 0\nt 3 0\n1 2 -1 0\n1 3 -1 0\n"
        nondeterministic["versions"][0].update(
            nnf=text, sha256=hashlib.sha256(text.encode("ascii")).hexdigest()
        )
        for changed in (tampered, cyclic, nondeterministic):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    fresh.independent_ddnnf_rows(canonical_bytes(changed), scenario())

    def test_native_capabilities_are_never_substituted(self):
        inventory = fresh.capability_inventory()
        for arm in fresh.OPTIONAL_NATIVE_ARMS:
            with self.subTest(arm=arm):
                self.assertFalse(inventory[arm]["portability_control"])
                self.assertEqual(inventory[arm]["native_execution"], inventory[arm]["status"] == "available")


if __name__ == "__main__":
    unittest.main()
