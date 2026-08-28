"""Static build/evidence checks; no browser or benchmark execution."""

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deliverables_n22_24" / "master_explainer_2026_08_03"
PAGES = {
    "cm_master_template.html": "index.html",
    "cm_layperson_template.html": "layperson.html",
    "cm_investor_template.html": "investor.html",
    "cm_expert_template.html": "expert.html",
    "cm_usecases_template.html": "usecases.html",
    "cm_feature_model_template.html": "feature-model-evidence.html",
}


def loader():
    spec = importlib.util.spec_from_file_location("feature_model_website", SITE / "cm_feature_model_evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.current = ""

    def handle_data(self, data):
        if self.current is not None:
            self.current += data

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.scripts.append(self.current)
            self.current = None


class FeatureModelWebsiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = loader()
        cls.evidence, cls.numbers = cls.module.build_feature_model_evidence(SITE)
        cls.data = json.loads((SITE / "cm_master_data_2026_08_03.json").read_text(encoding="utf-8"))

    def test_generated_evidence_and_numbers_equal_selected_audits(self):
        self.assertEqual(self.evidence, self.data["e20_feature_model_audit"])
        for name, record in self.numbers.items():
            self.assertEqual(self.data["_numbers"][name], record, name)
        self.assertEqual(self.numbers["fm.cases"]["value"], 240)
        self.assertEqual(self.numbers["fm.assignments"]["value"], 5591040)
        self.assertEqual(self.numbers["fm.delta_cases"]["value"], 120)
        self.assertEqual(self.numbers["fm.tests"]["value"], 22)

    def test_all_generated_pages_are_current_exact_template_expansions(self):
        css = (SITE / "cm_master_shared.css").read_text(encoding="utf-8")
        lib = (SITE / "cm_master_shared.js").read_text(encoding="utf-8")
        payload = json.dumps(self.data, separators=(",", ":"), ensure_ascii=False)
        for template, page in PAGES.items():
            expected = (SITE / template).read_text(encoding="utf-8")
            expected = expected.replace("/*__CM_CSS__*/", css).replace("/*__CM_LIB__*/", lib)
            expected = expected.replace("/*__CM_DATA__*/null", payload)
            actual = (SITE / page).read_text(encoding="utf-8")
            self.assertEqual(actual, expected, page)
            parsed = Scripts()
            parsed.feed(actual)
            self.assertEqual(len(parsed.scripts), 3, page)
            self.assertIsNone(parsed.current, page)

    @unittest.skipUnless(shutil.which("node"), "Node unavailable for non-browser JavaScript syntax check")
    def test_all_generated_inline_scripts_have_valid_javascript_syntax(self):
        scripts = []
        for page in PAGES.values():
            parsed = Scripts()
            parsed.feed((SITE / page).read_text(encoding="utf-8"))
            scripts.extend({"filename": f"{page}:script{index}", "code": code}
                           for index, code in enumerate(parsed.scripts))
        check = "const fs=require('fs'),vm=require('vm'); for(const s of JSON.parse(fs.readFileSync(0,'utf8'))) new vm.Script(s.code,{filename:s.filename});"
        result = subprocess.run([shutil.which("node"), "-e", check], input=json.dumps(scripts),
                                text=True, encoding="utf-8", capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_summaries_are_visible_routes_not_only_embedded_data(self):
        shared = (SITE / "cm_master_shared.js").read_text(encoding="utf-8")
        self.assertIn('["feature-model-evidence.html", "Results & audit"]', shared)
        for template in PAGES:
            if template != "cm_feature_model_template.html":
                self.assertIn("app.append(featureModelAuditUpdate());", (SITE / template).read_text(encoding="utf-8"))
        page = (SITE / "cm_feature_model_template.html").read_text(encoding="utf-8")
        for anchor in ("summary", "correctness", "comparisons", "coverage", "artifacts", "gaps", "scope", "downloads"):
            self.assertIn(f'section("{anchor}"', page)
        self.assertIn("E.gaps.forEach", page)
        self.assertIn("E.links.forEach", page)

    def test_measurement_and_independence_limits_remain_explicit(self):
        self.assertEqual(self.evidence["performance_status"], "provisional_measurement_gaps_open")
        self.assertFalse(self.evidence["automatic_latest_run_selection"])
        self.assertFalse(self.evidence["source_qualification"]["formal_unsat_proof"])
        self.assertFalse(self.evidence["source_qualification"]["historical_dirty_source_reconstructed"])
        self.assertFalse(self.evidence["source_qualification"]["actual_sifted_graphs_independently_replayed"])
        self.assertEqual({gap["id"] for gap in self.evidence["gaps"]}, {f"M{x:02d}" for x in range(1, 14)})
        self.assertEqual(sum(gap["severity"] == "high" for gap in self.evidence["gaps"]), 8)
        self.assertEqual(len(self.evidence["forbidden_rankings"]), 3)

    def test_every_new_evidence_download_and_source_link_resolves(self):
        targets = [link["href"] for link in self.evidence["links"]]
        targets += [run["checksum_href"] for run in self.evidence["runs"]]
        targets += [gap["source_href"] for gap in self.evidence["gaps"]]
        for relative in targets:
            self.assertTrue((SITE / relative).is_file(), relative)
            self.assertTrue((SITE / relative).resolve().is_relative_to(SITE.resolve()), relative)
        for filename in ("CONFIGURATION-REPRESENTATION-BATTERY-RESULTS.md", "HARDWARE-EPFL-CONTEXT-PILOT-RESULTS.md",
                         "CM_USE_CASE_BENCHMARK_RESEARCH_2026-08-27.md", "synthetic/MANIFEST.json"):
            self.assertTrue((SITE / self.module.BENCHMARK_DIR / filename).is_file(), filename)

    def test_old_no_configuration_evidence_claim_is_removed(self):
        content = self.data["_content"]
        self.assertNotIn("no policy, access-control or configuration workload has been measured", json.dumps(content))
        configuration = next(item for item in content["use_cases"]["items"] if item["id"] == "configuration")
        self.assertIn("performance provisional", configuration["status"])
        self.assertIn("not deployed workflows", " ".join(content["project_state"]["boundaries"]))

    def test_no_absolute_machine_paths_embedded_in_new_evidence(self):
        self.assertNotRegex(json.dumps(self.evidence), r"[A-Za-z]:\\\\|/Users/|/home/")


class PinnedEvidenceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.module = loader()
        self.temporary = tempfile.TemporaryDirectory(prefix="cm-website-identity-")
        self.addCleanup(self.temporary.cleanup)
        self.run = Path(self.temporary.name)
        self.payload = self.run / "summary.json"
        self.payload.write_text('{"status":"passed"}', encoding="utf-8")

    def manifest(self, relative="summary.json", duplicate=False):
        digest = hashlib.sha256(self.payload.read_bytes()).hexdigest()
        text = f"{digest}  {relative}\n"
        text = text * 2 if duplicate else text
        payload = text.encode("ascii")
        (self.run / "CHECKSUMS.sha256").write_bytes(payload)
        return hashlib.sha256(payload).hexdigest()

    def test_unchanged_evidence_passes(self):
        self.assertEqual(self.module.verify_run(self.run, self.manifest()), 1)

    def test_changed_payload_is_refused(self):
        expected = self.manifest()
        self.payload.write_text('{"status":"failed"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed or missing"):
            self.module.verify_run(self.run, expected)

    def test_rewritten_manifest_cannot_inherit_old_audit(self):
        expected = self.manifest()
        self.payload.write_text('{"status":"failed"}', encoding="utf-8")
        self.manifest()
        with self.assertRaisesRegex(ValueError, "identity changed"):
            self.module.verify_run(self.run, expected)

    def test_traversal_and_duplicate_entries_are_refused(self):
        with self.assertRaisesRegex(ValueError, "Unsafe or repeated"):
            self.module.verify_run(self.run, self.manifest("../summary.json"))
        with self.assertRaisesRegex(ValueError, "Unsafe or repeated"):
            self.module.verify_run(self.run, self.manifest(duplicate=True))


if __name__ == "__main__":
    unittest.main()
