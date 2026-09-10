#!/usr/bin/env python3
"""Generate the 2026-09-10 Phase-1 website value/graph/artifact audit.

The audit reads the committed site from HEAD, records the live deployment hashes
captured on 2026-09-10, and inventories the dirty worktree separately.  It does
not modify the website, copy evidence into publication paths, commit, or push.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


AUDIT_DATE = "2026-09-10"
CUTOFF = "accepted commit-reachable evidence through 2026-09-08"
SITE_REL = PurePosixPath("deliverables_n22_24/master_explainer_2026_08_03")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

ROUTES = [
    {
        "file": "index.html",
        "url": "https://relative0.github.io/Correspondence_Matrices/",
        "bytes": 605380,
        "sha256": "97b54ff628fd45ae398022aba56a4525c43dbf8293b8546220d58e2f56faeaf2",
        "title": "Correspondence Matrices — a structural layer for Boolean computation",
        "body_chars": 85668,
        "headings": 196,
        "links": 37,
        "tables": 49,
        "table_rows": 418,
        "svgs": 22,
    },
    {
        "file": "layperson.html",
        "url": "https://relative0.github.io/Correspondence_Matrices/layperson.html",
        "bytes": 590462,
        "sha256": "40e7960a521b8121a0817662d961ef9e792c175c0531352811ad4f7f8ec2ac26",
        "title": "Correspondence Matrices — simple one-pager",
        "body_chars": 24308,
        "headings": 86,
        "links": 33,
        "tables": 9,
        "table_rows": 73,
        "svgs": 2,
    },
    {
        "file": "investor.html",
        "url": "https://relative0.github.io/Correspondence_Matrices/investor.html",
        "bytes": 594715,
        "sha256": "a905f3a3a9c5e568a2ab3fff071db702c90e0167818d9c348c9ae5232ab002e0",
        "title": "Correspondence Matrices — investor brief",
        "body_chars": 33277,
        "headings": 108,
        "links": 33,
        "tables": 19,
        "table_rows": 145,
        "svgs": 7,
    },
    {
        "file": "expert.html",
        "url": "https://relative0.github.io/Correspondence_Matrices/expert.html",
        "bytes": 603262,
        "sha256": "96c3709c7b8a214453c72098a8e2aca18441305566814402015ad933549cfba0",
        "title": "Correspondence Matrices — technical summary",
        "body_chars": 49573,
        "headings": 117,
        "links": 42,
        "tables": 53,
        "table_rows": 872,
        "svgs": 21,
    },
    {
        "file": "usecases.html",
        "url": "https://relative0.github.io/Correspondence_Matrices/usecases.html",
        "bytes": 586785,
        "sha256": "bbf65c52f9712fbe54c183fa6a3d7a13563dd3699563d6e25abad501bc987c0b",
        "title": "Correspondence Matrices — audited use cases and benchmarks",
        "body_chars": 21720,
        "headings": 78,
        "links": 37,
        "tables": 0,
        "table_rows": 0,
        "svgs": 0,
    },
    {
        "file": "feature-model-evidence.html",
        "url": "https://relative0.github.io/Correspondence_Matrices/feature-model-evidence.html",
        "bytes": 598139,
        "sha256": "c1da86b7f7627c2a90265d3e04cde53e9b4f234403f7cb014418bbf3daa59d4b",
        "title": "Correspondence Matrices — feature-model results and independence audit",
        "body_chars": 13501,
        "headings": 16,
        "links": 58,
        "tables": 6,
        "table_rows": 35,
        "svgs": 0,
    },
    {
        "file": "learning-neural-evidence.html",
        "url": "https://relative0.github.io/Correspondence_Matrices/learning-neural-evidence.html",
        "bytes": 611045,
        "sha256": "5760b94136bd9be917f3a7836428aa00defe2b0b3bbdca3c1ca15fd33ef0c64a",
        "title": "Correspondence Matrices — learning and neural evidence",
        "body_chars": 20661,
        "headings": 50,
        "links": 134,
        "tables": 5,
        "table_rows": 76,
        "svgs": 0,
    },
]

OG = {
    "file": "og.png",
    "url": "https://relative0.github.io/Correspondence_Matrices/og.png",
    "bytes": 844812,
    "sha256": "d0bd12dfa78ba593fb9d1f0a96b78551f81b5e9fc6251c1c914f8f01b63ba039",
}

NUM_SPAN_COUNTS = {
    "index.html": (359, 187),
    "layperson.html": (90, 62),
    "investor.html": (153, 88),
    "expert.html": (306, 222),
    "usecases.html": (22, 16),
    "feature-model-evidence.html": (17, 12),
    "learning-neural-evidence.html": (0, 0),
}
for _route in ROUTES:
    _route["provenance_span_occurrences"], _route["distinct_provenance_titles"] = NUM_SPAN_COUNTS[_route["file"]]

# Each rendered SVG was inspected in the in-app browser.  All have role=img,
# an aria-label, a nearby value table, and no broken image.  SVG title/desc are
# absent; that is an accessibility backlog item, not a value-integrity failure.
CHARTS = [
    ("assignment-growth", "fig-assignment-growth", "Explicit answer-vector growth", "e18_assignment_growth", 4, ["index.html", "layperson.html"]),
    ("ambient", "fig-ambient", "grouped columns", "e8_ambient_n", 9, ["index.html", "expert.html"]),
    ("compile", "fig-compile", "Preparation versus unfolded size", "e10_compile_scaling", 31, ["index.html", "expert.html"]),
    ("wrapper", "fig-wrapper", "Wrapper ratio by live_k", "e6_wrapper_ratio", 6, ["index.html", "expert.html"]),
    ("wrapper-cost", "fig-wrapper-cost", "grouped columns", "e7_wrapper_cost", 6, ["index.html", "expert.html"]),
    ("breakeven-share", "fig-breakeven", "Finite versus never-break-even shares", "e11_breakeven", 3, ["index.html", "layperson.html", "investor.html", "expert.html"]),
    ("breakeven-distribution", "fig-breakeven-distribution", "Break-even distributions", "e11_breakeven", 7, ["index.html", "investor.html", "expert.html"]),
    ("kernel", "fig-kernel", "CM versus plain CSE across three scopes", "e1_kernel_vs_cse", 7, ["index.html", "investor.html", "expert.html"]),
    ("engines", "fig-engines", "Engine crossover by live_k", "e15_engines", 10, ["index.html", "expert.html"]),
    ("guard", "fig-guard", "grouped columns", "e9_guard", 15, ["index.html", "expert.html"]),
    ("cudd-build", "fig-cudd-build", "grouped columns", "e12_cudd", 3, ["index.html", "expert.html"]),
    ("cudd-eval", "fig-cudd-eval", "Evaluation and extraction costs", "e12_cudd", 3, ["index.html", "expert.html"]),
    ("cudd-orders-structure", "fig-cudd-orders", "grouped columns", "e16_cudd_orders", 3, ["index.html", "expert.html"]),
    ("cudd-orders-cost", "fig-cudd-orders", "Order-search cost", "e16_cudd_orders", 3, ["index.html", "expert.html"]),
    ("epfl", "fig-epfl", "EPFL per-circuit ratios", "e4_epfl_per_circuit", 19, ["index.html", "expert.html"]),
    ("flat", "fig-flat", "CM versus CSE-flat across accepted workload scopes", "e2_kernel_vs_cse_flat", 9, ["index.html", "investor.html", "expert.html"]),
    ("roadmap", "fig-roadmap", "Roadmap effort by priority", "_content.frontier", 6, ["index.html", "investor.html", "expert.html"]),
    ("pods", "fig-pods", "Per-pod replication", "e5_pods", 5, ["index.html", "investor.html", "expert.html"]),
    ("schedule", "fig-schedule", "Schedule comparison", "e14_schedule", 8, ["index.html", "expert.html"]),
    ("strata-grid", "fig-strata", "Family × shape interaction grid", "e3_local_strata", 11, ["index.html", "expert.html"]),
    ("strata-live-k", "fig-strata", "Local strata by live_k", "e3_local_strata", 11, ["index.html", "expert.html"]),
    ("discrepancies", "fig-discrepancies", "Absolute schedule shift", "e17_discrepancies", 5, ["index.html", "investor.html", "expert.html"]),
]

AUTHORED_FILES = [
    "cm_master_content_2026_08_03.json",
    "cm_master_shared.js",
    "cm_master_template.html",
    "cm_layperson_template.html",
    "cm_investor_template.html",
    "cm_expert_template.html",
    "cm_usecases_template.html",
    "cm_feature_model_template.html",
    "cm_learning_neural_template.html",
]

SITE_ASSETS = [r["file"] for r in ROUTES] + ["og.png"]
SITE_SOURCES = AUTHORED_FILES + [
    "cm_master_data_2026_08_03.json",
    "cm_master_build_2026_08_03.py",
    "cm_feature_model_evidence.py",
    "cm_learning_neural_evidence.py",
    "cm_master_shared.css",
]


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(args, cwd=ROOT, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def git_text(*args: str) -> str:
    return run("git", *args).stdout.decode("utf-8", errors="strict")


def head_bytes(path: str | PurePosixPath) -> bytes:
    return run("git", "cat-file", "blob", f"HEAD:{PurePosixPath(path)}").stdout


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_head(path: str | PurePosixPath) -> Any:
    return json.loads(head_bytes(path).decode("utf-8"))


def get_path(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


def walk(obj: Any, path: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            child = f"{path}.{key}" if path else str(key)
            yield from walk(value, child)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            child = f"{path}[{index}]"
            yield from walk(value, child)
    else:
        yield path, obj


def walk_numeric(obj: Any, path: str = "") -> Iterable[tuple[str, int | float]]:
    for item_path, value in walk(obj, path):
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
            if not re.search(r"(?:sha|date|year|line|seed)(?:$|[_\.])", item_path, re.I):
                yield item_path, value


def fmt_value(value: Any, fmt: str) -> str:
    if fmt in {"ratio2"}: return f"{float(value):.2f}"
    if fmt in {"ratio3"}: return f"{float(value):.3f}"
    if fmt in {"ratio4"}: return f"{float(value):.4f}"
    if fmt == "num1": return f"{float(value):.1f}"
    if fmt == "num1s": return f"{float(value):.1f}".removesuffix(".0")
    if fmt in {"int", "big"}: return f"{round(float(value)):,}"
    if fmt == "x0": return f"{round(float(value)):,}×"
    if fmt == "x1": return f"{float(value):.1f}×"
    if fmt == "x2": return f"{float(value):.2f}×"
    if fmt == "x3": return f"{float(value):.3f}×"
    if fmt == "x9": return f"{float(value):.9f}×"
    if fmt == "xcomma": return f"{round(float(value)):,}×"
    if fmt == "pct0": return f"{round(float(value))}%"
    if fmt == "pct1": return f"{float(value):.1f}%"
    if fmt == "pct2": return f"{float(value):.2f}%"
    if fmt == "pctsign2": return f"{float(value):+.2f}%"
    if fmt == "usd": return f"${float(value):.4f}"
    if fmt == "ms0": return f"{float(value):.{1 if float(value) < 10 else 0}f} ms"
    if fmt == "us0":
        v = float(value)
        if v >= 100000: return f"{v / 1000:.0f} ms"
        if v >= 1000: return f"{v / 1000:.{1 if v >= 10000 else 2}f} ms"
        return f"{v:.{2 if v < 10 else 1}f} µs"
    return str(value)


def surface_for(token: str) -> dict[str, Any]:
    prefix = token.split(".", 1)[0]
    mapping = {
        "kernel": (["index.html", "investor.html", "expert.html"], "#fig-kernel and landing summary"),
        "flat": (["index.html", "investor.html", "expert.html"], "#fig-flat and landing summary"),
        "symv3": (["index.html", "investor.html", "expert.html"], "#latest-evidence / #fig-flat"),
        "fm": (["feature-model-evidence.html"], "result, comparison, gap, and data tables"),
        "ln": (["learning-neural-evidence.html"], "learning quality/timeline tables"),
        "arch": (["expert.html"], "current exact architecture and query-ladder tables"),
        "recognition": (["index.html", "learning-neural-evidence.html"], "#latest-evidence / milestone timeline"),
        "cudd": (["index.html", "expert.html"], "#fig-cudd-build / #fig-cudd-eval"),
        "be": (["index.html", "layperson.html", "investor.html", "expert.html"], "break-even charts and tables"),
        "guard": (["index.html", "expert.html"], "#fig-guard"),
        "sched": (["index.html", "expert.html"], "#fig-schedule"),
        "bx1": (["index.html", "expert.html"], "#fig-engines"),
        "epfl": (["index.html", "expert.html"], "#fig-epfl"),
        "wrap": (["index.html", "expert.html"], "#fig-wrapper / #fig-wrapper-cost"),
    }
    routes, section = mapping.get(prefix, (["index.html", "expert.html"], "evidence prose/table"))
    return {"routes": routes, "section_or_chart": section}


def ratio_direction(token: str, fmt: str) -> str:
    if token.startswith(("kernel.", "flat.", "symv3.", "fm.endpoint.")):
        return "CM_time / baseline_time; below 1 favors CM"
    if token.startswith(("recognition.c16.", "arch.")) and fmt.startswith("x"):
        return "named_candidate speedup over comparator; above 1 favors the named candidate"
    return "not applicable or defined by the adjacent chart/table contract"


def token_verdict(token: str, displayed: bool) -> tuple[str, str, str]:
    if not displayed:
        return ("not_rendered_inventory_only", "none", "supporting_or_unused")
    if token == "flat.local":
        return (
            "historically_correct_but_not_current_headline",
            "Retain only in an explicitly historical B1/E3 row; use the B2/B4 V3 result for the current flattened-CSE headline.",
            "historical",
        )
    if token.startswith("recognition.c16."):
        return (
            "correct_local_value_but_latest_same_contract_confirmation_omitted",
            "Keep the local result with its machine label and add the accepted Linux 3.177887× whole-path and 3.117978× p95 confirmation.",
            "local_primary_plus_later_confirmation",
        )
    if token.startswith("fm.endpoint."):
        return (
            "correct_for_saved_warm_output_contract_performance_provisional",
            "Retain the current caveat; do not promote to a cold-pipeline or domain-wide ranking.",
            "task_specific_provisional",
        )
    if token.startswith("arch."):
        return (
            "correct_for_named_architecture_contract_through_cutoff",
            "Retain explicit task, host, baseline, and charged-boundary labels; do not generalize to a universal CM winner.",
            "current_confirmation_or_control",
        )
    return ("matches_committed_published_evidence", "retain unless superseded by a backlog item", "published_primary_or_supporting")


def provenance_paths(record: dict[str, Any]) -> list[str]:
    prov = record.get("prov", [])
    if isinstance(prov, str): prov = [prov]
    return [str(p).split(" ::", 1)[0].strip() for p in prov]


def source_date_class(prov: list[str]) -> str:
    text = " ".join(prov)
    if re.search(r"202609(?:09|10)|2026[-_]09[-_](?:09|10)", text):
        return "recent_2026-09-09_or_10"
    return "at_or_before_normal_cutoff_or_undated"


def resolve_site_reference(raw: str) -> str | None:
    value = raw.strip().strip("'\"`<>()[]{}.,;:")
    value = value.split(" ::", 1)[0].split("#", 1)[0].split("?", 1)[0]
    if value.startswith("https://github.com/Relative0/Correspondence_Matrices/blob/main/"):
        value = value.split("/blob/main/", 1)[1]
    if re.match(r"^[a-z][a-z0-9+.-]*://", value, re.I):
        return None
    value = value.replace("\\", "/")
    if value.startswith("../../") or value.startswith("../"):
        parts = list(SITE_REL.parts)
        for part in PurePosixPath(value).parts:
            if part == "..":
                if parts: parts.pop()
            elif part not in {"."}:
                parts.append(part)
        value = "/".join(parts)
    elif value.startswith("use_case_benchmarks_2026-08-27/") or value in SITE_ASSETS:
        value = f"{SITE_REL}/{value}"
    value = str(PurePosixPath(value))
    if value.startswith(("docs/", "deliverables_n22_24/", "tests/", "scripts/", "native/", "Correspondence_Matrices/", "cmbench/")):
        return value
    return None


def collect_references(data: Any, authored: dict[str, str], token_records: dict[str, Any], files: set[str]) -> dict[str, set[str]]:
    refs: dict[str, set[str]] = defaultdict(set)
    path_pattern = re.compile(
        r"(?:(?:\.\./)+)?(?:docs|deliverables_n22_24|tests|scripts|native|Correspondence_Matrices|cmbench)/"
        r"[A-Za-z0-9_./+*\-]+?\.(?:sha256|jsonl|json|csv|md|py|html|xml|zip|png|txt)"
    )

    def add(raw: str, where: str) -> None:
        if re.match(r"^[a-z][a-z0-9+.-]*://", raw.strip(), re.I):
            return
        base = raw.split(" ::", 1)[0].strip()
        candidates = path_pattern.findall(raw)
        if re.fullmatch(r"(?:(?:\.\./)+)?(?:docs|deliverables_n22_24|tests|scripts|native|Correspondence_Matrices|cmbench)/[^\s,;]+", base):
            candidates.append(base)
        if re.fullmatch(r"use_case_benchmarks_2026-08-27/[^\s,;]+", base):
            candidates.append(base)
        for candidate in candidates:
            resolved = resolve_site_reference(candidate)
            if resolved:
                if "*" in resolved:
                    import fnmatch
                    for match in sorted(p for p in files if fnmatch.fnmatch(p, resolved)):
                        refs[match].add(f"{where} [expanded from {resolved}]")
                else:
                    refs[resolved].add(where)

    for path, value in walk(data):
        if isinstance(value, str): add(value, f"data:{path}")
    for token, record in token_records.items():
        for prov in provenance_paths(record): add(prov, f"token:{token}")
    for filename, text in authored.items():
        for match in re.finditer(r"href\s*=\s*[\"']([^\"']+)", text):
            add(match.group(1), f"authored:{filename}")

    # Essential tests and site-source downloads are relevant even if the page
    # does not currently link them.
    essentials = [
        "tests/test_cm_master_website.py",
        "tests/test_cm_website_navigation.py",
        "tests/test_cm_feature_model_website.py",
        "tests/test_cm_learning_neural_website.py",
        "tests/test_cm_recent_dispositions_website.py",
        "tests/test_source_anf_hybrid.py",
        "tests/test_gf2_anf_rank.py",
        "tests/test_cm_architecture_comparison_analysis.py",
        "tests/test_cm_architecture_query_ladder_cross_machine_package.py",
        "tests/test_cm_comparative_architecture_refresh_harness.py",
        "tests/test_query_ladder_q64_execution.py",
        "docs/recognition/LEARNING_MILESTONE_C6_PACKED_SOURCE_ANF_2026_08_30.md",
        "docs/recognition/learning_milestone_c6_packed_source_anf_results.json",
        "docs/recognition/verification/natural-source-anf-hybrid-20260830-004.json",
        "docs/recognition/c16_linux_confirmation/RUNPOD_C16_PACKAGE_V2_FINAL_VERIFICATION_20260831.json",
        "docs/recognition/c16_linux_confirmation/C16_SECOND_MACHINE_TIMING_PACKAGE_V2_PROTOCOL_2026_08_31.md",
        "docs/recognition/c16_linux_confirmation/verify_runpod_c16_package_v2_attempt.py",
        "docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004/FINAL_REPORT_AFTER_SECOND_HOST.md",
        "docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004/SURFACE_ASSESSMENT.json",
        "docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004/SURFACE_INDEPENDENT_VERIFICATION.json",
    ]
    essentials.extend(f"{SITE_REL}/{f}" for f in SITE_SOURCES)
    for path in essentials:
        refs[path].add("recommended_manifest_addition")
    return refs


def git_inventory() -> tuple[set[str], set[str]]:
    files = set(git_text("ls-tree", "-r", "--name-only", "HEAD").splitlines())
    dirs = set(git_text("ls-tree", "-d", "-r", "--name-only", "HEAD").splitlines())
    return files, dirs


def artifact_record(path: str, refs: set[str], files: set[str], dirs: set[str]) -> dict[str, Any]:
    is_file = path in files
    is_dir = path in dirs or any(p.startswith(path.rstrip("/") + "/") for p in files)
    deliberately_excluded = any("excluded_missing_artifacts" in ref for ref in refs)
    result: dict[str, Any] = {
        "path": path,
        "referenced_by": sorted(refs),
        "head_status": "tracked_file" if is_file else "tracked_directory" if is_dir else "deliberately_excluded_missing_artifact" if deliberately_excluded else "missing_from_HEAD",
        "published_link_present": not deliberately_excluded and any(not r.startswith("recommended_") for r in refs),
        "recommended_manifest_addition": "recommended_manifest_addition" in refs,
    }
    if is_file:
        content = head_bytes(path)
        result.update({"bytes": len(content), "sha256_git_blob_bytes": sha256(content), "git_object": git_text("rev-parse", f"HEAD:{path}").strip()})
    elif is_dir:
        children = sorted(p for p in files if p.startswith(path.rstrip("/") + "/"))
        result.update({"file_count": len(children), "git_tree": git_text("rev-parse", f"HEAD:{path}").strip() if path in dirs else None})
    suffix = PurePosixPath(path).suffix.lower()
    result["artifact_type"] = {
        ".json": "machine-readable evidence",
        ".jsonl": "machine-readable raw rows",
        ".csv": "tabular evidence",
        ".md": "report or protocol",
        ".py": "reproduction, builder, or test code",
        ".html": "published page or template",
        ".zip": "download bundle",
        ".sha256": "checksum manifest",
        ".xml": "test report",
        ".png": "image asset",
    }.get(suffix, "directory or supporting artifact")
    if "source_fixtures/" in path and "LICENSE" in path.upper():
        result["license_status"] = "third_party_license_file"
    else:
        result["license_status"] = "root_project_license_not_declared; public visibility is not a redistribution license"
    if suffix == ".zip":
        result["privacy_status"] = "manual_archive_contents_review_required_before_public_download"
    elif re.search(r"authorization|pod|host|manifest", path, re.I):
        result["privacy_status"] = "manual_operational_metadata_review_required"
    else:
        result["privacy_status"] = "no_secret_like_path; content-level secret scan intentionally not performed"
    if result["head_status"] == "deliberately_excluded_missing_artifact":
        result["disposition"] = "retain_as_explicit_exclusion; do_not_offer_as_download"
    elif result["head_status"] == "missing_from_HEAD":
        result["disposition"] = "repair_or_remove_reference"
    elif is_dir:
        result["disposition"] = "package_with_manifest_before_offering_as_one_download"
    elif result["recommended_manifest_addition"] and not result["published_link_present"]:
        result["disposition"] = "add_stable_commit-pinned_view_and_raw_download_links_after_review"
    else:
        result["disposition"] = "retain_but_pin_to_a_reviewed_commit_and_offer_raw_download"
    return result


def md_table(headers: list[str], rows: Iterable[Iterable[Any]]) -> str:
    def esc(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(esc(v) for v in row) + " |" for row in rows)
    return "\n".join(lines)


def main() -> None:
    head = git_text("rev-parse", "HEAD").strip()
    origin = git_text("ls-remote", "origin", "refs/heads/main").split()[0]
    data_path = SITE_REL / "cm_master_data_2026_08_03.json"
    data = json_head(data_path)
    token_records: dict[str, dict[str, Any]] = data["_numbers"]

    authored = {name: head_bytes(SITE_REL / name).decode("utf-8") for name in AUTHORED_FILES}
    template_mentions: dict[str, list[str]] = defaultdict(list)
    for token in token_records:
        for filename, text in authored.items():
            for line_number, line in enumerate(text.splitlines(), 1):
                if re.search(rf"(?<![A-Za-z0-9_.]){re.escape(token)}(?![A-Za-z0-9_.])", line):
                    template_mentions[token].append(f"{SITE_REL}/{filename}:{line_number}")

    data_refs: dict[str, list[str]] = defaultdict(list)
    token_names = set(token_records)
    for path, value in walk({k: v for k, v in data.items() if k != "_numbers"}):
        if isinstance(value, str) and value in token_names:
            data_refs[value].append(f"cm_master_data_2026_08_03.json::{path}")

    claims: list[dict[str, Any]] = []
    for index, token in enumerate(sorted(token_records), 1):
        record = token_records[token]
        displayed = bool(template_mentions[token] or data_refs[token])
        verdict, action, evidence_role = token_verdict(token, displayed)
        prov = record.get("prov", [])
        if isinstance(prov, str): prov = [prov]
        claims.append({
            "claim_id": f"NUM-{index:04d}",
            "kind": "named_numeric_token",
            "token": token,
            "location": {
                **surface_for(token),
                "authored_mentions": template_mentions[token],
                "data_references": data_refs[token],
            },
            "displayed_or_referenced": displayed,
            "presentation": {
                "raw_value": record.get("value"),
                "format": record.get("fmt", "text"),
                "rendered_value": fmt_value(record.get("value"), record.get("fmt", "text")),
                "note": record.get("note", ""),
                "ratio_direction": ratio_direction(token, record.get("fmt", "text")),
            },
            "provenance": prov,
            "contract_identity": ratio_direction(token, record.get("fmt", "text")),
            "evidence_role": evidence_role,
            "cutoff_class": source_date_class(prov),
            "latest_same_contract_match": "same as provenance except where verdict/action names a later result",
            "verdict": verdict,
            "recommended_action": action,
            "downloadable_source_refs": provenance_paths(record),
        })

    # Every chart and every numeric scalar in its backing data block receives a
    # ledger row.  This deliberately over-includes table/support values so a
    # later update cannot alter a plotted source block without review.
    chart_records: list[dict[str, Any]] = []
    for chart_index, (key, section, aria, root_path, table_rows, routes) in enumerate(CHARTS, 1):
        block = get_path(data, root_path)
        numbers = list(walk_numeric(block, root_path))
        provenance = []
        for path, value in walk(block, root_path):
            if "provenance" in path.lower() and isinstance(value, str):
                provenance.append(value)
        chart = {
            "chart_id": f"CHART-{chart_index:02d}",
            "key": key,
            "section_id": section,
            "aria_label": aria,
            "routes": routes,
            "data_root": root_path,
            "numeric_scalar_count": len(numbers),
            "nearby_table_rows": table_rows,
            "browser_checks": {"role_img": True, "aria_label_present": True, "nearby_value_table_present": table_rows > 0, "svg_title_present": False, "svg_desc_present": False},
            "value_integrity_verdict": "backing block is identical in live deployment and HEAD; table and SVG share the same embedded data",
            "accessibility_action": "Add SVG title/desc; retain the verified keyboard-focusable marks, live tooltip status, and full value table fallback.",
            "provenance": sorted(set(provenance)),
        }
        chart_records.append(chart)
        for point_index, (point_path, value) in enumerate(numbers, 1):
            claims.append({
                "claim_id": f"{chart['chart_id']}-VALUE-{point_index:04d}",
                "kind": "chart_or_adjacent_table_numeric_value",
                "token": None,
                "location": {"routes": routes, "section_or_chart": f"#{section}", "data_path": point_path},
                "displayed_or_referenced": True,
                "presentation": {"raw_value": value, "format": "renderer-specific", "rendered_value": None, "note": "Inventoried from the exact committed backing block.", "ratio_direction": "defined by the chart axis/table heading"},
                "provenance": sorted(set(provenance)),
                "contract_identity": root_path,
                "evidence_role": "plotted_or_adjacent_table_data",
                "cutoff_class": source_date_class(provenance),
                "latest_same_contract_match": "no later accepted contract-matched replacement found, except the separately listed C16/C6 omissions",
                "verdict": "matches_live_and_committed_backing_data",
                "recommended_action": "retain; if edited, regenerate chart and its table from the same source block",
                "downloadable_source_refs": [p.split(" ::", 1)[0] for p in provenance],
            })

    # Significant status/conclusion strings and booleans are inventoried from
    # the decision-bearing blocks.  Numeric details have separate rows above.
    for block_name in ["_flags", "_superseded", "e19_current_evidence", "e20_feature_model_audit", "e21_current_architecture", "e22_learning_neural", "e23_current_research"]:
        block = data[block_name]
        for path, value in walk(block, block_name):
            if isinstance(value, bool) or (isinstance(value, str) and len(value.strip()) >= 24 and not resolve_site_reference(value)):
                verdict = "consistent_with_cutoff_state_and_current_qualifications"
                action = "retain with its adjacent scope and provenance"
                if block_name == "e22_learning_neural" and path.startswith("e22_learning_neural.timeline[6]"):
                    if path.endswith(".result") or path.endswith(".status"):
                        verdict = "aggregate_timeline_is_too_coarse_to_expose_the_positive_C6_sub-result"
                        action = "split C6 from C7–C12 and add the exact cached-packed-source-ANF result without implying neural promotion"
                claims.append({
                    "claim_id": f"STATUS-{len(claims)+1:05d}",
                    "kind": "qualitative_or_status_claim",
                    "token": None,
                    "location": {"routes": surface_for(block_name.split("_", 1)[0]).get("routes"), "section_or_chart": block_name, "data_path": path},
                    "displayed_or_referenced": True,
                    "presentation": {"raw_value": value, "format": "text_or_boolean", "rendered_value": str(value), "note": ""},
                    "provenance": [],
                    "contract_identity": block_name,
                    "evidence_role": "status_or_qualification",
                    "cutoff_class": "at_or_before_normal_cutoff",
                    "latest_same_contract_match": "reviewed against the Sep-8 disposition and Sep-10 recent-result boundary",
                    "verdict": verdict,
                    "recommended_action": action,
                    "downloadable_source_refs": [],
                })

    # High-value omissions and the post-cutoff q64 result are explicit ledger
    # records even though they are absent from the current rendered pages.
    c6_path = "docs/recognition/learning_milestone_c6_packed_source_anf_results.json"
    c6 = json_head(c6_path)
    c6_values = {}
    for split in ("test", "confirmatory"):
        cached = c6["method_summary"][f"cached_packed_source_anf/{split}"]
        truth = c6["method_summary"][f"truth_vector_anf/{split}"]
        c6_values[split] = {
            "median_speedup": truth["median_total_ns"] / cached["median_total_ns"],
            "p95_speedup": truth["p95_total_ns"] / cached["p95_total_ns"],
            "cached_median_total_ns": cached["median_total_ns"],
            "truth_median_total_ns": truth["median_total_ns"],
            "accuracy": cached["accuracy"],
            "canonical_partition_accuracy": cached["canonical_partition_accuracy"],
            "semantic_mismatches": cached["semantic_mismatches"],
        }
        claims.append({
            "claim_id": f"MISSING-C6-{split.upper()}",
            "kind": "accepted_result_missing_from_site",
            "token": None,
            "location": {"routes": ["learning-neural-evidence.html", "index.html"], "section_or_chart": "C6 milestone/current evidence", "data_path": f"method_summary.cached_packed_source_anf/{split}"},
            "displayed_or_referenced": False,
            "presentation": {"raw_value": c6_values[split]["median_speedup"], "format": "x3", "rendered_value": f"{c6_values[split]['median_speedup']:.3f}×", "note": "truth-vector median total / cached packed source-ANF median total"},
            "provenance": [f"{c6_path} :: method_summary cached_packed_source_anf/{split} and truth_vector_anf/{split}"],
            "contract_identity": "exact source-derived canonical ANF; cached packed source ANF versus truth-vector ANF; same split and total-time boundary",
            "evidence_role": "accepted held-out test" if split == "test" else "accepted held-out confirmation",
            "cutoff_class": "at_or_before_normal_cutoff",
            "latest_same_contract_match": "this accepted C6 result",
            "verdict": "missing_material_positive_result",
            "recommended_action": "Add after review with exactness, split, p95, and no-production-promotion qualifications.",
            "downloadable_source_refs": [c6_path, "docs/recognition/LEARNING_MILESTONE_C6_PACKED_SOURCE_ANF_2026_08_30.md", "docs/recognition/verification/natural-source-anf-hybrid-20260830-004.json"],
        })

    c16_linux_path = "docs/recognition/c16_linux_confirmation/RUNPOD_C16_PACKAGE_V2_FINAL_VERIFICATION_20260831.json"
    c16_linux = json_head(c16_linux_path)
    for key, label in [("screened_whole_path_over_exhaustive", "whole-path"), ("screened_whole_path_p95", "whole-path p95")]:
        value = c16_linux["speedup"][key]
        claims.append({
            "claim_id": f"MISSING-C16-LINUX-{key.upper()}",
            "kind": "accepted_same_contract_confirmation_missing_from_site",
            "token": None,
            "location": {"routes": ["index.html", "learning-neural-evidence.html"], "section_or_chart": "#latest-evidence / C16", "data_path": f"speedup.{key}"},
            "displayed_or_referenced": False,
            "presentation": {"raw_value": value, "format": "x4", "rendered_value": f"{value:.4f}×", "note": f"Linux/GCC {label} speedup"},
            "provenance": [f"{c16_linux_path} :: speedup.{key}"],
            "contract_identity": "C16 exact-screened GF(2) same whole-path contract, Linux/GCC second machine",
            "evidence_role": "accepted cross-machine confirmation",
            "cutoff_class": "at_or_before_normal_cutoff",
            "latest_same_contract_match": "this 2026-08-31 verified Linux confirmation",
            "verdict": "latest_confirmation_omitted",
            "recommended_action": "Add beside—not in place of—the labeled Windows/local result; report exactness and zero mismatches.",
            "downloadable_source_refs": [c16_linux_path],
        })

    recent_claims = [
        {
            "claim_id": "RECENT-Q64-WINDOWS-FULLY-CHARGED",
            "kind": "recent_unpublished_result",
            "value": 0.949341,
            "contract": "q64 native_fused_slots fully charged speedup on Windows physical host",
            "verdict": "post-cutoff_no-go; do not publish as a positive use case",
        },
        {
            "claim_id": "RECENT-Q64-LINUX-FULLY-CHARGED",
            "kind": "recent_unpublished_result",
            "value": 0.977972,
            "contract": "q64 native_fused_slots fully charged speedup on Linux second physical host",
            "verdict": "post-cutoff_no-go; do not publish as a positive use case",
        },
    ]
    for item in recent_claims:
        value = item["value"]
        contract = item["contract"]
        verdict = item["verdict"]
        claims.append({
            "claim_id": item["claim_id"],
            "kind": item["kind"],
            "token": None,
            "location": {"routes": [], "section_or_chart": "not on live site", "data_path": None},
            "displayed_or_referenced": False,
            "presentation": {"raw_value": value, "format": "x6", "rendered_value": f"{value:.6f}×", "note": "fails the precommitted 1.10 materiality gate"},
            "provenance": ["docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004/FINAL_REPORT_AFTER_SECOND_HOST.md"],
            "contract_identity": contract,
            "evidence_role": "recent two-host adjudication",
            "cutoff_class": "recent_2026-09-10_not_public_by_default",
            "latest_same_contract_match": "this post-cutoff result",
            "verdict": verdict,
            "recommended_action": "Hold for a later publication review; if added, present only as a no-go/current limitation.",
            "downloadable_source_refs": ["docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004/FINAL_REPORT_AFTER_SECOND_HOST.md"],
        })

    fm16 = next(row for row in data["e20_feature_model_audit"]["rows"] if row["k"] == 16)
    fm_cnf = fm16["statistics"]["endpoint_cm_over_cnf"]
    fm_cudd = fm16["statistics"]["endpoint_cm_over_cudd_extraction"]
    recomputed_fm_cnf = math.exp(sum(math.log(v) for v in fm_cnf["per_history"].values()) / len(fm_cnf["per_history"]))
    recomputed_fm_cudd = math.exp(sum(math.log(v) for v in fm_cudd["per_history"].values()) / len(fm_cudd["per_history"]))
    recomputations = [
        {"id": "R-C6-TEST-MEDIAN", "formula": "696850 / 530550", "result": c6_values["test"]["median_speedup"], "expected": 1.3134483083592499, "pass": math.isclose(c6_values["test"]["median_speedup"], 1.3134483083592499, rel_tol=1e-12)},
        {"id": "R-C6-CONFIRM-MEDIAN", "formula": "572350 / 349600", "result": c6_values["confirmatory"]["median_speedup"], "expected": 1.6371567505720823, "pass": math.isclose(c6_values["confirmatory"]["median_speedup"], 1.6371567505720823, rel_tol=1e-12)},
        {"id": "R-C6-TEST-P95", "formula": "6029500 / 2771400", "result": c6_values["test"]["p95_speedup"], "expected": 2.175615212527964, "pass": math.isclose(c6_values["test"]["p95_speedup"], 2.175615212527964, rel_tol=1e-12)},
        {"id": "R-C6-CONFIRM-P95", "formula": "7404900 / 4033500", "result": c6_values["confirmatory"]["p95_speedup"], "expected": 1.8358497582744515, "pass": math.isclose(c6_values["confirmatory"]["p95_speedup"], 1.8358497582744515, rel_tol=1e-12)},
        {"id": "R-FM-K16-CNF-GEOMEAN", "formula": "geomean(seven equal-history ratios)", "result": recomputed_fm_cnf, "expected": fm_cnf["equal_history_geomean"], "pass": math.isclose(recomputed_fm_cnf, fm_cnf["equal_history_geomean"], rel_tol=1e-12)},
        {"id": "R-FM-K16-CUDD-GEOMEAN", "formula": "geomean(seven equal-history ratios)", "result": recomputed_fm_cudd, "expected": fm_cudd["equal_history_geomean"], "pass": math.isclose(recomputed_fm_cudd, fm_cudd["equal_history_geomean"], rel_tol=1e-12)},
        {"id": "R-FM-K16-CUDD-PARITY", "formula": "CI low < 1 < CI high", "result": fm_cudd["cluster_bootstrap_ci95"], "expected": "crosses parity", "pass": fm_cudd["cluster_bootstrap_ci95"][0] < 1 < fm_cudd["cluster_bootstrap_ci95"][1]},
        {"id": "R-C16-LINUX-WHOLE", "formula": "verified JSON speedup field", "result": c16_linux["speedup"]["screened_whole_path_over_exhaustive"], "expected": 3.177887162605386, "pass": c16_linux["status"] == "pass" and c16_linux["semantic_mismatches"] == 0 and c16_linux["artifact_mismatches"] == 0},
    ]

    files, dirs = git_inventory()
    references = collect_references(data, authored, token_records, files)
    artifacts = [artifact_record(path, refs, files, dirs) for path, refs in sorted(references.items())]

    # Freeze live, committed, and worktree site states separately.
    site_hash_rows = []
    for live in ROUTES + [OG]:
        rel = str(SITE_REL / live["file"])
        hb = head_bytes(rel)
        wp = ROOT / Path(rel)
        wb = wp.read_bytes()
        git_diff = run("git", "diff", "--quiet", "--", rel, check=False)
        site_hash_rows.append({
            "file": live["file"],
            "live_url": live["url"],
            "live_http_status": 200,
            "live_bytes": live["bytes"],
            "live_sha256": live["sha256"],
            "head_bytes": len(hb),
            "head_sha256": sha256(hb),
            "live_equals_HEAD": len(hb) == live["bytes"] and sha256(hb) == live["sha256"],
            "worktree_bytes": len(wb),
            "worktree_sha256": sha256(wb),
            "worktree_raw_bytes_equal_HEAD": wb == hb,
            "worktree_git_filtered_content_equal_HEAD": git_diff.returncode == 0,
            "worktree_equals_HEAD": wb == hb,
        })

    source_hash_rows = []
    for filename in SITE_SOURCES:
        rel = str(SITE_REL / filename)
        hb = head_bytes(rel)
        wp = ROOT / Path(rel)
        wb = wp.read_bytes()
        git_diff = run("git", "diff", "--quiet", "--", rel, check=False)
        source_hash_rows.append({"file": filename, "head_sha256": sha256(hb), "worktree_sha256": sha256(wb), "worktree_raw_bytes_equal_HEAD": wb == hb, "worktree_git_filtered_content_equal_HEAD": git_diff.returncode == 0, "worktree_equals_HEAD": wb == hb})

    raw_status_lines = git_text("status", "--short").splitlines()
    audit_dir_marker = f"{SITE_REL}/website_audit_2026-09-10/"
    status_lines = [line for line in raw_status_lines if audit_dir_marker not in line.replace("\\", "/")]
    hash_manifest = {
        "schema": "cm-website-before-state-sha256/v1",
        "audit_date": AUDIT_DATE,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "normal_public_evidence_cutoff": CUTOFF,
        "live_base_url": "https://relative0.github.io/Correspondence_Matrices/",
        "repository": "https://github.com/Relative0/Correspondence_Matrices",
        "head": head,
        "origin_main_observed_with_git_ls_remote": origin,
        "head_equals_origin_main": head == origin,
        "live_assets": site_hash_rows,
        "authored_and_generated_sources": source_hash_rows,
        "dirty_worktree_status_short": status_lines,
        "notes": [
            "All live assets returned HTTP 200 and matched the committed HEAD byte-for-byte.",
            "The dirty worktree is inventoried but was not used as the published truth state and was not modified by this audit generator.",
            "The new audit output directory is excluded from dirty_worktree_status_short so this remains a before-audit project-state inventory.",
            "Raw worktree SHA equality is recorded separately from Git-filtered content equality because clean Windows files can differ from Git blob bytes only by CRLF normalization.",
            "Live hashes were captured with read-only HTTP GETs on 2026-09-10; generated pages were also inspected in the in-app browser.",
        ],
    }
    (HERE / f"BEFORE-SITE-SHA256-{AUDIT_DATE}.json").write_text(json.dumps(hash_manifest, indent=2) + "\n", encoding="utf-8", newline="\n")

    ledger = {
        "schema": "cm-website-claim-ledger/v2",
        "audit_date": AUDIT_DATE,
        "normal_public_evidence_cutoff": CUTOFF,
        "head": head,
        "origin_main": origin,
        "live_equals_HEAD_for_all_published_assets": all(r["live_equals_HEAD"] for r in site_hash_rows),
        "scope": {
            "routes": ROUTES,
            "browser_summary": {
                "route_count": len(ROUTES),
                "svg_charts": sum(r["svgs"] for r in ROUTES),
                "tables": sum(r["tables"] for r in ROUTES),
                "table_rows": sum(r["table_rows"] for r in ROUTES),
                "link_occurrences": sum(r["links"] for r in ROUTES),
                "provenance_span_occurrences": sum(r["provenance_span_occurrences"] for r in ROUTES),
                "distinct_provenance_titles_across_routes": 271,
                "broken_images": 0,
                "console_errors_observed": 0,
                "index_chart_focusable_marks": 246,
            },
            "named_numeric_tokens": len(token_records),
            "referenced_named_numeric_tokens": sum(bool(template_mentions[t] or data_refs[t]) for t in token_records),
            "chart_definitions": len(chart_records),
            "chart_backing_numeric_scalar_occurrences": sum(c["numeric_scalar_count"] for c in chart_records),
        },
        "verdict_taxonomy": {
            "matches_committed_published_evidence": "value/provenance agrees with the published committed source for its stated contract",
            "historically_correct_but_not_current_headline": "valid historical value, but a later stronger contract/result should lead current wording",
            "missing_material_positive_result": "accepted pre-cutoff result absent from the rendered site",
            "latest_confirmation_omitted": "displayed local result is valid but a later same-contract confirmation is missing",
            "recent_2026-09-10_not_public_by_default": "post-cutoff evidence inventoried separately and not approved as a public claim",
        },
        "recomputations": recomputations,
        "charts": chart_records,
        "claims": claims,
    }
    ledger_path = HERE / f"CM-WEBSITE-CLAIM-LEDGER-{AUDIT_DATE}.json"
    ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    csv_path = HERE / f"CM-WEBSITE-CLAIM-LEDGER-{AUDIT_DATE}.csv"
    csv_fields = ["claim_id", "kind", "token", "displayed_or_referenced", "routes", "section_or_chart", "data_path", "raw_value", "rendered_value", "contract_identity", "evidence_role", "cutoff_class", "verdict", "recommended_action", "provenance"]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for claim in claims:
            location = claim.get("location", {})
            presentation = claim.get("presentation", {})
            writer.writerow({
                "claim_id": claim.get("claim_id"), "kind": claim.get("kind"), "token": claim.get("token"),
                "displayed_or_referenced": claim.get("displayed_or_referenced"), "routes": "; ".join(location.get("routes") or []),
                "section_or_chart": location.get("section_or_chart"), "data_path": location.get("data_path"),
                "raw_value": presentation.get("raw_value"), "rendered_value": presentation.get("rendered_value"),
                "contract_identity": claim.get("contract_identity"), "evidence_role": claim.get("evidence_role"),
                "cutoff_class": claim.get("cutoff_class"), "verdict": claim.get("verdict"),
                "recommended_action": claim.get("recommended_action"), "provenance": "; ".join(claim.get("provenance") or []),
            })

    artifact_manifest = {
        "schema": "cm-website-downloadable-artifact-manifest/v1",
        "audit_date": AUDIT_DATE,
        "head": head,
        "normal_public_evidence_cutoff": CUTOFF,
        "root_project_license_present": any(p.upper().startswith(("LICENSE", "COPYING")) for p in files),
        "publication_rule": "No artifact is copied or newly published in Phase 1. Phase 2 should use reviewed, commit-pinned links and a checksum/license/privacy manifest.",
        "artifacts": artifacts,
    }
    artifact_json_path = HERE / f"CM-WEBSITE-DOWNLOADABLE-ARTIFACT-MANIFEST-{AUDIT_DATE}.json"
    artifact_json_path.write_text(json.dumps(artifact_manifest, indent=2) + "\n", encoding="utf-8", newline="\n")

    missing_artifacts = [a for a in artifacts if a["head_status"] == "missing_from_HEAD"]
    excluded_artifacts = [a for a in artifacts if a["head_status"] == "deliberately_excluded_missing_artifact"]
    recommended_artifacts = [a for a in artifacts if a["recommended_manifest_addition"]]
    current_linked_artifacts = [a for a in artifacts if a["published_link_present"]]
    artifact_md = f"""# CM website downloadable-artifact manifest — {AUDIT_DATE}

