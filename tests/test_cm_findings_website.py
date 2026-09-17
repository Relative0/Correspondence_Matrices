"""Evidence and integration checks for the practical findings guide."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deliverables_n22_24/master_explainer_2026_08_03"
spec = importlib.util.spec_from_file_location("findings_evidence", SITE / "cm_findings_evidence.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FindingsWebsiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((SITE / "cm_master_data_2026_08_03.json").read_text(encoding="utf-8"))
        cls.guide = module.build_findings(cls.data)

    def test_generated_guide_and_download_match_checked_evidence(self):
        self.assertEqual(self.data["e26_findings"], self.guide)
        self.assertEqual(json.loads((SITE / module.DOWNLOAD).read_text(encoding="utf-8")), self.guide)
        self.assertEqual(len(self.guide["cards"]), 8)
        self.assertEqual(len({c["id"] for c in self.guide["cards"]}), 8)

    def test_measurements_recompute_from_inputs_and_fail_on_refusals(self):
        data = copy.deepcopy(self.data)
        panel = next(p for p in data["e25_latest_results"]["panels"] if p["id"] == "bucket-count")
        row = next(r for r in panel["rows"] if r["case"] == "model-09" and r["q"] == 8 and r["method"] == "numpy_min_fill")
        row["cold_ms"] *= 2
        card = next(c for c in module.build_findings(data)["cards"] if c["id"] == "bucket")
        self.assertAlmostEqual(card["metrics"][0]["ratio"], 121.169078 / (29.76176 * 2))
        row["status"] = "refused"
        with self.assertRaises(ValueError):
            module.build_findings(data)

    def test_code_and_local_evidence_links_resolve(self):
        for card in self.guide["cards"]:
            with self.subTest(card=card["id"]):
                self.assertTrue(card["boundary"])
                self.assertTrue((SITE / card["evidence"].split("#")[0]).is_file())
                for link in card["code"]:
                    self.assertTrue((ROOT / link["path"]).is_file(), link)
                    self.assertIn(module.SOURCE_REVISION, link["href"])
                for metric in card["metrics"]:
                    self.assertTrue((SITE / metric["source_href"]).is_file())
                    self.assertAlmostEqual(metric["ratio"], metric["control"] / metric["candidate"])
                    self.assertTrue(metric["scope"])
                    self.assertTrue(metric["selectors"])

    def test_page_is_deployed_and_navigation_and_limits_are_present(self):
        page = (SITE / "findings.html").read_text(encoding="utf-8")
        self.assertIn('role:"group","aria-label":"Filter findings by task"', page)
        self.assertIn('aria-pressed', page)
        self.assertIn('article.hidden=', page)
        self.assertIn('When to be careful.', page)
        self.assertIn('Editorial assessment', page)
        self.assertIn('not a global leaderboard', page)
        self.assertIn('findings.html', (ROOT / '.github/workflows/publish-results-site.yml').read_text())
        self.assertIn('cm_findings_template.html', (ROOT / 'scripts/cm_website_release_verify.py').read_text())
        for name in ('index', 'latest-results', 'data-downloads', 'expert', 'usecases'):
            self.assertIn('["findings.html", "Findings cheat sheet"]', (SITE / (name + '.html')).read_text(encoding='utf-8'))


if __name__ == "__main__":
    unittest.main()
