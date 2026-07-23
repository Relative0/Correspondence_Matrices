from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from cm_exprlib import Expr
from cm_remote_worker import execute_cm_request
from cm_runpod_client import CMRunPodClient
from cm_runpod_config import CMRunPodConfig
from cm_runpod_protocol import CMRemoteRequest, CMRemoteResponse


@dataclass(frozen=True)
class CMRemoteExecutionResult:
    response: CMRemoteResponse
    pod_started: bool = False
    ready_wait_time_s: float = 0.0
    request_time_s: float = 0.0
    total_wall_time_s: float = 0.0
    fallback_used: bool = False
    status: str = "ok"
    diagnostics: dict[str, Any] = field(default_factory=dict)


class LocalMockCMRemoteExecutor:
    def execute(self, request: CMRemoteRequest) -> CMRemoteExecutionResult:
        started = time.perf_counter()
        response = execute_cm_request(request)
        return CMRemoteExecutionResult(
            response=response,
            request_time_s=response.timing.get("remote_total_time_s", 0.0),
            total_wall_time_s=time.perf_counter() - started,
            status="ok" if response.ok else "error",
        )


class RunPodCMRemoteExecutor:
    def __init__(self, config: CMRunPodConfig) -> None:
        self.config = config
        self.client = CMRunPodClient(config)

    def execute(self, request: CMRemoteRequest, *, start: bool = True, stop_after_run: bool | None = None) -> CMRemoteExecutionResult:
        started = time.perf_counter()
        pod_started = False
        ready_wait = 0.0
        try:
            if self.config.is_lifecycle_configured:
                _, pod_started, ready_wait = self.client.wait_for_pod_ready(start_if_stopped=start)
            ready_wait += self.client.wait_for_worker_ready()
            response, request_time = self.client.execute(request)
            return CMRemoteExecutionResult(
                response=response,
                pod_started=pod_started,
                ready_wait_time_s=ready_wait,
                request_time_s=request_time,
                total_wall_time_s=time.perf_counter() - started,
                status="ok" if response.ok else "error",
            )
        finally:
            should_stop = self.config.stop_after_run if stop_after_run is None else stop_after_run
            if should_stop and self.config.is_lifecycle_configured:
                self.client.stop_pod()


def build_remote_request(
    expr: Expr,
    n_vars: int,
    *,
    hybrid_threshold: int = 7,
    use_persistent_cache: bool = True,
    eval_repeat: int = 1,
    large_n_safe: bool = False,
    max_full_output_vars: int | None = None,
    words_eval: bool = False,
) -> CMRemoteRequest:
    return CMRemoteRequest.from_expr(
        expr,
        [f"x{i}" for i in range(n_vars)],
        hybrid_threshold=hybrid_threshold,
        use_persistent_cache=use_persistent_cache,
        eval_repeat=eval_repeat,
        allow_reduced_output=large_n_safe,
        max_full_output_vars=max_full_output_vars,
        words_eval=words_eval,
    )