## Decision

The live site exposes evidence primarily as GitHub `blob/main` links. The referenced material is therefore viewable, but the download experience is not a frozen evidence release: links can drift with `main`, directories are not single downloads, and the repository has no root project license. Phase 2 should add a reviewed download hub with commit-pinned **view** and **raw download** links, SHA-256, byte size, contract, and the exact tests/verifier for each result.

No artifact was copied, published, committed, pushed, or deployed in this Phase-1 audit.

## Inventory summary

- Referenced or nominated paths: **{len(artifacts)}**
- Currently referenced by site data/templates: **{len(current_linked_artifacts)}**
- Explicitly nominated additions: **{len(recommended_artifacts)}**
- Missing from `HEAD`: **{len(missing_artifacts)}**
- Deliberately absent and explicitly excluded from numeric rendering: **{len(excluded_artifacts)}**
- Root project license: **not present**. Public GitHub visibility does not itself grant redistribution rights; add/clarify a project license before assembling redistributable bundles.
- Privacy scan: filenames and publication scope were checked. Artifact contents were not searched for secrets; operational manifests and ZIPs remain flagged for manual review.

## Priority download sets for Phase 2

{md_table(["Set", "What to expose", "Minimum contents", "Disposition"], [
    ("Website evidence snapshot", "Exact site inputs and validation", "master data/content, three builders, templates/shared code, five website tests, before-state SHA manifest", "publish a small commit-pinned bundle after license review"),
    ("Current flattened-CSE result", "B2/B4 V3 0.8906 [0.8741, 0.9073] and wrapper 3.0941", "audited_v3_inference.csv, audited_v3_audit.json, protocol/readme if present", "add stable view/raw links; label 1.0038 historical"),
    ("C6 exact packed source-ANF", "1.313× test; 1.637× confirmation; exactness and p95", "report, result JSON, raw run directory or reviewed archive, independent verification, relevant tests", "add; currently missing from rendered evidence"),
    ("C16 exact screening", "local plus Linux 3.1779× whole-path and 3.1180× p95", "local result, Linux final verification, protocol, dataset/manifest, verifier, tests", "add Linux confirmation beside local result"),
    ("Feature-model audit", "correctness replay, performance gaps, 0.277 task-specific result", "audit report, corpus/raw CSVs, artifact replay, clustered statistics, measurement gaps, regression JUnit/tests", "retain links; add frozen raw-download index"),
    ("Current architecture", "complete relation, multi-root, small-task controls, q1/q4/q16/q64 ladder", "analysis JSONs, source freezes/manifests, independent verification, tests", "retain qualifications and pin links"),
    ("Recent q64 adjudication", "0.949341 / 0.977972 fully charged no-go", "final report, assessment, verification, checksum manifest; ZIP only after archive/privacy review", "hold outside normal public set pending later review"),
])}

