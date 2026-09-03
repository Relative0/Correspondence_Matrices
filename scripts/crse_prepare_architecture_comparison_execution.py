"""Create the post-freeze oracle, execution contract, protocol, and upload manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.architecture_comparison_campaign import (
    QUERY_COUNTS,
    build_oracles,
    validate_oracles,
)
from cmbench.comparative.architecture_comparison_freeze import verify_freeze


HERE = ROOT / "docs/recognition/architecture_comparison_execution_20260903"
FREEZE = ROOT / "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json"
ORACLES = HERE / "ORACLES.json"
ORACLE_VERIFICATION = HERE / "ORACLE_VERIFICATION.json"
CONTRACT = HERE / "EXECUTION_CONTRACT.json"
PROTOCOL = HERE / "PROTOCOL.md"
MANIFEST = HERE / "UPLOAD_MANIFEST.json"
RUN_NAME = "architecture-comparison-linux-gcc-20260903-001"
IMAGE_TAG = "python:3.13.15-bookworm"
IMAGE_AMD64_DIGEST = "sha256:a53008522631dbcb063c4d5982aa91a00e86e51d90bbcf3513313f1a5c163af8"
IMAGE = f"{IMAGE_TAG}@{IMAGE_AMD64_DIGEST}"
NUMPY = {
    "name": "numpy", "version": "2.3.2",
    "requirement": "numpy==2.3.2 --hash=sha256:938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f",
    "sha256": "938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f",
}
PYTHON_SAT = {
    "name": "python-sat", "version": "1.9.dev15",
    "filename": "python_sat-1.9.dev15-cp313-cp313-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl",
    "bytes": 3_943_142,
    "sha256": "fd55285f4ef679aaa62699660121423ec35b97324095ae34db4edb0356422a45",
    "url": "https://files.pythonhosted.org/packages/cf/96/4290b2af2853f81061b9aa6ddf118523bc9b1d922842ee78124844ee35d9/python_sat-1.9.dev15-cp313-cp313-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl",
}
SIX = {
    "name": "six", "version": "1.17.0",
    "filename": "six-1.17.0-py2.py3-none-any.whl",
    "bytes": 11_050,
    "sha256": "4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274",
    "url": "https://files.pythonhosted.org/packages/b7/ce/149a00dd41f10bc29e5921b496af8b574d8413afcd5e30dfa0ed46c2cc5e/six-1.17.0-py2.py3-none-any.whl",
}
NETWORKX = {
    "name": "networkx", "version": "3.6.1",
    "filename": "networkx-3.6.1-py3-none-any.whl",
    "bytes": 2_068_504,
    "sha256": "d47fbf302e7d9cbbb9e2555a0d267983d2aa476bac30e90dfbe5669bd57f3762",
    "url": "https://files.pythonhosted.org/packages/9e/c9/b2622292ea83fbb4ec318f5b9ab867d0a28ab43c5717bb85b0a5f6b3b0a4/networkx-3.6.1-py3-none-any.whl",
}
RESULT_CAP_BYTES = 48 << 20

RUNTIME_SOURCES = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cm_normalize.py",
    "cmbench/__init__.py",
    "cmbench/backends/__init__.py",
    "cmbench/backends/bitset_engine.py",
    "cmbench/comparative/__init__.py",
    "cmbench/comparative/architecture_comparison_campaign.py",
    "cmbench/comparative/architecture_comparison_freeze.py",
    "cmbench/comparative/architecture_refresh_harness.py",
    "cmbench/comparative/arms.py",
    "cmbench/comparative/comparison_prefreeze.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/gf2_multi_root.py",
    "cmbench/comparative/gf2_multi_root_python.py",
    "cmbench/comparative/gf2_native_slots.py",
    "cmbench/comparative/gf2_restricted_evaluators.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "cmbench/comparative/ir.py",
    "cmbench/comparative/persistence.py",
    "cmbench/comparative/schedule.py",
    "cmbench/comparative/tasks.py",
    "cmbench/expr/__init__.py",
    "cmbench/expr/eval.py",
    "cmbench/output_budget.py",
    "cmbench/recognition/__init__.py",
    "cmbench/recognition/features.py",
    "cmbench/recognition/gf2_decomposition.py",
    "cmbench/recognition/natural_decomposition.py",
    "cmbench/recognition/portfolio.py",
    "cmbench/recognition/proved_rules.py",
    "cmbench/recognition/yosys_unused_gf2_data.py",
    "cmbench/recognition/yosys_wide_restriction_data.py",
    "scripts/build_cm_fused_slots.py",
    "scripts/cm_architecture_comparison_campaign.py",
    "scripts/cm_measurement_verify.py",
    "scripts/cm_native_contracts.py",
    "scripts/cm_session_contracts.py",
    "scripts/crse_verify_architecture_comparison_campaign.py",
    "native/cm_fused_slots/fused_slot_executor.c",
    "native/cm_fused_slots/build_msvc.cmd",
    "deliverables_n22_24/v4audit_corpus_2026_07_24.jsonl",
    "deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/independence_audit_2026_08_27/artifact_audit.py",
    "docs/recognition/c36_wide_repeated_query_dataset.json",
    "docs/recognition/c37_native_exact_confirmation_dataset.json",
    "docs/recognition/runs/architecture-refresh-harness-development-20260903-001/RESULT.json",
    "docs/recognition/architecture_comparison_prefreeze_20260903/PREFREEZE.json",
    "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json",
    "docs/recognition/architecture_comparison_freeze_20260903/VERIFICATION.json",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        if isinstance(value, str):
            stream.write(value)
        else:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")


def main() -> int:
    if HERE.exists():
        raise SystemExit("refusing to overwrite architecture comparison execution package")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    freeze_verification = verify_freeze(freeze, ROOT)
    oracles = build_oracles(ROOT, freeze)
    validate_oracles(oracles, ROOT, freeze)
    _write_new(ORACLES, oracles)
    oracle_verification = {
        "schema": "cm-architecture-comparison-oracle-verification/v1",
        "status": "verified_exact_postfreeze",
        "freeze_file_sha256": _sha256(FREEZE),
        "parent_freeze_sha256": freeze["freeze_sha256"],
        "parent_freeze_verification": freeze_verification["status"],
        "oracles_file_sha256": _sha256(ORACLES),
        "oracles_canonical_sha256": oracles["oracles_sha256"],
        "runnable_cases": {
            lane: sum(row["status"] == "runnable" for row in oracles["lanes"][lane].values())
            for lane in "ABCD"
        },
        "refused_cases": {
            lane: sum(row["status"] == "refused" for row in oracles["lanes"][lane].values())
            for lane in "AD"
        },
        "selection_changed_after_oracles": False,
        "method_timings_observed": False,
        "timing_evidence_produced": False,
    }
    _write_new(ORACLE_VERIFICATION, oracle_verification)

    lane_cells = {
        lane: freeze["schedules"][lane]["planned_cells"] for lane in "ABC"
    }
    lane_cells["D"] = sum(
        row["planned_cells"] for row in freeze["schedules"]["D"]["task_sublanes"].values()
    ) + freeze["schedules"]["D"]["structural_reload"]["planned_cells"]
    contract = {
        "schema": "cm-architecture-comparison-execution-contract/v1",
        "status": "prepared_not_authorized",
        "date": "2026-09-03",
        "run_name": RUN_NAME,
        "parent_freeze_file_sha256": _sha256(FREEZE),
        "parent_freeze_sha256": freeze["freeze_sha256"],
        "oracles_file_sha256": _sha256(ORACLES),
        "oracle_verification_sha256": _sha256(ORACLE_VERIFICATION),
        "schedule": {
            "lane_cells": lane_cells,
            "total_cells": sum(lane_cells.values()),
            "lane_b_query_checkpoints": list(QUERY_COUNTS),
            "lane_d_lifecycle_assignment": "block_parity_balanced",
            "each_lane_d_backend_lifecycle_observations_per_case_sublane": 4,
            "all_unfavorable_and_refused_cells_retained": True,
        },
        "bounded_refusals": {
            "complete_relation": {
                "cases": 7,
                "reason": "complete_relation_live_width_gt_16",
                "interpretation": "legacy guard cases retained as refusal rows, never allocated",
            },
            "smaller_tasks": {
                "cases": 4,
                "reason": "task_width_gt_8",
                "interpretation": "history cases outside the admitted bounded task adapter retained as refusal rows",
            },
        },
        "runtime": {
            "image": IMAGE,
            "python": "3.13.15",
            "compiler": "GCC-family cc",
            "compiler_flags": ["-std=c11", "-O3", "-Wall", "-Wextra", "-Wpedantic", "-shared", "-fPIC"],
            "dependencies": [NUMPY, SIX, NETWORKX, PYTHON_SAT],
        },
        "limits": {
            "wall_seconds": 420,
            "result_cap_bytes": RESULT_CAP_BYTES,
            "complete_relation_max_live_vars": 16,
            "smaller_task_max_vars": 8,
            "one_cloud_create": True,
            "automatic_replacement": False,
        },
        "permissions": {
            "postfreeze_oracle_generation_complete": True,
            "local_synthetic_clock_functional_validation": True,
            "timed_local_campaign": False,
            "runpod_authorization_request": True,
            "runpod_execution": False,
            "selector_fitting": False,
            "neural_training": False,
            "production_routing_change": False,
            "website_update": False,
            "publication": False,
        },
        "claim_boundary": {
            "historical_1_472x_unchanged": True,
            "new_results_require_independent_verification": True,
            "cross_machine_claim_requires_separate_replication": True,
            "no_universal_winner_headline": True,
        },
    }
    if contract["schedule"]["total_cells"] != 19_646:
        raise ValueError("unexpected frozen campaign size")
    _write_new(CONTRACT, contract)
    protocol = f"""# Architecture-aware four-lane comparison execution protocol

