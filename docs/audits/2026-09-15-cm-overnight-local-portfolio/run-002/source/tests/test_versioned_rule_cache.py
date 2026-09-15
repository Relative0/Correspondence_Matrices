from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Not, Or, Var, Xor
from cmbench.recognition.proved_rules import aig_xor_expr, canonical
from cmbench.recognition.rule_pack import (
    FACTOR_RULE_ID, OR_RULE_ID, RULE_PRIORITY_V2, XOR_RULE_ID, CompiledRulePack,
    ProvedRulePack, StructuralConeCache, aig_or_expr, compile_rule_pack,
    factored_or_expr, prove_rule_pack, prove_rule_pack_v2,
)
from cmbench.recognition.teacher import teach
from cmbench.recognition.versioned_rule_experiment import (
    VersionedRuleConfig, make_versions, run_versioned_rule_experiment,
)


class ProvedRulePackTests(unittest.TestCase):
    def test_pack_proof_roundtrip_and_tamper_rejection(self):
        pack = prove_rule_pack()
        self.assertEqual(pack.document["priority"], [XOR_RULE_ID, OR_RULE_ID])
        self.assertEqual(sum(len(rule["proof_rows"]) for rule in pack.document["rules"]), 8)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "pack.json"
            pack.save(path)
            self.assertEqual(ProvedRulePack.load(path).to_dict(), pack.to_dict())
        document = pack.to_dict()
        document["rules"][1]["proof_rows"][3]["rhs"] = True
        rule = document["rules"][1]
        rule["proof_rows_sha256"] = hashlib.sha256(canonical(rule["proof_rows"])).hexdigest()
        payload = {key: value for key, value in document.items() if key != "payload_sha256"}
        document["payload_sha256"] = hashlib.sha256(canonical(payload)).hexdigest()
        with self.assertRaises(ValueError):
            ProvedRulePack.from_dict(document)

    def test_v2_pack_proves_and_applies_nonoverlapping_factor_rule(self):
        pack = prove_rule_pack_v2()
        self.assertEqual(pack.document["priority"], list(RULE_PRIORITY_V2))
        self.assertEqual(sum(len(rule["proof_rows"]) for rule in pack.document["rules"]), 16)
        matcher = compile_rule_pack(pack)
        a = Or(Var(0), Var(1))
        source = factored_or_expr(a, Var(2), Var(3))
        rewrite = matcher.rewrite(source, 8)
        self.assertEqual(rewrite.applications_by_rule[FACTOR_RULE_ID], 1)
        self.assertEqual(rewrite.conflicts, 0)
        self.assertEqual(teach(source, 8).bits, teach(rewrite.result, 8).bits)

    def test_v2_factor_match_handles_commuted_products(self):
        matcher = compile_rule_pack(prove_rule_pack_v2())
        shared = And(Var(0), Var(1))
        source = Or(And(Var(2), shared), And(Var(3), shared))
        rewrite = matcher.rewrite(source, 8)
        self.assertEqual(rewrite.applications_by_rule[FACTOR_RULE_ID], 1)
        self.assertEqual(teach(source, 8).bits, teach(rewrite.result, 8).bits)

    def test_priority_selects_xor_and_pack_preserves_sharing(self):
        matcher = compile_rule_pack(prove_rule_pack())
        a = And(Var(0), Var(1))
        b = Or(Var(2), Not(Var(3)))
        xor_site = aig_xor_expr(a, b)
        or_site = aig_or_expr(Var(4), Var(5))
        shared = And(xor_site, or_site)
        source = Or(shared, shared)
        rewrite = matcher.rewrite(source, 8)
        self.assertEqual(rewrite.applications_by_rule, {XOR_RULE_ID: 1, OR_RULE_ID: 1})
        self.assertEqual(rewrite.conflicts, 1)
        self.assertIs(rewrite.result.a, rewrite.result.b)
        self.assertIsInstance(rewrite.result.a.a, Xor)
        self.assertIsInstance(rewrite.result.a.b, Or)
        self.assertEqual(teach(source, 8).bits, teach(rewrite.result, 8).bits)


