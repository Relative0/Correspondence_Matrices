"""Download and reconcile the completed v2 remote contracts without creating a pod."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import re
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import foundational_three_v2_execute as wrapper  # noqa: E402

wrapper.configure()
c = wrapper.controller
RUN_DIR = c.PACKAGE_ROOT / "remote" / "runpod-foundational-three-v2-20260901-112500"
POD_ID = "mwb0bz52ewxxss"
POD_NAME = "cm-foundational-three-v2-ed5293286584"
REMOTE_ROOT = "/workspace/bundle/repo/"


def run() -> None:
    c.verify_local_authorization()
    client = c.base.api_session()
    ssh = None
    try:
        pod = c.base.pod_detail(client, POD_ID)
        c.verified_shape(pod, POD_ID, POD_NAME, c.RATE_CAP)
        environment = pod.get("env") or {}
        token = str(environment.get("CM_BOOTSTRAP_TOKEN") or "") if isinstance(environment, dict) else ""
        if not token or any(character.isspace() for character in token):
            raise RuntimeError("existing pod bootstrap credential reference unavailable")
        ssh, _shape = c.wait_for_ssh(client, POD_ID, POD_NAME, token, c.RATE_CAP, timeout=180)
        manifest_remote = REMOTE_ROOT + "docs/video_factory/deep_series/foundational_cm_production_v1/PRODUCTION_MANIFEST_V1.json"
        with ssh.open_sftp() as sftp:
            with sftp.open(manifest_remote, "rb") as handle:
                manifest = json.loads(handle.read().decode("utf-8"))
            destination = RUN_DIR / "remote_contracts"
            destination.mkdir(parents=True, exist_ok=True)
            files = ["docs/video_factory/deep_series/foundational_cm_production_v1/PRODUCTION_MANIFEST_V1.json"]
            files.extend(str(item["path"]) for item in manifest["artifacts"])
            for relative in files:
                posix = PurePosixPath(relative)
                if posix.is_absolute() or ".." in posix.parts:
                    raise RuntimeError("remote contract manifest contains an unsafe path")
                target = destination / Path(*posix.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                sftp.get(REMOTE_ROOT + relative, str(target))
        print("remote_contracts_downloaded=" + str(len(files)), flush=True)
    finally:
        if ssh is not None:
            ssh.close()
        client.close()


if __name__ == "__main__":
    run()
