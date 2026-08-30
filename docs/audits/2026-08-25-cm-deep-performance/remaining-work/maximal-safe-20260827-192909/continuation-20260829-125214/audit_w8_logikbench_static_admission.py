"""Apply the frozen W8 static admission rules without importing corpus code."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "external/logikbench-confirmation-20260830"
ACQUISITION = HERE / "W8-LOGIKBENCH-ACQUISITION.json"
PARENT_FREEZE = ROOT / "docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json"
OUTPUT = HERE / "W8-LOGIKBENCH-STATIC-ADMISSION.json"
RTL_SUFFIXES = frozenset({".v", ".sv", ".vh", ".svh"})
SEQUENTIAL = re.compile(r"\b(?:always_ff|always_latch|posedge|negedge)\b")
INITIAL = re.compile(r"\binitial\b")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def license_id(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if "Apache License" in text and "Version 2.0" in text:
        return "Apache-2.0"
    if "ISC License" in text or "Permission to use, copy, modify, and/or distribute" in text:
        return "ISC"
    if "Redistribution and use in source and binary forms" in text:
        return "BSD-3-Clause"
    if "Permission is hereby granted, free of charge" in text:
        return "MIT"
    raise ValueError("unrecognized license text: " + path.as_posix())


def main() -> int:
    acquisition = json.loads(ACQUISITION.read_text(encoding="utf-8"))
    parent = json.loads(PARENT_FREEZE.read_text(encoding="utf-8"))
    if (
        acquisition.get("commit") != "891ced851ea4c2f9a46f6ab991eeee199e2fd516"
        or acquisition.get("clean") is not True
        or acquisition.get("repository_code_executed") is not False
        or acquisition.get("cluster_count") != 140
        or parent.get("timing_results_inspected") is not False
    ):
        raise RuntimeError("static-admission prerequisite changed")

    existing_source_hashes = {
        case["source"]["sha256"] for case in parent["cases"]
        if case.get("source", {}).get("sha256")
    }
    root_license = license_id(SOURCE / "LICENSE")
    if root_license != "MIT":
        raise RuntimeError("repository license changed")

    rows = []
    for cluster in acquisition["clusters"]:
        directory = SOURCE / "logikbench/benchmarks" / cluster["group"] / cluster["name"]
        rtl_paths = [SOURCE / name for name in cluster["rtl_paths"]]
        if not rtl_paths or any(not path.is_file() for path in rtl_paths):
            raise RuntimeError("recorded RTL source is absent")
        rtl_hashes = [sha256(path) for path in rtl_paths]
        text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in rtl_paths)
        sequential_markers = sorted(set(SEQUENTIAL.findall(text)))
        initial_present = INITIAL.search(text) is not None
        metadata = directory / f"{cluster['name']}.py"
        local_licenses = [SOURCE / name for name in cluster["local_license_paths"]]
        licenses = [license_id(path) for path in local_licenses] or [root_license]
        overlap = sorted(set(rtl_hashes) & existing_source_hashes)
        reasons = []
        if not metadata.is_file():
            reasons.append("missing_static_design_metadata")
        if sequential_markers:
            reasons.append("static_sequential_marker")
        if initial_present:
            reasons.append("initial_block")
        if cluster["ai_provenance_present"]:
            reasons.append("ai_origin_reserved_from_primary_confirmation")
        if overlap:
            reasons.append("source_hash_overlaps_existing_freeze")
        row = {
            "cluster_id": cluster["cluster_id"],
            "group": cluster["group"],
            "name": cluster["name"],
            "tree_sha256": cluster["tree_sha256"],
            "rtl_paths": cluster["rtl_paths"],
            "rtl_sha256": rtl_hashes,
            "source_set_sha256": hashlib.sha256("\n".join(
                f"{path.relative_to(directory).as_posix()}\0{digest}"
                for path, digest in zip(rtl_paths, rtl_hashes)
            ).encode("utf-8")).hexdigest(),
            "metadata_path": metadata.relative_to(SOURCE).as_posix() if metadata.is_file() else None,
            "license_ids": licenses,
            "license_paths": cluster["local_license_paths"] or ["LICENSE"],
            "ai_provenance_present": cluster["ai_provenance_present"],
            "sequential_markers": sequential_markers,
            "initial_present": initial_present,
            "existing_freeze_hash_overlap": overlap,
            "static_admitted": not reasons,
            "static_exclusion_reasons": reasons,
        }
        row["selection_key"] = hashlib.sha256(
            ("cm-w8-logikbench-static-v1\0" + row["cluster_id"] + "\0" + row["source_set_sha256"])
            .encode("utf-8")
        ).hexdigest()
        rows.append(row)

    admitted = sorted((row for row in rows if row["static_admitted"]),
                      key=lambda row: (row["selection_key"], row["cluster_id"]))
    excluded = [row for row in rows if not row["static_admitted"]]
    report = {
        "schema": "cm-comparative-w8-logikbench-static-admission/v1",
        "source_commit": acquisition["commit"],
        "acquisition_sha256": sha256(ACQUISITION),
        "parent_freeze_sha256": parent["freeze_sha256"],
        "comparative_timing_inspected": False,
        "corpus_code_executed": False,
        "selection_uses_only_static_source_license_and_provenance": True,
        "admission_rules": {
            "one_cluster_per_benchmark_directory": True,
            "recognized_permissive_license_required": True,
            "existing_source_hash_overlap_forbidden": True,
            "static_sequential_markers_forbidden": ["always_ff", "always_latch", "posedge", "negedge"],
            "initial_blocks_forbidden": True,
            "ai_origin_reserved_from_primary_confirmation": True,
            "final_yosys_and_cone_admission_still_required": True,
        },
        "clusters": rows,
        "cluster_count": len(rows),
        "static_admitted_cluster_ids_in_frozen_order": [row["cluster_id"] for row in admitted],
        "static_admitted_count": len(admitted),
        "static_admitted_by_group": {
            group: sum(row["group"] == group for row in admitted)
            for group in ("basic", "arithmetic", "blocks")
        },
        "static_excluded_count": len(excluded),
        "static_exclusion_counts": {
            reason: sum(reason in row["static_exclusion_reasons"] for row in excluded)
            for reason in sorted({reason for row in excluded for reason in row["static_exclusion_reasons"]})
        },
        "ready_for_yosys_conversion_scout": len(admitted) >= 30,
    }
    if (
        len(rows) != 140
        or len(admitted) < 30
        or any(row["existing_freeze_hash_overlap"] for row in rows)
        or not report["ready_for_yosys_conversion_scout"]
    ):
        raise RuntimeError(
            "static W8 corpus is not ready for conversion: "
            f"rows={len(rows)} admitted={len(admitted)} "
            f"overlaps={sum(bool(row['existing_freeze_hash_overlap']) for row in rows)}"
        )

    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, OUTPUT)
    print(json.dumps({
        "clusters": report["cluster_count"],
        "admitted": report["static_admitted_count"],
        "admitted_by_group": report["static_admitted_by_group"],
        "excluded": report["static_excluded_count"],
        "exclusion_counts": report["static_exclusion_counts"],
        "ready": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
