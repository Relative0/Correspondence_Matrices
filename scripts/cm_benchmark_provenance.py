"""Exact-source provenance helpers for CM benchmark evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from cmbench.reporting.provenance import sha256_file


def source_hashes(repo_root: Path, relative_paths: Iterable[str]) -> dict[str, str]:
    return {
        relative_path: sha256_file(repo_root / relative_path)
        for relative_path in relative_paths
    }


def capture_source_snapshot(
    repo_root: Path,
    destination: Path,
    relative_paths: Iterable[str],
) -> dict:
    """Copy exact benchmark sources and write a content-hash manifest.

    The destination is created exclusively. Existing paths are refused so a
    benchmark rerun cannot silently replace the sources that produced evidence.
    """
    paths = tuple(dict.fromkeys(relative_paths))
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite source snapshot: {destination}")
    # Read and validate the complete source set before creating the destination.
    # A missing/unreadable later source must not strand a partial snapshot that
    # then blocks a corrected rerun under the fail-closed overwrite policy.
    payloads = [
        (relative_path, (repo_root / relative_path).read_bytes())
        for relative_path in paths
    ]
    destination.mkdir(parents=True)
    files = []
    for relative_path, payload in payloads:
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        files.append(
            {
                "path": relative_path,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "format": "cm-benchmark-exact-source-snapshot-v1",
        "files": files,
    }
    manifest_path = destination / "source_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "directory": str(destination),
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "files": files,
    }
