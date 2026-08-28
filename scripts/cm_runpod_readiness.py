"""Credential-free, offline inventory for comparing CM Runpod task setups.

This deliberately does not import a Runpod client, load dotenv files, inspect
environment values, contact Runpod, or certify that an account/pod is usable.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = Path(
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909"
)
CONTROLLERS = CAMPAIGN / "runpod-authorized-20260827-213104"
ENV_NAMES = (
    "RUNPOD_API_KEY", "RP_TOKEN", "RUNPOD_POD_ID", "CM_RUNPOD_BASE_URL",
    "CM_RUNPOD_PERSISTENT_ROOT", "CM_RUNPOD_START_TIMEOUT_SECONDS",
    "CM_RUNPOD_REQUEST_TIMEOUT_SECONDS", "CM_RUNPOD_STOP_AFTER_RUN",
)
CREDENTIAL_CANDIDATES = (
    Path(".env"), Path(".env.local"), Path(".env.runpod"),
    Path(".env.runpod.local"), CAMPAIGN / ".env.runpod.local",
)
# Only reviewed source files: never enumerate or hash credential/config files.
SOURCE_FILES = (
    Path("scripts/cm_runpod_readiness.py"),
    Path("cm_runpod_config.py"), Path("cm_runpod_client.py"),
    Path("cm_runpod_deploy.py"),
    Path("deliverables_n22_24/cm_selector_runpod_campaign_2026_08_24.py"),
    Path("deliverables_n22_24/cm_memo_runpod_campaign_2026_08_26.py"),
    CONTROLLERS / "runpod_smoke_controller.py",
    CONTROLLERS / "runpod_retry_cpu8_v1_controller.py",
    CONTROLLERS / "runpod_gpu_smoke_controller.py",
)
PACKAGES = ("requests", "numpy", "python-sat", "dd", "pytest")


def path_status(path: Path) -> str:
    """Inspect directory metadata only; do not follow a final symlink."""
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unavailable"
    if stat.S_ISLNK(mode):
        return "symlink_not_followed"
    if stat.S_ISREG(mode):
        return "regular_file"
    if stat.S_ISDIR(mode):
        return "directory"
    return "other"


def _has_link_parent(root: Path, relative: Path) -> bool:
    current = root
    for part in relative.parts:
        current = current / part
        # is_junction handles Windows reparse-point directory aliases too.
        if current.is_symlink() or current.is_junction():
            return True
    return False


def source_record(root: Path, relative: Path) -> dict:
    if relative not in SOURCE_FILES:
        raise ValueError("source is not on the reviewed allowlist")
    path = root / relative
    row = {"relative_path": relative.as_posix(), "status": path_status(path)}
    try:
        if _has_link_parent(root, relative) or not path.resolve().is_relative_to(root):
            row["status"] = "linked_source_refused"
        elif row["status"] == "regular_file":
            before = path.stat()
            payload = path.read_bytes()
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                row["status"] = "changed_during_read"
            else:
                row["sha256"] = hashlib.sha256(payload).hexdigest()
                row["bytes"] = len(payload)
    except OSError:
        row["status"] = "unavailable"
    return row


def git_identity(root: Path) -> dict:
    result = {}
    for name, argument in (("head", "HEAD"), ("top_level", "--show-toplevel")):
        try:
            proc = subprocess.run(
                ["git", "-c", "core.fsmonitor=false", "rev-parse", argument],
                cwd=root, capture_output=True, text=True, timeout=5, check=False,
            )
            value = proc.stdout.strip()
            if proc.returncode or (name == "head" and not re.fullmatch(r"[0-9a-f]{40,64}", value)):
                result[name] = "unavailable"
            else:
                result[name] = value
        except (OSError, subprocess.TimeoutExpired):
            result[name] = "unavailable"
    # Do not enumerate status, remotes, ignored files, git config or credentials.
    return result


def inventory(root: Path, environment_names: Iterable[str] | None = None) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project root must be a directory")
    # Iterate names only. Even a membership check on os.environ can fetch a
    # value internally, so build a set of keys without indexing the mapping.
    names = frozenset(iter(os.environ) if environment_names is None else environment_names)
    versions = {}
    for package in PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not_installed_in_this_interpreter"
    return {
        "schema": "cm-runpod-offline-inventory/v1",
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "assessment": "offline_inventory_only_not_connection_validation",
        "project_root": str(root),
        "diagnostic_script_root": str(ROOT),
        "working_directory": str(Path.cwd()),
        "git": git_identity(root),
        "runtime": {
            "executable": sys.executable,
            "python": sys.version.split()[0],
            "prefix": sys.prefix,
            "expected_windows_venv": str(root / ".venv/Scripts/python.exe"),
            "expected_windows_venv_status": path_status(root / ".venv/Scripts/python.exe"),
            "using_expected_venv": Path(sys.prefix).resolve() == root / ".venv",
            "package_metadata_versions": versions,
            "native_backends_imported_or_tested": False,
        },
        "credential_file_metadata_only": [
            {"path": str(root / relative), "status": path_status(root / relative)}
            for relative in CREDENTIAL_CANDIDATES
        ],
        "process_environment_names_present": {name: name in names for name in ENV_NAMES},
        "source_files": [source_record(root, relative) for relative in SOURCE_FILES],
        "workflow_configuration": {
            "historical_disposable_campaign": {
                "loader": "cm_runpod_config.load_runpod_config",
                "existing_pod_id_required": False,
                "existing_worker_url_required": False,
                "transport": "REST v1 lifecycle; per-pod HTTP bootstrap/worker proxies",
            },
            "older_existing_worker_client": {
                "loader": "cm_runpod_config.load_runpod_config",
                "root_env_precedence_low_to_high": [str(path) for path in CREDENTIAL_CANDIDATES[:4]],
                "process_environment_overrides_files": True,
                "api_key_fallback_name": "RP_TOKEN",
                "worker_execution_requires": ["CM_RUNPOD_BASE_URL"],
                "pod_lifecycle_requires": ["RUNPOD_API_KEY (or RP_TOKEN)", "RUNPOD_POD_ID"],
                "warning": "Some client operations can start a pod; do not use as an offline check.",
            },
            "memory_smoke_controller": {
                "credential_path": str(root / CAMPAIGN / ".env.runpod.local"),
                "credential_name": "RUNPOD_API_KEY",
                "uses_root_dotenv_or_process_environment_for_key": False,
                "existing_pod_id_required": False,
                "existing_worker_url_required": False,
                "transport": "port-free approved bundle; REST lifecycle and bounded log retrieval",
            },
        },
        "limits": [
            "File/name presence does not establish contents, nonempty values, valid credentials or account permissions.",
            "Package metadata does not prove imports or CUDD/native solver availability.",
            "Workflow descriptions document the reviewed code; compare source hashes if another task changes it.",
            "Source hashes are observations, not an executable snapshot or historical-source reconstruction.",
            "No network, authentication, account, pod, billing or resource readiness was tested.",
        ],
        "credential_contents_read": False,
        "environment_values_read": False,
        "network_requests_performed": False,
        "authenticated_connectivity_tested": False,
        "resource_mutations_performed": False,
    }


def write_report(root: Path, output: Path, report: dict) -> Path:
    """Create a new JSON report inside this project; never overwrite a file."""
    root = root.resolve(strict=True)
    path = output if output.is_absolute() else root / output
    path = path.absolute()
    if not path.is_relative_to(root) or ".." in path.parts:
        raise ValueError("report must be inside the selected project")
    relative = path.relative_to(root)
    if path.suffix.lower() != ".json" or any(part.startswith(".") for part in relative.parts):
        raise ValueError("report must be a non-hidden JSON path")
    if _has_link_parent(root, relative) or not path.resolve().is_relative_to(root):
        raise ValueError("linked report paths are refused")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, help="optional new JSON path inside the selected project")
    args = parser.parse_args(argv)
    try:
        report = inventory(args.project_root)
        if args.output is not None:
            write_report(args.project_root, args.output, report)
    except (OSError, ValueError) as exc:
        # Never include an arbitrary exception message or request/config object.
        print(f"Offline inventory failed ({type(exc).__name__}); check paths and overwrite policy.", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
