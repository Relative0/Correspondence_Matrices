import csv
import hashlib
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deliverables_n22_24" / "master_explainer_2026_08_03"
RERUN = ROOT / "docs" / "audits" / "2026-08-25-cm-deep-performance" / "reruns" / "campaign-20260826-132038"
THREE_LANE = ROOT / "docs" / "audits" / "2026-08-25-cm-deep-performance" / "remaining-work" / "three-lane-20260827-011536"
USE_CASE_BENCHMARKS = SITE / "use_case_benchmarks_2026-08-27"


class Parser(HTMLParser):
    pass


def load_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class MasterWebsiteEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((SITE / "cm_master_data_2026_08_03.json").read_text(encoding="utf-8"))
        cls.content = json.loads((SITE / "cm_master_content_2026_08_03.json").read_text(encoding="utf-8"))
        cls.use_case_catalog = json.loads((USE_CASE_BENCHMARKS / "CM-USE-CASE-BENCHMARK-CATALOG.json").read_text(encoding="utf-8"))

    def test_evidence_revision_is_deliberately_pinned(self):
        self.assertEqual(
            self.data["_campaign"]["evidence_revision"],
            "4dbfffc1db749e85401d533c5a07cb529a41eb37",
        )

    def test_cache_tokens_equal_machine_readable_fields(self):
        rows = load_csv(RERUN / "cache_reuse50_summary.csv")
        by_k = {int(row["n_vars"]): row for row in rows}
        for k in (4, 8, 12, 16):
            expected = float(by_k[k]["ratio_cm_hybrid_no_reinflate_cached_over_bitset_cached"])
            self.assertEqual(self.data["_numbers"][f"cache.exec.k{k}"]["value"], expected)

    def test_trace_and_workload_boundaries_equal_audits(self):
        trace = json.loads((ROOT / "docs" / "audits" / "2026-08-25-cm-deep-performance" / "remaining-work" / "campaign-20260826-154541" / "trace_overhead_v3_sample16_summary.json").read_text(encoding="utf-8"))
        workload = json.loads((THREE_LANE / "WORKLOAD-MANIFEST-TEMPLATE-VALIDATION.json").read_text(encoding="utf-8"))
        self.assertEqual(self.data["_numbers"]["trace.v3.ratio"]["value"], trace["ratio_median"])
        self.assertEqual(self.data["_numbers"]["trace.sample_every"]["value"], trace["sample_every"])
        self.assertEqual(self.data["_numbers"]["workload.blockers"]["value"], len(workload["blockers"]))
        self.assertFalse(self.data["e19_current_evidence"]["workload_intake"]["ready_for_metrics_capture"])

    def test_memory_policy_is_proposed_not_current(self):
        late = json.loads((SITE / "website_audit_2026-08-27" / "ACCEPTED-LATE-EVIDENCE.json").read_text(encoding="utf-8"))
        policy = self.data["e19_current_evidence"]["temporary_memory"]["policy"]
        self.assertEqual(policy, late["temporary_memory_policy"])
        self.assertIsNone(policy["current_default_temporary_limit"])
        self.assertIn("approval deferred", policy["decision_state"])

    def test_all_pages_parse_and_include_current_update(self):
        for name in ("index.html", "layperson.html", "investor.html", "expert.html", "usecases.html"):
            text = (SITE / name).read_text(encoding="utf-8")
            Parser().feed(text)
            self.assertNotIn("The persistent cache has never been studied", text, name)
        for name in ("index.html", "layperson.html", "investor.html", "expert.html"):
            text = (SITE / name).read_text(encoding="utf-8")
            self.assertIn("What the 2026-08-26/27 evidence added", text, name)

    def test_master_links_latest_persistence_and_trace_evidence(self):
        text = (SITE / "index.html").read_text(encoding="utf-8")
        report = ROOT / "docs" / "research" / "PERSISTENCE-AND-TRACE-PROGRESS-2026-08-29.md"
        summary = json.loads(
            (
                ROOT
                / "docs"
                / "research"
                / "verification"
                / "comparative-persistence-pilot-v2-2026-08-29"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(report.is_file())
        self.assertIn("Latest verified research · 2026-08-29", text)
        self.assertIn("144/144 frozen serialize/reload cells", text)
        self.assertIn("zero observed natural sessions", text)
        self.assertIn("PERSISTENCE-AND-TRACE-PROGRESS-2026-08-29.md", text)
        self.assertEqual(summary["reconciliation"]["observed_cells"], 144)
        self.assertEqual(summary["exact_relation_rows"], 288)
        self.assertFalse(summary["trace_audit"]["natural_claim_permitted"])

    def test_use_case_page_keeps_hypotheses_and_boundaries_visible(self):
        text = (SITE / "usecases.html").read_text(encoding="utf-8")
        self.assertIn("Quantum-computing support logic", text)
        self.assertIn("Quantum amplitudes, phase, entanglement", text)
        self.assertIn("Where other methods lead", text)
        self.assertIn("Benchmark this hypothesis", text)
        self.assertIn("Synthetic cases deliberately sweep reuse", text)
        self.assertIn("Download the machine-readable catalog", text)

    def test_all_eight_use_cases_have_a_complete_benchmark_contract(self):
        entries = self.use_case_catalog["entries"]
        expected_ids = {"hardware", "ai", "biology", "quantum", "compiler", "security", "configuration", "regulated"}
        self.assertEqual({entry["id"] for entry in entries}, expected_ids)
        self.assertEqual({item["id"] for item in self.content["use_cases"]["items"]}, expected_ids)
        for entry in entries:
            self.assertTrue(entry["audit_verdict"], entry["id"])
            self.assertTrue(entry["scope_correction"], entry["id"])
            self.assertGreaterEqual(len(entry["real_datasets"]), 2, entry["id"])
            self.assertGreaterEqual(len(entry["baselines"]), 3, entry["id"])
            self.assertGreaterEqual(len(entry["tasks"]), 5, entry["id"])
            self.assertTrue(entry["dominance_gate"], entry["id"])
            for dataset in entry["real_datasets"]:
                self.assertTrue(dataset["url"].startswith("https://"), dataset)

    def test_synthetic_use_case_suites_are_complete_and_self_consistent(self):
        synthetic = USE_CASE_BENCHMARKS / "synthetic"
        manifest = json.loads((synthetic / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["domain_count"], 8)
        self.assertEqual(manifest["case_count"], 48)
        for file_record in manifest["files"]:
            payload = (synthetic / file_record["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), file_record["sha256"])
            cases = [json.loads(line) for line in payload.decode("utf-8").splitlines()]
            self.assertEqual(len(cases), file_record["cases"])
            for case in cases:
                self.assertTrue(case["synthetic_only"])
                self.assertEqual([version["id"] for version in case["versions"]], ["base", "equivalent_rewrite", "localized_change"])
                base, equivalent, changed = case["versions"]
                for base_eval, equivalent_eval in zip(base["evaluations"], equivalent["evaluations"]):
                    self.assertEqual(
                        [root["packed_bits_sha256"] for root in base_eval["roots"]],
                        [root["packed_bits_sha256"] for root in equivalent_eval["roots"]],
                    )
                self.assertNotEqual(
                    [root["packed_bits_sha256"] for root in base["evaluations"][0]["roots"]],
                    [root["packed_bits_sha256"] for root in changed["evaluations"][0]["roots"]],
                )

    def test_authored_result_tokens_resolve_uniquely(self):
        token_re = re.compile(r"\{\{([A-Za-z0-9_.]+)\}\}")
        used = set()
        for path in [SITE / "cm_master_content_2026_08_03.json", SITE / "cm_master_shared.js", *SITE.glob("cm_*_template.html")]:
            used.update(token_re.findall(path.read_text(encoding="utf-8")))
        used.discard("token")  # documented placeholder in the content contract
        self.assertFalse(used - set(self.data["_numbers"]))


if __name__ == "__main__":
    unittest.main()
