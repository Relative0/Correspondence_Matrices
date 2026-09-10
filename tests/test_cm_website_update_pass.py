"""Regression checks for the 2026-09-10 comprehensive website update pass."""

import csv
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deliverables_n22_24" / "master_explainer_2026_08_03"
REVISION = "ff7511b401b0008ef3bff0f426f24c59a74c84f5"


class WebsiteUpdatePassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((SITE / "cm_master_data_2026_08_03.json").read_text(encoding="utf-8"))
        cls.numbers = cls.data["_numbers"]

    def test_flattened_cse_headline_uses_current_v3_and_retains_history(self):
        inference = SITE.parent / "corrections_2026_08_25" / "symmetric" / "audited_v3_inference.csv"
        with inference.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        current = next(
            row for row in rows
            if row["scope"] == "overall" and row["corpus"] == "all" and row["live_k"] == "all"
            and row["metric"] == "cm_current_over_cse_flat_current"
        )
        plotted = self.data["e2_kernel_vs_cse_flat"]["rows"]
        self.assertEqual(plotted[0]["group"], "current")
        self.assertEqual(plotted[0]["value"], float(current["paired_formula_cluster_geomean"]))
        self.assertLess(plotted[0]["hi"], 1.0)
        self.assertEqual(plotted[1]["value"], self.numbers["flat.local"]["value"])
        self.assertGreater(plotted[1]["value"], 1.0)
        template = (SITE / "cm_master_template.html").read_text(encoding="utf-8")
        self.assertIn('P("{{symv3.bare.overall}}")', template)
        self.assertNotIn("DATA.e2_kernel_vs_cse_flat.rows[1].value", template)

    def test_c16_local_and_linux_values_are_evidence_bound(self):
        local = json.loads((ROOT / "docs/recognition/learning_milestone_c16_exact_screened_gf2_results.json").read_text(encoding="utf-8"))
        linux = json.loads((ROOT / "docs/recognition/c16_linux_confirmation/RUNPOD_C16_PACKAGE_V2_FINAL_VERIFICATION_20260831.json").read_text(encoding="utf-8"))
        self.assertEqual(self.numbers["recognition.c16.whole_path_speedup"]["value"], local["summary"]["speedup"]["screened_whole_path_over_exhaustive"])
        self.assertEqual(self.numbers["recognition.c16.linux_whole_path_speedup"]["value"], linux["speedup"]["screened_whole_path_over_exhaustive"])
        self.assertEqual(self.numbers["recognition.c16.linux_p95_speedup"]["value"], linux["speedup"]["screened_whole_path_p95"])
        self.assertEqual(self.numbers["recognition.c16.linux_semantic_mismatches"]["value"], 0)
        self.assertEqual(self.numbers["recognition.c16.linux_artifact_mismatches"]["value"], 0)
        self.assertFalse(local["production_promotion"])

    def test_download_index_is_commit_pinned_and_hash_complete(self):
        evidence = self.data["e24_downloads"]
        self.assertEqual(evidence["revision"], REVISION)
        self.assertEqual({group["id"] for group in evidence["sets"]}, {
            "website-audit", "symmetric-v3", "c6-packed-core", "c16-screening", "feature-model", "architecture",
        })
        artifacts = [item for group in evidence["sets"] for item in group["artifacts"]]
        self.assertEqual(len(artifacts), evidence["artifact_count"])
        self.assertGreaterEqual(len(artifacts), 30)
        self.assertGreater(evidence["candidate_artifact_count"], evidence["artifact_count"])
        for item in artifacts:
            path = (ROOT / item["path"]).resolve()
            self.assertTrue(path.is_relative_to(ROOT), item["path"])
            self.assertTrue(path.is_file(), item["path"])
            payload = path.read_bytes()
            if path.suffix.lower() in {".csv", ".html", ".json", ".jsonl", ".md", ".py", ".sha256", ".txt", ".yml", ".yaml"}:
                payload = payload.replace(b"\r\n", b"\n")
            self.assertEqual(item["sha256"], hashlib.sha256(payload).hexdigest(), item["path"])
            self.assertIn(f"/blob/{REVISION}/", item["view"])
            self.assertIn(f"/{REVISION}/", item["raw"])
            self.assertTrue(item["role"] and item["contract"] and item["scope"])

    def test_every_chart_constructor_emits_title_and_description(self):
        shared = (SITE / "cm_master_shared.js").read_text(encoding="utf-8")
        self.assertIn("function chartSvg(width, height, title, description)", shared)
        self.assertIn('el("title"', shared)
        self.assertIn('el("desc"', shared)
        self.assertEqual(shared.count('el("svg"'), 1)
        self.assertEqual(shared.count("chartSvg(W, H"), 9)

    def test_generated_download_page_is_expanded_and_deployed(self):
        page = (SITE / "data-downloads.html").read_text(encoding="utf-8")
        for marker in ("/*__CM_CSS__*/", "/*__CM_LIB__*/", "/*__CM_DATA__*/"):
            self.assertNotIn(marker, page)
        self.assertIn("Data & downloads", page)
        workflow = (ROOT / ".github/workflows/publish-results-site.yml").read_text(encoding="utf-8")
        self.assertIn('cp "$site_dir/data-downloads.html" _site/', workflow)


if __name__ == "__main__":
    unittest.main()
