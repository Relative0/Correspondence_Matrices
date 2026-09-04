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
C38_ADJUDICATION = ROOT / "docs" / "recognition" / "c38_linux_confirmation" / "C38_CROSS_MACHINE_ADJUDICATION_20260903.json"
ARCHITECTURE_ANALYSIS = ROOT / "docs" / "recognition" / "architecture_comparison_execution_retry_20260903" / "ANALYSIS.json"
ARCHITECTURE_CROSS_MACHINE = ROOT / "docs" / "recognition" / "architecture_query_ladder_cross_machine_execution_20260904" / "CROSS_MACHINE_ANALYSIS.json"


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

    def test_headline_tiles_keep_synthetic_and_epfl_cohorts_separate(self):
        text = (SITE / "index.html").read_text(encoding="utf-8")
        self.assertIn("local synthetic kernel, {{kernel.local.pct}} faster; EPFL", text)
        self.assertIn("Linux synthetic replications", text)
        self.assertIn("with its clustered interval spanning parity", text)
        self.assertNotIn("replicated on real circuits and on {{kernel.pod.count}}", text)

    def test_master_links_latest_public_repository_evidence(self):
        text = (SITE / "index.html").read_text(encoding="utf-8")
        report = ROOT / "docs" / "research" / "FRESH-PROCESS-PERSISTENCE-PROGRESS-2026-08-29.md"
        summary = json.loads(
            (
                ROOT
                / "docs"
                / "research"
                / "verification"
                / "fresh-process-persistence-v2-2026-08-29"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(report.is_file())
        c16 = json.loads(
            (ROOT / "docs" / "recognition" / "learning_milestone_c16_exact_screened_gf2_results.json")
            .read_text(encoding="utf-8")
        )
        self.assertIn("Latest public-repository evidence · 2026-08-30", text)
        self.assertIn("C16 exact-screened CM/GF(2) tail", text)
        self.assertIn("LEARNING_MILESTONE_C16_EXACT_SCREENED_GF2_2026_08_30.md", text)
        self.assertIn("COMPARATIVE-PLAN-EXECUTION-STATUS-20260829.md", text)
        self.assertIn("256/256 counterbalanced cells", text)
        self.assertIn("zero observed natural sessions", text)
        self.assertIn("FRESH-PROCESS-PERSISTENCE-PROGRESS-2026-08-29.md", text)
        self.assertEqual(summary["reconciliation"]["observed_cells"], 256)
        self.assertEqual(summary["exact_relation_rows"], 512)
        self.assertEqual(summary["refused_arms"], ["cudd_bdd", "cudd_zdd", "d4_ddnnf"])
        self.assertFalse(summary["performance_claim_permitted"])
        self.assertFalse(c16["production_promotion"])
        self.assertEqual(c16["verification"]["source_cases_replayed"], 40)
        self.assertEqual(c16["verification"]["controls_replayed"], 12)
        self.assertEqual(c16["verification"]["measurement_rows_checked"], 360)

    def test_expert_current_architecture_task_map_tracks_verified_evidence(self):
        c38 = json.loads(C38_ADJUDICATION.read_text(encoding="utf-8"))
        architecture = json.loads(ARCHITECTURE_ANALYSIS.read_text(encoding="utf-8"))
        cross_machine = json.loads(ARCHITECTURE_CROSS_MACHINE.read_text(encoding="utf-8"))
        current = self.data["e21_current_architecture"]
        numbers = self.data["_numbers"]

        self.assertEqual(
            current["source_freezes"]["architecture_comparison_sha256"],
            architecture["inputs"]["freeze_sha256"],
        )
        self.assertEqual(
            current["source_freezes"]["query_ladder_sha256"],
            cross_machine["task_contract"]["freeze_sha256"],
        )

        self.assertEqual(c38["status"], "exact_replication_passed_per_case_performance_not_confirmed")
        self.assertTrue(c38["exactness_verified_on_both"])
        self.assertTrue(current["native_portability"]["guarded_opt_in_backend_retained"])
        self.assertEqual(
            numbers["arch.native.windows.single"]["value"],
            c38["executions"][0]["single_root"]["aggregate_speedup"],
        )
        self.assertEqual(
            numbers["arch.native.linux.single_min"]["value"],
            c38["executions"][1]["single_root"]["minimum_case_speedup"],
        )

        lane_a = architecture["lanes"]["A"]
        self.assertEqual(current["complete_relation"]["best_cm"], "cm_ir_recursive_packed")
        self.assertEqual(
            numbers["arch.complete.cm_over_dense"]["value"],
            lane_a["best_fixed_cm_over_dense"]["case_cluster_geomean_speedup"],
        )
        self.assertEqual(
            numbers["arch.complete.cm_over_bitset"]["value"],
            lane_a["direct_bitset_over_best_fixed_cm"]["case_cluster_geomean_speedup"],
        )
        self.assertEqual(numbers["arch.complete.bitset_wins"]["value"], 78)

        query_rows = {row["query_count"]: row for row in current["query_ladder"]["rows"]}
        self.assertEqual(query_rows[1]["gcc_best"], "r2_topological_liveness")
        self.assertEqual(query_rows[4]["clang_best"], "r2_topological_liveness")
        self.assertEqual(query_rows[16]["gcc_best"], "cse_flat_bigint")
        self.assertEqual(query_rows[16]["clang_best"], "r2_topological_liveness")
        self.assertEqual(query_rows[64]["gcc_best"], "cse_flat_bigint")
        self.assertEqual(query_rows[64]["clang_best"], "cse_flat_bigint")
        self.assertEqual(
            numbers["arch.ladder.q64.clang.cse"]["value"],
            cross_machine["hosts"]["clang_epyc_9575f"]["query_counts"]["64"]
            ["speedup_over_r2"]["cse_flat_bigint"]["case_cluster_geomean_speedup"],
        )
        self.assertFalse(current["query_ladder"]["absolute_cross_host_timing_comparison_permitted"])
        self.assertFalse(current["query_ladder"]["memory_router_calibration_permitted"])

        task_rows = {row["task"]: row for row in current["small_queries"]["rows"]}
        self.assertEqual(task_rows["exact_count/fresh_engine"]["winner"], "cnf/fresh_engine")
        self.assertEqual(task_rows["sat_status/resident_engine"]["winner"], "sat/resident_engine")
        for row in current["native_portability"]["rows"] + current["query_ladder"]["rows"] + current["small_queries"]["rows"]:
            for key, value in row.items():
                if key.endswith("_token"):
                    self.assertIn(value, numbers, (key, value))

        expert = (SITE / "cm_expert_template.html").read_text(encoding="utf-8")
        self.assertIn('section("x0", "Current", "Current architecture task map — 2026-09-04"', expert)
        self.assertIn("{{arch.native.windows.single}}", expert)
        self.assertIn("CSE-flat and direct BitSet are comparison controls, not CM-family members", expert)
        self.assertIn("No neural training or selector fit was performed", expert)

    def test_master_focuses_top_navigation_and_keeps_specialist_views_at_bottom(self):
        template = (SITE / "cm_master_template.html").read_text(encoding="utf-8")
        top = template.split("/* headline tiles", 1)[0]
        bottom = template.split("/* ============================================================ SECTION 8 */", 1)[1]
        self.assertIn('"Simple One-Pager"', top)
        self.assertIn('"CM Use Cases"', top)
        self.assertIn('"Results & audit"', top)
        self.assertNotIn('"Investor Brief"', top)
        self.assertNotIn('"Technical Summary"', top)
        self.assertIn('"Investor Brief"', bottom)
        self.assertIn('"Technical Summary"', bottom)

    def test_github_pages_routes_evidence_files_to_the_repository(self):
        shared = (SITE / "cm_master_shared.js").read_text(encoding="utf-8")
        self.assertIn("function hostedEvidenceHref(href)", shared)
        self.assertIn("https://github.com/Relative0/Correspondence_Matrices/blob/main/", shared)
        self.assertIn('t === "a" && k === "href"', shared)

    def test_decision_atlas_has_five_independent_why_dialogs(self):
        shared = (SITE / "cm_master_shared.js").read_text(encoding="utf-8")
        atlas = shared.split("FIG.decisionAtlas = () => {", 1)[1].split("FIG.assignmentGrowth", 1)[0]
        self.assertIn('class: "analysis-dialog decision-dialog"', shared)
        self.assertIn('visualOwnInteraction: true', atlas)
        self.assertIn('["Why", it.why]', shared)
        self.assertEqual(len(re.findall(r"\bwhy:", atlas)), 5)
        self.assertIn('table(["situation", "answer", "evidence signal", "why"]', atlas)
        self.assertIn('answer: "CUDD for the canonical graph"', atlas)
        self.assertIn("the CM kernel was", atlas)
        self.assertIn("labels its performance provisional", atlas)
        self.assertNotIn('answer: "Use CUDD"', atlas)

        canonical = next(item for item in self.content["scenarios"]["items"] if item["id"] == "sc-canonical")
        self.assertIn("canonical ROBDD", canonical["verdict"])
        self.assertIn("fresh-manager timing is not a CUDD speed win", canonical["technical"][0])
        self.assertIn("CM the measured winner over CUDD for that endpoint", canonical["technical"][1])
        self.assertIn("performance provisional", canonical["technical"][3])

        for name in ("index.html", "layperson.html"):
            text = (SITE / name).read_text(encoding="utf-8")
            self.assertIn("Evidence, why, and boundary", text, name)
            self.assertIn("CUDD for the canonical graph", text, name)

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
