"""Create a deterministic, allowlisted, content-addressed Linux render bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
from typing import Any
import zipfile


HERE = Path(__file__).resolve().parent
FACTORY = HERE.parent


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision(root: Path, fallback_head: str | None = None) -> dict[str, Any]:
    def run(*args: str) -> str:
        proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", check=True)
        return proc.stdout
    try:
        head = run("rev-parse", "HEAD").strip()
        status = run("status", "--short", "--untracked-files=no")
        diff = run("diff", "--binary", "--no-ext-diff")
        return {"head": head, "dirty": bool(status.strip()), "tracked_diff_sha256": sha256_bytes(diff.encode("utf-8"))}
    except subprocess.CalledProcessError:
        if fallback_head is None:
            raise
        return {
            "head": fallback_head, "dirty": True, "tracked_diff_sha256": None,
            "note": "git metadata was sandbox-inaccessible; every selected byte is bound below",
        }


def normalized_bytes(archive_path: str, source: Path) -> bytes:
    data = source.read_bytes()
    if archive_path.startswith("cm/proofs/") and archive_path.endswith("/assembly.spec.json"):
        value = json.loads(data.decode("utf-8"))
        video_id = PurePosixPath(archive_path).parts[2]
        value["slots"][0]["source"]["request"]["spec"] = (
            f"${{BUNDLE_ROOT}}/cm/proofs/{video_id}/resolved.spec.json"
        )
        data = json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    if b"C:\\\\" in data or b"C:\\" in data:
        raise ValueError(f"Windows absolute path remains in allowlisted payload: {archive_path}")
    return data


def expand(allowlist: dict[str, Any], roots: dict[str, Path]) -> list[tuple[str, bytes, str]]:
    selected: dict[str, tuple[bytes, str]] = {}
    denied = {name.lower() for name in allowlist["deny_names"]}
    suffixes = {suffix.lower() for suffix in allowlist["deny_suffixes"]}
    for rule in allowlist["patterns"]:
        root_id = rule["root"]
        root = roots[root_id].resolve()
        if not root.is_dir():
            raise ValueError(f"source root does not exist: {root_id}={root}")
        matches = sorted(path for path in root.glob(rule["glob"]) if path.is_file())
        if not matches:
            raise ValueError(f"allowlist pattern matched nothing: {root_id}:{rule['glob']}")
        for path in matches:
            if path.is_symlink():
                raise ValueError(f"symlink refused: {path}")
            relative = path.relative_to(root)
            if any(part.lower() in denied for part in relative.parts) or path.suffix.lower() in suffixes:
                raise ValueError(f"deny rule matched allowlisted file: {path}")
            if path.stat().st_size > allowlist["max_file_bytes"]:
                raise ValueError(f"allowlisted file exceeds size cap: {path}")
            archive_path = (PurePosixPath(allowlist["roots"][root_id]) / PurePosixPath(relative.as_posix())).as_posix()
            selected[archive_path] = (normalized_bytes(archive_path, path), rule["category"])
    return [(path, *selected[path]) for path in sorted(selected)]


def zip_entry(path: str, data: bytes) -> tuple[zipfile.ZipInfo, bytes]:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info, data


def build(ivc_root: Path, pop_root: Path, dist: Path, *,
          ivc_head: str | None = None, pop_head: str | None = None) -> dict[str, Any]:
    allowlist = json.loads((HERE / "allowlist.json").read_text("utf-8"))
    roots = {"cm": FACTORY, "ivc": ivc_root, "pop": pop_root, "runpod": HERE}
    selected = expand(allowlist, roots)
    entries = [
        {"path": path, "size": len(data), "sha256": sha256_bytes(data), "category": category}
        for path, data, category in selected
    ]
    batch_path = FACTORY / "batch_manifest.json"
    dependencies = {
        "python_requirements_sha256": sha256(HERE / "requirements.lock"),
        "node_package_lock_sha256": sha256(pop_root / "package-lock.json"),
        "base_image": "python:3.10.15-slim-bookworm@sha256:97ff6fda70178dee6c144d41030fb88b6ec86d75e1c517fe96b8f62094ea7ac2",
        "ffmpeg": "Debian bookworm package, resolved and recorded at image build",
        "chromium": "Playwright 1.53.1 Chromium, resolved by package-lock and recorded at image build",
        "fonts": allowlist["system_fonts"],
    }
    manifest = {
        "schema_version": "1.0", "package_id": "cm-video-level1-proof3-linux-v1",
        "batch_id": "cm-video-level1-proof3-v1",
        "batch_manifest_sha256": sha256(batch_path),
        "source_revisions": {
            "cm": git_revision(FACTORY.parents[1]), "ivc": git_revision(ivc_root, ivc_head),
            "pop": git_revision(pop_root, pop_head),
        },
        "dependencies": dependencies,
        "files": entries,
        "payload_sha256": sha256_bytes(canonical_bytes(entries)),
        "expected_outputs": [
            "render_result.json", "progress.jsonl", "*-16x9.mp4", "provenance.json",
            "gap_report.json", "cadence_report.json", "previews/*.png",
        ],
    }
    manifest_data = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    dist.mkdir(parents=True, exist_ok=True)
    temporary = dist / "bundle.zip.tmp"
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, data, _category in selected:
            info, payload = zip_entry(path, data)
            archive.writestr(info, payload)
        info, payload = zip_entry("package_manifest.json", manifest_data)
        archive.writestr(info, payload)
    bundle_sha = sha256(temporary)
    addressed = dist / f"cm-video-level1-proof3-linux-v1-{bundle_sha[:16]}.zip"
    os.replace(temporary, addressed)
    stable = dist / "bundle.zip"
    shutil.copyfile(addressed, stable)
    exclusion = {
        "schema_version": "1.0", "status": "passed", "selected_files": len(entries),
        "selected_bytes": sum(entry["size"] for entry in entries),
        "denied_names": allowlist["deny_names"], "denied_suffixes": allowlist["deny_suffixes"],
        "not_included": [
            ".env* and credentials", "git metadata", "local databases", "node_modules and caches",
            "proof MP4/output trees", "historical runs", "unrelated CM corpora",
        ],
        "windows_absolute_paths": 0,
    }
    record = {
        "schema_version": "1.0", "status": "ready_local_only", "bundle": addressed.name,
        "bundle_sha256": bundle_sha, "bundle_bytes": addressed.stat().st_size,
        "payload_sha256": manifest["payload_sha256"],
        "batch_manifest_sha256": manifest["batch_manifest_sha256"],
        "container_built": False, "cloud_uploaded": False,
    }
    (dist / "package_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (dist / "exclusion_audit.json").write_text(json.dumps(exclusion, indent=2) + "\n", encoding="utf-8")
    (dist / "bundle_record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ivc-root", type=Path, required=True)
    parser.add_argument("--pop-root", type=Path, required=True)
    parser.add_argument("--dist", type=Path, default=HERE / "dist")
    parser.add_argument("--ivc-head", default=None)
    parser.add_argument("--pop-head", default=None)
    args = parser.parse_args()
    print(json.dumps(build(
        args.ivc_root.resolve(), args.pop_root.resolve(), args.dist.resolve(),
        ivc_head=args.ivc_head, pop_head=args.pop_head,
    ), indent=2))


if __name__ == "__main__":
    main()
