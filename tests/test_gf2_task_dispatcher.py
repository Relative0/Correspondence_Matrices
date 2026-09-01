import json
import tempfile
import unittest
from pathlib import Path

from cm_exprlib import And, Or, Var, Xor
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2
from cmbench.recognition.gf2_task_dispatcher import (
    EXHAUSTIVE,
    SCREENED,
    GF2DecompositionTask,
    compile_gf2_dispatcher,
    current_platform_identity,
    freeze_gf2_dispatch_policy,
    load_gf2_dispatch_policy,
    save_gf2_dispatch_policy,
    select_gf2_arm,
    verify_gf2_execution,
)
from cmbench.recognition.portfolio import reference_bits


class GF2TaskDispatcherTests(unittest.TestCase):
    def task(self, n_vars):
        return GF2DecompositionTask(n_vars, tuple(range(n_vars)))

    def test_policy_roundtrip_and_tamper_rejection(self):
        policy = freeze_gf2_dispatch_policy()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            save_gf2_dispatch_policy(policy, path)
            self.assertEqual(load_gf2_dispatch_policy(path), policy)
            changed = json.loads(path.read_text(encoding="utf-8"))
            changed["tiny_case_max_n_vars"] = 4
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_gf2_dispatch_policy(path)

    def test_tiny_bypass_screened_selection_and_advice_off(self):
        identity = current_platform_identity()
        policy = freeze_gf2_dispatch_policy(identity)
        tiny = select_gf2_arm(policy, self.task(3), identity=identity)
        self.assertEqual((tiny.selected_arm, tiny.reason), (EXHAUSTIVE, "tiny_case_bypass"))
        regular = select_gf2_arm(policy, self.task(4), identity=identity)
        self.assertEqual((regular.selected_arm, regular.reason), (SCREENED, "c16_screened_tail"))
        disabled = select_gf2_arm(
            policy, self.task(8), identity=identity, advice_enabled=False
        )
        self.assertEqual(disabled.selected_arm, EXHAUSTIVE)
        self.assertEqual(disabled.reason, "advice_globally_disabled")

    def test_unknown_platform_abstains_and_bad_task_refuses(self):
        identity = current_platform_identity()
        policy = freeze_gf2_dispatch_policy(identity)
        other = {**identity, "system": "OtherOS"}
        decision = select_gf2_arm(policy, self.task(6), identity=other)
        self.assertEqual(decision.selected_arm, EXHAUSTIVE)
        self.assertTrue(decision.abstained)
        invalid = GF2DecompositionTask(4, (1, 0, 2, 3))
        refused = select_gf2_arm(policy, invalid, identity=identity)
        self.assertFalse(refused.admitted)
        with self.assertRaises(ValueError):
            compile_gf2_dispatcher(policy, invalid, identity=identity)

    def test_selected_shadow_and_advice_off_preserve_exact_best(self):
        identity = current_platform_identity()
        policy = freeze_gf2_dispatch_policy(identity)
        expressions = (
            Xor(And(Var(0), Var(1)), Or(Var(2), Var(3))),
            Xor(And(Var(0), Var(1)), And(Var(2), Var(3))),
        )
        for expression in expressions:
            bits = reference_bits(expression, 4)
            expected = analyze_exact_gf2(bits, 4).best
            expected_document = expected.to_dict() if expected else None
            selected = compile_gf2_dispatcher(
                policy, self.task(4), identity=identity, shadow=True
            ).execute(bits)
            self.assertEqual(selected.selected_arm, SCREENED)
            self.assertEqual(selected.best_artifact, expected_document)
            self.assertTrue(selected.shadow_best_identity_match)
            verify_gf2_execution(
                selected.to_dict(), bits, policy_sha256=policy["policy_sha256"]
            )
            disabled = compile_gf2_dispatcher(
                policy, self.task(4), identity=identity,
                advice_enabled=False, shadow=False,
            ).execute(bits)
            self.assertEqual(disabled.selected_arm, EXHAUSTIVE)
            self.assertEqual(disabled.best_artifact, expected_document)

    def test_tiny_execution_and_result_tamper_rejection(self):
        identity = current_platform_identity()
        policy = freeze_gf2_dispatch_policy(identity)
        bits = reference_bits(Xor(Var(0), And(Var(1), Var(2))), 3)
        result = compile_gf2_dispatcher(
            policy, self.task(3), identity=identity, shadow=True
        ).execute(bits)
        self.assertEqual(result.selected_arm, EXHAUSTIVE)
        self.assertEqual(result.decision_reason, "tiny_case_bypass")
        document = result.to_dict()
        verify_gf2_execution(document, bits, policy_sha256=policy["policy_sha256"])
        changed = json.loads(json.dumps(document))
        changed["source_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            verify_gf2_execution(changed, bits, policy_sha256=policy["policy_sha256"])


if __name__ == "__main__":
    unittest.main()
