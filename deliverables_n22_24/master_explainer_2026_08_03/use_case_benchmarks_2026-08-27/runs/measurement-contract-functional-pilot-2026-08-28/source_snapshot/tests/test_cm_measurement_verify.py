"""Bounded functional and failure controls, not benchmark performance claims."""

import copy
import json
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from scripts import cm_measurement_verify as verify


class MeasurementVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = self.root / "cells.jsonl"

    def test_generated_cases_are_deterministic_and_cover_word_boundary(self):
        self.assertEqual(verify.fixtures(), verify.fixtures())
        self.assertEqual(len(verify.fixtures()), 37)
        self.assertEqual({case["k"] for case in verify.fixtures()}, {0, 1, 5, 6, 7, 8})

    def test_randomized_three_arm_agreement_and_independent_instruction_replay(self):
        auditor = verify.independent_auditor()
        for case in verify.fixtures():
            expected = verify.scalar_vector(case)
            for arm in verify.ARMS:
                with self.subTest(case=case["id"], arm=arm):
                    evaluate, program = verify.prepare(case, arm)
                    self.assertEqual(evaluate(), expected)
                    self.assertEqual(evaluate(), expected)
                    if program is not None:
                        artifact = verify.export_flat(program, case["k"])
                        self.assertEqual(auditor.replay_flat(artifact), expected)

    def test_reversed_clauses_and_duplicate_clauses_preserve_relation(self):
        for case in verify.fixtures():
            changed = {**case, "clauses": list(reversed(case["clauses"])) * 2}
            expected = verify.scalar_vector(case)
            for arm in verify.ARMS:
                self.assertEqual(verify.prepare(changed, arm)[0](), expected)

    def test_variable_permutation_matches_independent_assignment_mapping(self):
        for k in (1, 5, 6, 7, 8):
            case = {"id": "permutation", "k": k, "clauses": [[1, -k], [k]]}
            changed = {**case, "clauses": [[(1 if lit > 0 else -1) * (k + 1 - abs(lit))
                                           for lit in clause] for clause in case["clauses"]]}
            original = verify.scalar_vector(case)
            expected = sum(((original >> int(f"{a:0{k}b}"[::-1], 2)) & 1) << a for a in range(1 << k))
            for arm in verify.ARMS:
                self.assertEqual(verify.prepare(changed, arm)[0](), expected)

    def test_structural_reload_does_not_trust_cached_answer(self):
        for k in (0, 1, 5, 6, 7, 8):
            case = {"id": "reload", "k": k, "clauses": [] if k == 0 else [[1]]}
            for arm in ("cm", "cse"):
                program = verify.prepare(case, arm)[1]
                artifact = json.loads(verify.encoded(verify.export_flat(program, k)))
                artifact["packed_hex"] = "deliberately invalid cached answer"
                loaded, width = verify.import_flat(artifact)
                self.assertIsNone(loaded.word_plan)
                self.assertFalse(loaded.bound_cache)
                self.assertEqual(verify.execute_flat(loaded, width), verify.scalar_vector(case))

    def test_strict_reload_rejects_invalid_structure_before_execution(self):
        good = {"schema": "cm-flat-packed/v1", "k": 1, "n_slots": 2, "root_slot": 1,
                "loads": [[0, "var", "x0"]], "ops": [[1, 0, [0]]]}
        variants = []
        for key, value in (("k", 100000), ("k", True), ("n_slots", 10**20), ("root_slot", -1), ("schema", "unknown")):
            variants.append({**good, key: value})
        for operation in ([1, 9, [0]], [1, 0, [1]], [0, 0, [0]], [1, 0, [0, 0]], [1, 4, [0]]):
            variants.append({**good, "ops": [operation]})
        variants.extend(({**good, "loads": [[0, "var", "x2"]]},
                         {**good, "loads": [[0, "const", 2]]}, {**good, "ops": []}))
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                verify.import_flat(variant)

    def test_case_limits_refuse_before_large_allocation(self):
        for case in ({"k": 1000000, "clauses": []}, {"k": True, "clauses": []},
                     {"k": 1, "clauses": [[0]]}, {"k": 1, "clauses": [[True]]},
                     {"k": 0, "clauses": [[1]]}, {"k": 1, "clauses": [[]] * 129}):
            with self.assertRaises(ValueError):
                verify.prepare(case, "cm")

    def test_cold_clock_contains_preparation_and_first_touch(self):
        events = []
        ticks = iter((0, 4, 9, 10, 14))

        def prepare(case, arm):
            events.append("prepare")

            def execute():
                events.append("execute")
                return 3

            return execute, None

        with patch.object(verify, "prepare", prepare):
            result = verify.measure({"k": 1, "clauses": []}, "cnf", rounds=1, clock=lambda: next(ticks))
        self.assertEqual(events, ["prepare", "execute", "execute"])
        self.assertEqual(result["cold_prepare_ns"], 4)
        self.assertEqual(result["cold_first_execution_ns"], 5)
        self.assertEqual(result["cold_total_ns"], 9)
        self.assertEqual(result["warm_recompute_ns"], [4])
        self.assertFalse(result["output_cache_used"])

    def test_warm_result_mismatch_is_not_timed_as_success(self):
        values = iter((1, 0))
        with patch.object(verify, "prepare", return_value=(lambda: next(values), None)), self.assertRaises(ValueError):
            verify.measure({"k": 1, "clauses": []}, "cnf", rounds=1)

    def test_balance_places_every_arm_in_every_position_equally(self):
        for count in (1, 3, 4, 7):
            arms = tuple(str(i) for i in range(count))
            schedule = verify.balanced_schedule(arms)
            self.assertEqual(len(schedule), 2 * count)
            for arm in arms:
                self.assertEqual(Counter(row.index(arm) for row in schedule), Counter({i: 2 for i in range(count)}))
        with self.assertRaises(ValueError):
            verify.balanced_schedule(("cm", "cm"))

    def fake_cell(self, behavior, expected=1, cell_id="test"):
        return verify.run_cell(self.root, self.ledger, cell_id, {"mode": "test"}, expected, invoke=behavior)

    def test_success_uses_fresh_worker_command_and_records_both_events(self):
        calls = []

        def fake(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, b'{"packed_hex":"0x1"}', b"")

        row = self.fake_cell(fake)
        self.assertEqual(row["status"], "ok")
        self.assertIn("--worker", calls[0][0])
        self.assertEqual(calls[0][1]["timeout"], 15)
        self.assertEqual(calls[0][1]["cwd"], self.root)
        self.assertEqual(len(self.ledger.read_text().splitlines()), 2)
        self.assertFalse(verify.read_ledger(self.ledger)["unfinished"])

    def test_failure_outcomes_remain_and_later_cells_continue(self):
        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(args[0], 15)

        def memory(*args, **kwargs):
            raise MemoryError()

        outcomes = [
            (timeout, "timeout"), (memory, "memory_limit"),
            (lambda *a, **k: subprocess.CompletedProcess([], 4, b"", b"not logged"), "error"),
            (lambda *a, **k: subprocess.CompletedProcess([], 0, b"not json", b""), "error"),
            (lambda *a, **k: subprocess.CompletedProcess([], 0, b"{}", b""), "error"),
            (lambda *a, **k: subprocess.CompletedProcess([], 0, b'{"packed_hex":"0x0"}', b""), "mismatch"),
            (lambda *a, **k: subprocess.CompletedProcess([], 0, b" " * (verify.MAX_RECORD + 1), b""), "error"),
            (lambda *a, **k: subprocess.CompletedProcess([], 0, b'{"packed_hex":"0x1"}', b""), "ok"),
        ]
        for i, (behavior, expected) in enumerate(outcomes):
            self.assertEqual(self.fake_cell(behavior, cell_id=str(i))["status"], expected)
        self.assertEqual(len(verify.read_ledger(self.ledger)["cells"]), len(outcomes))

    def test_interruption_leaves_visible_running_cell(self):
        def interrupted(*a, **kw):
            raise KeyboardInterrupt()

        with self.assertRaises(KeyboardInterrupt):
            self.fake_cell(interrupted)
        self.assertEqual(verify.read_ledger(self.ledger)["unfinished"], ["test"])

    def test_partial_tail_preserves_running_cell_but_middle_corruption_refused(self):
        self.ledger.write_bytes(b'{"cell_id":"a","status":"running"}\n{"cell')
        result = verify.read_ledger(self.ledger)
        self.assertTrue(result["partial_tail"])
        self.assertEqual(result["unfinished"], ["a"])
        self.ledger.write_bytes(b'not-json\n{"cell_id":"a","status":"running"}\n')
        with self.assertRaises(ValueError):
            verify.read_ledger(self.ledger)

    def test_duplicate_terminal_records_are_refused(self):
        for state in ("running", "ok", "ok"):
            verify.append_record(self.ledger, {"cell_id": "a", "status": state})
        with self.assertRaises(ValueError):
            verify.read_ledger(self.ledger)

    def test_worker_refuses_arbitrary_reload_path(self):
        for name in ("../../.env", "C:/elsewhere/cell-1-artifact.json", "cell-1-artifact.json/other"):
            with self.assertRaises(ValueError):
                verify.worker({"mode": "reload", "artifact_file": name})

    def test_snapshot_mutation_and_duplicate_manifest_entries_are_refused(self):
        import hashlib
        source = self.root / "test.py"
        source.write_bytes(b"original")
        manifest = {"files": [{"path": "test.py", "sha256": hashlib.sha256(b"original").hexdigest()}]}
        path = self.root / "source_manifest.json"
        path.write_bytes(verify.encoded(manifest))
        with patch.object(verify, "SOURCES", ("test.py",)):
            verify.verify_snapshot(self.root)
            source.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                verify.verify_snapshot(self.root)
            manifest["files"].append(copy.deepcopy(manifest["files"][0]))
            path.write_bytes(verify.encoded(manifest))
            with self.assertRaises(ValueError):
                verify.verify_snapshot(self.root)


if __name__ == "__main__":
    unittest.main()
