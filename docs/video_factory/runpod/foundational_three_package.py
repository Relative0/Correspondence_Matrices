"""Create the exact, secret-free RunPod v3 bundle and proposal for three narrated CM videos.

This command performs local packaging only.  It never reads RUNPOD_API_KEY,
contacts RunPod, creates a resource, or performs paid work.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
FACTORY = ROOT / "docs" / "video_factory"
OUT = FACTORY / "runpod" / "foundational_three_v3"
POP = ROOT.parent / "PoP" / "Tools" / "POP-Video-Creator"
PRODUCTION = FACTORY / "deep_series" / "foundational_cm_production_v2"

SOURCE_FILES = {
    ROOT / "docs/video_factory/foundational_cm_production.py": "repo/docs/video_factory/foundational_cm_production.py",
    ROOT / "docs/video_factory/foundational_cm_narration.py": "repo/docs/video_factory/foundational_cm_narration.py",
    ROOT / "docs/video_factory/deep_series/episodes/operator-cms-from-truth-tables/revision_v3/SCRIPT_V3.md": "repo/docs/video_factory/deep_series/episodes/operator-cms-from-truth-tables/revision_v3/SCRIPT_V3.md",
    ROOT / "docs/video_factory/deep_series/episodes/operator-cms-from-truth-tables/revision_v3/VISUAL_AND_PRODUCTION_SPEC_V3.md": "repo/docs/video_factory/deep_series/episodes/operator-cms-from-truth-tables/revision_v3/VISUAL_AND_PRODUCTION_SPEC_V3.md",
    ROOT / "docs/video_factory/deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v3/SCRIPT_V3.md": "repo/docs/video_factory/deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v3/SCRIPT_V3.md",
    ROOT / "docs/video_factory/deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v3/VISUAL_AND_PRODUCTION_SPEC_V3.md": "repo/docs/video_factory/deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v3/VISUAL_AND_PRODUCTION_SPEC_V3.md",
    ROOT / "docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v4/SCRIPT_V4.md": "repo/docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v4/SCRIPT_V4.md",
    ROOT / "docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v4/VISUAL_AND_PRODUCTION_SPEC_V4.md": "repo/docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v4/VISUAL_AND_PRODUCTION_SPEC_V4.md",
    ROOT / "docs/video_factory/sources/CM_PAPER_SOURCE_NOTE_2026_09_01.md": "repo/docs/video_factory/sources/CM_PAPER_SOURCE_NOTE_2026_09_01.md",
    PRODUCTION / "MATH_TYPOGRAPHY_CONTRACT_V2.json": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/MATH_TYPOGRAPHY_CONTRACT_V2.json",
    PRODUCTION / "PRODUCTION_MANIFEST_V2.json": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/PRODUCTION_MANIFEST_V2.json",
    PRODUCTION / "PREVIEW_REPORT_V2.json": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/PREVIEW_REPORT_V2.json",
    PRODUCTION / "VALIDATION_REPORT_V2.json": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/VALIDATION_REPORT_V2.json",
    PRODUCTION / "NARRATION_AND_MUX_PLAN_V2.md": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/NARRATION_AND_MUX_PLAN_V2.md",
    PRODUCTION / "narration/auditions/AUDITION_MANIFEST_V2.json": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/narration/auditions/AUDITION_MANIFEST_V2.json",
    PRODUCTION / "narration/auditions/af_heart.wav": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/narration/auditions/af_heart.wav",
    PRODUCTION / "narration/auditions/af_bella.wav": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/narration/auditions/af_bella.wav",
    PRODUCTION / "narration/auditions/bf_emma.wav": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/narration/auditions/bf_emma.wav",
    PRODUCTION / "episodes/operator-cms-from-truth-tables/PRODUCTION_CONTRACT_V2.json": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/episodes/operator-cms-from-truth-tables/PRODUCTION_CONTRACT_V2.json",
    PRODUCTION / "episodes/operator-cms-from-truth-tables/NARRATION_CONTRACT_V2.json": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/episodes/operator-cms-from-truth-tables/NARRATION_CONTRACT_V2.json",
    PRODUCTION / "episodes/logical-matrices-to-higher-dimensional-cms/PRODUCTION_CONTRACT_V2.json": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/episodes/logical-matrices-to-higher-dimensional-cms/PRODUCTION_CONTRACT_V2.json",
    PRODUCTION / "episodes/logical-matrices-to-higher-dimensional-cms/NARRATION_CONTRACT_V2.json": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/episodes/logical-matrices-to-higher-dimensional-cms/NARRATION_CONTRACT_V2.json",
    PRODUCTION / "episodes/what-is-explicit-cm/PRODUCTION_CONTRACT_V2.json": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/episodes/what-is-explicit-cm/PRODUCTION_CONTRACT_V2.json",
    PRODUCTION / "episodes/what-is-explicit-cm/NARRATION_CONTRACT_V2.json": "repo/docs/video_factory/deep_series/foundational_cm_production_v2/episodes/what-is-explicit-cm/NARRATION_CONTRACT_V2.json",
    POP / "pop_video/render/frame_driver.js": "pop/pop_video/render/frame_driver.js",
    POP / "package.json": "pop/package.json",
    POP / "package-lock.json": "pop/package-lock.json",
}

for preview_path in (
    PRODUCTION / "episodes/operator-cms-from-truth-tables/previews/CONTACT_SHEET.png",
    PRODUCTION / "episodes/operator-cms-from-truth-tables/previews/operator-cms-from-truth-tables.silent-animatic.mp4",
    PRODUCTION / "episodes/logical-matrices-to-higher-dimensional-cms/previews/CONTACT_SHEET.png",
    PRODUCTION / "episodes/logical-matrices-to-higher-dimensional-cms/previews/logical-matrices-to-higher-dimensional-cms.silent-animatic.mp4",
    PRODUCTION / "episodes/what-is-explicit-cm/previews/CONTACT_SHEET.png",
    PRODUCTION / "episodes/what-is-explicit-cm/previews/what-is-explicit-cm.silent-animatic.mp4",
):
    SOURCE_FILES[preview_path] = "repo/" + preview_path.relative_to(ROOT).as_posix()

BOOTSTRAP = r'''#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export CM_REMOTE_WORK=1
BUNDLE_ROOT="${CM_FOUNDATIONAL_BUNDLE_ROOT:-/workspace/bundle}"
OUTPUT_ROOT="${CM_FOUNDATIONAL_OUTPUT_ROOT:-/workspace/foundational-output}"
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl ffmpeg fontconfig fonts-dejavu-core fonts-liberation nodejs npm unzip zip tini
rm -rf /var/lib/apt/lists/*
python -m pip install --no-cache-dir --requirement "$BUNDLE_ROOT/runpod/requirements.lock"
npm ci --prefix "$BUNDLE_ROOT/pop"
cd "$BUNDLE_ROOT/pop"
npx playwright install --with-deps chromium
export CM_POP_ROOT="$BUNDLE_ROOT/pop"
cd "$BUNDLE_ROOT/repo"
python docs/video_factory/foundational_cm_production.py validate > /workspace/foundational-validation.json
python -c 'import json; raise SystemExit(0 if json.load(open("/workspace/foundational-validation.json", encoding="utf-8"))["status"] == "pass" else 1)'
python docs/video_factory/foundational_cm_production.py render-full --output-root "$OUTPUT_ROOT" --width 1920 --height 1080 --workers 4
mkdir -p docs/video_factory/tmp/kokoro
curl -L --fail --retry 3 -o docs/video_factory/tmp/kokoro/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx
curl -L --fail --retry 3 -o docs/video_factory/tmp/kokoro/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin
echo "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a  docs/video_factory/tmp/kokoro/kokoro-v1.0.onnx" | sha256sum -c -
echo "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d  docs/video_factory/tmp/kokoro/voices-v1.0.bin" | sha256sum -c -
for VIDEO_ID in operator-cms-from-truth-tables logical-matrices-to-higher-dimensional-cms what-is-explicit-cm; do
  python docs/video_factory/foundational_cm_narration.py mux-master --video-id "$VIDEO_ID" --voice af_heart --speed 0.98 --silent-master "$OUTPUT_ROOT/$VIDEO_ID/$VIDEO_ID.silent-master.mp4"
done
cp -r docs/video_factory/deep_series/foundational_cm_production_v2/narration "$OUTPUT_ROOT/narration"
cd "$OUTPUT_ROOT"
zip -q -r /workspace/foundational-three-results.zip .
sha256sum /workspace/foundational-three-results.zip > /workspace/foundational-three-results.zip.sha256
'''

REQUIREMENTS = "fonttools==4.62.1\nkokoro-onnx==0.6.1\nsoundfile==0.14.0\n"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(2026, 9, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def build() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    for path in SOURCE_FILES:
        if not path.is_file():
            raise FileNotFoundError(path)
    bundle = OUT / "bundle.zip"
    records = []
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, arcname in sorted(SOURCE_FILES.items(), key=lambda item: item[1]):
            archive.writestr(zip_info(arcname), source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            records.append({"path": arcname, "sha256": sha256(source), "bytes": source.stat().st_size})
        archive.writestr(zip_info("runpod/bootstrap.sh"), BOOTSTRAP, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        archive.writestr(zip_info("runpod/requirements.lock"), REQUIREMENTS, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        records.extend([
            {"path": "runpod/bootstrap.sh", "sha256": hashlib.sha256(BOOTSTRAP.encode()).hexdigest(), "bytes": len(BOOTSTRAP.encode())},
            {"path": "runpod/requirements.lock", "sha256": hashlib.sha256(REQUIREMENTS.encode()).hexdigest(), "bytes": len(REQUIREMENTS.encode())},
        ])
    bundle_sha = sha256(bundle)
    package = {
        "schema_version": "1.0", "status": "packaged_not_authorized",
        "bundle": {"path": bundle.name, "sha256": bundle_sha, "bytes": bundle.stat().st_size},
        "entries": records, "entry_count": len(records),
        "secret_files_included": False,
        "forbidden_patterns": [".env", "RUNPOD_API_KEY", "token", "credential cache"],
    }
    package["package_manifest_sha256"] = canonical_hash(package)
    write_json(OUT / "package_manifest.json", package)

    preview = json.loads((PRODUCTION / "PREVIEW_REPORT_V2.json").read_text(encoding="utf-8"))
    production_manifest = json.loads((PRODUCTION / "PRODUCTION_MANIFEST_V2.json").read_text(encoding="utf-8"))
    content_records = [
        item for item in records
        if "/revision_v3/" in item["path"]
        or "/revision_v4/SCRIPT_V4.md" in item["path"]
        or item["path"].endswith("CM_PAPER_SOURCE_NOTE_2026_09_01.md")
    ]
    content_identity = canonical_hash(content_records)
    total_frames = int(production_manifest["total_duration_s"] * 30)
    measured_floor_fps = 4.4176
    render_seconds = total_frames / measured_floor_fps
    setup_encode_allowance = 2400
    estimated_seconds = render_seconds + setup_encode_allowance
    rate = 0.27
    proposal = {
        "schema_version": "1.0",
        "proposal_id": "cm-video-foundational-three-production-remote-v3",
        "status": "exact_authorization_requested",
        "remote_or_paid_work_authorized": False,
        "purpose": "Render, narrate, caption, mux, and QA three symbol-safe 1920x1080 foundational CM review masters using the exact bra-ket revisions and the provisional offline neural voice af_heart. Publication and unrelated episodes are excluded.",
        "content_identity": {
            "paper_audited_script_and_visual_identity": content_identity,
            "production_package_identity": production_manifest["package_identity_sha256"],
            "scope": [x["video_id"] for x in production_manifest["episodes"]],
        },
        "immutable_inputs": {
            "bundle_file": bundle.name, "bundle_sha256": bundle_sha, "bundle_bytes": bundle.stat().st_size,
            "package_manifest_sha256": package["package_manifest_sha256"],
            "controller_core_file": "../foundational_three_execute.py",
            "controller_core_sha256": sha256(FACTORY / "runpod" / "foundational_three_execute.py"),
        },
        "render_contract": {
            "episodes": 3, "scenes": sum(x["settled_frames"] for x in preview["episodes"]),
            "width": 1920, "height": 1080, "fps": 30,
            "total_frames": total_frames, "duration_seconds": production_manifest["total_duration_s"],
            "audio": True, "narrator": "offline Kokoro ONNX af_heart at base speed 0.98",
            "audio_contract": "48 kHz mono AAC in master; -18 LUFS target; -1.5 dBTP; embedded English captions plus sidecar WebVTT",
            "font": "embedded DejaVu Sans/Mono with pre-render cmap audit",
            "matrix_brackets": "drawn geometry",
            "required_qa": ["exact hashes", "frame count and media contract", "opening/middle/final decoded frames", "remote font cmap audit", "bra-ket symbol specimen", "cue-window fit", "48 kHz mono narration", "embedded and sidecar captions", "full narrated-master decode", "owned-pod cleanup"],
        },
        "resource": {
            "provider": "RunPod", "product": "Pod", "cloud": "SECURE", "gpu_id": "NVIDIA RTX A5000", "gpu_count": 1,
            "minimum_vcpus": 4, "minimum_ram_gb": 8, "container_disk_gb": 30, "volume_gb": 0,
            "base_image": "python:3.10.15-slim-bookworm@sha256:97ff6fda70178dee6c144d41030fb88b6ec86d75e1c517fe96b8f62094ea7ac2",
            "ports": ["22/tcp"],
            "mismatch_policy": "Delete immediately without rendering if exact owned resource checks fail.",
        },
        "quote": {
            "rate_usd_per_hour": rate, "pricing_checked_date": "2026-09-01",
            "source": "https://www.runpod.io/pricing", "estimate_is_not_a_charge": True,
        },
        "cost_model": {
            "measured_floor_frames_per_second": measured_floor_fps,
            "render_seconds_estimate": round(render_seconds, 1),
            "setup_encode_download_allowance_seconds": setup_encode_allowance,
            "estimated_runtime_seconds": round(estimated_seconds, 1),
            "estimated_compute_usd": round(estimated_seconds / 3600 * rate, 4),
        },
        "v3_revision": {
            "prior_proposal_id": "cm-video-foundational-three-production-remote-v2",
            "prior_run_completed": True,
            "prior_owned_pod_absent_verified": True,
            "changes": [
                "Add the paper's four basis dyads and a readable 4x4 table of all sixteen named operator CMs.",
                "Show ket-bra outer products for base logical matrices and tensor construction for the 4x4 logical matrix.",
                "Add offline neural narration, real retrieval pauses, sidecar and embedded captions, and narrated-master mux QA."
            ]
        },
        "authorization_ceiling": {
            "maximum_total_runpod_spend_usd": 1.25, "maximum_pod_creates": 1, "maximum_parallel_pods": 1,
            "maximum_runtime_seconds": 14400,
            "retry_policy": "No second pod create. Resume inside the one owned pod only; a failed or deleted pod requires a new exact proposal.",
            "no_other_paid_services": True,
        },
        "transport_and_cleanup": {
            "credential_reference": "existing RUNPOD_API_KEY environment variable; never print, persist, bundle, or transmit its value except as the RunPod API authorization header",
            "upload": "one hash-bound bundle via SFTP; verify SHA-256 before extraction",
            "download": "one bounded result ZIP plus SHA-256; reject unsafe paths or unexpected files",
            "publish": False, "commit_or_push": False, "delete_on_terminal": True,
            "final_owned_inventory_reconciliation": True,
            "detached_render_monitor": "The render runs as an in-pod detached job. The controller polls its exit record, reconnects after transient SSH loss, and downloads only after an exact zero exit.",
        },
        "authorization_effect": "Approval authorizes only one new Secure A5000 pod/create for the exact three revised narrated review masters in this bundle, including local-in-pod Kokoro synthesis and mux, up to an additional $1.25. It does not authorize any external voice service, publication, other episodes, commit, or push.",
    }
    proposal["proposal_sha256"] = canonical_hash(proposal)
    write_json(OUT / "proposal.json", proposal)
    approval = (
        "I approve proposal `cm-video-foundational-three-production-remote-v3` exactly as stated, "
        f"proposal identity `{proposal['proposal_sha256']}`, including at most $1.25 RunPod spend."
    )
    (OUT / "PROPOSAL.md").write_text(
        "# Foundational CM three-video narrated RunPod production proposal\n\n"
        f"Proposal identity: `{proposal['proposal_sha256']}`\n\n"
        f"Bundle: `{bundle.name}` / `{bundle_sha}`\n\n"
        f"Scope: **3 narrated review masters / {total_frames} frames / {production_manifest['total_duration_s']/60:.2f} minutes**\n\n"
        f"Estimated compute / hard ceiling: **${proposal['cost_model']['estimated_compute_usd']:.2f} / $1.25**\n\n"
        "No RunPod resource has been created and no paid work is authorized by this proposal.\n\n"
        "## Exact approval text\n\n" + approval + "\n",
        encoding="utf-8",
    )
    return {"package": package, "proposal": proposal, "approval_text": approval}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=False))
