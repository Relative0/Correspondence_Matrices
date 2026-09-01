"""Freeze and validate the exact first-five RunPod production proposal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any
import zipfile

import deep_series_first5_package as first5_package


HERE = Path(__file__).resolve().parent
ROOT = HERE / "deep_series_first5_v1"
REVIEW = HERE.parent / "deep_series" / "first_five_review" / "manifest.json"
SMOKE_VERIFICATION = (
    HERE
    / "deep_series_smoke_v1"
    / "remote"
    / "runpod-first5-smoke-v1-20260831-140258"
    / "attempt-2"
    / "LOCAL_VERIFICATION.json"
)
PROPOSAL_ID = "cm-video-deep-series-first5-production-remote-v1"


class ProposalError(RuntimeError):
    """Raised when the proposal no longer matches its frozen inputs."""


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def frozen_jobs(bundle: Path, record: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = []
    with zipfile.ZipFile(bundle) as archive:
        batch = json.loads(archive.read("cm/batch_manifest.json"))
        for job_id in batch["ordered_job_ids"]:
            job = json.loads(archive.read(f"cm/jobs/{job_id}.json"))
            jobs.append(
                {
                    "job_id": job_id,
                    "video_id": job["video_id"],
                    "chapter_id": job["chapter_id"],
                    "duration_frames": job["frame_contract"]["duration_frames"],
                    "duration_seconds": round(
                        job["frame_contract"]["duration_frames"]
                        / job["frame_contract"]["fps"],
                        4,
                    ),
                    "primitive_coverage": job["expected_primitives"],
                    "job_sha256": batch["job_hashes"][job_id],
                }
            )
    if [item["job_id"] for item in jobs] != record["ordered_job_ids"]:
        raise ProposalError("bundle job order does not match its record")
    return jobs


def build() -> dict[str, Any]:
    record = load(ROOT / "bundle_record.json")
    review = load(REVIEW)
    quote = load(ROOT / "quote.json")
    smoke = load(SMOKE_VERIFICATION)
    bundle = ROOT / record["bundle"]
    jobs = frozen_jobs(bundle, record)
    measured_fps = min(item["frames_per_second"] for item in smoke["media"])
    estimated_render_seconds = record["total_frames"] / measured_fps
    overhead_seconds = 1200
    estimated_runtime_seconds = estimated_render_seconds + overhead_seconds
    estimated_compute = estimated_runtime_seconds / 3600 * quote["rate_usd_per_hour"]
    proposal: dict[str, Any] = {
        "schema_version": "1.0",
        "proposal_id": PROPOSAL_ID,
        "status": "exact_authorization_requested_after_scoped_content_approval",
        "remote_or_paid_work_authorized": False,
        "purpose": "Render and QA all 17 silent visual chapter masters for the revised first five CM deep-series videos; narration, mux, and final release QA remain local.",
        "content_identity": {
            "bible_content_hash": review["bible_content_hash"],
            "review_manifest_sha256": review["review_manifest_sha256"],
            "scope": "first_five_only",
        },
        "immutable_inputs": {
            "bundle_file": record["bundle"],
            "bundle_sha256": record["bundle_sha256"],
            "bundle_bytes": record["bundle_bytes"],
            "payload_sha256": record["payload_sha256"],
            "batch_manifest_sha256": record["batch_manifest_sha256"],
        },
        "ordered_jobs": jobs,
        "render_contract": {
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "total_frames": record["total_frames"],
            "duration_seconds": round(record["total_frames"] / 30, 3),
            "audio": False,
            "render_workers": 4,
            "required_qa": [
                "exact input and output hashes",
                "frame count, dimensions, frame rate, duration, codec, and audio absence for every chapter",
                "opening, middle, and final decoded frames for every chapter",
                "identical-input repeated PNG equality for every chapter",
                "render and encode throughput plus child-process peak memory",
                "resumable ordered-job ledger and bounded result archive",
            ],
        },
        "smoke_basis": {
            "successful_jobs": len(smoke["media"]),
            "minimum_measured_frames_per_second": measured_fps,
            "technical_smoke_passed": smoke["status"] == "passed",
            "human_review_result": "infrastructure passed; visible compiler scaffolding found and corrected before this bundle",
        },
        "resource": {
            "provider": "RunPod",
            "product": "Pod",
            "cloud": "SECURE",
            "compute_type": "GPU",
            "gpu_id": "NVIDIA RTX A5000",
            "gpu_count": 1,
            "base_image": "python:3.10.15-slim-bookworm@sha256:97ff6fda70178dee6c144d41030fb88b6ec86d75e1c517fe96b8f62094ea7ac2",
            "container_disk_gb": 30,
            "volume_gb": 0,
            "network_volume": None,
            "ports": ["22/tcp"],
            "minimum_vcpus": 4,
            "minimum_ram_gb": 8,
            "actual_shape_policy": "Verify exact owned pod identity, Secure Cloud, GPU, image digest, compute rate, minimum CPU/RAM, zero volume, and SSH-only ports; delete immediately on mismatch.",
        },
        "quote": {
            **quote,
            "rate_cap_usd_per_hour": 0.27,
            "official_public_pricing_url": "https://www.runpod.io/pricing",
            "official_pod_billing_url": "https://docs.runpod.io/pods/pricing",
        },
        "cost_model": {
            "measured_render_seconds_estimate": round(estimated_render_seconds, 1),
            "fixed_boot_encode_download_allowance_seconds": overhead_seconds,
            "estimated_runtime_seconds": round(estimated_runtime_seconds, 1),
            "estimated_compute_usd": round(estimated_compute, 4),
            "estimate_is_not_a_charge": True,
        },
        "authorization_ceiling": {
            "maximum_total_runpod_spend_usd": 2.0,
            "maximum_pod_creates": 1,
            "maximum_parallel_pods": 1,
            "maximum_runtime_seconds_per_pod": 21600,
            "maximum_ordered_job_attempts_per_create": 1,
            "retry_policy": "No second create under this proposal. Resume completed chapters only within the one owned pod; a failed pod requires a new exact proposal.",
            "no_other_paid_services": True,
        },
        "transport_and_cleanup": {
            "credential_reference": "existing RUNPOD_API_KEY environment variable; never print, copy, persist, bundle, or transmit its value except as the RunPod API authorization header",
            "upload": "SFTP the one hash-bound bundle to the one owned ephemeral pod and verify SHA-256 before extraction",
            "download": "Download only the bounded result archive and verify safe paths, hashes, media contracts, and QA records locally",
            "keepalive": "SSH keepalive plus remote batch heartbeat; independent local watchdog remains authoritative",
            "publish": False,
            "commit_or_push": False,
            "delete_on_terminal": True,
            "final_owned_inventory_reconciliation": True,
        },
        "local_follow_on": {
            "remote_or_paid_work": False,
            "tasks": [
                "synthesize narration through the existing offline Windows SAPI Microsoft Mark route",
                "fit cue audio to declared windows without speech time-compression",
                "assemble chapter masters into five episode masters",
                "mux narration and sidecar captions, then inspect streams and decoded frames",
                "produce final hashes, provenance, contact sheets, and human-review packets",
            ],
        },
        "authorization_effect": "Approval authorizes only the exact 17-job silent visual render described here, on at most one Secure A5000 pod/create and at most $2.00. It does not authorize narration on RunPod, later episodes, the 51-video series, publication, commit, or push.",
        "proposal_sha256": "0" * 64,
    }
    proposal["proposal_sha256"] = canonical_sha256(
        {key: value for key, value in proposal.items() if key != "proposal_sha256"}
    )
    write_json(ROOT / "proposal.json", proposal)
    exact_approval_text = (
        "I approve CM deep-series first-five revised content bible "
        f"`{review['bible_content_hash']}` and scoped review manifest "
        f"`{review['review_manifest_sha256']}` for production planning, and I approve "
        f"proposal `{PROPOSAL_ID}` exactly as stated, proposal identity "
        f"`{proposal['proposal_sha256']}`, including at most $2.00 RunPod spend."
    )
    (ROOT / "PROPOSAL.md").write_text(
        "\n".join(
            [
                "# First-five CM deep-series RunPod production proposal",
                "",
                f"Proposal: `{PROPOSAL_ID}`",
                "",
                f"Proposal identity: `{proposal['proposal_sha256']}`",
                "",
                f"Scoped Bible / review: `{review['bible_content_hash']}` / `{review['review_manifest_sha256']}`",
                "",
                f"Jobs / frames / duration: **{len(jobs)} / {record['total_frames']} / {record['total_frames'] / 1800:.2f} minutes**",
                "",
                f"Measured estimate / hard ceiling: **${estimated_compute:.2f} / $2.00**",
                "",
                "No remote or paid work is authorized until Brian approves both the scoped content identities and this exact proposal.",
                "",
                "## Exact combined approval text",
                "",
                exact_approval_text,
                "",
            ]
        ),
        encoding="utf-8",
    )
    validate()
    return proposal


def validate() -> None:
    proposal = load(ROOT / "proposal.json")
    record = load(ROOT / "bundle_record.json")
    review = load(REVIEW)
    expected = canonical_sha256(
        {key: value for key, value in proposal.items() if key != "proposal_sha256"}
    )
    if proposal["proposal_sha256"] != expected:
        raise ProposalError("proposal identity is stale")
    if proposal["remote_or_paid_work_authorized"] is not False:
        raise ProposalError("unapproved proposal authorizes remote work")
    if proposal["proposal_id"] != record["proposal_id"]:
        raise ProposalError("proposal and bundle IDs differ")
    immutable = proposal["immutable_inputs"]
    if (
        immutable["bundle_sha256"] != record["bundle_sha256"]
        or immutable["payload_sha256"] != record["payload_sha256"]
        or immutable["batch_manifest_sha256"] != record["batch_manifest_sha256"]
        or proposal["content_identity"]["bible_content_hash"] != review["bible_content_hash"]
        or proposal["content_identity"]["review_manifest_sha256"]
        != review["review_manifest_sha256"]
        or len(proposal["ordered_jobs"]) != 17
        or proposal["render_contract"]["total_frames"] != 68399
        or proposal["authorization_ceiling"]["maximum_total_runpod_spend_usd"] != 2.0
        or proposal["authorization_ceiling"]["maximum_pod_creates"] != 1
    ):
        raise ProposalError("proposal no longer matches the frozen scope")
    first5_package.validate()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "validate"))
    args = parser.parse_args()
    if args.command == "build":
        proposal = build()
        print(
            json.dumps(
                {
                    "proposal_id": proposal["proposal_id"],
                    "proposal_sha256": proposal["proposal_sha256"],
                    "estimated_compute_usd": proposal["cost_model"]["estimated_compute_usd"],
                    "maximum_total_runpod_spend_usd": proposal["authorization_ceiling"]["maximum_total_runpod_spend_usd"],
                },
                indent=2,
            )
        )
    else:
        validate()


if __name__ == "__main__":
    main()
