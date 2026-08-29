from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cm_exprlib import And, Eqv, Not, Or, Var, Xor
from cmbench.recognition.computation_experiment import (
    EXACT_BACKENDS, ComputationCase, ComputationConfig, ComputationTask,
    TaskCostPolicy, exact_motif_candidate, fit_task_policy, load_epfl_d_cases,
    make_workload, measure_task, output_sha256, prepare_task, reference_task,
    run_computation_experiment, task_specs,
)
from cmbench.recognition.teacher import teach


class TaskComputationBackendTests(unittest.TestCase):
    def expressions(self):
        mux = Or(And(Var(0), Var(1)), And(Not(Var(0)), Var(2)))
        majority = Or(Or(And(Var(0), Var(1)), And(Var(0), Var(2))), And(Var(1), Var(2)))
        shared = Xor(And(Var(0), Var(1)), Eqv(Var(2), Var(3)))
        return (mux, majority, shared)

    def test_all_exact_backends_match_independent_task_contracts(self):
        for expr_index, expr in enumerate(self.expressions()):
            for task in task_specs(4):
                workload = make_workload(f"case-{expr_index}", task)
                expected = reference_task(expr, task, workload)
                for backend in EXACT_BACKENDS:
                    with self.subTest(expr=expr_index, task=task.task_id, backend=backend):
                        _build_ns, run = prepare_task(backend, expr, task, workload)
                        self.assertEqual(run(), expected)

    def test_explicit_cm_is_construction_not_cm_ir_alias(self):
        expr = Xor(Var(0), Var(1))
        task = ComputationTask("complete_vector", 1)
        workload = make_workload("cm", task)
        _build_ns, run = prepare_task("explicit_cm", expr, task, workload)
        self.assertEqual(run(), (teach(expr, 8).bits,))
        with self.assertRaises(ValueError):
            prepare_task("cm", expr, task, workload)

    def test_affine_mux_and_majority_candidates_are_exact(self):
        expressions = {
            "affine": Xor(Xor(Var(0), Var(1)), Var(2)),
            "mux3": Or(And(Var(0), Var(1)), And(Not(Var(0)), Var(2))),
            "majority3": Or(Or(And(Var(0), Var(1)), And(Var(0), Var(2))), And(Var(1), Var(2))),
        }
        for kind, expr in expressions.items():
            candidate, actual_kind = exact_motif_candidate(teach(expr, 8))
            self.assertEqual(actual_kind, kind)
            self.assertEqual(teach(candidate, 8).bits, teach(expr, 8).bits)


class TaskCostPolicyTests(unittest.TestCase):
    def rows(self):
        rows = []
        for case_id in ("a", "b"):
            for task in task_specs():
                costs = {"direct": 10, "cse": 20, "cm_ir": 30, "explicit_cm": 40}
                if task.kind in ("partial_restriction", "repeated_vector"):
                    costs.update(direct=30, cse=10)
                for arm, total_ns in costs.items():
                    rows.append({"case_id": case_id, "task_id": task.task_id,
                                 "arm": arm, "status": "ok", "total_ns": total_ns})
        return rows

    def test_fit_save_reload_and_tamper_rejection(self):
        policy = fit_task_policy(self.rows())
        self.assertEqual(policy.select(ComputationTask("single_assignment", 8))[0], "direct")
        self.assertEqual(policy.select(ComputationTask("partial_restriction", 8))[0], "cse")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "policy.json"
            policy.save(path)
            self.assertEqual(TaskCostPolicy.load(path).to_dict(), policy.to_dict())
            document = json.loads(path.read_text(encoding="utf-8"))
            document["cells"][next(iter(document["cells"]))]["selected"] = "cm_ir"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(ValueError):
                TaskCostPolicy.load(path)

    def test_learned_bypass_does_not_call_policy(self):
        expr = Xor(Var(0), Var(1))
        case = ComputationCase("bypass", "test", "affine", "generated:test", expr,
                               {"version": 2, "nodes": [], "root": 0})
        task = ComputationTask("single_assignment", 8)
        workload = make_workload(case.case_id, task)
        expected = reference_task(expr, task, workload)
        policy = fit_task_policy(self.rows())
        row = measure_task(case, task, workload, expected, "learned_router",
                           ComputationConfig(parent_counts=(2, 1, 1, 1), rounds=1,
                                             epfl_limit=1, learned_enabled=False),
                           policy, 0)
        self.assertEqual(row["model_calls"], 0)
        self.assertEqual(row["selection_reason"], "learned_disabled")
        self.assertEqual(row["mismatches"], 0)


class MilestoneDExperimentTests(unittest.TestCase):
    def test_register_and_machine_summary_preserve_full_agenda(self):
        root = Path(__file__).resolve().parents[1]
        register = json.loads((root / "docs/recognition/experiment_register.json").read_text(encoding="utf-8"))
        self.assertEqual([track["id"] for track in register["tracks"]], [f"R{i:02d}" for i in range(1, 19)])
        self.assertEqual(len(register["applications"]), 8)
        recorded = {track["id"] for track in register["tracks"]
                    if any(result.get("report") == "LEARNING_MILESTONE_D_2026_08_29.md"
                           for result in track["results"])}
        self.assertEqual(recorded, {"R01", "R03", "R04", "R06", "R09", "R13", "R16", "R18"})
        summary = json.loads((root / "docs/recognition/learning_milestone_d_results.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["semantic_mismatches"], 0)
        self.assertEqual(summary["row_counts"]["training"] + summary["row_counts"]["evaluation"], 7040)
        self.assertFalse(any(summary["promotion"].values()))

    def test_epfl_d_slice_excludes_milestone_c_and_is_exact(self):
        cases, manifest = load_epfl_d_cases(4)
        self.assertEqual(len(cases), 4)
        self.assertFalse(set(manifest["selected_ids"]) & set(manifest["prior_milestone_c_ids_excluded"]))
        self.assertFalse(manifest["training_use"])
        for case in cases:
            task = ComputationTask("complete_vector", 1)
            expected = reference_task(case.expr, task, make_workload(case.case_id, task))
            self.assertEqual(output_sha256(expected), output_sha256((teach(case.expr, 8).bits,)))

    def test_small_complete_pipeline_retains_exact_artifacts(self):
        config = ComputationConfig(data_seed=71, parent_counts=(2, 1, 1, 1),
                                   rounds=1, epfl_limit=2, max_seconds=60)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "run"
            result = run_computation_experiment(config, output, progress=lambda _message: None)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["semantic_mismatches"], 0)
            self.assertEqual(result["failed_rows"], 0)
            self.assertTrue(result["source_unchanged"])
            self.assertEqual(result["learned_bypass"]["model_calls"], 0)
            self.assertEqual(result["learned_bypass"]["output_mismatches"], 0)
            self.assertEqual(result["row_counts"]["training"], 2 * 2 * 10 * 4)
            self.assertEqual(result["row_counts"]["evaluation"], (2 * 3 + 2) * 10 * 8)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "complete")
            self.assertIn("task_router.json", manifest["files_sha256"])
            self.assertTrue((output / "report.md").is_file())
            from scripts.crse_computation_verify import main as verify
            verification = Path(temp) / "verification.json"
            self.assertEqual(verify([str(output), "--output", str(verification)]), 0)
            self.assertEqual(json.loads(verification.read_text(encoding="utf-8"))["status"], "pass")


if __name__ == "__main__":
    unittest.main()
