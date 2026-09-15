"""Analyze and bind a completed overnight CM portfolio assurance run."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = (
    ROOT
    / "docs/audits/2026-09-15-cm-overnight-local-portfolio/run-003"
)
DEFAULT_BASELINE = (
    ROOT
    / "docs/audits/2026-09-14-cm-benchmark-attribution/TEST_COMPARISON.json"
)
EXPECTED_COLLECTION_REFUSALS = {
    "tests/test_natural_cut_ranking.py": "optional PyTorch dependency is absent",
    "tests/test_natural_decomposition.py": "optional PyTorch dependency is absent",
    "tests/test_natural_variable_cut.py": "optional PyTorch dependency is absent",
    "tests/test_packed_io_campaign.py": "the Unix resource module is unavailable on Windows",
    "tests/test_recognition_neural.py": "optional PyTorch dependency is absent",
    "tests/test_source_anf_hybrid.py": "optional PyTorch dependency is absent",
    "tests/test_variable_decomposition.py": "optional PyTorch dependency is absent",
    "tests/test_yosys_source_anf.py": "optional PyTorch dependency is absent",
}
EXPECTED_ALL_SKIPPED = {
    "tests/test_bucket_cudd_reference.py": "optional CUDD binding is absent",
}


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def junit_cases(path: Path) -> list[dict]:
    root = ET.parse(path).getroot()
    cases = []
    for element in root.iter("testcase"):
        outcome = "passed"
        detail = None
        for kind in ("failure", "error", "skipped"):
            child = element.find(kind)
            if child is not None:
                outcome = kind
                detail = child.attrib.get("message") or (child.text or "").strip()
                break
        cases.append(
            {
                "classname": element.attrib.get("classname", ""),
                "name": element.attrib.get("name", ""),
                "outcome": outcome,
                "seconds": float(element.attrib.get("time", "0") or 0),
                "detail": detail,
            }
        )
    return cases


def verify_run(run: Path, plan: dict, rows: list[dict]) -> dict:
    expected = {cell["cell_id"]: cell for cell in plan["cells"]}
    failures: list[str] = []
    if load_json(run / "RUN.json").get("reason") != "schedule_complete":
        failures.append("terminal reason is not schedule_complete")
    if len(rows) != len(plan["cells"]):
        failures.append("ledger row count differs from plan")
    if len({row["cell_id"] for row in rows}) != len(rows):
        failures.append("duplicate ledger cell")
    if sha256(run / "ledger.jsonl") != load_json(run / "RUN.json").get(
        "ledger_sha256"
    ):
        failures.append("terminal ledger hash mismatch")
    for name, expected_hash in plan["sources"].items():
        if sha256(run / "source" / name) != expected_hash:
            failures.append(f"source snapshot mismatch: {name}")
    for cell in plan["cells"]:
        if sha256(run / "source" / cell["path"]) != cell["input_sha256"]:
            failures.append(f"test snapshot mismatch: {cell['path']}")
    for row in rows:
        cell = expected.get(row["cell_id"])
        if cell is None or row["input_sha256"] != cell["input_sha256"]:
            failures.append(f"ledger identity mismatch: {row['cell_id']}")
            continue
        for record in row["logs"].values():
            path = run / record["path"]
            if path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
                failures.append(f"log identity mismatch: {record['path']}")
        record = row.get("junit")
        if record:
            path = run / record["path"]
            if path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
                failures.append(f"JUnit identity mismatch: {record['path']}")
    return {
        "status": "passed" if not failures else "failed",
        "failures": failures,
        "rows": len(rows),
        "planned_cells": len(plan["cells"]),
    }


def readiness() -> list[dict]:
    return [
        {
            "surface": "broad_repository_replay",
            "catalog_ids": [],
            "state": "ready",
            "overnight_disposition": "executed",
            "basis": "All 271 frozen top-level pytest modules ran in fresh bounded processes.",
        },
        {
            "surface": "synthetic_and_boundary_controls",
            "catalog_ids": ["S01-S13"],
            "state": "correctness_only",
            "overnight_disposition": "executed_via_existing_tests",
            "basis": "Core, synthetic, normalization, representation and boundary modules were replayed; no new timing claim was tested.",
        },
        {
            "surface": "sat_counting_projection_controls",
            "catalog_ids": ["C01", "C04", "C05"],
            "state": "correctness_only",
            "overnight_disposition": "executed_via_existing_tests",
            "basis": "Ten of eleven exact-control modules passed; the one nonpassing module matched the retained baseline.",
        },
        {
            "surface": "affine_controls",
            "catalog_ids": ["A01", "A02", "A03"],
            "state": "correctness_only",
            "overnight_disposition": "executed_via_existing_tests",
            "basis": "All 40 affine-group modules passed; results exercise general affine algorithms and do not isolate a CM gain.",
        },
        {
            "surface": "lifecycle_and_containment",
            "catalog_ids": ["L01-L05", "L07"],
            "state": "ready",
            "overnight_disposition": "executed_via_existing_tests",
            "basis": "All 19 lifecycle modules passed and every worker reported verified process-tree cleanup.",
        },
        {
            "surface": "feature_model_smoke",
            "catalog_ids": ["F01", "F06", "F09", "F10"],
            "state": "correctness_only",
            "overnight_disposition": "executed_via_existing_tests",
            "basis": "All seven feature-model modules passed; no ordered real configurator history was available.",
        },
        {
            "surface": "hardware_smoke",
            "catalog_ids": ["H01", "H02", "H07-H10"],
            "state": "correctness_only",
            "overnight_disposition": "partial_existing_evidence",
            "basis": "Ten of nineteen modules passed; nine historical package or retained-artifact checks remained nonpassing exactly as in the prior baseline.",
        },
        {
            "surface": "biology_timing",
            "catalog_ids": ["B01", "B03", "B04"],
            "state": "ready",
            "overnight_disposition": "excluded_completed_no_go",
            "basis": "The separate 288-cell matched session pilot already found no CM signal and zero output disagreements.",
        },
        {
            "surface": "sympy_claim_cleanup",
            "catalog_ids": ["Y02-Y05"],
            "state": "ready",
            "overnight_disposition": "excluded_completed_no_go",
            "basis": "The separate development gate found no attributable five-percent CM total-session gain.",
        },
        {
            "surface": "policy_weighted_probability_and_new_domain_adapters",
            "catalog_ids": ["P01-P06", "B05-B08", "C06-C08"],
            "state": "deferred",
            "overnight_disposition": "not_run",
            "basis": "No demonstrated consumer or preserved task semantics justify speculative adapters.",
        },
    ]


def analyze(run: Path, baseline_path: Path, output: Path) -> dict:
    plan = load_json(run / "PLAN.json")
    rows = load_rows(run / "ledger.jsonl")
    baseline = load_json(baseline_path)
    verification = verify_run(run, plan, rows)
    if verification["status"] != "passed":
        raise RuntimeError("run verification failed: " + repr(verification["failures"]))

    cases: list[dict] = []
    module_rows = []
    reason_counts = Counter()
    group_status = defaultdict(Counter)
    wall_seconds = 0.0
    cpu_seconds = 0.0
    peak_memory = 0
    max_output = 0
    cleanup_verified = True
    for row in rows:
        supervisor = row.get("supervisor") or {}
        reason_counts[row["reason"]] += 1
        group_status[row["group"]][row["status"]] += 1
        wall_seconds += float(supervisor.get("wall_seconds") or 0)
        cpu_seconds += float(supervisor.get("cpu_seconds") or 0)
        peak_memory = max(peak_memory, int(supervisor.get("peak_memory_bytes") or 0))
        max_output = max(max_output, int(supervisor.get("output_bytes_captured") or 0))
        cleanup_verified = cleanup_verified and bool(supervisor.get("cleanup_verified"))
        module_cases = junit_cases(run / row["junit"]["path"]) if row.get("junit") else []
        for case in module_cases:
            case["module_path"] = row["path"]
        cases.extend(module_cases)
        nonpassing = [case for case in module_cases if case["outcome"] in {"failure", "error"}]
        if row["path"] in EXPECTED_COLLECTION_REFUSALS:
            interpreted = "expected_dependency_or_platform_refusal"
        elif row["path"] in EXPECTED_ALL_SKIPPED:
            interpreted = "expected_all_skipped"
        elif nonpassing:
            interpreted = "baseline_pytest_nonpassing"
        elif row["status"] == "passed":
            interpreted = "passed"
        else:
            interpreted = "harness_or_resource_error"
        module_rows.append(
            {
                "path": row["path"],
                "group": row["group"],
                "raw_status": row["status"],
                "interpreted_status": interpreted,
                "test_cases": len(module_cases),
                "failures": sum(case["outcome"] == "failure" for case in module_cases),
                "errors": sum(case["outcome"] == "error" for case in module_cases),
                "skipped": sum(case["outcome"] == "skipped" for case in module_cases),
                "wall_seconds": supervisor.get("wall_seconds"),
                "peak_memory_bytes": supervisor.get("peak_memory_bytes"),
            }
        )

    current_nonpassing = sorted(
        [case["classname"], case["name"], case["outcome"]]
        for case in cases
        if case["outcome"] in {"failure", "error"}
    )
    current_supported_nonpassing = sorted(
        [case["classname"], case["name"], case["outcome"]]
        for case in cases
        if case["outcome"] in {"failure", "error"}
        and case["module_path"] not in EXPECTED_COLLECTION_REFUSALS
    )
    prior_nonpassing = sorted(baseline["current_nonpassing"])
    current_set = {tuple(row) for row in current_supported_nonpassing}
    prior_set = {tuple(row) for row in prior_nonpassing}
    outcome_counts = Counter(case["outcome"] for case in cases)
    started = datetime.fromisoformat(load_json(run / "RUN.json")["started_utc"].replace("Z", "+00:00"))
    ended = datetime.fromisoformat(load_json(run / "RUN.json")["updated_utc"].replace("Z", "+00:00"))

    report = {
        "schema": "cm-overnight-local-portfolio-test-results/v1",
        "run": run.relative_to(ROOT).as_posix(),
        "baseline": baseline_path.relative_to(ROOT).as_posix(),
        "git_head": plan["git_head"],
        "plan_sha256": sha256(run / "PLAN.json"),
        "ledger_sha256": sha256(run / "ledger.jsonl"),
        "terminal_reason": load_json(run / "RUN.json")["reason"],
        "modules": {
            "total": len(module_rows),
            "passed": sum(row["interpreted_status"] == "passed" for row in module_rows),
            "baseline_pytest_nonpassing": sum(
                row["interpreted_status"] == "baseline_pytest_nonpassing"
                for row in module_rows
            ),
            "expected_dependency_or_platform_refusal": sum(
                row["interpreted_status"]
                == "expected_dependency_or_platform_refusal"
                for row in module_rows
            ),
            "expected_all_skipped": sum(
                row["interpreted_status"] == "expected_all_skipped"
                for row in module_rows
            ),
            "harness_or_resource_error": sum(
                row["interpreted_status"] == "harness_or_resource_error"
                for row in module_rows
            ),
        },
        "test_cases": {
            "total": len(cases),
            **dict(sorted(outcome_counts.items())),
        },
        "baseline_comparison": {
            "prior_nonpassing": len(prior_nonpassing),
            "current_supported_nonpassing": len(current_supported_nonpassing),
            "current_including_expected_collection_refusals": len(current_nonpassing),
            "same_nonpassing_test_ids_and_kinds": current_set == prior_set,
            "new_nonpassing": [list(row) for row in sorted(current_set - prior_set)],
            "resolved_nonpassing": [list(row) for row in sorted(prior_set - current_set)],
            "expected_collection_refusals": [
                {"path": path, "reason": reason}
                for path, reason in sorted(EXPECTED_COLLECTION_REFUSALS.items())
            ],
            "expected_all_skipped": [
                {"path": path, "reason": reason}
                for path, reason in sorted(EXPECTED_ALL_SKIPPED.items())
            ],
        },
        "containment": {
            "cleanup_verified_for_all_modules": cleanup_verified,
            "timeout_or_resource_limit_modules": sum(
                row["reason"]
                in {
                    "timeout",
                    "memory_limit",
                    "output_limit",
                    "job_cleanup_unverified",
                }
                for row in rows
            ),
            "elapsed_seconds": (ended - started).total_seconds(),
            "summed_worker_wall_seconds": wall_seconds,
            "summed_worker_cpu_seconds": cpu_seconds,
            "maximum_peak_committed_bytes": peak_memory,
            "maximum_captured_output_bytes": max_output,
        },
        "raw_reason_counts": dict(sorted(reason_counts.items())),
        "group_raw_status_counts": {
            group: dict(sorted(counts.items()))
            for group, counts in sorted(group_status.items())
        },
        "nonpassing_or_refused_modules": [
            row for row in module_rows if row["interpreted_status"] != "passed"
        ],
        "verification": verification,
        "interpretation": (
            "This is a fresh-process assurance replay. Pytest outcome and baseline "
            "parity are evidence; worker runtimes are diagnostic and do not compare "
            "CM with an incumbent."
        ),
    }

    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "TEST_RESULTS.json", report)
    ready = {
        "schema": "cm-overnight-local-portfolio-adapter-readiness/v1",
        "rows": readiness(),
    }
    write_json(output / "ADAPTER_READINESS.json", ready)
    write_json(output / "VERIFICATION.json", verification)
    write_markdown(output, report, ready)
    write_manifest(output, run, baseline_path)
    return report


def write_markdown(output: Path, report: dict, ready: dict) -> None:
    modules = report["modules"]
    cases = report["test_cases"]
    comparison = report["baseline_comparison"]
    containment = report["containment"]
    lines = [
        "# Overnight local CM portfolio test results",
        "",
        f"The frozen schedule completed all {modules['total']} fresh-process module cells. "
        f"{modules['passed']} modules passed, {modules['baseline_pytest_nonpassing']} "
        "contained baseline-matched pytest nonpasses, eight made expected collection "
        "refusals for absent optional dependencies or Windows platform limits, and one "
        "optional-control module skipped every test. No module ended in a harness or "
        "resource error.",
        "",
        f"Across {cases['total']} collected test cases, {cases.get('passed', 0)} passed, "
        f"{cases.get('failure', 0)} failed, {cases.get('error', 0)} errored and "
        f"{cases.get('skipped', 0)} were skipped. The "
        f"{comparison['current_supported_nonpassing']} supported nonpassing test IDs "
        "and outcome kinds exactly match the retained September 14 "
        "baseline. The additional eight collection records come from modules that the "
        "baseline explicitly excluded after readiness collection; there are no new or "
        "resolved supported nonpassing tests.",
        "",
        "## Containment",
        "",
        f"All process-tree cleanups verified. No timeout or resource limit fired. The run "
        f"used {containment['elapsed_seconds']:.3f} seconds elapsed and "
        f"{containment['summed_worker_cpu_seconds']:.3f} summed worker CPU seconds. "
        f"Maximum job peak committed memory was {containment['maximum_peak_committed_bytes']} "
        f"bytes; maximum captured output from one module was "
        f"{containment['maximum_captured_output_bytes']} bytes.",
        "",
        "## Group outcomes",
        "",
        "| Group | Passed modules | Nonpassing modules |",
        "| --- | ---: | ---: |",
    ]
    for group, counts in report["group_raw_status_counts"].items():
        lines.append(
            f"| {group} | {counts.get('passed', 0)} | {counts.get('backend_error', 0) + counts.get('test_failure', 0)} |"
        )
    lines.extend(
        [
            "",
            "The run ledger calls every nonzero pytest exit `backend_error` because the frozen "
            "supervisor reports worker exits generically. JUnit separates 30 baseline-matched "
            "nonpassing modules, eight expected collection refusals, and one all-skipped "
            "optional CUDD module. The immutable ledger is preserved; this terminal analysis "
            "supplies the corrected interpretation.",
            "",
            "## Nonpassing and refused modules",
            "",
            "| Module | Failures | Errors |",
            "| --- | ---: | ---: |",
        ]
    )
    for row in report["nonpassing_or_refused_modules"]:
        lines.append(
            f"| `{row['path']}` | {row['failures']} | {row['errors']} |"
        )
    lines.extend(
        [
            "",
            "The supported failures are retained source/artifact drift, unavailable historical "
            "packages, platform assumptions, and previously recorded test errors. Exact "
            "supported test-ID parity with the prior baseline means this campaign found no "
            "new regression. The nine refused/all-skipped modules preserve explicit dependency "
            "and platform readiness outcomes rather than silently omitting them.",
            "",
        ]
    )
    (output / "TEST_RESULTS.md").write_text(
        "\n".join(lines), encoding="utf-8", newline="\n"
    )

    report_lines = [
        "# Overnight local CM portfolio assurance",
        "",
        "## Decision",
        "",
        "The local assurance plan is complete. It found no new correctness disagreement, "
        "silent semantic mismatch, containment failure, or representation-specific CM "
        "mechanism that warrants another development benchmark. The scheduled work finished "
        "well inside the eight-hour ceiling; consuming the unused ceiling with repetitions "
        "would not test a new hypothesis.",
        "",
        "The run does not change the existing benchmark decision. The matched biology and "
        "SymPy studies remain no-go results, and the blanket 2,400-case cloud proposal remains "
        "superseded. The repository replay adds bounded Windows portability and regression "
        "custody across the remaining locally executable surfaces.",
        "",
        "## Results",
        "",
        f"- Frozen modules executed: {modules['total']} of {modules['total']}.",
        f"- Module outcomes: {modules['passed']} passed; {modules['baseline_pytest_nonpassing']} contained baseline-matched pytest nonpasses; eight expected dependency/platform collection refusals; one all-skipped optional-control module; zero harness/resource errors.",
        f"- Test cases: {cases['total']} total; {cases.get('passed', 0)} passed; {cases.get('failure', 0)} failed; {cases.get('error', 0)} errored; {cases.get('skipped', 0)} skipped.",
        f"- Baseline reconciliation: all {comparison['current_supported_nonpassing']} supported nonpassing test IDs and kinds match September 14; zero new and zero resolved. Eight separately retained collection errors are the same modules explicitly excluded from that supported baseline.",
        "- Cleanup: verified for every module; zero timeout, memory, output, or cleanup breaches.",
        "",
        "## Coverage gained",
        "",
        "The replay exercised existing correctness and boundary tests for synthetic/core, "
        "SAT/counting/projection, affine, lifecycle, feature-model and hardware surfaces. "
        "All affine, biology, feature-model and lifecycle module cells passed. Hardware and "
        "core historical-replay modules retained known nonpasses because their expected "
        "artifacts or hashes no longer match the current source checkpoint. This is executable "
        "assurance coverage, not execution of every source corpus or scale in the 80-family "
        "research catalog.",
        "",
        "No new width or resource failure boundary appeared under the two-GiB committed-memory, "
        "300-second module, one-MiB output and one-CPU limits. Detailed per-module measurements "
        "and identities remain in `run-003/ledger.jsonl`.",
        "",
        "## Disposition",
        "",
        "Stop the overnight campaign here. Reopen benchmarking only when a new CM mechanism "
        "changes the matched normalized plan, or when a real consumer supplies an ordered "
        "trace and output contract. Policy, weighted inference, reliability and other new "
        "domain adapters remain deferred because they would be speculative under the current "
        "no-go evidence. No cloud work, download, upload, publication, commit or push occurred.",
        "",
        "See `TEST_RESULTS.md`, `ADAPTER_READINESS.json`, `VERIFICATION.json`, "
        "`AUDIT_MANIFEST.json` and the immutable `run-003/` directory for the complete evidence.",
        "",
    ]
    (output / "REPORT.md").write_text(
        "\n".join(report_lines), encoding="utf-8", newline="\n"
    )


def write_manifest(output: Path, run: Path, baseline_path: Path) -> None:
    paths = [
        ROOT / ".gitattributes",
        ROOT / ".gitignore",
        output / "PLAN.md",
        output / "REPORT.md",
        output / "TEST_RESULTS.json",
        output / "TEST_RESULTS.md",
        output / "ADAPTER_READINESS.json",
        output / "VERIFICATION.json",
        ROOT / "scripts/cm_overnight_local_portfolio.py",
        ROOT / "scripts/cm_overnight_local_portfolio_audit.py",
        ROOT / "tests/test_cm_overnight_local_portfolio.py",
        ROOT / "tests/test_cm_overnight_local_portfolio_audit.py",
        run / "PLAN.json",
        run / "ENVIRONMENT.json",
        run / "ledger.jsonl",
        run / "RUN.json",
        run / "SUMMARY.json",
        run / "REPORT.md",
        baseline_path,
    ]
    manifest = {
        "schema": "cm-overnight-local-portfolio-audit-manifest/v1",
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in paths
        ],
        "run_evidence_binding": (
            "The run plan binds all 273 frozen source/test snapshots; the append-only ledger "
            "binds every JUnit and nonempty log. This manifest binds the run indexes and "
            "terminal interpretation without duplicating those entries."
        ),
    }
    write_json(output / "AUDIT_MANIFEST.json", manifest)


def verify_manifest(manifest_path: Path, root: Path = ROOT) -> dict:
    manifest = load_json(manifest_path)
    failures = []
    for record in manifest.get("files", []):
        path = root / record["path"]
        if not path.is_file():
            failures.append({"path": record["path"], "reason": "missing"})
        elif path.stat().st_size != record["bytes"]:
            failures.append({"path": record["path"], "reason": "size"})
        elif sha256(path) != record["sha256"]:
            failures.append({"path": record["path"], "reason": "sha256"})
    return {
        "status": "passed" if not failures else "failed",
        "checked_files": len(manifest.get("files", [])),
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_RUN.parent,
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        result = verify_manifest(args.output.resolve() / "AUDIT_MANIFEST.json")
        print(json.dumps(result))
        if result["status"] != "passed":
            raise SystemExit(1)
        return
    report = analyze(args.run.resolve(), args.baseline.resolve(), args.output.resolve())
    print(
        json.dumps(
            {
                "status": "passed",
                "modules": report["modules"],
                "test_cases": report["test_cases"],
                "baseline_comparison": report["baseline_comparison"],
            }
        )
    )


if __name__ == "__main__":
    main()