class StructuralConeCacheTests(unittest.TestCase):
    def test_clone_hits_and_source_or_pack_change_invalidates(self):
        matcher = compile_rule_pack(prove_rule_pack())
        source = aig_or_expr(And(Var(0), Var(1)), Var(2))
        clone = expr_from_json(expr_to_json_dag(source))
        cache = StructuralConeCache(max_entries=2)
        cold = cache.rewrite("cone-a", source, matcher)
        hit = cache.rewrite("cone-a", clone, matcher)
        changed = cache.rewrite("cone-a", aig_or_expr(Var(0), Var(3)), matcher)
        pack_changed = cache.rewrite("cone-a", aig_or_expr(Var(0), Var(3)),
                                     CompiledRulePack("0" * 64))
        self.assertEqual((cold.reason, hit.reason, changed.reason, pack_changed.reason),
                         ("cold_miss", "unchanged_structural_identity",
                          "source_changed", "pack_changed"))
        self.assertFalse(cold.cache_hit)
        self.assertTrue(hit.cache_hit)
        self.assertTrue(changed.invalidated)
        self.assertTrue(pack_changed.invalidated)
        self.assertEqual(cache.invalidate_missing(set()), 1)
        self.assertEqual(cache.size, 0)

    def test_digest_collision_still_compares_exact_canonical_source(self):
        matcher = compile_rule_pack(prove_rule_pack_v2())
        collision = lambda _value: "0" * 64
        cache = StructuralConeCache(max_entries=2, identity_hasher=collision)
        first = cache.rewrite("cone-a", aig_or_expr(Var(0), Var(1)), matcher)
        second = cache.rewrite("cone-a", aig_or_expr(Var(0), Var(2)), matcher)
        self.assertFalse(first.cache_hit)
        self.assertFalse(second.cache_hit)
        self.assertTrue(second.invalidated)
        self.assertEqual(second.reason, "source_changed")

    def test_cache_serialization_reproduces_before_accepting_hits(self):
        matcher = compile_rule_pack(prove_rule_pack_v2())
        source = factored_or_expr(Var(0), Var(1), Var(2))
        cache = StructuralConeCache(max_entries=2)
        cache.rewrite("cone-a", source, matcher)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cache.json"
            cache.save(path)
            restored = StructuralConeCache.load(path, matcher)
            hit = restored.rewrite("cone-a", expr_from_json(expr_to_json_dag(source)), matcher)
        self.assertTrue(hit.cache_hit)
        self.assertEqual(hit.reason, "unchanged_structural_identity")

    def test_cache_refuses_capacity_overflow(self):
        matcher = compile_rule_pack(prove_rule_pack_v2())
        cache = StructuralConeCache(max_entries=1)
        cache.rewrite("cone-a", aig_or_expr(Var(0), Var(1)), matcher)
        with self.assertRaises(ValueError):
            cache.rewrite("cone-b", aig_or_expr(Var(0), Var(2)), matcher)

    def test_related_versions_have_exact_declared_change_sets(self):
        config = VersionedRuleConfig(data_seed=17, cone_count=8,
                                     changed_per_transition=2, rounds=1, max_seconds=30)
        versions, manifest = make_versions(config)
        self.assertEqual([manifest["changes"][version]["changed_count"]
                          for version in ("v1", "v2", "v3")], [0, 2, 2])
        for version in ("v1", "v2", "v3"):
            self.assertEqual(len(set(manifest["changes"][version]["structural_sha256"].values())), 8)
        for previous, current in (("v1", "v2"), ("v2", "v3")):
            prior = {cone.cone_id: cone for cone in versions[previous]}
            for cone in versions[current]:
                if not cone.changed_from_previous:
                    self.assertEqual(cone.expr, prior[cone.cone_id].expr)
                    self.assertIsNot(cone.expr, prior[cone.cone_id].expr)


class VersionedRuleExperimentTests(unittest.TestCase):
    def test_register_and_summary_preserve_complete_agenda(self):
        root = Path(__file__).resolve().parents[1]
        register = json.loads((root / "docs/recognition/experiment_register.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual([track["id"] for track in register["tracks"]],
                         [f"R{index:02d}" for index in range(1, 19)])
        self.assertEqual(len(register["applications"]), 8)
        recorded = {track["id"] for track in register["tracks"]
                    if any(result.get("report") == "VERSIONED_RULE_CACHE_MILESTONE_D3_2026_08_29.md"
                           for result in track["results"])}
        self.assertEqual(recorded, {"R03", "R04", "R05", "R09", "R16", "R18"})
        summary = json.loads((root / "docs/recognition/versioned_rule_cache_milestone_d3_results.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual(summary["verification"]["semantic_mismatches"], 0)
        self.assertEqual(summary["verification"]["changed_cone_invalidations_verified"], 8)
        self.assertFalse(summary["criteria"]["production_promotion"])

    def test_small_run_is_exact_and_independently_verifiable(self):
        config = VersionedRuleConfig(data_seed=23, cone_count=8,
                                     changed_per_transition=2, rounds=1, max_seconds=30)
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            result = run_versioned_rule_experiment(config, run, progress=lambda _message: None)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["semantic_mismatches"], 0)
            self.assertTrue(result["criteria"]["exact_invalidation_met"])
            self.assertEqual(result["summaries"]["versions"]["v2"]["cache_hits"], 6)
            from scripts.crse_versioned_rule_verify import verify
            verification = verify(run)
            self.assertEqual(verification["status"], "pass")
            self.assertEqual(verification["measurement_rows_verified"], 9)


if __name__ == "__main__":
    unittest.main()