This package executes the verified parent freeze without changing its selected
cases, arm orders, or publication gates. It creates {contract['schedule']['total_cells']:,}
timed rows across complete relations, q1/q4/q16/q64 repeated restrictions,
related three-root outputs, and bounded smaller-task/persistence sublanes.

The post-freeze oracle pass is selection-independent and contains no method
timings. Seven legacy complete-relation cases above 16 live variables and four
history cases above the Lane D k<=8 contract remain in their original schedule
positions as explicit zero-allocation refusal rows. They are not silently
dropped. Lane D assigns the two lifecycles by block parity, so every backend has
four observations under each lifecycle per executable case and sublane while
preserving the parent's 1,470-cell count.

The decision-bearing run requires the pinned amd64 Python 3.13.15 Bookworm
image, NumPy 2.3.2, hash-locked python-sat 1.9.dev15 with Cadical195 and its
two exact runtime dependencies (six 1.17.0 and NetworkX 3.6.1), and a
GCC-family C11 compiler using the exact flags in `EXECUTION_CONTRACT.json`.
The workload has no network access after dependency setup. An independent
verifier must replay the oracle set, verify all {contract['schedule']['total_cells']:,}
schedule positions and timing sums, and find zero semantic or source/artifact
mismatches before any performance interpretation.

