"""Finish current reconciliation, then make at most one already-authorized v1 attempt."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
EXPECTED_CONTROLLER = "40adb66b61ba59dda9282bf264b6767c738d168ed31abc84c790e1c6c2b3ccac"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    controller_path = ROOT / "runpod_retry_cpu8_v1_controller.py"
    if hashlib.sha256(controller_path.read_bytes()).hexdigest() != EXPECTED_CONTROLLER:
        raise RuntimeError("checked controller changed")
    if (ROOT / "cpu8-v1-execute-001").exists():
        raise RuntimeError("refusing to repeat the v1 attempt")
    controller = load("resume_v1_controller", controller_path.name)
    reconcile = load("resume_cpu8_reconciliation", "reconcile_cpu8.py")
    previous = ROOT / "cpu8-execute-001"
    state = json.loads((previous / "controller-state.json").read_text())
    horizon = state["created_epoch"] + 1205
    gate = ROOT / "cpu8-v1-continuation-gate"
    gate.mkdir(exist_ok=False)
    controller.OUT = gate
    with controller.host_awake_guard("continuation"):
        while time.time() < horizon:
            if reconcile.main():
                raise RuntimeError("inventory uncertain or nonempty; no creation permitted")
            print(json.dumps({"phase": "reconciling_previous_request", "remaining_s": max(0, round(horizon-time.time()))}), flush=True)
            time.sleep(min(45, max(0, horizon-time.time())))
        if reconcile.main():
            raise RuntimeError("post-horizon inventory uncertain or nonempty")
        watchdog = json.loads((previous / "WATCHDOG-RESULT.json").read_text())
        released = json.loads((previous / "HOST-AWAKE-RELEASED-watchdog.json").read_text())
        if not watchdog.get("owned_pod_absent") or watchdog.get("terminated") or not released.get("released"):
            raise RuntimeError("prior watchdog did not confirm an unallocated request")
        controller.write_exclusive(gate / "PRIOR-REQUEST-RECONCILED.json", {
            "checked_utc": controller.utc_now(), "owned_name": state["name"],
            "after_original_horizon": True, "independent_inventory_status": "v1_and_v2_empty",
            "watchdog_result": watchdog, "watchdog_awake_release": released,
            "status": "owned_pod_absent_after_horizon"})
        if hashlib.sha256(controller_path.read_bytes()).hexdigest() != EXPECTED_CONTROLLER:
            raise RuntimeError("controller changed while waiting")
        print(json.dumps({"phase": "launching_single_authorized_cpu8_v1_attempt", "checked_utc": controller.utc_now()}), flush=True)
        result = subprocess.run([sys.executable, str(controller_path)],
                                env={**os.environ, "CM_SMOKE_RUN_LABEL": "cpu8-v1-execute-001"})
        controller.write_exclusive(gate / "CONTINUATION-RESULT.json", {
            "finished_utc": controller.utc_now(), "child_exit_code": result.returncode,
            "automatic_replacement_attempts": 0})
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
