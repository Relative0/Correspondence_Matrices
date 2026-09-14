"""Freeze the successor biology-admission and d4-abort diagnosis.

This reads the completed campaign artifacts and pinned d4 source without
modifying them.  It emits a new audit describing the stricter admission rule
and the bounded d4 cache contract used by successor runs.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.backends.native_count import (  # noqa: E402
    D4_CACHE_ADDITIONAL_PAGE_BYTES,
    D4_CACHE_FIRST_PAGE_BYTES,
)
from cmbench.biology_bnet import (  # noqa: E402
    parse_bnet,
    undeclared_bnet_regulators,
)


BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
PRELAUNCH = BASE / "prelaunch-008"
SCREEN = BASE / "runpod-results-002/evidence/core-screen"
RESULTS = BASE / "results-analysis-001/RESULTS.json"
D4_ARCHIVE = BASE / (
    "native-cache/d4v2-15eff31962466804a48374826b9e5a746fc2766e.tar.gz"
)
OUT = BASE / "admission-d4-correction-001"
D4_PREFIX = "d4v2-15eff31962466804a48374826b9e5a746fc2766e"
D4_OPTIONS_MEMBER = f"{D4_PREFIX}/demo/counter/src/option.dsc"
D4_ALLOCATOR_MEMBER = f"{D4_PREFIX}/src/caching/bucket/BucketAllocator.cpp"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def archive_text(member: str) -> str:
    with tarfile.open(D4_ARCHIVE, "r:gz") as archive:
        extracted = archive.extractfile(member)
        if extracted is None:
            raise RuntimeError(f"missing d4 archive member: {member}")
        return extracted.read().decode("utf-8")


def matching_line(text: str, needle: str) -> dict[str, object]:
    for number, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return {"line": number, "text": line.strip()}
    raise RuntimeError(f"source evidence not found: {needle}")


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f"successor audit already exists: {OUT}")

    ledger_path = PRELAUNCH / "ADMISSION_LEDGER.json"
    plan_path = SCREEN / "PLAN.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    biology_rows = [
        row for row in ledger["rows"] if row["group"] == "biological_functions"
    ]

    model_dispositions: dict[str, dict[str, object]] = {}
    for row in biology_rows:
        model_sha = row["sha256"]
        if model_sha in model_dispositions:
            continue
        source = ROOT / row["path"]
        if digest(source) != model_sha:
            raise RuntimeError(f"biology source hash mismatch: {source}")
        functions = parse_bnet(source.read_text(encoding="utf-8"))
        undeclared = list(undeclared_bnet_regulators(functions))
        model_dispositions[model_sha] = {
            "path": row["path"],
            "sha256": model_sha,
            "declared_targets": len(functions),
            "undeclared_regulators": undeclared,
            "state": "admitted" if not undeclared else "refused",
            "reason": (
                "closed under declared targets"
                if not undeclared
                else "BNet fixed-point model is not closed under declared targets"
            ),
        }

    successor_rows = []
    for row in biology_rows:
        disposition = model_dispositions[row["sha256"]]
        successor_rows.append(
            {
                "case_id": row["case_id"],
                "selector": row["selector"],
                "path": row["path"],
                "sha256": row["sha256"],
                "previous_state": row["state"],
                "state": disposition["state"],
                "reason": disposition["reason"],
                "undeclared_regulators": disposition["undeclared_regulators"],
            }
        )

    biology_cells = [
        cell for cell in plan["cells"] if cell["lane"] == "biology_fixed_points"
    ]
    screen_cases = {
        cell["case_id"]: cell["input_sha256"] for cell in biology_cells
    }
    unknown_screen_hashes = sorted(
        set(screen_cases.values()).difference(model_dispositions)
    )
    if unknown_screen_hashes:
        raise RuntimeError(f"screen biology hashes absent from ledger: {unknown_screen_hashes}")

    closed_screen_cases = sum(
        model_dispositions[model_sha]["state"] == "admitted"
        for model_sha in screen_cases.values()
    )
    closed_screen_cells = sum(
        model_dispositions[cell["input_sha256"]]["state"] == "admitted"
        for cell in biology_cells
    )
    observed_biology_closure_errors = sum(
        item["cells"]
        for item in results["posthoc_worker_error_classification"]
        if item["classification"] == "input_not_closed_under_declared_targets"
    )
    if len(biology_cells) - closed_screen_cells != observed_biology_closure_errors:
        raise RuntimeError("successor biology admission does not reconcile with frozen results")

    options_text = archive_text(D4_OPTIONS_MEMBER)
    allocator_text = archive_text(D4_ALLOCATOR_MEMBER)
    core_runner_path = ROOT / "scripts/cm_benchmark_core_screen.py"
    core_runner_text = core_runner_path.read_text(encoding="utf-8")
    d4_abort_cells = sum(
        item["cells"]
        for item in results["posthoc_worker_error_classification"]
        if item["classification"] == "d4_native_abort_signal_6"
    )

    admitted_rows = sum(row["state"] == "admitted" for row in successor_rows)
    closed_models = sum(
        item["state"] == "admitted" for item in model_dispositions.values()
    )
    document = {
        "schema": "cm-benchmark-successor-admission-d4-diagnostic/v1",
        "created_utc": now(),
        "campaign_id": "cm-mega-prelaunch-20260914-008",
        "scope": (
            "local successor correction; completed campaign evidence and frozen "
            "admission ledger are read-only"
        ),
        "source_hashes": {
            "admission_ledger": digest(ledger_path),
            "core_screen_plan": digest(plan_path),
            "results": digest(RESULTS),
            "d4_source_archive": digest(D4_ARCHIVE),
            "core_screen_runner": digest(core_runner_path),
            "biology_adapter_successor": digest(ROOT / "cmbench/biology_bnet.py"),
            "campaign_prelaunch_successor": digest(ROOT / "cmbench/campaign_prelaunch.py"),
            "native_count_adapter_successor": digest(
                ROOT / "cmbench/backends/native_count.py"
            ),
        },
        "biology": {
            "candidate_rows": len(successor_rows),
            "admitted_candidate_rows": admitted_rows,
            "refused_candidate_rows": len(successor_rows) - admitted_rows,
            "unique_models": len(model_dispositions),
            "closed_unique_models": closed_models,
            "refused_unique_models": len(model_dispositions) - closed_models,
            "screen_unique_cases": len(screen_cases),
            "screen_closed_cases": closed_screen_cases,
            "screen_refused_cases": len(screen_cases) - closed_screen_cases,
            "screen_cells": len(biology_cells),
            "screen_closed_cells": closed_screen_cells,
            "screen_refused_cells": len(biology_cells) - closed_screen_cells,
            "observed_frozen_closure_errors": observed_biology_closure_errors,
            "reconciliation": "exact",
            "successor_rows": successor_rows,
        },
        "d4": {
            "observed_frozen_abort_cells": d4_abort_cells,
            "diagnosis": (
                "the pinned d4 default first cache page equals the worker address-space "
                "limit and is allocated eagerly"
            ),
            "worker_address_space_limit_bytes": 4 << 30,
            "upstream_default_first_page_bytes": 1 << 32,
            "upstream_default_additional_page_bytes": 1 << 29,
            "successor_first_page_bytes": D4_CACHE_FIRST_PAGE_BYTES,
            "successor_additional_page_bytes": D4_CACHE_ADDITIONAL_PAGE_BYTES,
            "source_evidence": {
                "default_first_page": matching_line(
                    options_text, 'default_value((1UL<<32))'
                ),
                "default_additional_page": matching_line(
                    options_text, 'default_value((1UL<<29))'
                ),
                "eager_allocation": matching_line(
                    allocator_text, "m_data = new char[m_sizeData];"
                ),
                "worker_limit": matching_line(
                    core_runner_text,
                    "resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30))",
                ),
            },
            "successor_contract": [
                "--cache-size-first-page",
                str(D4_CACHE_FIRST_PAGE_BYTES),
                "--cache-size-additional-page",
                str(D4_CACHE_ADDITIONAL_PAGE_BYTES),
            ],
            "native_linux_replay": "not run locally",
            "native_linux_replay_blocker": (
                "Docker daemon unavailable; installed WSL environment lacks Python, "
                "g++, CMake, and Ninja"
            ),
        },
    }

    OUT.mkdir(parents=True, exist_ok=False)
    diagnostic_path = OUT / "DIAGNOSTIC.json"
    diagnostic_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = f"""# CM successor admission and d4 correction

