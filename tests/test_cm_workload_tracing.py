from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import cm_bench
from cm_exprlib import And, Not, Var
from cmbench.availability import detect_backends
from cmbench.config import BenchmarkConfig
from cmbench.context import make_context
from cmbench.tracing.integration import (
    trace_expression_family_result,
    trace_partial_context_result,
    trace_single_expression_result,
)
from cmbench.tracing.replay import TraceFileError, load_trace_events, summarize_trace_files
from cmbench.tracing.schema import TraceValidationError, validate_trace_event
from cmbench.tracing.sink import JsonlTraceSink, NullTraceSink
from scripts import cm_replay_workload_trace, cm_validate_workload_trace


class WorkloadTraceTests(unittest.TestCase):
    def test_null_sink_is_disabled_and_creates_nothing(self) -> None:
        sink = NullTraceSink()
        self.assertFalse(sink.enabled)
        self.assertFalse(sink.emit("evaluation_result", backend="cm"))
        sink.close()
        self.assertEqual(sink.stats()["events_written"], 0)

    def test_schema_round_trip_and_privacy_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trace.jsonl"
            sink = JsonlTraceSink(path, session_id="a" * 64)
            self.assertTrue(
                sink.emit(
                    "evaluation_result",
                    workload_id="b" * 64,
                    expression_digest="c" * 64,
                    backend="cm",
                    n_vars=4,
                    total_s=0.001,
                    exact_ok=True,
                    status="ok",
                )
            )
            sink.close()
            events = load_trace_events([path])
            self.assertEqual(events[1]["payload"]["expression_digest"], "c" * 64)
            self.assertEqual(events[-1]["event_type"], "session_end")
            bad = dict(events[1])
            bad["payload"] = {"expression_text": "x0"}
            with self.assertRaises(TraceValidationError):
                validate_trace_event(bad)

    def test_invalid_schema_and_value_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trace.jsonl"
            sink = JsonlTraceSink(path, session_id="d" * 64)
            with self.assertRaises(TraceValidationError):
                sink.emit("evaluation_result", backend="cm", total_s=float("nan"))
            with self.assertRaises(TraceValidationError):
                sink.emit("unknown", backend="cm")
            sink.close()

    def test_base_and_rotation_paths_refuse_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "trace.jsonl"
            base.write_text("occupied", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                JsonlTraceSink(base)

            base.unlink()
            rotated = Path(td) / "trace.0001.jsonl"
            rotated.write_text("occupied", encoding="utf-8")
            sink = JsonlTraceSink(base, max_bytes=1024, max_files=2, flush_every=1)
            with self.assertRaises(FileExistsError):
                sink.emit("evaluation_result", backend="cm", status="ok")
            sink.close()
            self.assertEqual(rotated.read_text(encoding="utf-8"), "occupied")

    def test_byte_bound_records_drop_and_never_exceeds_limit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trace.jsonl"
            sink = JsonlTraceSink(path, max_bytes=1024, max_files=1, flush_every=1)
            for _ in range(20):
                sink.emit("evaluation_result", backend="cm", compiler_identity="x" * 200, status="ok")
            sink.close()
            self.assertLessEqual(path.stat().st_size, 1024)
            self.assertGreaterEqual(sink.stats()["dropped_events"], 1)
            self.assertIn("trace_drop", [event["event_type"] for event in load_trace_events([path])])

    def test_writer_failure_is_contained(self) -> None:
        class BrokenStream:
            def write(self, value):
                raise OSError("simulated")

            def flush(self):
                raise OSError("simulated")

            def close(self):
                return None

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trace.jsonl"
            sink = JsonlTraceSink(path, flush_every=1)
            original = sink._stream
            assert original is not None
            original.flush()
            original.close()
            sink._stream = BrokenStream()
            self.assertFalse(sink.emit("evaluation_result", backend="cm", status="ok"))
            self.assertEqual(sink.stats()["io_error_count"], 1)
            self.assertFalse(sink.enabled)
            sink.close()

    def test_corrupt_and_duplicate_events_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trace.jsonl"
            sink = JsonlTraceSink(path, session_id="e" * 64)
            sink.emit("evaluation_result", backend="cm", status="ok")
            sink.close()
            text = path.read_text(encoding="ascii")
            corrupt = Path(td) / "corrupt.jsonl"
            corrupt.write_text(text + "{", encoding="ascii")
            with self.assertRaises(TraceFileError):
                load_trace_events([corrupt])
            duplicate = Path(td) / "duplicate.jsonl"
            lines = text.splitlines()
            duplicate.write_text("\n".join(lines + [lines[1]]) + "\n", encoding="ascii")
            with self.assertRaises(TraceFileError):
                load_trace_events([duplicate])

    def test_validator_and_replay_refuse_overwrite_and_hash_input(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace = Path(td) / "trace.jsonl"
            sink = JsonlTraceSink(trace)
            sink.emit("evaluation_result", backend="cm", expression_digest="f" * 64, status="ok")
            sink.close()
            audit = Path(td) / "audit.json"
            replay = Path(td) / "replay.json"
            self.assertEqual(
                cm_validate_workload_trace.main(["--input", str(trace), "--output", str(audit)]),
                0,
            )
            self.assertEqual(
                cm_replay_workload_trace.main(["--input", str(trace), "--output", str(replay)]),
                0,
            )
            audit_payload = json.loads(audit.read_text(encoding="utf-8"))
            self.assertEqual(audit_payload["validation_status"], "pass")
            self.assertEqual(len(audit_payload["input_files"][0]["sha256"]), 64)
            replay_payload = json.loads(replay.read_text(encoding="utf-8"))
            self.assertFalse(replay_payload["expressions_executed"])
            with self.assertRaises(FileExistsError):
                cm_validate_workload_trace.main(["--input", str(trace), "--output", str(audit)])

    def test_multi_session_replay_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            a = Path(td) / "a.jsonl"
            b = Path(td) / "b.jsonl"
            with JsonlTraceSink(a, session_id="b" * 64) as sink:
                sink.emit("evaluation_result", backend="cm", expression_digest="1" * 64, status="ok")
            with JsonlTraceSink(b, session_id="a" * 64) as sink:
                sink.emit("evaluation_result", backend="cm", expression_digest="1" * 64, status="ok")
            first = load_trace_events([a, b])
            second = load_trace_events([b, a])
            self.assertEqual([event["event_id"] for event in first], [event["event_id"] for event in second])
            summary = summarize_trace_files([a, b])
            self.assertEqual(summary["session_count"], 2)
            self.assertEqual(summary["repeated_expression_count"], 1)

    def test_single_expression_benchmark_trace_preserves_results(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace = Path(td) / "bench.jsonl"
            config = BenchmarkConfig(
                sizes=(2,),
                trials=1,
                seed=7,
                max_depth=2,
                no_sympy=True,
                no_dd=True,
                no_robdd=True,
                no_numba=True,
                no_espresso=True,
                no_bdd_sop=True,
                cm_compare_no_reinflate=True,
                cm_trace_jsonl=str(trace),
            )
            ctx = make_context(config, detect_backends())
            raw, summary = cm_bench.run_bench([2], 1, 7, 2, False, config=config, ctx=ctx)
            ctx.close_trace()
            self.assertEqual(len(raw), 1)
            self.assertEqual(len(summary), 1)
            self.assertTrue(bool(raw.iloc[0]["cm_hybrid_no_reinflate_ok"]))
            event_types = [event["event_type"] for event in load_trace_events([trace])]
            self.assertIn("evaluation_result", event_types)

    def test_sampling_is_deterministic_per_workload_stream(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace = Path(td) / "sampled.jsonl"
            config = BenchmarkConfig(
                sizes=(2,),
                trials=1,
                seed=1,
                max_depth=1,
                cm_trace_jsonl=str(trace),
                cm_trace_sample_every=2,
            )
            ctx = make_context(config, detect_backends())
            row = {
                "n_vars": 2,
                "trial": 0,
                "expr_unique_var_count": 2,
                "cm_hybrid_no_reinflate_time_s": 0.001,
                "cm_hybrid_no_reinflate_ok": True,
            }
            for index in range(3):
                trace_single_expression_result(ctx, Var(0), row, workload_id=f"sample:{index}")
            ctx.close_trace()
            events = load_trace_events([trace])
            evaluations = [event for event in events if event["event_type"] == "evaluation_result"]
            self.assertEqual(len(evaluations), 2)
            self.assertEqual([event["payload"]["sample_every"] for event in evaluations], [2, 2])
            restart = next(event for event in events if event["event_type"] == "process_restart")
            self.assertEqual(restart["payload"]["policy"], "sampled")

    def test_family_and_context_helpers_emit_only_anonymous_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace = Path(td) / "helpers.jsonl"
            config = BenchmarkConfig(
                sizes=(2,), trials=1, seed=1, max_depth=1, cm_trace_jsonl=str(trace)
            )
            ctx = make_context(config, detect_backends())
            variants = [Var(0), And(Var(0), Not(Var(1)))]
            trace_expression_family_result(
                ctx,
                variants,
                {
                    "n_vars": 2,
                    "family_cm_cache_compile_total_s": 0.01,
                    "family_cm_cache_eval_total_s": 0.02,
                    "family_cm_cache_total_time_s": 0.03,
                    "family_cm_cache_ok_rate": 1.0,
                },
                family_id="raw-family-name",
                trial=0,
            )
            trace_partial_context_result(
                ctx,
                variants[1],
                [{"x0": 0}, {"x0": 1, "x1": 0}],
                {
                    "n_vars": 2,
                    "partial_cm_cache_compile_once_s": 0.01,
                    "partial_cm_cache_eval_contexts_total_s": 0.02,
                    "partial_cm_cache_total_s": 0.03,
                    "partial_cm_cache_ok_rate": 1.0,
                },
                trial=0,
            )
            ctx.close_trace()
            raw_text = trace.read_text(encoding="ascii")
            self.assertNotIn("raw-family-name", raw_text)
            self.assertNotIn("x0", raw_text)
            events = load_trace_events([trace])
            self.assertEqual(sum(event["event_type"] == "family_version" for event in events), 2)
            self.assertEqual(sum(event["event_type"] == "context_transition" for event in events), 2)


if __name__ == "__main__":
    unittest.main()