This preparation does not authorize a cloud resource. A later exact approval
is limited to one Secure CPU Pod, one create and no replacement, 2 vCPU, at
least 4 GB RAM, 12 GB ephemeral disk, no persistent/network volume, a
$0.25/hour rate ceiling, a $0.05 controller cost ceiling, deletion within ten
minutes, and twelve-minute inventory reconciliation. It authorizes no training,
selector fit, production routing, website change, publication, commit, or push.
"""
    _write_new(PROTOCOL, protocol)

    package_paths = [*RUNTIME_SOURCES, ORACLES.relative_to(ROOT).as_posix(),
                     ORACLE_VERIFICATION.relative_to(ROOT).as_posix(),
                     CONTRACT.relative_to(ROOT).as_posix(), PROTOCOL.relative_to(ROOT).as_posix()]
    files = []
    for relative in sorted(set(package_paths)):
        path = ROOT.joinpath(*Path(relative).parts)
        if not path.is_file():
            raise FileNotFoundError(relative)
        files.append({
            "source": relative, "target": relative,
            "bytes": path.stat().st_size, "sha256": _sha256(path),
        })
    manifest = {
        "schema": "cm-architecture-comparison-runpod-upload-manifest/v1",
        "authorization_status": "upload_not_authorized_exact_approval_pending",
        "created_date": "2026-09-03",
        "run_name": RUN_NAME,
        "file_count": len(files),
        "bytes": sum(row["bytes"] for row in files),
        "files": files,
        "commands": [
            ["python", "-B", "scripts/cm_architecture_comparison_campaign.py",
             "--output", f"run-output/{RUN_NAME}", "--compiler", "cc",
             "--max-seconds", "420"],
            ["python", "-B", "scripts/crse_verify_architecture_comparison_campaign.py",
             "--run-dir", f"run-output/{RUN_NAME}"],
        ],
        "execution_contract_sha256": _sha256(CONTRACT),
        "protocol_sha256": _sha256(PROTOCOL),
        "oracles_sha256": _sha256(ORACLES),
        "oracle_verification_sha256": _sha256(ORACLE_VERIFICATION),
        "runtime": contract["runtime"],
        "limits": contract["limits"],
        "network_during_setup": "pinned image plus four hash-locked wheels only",
        "network_during_workload": False,
        "result_cap_bytes": RESULT_CAP_BYTES,
        "excluded": [".env*", ".git/", "credentials", "tokens", "Windows DLLs", "website files", "unrelated dirty work"],
    }
    _write_new(MANIFEST, manifest)
    print(json.dumps({
        "oracles_sha256": oracles["oracles_sha256"],
        "total_cells": contract["schedule"]["total_cells"],
        "package_files": manifest["file_count"],
        "package_bytes": manifest["bytes"],
        "authorization_status": manifest["authorization_status"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