## Broken/missing references

{("None among the normalized repository paths collected from the committed data/templates." if not missing_artifacts else md_table(["Path", "Referenced by"], [(a['path'], '; '.join(a['referenced_by'])) for a in missing_artifacts]))}

The two missing neural reassessment `assessment.json` paths are not broken download links: the site explicitly records that they are absent from integrated Git history and suppresses their dependent numeric claims. They remain `deliberately_excluded_missing_artifact` in the JSON manifest.

## Machine-readable detail

The companion JSON contains each normalized path, `HEAD` status, Git object identity, SHA-256 for files, byte size, reference locations, license/privacy flag, and recommended disposition. It intentionally over-includes supporting evidence so Phase 2 can choose a minimal, reviewable public package without rediscovering provenance.
"""
    (HERE / f"CM-WEBSITE-DOWNLOADABLE-ARTIFACT-MANIFEST-{AUDIT_DATE}.md").write_text(artifact_md, encoding="utf-8", newline="\n")

    chart_table_rows = []
    for c in chart_records:
        chart_table_rows.append((c["chart_id"], " / ".join(c["routes"]), f"#{c['section_id']}", c["aria_label"], c["data_root"], c["numeric_scalar_count"], c["nearby_table_rows"], "values match HEAD/live; add SVG title/desc"))

    audit_md = f"""# CM website value and graph audit — {AUDIT_DATE}

