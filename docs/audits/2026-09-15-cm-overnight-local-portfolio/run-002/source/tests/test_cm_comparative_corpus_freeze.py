"""Offline Phase 6 corpus-role, source-identity, and order-freeze tests."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.corpus_freeze import (
    FREEZE_SCHEMA,
    PRIMARY_METRICS,
    build_freeze,
    dimacs_metadata,
    evaluate_gate,
    validate_freeze,
    verify_sources,
)


class ComparativeCorpusFreezeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        members = [
            {"id": "reg-member", "expression_v2": {"version": 2, "nodes": [{"op": "var", "i": 0}], "root": 0}},
            {"id": "confirm-member", "expression_v2": {"version": 2, "nodes": [{"op": "var", "i": 1}], "root": 0}},
        ]
        self.members = members
        (self.root / "corpus.jsonl").write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in members) + "\n",
            encoding="utf-8",
        )
        (self.root / "development.blif").write_text(".model tiny\n.inputs a\n.outputs y\n.names a y\n1 1\n.end\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def member_sha(self, member):
        return hashlib.sha256(canonical_bytes(member)).hexdigest()

    def member_case(self, *, case_id, cluster_id, role, member):
        return {
            "case_id": case_id,
            "cluster_id": cluster_id,
            "role": role,
            "origin": "synthetic",
            "family": "tiny",
            "kind": "expression_jsonl_member",
            "tasks": ["complete_relation"],
            "source": {
                "path": "corpus.jsonl",
                "member_id": member["id"],
                "member_sha256": self.member_sha(member),
                "license": "project-test",
                "provenance": "unit-test fixture",
            },
            "strata": {"live_k": 1, "shape": "leaf"},
        }

    def draft(self):
        return {
            "schema": FREEZE_SCHEMA,
            "freeze_id": "p6-unit",
            "created_utc": "2026-08-30T00:00:00Z",
            "timing_results_inspected": False,
            "cases": [
                self.member_case(case_id="reg-1", cluster_id="reg-cluster", role="regression", member=self.members[0]),
                {
                    "case_id": "dev-1",
                    "cluster_id": "dev-cluster",
                    "role": "development",
                    "origin": "natural",
                    "family": "control",
                    "kind": "blif",
                    "tasks": ["complete_relation"],
                    "source": {
                        "path": "development.blif",
                        "member_id": None,
                        "member_sha256": None,
                        "license": "project-test",
                        "provenance": "unit-test fixture",
                    },
                    "strata": {"live_k": None, "shape": "circuit"},
                },
                self.member_case(
                    case_id="confirm-1", cluster_id="confirm-cluster", role="confirmation", member=self.members[1]
                ),
            ],
            "exclusions": [
                {
                    "exclusion_id": "malformed",
                    "scope": "all",
                    "predicate": "parser_status != accepted",
                    "reason": "the requested artifact cannot be defined",
                    "frozen_before_timing": True,
                }
            ],
            "schedule_policies": [
                {
                    "policy_id": "complete-relation",
                    "task": "complete_relation",
                    "eligible_roles": ["regression", "development", "confirmation"],
                    "arms": ["cm-a", "cm-b"],
                    "minimum_blocks": 8,
                    "maximum_blocks": 16,
                    "locality": "round_robin",
                    "seed": 31337,
                    "shard_cells": 32,
                    "noise_rule": {
                        "metric": "mad_over_median",
                        "threshold_ppm": 50_000,
                        "step_blocks": 4,
                        "independent_units_first": True,
                    },
                }
            ],
            "primary_metrics": list(PRIMARY_METRICS),
            "secondary_metrics": ["artifact_bytes", "task_stage_ns"],
            "confirmation": {
                "required": True,
                "selection_locked": True,
                "timing_results_inspected": False,
                "minimum_independent_clusters": 1,
            },
            "gate_requirements": {
                "minimum_independent_clusters": {"regression": 1, "development": 1, "confirmation": 1},
                "required_tasks": ["complete_relation"],
                "development_origins": ["natural"],
            },
            "provenance": {"plan": "unit-test", "native_readiness": "passed"},
        }

    def test_build_is_deterministic_and_ready_when_all_roles_exist(self):
        first = build_freeze(self.draft(), self.root)
        second = build_freeze(self.draft(), self.root)
        self.assertEqual(first, second)
        validate_freeze(first)
        source_check = verify_sources(first, self.root)
        self.assertTrue(source_check["verified"])
        gate = evaluate_gate(first, source_check)
        self.assertTrue(gate["ready_for_paid_measurement"])
        self.assertEqual(gate["independent_clusters"], {"regression": 1, "development": 1, "confirmation": 1})
        ledger = first["schedule_policies"][0]["order_ledger"]
        self.assertEqual(len(ledger), 3 * 16)
        self.assertTrue(all(len(row["arm_order"]) == 2 for row in ledger))
        self.assertEqual(sum(row["conditional_extension"] for row in ledger), 3 * 8)

    def test_source_mutation_is_detected_without_changing_freeze(self):
        freeze = build_freeze(self.draft(), self.root)
        original = freeze["freeze_sha256"]
        (self.root / "development.blif").write_text("changed\n", encoding="utf-8")
        check = verify_sources(freeze, self.root)
        self.assertFalse(check["verified"])
        self.assertEqual(freeze["freeze_sha256"], original)

    def test_member_hash_and_secret_path_fail_closed(self):
        draft = self.draft()
        draft["cases"][0]["source"]["member_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "member SHA-256"):
            build_freeze(draft, self.root)
        secret = self.draft()
        secret["cases"][0]["source"]["path"] = ".env"
        with self.assertRaisesRegex(ValueError, "secret-like"):
            build_freeze(secret, self.root)

    def test_clusters_cannot_cross_roles(self):
        freeze = build_freeze(self.draft(), self.root)
        freeze["cases"][2]["cluster_id"] = freeze["cases"][0]["cluster_id"]
        core = {key: value for key, value in freeze.items() if key != "freeze_sha256"}
        freeze["freeze_sha256"] = hashlib.sha256(canonical_bytes(core)).hexdigest()
        with self.assertRaisesRegex(ValueError, "cluster spans"):
            validate_freeze(freeze)

    def test_timing_inspection_and_order_tampering_fail_closed(self):
        freeze = build_freeze(self.draft(), self.root)
        for mutate, message in (
            (lambda row: row.__setitem__("timing_results_inspected", True), "precede timing"),
            (
                lambda row: row["schedule_policies"][0]["order_ledger"][0].__setitem__("arm_order", ["cm-a", "cm-a"]),
                "order ledger mismatch",
            ),
        ):
            changed = copy.deepcopy(freeze)
            mutate(changed)
            core = {key: value for key, value in changed.items() if key != "freeze_sha256"}
            changed["freeze_sha256"] = hashlib.sha256(canonical_bytes(core)).hexdigest()
            with self.assertRaisesRegex(ValueError, message):
                validate_freeze(changed)

    def test_unbalanced_blocks_are_rejected(self):
        draft = self.draft()
        draft["schedule_policies"][0]["minimum_blocks"] = 9
        with self.assertRaisesRegex(ValueError, "counterbalance cycles"):
            build_freeze(draft, self.root)

    def test_missing_confirmation_is_a_gate_failure_not_an_invalid_freeze(self):
        draft = self.draft()
        draft["cases"] = [row for row in draft["cases"] if row["role"] != "confirmation"]
        freeze = build_freeze(draft, self.root)
        gate = evaluate_gate(freeze, verify_sources(freeze, self.root))
        self.assertFalse(gate["ready_for_paid_measurement"])
        self.assertIn("confirmation_independent_clusters_below_minimum", gate["reasons"])
        self.assertIn("confirmation_policy_minimum_not_met", gate["reasons"])

    def test_dimacs_metadata_is_strict_and_does_not_solve(self):
        valid = self.root / "valid.cnf"
        valid.write_text("c max 2 0\np cnf 3 2\n1 -2 0\n3\n0\n", encoding="utf-8")
        self.assertEqual(dimacs_metadata(valid), {
            "variables": 3,
            "clauses": 2,
            "literal_occurrences": 3,
            "maximum_clause_width": 2,
            "empty_clauses": 0,
            "comment_directives": ["max"],
        })
        malformed = self.root / "malformed.cnf"
        malformed.write_text("p cnf 2 2\n1 0\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "clause count mismatch"):
            dimacs_metadata(malformed)

    def test_duplicate_json_keys_in_member_fail_closed(self):
        draft = self.draft()
        (self.root / "corpus.jsonl").write_text(
            '{"id":"reg-member","id":"reg-member"}\n'
            + json.dumps(self.members[1], sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            build_freeze(draft, self.root)


if __name__ == "__main__":
    unittest.main()