Status: implemented locally and reconciled against the frozen campaign evidence.

## Biology admission

Whole-model fixed-point admission now requires every referenced regulator to have a declared update function. Applied to the frozen ledger, the successor rule admits {admitted_rows} of {len(successor_rows)} candidate rows across {closed_models} of {len(model_dispositions)} unique models and refuses the other {len(successor_rows) - admitted_rows} rows across {len(model_dispositions) - closed_models} models.

The rule predicts that {closed_screen_cases} of {len(screen_cases)} selected biology cases are admissible. Those cases produce {closed_screen_cells} of {len(biology_cells)} cells; the remaining {len(biology_cells) - closed_screen_cells} refused cells exactly match all {observed_biology_closure_errors} frozen undeclared-regulator errors. The original admission ledger and results remain unchanged.

## d4 abort diagnosis

The pinned d4 source defaults its first cache page to 4 GiB and allocates that page eagerly. The screen worker independently imposed a 4 GiB address-space limit. This collision explains the uniform signal-6 aborts on all {d4_abort_cells} d4 corpus cells while the pre-worker smoke could pass.

The successor adapter now passes a 256 MiB first page and 64 MiB additional pages explicitly and rejects unsafe cache sizes. This retains a bounded cache without relying on the upstream 4 GiB default.

## Verification boundary

The admission and command contracts are covered by focused local tests, and this audit reconciles the admission rule with the frozen SHA-256 identities and observed errors. A post-fix native Linux execution was not possible on this host: Docker has no available daemon, and the installed WSL environment lacks Python and the C++ build toolchain. No cloud resources were created and no campaign evidence was rewritten.
"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "complete",
                "diagnostic_sha256": digest(diagnostic_path),
                "biology_admitted_candidate_rows": admitted_rows,
                "biology_refused_candidate_rows": len(successor_rows) - admitted_rows,
                "screen_refused_cells": len(biology_cells) - closed_screen_cells,
                "d4_abort_cells_diagnosed": d4_abort_cells,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