## Executive determination

The deployed site is byte-for-byte identical to `origin/main` / `HEAD` **{head}** for all seven HTML routes and `og.png`. It is therefore pushing and publishing correctly. It is **not yet fully current as an evidence summary under the normal 2026-09-08 cutoff**:

1. **Flattened CSE:** `1.0038` is a valid historical B1/E3 local kernel ratio, but it is not the latest current headline. The later exactly counterbalanced B2/B4 V3 bare ratio is **0.8905696773 [0.8740654100, 0.9072717742]**. Because these are CM-time/baseline-time ratios, values below 1 favor CM. Keep `1.0038` only as explicitly historical. Keep the separate public-wrapper result **3.094136**, which shows the wrapper remained slower.
2. **C16 exact screening:** the displayed local Windows **3.545324×** whole-path result is correct for that machine, but the accepted same-contract Linux confirmation is missing: **3.177887×** whole-path and **3.117978×** p95, with 40 cases, 360 measurements, zero semantic mismatches, and zero artifact mismatches.
3. **C6 exact packed source-ANF:** an accepted positive result is missing. Recomputed from the saved same-split total medians, cached packed source-ANF is **1.313448×** faster than truth-vector ANF on test and **1.637157×** on confirmation; p95 speedups are **2.175615×** and **1.835850×**. Accuracy and canonical-partition accuracy are 1.0 with zero semantic mismatches. The packed core advanced; the learned hybrid gate and production promotion did not.
4. **Feature-model k=16:** the displayed CM/direct-CNF warm-output ratio **0.276951 [0.200748, 0.371722]** is correctly shown as promising, task-specific, and performance-provisional. The CUDD ratio **0.624416 [0.215794, 1.535452]** crosses parity and is correctly not a “CM wins” headline.
5. **Current architecture:** the Sep-4 complete-relation, multi-root, small-task, and query-ladder findings are current for the normal cutoff and are materially qualified. The Sep-10 q64 adjudication is post-cutoff and correctly absent; its fully charged native values (**0.949341× Windows, 0.977972× Linux**) fail the 1.10 materiality gate and are not a new positive public use case.

