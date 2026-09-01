"""Independently reconcile and summarize the saved P7 W4 timing/RSS scout.

This verifier is deliberately separate from the hash-bound remote program and
controller.  Its summaries are diagnostic development-scout results, not the
principal P7 result and not an external-method comparison.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import statistics
import sys
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import p7_runner
from cmbench.comparative.corpus_freeze import validate_freeze


HERE = Path(__file__).resolve().parent
FAILED_RUN_DIR = HERE / "p7-w4-timing-v1-001"
RUN_DIR = HERE / "p7-w4-timing-v2-retry-001"
EVIDENCE = RUN_DIR / "evidence/run-output"
MANIFEST = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V2-20260830.json"
SELECTION = ROOT / "docs/research/verification/comparative-p7-w4-timing-scout-v1-2026-08-31/selection.json"
OUTPUT = HERE / "P7-W4-TIMING-FINAL-INDEPENDENT-AUDIT.json"
FREEZE_SHA256 = "d81ab57d4fbfe8a49a28314cc645d9ddf24e7d7182abfe1d2f36c016430c7b31"
BUNDLE_SHA256 = "83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668"
POLICIES = {
    "p7-ir": {
        "blocks": 8,
        "arms": ("cm-ir-current", "cm-ir-two-memo", "cm-cse-flat", "cm-raw-flat"),
        "baseline": "cm-ir-current",
        "cells": 384,
    },
    "p7-relation": {
        "blocks": 10,
        "arms": ("cm-dense", "cm-packed-bigint", "cm-packed-words", "cm-no-reinflate", "cm-cse-flat"),
        "baseline": "cm-dense",
        "cells": 600,
    },
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def median(values: list[int] | list[float]) -> float:
    if not values:
        raise ValueError("median requires a nonempty sample")
    return float(statistics.median(values))


def geometric_mean(values: list[float]) -> float:
    if not values or any(type(value) not in (int, float) or value <= 0 or not math.isfinite(value) for value in values):
        raise ValueError("geometric mean requires finite positive values")
    return math.exp(math.fsum(math.log(value) for value in values) / len(values))


def metric_summary(values: list[int]) -> dict:
    if not values or any(type(value) is not int or value <= 0 for value in values):
        raise ValueError("metric sample must contain positive integers")
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "min": ordered[0],
        "median": median(ordered),
        "max": ordered[-1],
    }


def paired_summary(rows: list[dict], baseline: str, candidate: str, metric: str) -> dict:
    by_key = {(row["case_id"], row["block"], row["arm"]): row for row in rows}
    pairs = []
    for case_id, block in sorted({(row["case_id"], row["block"]) for row in rows}):
        base = by_key.get((case_id, block, baseline))
        other = by_key.get((case_id, block, candidate))
        if base is None or other is None:
            raise ValueError("incomplete paired arm coverage")
        pairs.append((base[metric], other[metric]))
    ratios = [candidate_value / baseline_value for baseline_value, candidate_value in pairs]
    return {
        "baseline": baseline,
        "candidate": candidate,
        "metric": metric,
        "pairs": len(pairs),
        "candidate_over_baseline_geometric_mean": geometric_mean(ratios),
        "candidate_over_baseline_median": median(ratios),
        "candidate_lower_count": sum(candidate_value < baseline_value for baseline_value, candidate_value in pairs),
        "ties": sum(candidate_value == baseline_value for baseline_value, candidate_value in pairs),
        "candidate_higher_count": sum(candidate_value > baseline_value for baseline_value, candidate_value in pairs),
    }


def summarize_policy(rows: list[dict], spec: dict) -> dict:
    expected = 12 * spec["blocks"] * len(spec["arms"])
    if len(rows) != expected:
        raise ValueError("unexpected policy row count")
    keys = {(row["case_id"], row["block"], row["arm"]) for row in rows}
    if len(keys) != expected:
        raise ValueError("duplicate policy case/block/arm cell")
    cases = {row["case_id"] for row in rows}
    if len(cases) != 12:
        raise ValueError("unexpected policy case count")
    if {row["arm"] for row in rows} != set(spec["arms"]):
        raise ValueError("unexpected policy arm set")
    if {row["block"] for row in rows} != set(range(spec["blocks"])):
        raise ValueError("unexpected policy block set")

    arms = {}
    for arm in spec["arms"]:
        arm_rows = [row for row in rows if row["arm"] == arm]
        per_case_task = [
            median([row["task_total_wall_ns"] for row in arm_rows if row["case_id"] == case_id])
            for case_id in sorted(cases)
        ]
        arms[arm] = {
            "cells": len(arm_rows),
            "cases": len(cases),
            "task_total_wall_ns": metric_summary([row["task_total_wall_ns"] for row in arm_rows]),
            "fresh_process_controller_wall_ns": metric_summary(
                [row["fresh_process_controller_wall_ns"] for row in arm_rows]
            ),
            "process_tree_peak_rss_bytes": metric_summary(
                [row["process_tree_peak_rss_bytes"] for row in arm_rows]
            ),
            "median_of_case_median_task_total_wall_ns": median(per_case_task),
            "median_controller_over_task_ratio": median([
                row["fresh_process_controller_wall_ns"] / row["task_total_wall_ns"]
                for row in arm_rows
            ]),
        }

    comparisons = {}
    for candidate in spec["arms"]:
        if candidate == spec["baseline"]:
            continue
        comparisons[candidate] = {}
        for metric in ("task_total_wall_ns", "process_tree_peak_rss_bytes"):
            comparisons[candidate][metric] = paired_summary(rows, spec["baseline"], candidate, metric)
        comparisons[candidate]["by_origin"] = {}
        for origin in ("synthetic", "natural"):
            origin_rows = [row for row in rows if row["origin"] == origin]
            comparisons[candidate]["by_origin"][origin] = {
                metric: paired_summary(origin_rows, spec["baseline"], candidate, metric)
                for metric in ("task_total_wall_ns", "process_tree_peak_rss_bytes")
            }

    block_medians = {}
    for block in range(spec["blocks"]):
        block_medians[str(block)] = {
            arm: median([
                row["task_total_wall_ns"]
                for row in rows if row["block"] == block and row["arm"] == arm
            ])
            for arm in spec["arms"]
        }
    return {
        "cells": len(rows),
        "cases": len(cases),
        "blocks": spec["blocks"],
        "arms": arms,
        "paired_diagnostics": comparisons,
        "block_median_task_total_wall_ns": block_medians,
    }


def verify_zip(run: dict) -> dict:
    archive_path = RUN_DIR / "evidence.zip"
    evidence_record = run.get("evidence", {})
    if sha256(archive_path) != evidence_record.get("sha256"):
        raise ValueError("evidence ZIP hash mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate evidence member")
        for name in names:
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError("unsafe evidence member")
            extracted = RUN_DIR / "evidence" / Path(*pure.parts)
            if not extracted.is_file() or extracted.read_bytes() != archive.read(name):
                raise ValueError("extracted evidence mismatch: " + name)
    extracted_names = {
        path.relative_to(RUN_DIR / "evidence").as_posix()
        for path in (RUN_DIR / "evidence").rglob("*") if path.is_file()
    }
    if extracted_names != set(names):
        raise ValueError("evidence extraction member set mismatch")
    return {"bytes": archive_path.stat().st_size, "sha256": sha256(archive_path), "files": len(names)}


def verify_checksums(output: Path) -> None:
    rows = load(output / "checksums.json")["files"]
    expected = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*") if path.is_file() and path.name != "checksums.json"
    }
    if {row["path"] for row in rows} != expected:
        raise ValueError("P7 checksum member set mismatch")
    for row in rows:
        path = output / row["path"]
        if path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            raise ValueError("P7 checksum mismatch: " + row["path"])


def junit_counts(path: Path) -> dict:
    root = ET.parse(path).getroot()
    local = lambda element: element.tag.rsplit("}", 1)[-1]
    cases = [row for row in root.iter() if local(row) == "testcase"]
    result = {"tests": len(cases), "failures": 0, "errors": 0, "skipped": 0}
    for case in cases:
        children = {local(child) for child in case}
        for singular, plural in (("failure", "failures"), ("error", "errors"), ("skipped", "skipped")):
            result[plural] += int(singular in children)
    return result


def read_terminal_rows(output: Path, plan: dict, oracles: dict, origins: dict) -> list[dict]:
    records = []
    for segment in sorted((output / "ledger").glob("segment-*.jsonl")):
        records.extend(json.loads(line) for line in segment.read_text(encoding="utf-8").splitlines() if line.strip())
    by_cell: dict[str, list[dict]] = defaultdict(list)
    for row in records:
        by_cell[row["cell_id"]].append(row)
    planned = {cell["cell_id"]: cell for cell in plan["cells"]}
    if set(by_cell) != set(planned):
        raise ValueError("ledger/plan cell set mismatch")

    result = []
    worker_pids = []
    for cell_id, cell in planned.items():
        transitions = by_cell[cell_id]
        if (
            len(transitions) != 2
            or transitions[0].get("status") != "running"
            or transitions[1].get("status") != "ok"
            or transitions[0].get("attempt") != 1
            or transitions[1].get("attempt") != 1
            or transitions[0].get("request_sha256") != transitions[1].get("request_sha256")
        ):
            raise ValueError("ledger transition mismatch")
        terminal = transitions[1]["result"]
        worker = terminal["worker"]
        resources = terminal["resources"]
        timings = terminal["timings_ns"]
        if (
            terminal.get("status") != "ok"
            or terminal.get("performance_measurement") is not True
            or terminal.get("outside_span_validation") is not True
            or worker.get("performance_measurement") is not True
            or worker.get("cell_id") != cell_id
            or worker.get("case_id") != cell["case_id"]
            or worker.get("arm") != cell["arm"]
            or worker.get("semantic_sha256") != oracles[cell["case_id"]]["result_sha256"]
            or resources.get("cleanup_verified") is not True
            or resources.get("streams_closed") is not True
            or resources.get("whole_tree_rss_measured") is not True
        ):
            raise ValueError("terminal worker/oracle/resource mismatch")
        values = (
            timings.get("task_total_wall_ns"),
            timings.get("fresh_process_controller_wall_ns"),
            terminal.get("process_tree_peak_rss_bytes"),
        )
        if any(type(value) is not int or value <= 0 for value in values):
            raise ValueError("invalid timing/RSS metric")
        worker_pids.append(worker["environment"]["pid"])
        result.append({
            "cell_id": cell_id,
            "case_id": cell["case_id"],
            "origin": origins[cell["case_id"]],
            "arm": cell["arm"],
            "block": cell["block"],
            "arm_position": cell["arm_position"],
            "schedule_position": cell["schedule_position"],
            "task_total_wall_ns": values[0],
            "fresh_process_controller_wall_ns": values[1],
            "process_tree_peak_rss_bytes": values[2],
        })
    if len(worker_pids) != len(set(worker_pids)):
        raise ValueError("fresh worker PID reuse within pod")
    return result


def verify_policy(policy_id: str, freeze: dict, origins: dict) -> tuple[dict, list[dict]]:
    spec = POLICIES[policy_id]
    output = EVIDENCE / policy_id
    plan = load(output / "plan.json")
    p7_runner.validate_plan(plan, freeze)
    if (
        plan.get("policy_id") != policy_id
        or plan.get("profile") != "performance"
        or plan.get("performance_measurement") is not True
        or plan.get("blocks") != spec["blocks"]
        or len(plan.get("cells", [])) != spec["cells"]
    ):
        raise ValueError("plan scope mismatch")
    verify_checksums(output)
    if load(output / "source-before.json") != load(output / "source-after.json"):
        raise ValueError("P7 source identity changed")
    oracle_package = load(output / "oracles.json")
    oracles = p7_runner.validate_oracle_package(oracle_package, plan)
    state = p7_runner.read_segments(output / "ledger")
    reproduced = p7_runner.summary(plan, state, oracle_package, source_unchanged=True)
    saved = load(output / "summary.json")
    if reproduced != saved or saved.get("status") != "passed" or saved.get("performance_claim_permitted") is not True:
        raise ValueError("P7 summary reproduction mismatch")
    rows = read_terminal_rows(output, plan, oracles, origins)
    return {
        "plan_sha256": sha256(output / "plan.json"),
        "summary_sha256": sha256(output / "summary.json"),
        "checksums_sha256": sha256(output / "checksums.json"),
        "source_unchanged": True,
        "reproduced_summary": True,
        "diagnostics": summarize_policy(rows, spec),
    }, rows


def verify_outer(run: dict) -> dict:
    if (
        run.get("status") != "complete"
        or run.get("creation_http_status") != 201
        or run.get("uploaded_source_files") != 96
        or run.get("evidence", {}).get("verified") is not True
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or run.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
    ):
        raise ValueError("run or owned-cleanup status mismatch")
    runtime = load(EVIDENCE / "RUNTIME.json")
    remote_validation = load(EVIDENCE / "REMOTE-VALIDATION.json")
    if (
        runtime.get("runpod_pod_id") != run.get("pod_id")
        or len(runtime.get("affinity", [])) != 2
        or runtime.get("performance_measurement") is not True
        or runtime.get("principal_p7_result") is not False
        or runtime.get("w4_freeze_sha256") != FREEZE_SHA256
        or remote_validation.get("status") != "complete"
        or remote_validation.get("validation_errors") != []
        or remote_validation.get("source_unchanged") is not True
    ):
        raise ValueError("runtime or remote-validation mismatch")
    manifest = load(MANIFEST)
    expected_sources = [
        {"target": row["target"], "bytes": row["bytes"], "sha256": row["sha256"]}
        for row in manifest["files"]
    ]
    if (
        len(expected_sources) != 96
        or load(EVIDENCE / "SOURCE-BEFORE.json") != expected_sources
        or load(EVIDENCE / "SOURCE-AFTER.json") != expected_sources
    ):
        raise ValueError("outer source identity mismatch")
    counts = junit_counts(EVIDENCE / "focused.xml")
    if counts["tests"] <= 0 or any(counts[key] for key in ("failures", "errors", "skipped")):
        raise ValueError("focused JUnit mismatch")
    return {"runtime": runtime, "remote_validation": remote_validation, "focused_junit": counts}


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    failed = load(FAILED_RUN_DIR / "RUN.json")
    run = load(RUN_DIR / "RUN.json")
    failed_progress = [
        json.loads(line)
        for line in (FAILED_RUN_DIR / "upload-progress.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if (
        failed.get("status") != "failed"
        or failed.get("pod_id") != "fixszqtou7pal8"
        or failed.get("error") != "proxy HTTP 400"
        or failed.get("uploaded_source_files") != 0
        or failed.get("cleanup", {}).get("owned_pod_absent") is not True
        or failed.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
        or not failed_progress
        or failed_progress[-1].get("accepted_bytes") != 16 * (256 << 10)
    ):
        raise ValueError("preserved V1 transport failure mismatch")
    outer = verify_outer(run)
    archive = verify_zip(run)
    freeze = load(EVIDENCE / "DERIVED-FREEZE.json")
    validate_freeze(freeze)
    if freeze.get("freeze_sha256") != FREEZE_SHA256 or len(freeze.get("cases", [])) != 12:
        raise ValueError("derived freeze mismatch")
    selection = load(SELECTION)
    origins = {row["case_id"]: row["origin"] for row in selection["cases"]}
    if set(origins) != {case["case_id"] for case in freeze["cases"]}:
        raise ValueError("selection/freeze case mismatch")

    policies = {}
    all_rows = []
    for policy_id in POLICIES:
        policies[policy_id], rows = verify_policy(policy_id, freeze, origins)
        all_rows.extend(rows)
    if len(all_rows) != 984 or len({row["cell_id"] for row in all_rows}) != 984:
        raise ValueError("combined W4 cell identity mismatch")

    report = {
        "schema": "cm-runpod-p7-w4-timing-final-independent-audit/v1",
        "status": "passed_diagnostic_development_timing_scout",
        "run_directory": RUN_DIR.name,
        "pod_id": run["pod_id"],
        "attempts": [
            {
                "run_directory": FAILED_RUN_DIR.name,
                "pod_id": failed["pod_id"],
                "status": failed["status"],
                "error": failed["error"],
                "accepted_encoded_payload_bytes": failed_progress[-1]["accepted_bytes"],
                "uploaded_source_files": 0,
                "cleanup_verified": True,
                "estimated_compute_cost_usd": failed.get("estimated_compute_cost_usd"),
            },
            {
                "run_directory": RUN_DIR.name,
                "pod_id": run["pod_id"],
                "status": run["status"],
                "uploaded_source_files": run["uploaded_source_files"],
                "cleanup_verified": True,
                "estimated_compute_cost_usd": run.get("estimated_compute_cost_usd"),
            },
        ],
        "freeze_sha256": FREEZE_SHA256,
        "source_bundle_sha256": BUNDLE_SHA256,
        "archive": archive,
        "runtime": outer["runtime"],
        "focused_junit": outer["focused_junit"],
        "policies": policies,
        "combined": {
            "independent_development_cases": 12,
            "synthetic_cases": sum(origin == "synthetic" for origin in origins.values()),
            "natural_cases": sum(origin == "natural" for origin in origins.values()),
            "verified_primary_cells": len(all_rows),
            "fresh_worker_processes": len(all_rows),
            "performance_measurement": True,
            "principal_p7_result": False,
            "external_method_comparison": False,
            "confirmation_cases_used": False,
        },
        "interpretation_limits": [
            "development-scout diagnostics only; not the principal P7 result",
            "paired ratios are descriptive and carry no inferential significance claim",
            "sampled process-tree RSS is not a kernel-enforced memory quota",
            "fresh-process controller wall time includes process startup and supervision overhead",
            "the untouched W8 confirmation corpus remains reserved for a later confirmation stage",
        ],
        "successful_run_estimated_compute_cost_usd": run.get("estimated_compute_cost_usd"),
        "combined_attempt_estimated_compute_cost_usd": (
            float(failed.get("estimated_compute_cost_usd") or 0.0)
            + float(run.get("estimated_compute_cost_usd") or 0.0)
        ),
        "source_unchanged": True,
        "verified": True,
    }
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(OUTPUT)
    print(json.dumps({
        "status": report["status"],
        "cells": report["combined"]["verified_primary_cells"],
        "policies": {key: value["diagnostics"]["cells"] for key, value in policies.items()},
        "principal_p7_result": False,
        "verified": True,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
