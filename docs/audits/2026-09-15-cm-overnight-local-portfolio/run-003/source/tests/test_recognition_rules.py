from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from cm_exprlib import And, Not, Or, Var, Xor
from cmbench.recognition.proved_rules import (
    ProvedRule, aig_xor_expr, canonical, compile_rule, prove_aig_xor_rule,
)
from cmbench.recognition.rule_experiment import (
    RuleExperimentConfig, make_rule_regions, run_rule_experiment,
)
from cmbench.recognition.teacher import teach


class ProvedMetavariableRuleTests(unittest.TestCase):
    def test_proof_exhausts_boolean_domain_and_rejects_tampering(self):
        proof = prove_aig_xor_rule()
        self.assertEqual(len(proof.document["proof_rows"]), 4)
        self.assertTrue(all(row["lhs"] == row["rhs"] for row in proof.document["proof_rows"]))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rule.json"
            proof.save(path)
            self.assertEqual(ProvedRule.load(path).to_dict(), proof.to_dict())
            document = json.loads(path.read_text(encoding="utf-8"))
            document["replacement"]["op"] = "or"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(ValueError):
                ProvedRule.load(path)
        document = proof.to_dict()
        document["proof_rows"][3]["rhs"] = True
        document["proof_rows_sha256"] = hashlib.sha256(canonical(document["proof_rows"])).hexdigest()
        payload = {key: value for key, value in document.items() if key != "payload_sha256"}
        document["payload_sha256"] = hashlib.sha256(canonical(payload)).hexdigest()
        with self.assertRaises(ValueError):
            ProvedRule.from_dict(document)

    def test_compiled_matcher_handles_commutation_and_rejects_near_matches(self):
        config = RuleExperimentConfig(batch_sizes=(8,), rounds=1, epfl_limit=1,
                                      negative_controls=8, max_seconds=30)
        positive, negative = make_rule_regions(config)
        shifted, _ = make_rule_regions(RuleExperimentConfig(
            data_seed=config.data_seed + 1, batch_sizes=(8,), rounds=1,
            epfl_limit=1, negative_controls=8, max_seconds=30))
        self.assertNotEqual(positive[0].expr, shifted[0].expr)
        matcher = compile_rule(prove_aig_xor_rule())
        for region in positive:
            with self.subTest(region=region.region_id):
                rewrite = matcher.rewrite(region.expr, 8)
                self.assertEqual(rewrite.applications, 1)
                self.assertEqual(teach(region.expr, 8).bits, teach(rewrite.result, 8).bits)
        for region in negative:
            with self.subTest(region=region.region_id):
                self.assertEqual(matcher.rewrite(region.expr, 8).applications, 0)

    def test_rewrite_preserves_dag_sharing_and_can_require_instance_check(self):
        a = And(Var(0), Var(1))
        b = Or(Var(2), Not(Var(3)))
        motif = aig_xor_expr(a, b)
        source = And(motif, motif)
        matcher = compile_rule(prove_aig_xor_rule())
        calls = []
        rewrite = matcher.rewrite(source, 8,
            verify=lambda before, after: calls.append((before, after)) is None)
        self.assertEqual(rewrite.applications, 1)
        self.assertEqual(len(calls), 1)
        self.assertIs(rewrite.result.a, rewrite.result.b)
        self.assertIsInstance(rewrite.result.a, Xor)
        rejected = matcher.rewrite(motif, 8, verify=lambda _before, _after: False)
        self.assertEqual(rejected.applications, 0)
        self.assertEqual(rejected.rejected, 1)
        self.assertEqual(teach(rejected.result, 8).bits, teach(motif, 8).bits)


class ProvedRuleExperimentTests(unittest.TestCase):
    def test_register_and_summary_preserve_full_research_agenda(self):
        root = Path(__file__).resolve().parents[1]
        register = json.loads((root / "docs/recognition/experiment_register.json").read_text(encoding="utf-8"))
        self.assertEqual([track["id"] for track in register["tracks"]],
                         [f"R{index:02d}" for index in range(1, 19)])
        self.assertEqual(len(register["applications"]), 8)
        recorded = {track["id"] for track in register["tracks"]
                    if any(result.get("report") == "PROVED_RULE_MILESTONE_D2_2026_08_29.md"
                           for result in track["results"])}
        self.assertEqual(recorded, {"R03", "R04", "R05", "R16", "R18"})
        summary = json.loads((root / "docs/recognition/proved_rule_milestone_d2_results.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual(summary["verification"]["semantic_mismatches"], 0)
        self.assertEqual(summary["data"]["epfl_internal_applications"], 5)
        self.assertFalse(summary["criteria"]["production_promotion"])

    def test_small_run_is_exact_and_independently_verifiable(self):
        config = RuleExperimentConfig(data_seed=91, batch_sizes=(1, 8), rounds=1,
                                      epfl_limit=2, negative_controls=4, max_seconds=30)
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            result = run_rule_experiment(config, run, progress=lambda _message: None)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["semantic_mismatches"], 0)
            self.assertEqual(result["negative_controls"]["false_matches"], 0)
            self.assertTrue(result["criteria"]["bounded_reuse_demonstrated"])
            from scripts.crse_rule_verify import verify
            verification = verify(run)
            self.assertEqual(verification["status"], "pass")
            self.assertEqual(verification["measurement_rows_verified"], 12)


if __name__ == "__main__":
    unittest.main()
