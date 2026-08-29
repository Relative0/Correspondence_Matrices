"""Adversarial v2 measurement contracts; tiny local fixtures, no cloud jobs."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import cm_measurement_verify as verify
from scripts import cm_process_supervisor as supervisor


class MeasurementProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cm-contract-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = self.root / "cells.jsonl"
        self.request = {"mode": "measure", "arm": "cnf", "case": {"k": 1, "clauses": [[1]]}}
        self.good = verify.measure(self.request["case"], "cnf")
        self.good.update(pid=123, interpreter=sys.executable, source_root=str(self.root),
                         request_sha256=verify.digest(self.request))

    def test_valid_current_worker_fields_are_accepted_for_all_arms(self):
        for arm in verify.ARMS:
            for k in (0, 1, 6, 8):
                request = {"mode": "measure", "arm": arm, "case": {"k": k, "clauses": []}, "warm_rounds": 1}
                result = verify.worker(request)
                self.assertEqual(verify.validate_result(result, request, verify.ROOT), verify.scalar_vector(request["case"]))

    def test_request_rejects_unknown_modes_fields_widths_and_rounds(self):
        variants = [None, {}, {"mode": "test"}, {**self.request, "arm": "cudd"},
                    {**self.request, "extra": "ignored?"}, {**self.request, "case": {"k": 9, "clauses": []}}]
        variants += [{**self.request, "warm_rounds": x} for x in (0, 13, True, 1.0, "6")]
        for request in variants:
            with self.subTest(request=request), self.assertRaises(ValueError):
                verify.validate_request(request)

    def test_invalid_request_never_invokes_worker(self):
        with patch.object(verify.subprocess, "run") as invoke:
            row = verify.run_cell(self.root, self.ledger, "invalid", {"mode": "test"}, 1, invoke=invoke)
        self.assertEqual(row["status"], "error")
        invoke.assert_not_called()
        self.assertFalse(verify.read_ledger(self.ledger)["unfinished"])

    def supervised(self, pids=(123,), status="ok", cleanup=True):
        return supervisor.Result(status, "test_reason", returncode=0, stdout=verify.encoded(self.good), pid=100,
                                 resources={"cleanup_verified": cleanup, "streams_closed": True,
                                            "attached_before_resume": True, "observed_job_pids": list(pids)})

    def test_supervised_worker_pid_can_differ_from_launcher_but_must_be_observed(self):
        for number, pids in enumerate(((100, 123), (100,))):
            with patch.object(supervisor, "run", return_value=self.supervised(pids)):
                row = verify.run_cell(self.root, self.ledger, str(number), self.request, 2)
            self.assertEqual(row["status"], "ok" if 123 in pids else "error")
            self.assertEqual(row.get("worker_pid_observed_in_owned_job", False), 123 in pids)

    def test_supervisor_outcomes_and_unverified_cleanup_cannot_become_success(self):
        for number, status in enumerate(("refused", "timeout", "output_limit", "error", "unknown")):
            with patch.object(supervisor, "run", return_value=self.supervised(status=status)):
                row = verify.run_cell(self.root, self.ledger, str(number), self.request, 2)
            self.assertEqual(row["status"], status if status in {"refused", "timeout"} else "error")
        with patch.object(supervisor, "run", return_value=self.supervised(cleanup=False)):
            row = verify.run_cell(self.root, self.ledger, "cleanup", self.request, 2)
        self.assertEqual(row["status"], "error")

    def test_every_result_field_is_required_and_unknown_fields_refused(self):
        for field in self.good:
            result = dict(self.good)
            del result[field]
            with self.subTest(field=field), self.assertRaises((ValueError, KeyError)):
                verify.validate_result(result, self.request, self.root)
        with self.assertRaises(ValueError):
            verify.validate_result({**self.good, "unaccounted_phase_ns": 1}, self.request, self.root)

    def test_identity_and_output_contract_mutations_are_refused(self):
        changes = {"schema": "cm-measurement-contract-cell/v1", "arm": "cm", "task": "exact_count",
                   "k": True, "case_sha256": "0" * 64, "request_sha256": "0" * 64,
                   "source_root": "elsewhere", "interpreter": "other-python", "pid": True,
                   "output_cache_used": True, "zero_width_adapter": True,
                   "kernel": "numpy_words", "timings_for_contract_diagnostics_only": False,
                   "artifact": {"cached": "0x2"}}
        for field, value in changes.items():
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify.validate_result({**self.good, field: value}, self.request, self.root)

    def test_packed_output_is_canonical_and_bounded_before_integer_parsing(self):
        for value in (None, 2, "0X2", "0x02", "-0x1", "0x+2", "0xf", "0x" + "f" * 10000):
            with self.subTest(value=str(value)[:20]), self.assertRaises(ValueError):
                verify.validate_result({**self.good, "packed_hex": value}, self.request, self.root)

    def test_bad_warm_samples_and_phase_totals_are_refused(self):
        for value in (None, [], [0] * 5, [0] * 7, [True] * 6, [-1] * 6, [1.5] * 6,
                      [float("nan")] * 6, [verify.MAX_TIMING_NS + 1] * 6):
            with self.subTest(value=value), self.assertRaises(ValueError):
                verify.validate_result({**self.good, "warm_recompute_ns": value}, self.request, self.root)
        for field in ("cold_prepare_ns", "cold_first_execution_ns", "cold_total_ns"):
            for value in (-1, True, 1.0, verify.MAX_TIMING_NS + 1):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    verify.validate_result({**self.good, field: value}, self.request, self.root)
        with self.assertRaisesRegex(ValueError, "phase accounting"):
            verify.validate_result({**self.good, "cold_total_ns": self.good["cold_total_ns"] + 1}, self.request, self.root)

    def reload_fixture(self):
        frozen = self.root / "source_snapshot"
        frozen.mkdir()
        artifacts = self.root / "artifacts"
        artifacts.mkdir()
        program = verify.prepare({"k": 1, "clauses": [[1]]}, "cm")[1]
        raw = verify.encoded(verify.export_flat(program, 1)) + b"\n"
        path = artifacts / "cell-1-artifact.json"
        path.write_bytes(raw)
        request = {"mode": "reload", "artifact_file": path.name,
                   "artifact_sha256": hashlib.sha256(raw).hexdigest(), "k": 1, "arm": "cm"}
        return frozen, path, request

    def test_reload_checks_exact_artifact_identity_before_execution(self):
        frozen, path, request = self.reload_fixture()
        with patch.object(verify, "ROOT", frozen):
            result = verify.worker(request)
            self.assertEqual(verify.validate_result(result, request, frozen), 2)
            path.write_bytes(path.read_bytes() + b" ")
            with patch.object(verify, "execute_flat") as execute, self.assertRaisesRegex(ValueError, "identity changed"):
                verify.worker(request)
            execute.assert_not_called()

    def test_reload_universe_and_all_phase_fields_are_checked(self):
        frozen, _path, request = self.reload_fixture()
        with patch.object(verify, "ROOT", frozen):
            result = verify.worker(request)
        changes = {"artifact_sha256": "0" * 64, "k": 0, "arm": "cse", "cached_answer_used": True,
                   "os_file_cache": "cold", "reload_total_ns": result["reload_total_ns"] + 1,
                   "file_read_decode_ns": True, "reconstruct_ns": -1, "first_query_ns": "1"}
        for field, value in changes.items():
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify.validate_result({**result, field: value}, request, frozen)
        for field in result:
            changed = dict(result)
            del changed[field]
            with self.subTest(missing=field), self.assertRaises((ValueError, KeyError)):
                verify.validate_result(changed, request, frozen)

    def test_structurally_invalid_or_wrong_universe_artifact_is_refused(self):
        request = {**self.request, "arm": "cm"}
        result = verify.worker(request)
        for key, value in (("k", 0), ("root_slot", 100000), ("n_slots", True)):
            changed = copy.deepcopy(result)
            changed["artifact"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify.validate_result(changed, request, verify.ROOT)

    def test_duplicate_and_nonfinite_json_are_not_accepted(self):
        for raw in (b'{"status":"ok","status":"error"}', b'{"x":NaN}', b'{"x":Infinity}'):
            with self.assertRaises(ValueError):
                verify.strict_json(raw)

    def test_malformed_result_does_not_prevent_later_valid_cell(self):
        invalid = {**self.good, "warm_recompute_ns": [-1] * 6}
        for number, payload in enumerate((invalid, self.good)):
            fake = lambda *a, data=payload, **kw: subprocess.CompletedProcess([], 0, verify.encoded(data), b"")
            row = verify.run_cell(self.root, self.ledger, str(number), self.request, 2, invoke=fake)
            self.assertEqual(row["status"], "error" if number == 0 else "ok")
        self.assertEqual(len(verify.read_ledger(self.ledger)["cells"]), 2)

    def test_ledger_refuses_unknown_states_changed_requests_and_complete_corruption(self):
        variants = [b'{"cell_id":"a","status":"banana"}\n', b'broken\n',
                    b'{"cell_id":"a","status":"running","request_sha256":"a"}\n'
                    b'{"cell_id":"a","status":"ok","request_sha256":"b"}\n']
        for raw in variants:
            self.ledger.write_bytes(raw)
            with self.assertRaises(ValueError):
                verify.read_ledger(self.ledger)

    def test_schedule_retains_missing_unexpected_and_interrupted_cells(self):
        verify.append_record(self.ledger, {"cell_id": "a", "status": "running"})
        state = verify.read_ledger(self.ledger)
        result = verify.reconcile_schedule(state, [{"cell_id": "b"}])
        self.assertFalse(result["all_scheduled_cells_retained"])
        self.assertEqual(result["missing_cells"], ["b"])
        self.assertEqual(result["unexpected_cells"], ["a"])
        self.assertEqual(result["unfinished_cells"], ["a"])
        for scheduled in ([], [{"cell_id": "a"}, {"cell_id": "a"}]):
            with self.assertRaises(ValueError):
                verify.reconcile_schedule(state, scheduled)


if __name__ == "__main__":
    unittest.main()
