"""Independent arithmetic audit of saved results; no timing or model execution."""

import json
import statistics
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deliverables_n22_24/master_explainer_2026_08_03"
Q64 = ROOT / "docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class NeuralPublicationNumericAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read(SITE / "cm_master_data_2026_08_03.json")
        cls.numbers = cls.data["_numbers"]

    def value(self, key):
        return self.numbers[key]["value"]

    def cells(self, path, expected):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), expected)
        seen = set()
        for row in rows:
            identity = (row["case_id"], row["query_count"], row["arm"], row["block"])
            self.assertNotIn(identity, seen)
            seen.add(identity)
            self.assertEqual(row["status"], "ok")
            self.assertTrue(row["exact_check_passed"])
            self.assertFalse(row["fresh_process_lifecycle_in_accounted_total"])
            timings = row["timings_ns"]
            self.assertEqual(timings["accounted_total_ns"], sum(v for k, v in timings.items() if k != "accounted_total_ns"))
            self.assertIn("cleanup_ns", timings)
        return rows

    def test_q64_gross_and_charged_ratios_from_all_raw_cells(self):
        replay = read(Q64 / "STDLIB_SUMMARY_REPLAY.json")
        for host, prefix in (("windows-physical-001", "windows_q64"), ("physical-002", "linux_q64")):
            groups = defaultdict(list)
            for row in self.cells(Q64 / host / "RAW.jsonl", 9216):
                groups[row["case_id"], row["arm"]].append(row["timings_ns"]["accounted_total_ns"])
            self.assertEqual(len(groups), 72 * 8)
            self.assertTrue(all(len(rows) == 16 for rows in groups.values()))
            medians = {key: statistics.median(rows) for key, rows in groups.items()}
            cases = {case for case, _ in groups}
            arms = {arm for _, arm in groups}
            totals = {arm: sum(medians[case, arm] for case in cases) for arm in arms}
            fixed = min(totals.values())
            oracle = sum(min(medians[case, arm] for arm in arms) for case in cases)
            economics = replay["surface"]["economics_by_host"][host]
            charges = sum(economics["p95_costs_ns_per_case"].values())
            self.assertEqual(fixed, economics["best_fixed_sum_ns"])
            self.assertEqual(oracle, economics["oracle_sum_ns"])
            self.assertAlmostEqual(fixed / oracle, self.value(f"ln.{prefix}_gross"))
            self.assertAlmostEqual(fixed / (oracle + len(cases) * charges), self.value(f"ln.{prefix}_fully_charged"))

    def test_batch_sum_ratios_and_wins_from_all_raw_cells(self):
        groups = defaultdict(list)
        path = ROOT / "docs/audits/2026-09-11-cm-continuation/native-run/RAW.jsonl"
        for row in self.cells(path, 2592):
            groups[row["query_count"], row["case_id"], row["arm"]].append(row["timings_ns"]["accounted_total_ns"])
        self.assertTrue(all(len(rows) == 12 for rows in groups.values()))
        for q in (8, 32, 96):
            scalar, batch = [], []
            for case in sorted({case for count, case, _ in groups if count == q}):
                scalar.append(statistics.median(groups[q, case, "native_scalar_v1"]))
                batch.append(statistics.median(groups[q, case, "native_batch_v1"]))
            self.assertEqual(len(scalar), 36)
            self.assertAlmostEqual(sum(scalar) / sum(batch), self.value(f"ln.batch_q{q}_speedup"))
            self.assertEqual(sum(b < a for a, b in zip(scalar, batch)), self.value(f"ln.batch_q{q}_wins"))

    def test_positive_c6_graph_values_are_summary_ratios(self):
        result = read(ROOT / "docs/recognition/learning_milestone_c6_packed_source_anf_results.json")
        for split in ("test", "confirmatory"):
            baseline = result["method_summary"][f"truth_vector_anf/{split}"]
            candidate = result["method_summary"][f"cached_packed_source_anf/{split}"]
            for metric in ("median", "p95"):
                self.assertAlmostEqual(baseline[f"{metric}_total_ns"] / candidate[f"{metric}_total_ns"], self.value(f"ln.c6.{split}.{metric}_speedup"))
        self.assertFalse(result["criteria"]["production_promotion"])

    def test_c16_confirmation_and_graph_bindings(self):
        result = read(ROOT / "docs/recognition/c16_linux_confirmation/RUNPOD_C16_PACKAGE_V2_FINAL_VERIFICATION_20260831.json")
        totals = result["median_case_sum_ns"]
        ratio = totals["explicit_cm_exhaustive"]["total_ns"] / totals["explicit_cm_screened"]["total_ns"]
        self.assertAlmostEqual(ratio, self.value("recognition.c16.linux_whole_path_speedup"))
        template = (SITE / "cm_learning_neural_template.html").read_text(encoding="utf-8")
        self.assertIn('"data-evidence-token": key', template)
        self.assertIn('"data-evidence-value": String(value)', template)
        self.assertIn("not percentiles of paired speedups", template)


if __name__ == "__main__":
    unittest.main()
