"""Replay the frozen successor shard and remote worker locally in WSL."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
PRELAUNCH = BASE / "successor-prelaunch-002"
OUT = BASE / "wsl-successor-remote-replay-003"
MANIFEST = PRELAUNCH / "UPLOAD_MANIFEST.json"
RUNNER = ROOT / "scripts/cm_benchmark_core_screen_v2.py"
PLAN = PRELAUNCH / "PLAN.json"
REMOTE = ROOT / "scripts/cm_benchmark_runpod_successor_remote.py"
WSL_ROOT = Path("/workspace/cm-benchmark")
WSL_OUTPUT = Path("/workspace/cm-benchmark-successor")
VENV = Path("/opt/cm-successor-replay-003")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    if sys.platform != "linux":
        raise RuntimeError("successor remote replay must run inside WSL")
    if OUT.exists() or WSL_ROOT.exists() or WSL_OUTPUT.exists() or VENV.exists():
        raise RuntimeError("successor replay target already exists")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (
        manifest.get("campaign_id") != "cm-mega-successor-20260914-009"
        or len(manifest.get("bundles", [])) != 1
        or len(manifest.get("controls", [])) != 2
    ):
        raise RuntimeError("successor upload manifest mismatch")

    OUT.mkdir(parents=True, exist_ok=False)
    Path("/workspace").mkdir(exist_ok=True)
    result_zip = OUT / "evidence.zip"
    subprocess.run(
        [sys.executable, "-m", "venv", str(VENV)], check=True, timeout=120
    )
    env = {
        **os.environ,
        "CM_SHARD_DIR": str(PRELAUNCH),
        "CM_SHARDS": json.dumps(manifest["bundles"], separators=(",", ":")),
        "CM_RESULT_PATH": str(result_zip),
        "CM_CORE_SCREEN_SOURCE": str(RUNNER),
        "CM_CORE_SCREEN_PLAN_SOURCE": str(PLAN),
        "CM_CORE_SCREEN_SHA256": digest(RUNNER),
        "CM_CORE_SCREEN_PLAN_SHA256": digest(PLAN),
        "PYTHONUNBUFFERED": "1",
    }
    completed = subprocess.run(
        [str(VENV / "bin/python"), str(REMOTE)],
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        timeout=5400,
    )
    if completed.returncode != 0 or not result_zip.is_file():
        raise RuntimeError(f"successor remote replay failed: {completed.returncode}")

    evidence = OUT / "evidence"
    evidence.mkdir()
    with zipfile.ZipFile(result_zip) as archive:
        infos = archive.infolist()
        for info in infos:
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or ".." in pure.parts or info.is_dir():
                raise RuntimeError("unsafe successor replay result member")
            target = evidence.joinpath(*pure.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
    summary = json.loads((evidence / "SUMMARY.json").read_text(encoding="utf-8"))
    if (
        summary.get("status") != "passed"
        or summary.get("shards") != 1
        or summary.get("core_screen", {}).get("cells") != 108
        or summary.get("core_screen", {}).get("correctness_mismatches")
        or summary.get("core_screen", {}).get("status_counts", {}).get("worker_error", 0)
        or summary.get("core_screen", {}).get("status_counts", {}).get("error", 0)
    ):
        raise RuntimeError("successor replay summary mismatch")
    record = {
        "schema": "cm-benchmark-wsl-successor-remote-replay/v1",
        "created_utc": now(),
        "status": "passed",
        "source_hashes": {
            "upload_manifest": digest(MANIFEST),
            "bundle": digest(PRELAUNCH / manifest["bundles"][0]["path"]),
            "runner": digest(RUNNER),
            "plan": digest(PLAN),
            "remote_worker": digest(REMOTE),
        },
        "evidence_zip_sha256": digest(result_zip),
        "evidence_files": len(infos),
        "summary": summary,
        "cloud_calls": 0,
        "secret_access": False,
    }
    record_path = OUT / "REPLAY.json"
    record_path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "passed",
                "replay_sha256": digest(record_path),
                "evidence_zip_sha256": record["evidence_zip_sha256"],
                "core_screen": summary["core_screen"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