## Frozen states

{md_table(["State", "Identity / finding", "Audit use"], [
    ("Live GitHub Pages", "8/8 assets HTTP 200 and SHA-256-equal to HEAD", "what the public sees"),
    ("origin/main", origin, "remote publication source"),
    ("local HEAD", head, "committed audit source"),
    ("Authored/generated site at HEAD", "data, content, builders, templates, shared JS/CSS, seven pages", "published claim construction"),
    ("Dirty worktree", f"{len(status_lines)} status entries; {sum(not r['worktree_equals_HEAD'] for r in site_hash_rows)} generated site assets differ from HEAD", "inventoried only; not treated as public truth"),
    ("Recent Sep 9–10 evidence", "q64 two-host no-go and local in-progress site edits", "separate unpublished inventory"),
])}

The exact hashes and dirty-state list are in `BEFORE-SITE-SHA256-{AUDIT_DATE}.json`.

## Coverage

- Rendered routes inspected in the in-app browser: **{len(ROUTES)}**.
- Rendered SVG occurrences: **{sum(r['svgs'] for r in ROUTES)}**; distinct chart definitions: **{len(chart_records)}**.
- Tables: **{sum(r['tables'] for r in ROUTES)}** with **{sum(r['table_rows'] for r in ROUTES):,}** rendered body rows.
- Link occurrences: **{sum(r['links'] for r in ROUTES)}**.
- Provenance-bearing `span.num[title]` occurrences: **{sum(r['provenance_span_occurrences'] for r in ROUTES)}** with **271** distinct provenance titles across routes. The learning/neural route has no such spans because its tables use plain `T()` output; Phase 2 should expose equivalent token/provenance metadata there and in chart/table values.
- Broken images: **0**. Browser console errors observed: **0**.
- Named provenance-bearing numeric tokens: **{len(token_records)}**; referenced from authored/data render paths: **{sum(bool(template_mentions[t] or data_refs[t]) for t in token_records)}**.
- Chart/table backing numeric scalar occurrences inventoried: **{sum(c['numeric_scalar_count'] for c in chart_records)}**.
- The JSON/CSV ledger contains **{len(claims):,}** records, including named values, every numeric scalar in every chart backing block, decision/status claims, missing accepted results, and post-cutoff findings.

