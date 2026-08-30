"""Provider-neutral, fail-closed lifecycle model for a future approved RunPod job.

There is intentionally no RunPod client, endpoint, credential lookup, or HTTP
code here.  Level 1 tests the ownership and authorization state machine with a
local fake only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import secrets
from typing import Any, Protocol


@dataclass(frozen=True)
class Authorization:
    authorization_id: str
    batch_id: str
    batch_manifest_sha256: str
    bundle_sha256: str
    image: str
    cloud_type: str
    cpu_flavor: str
    vcpu: int
    ram_gb: int
    container_disk_gb: int
    volume_gb: int
    country_codes: tuple[str, ...]
    max_creates: int
    max_parallel_pods: int
    max_rate_usd_per_hour: float
    max_total_cost_usd: float
    timeout_seconds: int
    cleanup: str

    def validate(self) -> None:
        if self.cloud_type not in {"SECURE", "COMMUNITY"}:
            raise ValueError("unsupported cloud type")
        if self.max_creates != 1 or self.max_parallel_pods != 1:
            raise ValueError("proof controller is limited to one create and one pod")
        if self.volume_gb != 0 or self.cleanup != "delete_on_terminal":
            raise ValueError("proof controller requires ephemeral disk and delete_on_terminal")
        if min(self.vcpu, self.ram_gb, self.container_disk_gb, self.timeout_seconds) <= 0:
            raise ValueError("resource and timeout values must be positive")
        for value in (self.batch_manifest_sha256, self.bundle_sha256):
            if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                raise ValueError("authorization hashes must be lowercase SHA-256")


class Backend(Protocol):
    def quote(self, authorization: Authorization) -> float: ...
    def create(self, authorization: Authorization) -> dict[str, Any]: ...
    def shape(self, pod_id: str) -> dict[str, Any]: ...
    def upload(self, pod_id: str, bundle: Path, bootstrap_token: str) -> None: ...
    def execute(self, pod_id: str, batch_sha256: str, bootstrap_token: str,
                timeout_seconds: int, max_total_cost_usd: float) -> None: ...
    def download(self, pod_id: str, destination: Path) -> list[Path]: ...
    def delete(self, pod_id: str) -> None: ...
    def owned_inventory(self, authorization_id: str) -> set[str]: ...


class OwnedPodController:
    def __init__(self, backend: Backend, event_log: Path):
        self.backend = backend
        self.event_log = event_log
        self.sequence = 0
        self.owned_pod_id: str | None = None

    def event(self, name: str, **fields: Any) -> None:
        self.sequence += 1
        self.event_log.parent.mkdir(parents=True, exist_ok=True)
        record = {"schema_version": "1.0", "sequence": self.sequence, "event": name, **fields}
        with self.event_log.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @classmethod
    def _verify_downloads(cls, paths: list[Path]) -> None:
        results = [path for path in paths if path.name == "render_result.json"]
        if not results:
            raise RuntimeError("no render results downloaded")
        downloaded_hashes = {cls._sha256(path) for path in paths if path.name != "render_result.json"}
        for path in results:
            data = json.loads(path.read_text("utf-8"))
            if data.get("passed") is not True or data.get("status") != "passed":
                raise RuntimeError(f"downloaded result did not pass: {path}")
            missing = set(data.get("outputs", {}).values()) - downloaded_hashes
            if missing:
                raise RuntimeError(f"downloaded outputs do not satisfy result hashes: {sorted(missing)}")

    def run(self, authorization: Authorization, bundle: Path, batch_manifest: Path,
            download_dir: Path) -> None:
        authorization.validate()
        if self._sha256(bundle) != authorization.bundle_sha256:
            raise ValueError("bundle hash does not match authorization")
        if self._sha256(batch_manifest) != authorization.batch_manifest_sha256:
            raise ValueError("batch manifest hash does not match authorization")
        self.event("authorization_verified", authorization_id=authorization.authorization_id,
                   authorization_sha256=hashlib.sha256(
                       json.dumps(asdict(authorization), sort_keys=True).encode("utf-8")
                   ).hexdigest())
        terminal_error: Exception | None = None
        try:
            rate = self.backend.quote(authorization)
            if rate > authorization.max_rate_usd_per_hour:
                raise RuntimeError("quoted rate exceeds authorized ceiling")
            self.event("quote_verified", rate_usd_per_hour=rate)
            created = self.backend.create(authorization)
            self.owned_pod_id = str(created["id"])
            self.event("pod_created", pod_id=self.owned_pod_id)
            expected_shape = {
                "cloud_type": authorization.cloud_type, "cpu_flavor": authorization.cpu_flavor,
                "vcpu": authorization.vcpu, "ram_gb": authorization.ram_gb,
                "container_disk_gb": authorization.container_disk_gb, "volume_gb": 0,
            }
            if self.backend.shape(self.owned_pod_id) != expected_shape:
                raise RuntimeError("created pod shape does not match authorization")
            self.event("shape_verified", pod_id=self.owned_pod_id)
            token = secrets.token_urlsafe(32)
            self.event("bootstrap_issued", token_sha256=hashlib.sha256(token.encode()).hexdigest())
            self.backend.upload(self.owned_pod_id, bundle, token)
            self.event("bundle_uploaded", bundle_sha256=authorization.bundle_sha256)
            self.backend.execute(
                self.owned_pod_id, authorization.batch_manifest_sha256, token,
                authorization.timeout_seconds, authorization.max_total_cost_usd,
            )
            self.event("batch_executed", batch_manifest_sha256=authorization.batch_manifest_sha256)
            downloaded = self.backend.download(self.owned_pod_id, download_dir)
            self._verify_downloads(downloaded)
            self.event("results_verified", files=len(downloaded))
        except Exception as exc:
            terminal_error = exc
            self.event("terminal_failure", error_type=type(exc).__name__)
        finally:
            if self.owned_pod_id is not None and authorization.cleanup == "delete_on_terminal":
                self.backend.delete(self.owned_pod_id)
                self.event("owned_pod_deleted", pod_id=self.owned_pod_id)
            remaining = self.backend.owned_inventory(authorization.authorization_id)
            self.event("inventory_reconciled", remaining_owned=sorted(remaining))
            if remaining:
                terminal_error = terminal_error or RuntimeError("owned pod remains after reconciliation")
        if terminal_error is not None:
            raise terminal_error
