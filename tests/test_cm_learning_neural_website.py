"""Evidence-bound checks for the learning/neural static website page."""

import importlib.util
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deliverables_n22_24" / "master_explainer_2026_08_03"


def loader():
    spec = importlib.util.spec_from_file_location("learning_neural_website", SITE / "cm_learning_neural_evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LearningNeuralWebsiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = loader()
        cls.evidence, cls.numbers = cls.module.build_learning_neural_evidence(SITE)
        cls.data = json.loads((SITE / "cm_master_data_2026_08_03.json").read_text(encoding="utf-8"))
        cls.template = (SITE / "cm_learning_neural_template.html").read_text(encoding="utf-8")
        cls.page = (SITE / "learning-neural-evidence.html").read_text(encoding="utf-8")

    def test_generated_payload_matches_pinned_loader(self):
        self.assertEqual(self.data["e22_learning_neural"], self.evidence)
        for key, value in self.numbers.items():
            self.assertEqual(self.data["_numbers"][key], value, key)
        self.assertEqual(self.evidence["status"], "verified_read_only_no_training")

    def test_decision_fails_closed(self):
        self.assertIn("No selector or neural route is promoted", self.evidence["decision"])
        self.assertEqual(len(self.evidence["tasks"]), 6)
        self.assertGreaterEqual(len(self.evidence["timeline"]), 15)
        self.assertEqual(self.numbers["ln.label_disagree"]["value"], 1)
        self.assertEqual(self.numbers["ln.economic_gate"]["value"], 1.10)
        self.assertTrue(all(item["status"] == "missing" for item in self.evidence["charged_costs"]))
        self.assertEqual(len(self.evidence["excluded_missing_artifacts"]), 2)
        for token in ("ln.initial_cases", "ln.word_headroom", "ln.bigint_headroom", "ln.bigint_labels", "ln.native_headroom"):
            self.assertNotIn(token, self.numbers)

    def test_page_exposes_required_sections_and_interactions(self):
        for anchor in ("dashboard", "status", "tasks", "timeline", "representations", "quality", "exact-controls", "economics", "provenance", "certificate", "next-work"):
            self.assertIn(f'section("{anchor}"', self.template)
        for control in ("ln-task", "ln-status", "ln-search"):
            self.assertIn(control, self.template)
        for graphic in ("ln-bullet-track", "ln-agreement-bar", "ln-c5-graphic", "ln-split-bar", "ln-cost-ledger"):
            self.assertIn(graphic, self.template)
        for token in ("ln.gcc_gross", "ln.clang_gross", "ln.economic_gate", "ln.c5_slow_min", "ln.freeze_cases"):
            self.assertIn(token, self.template)
        self.assertIn("prefers-reduced-motion", self.page)
        self.assertIn("Unsupported numbers excluded", self.page)

    def test_source_template_forwards_to_generated_page_without_a_fourth_script(self):
        self.assertIn("cm_learning_neural_template\\.html", self.template)
        self.assertIn('location.replace("learning-neural-evidence.html")', self.template)
        self.assertIn("if (!IS_SOURCE_TEMPLATE)", self.template)
        self.assertIn("initialTarget.scrollIntoView()", self.template)
        self.assertEqual(self.template.count("<script>"), 3)
        self.assertNotIn("http-equiv=\"refresh\"", self.template)

    def test_generated_page_is_fully_expanded(self):
        for marker in ("/*__CM_CSS__*/", "/*__CM_LIB__*/", "/*__CM_DATA__*/"):
            self.assertNotIn(marker, self.page)
        self.assertNotIn("‹?ln.", self.page)

    def test_source_links_resolve_and_no_machine_paths_leak(self):
        for link in self.evidence["links"]:
            self.assertTrue((SITE / link["href"]).resolve().is_file(), link["href"])
        serialized = json.dumps(self.evidence)
        self.assertNotRegex(serialized, r"[A-Za-z]:\\\\|/Users/|/home/")

    def test_complete_milestone_index_resolves_and_binds_artifacts(self):
        rows = self.evidence["milestone_sources"]
        self.assertEqual(len(rows), self.numbers["ln.milestone_source_pairs"]["value"])
        self.assertGreaterEqual(len(rows), 35)
        self.assertEqual(len({row["milestone"] for row in rows}), len(rows))
        for row in rows:
            report = (SITE / row["report"]).resolve()
            artifact = (SITE / row["artifact"]).resolve()
            self.assertTrue(report.is_file(), row["milestone"])
            self.assertTrue(artifact.is_file(), row["milestone"])
            payload = artifact.read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(hashlib.sha256(payload).hexdigest(), row["artifact_sha256"])
        for row in self.evidence["timeline"]:
            self.assertTrue((SITE / row["report"]).resolve().is_file(), row["milestone"])
            self.assertTrue((SITE / row["artifact"]).resolve().is_file(), row["milestone"])

    def test_action_boundaries_are_explicit(self):
        actions = self.evidence["next_actions"]
        self.assertEqual(set(actions), {"now", "benchmark", "prohibited"})
        self.assertTrue(all(actions.values()))
        self.assertIn("Do not train", " ".join(actions["prohibited"]))
        self.assertIn("raw 16-block timings", " ".join(actions["now"]))
        self.assertIn("all 16 paired q64 blocks", " ".join(actions["benchmark"]))

    def test_new_read_only_integrity_gates_are_visible(self):
        self.assertEqual(self.evidence["updated"], "2026-09-10")
        self.assertIn("Raw q64 evidence verifier", self.template)
        self.assertIn("Neural memory repeatability gate", self.template)
        self.assertIn("cm_query_ladder_decision_surface.py", self.template)
        self.assertIn("crse_audit_h6_freeze_portability.py", self.template)
        self.assertTrue(any(
            link["label"] == "Decision-surface and memory-evaluation boundary"
            for link in self.evidence["links"]
        ))

    def test_c6_positive_exact_core_is_separate_from_learned_routing(self):
        c6 = json.loads(
            (ROOT / "docs" / "recognition" / "learning_milestone_c6_packed_source_anf_results.json")
            .read_text(encoding="utf-8")
        )
        methods = c6["method_summary"]
        expected = {
            "ln.c6.test.median_speedup": methods["truth_vector_anf/test"]["median_total_ns"] / methods["cached_packed_source_anf/test"]["median_total_ns"],
            "ln.c6.test.p95_speedup": methods["truth_vector_anf/test"]["p95_total_ns"] / methods["cached_packed_source_anf/test"]["p95_total_ns"],
            "ln.c6.confirmatory.median_speedup": methods["truth_vector_anf/confirmatory"]["median_total_ns"] / methods["cached_packed_source_anf/confirmatory"]["median_total_ns"],
            "ln.c6.confirmatory.p95_speedup": methods["truth_vector_anf/confirmatory"]["p95_total_ns"] / methods["cached_packed_source_anf/confirmatory"]["p95_total_ns"],
        }
        for token, value in expected.items():
            self.assertEqual(self.numbers[token]["value"], value)
            self.assertEqual(self.numbers[token]["fmt"], "x6")
        self.assertEqual(self.numbers["ln.c6.semantic_mismatches"]["value"], 0)
        self.assertFalse(c6["criteria"]["production_promotion"])
        self.assertIn("C6 · positive exact-core result", self.template)
        self.assertIn("learned hybrid remained unpromoted", self.template)

    def test_source_blind_contract_is_visible(self):
        self.assertEqual(self.numbers["ln.freeze_cases"]["value"], 72)
        self.assertEqual(self.numbers["ln.features"]["value"], 13)
        self.assertEqual(self.numbers["ln.prior_overlap"]["value"], 0)
        self.assertTrue(self.evidence["source_blind"]["forbidden"])
        self.assertTrue(self.evidence["certificate"])


if __name__ == "__main__":
    unittest.main()