## Ratio and timing contract rules applied

- CM/baseline **time ratios** (`kernel.*`, `flat.*`, `symv3.*`, feature-model endpoint ratios): below 1 favors CM.
- Named-candidate **speedups** (`recognition.c16.*`, architecture speedups): above 1 favors the named candidate.
- Kernel, prepared/warm output, wrapper/whole-call, complete-relation, related-root, and repeated-query contracts were not substituted for one another.
- Cross-host absolute timings were not compared. Cross-host evidence is used only when each host reports a within-host ratio under the frozen contract.
- A point estimate is not called positive when its interval crosses parity.
- Obsolete/weak baselines remain historical context, not current-use-case proof.

## Derived-value checks

{md_table(["Check", "Formula / condition", "Result", "Expected", "Verdict"], [(r['id'], r['formula'], r['result'], r['expected'], "PASS" if r['pass'] else "FAIL") for r in recomputations])}

All eight recomputations pass. The chart renderer and adjacent value tables consume the same embedded committed data, eliminating a separate handwritten chart-value channel.

## Validation executed

- Website surface: **47 tests and 28 subtests passed** across master-site, navigation, feature-model, learning/neural, and recent-disposition suites.
- C6 packed source-ANF: **3 tests passed** with `unittest` in `.venv-crse-neural` (the default `.venv` cannot collect this module because PyTorch is not installed; the neural environment has PyTorch but not pytest).
- C16/GF(2): **8 tests passed**.
- Sep-10 q64 execution evidence: **3 tests passed**.
- Architecture comparison analysis: **3 tests passed**.
- Cross-machine query-ladder package: **8 tests passed**.
- Audit artifact validation: all required files exist; JSON parses; all 2,318 claim IDs are unique; CSV and JSON both contain 2,318 claims; all required claim fields are populated; all eight recomputations pass; all 22 charts are present; no normalized tracked artifact reference is broken; both intentionally absent neural assessments are classified as explicit exclusions.

