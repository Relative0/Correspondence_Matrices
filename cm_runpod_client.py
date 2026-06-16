from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from cm_runpod_config import CMRunPodConfig, CMRunPodConfigError
from cm_runpod_protocol import CMRemoteRequest, CMRemoteResponse


class CMRunPodClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class PodStatus:
    pod_id: str
    desired_status: str
    runtime_status: str
    raw: dict[str, Any]

    @property
    def is_running(self) -> bool:
        text = f"{self.desired_status} {self.runtime_status} {self.raw}".upper()
        return "RUNNING" in text


class CMRunPodClient:
    REST_BASE_URL = "https://rest.runpod.io/v1"
    GRAPHQL_URL = "https://api.runpod.io/graphql"

    def __init__(self, config: CMRunPodConfig) -> None:
        self.config = config
        self.session = requests.Session()
        if config.api_key:
            self.session.headers.update({"Authorization": f"Bearer {config.api_key}"})

    def get_pod_status(self) -> PodStatus:
        self.config.require_lifecycle()
        response = self.session.get(f"{self.REST_BASE_URL}/pods/{self.config.pod_id}", timeout=60)
        response.raise_for_status()
        raw = response.json()
        if not isinstance(raw, dict):
            raise CMRunPodClientError(f"malformed RunPod status response: {raw!r}")
        pod = raw.get("pod") if isinstance(raw.get("pod"), dict) else raw
        return PodStatus(
            pod_id=self.config.pod_id,
            desired_status=str(pod.get("desiredStatus") or pod.get("desired_status") or pod.get("status") or ""),
            runtime_status=str(
                pod.get("runtimeStatus")
                or pod.get("runtime_status")
                or pod.get("machineStatus")
                or pod.get("status")
                or ""
            ),
            raw=pod,
        )

    def start_pod(self, gpu_count: int = 1) -> PodStatus:
        self.config.require_lifecycle()
        query = """
        mutation ResumePod($podId: String!, $gpuCount: Int!) {
          podResume(input: { podId: $podId, gpuCount: $gpuCount }) {
            id
            desiredStatus
            imageName
          }
        }
        """
        response = requests.post(
            f"{self.GRAPHQL_URL}?api_key={self.config.api_key}",
            json={"query": query, "variables": {"podId": self.config.pod_id, "gpuCount": gpu_count}},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise CMRunPodClientError(f"RunPod podResume failed: {payload['errors']}")
        return self.get_pod_status()

    def stop_pod(self) -> PodStatus:
        self.config.require_lifecycle()
        response = self.session.post(f"{self.REST_BASE_URL}/pods/{self.config.pod_id}/stop", timeout=60)
        response.raise_for_status()
        return self.wait_for_stopped()

    def wait_for_pod_ready(self, *, start_if_stopped: bool = True, poll_interval: float = 10.0) -> tuple[PodStatus, bool, float]:
        started = time.perf_counter()
        status = self.get_pod_status()
        pod_started = False
        if start_if_stopped and not status.is_running:
            self.start_pod()
            pod_started = True
        deadline = time.perf_counter() + self.config.start_timeout_seconds
        while time.perf_counter() < deadline:
            status = self.get_pod_status()
            if status.is_running:
                return status, pod_started, time.perf_counter() - started
            time.sleep(poll_interval)
        raise CMRunPodClientError(
            f"RunPod execution requested, but pod is unavailable/offline after {self.config.start_timeout_seconds}s."
        )

    def wait_for_stopped(self, timeout: int = 300, poll_interval: float = 5.0) -> PodStatus:
        deadline = time.perf_counter() + timeout
        last = self.get_pod_status()
        while time.perf_counter() < deadline:
            last = self.get_pod_status()
            if not last.is_running:
                return last
            time.sleep(poll_interval)
        return last

    def wait_for_worker_ready(self, timeout: int | None = None, poll_interval: float = 3.0) -> float:
        self.config.require_worker()
        started = time.perf_counter()
        deadline = time.perf_counter() + float(timeout or self.config.start_timeout_seconds)
        last_error = ""
        while time.perf_counter() < deadline:
            try:
                response = self.session.get(f"{self.config.base_url}/health", timeout=10)
                if response.ok and response.json().get("ok"):
                    return time.perf_counter() - started
                last_error = response.text[:200]
            except Exception as exc:
                last_error = str(exc)
            time.sleep(poll_interval)
        raise CMRunPodClientError(f"RunPod execution requested, but worker is unavailable/offline. {last_error}")

    def execute(self, request: CMRemoteRequest) -> tuple[CMRemoteResponse, float]:
        self.config.require_worker()
        started = time.perf_counter()
        response = self.session.post(
            f"{self.config.base_url}/execute",
            json=request.to_dict(),
            timeout=self.config.request_timeout_seconds,
        )
        elapsed = time.perf_counter() - started
        try:
            payload = response.json()
        except Exception as exc:
            raise CMRunPodClientError(f"malformed CM worker response: {exc}") from exc
        if not response.ok and not isinstance(payload, dict):
            raise CMRunPodClientError(f"CM worker request failed with HTTP {response.status_code}")
        return CMRemoteResponse.from_dict(payload), elapsed


def config_error_message(exc: Exception) -> str:
    if isinstance(exc, CMRunPodConfigError):
        return str(exc)
    return f"RunPod execution requested, but pod is unavailable/offline. {exc}"
