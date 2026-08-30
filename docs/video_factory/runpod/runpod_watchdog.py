"""Independent delete-on-deadline watchdog for one owned video-render pod."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

import requests


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from cm_runpod_config import load_runpod_config  # noqa: E402

V1 = "https://rest.runpod.io/v1"
V2 = "https://api.runpod.io/v2"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append(path: Path, event: str, **fields: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"schema_version": "1.0", "timestamp": utc_now(), "actor": "watchdog",
              "event": event, **fields}
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def session() -> requests.Session:
    config = load_runpod_config()
    if not config.api_key or any(character.isspace() for character in config.api_key):
        raise RuntimeError("credential reference unavailable")
    client = requests.Session()
    client.trust_env = False
    client.headers["Authorization"] = "Bearer " + config.api_key
    return client


def inventory(client: requests.Session, base: str) -> list[dict[str, object]]:
    response = client.get(base + "/pods", timeout=15, allow_redirects=False)
    response.raise_for_status()
    body = response.json()
    pods = body if isinstance(body, list) else body.get("pods")
    if not isinstance(pods, list):
        raise RuntimeError("invalid inventory response")
    return pods


def owned(client: requests.Session, state: dict[str, object]) -> set[str]:
    expected_name = state["pod_name"]
    expected_id = state.get("pod_id")
    matches: set[str] = set()
    for base in (V1, V2):
        for pod in inventory(client, base):
            pod_id = pod.get("id")
            if pod.get("name") == expected_name:
                if not isinstance(pod_id, str) or not re.fullmatch(r"[a-z0-9]{8,40}", pod_id):
                    raise RuntimeError("owned-name match has invalid pod id")
                if expected_id and pod_id != expected_id:
                    raise RuntimeError("owned-name match disagrees with recorded pod id")
                matches.add(pod_id)
            if expected_id and pod_id == expected_id and pod.get("name") != expected_name:
                raise RuntimeError("recorded pod id no longer has the owned name")
    if len(matches) > 1:
        raise RuntimeError("multiple pods match the unique owned name")
    return matches


def delete_owned(client: requests.Session, state: dict[str, object], events: Path) -> bool:
    matches = owned(client, state)
    for pod_id in matches:
        attempts = []
        for base in (V1, V2):
            response = client.delete(base + "/pods/" + pod_id, timeout=20, allow_redirects=False)
            attempts.append({"api": base.rsplit("/", 1)[-1], "status": response.status_code})
            if response.status_code in (200, 202, 204, 404):
                break
        append(events, "delete_attempted", pod_id=pod_id, attempts=attempts)
    for _ in range(6):
        if not owned(client, state):
            return True
        time.sleep(5)
    return False


def arm(state_path: Path, ack_path: Path, events: Path) -> dict[str, object]:
    state = json.loads(state_path.read_text("utf-8"))
    with session() as client:
        if owned(client, state):
            raise RuntimeError("owned pod unexpectedly exists before controller create")
    append(events, "armed", authorization_id=state["authorization_id"],
           deadline_epoch=state["cleanup_epoch"])
    atomic_json(ack_path, {
        "schema_version": "1.0",
        "status": "armed",
        "authorization_id": state["authorization_id"],
        "pod_name": state["pod_name"],
        "deadline_epoch": state["cleanup_epoch"],
        "state_sha256": sha256(state_path),
        "armed_utc": utc_now(),
        "credential_value_recorded": False,
    })
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--done", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--ack", type=Path, required=True)
    args = parser.parse_args()
    while not args.state.is_file():
        if args.done.is_file():
            return
        time.sleep(0.25)
    state = arm(args.state, args.ack, args.events)
    while time.time() < float(state["cleanup_epoch"]):
        if args.done.is_file():
            append(args.events, "controller_done_seen")
            return
        time.sleep(2)
    try:
        with session() as client:
            absent = delete_owned(client, state, args.events)
        append(args.events, "deadline_reconciled", owned_pod_absent=absent)
        if not absent:
            raise RuntimeError("owned pod remained after watchdog deletion")
    except Exception as exc:
        append(args.events, "watchdog_failure", error_type=type(exc).__name__)
        raise


if __name__ == "__main__":
    main()