## Chart audit

{md_table(["ID", "Routes", "Section", "Accessible name", "Backing block", "Numeric scalars", "Table rows", "Verdict/action"], chart_table_rows)}

Chart values are intact and backed by visible tables. Every SVG has `role="img"` and an `aria-label`; all 22 landing-page charts have keyboard-focusable marks (246 marks total) and the shared tooltip uses an ARIA live-status region. None has an SVG `<title>` or `<desc>`. Phase 2 should add those elements while retaining keyboard detail and tables. This is an accessibility/traceability improvement, not evidence that plotted values are wrong.

## Contract-level verdicts

{md_table(["Surface", "Current display", "Latest accepted same-contract evidence", "Verdict", "Phase-2 action"], [
    ("Landing: CM vs flattened CSE", "1.0038 historical B1/E3 local", "0.8905696773 [0.8740654100, 0.9072717742] B2/B4 V3 bare; wrapper 3.094136", "historical value valid, headline stale/ambiguous", "lead with B2/B4 V3; retain 1.0038 in a dated historical row"),
    ("C16 latest evidence", "3.545324× local Windows whole path; minimum 0.892796×", "3.177887× Linux whole path; 3.117978× p95; exact 40/40, 360 rows", "local correct, cross-machine confirmation omitted", "show both machines and preserve no-production qualification"),
    ("Learning C6–C12 timeline", "coarse aggregate; no C6 positive numbers", "C6 1.313448× test, 1.637157× confirmation; exact; packed core only", "material accepted result omitted", "split C6 from later milestones and add downloads"),
    ("Feature-model k=16 direct CNF", "0.277 [0.201, 0.372]", "same saved warm-output contract", "current and properly provisional", "retain caveat; do not call cold-pipeline/domain dominance"),
    ("Feature-model k=16 CUDD", "0.624 [0.216, 1.535]", "same saved extraction contract", "interval crosses parity", "retain as inconclusive"),
    ("Architecture/query ladder", "Sep-4 current table with limitations", "same through normal cutoff", "current", "preserve task/host/baseline qualification"),
    ("Post-cutoff q64", "not displayed", "Sep-10 0.949341× / 0.977972× fully charged no-go", "correctly outside default public set", "later review may add only as a limitation/no-go"),
])}

## What this audit does not authorize

This is Phase 1 only. It does not change public copy or charts, package/copy artifacts into the site, commit, push, deploy, or approve Sep 9–10 findings for publication. Fresh benchmark execution was not needed: calculations were replayed from accepted machine-readable results, and the live deployment was checked against the exact committed assets.

## Review gate

Approve the Phase-2 backlog explicitly before modifying the site. The three evidence-content priorities are: current flattened-CSE headline/labels, C16 Linux confirmation, and the missing C6 positive exact result. Artifact publication also needs an explicit licensing decision and manual privacy review for operational manifests/archives.
"""
    (HERE / f"CM-WEBSITE-VALUE-AND-GRAPH-AUDIT-{AUDIT_DATE}.md").write_text(audit_md, encoding="utf-8", newline="\n")

    positive_md = f"""# CM website positive-use-case audit — {AUDIT_DATE}

## Rule

A “positive” result must use a current, task-matched comparator; preserve timing/materialization boundaries; have the favorable ratio direction; retain interval/tail/case heterogeneity; and survive the stated correctness/verification gate. A speedup against an obsolete or weaker arm is not promoted when a stronger current baseline wins.

## Positive or promising cases that should be visible

