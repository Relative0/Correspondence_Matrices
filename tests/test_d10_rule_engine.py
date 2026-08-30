import json
import tempfile
import unittest
from pathlib import Path

from cm_exprlib import And, Not, Or, Var, Xor
from cmbench.recognition.d10_rule_engine import (
    CANCEL_RULE, CARRY_RULE, COMPARATOR_RULE, MUX_RULE,
    D10ConeCache, D10RulePack, compile_d10_rule_pack, prove_d10_rule_pack,
)
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.d10_rule_experiment import D10Config, make_d10_cases, run_d10_experiment


class D10RuleEngineTests(unittest.TestCase):
    def setUp(self):
        self.pack = prove_d10_rule_pack()
        self.matcher = compile_d10_rule_pack(self.pack)

    def examples(self):
        a, b, c, d, e = (Var(index) for index in range(5))
        return {
            MUX_RULE: Or(And(a, b), And(Not(a), c)),
            COMPARATOR_RULE: Or(And(e, And(a, Not(b))), And(And(c, Not(d)), e)),
            CARRY_RULE: Or(And(b, c), Or(And(a, c), And(b, a))),
            CANCEL_RULE: Xor(Xor(b, a), Xor(c, a)),
        }

    def test_artifact_truth_rows_and_strict_reload(self):
        self.assertEqual([len(rule["proof_rows"]) for rule in self.pack.document["rules"]],
                         [8, 8, 32, 8])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pack.json"
            self.pack.save(path)
            self.assertEqual(D10RulePack.load(path).digest, self.pack.digest)
            changed = json.loads(path.read_text(encoding="utf-8"))
            changed["rules"][0]["proof_rows"][0]["rhs"] ^= 1
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(ValueError):
                D10RulePack.load(path)

    def test_all_rules_match_commuted_forms_and_are_exact(self):
        for rule_id, expression in self.examples().items():
            with self.subTest(rule_id=rule_id):
                rewrite = self.matcher.rewrite(expression, 5)
                self.assertEqual(rewrite.applications_by_rule[rule_id], 1)
                self.assertLess(rewrite.provenance[0]["operator_count_after"],
                                rewrite.provenance[0]["operator_count_before"])
                self.assertEqual(reference_bits(expression, 5), reference_bits(rewrite.result, 5))

    def test_noop_bypass_and_full_scan_control(self):
        expression = And(Var(0), Or(Var(1), Not(Var(2))))
        indexed = self.matcher.rewrite(expression, 3)
        scanned = self.matcher.rewrite(expression, 3, index_mode="full_scan")
        self.assertTrue(indexed.bypassed)
        self.assertEqual(indexed.screen_candidate_sites, 0)
        self.assertFalse(scanned.bypassed)
        self.assertEqual(scanned.applications, 0)
        self.assertEqual(indexed.result, expression)

    def test_near_matches_overlap_and_cycle_guard(self):
        a, b, c, d = (Var(index) for index in range(4))
        near = Or(And(a, b), And(Not(c), d))
        self.assertEqual(self.matcher.rewrite(near, 4).applications, 0)
        overlap = Or(And(a, And(b, Not(c))), And(a, And(d, Not(c))))
        rewrite = self.matcher.rewrite(overlap, 4)
        self.assertEqual(rewrite.applications_by_rule[COMPARATOR_RULE], 1)
        self.assertTrue(all(row["operator_count_after"] < row["operator_count_before"]
                            for row in rewrite.provenance))
        second = self.matcher.rewrite(rewrite.result, 4)
        self.assertEqual(second.applications, 0)

    def test_changed_cone_add_remove_revert_and_serialized_reload(self):
        original = self.examples()[MUX_RULE]
        changed = self.examples()[CANCEL_RULE]
        cache = D10ConeCache(4)
        cold = cache.rewrite("cone-a", original, self.matcher, 5)
        warm = cache.rewrite("cone-a", original, self.matcher, 5)
        modified = cache.rewrite("cone-a", changed, self.matcher, 5)
        reverted = cache.rewrite("cone-a", original, self.matcher, 5)
        added = cache.rewrite("cone-b", changed, self.matcher, 5)
        self.assertFalse(cold.cache_hit)
        self.assertTrue(warm.cache_hit)
        self.assertTrue(modified.invalidated)
        self.assertTrue(reverted.invalidated)
        self.assertEqual(cache.invalidate_missing({"cone-a"}), 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.json"
            cache.save(path)
            loaded = D10ConeCache.load(path, self.matcher)
            self.assertTrue(loaded.rewrite("cone-a", original, self.matcher, 5).cache_hit)
        self.assertEqual(reference_bits(added.result, 5), reference_bits(changed, 5))

    def test_source_backed_dataset_and_smoke_experiment(self):
        cases, provenance = make_d10_cases()
        self.assertEqual((len(cases), provenance["motif_rows"], provenance["no_op_rows"]),
                         (30, 16, 14))
        self.assertTrue(all(self.matcher.rewrite(case.expression, case.n_vars).applications == 0
                            for case in cases if case.kind == "no_op"))
        with tempfile.TemporaryDirectory() as directory:
            result = run_d10_experiment(D10Config("d10-test", 20260830, 3, 60.0),
                                        Path(directory) / "run", progress=lambda _message: None)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["semantic_mismatches"], 0)
            self.assertTrue(result["cache_version_probe"]["exact"])


if __name__ == "__main__":
    unittest.main()
