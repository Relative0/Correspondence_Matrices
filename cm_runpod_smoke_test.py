from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests

from cm_runpod_client import CMRunPodClient
from cm_runpod_config import load_runpod_config


@dataclass(frozen=True)
class ProxyProbe:
    ok: bool
    status_code: int | None
    content_type: str
    server: str
    text_sample: str
    error: str = ""


def run_smoke_test(*, local_mock: bool = False) -> int:
    if local_mock:
        print("RUNPOD_POD_ID=local-mock")
        print("RUNPOD_API_KEY=<redacted>")
        print("CM_RUNPOD_BASE_URL=http://127.0.0.1:0")
        print("CM_RUNPOD_PERSISTENT_ROOT=/workspace/cm-computation")
        print("RunPod API: OK")
        print("Pod status: RUNNING")
        print("Proxy URL: OK")
        print("CM worker: FOUND")
        print("Next step: deploy cm_remote_worker.py if worker not found")
        return 0

    disable_env_files = (
        str(os.environ.get("CM_RUNPOD_DISABLE_ENV_FILES", "")).strip().lower() in {"1", "true", "yes", "on"}
    )
    config = load_runpod_config(env_paths=[] if disable_env_files else None)
    missing = _missing_required(config)
    if missing:
        _print_config(config)
        print("RunPod API: FAILED")
        print("Pod status: UNKNOWN")
        print("Proxy URL: FAILED")
        print("CM worker: NOT FOUND")
        print(f"Error: missing required environment variable(s): {', '.join(missing)}", file=sys.stderr)
        if "RUNPOD_API_KEY" in missing:
            print("Error: missing API key. Set RUNPOD_API_KEY.", file=sys.stderr)
        if "RUNPOD_POD_ID" in missing:
            print("Error: missing pod ID. Set RUNPOD_POD_ID.", file=sys.stderr)
        print("Next step: deploy cm_remote_worker.py if worker not found")
        return 2

    _print_config(config)

    api_ok = False
    pod_status = "UNKNOWN"
    pod_error = ""
    try:
        status = CMRunPodClient(config).get_pod_status()
        api_ok = True
        pod_status = _normalize_pod_status(status)
    except Exception as exc:
        pod_error = str(exc)

    proxy = _probe_url(config.base_url)
    worker_found, worker_detail = _probe_worker(config.base_url)
    jupyter_found = _looks_like_jupyter(proxy)

    print(f"RunPod API: {'OK' if api_ok else 'FAILED'}")
    print(f"Pod status: {pod_status}")
    print(f"Proxy URL: {'OK' if proxy.ok else 'FAILED'}{_format_http_status(proxy.status_code)}")
    print(f"CM worker: {'FOUND' if worker_found else 'NOT FOUND'}")

    if not api_ok:
        print(f"Error: pod unavailable or RunPod API request failed. {pod_error}", file=sys.stderr)
    if pod_status != "RUNNING":
        print(f"Error: pod unavailable. Current status: {pod_status}", file=sys.stderr)
    if not proxy.ok:
        print(f"Error: proxy URL unreachable. {proxy.error}", file=sys.stderr)
    if proxy.ok and not worker_found:
        if jupyter_found:
            print("RunPod pod reachable, but CM worker service is not deployed yet.")
        else:
            print(f"Error: proxy URL reachable but not a CM worker. {worker_detail}", file=sys.stderr)
    print("Next step: deploy cm_remote_worker.py if worker not found")

    if not api_ok or not proxy.ok:
        return 2
    if pod_status != "RUNNING":
        return 2
    if not worker_found:
        return 3
    return 0


def _missing_required(config: Any) -> list[str]:
    missing = []
    if not config.pod_id:
        missing.append("RUNPOD_POD_ID")
    if not config.api_key:
        missing.append("RUNPOD_API_KEY")
    if not config.base_url:
        missing.append("CM_RUNPOD_BASE_URL")
    if not config.persistent_root:
        missing.append("CM_RUNPOD_PERSISTENT_ROOT")
    return missing


def _print_config(config: Any) -> None:
    print(f"RUNPOD_POD_ID={config.pod_id or '<missing>'}")
    print(f"RUNPOD_API_KEY={_redact(config.api_key)}")
    print(f"CM_RUNPOD_BASE_URL={config.base_url or '<missing>'}")
    print(f"CM_RUNPOD_PERSISTENT_ROOT={config.persistent_root or '<missing>'}")


def _redact(value: str) -> str:
    if not value:
        return "<missing>"
    return "<redacted>"


def _normalize_pod_status(status: Any) -> str:
    raw = f"{status.desired_status} {status.runtime_status} {status.raw}".upper()
    for name in ("RUNNING", "STOPPED", "EXITED", "PAUSED", "TERMINATED"):
        if name in raw:
            return "STOPPED" if name in {"EXITED", "TERMINATED"} else name
    return "UNKNOWN"


def _probe_url(url: str) -> ProxyProbe:
    try:
        response = requests.get(url, timeout=20, allow_redirects=True)
        return ProxyProbe(
            ok=True,
            status_code=response.status_code,
            content_type=response.headers.get("content-type", ""),
            server=response.headers.get("server", ""),
            text_sample=response.text[:4096],
        )
    except Exception as exc:
        return ProxyProbe(False, None, "", "", "", str(exc))


def _probe_worker(base_url: str) -> tuple[bool, str]:
    health_url = urljoin(f"{base_url.rstrip('/')}/", "health")
    try:
        response = requests.get(health_url, timeout=20)
    except Exception as exc:
        return False, f"/health unreachable: {exc}"
    if not response.ok:
        return False, f"/health returned HTTP {response.status_code}"
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return False, "/health did not return JSON"
    if payload.get("ok") is True and payload.get("service") == "cm-remote-worker":
        return True, "/health returned cm-remote-worker"
    return False, f"/health returned JSON but not the CM worker signature: {payload!r}"


def _looks_like_jupyter(probe: ProxyProbe) -> bool:
    haystack = " ".join([probe.content_type, probe.server, probe.text_sample]).lower()
    return "jupyter" in haystack or "jupyterlab" in haystack or "jupyter_server" in haystack


def _format_http_status(status_code: int | None) -> str:
    return "" if status_code is None else f" (HTTP {status_code})"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-mock", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    raise SystemExit(run_smoke_test(local_mock=args.local_mock))


if __name__ == "__main__":
    main()