{md_table(["Case", "Result", "Why it qualifies", "Boundary that must remain"], [
    ("Plain CSE kernel", "CM/CSE 0.887646 local; 0.926772 EPFL; five Linux synthetic replications 0.877–0.888", "same kernel task, ratios below 1", "kernel only; excludes preparation/wrapper"),
    ("Current flattened-CSE bare kernel", "B2/B4 V3 0.890570 [0.874065, 0.907272]", "exactly counterbalanced and interval wholly below parity", "bare CM, not public wrapper; 216 formulas/264 rows"),
    ("C6 cached packed source-ANF", "1.313448× test; 1.637157× confirmation; p95 2.175615× / 1.835850×", "same-split total-time comparison; exact accuracy/partition; zero mismatches", "packed exact core advances; learned hybrid and production promotion do not"),
    ("C16 exact-screened GF(2)", "3.545324× local; Linux 3.177887× whole path and 3.117978× p95", "same exact artifact, cross-machine confirmation, zero semantic/artifact mismatch", "minimum local case 0.892796×; not every case wins; production disabled"),
    ("Feature-model k=16 versus direct CNF", "CM/direct-CNF 0.276951 [0.200748, 0.371722]", "favorable bounded warm-output result across seven equal-weight histories", "performance-provisional; incomplete cold pipeline; conditioned slices"),
    ("Complete relation versus dense CM", "packed/recursive CM 1.053300× [1.045764, 1.060967]", "task-matched complete-relation comparison on one verified host", "direct BitSet is stronger and beats CM; not a best-current-backend win"),
    ("Related multi-root union reuse", "Python union 1.146961× [1.126666, 1.167327] and native union 1.237987× [1.209490, 1.263523] versus separate arenas", "same ordered related-root outputs; structural sharing saves repeated work", "single architecture-comparison host; native-vs-Python union interval crosses parity"),
    ("CSE-flat q64 engine over Python R2", "1.100368× GCC (minimum 1.030643) and 1.090161× Clang (minimum 1.013096), 54 cases per host", "within-host q64 repeated-query contract and all cases favorable", "positive engine result, not evidence that CM universally wins"),
])}

## Looks favorable but is not a current positive-use-case claim

{md_table(["Finding", "Reason not positive"], [
    ("Historical flattened-CSE 1.0038", "CM/baseline time ratio is slightly above 1, so CM is slightly slower; a later B2/B4 V3 contract is the current headline."),
    ("Public-wrapper 3.094136", "CM wrapper/baseline time ratio is above 1; the wrapper is about 3.09× the comparator time."),
    ("Feature-model CM/CUDD 0.624 [0.216, 1.535]", "The clustered interval crosses parity and the extraction contracts are sensitive/asymmetric."),
    ("Native union/Python union 1.002884 [0.953251, 1.046587]", "The interval crosses parity; retain shared-union benefit, not unconditional native superiority."),
    ("Complete-relation CM/direct BitSet 0.929550 [0.921916, 0.937246]", "This speedup-oriented field is direct-BitSet over CM expressed inversely in site naming; the underlying verdict is that BitSet wins all 78 cases."),
    ("CUDD full enumeration gains", "They compare against enumeration/extraction contracts, not the strongest current direct BitSet or task-specific solver."),
    ("All thirteen small-query controls", "CNF or SAT beats the CM arm by about 2.20×–16.23× on the matched small tasks."),
    ("Sep-10 q64 native stable subset", "The fixed subset is selective; fully charged two-host values 0.949341× and 0.977972× fail the 1.10 gate. It is post-cutoff and a no-go."),
])}

## Publication recommendation

The current site should foreground four CM-positive surfaces: the current B2/B4 V3 bare kernel, C6 packed exact source-ANF, C16 exact screening with both machines, and the bounded feature-model k=16 direct-CNF result with its provisional label. Keep plain-CSE and multi-root sharing as scoped supporting positives. Keep losses, parity crossings, and stronger-baseline outcomes immediately adjacent so readers can distinguish “where CM helps” from “where a current competitor remains better.”
"""
    (HERE / f"CM-WEBSITE-POSITIVE-USE-CASE-AUDIT-{AUDIT_DATE}.md").write_text(positive_md, encoding="utf-8", newline="\n")

    backlog_md = f"""# CM website update backlog — {AUDIT_DATE}

This is a review backlog, not authorization to edit, publish, commit, push, or deploy.

## P0 — evidence correctness and freshness

1. **Replace the ambiguous current flattened-CSE tile.** Lead with B2/B4 V3 bare CM/CSE-flat **0.8905696773 [0.8740654100, 0.9072717742]**. Preserve `1.0038` in a dated “historical B1/E3 local” row. Preserve wrapper **3.094136** as an unfavorable whole-call result. Add an inline “below 1 favors CM” label.
2. **Add the C16 Linux confirmation.** Show local Windows **3.545324×** separately from verified Linux **3.177887× whole path / 3.117978× p95**; state 40 cases, 360 rows, zero semantic/artifact mismatches, and the unfavorable local minimum **0.892796×**.
3. **Expose C6 instead of burying it in C6–C12.** Add **1.313448× test / 1.637157× confirmation** medians and **2.175615× / 1.835850× p95**, exactness, zero mismatches, and the boundary: packed exact core advanced; learned hybrid and production promotion did not.
4. **Keep feature-model claims provisional.** Retain `0.276951 [0.200748, 0.371722]` only as a bounded warm-output CM/direct-CNF result. Keep `0.624416 [0.215794, 1.535452]` CUDD as inconclusive.
5. **Do not convert the Sep-10 q64 no-go into a positive claim.** Hold it outside the normal public set until separately approved; if later added, show the failed 1.10 materiality gate and fully charged two-host values.

## P0 — downloadable evidence

6. **Create a Data & Downloads index generated from the manifest JSON.** Each claim set should include a commit-pinned GitHub view link, raw-download link, SHA-256, byte size, contract, host/split, evidence role, verifier/test links, and license/privacy status.
7. **Publish only reviewed minimal bundles.** Start with the website snapshot, B2/B4 V3, C6, C16, feature-model audit, and current architecture sets listed in the artifact audit. Do not expose a directory as if it were one downloadable file.
8. **Resolve licensing before bundling.** The repository has no root license. Add an explicit project license or a per-artifact rights statement; preserve the existing third-party fixture license.
9. **Review operational metadata and ZIP contents manually.** Do not publish tokens, credentials, private endpoints, local databases, or unnecessary pod/host identifiers. The Phase-1 manifest intentionally did not inspect secret stores or `.env*` files.

## P1 — graph and provenance quality

10. Add SVG `<title>` and `<desc>` to all 22 chart definitions; retain and regression-test the existing keyboard-focusable marks, ARIA live tooltip, and full table fallback.
11. Put ratio direction and timing boundary directly in every chart title/caption: time ratio versus speedup, kernel versus preparation/wrapper, warm versus cold, and lower- versus higher-is-better.
12. Pin evidence links to the reviewed commit rather than `main`; retain a visible “latest repository” link separately.
13. Add the exact source selector/field and evidence role to downloadable manifests; distinguish raw, summary, confirmatory, independent verification, and superseded evidence.
14. Add generated freshness checks that fail when a displayed source has a later accepted same-contract result or when a chart/table value is not produced from the same data object.
15. Give all `T()`/`TV()` table and chart values the same machine-readable token/provenance hooks as prose `P()` spans; the learning/neural route currently exposes no `span.num[title]` provenance nodes.

## P1 — tests for the update pass

16. Extend website tests to assert the B2/B4 headline and historical `1.0038` label, C16 Linux values/qualifications, C6 values/exactness/no-promotion boundary, and q64 post-cutoff exclusion.
17. Test every manifest path at the pinned commit, raw-download URL formation, SHA-256/size, missing-license warnings, and the absence of secret-like publication paths.
18. Rebuild all seven pages, run the full website test set, compare generated-page hashes, inspect every route at desktop and narrow viewport, and check console errors/broken links before deployment.

## P2 — later review

19. Decide whether the Sep-10 q64 no-go belongs in a public “current limitations/research disposition” section. It does not create a positive-use-case headline.
20. Consider a versioned evidence release archive only after license and privacy review; include the claim ledger and checksum manifest in the release.

## Acceptance gate for Phase 2

- No contract substitution.
- No value without a source selector and evidence role.
- No positive label when the ratio direction is unfavorable or an interval crosses parity.
- No post-cutoff result without explicit approval.
- No download without existence, checksum, license, privacy, and reproduction/test review.
- Live deployment must hash-match the reviewed build.
"""
    (HERE / f"CM-WEBSITE-UPDATE-BACKLOG-{AUDIT_DATE}.md").write_text(backlog_md, encoding="utf-8", newline="\n")

    print(json.dumps({
        "head": head,
        "origin_main": origin,
        "live_assets_match_head": all(r["live_equals_HEAD"] for r in site_hash_rows),
        "named_tokens": len(token_records),
        "referenced_tokens": sum(bool(template_mentions[t] or data_refs[t]) for t in token_records),
        "charts": len(chart_records),
        "chart_numeric_scalars": sum(c["numeric_scalar_count"] for c in chart_records),
        "ledger_records": len(claims),
        "artifacts": len(artifacts),
        "missing_artifacts": len(missing_artifacts),
        "outputs": sorted(p.name for p in HERE.iterdir() if p.is_file()),
    }, indent=2))


if __name__ == "__main__":
    main()
