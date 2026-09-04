"""Record an independent read-only RunPod inventory after the cross-machine run."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/architecture_query_ladder_cross_machine_execution_20260904"
CONTROLLER = ROOT / "scripts/runpod_architecture_query_ladder_cross_machine_controller.py"
RUN = HERE / "runpod-architecture-query-ladder-cross-machine-execute-001/RUN.json"
OUTPUT = HERE / "POST_RUN_INVENTORY.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite cross-machine post-run inventory")
    run = _load(RUN)
    if (
        run.get("status") != "complete"
        or run.get("creation_attempted") is not True
        or run.get("pod_created") is not True
        or run.get("automatic_replacement_queued") is not False
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or run.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
    ):
        raise ValueError("completed run and controller cleanup are required")

    spec = importlib.util.spec_from_file_location("cross_machine_post_inventory", CONTROLLER)
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    with controller.controller.preflight.session() as client:
        inventories = controller.shared.inventories(client)
    if inventories != {"v1": [], "v2": []}:
        raise RuntimeError("RunPod inventory is not empty after the cross-machine run")

    document = {
        "schema": "cm-runpod-post-run-inventory/v1",
        "checked_utc": controller.controller.preflight.utc_now(),
        "pod_id": run["pod_id"],
        "owned_pod_absent": True,
        "inventories": inventories,
        "resource_writes": 0,
        "credential_values_recorded": False,
    }
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(document, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps(document, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
