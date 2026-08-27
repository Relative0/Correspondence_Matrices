import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "deliverables_n22_24" / "master_explainer_2026_08_03" / "use_case_benchmarks_2026-08-27"
RUN2 = BENCHMARKS / "runs" / "hardware-epfl-context-pilot-2026-08-27-run2"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot = load_module("cm_epfl_context_pilot", BENCHMARKS / "cm_epfl_context_pilot.py")
pilot_audit = load_module("cm_epfl_context_pilot_audit", BENCHMARKS / "cm_epfl_context_pilot_audit.py")


class EPFLContextPilotTests(unittest.TestCase):
    def test_contexts_preserve_syntactic_axes_and_fix_only_semantic_inputs(self):
        record = next(
            item for item in pilot.load_records()
            if item["synt_support_size"] != item["sem_support_size"]
        )
        contexts = pilot.build_contexts(record)
        syntactic_names = {f"x{i}" for i in range(record["synt_support_size"])}
        semantic_original = set(record["sem_support_inputs"])
        semantic_names = {
            f"x{index}"
            for index, original in enumerate(record["synt_support_inputs"])
            if original in semantic_original
        }
        self.assertEqual(len(contexts), 13)
        for context in contexts:
            self.assertEqual(set(context["free"]) | set(context["fixed"]), syntactic_names)
            self.assertFalse(set(context["free"]) & set(context["fixed"]))
            self.assertLessEqual(set(context["fixed"]), semantic_names)

    def test_completed_repeat_passes_independent_reaggregation(self):
        result = pilot_audit.audit(RUN2)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["raw_rows"], 1677)
        self.assertEqual(result["formulas"], 129)
        self.assertEqual(result["packed_mismatches"], 0)
        self.assertTrue(result["construction_raw_reaggregated"])


if __name__ == "__main__":
    unittest.main()
