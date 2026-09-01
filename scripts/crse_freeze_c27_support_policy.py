"""Freeze C27's transparent rule before constructing confirmation data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.gf2_support_aware_policy import (
    freeze_support_aware_policy, save_support_aware_policy,
)

RUN = ROOT / "docs/recognition/runs/c26-fused-resident-windows-20260831-001"
OUTPUT = ROOT / "docs/recognition/c27_support_aware_policy.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite frozen C27 policy")
    result = json.loads((RUN / "results.json").read_text(encoding="utf-8"))
    verification = json.loads((RUN / "independent_verification.json").read_text(encoding="utf-8"))
    if (
        result.get("status") != "complete"
        or result.get("claims", {}).get("production_promotion") is not False
        or verification.get("status") != "verified"
        or verification.get("semantic_or_artifact_mismatches") != 0
        or verification.get("production_promotion") is not False
    ):
        raise SystemExit("refusing C27 policy freeze: C26 evidence incomplete")
    policy = freeze_support_aware_policy(
        c26_manifest_sha256=digest(RUN / "manifest.json"),
        c26_result_sha256=digest(RUN / "results.json"),
    )
    save_support_aware_policy(policy, OUTPUT)
    print(json.dumps({
        "policy_sha256": policy["policy_sha256"],
        "tiny_support_max_n_vars": policy["tiny_support_max_n_vars"],
        "fresh_confirmation_complete": policy["fresh_confirmation_complete"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
