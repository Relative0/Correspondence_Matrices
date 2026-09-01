"""Build and validate the deterministic first-five two-chapter RunPod smoke bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
from typing import Any
import zipfile


HERE = Path(__file__).resolve().parent
FACTORY = HERE.parent
DEEP_ROOT = FACTORY / "deep_series"
OUTPUT_ROOT = HERE / "deep_series_smoke_v1"
PROPOSAL_ID = "cm-video-deep-series-first5-smoke-remote-v1"
BATCH_ID = "cm-video-deep-series-first5-smoke-v1"
PACKAGE_ID = "cm-video-deep-series-first5-smoke-linux-v1"
BUNDLE_STEM = "cm-video-deep-series-first5-smoke-v1"
JOB_SUFFIX = "smoke"
REVIEW_PATH = DEEP_ROOT / "content_review_request.json"
REQUIRED_REVIEW_STATUS = "review_requested"
TARGETS = (
    ("conceptual-vs-measured", "c01"),
    ("what-is-explicit-cm", "c01"),
)
RUNTIME_FILES = (
    "deep_series_smoke_worker.py",
    "deep_series_smoke_batch.py",
    "deep_series_smoke_bootstrap.sh",
    "requirements.lock",
)


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


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def zip_entry(path: str, payload: bytes) -> tuple[zipfile.ZipInfo, bytes]:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info, payload


def safe_pop_files(pop_root: Path) -> list[Path]:
    roots = [pop_root / "pop_video"]
    files = [pop_root / "package.json", pop_root / "package-lock.json"]
    for root in roots:
        files.extend(path for path in root.rglob("*") if path.is_file())
    selected = []
    for path in sorted(set(files)):
        relative = path.relative_to(pop_root)
        if "__pycache__" in relative.parts or path.suffix.lower() in {".pyc", ".pyo"}:
            continue
        if path.stat().st_size > 5_000_000:
            raise ValueError(f"unexpected large POP runtime file: {path}")
        selected.append(path)
    return selected


def build(pop_root: Path, output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    review = json.loads(REVIEW_PATH.read_text("utf-8"))
    if review["status"] != REQUIRED_REVIEW_STATUS:
        raise ValueError("current content review request is missing")
    entries: dict[str, bytes] = {}
    for name in RUNTIME_FILES:
        entries[f"runpod/{name}"] = (HERE / name).read_bytes()
    for path in safe_pop_files(pop_root):
        entries[(PurePosixPath("pop") / path.relative_to(pop_root).as_posix()).as_posix()] = path.read_bytes()

    jobs: list[dict[str, Any]] = []
    for video_id, chapter_id in TARGETS:
        source = DEEP_ROOT / "episodes" / video_id / "chapters" / chapter_id / "executable_render_contract.json"
        contract_path = f"cm/contracts/{video_id}-{chapter_id}.json"
        contract_payload = source.read_bytes()
        entries[contract_path] = contract_payload
        contract = json.loads(contract_payload)
        job_id = f"{video_id}-{chapter_id}-{JOB_SUFFIX}"
        job = {
            "schema_version": "1.0",
            "job_id": job_id,
            "video_id": video_id,
            "chapter_id": chapter_id,
            "contract_path": contract_path,
            "contract_sha256": sha256_bytes(contract_payload),
            "cache_identity": contract["chapter_cache_identity"],
            "frame_contract": contract["frame_contract"],
            "expected_primitives": sorted({scene["primitive"] for scene in contract["resolved_scenes"]}),
            "render_workers": 4,
            "bible_content_hash": review["bible_content_hash"],
            "review_manifest_sha256": review["review_manifest_sha256"],
        }
        job_payload = json_bytes(job)
        job_path = f"cm/jobs/{job_id}.json"
        entries[job_path] = job_payload
        jobs.append({**job, "path": job_path, "sha256": sha256_bytes(job_payload)})

    batch = {
        "schema_version": "1.0",
        "batch_id": BATCH_ID,
        "proposal_id": PROPOSAL_ID,
        "status": "local_bundle_ready_remote_not_authorized",
        "remote_or_paid_work_authorized": False,
        "bible_content_hash": review["bible_content_hash"],
        "review_manifest_sha256": review["review_manifest_sha256"],
        "ordered_job_ids": [item["job_id"] for item in jobs],
        "job_hashes": {item["job_id"]: item["sha256"] for item in jobs},
        "total_frames": sum(item["frame_contract"]["duration_frames"] for item in jobs),
        "expected_primitive_coverage": sorted({primitive for item in jobs for primitive in item["expected_primitives"]}),
    }
    batch_payload = json_bytes(batch)
    entries["cm/batch_manifest.json"] = batch_payload
    entries["cm/content_review_request.json"] = json_bytes(review)

    file_manifest = [
        {"path": path, "size": len(payload), "sha256": sha256_bytes(payload)}
        for path, payload in sorted(entries.items())
    ]
    package = {
        "schema_version": "1.0",
        "package_id": PACKAGE_ID,
        "batch_id": BATCH_ID,
        "batch_manifest_sha256": sha256_bytes(batch_payload),
        "bible_content_hash": review["bible_content_hash"],
        "review_manifest_sha256": review["review_manifest_sha256"],
        "base_image": "python:3.10.15-slim-bookworm@sha256:97ff6fda70178dee6c144d41030fb88b6ec86d75e1c517fe96b8f62094ea7ac2",
        "files": file_manifest,
        "payload_sha256": sha256_bytes(canonical_bytes(file_manifest)),
        "expected_outputs": ["batch_result.json", "*/render_result.json", "*/*.mp4", "*/previews/*.png"],
    }
    output_root.mkdir(parents=True, exist_ok=True)
    temporary = output_root / "bundle.zip.tmp"
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, payload in sorted(entries.items()):
            info, data = zip_entry(path, payload)
            archive.writestr(info, data)
        info, data = zip_entry("package_manifest.json", json_bytes(package))
        archive.writestr(info, data)
    bundle_hash = sha256(temporary)
    bundle_name = f"{BUNDLE_STEM}-{bundle_hash[:16]}.zip"
    addressed = output_root / bundle_name
    os.replace(temporary, addressed)
    shutil.copyfile(addressed, output_root / "bundle.zip")
    (output_root / "batch_manifest.json").write_bytes(batch_payload)
    (output_root / "package_manifest.json").write_bytes(json_bytes(package))
    audit = {
        "schema_version": "1.0",
        "status": "passed",
        "credential_values_included": False,
        "selected_files": len(file_manifest),
        "selected_bytes": sum(item["size"] for item in file_manifest),
        "not_included": [
            "RUNPOD_API_KEY value", ".env files", "git metadata", "local databases",
            "node_modules and caches", "unrelated CM material", "episode narration audio",
        ],
    }
    (output_root / "exclusion_audit.json").write_bytes(json_bytes(audit))
    record = {
        "schema_version": "1.0",
        "status": "ready_local_only_remote_not_authorized",
        "proposal_id": PROPOSAL_ID,
        "bundle": bundle_name,
        "bundle_sha256": bundle_hash,
        "bundle_bytes": addressed.stat().st_size,
        "payload_sha256": package["payload_sha256"],
        "batch_manifest_sha256": package["batch_manifest_sha256"],
        "bible_content_hash": review["bible_content_hash"],
        "review_manifest_sha256": review["review_manifest_sha256"],
        "ordered_job_ids": batch["ordered_job_ids"],
        "total_frames": batch["total_frames"],
        "cloud_uploaded": False,
        "runpod_resource_created": False,
    }
    (output_root / "bundle_record.json").write_bytes(json_bytes(record))
    validate(output_root, check_proposal=False)
    return record


def validate(output_root: Path = OUTPUT_ROOT, *, check_proposal: bool = True) -> None:
    record = json.loads((output_root / "bundle_record.json").read_text("utf-8"))
    proposal_path = output_root / "proposal.json"
    proposal = json.loads(proposal_path.read_text("utf-8")) if proposal_path.is_file() else None
    bundle = output_root / record["bundle"]
    if sha256(bundle) != record["bundle_sha256"]:
        raise ValueError("bundle identity is stale")
    if sha256(output_root / "batch_manifest.json") != record["batch_manifest_sha256"]:
        raise ValueError("batch identity is stale")
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate bundle paths")
        manifest = json.loads(archive.read("package_manifest.json"))
        for item in manifest["files"]:
            path = PurePosixPath(item["path"])
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("unsafe bundle path")
            payload = archive.read(item["path"])
            if len(payload) != item["size"] or sha256_bytes(payload) != item["sha256"]:
                raise ValueError(f"bundle entry mismatch: {item['path']}")
        if sha256_bytes(canonical_bytes(manifest["files"])) != record["payload_sha256"]:
            raise ValueError("bundle payload identity is stale")
        archived_batch = archive.read("cm/batch_manifest.json")
        if sha256_bytes(archived_batch) != record["batch_manifest_sha256"]:
            raise ValueError("archived batch identity is stale")
        forbidden = ("RUNPOD_API_KEY", "api_key=", "authorization: bearer")
        for name in names:
            if any(part.casefold().startswith(".env") for part in PurePosixPath(name).parts):
                raise ValueError(f"environment file in bundle: {name}")
            payload = archive.read(name)
            if any(token.lower().encode() in payload.lower() for token in forbidden):
                raise ValueError(f"credential-like material in bundle: {name}")
    if record["cloud_uploaded"] or record["runpod_resource_created"]:
        raise ValueError("local bundle record claims remote activity")
    if proposal is not None and check_proposal:
        immutable = proposal["immutable_inputs"]
        identity = proposal["content_identity"]
        if (
            proposal["proposal_id"] != record["proposal_id"]
            or proposal["remote_or_paid_work_authorized"] is not False
            or immutable["bundle_file"] != record["bundle"]
            or immutable["bundle_sha256"] != record["bundle_sha256"]
            or immutable["payload_sha256"] != record["payload_sha256"]
            or immutable["batch_manifest_sha256"] != record["batch_manifest_sha256"]
            or identity["bible_content_hash"] != record["bible_content_hash"]
            or identity["review_manifest_sha256"] != record["review_manifest_sha256"]
        ):
            raise ValueError("proposal and frozen bundle identities disagree")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "validate"))
    parser.add_argument("--pop-root", type=Path)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    if args.command == "build":
        if args.pop_root is None:
            parser.error("build requires --pop-root")
        print(json.dumps(build(args.pop_root.resolve(), args.output_root.resolve()), indent=2))
    else:
        validate(args.output_root.resolve())


if __name__ == "__main__":
    main()
