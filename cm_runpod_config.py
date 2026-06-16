from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parent


class CMRunPodConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class CMRunPodConfig:
    base_url: str
    pod_id: str
    api_key: str
    persistent_root: str = "/workspace/cm-computation"
    start_timeout_seconds: int = 300
    stop_after_run: bool = False
    request_timeout_seconds: int = 300

    @property
    def is_lifecycle_configured(self) -> bool:
        return bool(self.pod_id and self.api_key)

    @property
    def is_worker_configured(self) -> bool:
        return bool(self.base_url)

    def require_worker(self) -> None:
        if not self.base_url:
            raise CMRunPodConfigError("CM_RUNPOD_BASE_URL is required for RunPod CM execution")

    def require_lifecycle(self) -> None:
        missing = []
        if not self.pod_id:
            missing.append("RUNPOD_POD_ID")
        if not self.api_key:
            missing.append("RUNPOD_API_KEY")
        if missing:
            raise CMRunPodConfigError("missing RunPod lifecycle configuration: " + ", ".join(missing))


def default_env_paths() -> list[Path]:
    return [ROOT / ".env", ROOT / ".env.local", ROOT / ".env.runpod", ROOT / ".env.runpod.local"]


def load_runpod_config(
    env: Mapping[str, str] | None = None,
    env_paths: Sequence[Path] | None = None,
) -> CMRunPodConfig:
    merged: dict[str, str] = {}
    paths = default_env_paths() if env_paths is None else list(env_paths)
    for path in paths:
        merged.update(_parse_env_file(path))
    merged.update(dict(os.environ if env is None else env))
    return CMRunPodConfig(
        base_url=_strip_slash(merged.get("CM_RUNPOD_BASE_URL", "")),
        pod_id=merged.get("RUNPOD_POD_ID", ""),
        api_key=merged.get("RUNPOD_API_KEY", "") or merged.get("RP_TOKEN", ""),
        persistent_root=merged.get("CM_RUNPOD_PERSISTENT_ROOT", "/workspace/cm-computation"),
        start_timeout_seconds=_int_env(merged, "CM_RUNPOD_START_TIMEOUT_SECONDS", 300),
        stop_after_run=_bool_env(merged, "CM_RUNPOD_STOP_AFTER_RUN", False),
        request_timeout_seconds=_int_env(merged, "CM_RUNPOD_REQUEST_TIMEOUT_SECONDS", 300),
    )


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def _int_env(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key, "")
    return int(raw) if str(raw).strip() else default


def _bool_env(env: Mapping[str, str], key: str, default: bool) -> bool:
    raw = str(env.get(key, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _strip_slash(value: str) -> str:
    return value.strip().rstrip("/")
