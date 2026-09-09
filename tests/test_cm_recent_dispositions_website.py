"""Evidence-bound checks for the September 2026 public dispositions."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deliverables_n22_24" / "master_explainer_2026_08_03"
VERIFICATION = ROOT / "docs" / "research" / "verification"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class RecentDispositionsWebsiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load(SITE / "cm_master_data_2026_08_03.json")
        cls.current = cls.data["e23_current_research"]
        cls.numbers = cls.data["_numbers"]

    def test_all_controlling_decisions_fail_closed(self):
        self.assertEqual(self.current["as_of"], "2026-09-08")
        self.assertFalse(self.current["production_behavior_changed"])
        self.assertFalse(self.current["runtime_selector_enabled"])
        self.assertFalse(self.current["runpod_request_permitted"])
        self.assertEqual(
            self.current["decisions"]["h2_h3"]["decision"],
            "no_go_close_h2_h3_still_deferred",
        )
        self.assertEqual(
            self.current["decisions"]["h6"]["decision"],
            "no_go_h6_estimator_and_routing_deferred",
        )
        self.assertEqual(
            self.current["decisions"]["independent_workflow"]["decision"],
            "no_go_no_material_component",
        )
        self.assertEqual(
            self.current["decisions"]["hardware"]["decision"],
            "insufficient_behavior_change_or_provenance",
        )

    def test_rendered_numbers_equal_controlling_summary_fields(self):
        incremental = load(
            VERIFICATION
            / "incremental-revision-local-gate-retry-003-2026-09-04"
            / "SUMMARY.json"
        )
        h2_h3 = load(
            VERIFICATION
            / "cm-h2-h3-profile-gate-retry-002-2026-09-08"
            / "SUMMARY.json"
        )
        h6 = load(
            VERIFICATION
            / "cm-h6-representation-estimator-attempt-001-2026-09-08"
            / "SUMMARY.json"
        )
        workflow = load(
            VERIFICATION
            / "cm-independent-active-workflow-2026-09-08"
            / "SUMMARY_RETRY_002.json"
        )
        self.assertEqual(
            self.numbers["recent.incremental.vs_cache"]["value"],
            incremental["incremental_update_over_current_persistent_cm"]["geomean"],
        )
        self.assertEqual(
            self.numbers["recent.h2h3.rows"]["value"], h2_h3["rows"]
        )
        self.assertEqual(
            self.numbers["recent.h6.ordered_pairs"]["value"],
            h6["metrics"]["pairwise_order_agreements"],
        )
        self.assertEqual(
            self.numbers["recent.workflow.profile_rows"]["value"],
            workflow["profile_rows"],
        )
        for token in (
            "recent.incremental.vs_cache",
            "recent.h2h3.rows",
            "recent.h6.ordered_pairs",
            "recent.workflow.profile_rows",
        ):
            self.assertIn(" :: ", self.numbers[token]["prov"])

    def test_each_audience_renders_the_disposition_and_source_links(self):
        expected = {
            "index.html": "Recent profile-first studies produced useful boundary evidence",
            "layperson.html": "Several promising ideas were tested and did not earn a product change",
            "investor.html": "The latest gates reduce technical uncertainty",
            "expert.html": "Decision-bearing September 4 and 8 results",
        }
        for name, phrase in expected.items():
            page = (SITE / name).read_text(encoding="utf-8")
            audience = "master" if name == "index.html" else name.removesuffix(".html")
            self.assertIn(f'currentResearchDisposition("{audience}")', page, name)
            self.assertIn("Research disposition · ${E.as_of}", page, name)
            self.assertIn(phrase, page, name)
            self.assertIn("Controlling summary", page, name)
            self.assertIn("Production behavior remains unchanged", page, name)

    def test_missing_neural_machine_artifacts_are_explicitly_excluded(self):
        neural = self.data["e22_learning_neural"]
        self.assertEqual(len(neural["excluded_missing_artifacts"]), 2)
        page = (SITE / "learning-neural-evidence.html").read_text(encoding="utf-8")
        self.assertIn("Unsupported numbers excluded", page)
        for token in (
            "ln.initial_cases",
            "ln.word_headroom",
            "ln.bigint_headroom",
            "ln.bigint_labels",
            "ln.native_headroom",
        ):
            self.assertNotIn(token, self.data["_numbers"])


if __name__ == "__main__":
    unittest.main()
