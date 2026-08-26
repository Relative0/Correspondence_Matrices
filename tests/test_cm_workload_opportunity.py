from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from cmbench.tracing.opportunity import screen_trace_events
from cmbench.tracing.replay import load_trace_events
from cmbench.tracing.sink import JsonlTraceSink
from scripts import cm_screen_workload_trace


SMALL_THRESHOLDS = {
    "cache_prepare_requests": 1,
    "cache_process_lifetimes": 2,
    "family_transitions": 1,
    "family_ids": 1,
    "context_transitions": 1,
    "context_streams": 1,
    "selector_independent_formulas": 1,
    "selector_eligible_calls": 1,
}


class WorkloadOpportunityTests(unittest.TestCase):
    def test_backend_results_do_not_double_count_selector_calls(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace = Path(td) / "trace.jsonl"
            with JsonlTraceSink(trace, session_id="a" * 64) as sink:
                common = {
                    "workload_id": "b" * 64,
                    "expression_digest": "c" * 64,
                    "semantic_support": 14,
                    "trial": 0,
                    "sample_every": 1,
                    "status": "ok",
                    "timing_boundary": "complete_output",
                }
                sink.emit("evaluation_result", backend="cm", total_s=0.002, **common)
                sink.emit("evaluation_result", backend="bitset", total_s=0.001, **common)
            report = screen_trace_events(
                load_trace_events([trace]),
                workload_label="dedup",
                evidence_class="real",
                threshold_overrides=SMALL_THRESHOLDS,
            )
            self.assertEqual(report["observations"]["eligible_formula_count_k13_15"], 1)
            self.assertEqual(report["observations"]["eligible_call_count_k13_15"], 1)
            self.assertTrue(report["gates"]["feature_selector"]["volume_adequate"])
            self.assertFalse(report["gates"]["feature_selector"]["opportunity_fraction_computable"])

    def test_sampled_capture_blocks_exact_cache_replay(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            paths = []
            for index, phase in enumerate(("cold", "warm")):
                trace = Path(td) / f"trace-{index}.jsonl"
                paths.append(trace)
                with JsonlTraceSink(trace, session_id=(str(index + 1) * 64)) as sink:
                    sink.emit(
                        "cache_lookup",
                        cache_key_digest="a" * 64,
                        artifact_bytes=128,
                        prepare_s=0.01,
                        phase=phase,
                        sample_every=16,
                        status="ok",
                    )
            report = screen_trace_events(
                load_trace_events(paths),
                workload_label="sampled-cache",
                evidence_class="real",
                complete_workload=True,
                threshold_overrides=SMALL_THRESHOLDS,
            )
            self.assertTrue(report["gates"]["cache"]["collection_adequate"])
            self.assertFalse(report["trace_quality"]["complete_capture"])
            self.assertFalse(report["gates"]["cache"]["exact_logical_replay_ready"])

    def test_complete_real_cache_trace_can_clear_logical_replay_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            paths = []
            for index, phase in enumerate(("cold", "warm")):
                trace = Path(td) / f"trace-{index}.jsonl"
                paths.append(trace)
                with JsonlTraceSink(trace, session_id=(str(index + 3) * 64)) as sink:
                    sink.emit(
                        "cache_lookup",
                        cache_key_digest="d" * 64,
                        artifact_bytes=256,
                        prepare_s=0.02,
                        phase=phase,
                        sample_every=1,
                        status="ok",
                    )
            report = screen_trace_events(
                load_trace_events(paths),
                workload_label="complete-cache",
                evidence_class="real",
                complete_workload=True,
                threshold_overrides=SMALL_THRESHOLDS,
            )
            self.assertTrue(report["trace_quality"]["complete_capture"])
            self.assertTrue(report["gates"]["cache"]["exact_logical_replay_ready"])

    def test_synthetic_volume_never_promotes_followup(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace = Path(td) / "trace.jsonl"
            with JsonlTraceSink(trace, session_id="e" * 64) as sink:
                for index in range(2):
                    sink.emit(
                        "family_version",
                        family_id="f" * 64,
                        expression_digest=(str(index + 1) * 64),
                        variant_index=index,
                        sample_every=1,
                        status="ok",
                    )
                    sink.emit(
                        "context_transition",
                        workload_id="1" * 64,
                        context_id=(str(index + 3) * 64),
                        context_index=index,
                        sample_every=1,
                        status="ok",
                    )
            report = screen_trace_events(
                load_trace_events([trace]),
                workload_label="synthetic",
                evidence_class="synthetic",
                context_stream_kind="synthetic",
                threshold_overrides=SMALL_THRESHOLDS,
            )
            self.assertTrue(report["gates"]["incremental_family"]["collection_adequate"])
            self.assertFalse(report["gates"]["incremental_family"]["followup_capture_ready"])
            self.assertTrue(report["gates"]["partial_context"]["collection_adequate"])
            self.assertFalse(report["gates"]["partial_context"]["followup_capture_ready"])
            self.assertEqual(report["recommended_next_step"], "collect_named_real_metrics_trace")

    def test_cli_records_hash_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace = Path(td) / "trace.jsonl"
            with JsonlTraceSink(trace, session_id="9" * 64) as sink:
                sink.emit("evaluation_result", backend="cm", status="ok", sample_every=16)
            output = Path(td) / "screen.json"
            argv = [
                "--input",
                str(trace),
                "--output",
                str(output),
                "--workload-label",
                "cli-smoke",
                "--evidence-class",
                "synthetic",
            ]
            self.assertEqual(cm_screen_workload_trace.main(argv), 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["inputs"][0]["sha256"]), 64)
            self.assertEqual(payload["screen_version"], "cm-workload-opportunity/v1")
            with self.assertRaises(FileExistsError):
                cm_screen_workload_trace.main(argv)


if __name__ == "__main__":
    unittest.main()
