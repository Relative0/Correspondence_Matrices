from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from cmbench.biology_bnet import parse_bnet, require_closed_bnet


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
SUCCESSOR_ADMISSION = BASE / "prelaunch-008/ADMISSION_LEDGER.json"
SUCCESSOR_BUNDLE_MANIFEST = BASE / "successor-prelaunch-001/UPLOAD_MANIFEST.json"
SUCCESSOR_INPUT = BASE / "input-freeze-009/admitted/biology/006-efd67e1cd585.bnet"


@pytest.mark.skipif(
    not SUCCESSOR_ADMISSION.exists() or not SUCCESSOR_INPUT.exists(),
    reason="frozen campaign evidence is excluded from the source-only integration",
)
def test_successor_plan_contains_only_unresolved_admissible_lanes(tmp_path: Path) -> None:
    output = tmp_path / "PLAN.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/cm_benchmark_core_screen_v2.py"),
            "freeze",
            "--admission",
            str(BASE / "prelaunch-008/ADMISSION_LEDGER.json"),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    plan = json.loads(output.read_text(encoding="utf-8"))
    body = {key: value for key, value in plan.items() if key != "plan_sha256"}
    assert plan["plan_sha256"] == hashlib.sha256(
        json.dumps(
            body, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()
    assert len(plan["cases"]) == 18
    assert len(plan["cells"]) == 108
    assert {cell["lane"] for cell in plan["cells"]} == {
        "exact_count",
        "biology_fixed_points",
    }

    prior = json.loads(
        (BASE / "runpod-results-002/evidence/core-screen/PLAN.json").read_text(
            encoding="utf-8"
        )
    )
    exact = {case["case_id"] for case in plan["cases"] if case["lane"] == "exact_count"}
    prior_exact = {
        case["case_id"] for case in prior["cases"] if case["lane"] == "exact_count"
    }
    assert exact == prior_exact

    ledger = json.loads(
        (BASE / "prelaunch-008/ADMISSION_LEDGER.json").read_text(encoding="utf-8")
    )
    source_by_name = {
        Path(row["path"]).name: ROOT / row["path"]
        for row in ledger["rows"]
        if row["group"] == "biological_functions"
    }
    biology = [
        case for case in plan["cases"] if case["lane"] == "biology_fixed_points"
    ]
    assert len(biology) == 10
    for case in biology:
        functions = parse_bnet(
            source_by_name[Path(case["path"]).name].read_text(encoding="utf-8")
        )
        require_closed_bnet(functions)
        assert len(functions) <= 16
        assert case["metadata"]["closed_under_declared_targets"] is True


@pytest.mark.skipif(
    not SUCCESSOR_BUNDLE_MANIFEST.exists(),
    reason="frozen source bundle is preserved outside the source-only integration",
)
def test_successor_upload_bundle_matches_frozen_manifest() -> None:
    folder = BASE / "successor-prelaunch-001"
    manifest_path = folder / "UPLOAD_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["authorization_granted"] is False
    assert manifest["scope"] == {
        "cells": 108,
        "inputs": 18,
        "lanes": ["biology_fixed_points", "exact_count"],
        "other_uploads_permitted": False,
    }
    assert len(manifest["bundles"]) == 1
    bundle_row = manifest["bundles"][0]
    bundle = folder / bundle_row["path"]
    assert bundle.stat().st_size == bundle_row["bytes"]
    assert hashlib.sha256(bundle.read_bytes()).hexdigest() == bundle_row["sha256"]
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        assert names == sorted(names)
        assert len(names) == len(set(names)) == bundle_row["files"]
        assert sum(info.file_size for info in archive.infolist()) == bundle_row[
            "expanded_bytes"
        ]
        assert sum(name.startswith("inputs/") for name in names) == 18
        for row in manifest["contents"]:
            assert hashlib.sha256(archive.read(row["archive"])).hexdigest() == row[
                "sha256"
            ]


def test_successor_worker_records_adapter_deadline_as_timeout(tmp_path: Path) -> None:
    request = tmp_path / "request.json"
    result = tmp_path / "result.json"
    request.write_text(
        json.dumps(
            {
                "cell": {
                    "campaign_id": "cm-mega-successor-20260914-009",
                    "lane": "exact_count",
                    "case_id": "deadline-fixture",
                    "arm": "d4",
                    "repetition": 0,
                    "position": 0,
                    "input_sha256": "0" * 64,
                    "cell_id": "1" * 64,
                },
                "result_path": str(result),
            }
        ),
        encoding="utf-8",
    )
    source = (
        "import json, pathlib; "
        "import scripts.cm_benchmark_core_screen_v2 as runner; "
        "runner.core.execute=lambda request: (_ for _ in ()).throw(TimeoutError()); "
        f"runner.worker(pathlib.Path({str(request)!r})); "
        f"print(pathlib.Path({str(result)!r}).read_text())"
    )
    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    terminal = json.loads(completed.stdout)
    assert terminal["status"] == "timeout"
    assert terminal["reason"] == "adapter_deadline"
