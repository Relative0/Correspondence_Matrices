"""Record a user's later exact authorization for the already frozen C38 request."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c38_linux_confirmation"
REQUEST = HERE / "RUNPOD_C38_AUTHORIZATION_REQUEST_20260903.json"
OUTPUT = HERE / "RUNPOD_C38_EXACT_PAYLOAD_AUTHORIZED_2026_09_03.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirmation-reference", required=True,
        help="Short traceability note identifying the user's exact approval message.",
    )
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite the C38 authorization record")
    request = load(REQUEST)
    if request.get("authorization_granted") is not False:
        raise ValueError("C38 request is not in its non-authorizing frozen state")
    authorization = dict(request)
    authorization.pop("authorization_granted")
    authorization["schema"] = "crse-runpod-c38-exact-payload-authorization/v1"
    authorization["authorized"] = True
    authorization["recorded_utc"] = datetime.now(timezone.utc).isoformat()
    authorization["authorization_request_sha256"] = sha256(REQUEST)
    authorization["user_confirmation_reference"] = args.confirmation_reference
    with OUTPUT.open("xb") as stream:
        stream.write(
            json.dumps(authorization, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")
            + b"\n"
        )
    print(json.dumps({
        "authorized": True,
        "authorization_sha256": sha256(OUTPUT),
        "authorization_request_sha256": authorization["authorization_request_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
