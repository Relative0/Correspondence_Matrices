"""Verify the W4 remote wrapper against the exact prior 96-file upload bundle."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V2-20260830.json"
BUNDLE = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V2-20260830.zip"
REMOTE = HERE / "runpod_p7_w4_timing_remote_v1.py"
LOCAL_FREEZE = (
    HERE.parents[5]
    / "docs"
    / "research"
    / "verification"
    / "comparative-p7-w4-timing-scout-v1-2026-08-31"
    / "freeze.json"
)
DESTINATION = HERE / "P7-W4-TIMING-PACKAGE-V2-LOCAL-VALIDATION.json"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def assignment(source: str, name: str):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return ast.literal_eval(node.value)
    raise RuntimeError(f"remote assignment unavailable: {name}")


def function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            value = ast.get_source_segment(source, node)
            if value:
                return value
    raise RuntimeError(f"remote function unavailable: {name}")


def main() -> int:
    if DESTINATION.exists():
        raise RuntimeError("W4 package validation already exists")
    manifest_bytes = MANIFEST.read_bytes()
    bundle_bytes = BUNDLE.read_bytes()
    manifest = json.loads(manifest_bytes)
    if (
        digest(manifest_bytes) != "9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74"
        or digest(bundle_bytes) != "83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668"
        or len(bundle_bytes) != 3_197_013
        or manifest.get("file_count") != 96
        or manifest.get("bytes") != 19_484_163
    ):
        raise RuntimeError("exact 96-file upload identity changed")
    expected = {row["target"]: row for row in manifest["files"]}
    if len(expected) != 96:
        raise RuntimeError("duplicate upload target")
    remote_source = REMOTE.read_text(encoding="utf-8")
    scout_ids = assignment(remote_source, "SCOUT_CASE_IDS")
    parent_hash = assignment(remote_source, "PARENT_FREEZE_SHA256")
    derived_hash = assignment(remote_source, "DERIVED_FREEZE_SHA256")
    derive_source = function_source(remote_source, "derive_w4_freeze")
    local_freeze = json.loads(LOCAL_FREEZE.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="cm-p7-w4-package-") as temporary_name:
        temporary = Path(temporary_name)
        with zipfile.ZipFile(BUNDLE) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or set(names) != set(expected):
                raise RuntimeError("bundle membership mismatch")
            for name in names:
                data = archive.read(name)
                row = expected[name]
                if len(data) != row["bytes"] or digest(data) != row["sha256"]:
                    raise RuntimeError(f"bundle member mismatch: {name}")
            archive.extractall(temporary)
        derived_out = temporary / "w4-derived"
        derived_out.mkdir()
        program = "\n".join(
            [
                "import hashlib, json",
                "from pathlib import Path",
                f"SCOUT_CASE_IDS = {scout_ids!r}",
                f"PARENT_FREEZE_SHA256 = {parent_hash!r}",
                f"DERIVED_FREEZE_SHA256 = {derived_hash!r}",
                f"OUT = Path({str(derived_out)!r})",
                derive_source,
                "parent = Path('docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json')",
                "path = derive_w4_freeze(parent)",
                "derived = json.loads(path.read_text(encoding='utf-8'))",
                "from cmbench.comparative import linux_supervisor, p7_runner",
                "limits = p7_runner.limits_record(linux_supervisor.Limits(timeout_seconds=30, rss_stop_bytes=1 << 30, stdout_bytes=p7_runner.MAX_WORKER_BYTES, stderr_bytes=256 << 10, input_bytes=p7_runner.MAX_REQUEST_BYTES, processes=4))",
                "plans = {}",
                "for policy, blocks in (('p7-ir', 8), ('p7-relation', 10)):",
                "    plan = p7_runner.build_plan(derived, policy_id=policy, roles=('development',), blocks=blocks, worker_source_manifest_sha256='a' * 64, resource_limits=limits, profile='performance')",
                "    plans[policy] = {'cells': len(plan['cells']), 'cases': len(plan['case_ids']), 'performance_measurement': plan['performance_measurement']} ",
                "print(json.dumps({'freeze': derived, 'plans': plans}, sort_keys=True))",
            ]
        )
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(temporary)
        environment["PYTHONNOUSERSITE"] = "1"
        completed = subprocess.run(
            [sys.executable, "-B", "-c", program],
            cwd=temporary,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode:
            raise RuntimeError("exact-bundle derivation failed: " + completed.stderr[-2000:])
        exact = json.loads(completed.stdout)
    if exact["freeze"] != local_freeze or exact["freeze"].get("freeze_sha256") != derived_hash:
        raise RuntimeError("exact bundle does not reproduce local W4 freeze")
    if exact["plans"] != {
        "p7-ir": {"cells": 384, "cases": 12, "performance_measurement": True},
        "p7-relation": {"cells": 600, "cases": 12, "performance_measurement": True},
    }:
        raise RuntimeError(f"exact bundle plan mismatch: {exact['plans']}")
    result = {
        "schema": "cm-runpod-p7-w4-timing-package-local-validation/v2",
        "ready": True,
        "upload_manifest_sha256": digest(manifest_bytes),
        "upload_bundle_sha256": digest(bundle_bytes),
        "upload_bundle_bytes": len(bundle_bytes),
        "source_files": manifest["file_count"],
        "source_bytes": manifest["bytes"],
        "remote_program_sha256": digest(REMOTE.read_bytes()),
        "parent_freeze_sha256": parent_hash,
        "derived_freeze_sha256": derived_hash,
        "selected_case_ids": scout_ids,
        "exact_bundle_reproduces_freeze": True,
        "plans": exact["plans"],
        "planned_primary_cells": sum(row["cells"] for row in exact["plans"].values()),
        "performance_measurement": True,
        "principal_p7_result": False,
    }
    DESTINATION.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
