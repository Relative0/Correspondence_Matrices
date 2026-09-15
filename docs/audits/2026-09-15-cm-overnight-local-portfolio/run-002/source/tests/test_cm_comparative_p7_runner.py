from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from cmbench.comparative import linux_supervisor, p7_runner
from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.evidence import append_record


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json"


class ComparativeP7RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.freeze = json.loads(FREEZE.read_text(encoding="utf-8"))

    def plan(self):
        limits = linux_supervisor.Limits()
        return p7_runner.build_plan(
            self.freeze,
            policy_id="p7-ir",
            roles=("development",),
            blocks=1,
            worker_source_manifest_sha256="a" * 64,
            resource_limits=p7_runner.limits_record(limits),
            case_limit=1,
            profile="functional",
        )

    def oracle_data(self, plan):
        package = p7_runner.oracle_package(plan, self.freeze, ROOT)
        return package, p7_runner.validate_oracle_package(package, plan)

    def test_functional_plan_preserves_frozen_order_and_performance_requires_full_cycle(self):
        plan = self.plan()
        self.assertEqual(len(plan["case_ids"]), 1)
        self.assertEqual(len(plan["cells"]), 4)
        self.assertFalse(plan["performance_measurement"])
        self.assertEqual([row["arm"] for row in plan["cells"]], [
            "cm-ir-two-memo", "cm-cse-flat", "cm-raw-flat", "cm-ir-current",
        ])
        p7_runner.validate_plan(plan, self.freeze)
        with self.assertRaises(ValueError):
            p7_runner.build_plan(
                self.freeze, policy_id="p7-ir", roles=("development",),
                blocks=1, worker_source_manifest_sha256="a" * 64,
                resource_limits=p7_runner.limits_record(linux_supervisor.Limits()),
                case_limit=1, profile="performance",
            )
        performance = p7_runner.build_plan(
            self.freeze, policy_id="p7-ir", roles=("development",),
            blocks=8, worker_source_manifest_sha256="a" * 64,
            resource_limits=p7_runner.limits_record(linux_supervisor.Limits()),
            case_limit=1, profile="performance",
        )
        self.assertEqual(len(performance["cells"]), 32)
        self.assertTrue(performance["performance_measurement"])
        self.assertFalse(any(row["conditional_extension"] for row in performance["cells"]))
        cell = plan["cells"][0]
        frozen_case = next(row for row in self.freeze["cases"] if row["case_id"] == cell["case_id"])
        self.assertEqual(cell["source_sha256"], frozen_case["source"]["sha256"])
        self.assertEqual(cell["lifecycle"], "fresh_process")
        self.assertEqual(cell["affinity_class"], "one-admitted-cpu")
        self.assertEqual(cell["worker_source_manifest_sha256"], "a" * 64)
        self.assertEqual(len(cell["configuration_sha256"]), 64)
        self.assertEqual(len(cell["output_contract_sha256"]), 64)

    def _fake_supervisor(self, mutate=None):
        def supervise(_command, *, input, cwd, limits):
            request = p7_runner.strict_json(input, limit=p7_runner.MAX_REQUEST_BYTES)
            worker = p7_runner.execute_worker(
                request, self.freeze, Path(cwd), clock=iter(range(1_000_000)).__next__,
            )
            if mutate is not None:
                mutate(worker)
            return linux_supervisor.Result(
                "ok", "completed", returncode=0,
                stdout=canonical_bytes(worker) + b"\n", stderr=b"", wall_ns=123456,
                resources={
                    "cleanup_verified": True, "streams_closed": True,
                    "whole_tree_rss_measured": True,
                    "peak_sampled_tree_rss_bytes": 1234,
                },
            )
        return supervise

    def test_cell_success_is_exact_and_validation_is_outside_timed_span(self):
        plan = self.plan()
        cell = plan["cells"][0]
        _package, oracles = self.oracle_data(plan)
        oracle = oracles[cell["case_id"]]
        result, request = p7_runner.execute_cell(
            plan=plan, cell=cell, oracle=oracle,
            python=Path(__file__), worker_program=Path(__file__), project_root=ROOT,
            freeze_path=FREEZE, limits=linux_supervisor.Limits(),
            supervise=self._fake_supervisor(),
        )
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["outside_span_validation"])
        self.assertEqual(result["worker"]["semantic_sha256"], oracle["result_sha256"])
        self.assertTrue(result["worker"]["source_preparation_in_timed_span"])
        self.assertGreater(result["timings_ns"]["task_total_wall_ns"], 0)
        self.assertEqual(result["process_tree_peak_rss_bytes"], 1234)
        self.assertEqual(len(request["request_sha256"]), 64)

    def test_complete_relation_worker_uses_fresh_process_contract_and_exact_oracle(self):
        plan = p7_runner.build_plan(
            self.freeze,
            policy_id="p7-relation",
            roles=("development",),
            blocks=1,
            worker_source_manifest_sha256="a" * 64,
            resource_limits=p7_runner.limits_record(linux_supervisor.Limits()),
            case_limit=1,
            profile="functional",
        )
        cell = plan["cells"][0]
        _package, oracles = self.oracle_data(plan)
        oracle = oracles[cell["case_id"]]
        result, _ = p7_runner.execute_cell(
            plan=plan, cell=cell, oracle=oracle,
            python=Path(__file__), worker_program=Path(__file__), project_root=ROOT,
            freeze_path=FREEZE, limits=linux_supervisor.Limits(),
            supervise=self._fake_supervisor(),
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["worker"]["semantic_sha256"], oracle["result_sha256"])
        self.assertIn(result["worker"]["artifact_kind"],
                      {"dense_cm", "packed_bigint", "packed_words"})

    def test_mismatch_timeout_and_cleanup_fail_closed(self):
        plan = self.plan()
        cell = plan["cells"][0]
        _package, oracles = self.oracle_data(plan)
        oracle = oracles[cell["case_id"]]

        def mismatch(worker):
            worker["semantic_sha256"] = "0" * 64

        result, _ = p7_runner.execute_cell(
            plan=plan, cell=cell, oracle=oracle,
            python=Path(__file__), worker_program=Path(__file__), project_root=ROOT,
            freeze_path=FREEZE, limits=linux_supervisor.Limits(),
            supervise=self._fake_supervisor(mismatch),
        )
        self.assertEqual((result["status"], result["reason"]),
                         ("mismatch", "outside_span_scalar_oracle_mismatch"))

        for supervised, expected in (
            (linux_supervisor.Result(
                "refused", "linux_proc_process_group_unavailable", wall_ns=1,
                resources={"cleanup_verified": True, "streams_closed": True}), "refused"),
            (linux_supervisor.Result(
                "timeout", "worker_deadline", wall_ns=1,
                resources={"cleanup_verified": True, "streams_closed": True}), "timeout"),
            (linux_supervisor.Result(
                "ok", "completed", stdout=b"{}", wall_ns=1,
                resources={"cleanup_verified": False, "streams_closed": True}), "error"),
        ):
            with self.subTest(expected=expected):
                result, _ = p7_runner.execute_cell(
                    plan=plan, cell=cell, oracle=oracle,
                    python=Path(__file__), worker_program=Path(__file__), project_root=ROOT,
                    freeze_path=FREEZE, limits=linux_supervisor.Limits(),
                    supervise=lambda *_args, **_kwargs: supervised,
                )
                self.assertEqual(result["status"], expected)

    def test_segmented_resume_preserves_interrupted_attempt_and_retries_exact_request(self):
        cell = self.plan()["cells"][0]
        with tempfile.TemporaryDirectory(prefix="cm-p7-ledger-") as directory:
            root = Path(directory)
            first = p7_runner.new_segment(root)
            append_record(first, {
                "cell_id": cell["cell_id"], "request_sha256": "1" * 64,
                "attempt": 1, "status": "running",
            })
            second = p7_runner.new_segment(root)
            recovered = p7_runner.recover_interrupted(p7_runner.read_segments(root), second)
            self.assertEqual(recovered, [cell["cell_id"]])
            append_record(second, {
                "cell_id": cell["cell_id"], "request_sha256": "1" * 64,
                "attempt": 2, "status": "running",
            })
            append_record(second, {
                "cell_id": cell["cell_id"], "request_sha256": "1" * 64,
                "attempt": 2, "status": "ok", "reason": "completed",
            })
            state = p7_runner.read_segments(root)
        self.assertEqual([row["status"] for row in state["histories"][cell["cell_id"]]],
                         ["running", "error", "running", "ok"])
        self.assertEqual(state["latest"][cell["cell_id"]]["attempt"], 2)

    def test_successful_ledger_state_requires_primary_metrics_cleanup_and_oracle_identity(self):
        plan = self.plan()
        cell = plan["cells"][0]
        package, oracles = self.oracle_data(plan)
        oracle = oracles[cell["case_id"]]
        result, request = p7_runner.execute_cell(
            plan=plan, cell=cell, oracle=oracle,
            python=Path(__file__), worker_program=Path(__file__), project_root=ROOT,
            freeze_path=FREEZE, limits=linux_supervisor.Limits(),
            supervise=self._fake_supervisor(),
        )
        history = [{
            "cell_id": cell["cell_id"], "request_sha256": request["request_sha256"],
            "attempt": 1, "status": "running",
        }, {
            "cell_id": cell["cell_id"], "request_sha256": request["request_sha256"],
            "attempt": 1, "status": "ok", "reason": "completed", "result": result,
        }]
        state = {
            "histories": {cell["cell_id"]: history},
            "latest": {cell["cell_id"]: history[-1]},
            "partial_tail_segments": [],
        }
        p7_runner.validate_state(plan, state, package)
        result["process_tree_peak_rss_bytes"] = 0
        with self.assertRaises(ValueError):
            p7_runner.validate_state(plan, state, package)

    def test_worker_refuses_extra_and_forged_identity_before_loading_source(self):
        plan = self.plan()
        cell = plan["cells"][0]
        _package, oracles = self.oracle_data(plan)
        request = p7_runner.request_for(plan, cell, oracles[cell["case_id"]])
        with mock.patch.object(p7_runner.p7, "load_case_expression") as load:
            with self.assertRaises(ValueError):
                p7_runner.execute_worker({**request, "extra": True}, self.freeze, ROOT)
            forged = json.loads(json.dumps(request))
            forged["cell"]["configuration_sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                p7_runner.execute_worker(forged, self.freeze, ROOT)
            load.assert_not_called()

    def test_source_preparation_occurs_after_measured_span_starts(self):
        plan = self.plan()
        cell = plan["cells"][0]
        _package, oracles = self.oracle_data(plan)
        request = p7_runner.request_for(plan, cell, oracles[cell["case_id"]])
        ticks = []

        def clock():
            ticks.append(len(ticks))
            return ticks[-1]

        original = p7_runner.p7.load_case_expression

        def checked_load(*args, **kwargs):
            self.assertGreaterEqual(len(ticks), 1)
            return original(*args, **kwargs)

        with mock.patch.object(p7_runner.p7, "load_case_expression", side_effect=checked_load):
            worker = p7_runner.execute_worker(request, self.freeze, ROOT, clock=clock)
        self.assertTrue(worker["source_preparation_in_timed_span"])
        self.assertGreater(worker["timings_ns"]["task_total_wall_ns"], 0)

    def test_strict_json_and_worker_output_reject_ambiguity(self):
        for payload in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":'):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    p7_runner.strict_json(payload, limit=1024)
        plan = self.plan()
        cell = plan["cells"][0]
        _package, oracles = self.oracle_data(plan)
        request = p7_runner.request_for(plan, cell, oracles[cell["case_id"]])
        for payload in (b'{}', b'{"schema":NaN}', b'{"schema":"x","schema":"y"}'):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    p7_runner.validate_worker(payload, request)

    def test_resource_profile_mismatch_refuses_before_supervisor(self):
        plan = self.plan()
        cell = plan["cells"][0]
        _package, oracles = self.oracle_data(plan)
        called = False

        def supervise(*_args, **_kwargs):
            nonlocal called
            called = True
            raise AssertionError("supervisor must not run")

        with self.assertRaises(ValueError):
            p7_runner.execute_cell(
                plan=plan, cell=cell, oracle=oracles[cell["case_id"]],
                python=Path(__file__), worker_program=Path(__file__), project_root=ROOT,
                freeze_path=FREEZE,
                limits=linux_supervisor.Limits(timeout_seconds=16),
                supervise=supervise,
            )
        self.assertFalse(called)

    def test_oracle_package_is_source_bound_and_tamper_evident(self):
        plan = self.plan()
        package, rows = self.oracle_data(plan)
        cell = plan["cells"][0]
        oracle = rows[cell["case_id"]]
        self.assertEqual(oracle["source_sha256"], cell["source_sha256"])
        self.assertEqual(oracle["case_sha256"], cell["case_sha256"])
        tampered = json.loads(json.dumps(package))
        tampered["cases"][0]["result_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            p7_runner.validate_oracle_package(tampered, plan)

    def test_partial_tail_cannot_be_hidden_by_a_later_segment(self):
        with tempfile.TemporaryDirectory(prefix="cm-p7-partial-") as directory:
            root = Path(directory)
            first = p7_runner.new_segment(root)
            first.write_bytes(b'{"cell_id":"partial"')
            p7_runner.new_segment(root)
            with self.assertRaises(ValueError):
                p7_runner.read_segments(root)

    def test_worker_cli_accepts_one_bounded_request_and_emits_one_result(self):
        plan = self.plan()
        cell = plan["cells"][0]
        _package, oracles = self.oracle_data(plan)
        request = p7_runner.request_for(plan, cell, oracles[cell["case_id"]])
        completed = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/cm_comparative_p7_runner.py"), "worker",
             "--project-root", str(ROOT), "--freeze", str(FREEZE)],
            input=canonical_bytes(request),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode(errors="replace"))
        worker = p7_runner.validate_worker(completed.stdout, request)
        self.assertEqual(worker["semantic_sha256"], oracles[cell["case_id"]]["result_sha256"])


if __name__ == "__main__":
    unittest.main()
