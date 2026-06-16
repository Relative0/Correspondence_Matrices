import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cm_expr_serde import expr_from_json, expr_to_json
from cm_exprlib import And, Var
from cm_remote_executor import LocalMockCMRemoteExecutor, build_remote_request
from cm_runpod_config import CMRunPodConfigError, load_runpod_config
from cm_runpod_protocol import CMRemoteRequest, CMRemoteResponse


class CMRunPodTests(unittest.TestCase):
    def test_config_loading_from_env(self) -> None:
        cfg = load_runpod_config(
            {
                "RUNPOD_API_KEY": "key",
                "RUNPOD_POD_ID": "pod",
                "CM_RUNPOD_BASE_URL": "https://example.test/",
                "CM_RUNPOD_PERSISTENT_ROOT": "/workspace/custom",
                "CM_RUNPOD_START_TIMEOUT_SECONDS": "12",
                "CM_RUNPOD_STOP_AFTER_RUN": "true",
            },
            env_paths=[],
        )
        self.assertEqual(cfg.api_key, "key")
        self.assertEqual(cfg.pod_id, "pod")
        self.assertEqual(cfg.base_url, "https://example.test")
        self.assertEqual(cfg.persistent_root, "/workspace/custom")
        self.assertEqual(cfg.start_timeout_seconds, 12)
        self.assertTrue(cfg.stop_after_run)

    def test_missing_env_behavior(self) -> None:
        cfg = load_runpod_config({}, env_paths=[])
        with self.assertRaises(CMRunPodConfigError):
            cfg.require_worker()
        with self.assertRaises(CMRunPodConfigError):
            cfg.require_lifecycle()

    def test_expr_and_protocol_round_trip(self) -> None:
        expr = And(Var(0), Var(1))
        self.assertEqual(expr_from_json(expr_to_json(expr)), expr)
        req = CMRemoteRequest.from_expr(expr, ["x0", "x1"], request_id="r1")
        self.assertEqual(CMRemoteRequest.from_dict(req.to_dict()), req)
        resp = CMRemoteResponse.from_dict(
            {
                "request_id": "r1",
                "ok": True,
                "result_repr": "packed_bitset",
                "result": {"bits_hex": "0x8"},
                "diagnostics": {"final_cm_materialization_performed": 0},
                "timing": {"remote_exec_time_s": 0.1},
            }
        )
        self.assertTrue(resp.ok)
        self.assertEqual(resp.result_repr, "packed_bitset")

    def test_local_mock_remote_executor(self) -> None:
        req = build_remote_request(And(Var(0), Var(1)), 2, hybrid_threshold=7)
        result = LocalMockCMRemoteExecutor().execute(req)
        self.assertTrue(result.response.ok)
        self.assertEqual(result.response.result_repr, "packed_bitset")
        self.assertEqual(result.response.result["bits_hex"], "0x8")

    def test_smoke_test_missing_env(self) -> None:
        root = Path(__file__).resolve().parents[1]
        # Avoid coupling test outcome to any local untracked .env.runpod file.
        # Smoke test should be able to run purely from the process environment.
        proc = subprocess.run(
            [sys.executable, str(root / "cm_runpod_smoke_test.py")],
            cwd=root,
            capture_output=True,
            text=True,
            env={
                **{
                    k: v
                    for k, v in os.environ.items()
                    if k not in {"CM_RUNPOD_BASE_URL", "RUNPOD_POD_ID", "RUNPOD_API_KEY", "RP_TOKEN"}
                },
                "CM_RUNPOD_DISABLE_ENV_FILES": "1",
            },
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("RunPod API: FAILED", proc.stdout)
        self.assertIn("CM worker: NOT FOUND", proc.stdout)
        self.assertIn("missing API key", proc.stderr)

    def test_benchmark_runpod_fields_with_local_mock(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = root / "cm_bench.py"
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--sizes",
                    "4",
                    "--trials",
                    "1",
                    "--max-depth",
                    "2",
                    "--seed",
                    "123",
                    "--out-prefix",
                    "bench_runpod",
                    "--cm-exec-target",
                    "runpod",
                    "--cm-runpod-local-mock",
                    "--no-sympy",
                    "--no-robdd",
                    "--no-dd",
                    "--no-espresso",
                    "--no-bdd-sop",
                    "--no-numba",
                ],
                cwd=tmpdir,
                check=True,
                capture_output=True,
                text=True,
            )
            with (tmpdir / "bench_runpod_summary.csv").open("r", newline="", encoding="utf-8") as f:
                row = list(csv.DictReader(f))[0]
            for col in [
                "cm_exec_target",
                "cm_runpod_pod_started_median",
                "cm_runpod_ready_wait_time_s_median",
                "cm_runpod_request_time_s_median",
                "cm_runpod_remote_exec_time_s_median",
                "cm_runpod_total_wall_time_s_median",
                "cm_runpod_result_repr",
                "cm_runpod_final_cm_materialized_median",
            ]:
                self.assertIn(col, row)
            self.assertEqual(row["cm_exec_target"], "runpod")
            self.assertEqual(row["cm_runpod_result_repr"], "packed_bitset")

    def test_runpod_unavailable_does_not_fallback_by_default(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = root / "cm_bench.py"
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--sizes",
                    "4",
                    "--trials",
                    "1",
                    "--max-depth",
                    "2",
                    "--out-prefix",
                    "bench_offline",
                    "--cm-exec-target",
                    "runpod",
                    "--no-sympy",
                    "--no-robdd",
                    "--no-dd",
                    "--no-espresso",
                    "--no-bdd-sop",
                    "--no-numba",
                ],
                cwd=tmpdir,
                check=True,
                capture_output=True,
                text=True,
                env={
                    k: v
                    for k, v in os.environ.items()
                    if k not in {"CM_RUNPOD_BASE_URL", "RUNPOD_POD_ID", "RUNPOD_API_KEY", "RP_TOKEN"}
                },
            )
            with (tmpdir / "bench_offline_summary.csv").open("r", newline="", encoding="utf-8") as f:
                row = list(csv.DictReader(f))[0]
            self.assertEqual(row["cm_exec_target"], "runpod")
            self.assertEqual(row["cm_runpod_status"], "offline")


if __name__ == "__main__":
    unittest.main()
