"""Record measurement/independence boundaries without retiming live code."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import random
import statistics
from pathlib import Path

from artifact_audit import (
    BASE, CORE, DELTA, SUPPLEMENT, csv_rows, finalize, read_json, require,
    sha, snapshot, verify_run, write_csv, write_json,
)

ARTIFACT_AUDIT = BASE / "runs/configuration-fm-deep-artifact-audit-2026-08-27"

GAPS = [
    ("M01", "high", "Cold construction is incomplete", "cm_feature_model_representation_battery.py", "run_case",
     "cm_compile_ns stops before get_flat_program and first binding/word-plan/scratch creation. CNF masks are warmed before timed sessions. Source conditioning and source witness solving are outside this cell.",
     "Keep warm output timings labeled warm. Rerun explicit parse/condition/compile/lower/bind/materialize/end-to-end cells on a frozen checkout."),
    ("M02", "high", "Version-delta extraction has asymmetric first-touch work", "cm_feature_model_version_delta.py", "cm_pair",
     "CM extraction includes get_flat_program and first word execution; CUDD extraction begins with constructed roots. Rounds repeatedly create fresh CM nodes. These are not comparable warm kernels.",
     "Do not rank warm CM versus CUDD from these ratios. Separate lowering, first execution, warmed execution, and equal-output end-to-end totals."),
    ("M03", "high", "Cold external d4 count is divided by warm popcount", "cm_feature_model_shootout_supplement.py", "run_supplement",
     "d4_count_over_packed_count_geomean divides cold child-process wall time by an already-materialized vector's one-shot bit_count. Process startup, parsing, solving and warm lookup are different tasks.",
     "Withdraw this ratio as a representation speedup. Show cold d4, warm CUDD count and warm vector count in separate cells; charge vector creation for cold counting."),
    ("M04", "high", "Historical CM reload checked cached output, not executable reuse", "cm_feature_model_representation_battery.py", "serialize_case",
     "The original CM roundtrip reads packed_hex, and reload time is JSON parsing. CUDD manager creation is outside its reload timer. Neither historical timing is a complete load-and-first-use comparison.",
     "Independent instruction replay now closes artifact correctness. Historical reload speed rankings still require normalized bundle/load/first-query reruns."),
    ("M05", "high", "Artifact byte and node contracts differ", "cm_feature_model_shootout_supplement.py", "run_supplement",
     "CM JSON includes instructions plus a hex cached vector and pretty-printing. d4's raw file omits the full variable universe. Its printed internal node/edge counters are not serialized graph counts.",
     "Use artifact-contracts.csv and audited serialized graph counts. Compare structure-only and self-describing bundle bytes separately; do not infer intrinsic compactness from raw format ratios."),
    ("M06", "medium", "RSS is sampled whole-process memory for unequal tasks", "cm_feature_model_shootout_supplement.py", "monitored",
     "1 ms polling measures process/import/interpreter/input-mask overhead too; no baseline subtraction or high-water OS metric. Python arms materialize vectors; d4 returns a count. RSS worker timings are not kernel timings.",
     "Label whole-process sampled peak RSS. Future equal-task runs should report baseline, incremental peak, OS high-water mark, repeats and resource/host-load metadata."),
    ("M07", "high", "Fixed-order CUDD was not explicitly made fixed", "cm_feature_model_representation_battery.py", "build_bdd",
     "The runner only creates and declares a BDD manager. Official dd v0.5.7 enables automatic reordering by default. No reordering counter/configuration was saved; reorder() with no order requests group sifting.",
     "Relabel as declared-initial-order CUDD; report audited final orders. A true fixed arm must disable reordering and record configuration/counters. Label the other arm group sifting."),
    ("M08", "high", "Actual sifted artifacts were not preserved", "cm_feature_model_shootout_supplement.py", "sifting_metrics",
     "The producer compares sifted output internally but saves only metrics and an equality flag, not the sifted graph/final order. Independent artifact replay covers saved pre-supplement BDDs, not the exact sifted objects.",
     "Keep native group-sifting correctness producer-checked, not independently replayed. Persist each selected sifted graph/order/configuration in a later run."),
    ("M09", "medium", "Transition fresh-versus-reused and timing protocol incomplete", "cm_feature_model_version_delta.py", "run",
     "The real transition runner has reused CM/shared CUDD builds but no matched fresh later-version arms. CM/CUDD run in fixed sequence; SAT enumeration is one-shot. This differs from the frozen five counterbalanced rounds and fresh-versus-reused protocol.",
     "Do not claim a real-history reuse speedup from cache hits alone. Add matched fresh/shared arms and counterbalanced repeated timings in a separately versioned follow-up protocol."),
    ("M10", "medium", "Transition aggregation does not give histories equal weight", "cm_feature_model_version_delta.py", "run",
     "The pooled geometric means give Linux fewer observations after one refusal. The frozen protocol specified equal-history weighting.",
     "Use clustered-statistics.json for corrected equal-history aggregates, still diagnostic for asymmetric timings. Keep original raw rows and pooled summaries unchanged."),
    ("M11", "high", "Historical dirty implementation state was not pinned", "cm_feature_model_version_delta.py", "current_git_head",
     "Run manifests record HEAD but not hashes/snapshots of dirty implementation files. Current audit snapshots cannot reconstruct the exact code loaded by historical processes. Concurrent tests also preclude assuming a quiet host.",
     "Treat historical timings as provisional. Use immutable source/dependency snapshots and run IDs for future timings; retain this audit's before/after hashes and do not edit the other task's code."),
    ("M12", "medium", "Coverage is local, sparse and largely unchanged", "cm_feature_model_version_delta.py", "choose_names",
     "Slices fix all outside variables, including auxiliaries; they are conditioned neighborhoods, not existential projections. Most sampled version deltas are zero. Random point queries on sparse relations favor invalid decisions.",
     "No whole-model equivalence, global scalability, domain dominance, or natural-session claim. Add held-out histories, multiple contexts, edit-local slices and balanced valid/invalid controls under a frozen selection rule."),
    ("M13", "medium", "Timeouts fail fast instead of retaining per-cell outcomes", "cm_feature_model_shootout_supplement.py", "monitored",
     "The wrapper raises on a timeout or backend failure before final CSV/summary output, rather than retaining a timeout/refusal row for each planned cell.",
     "No timeout occurred in the completed saved run. Future runners should flush case outcomes and retain partial evidence without reporting incomplete cells as passes."),
]


def compact_bytes(value: object) -> int:
    return len(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def audit(output: Path) -> dict:
    require(not output.exists(), f"refusing to overwrite {output}")
    output.mkdir(parents=True)
    observed = snapshot(output)
    runs = [verify_run(run) for run in (CORE, SUPPLEMENT, DELTA, ARTIFACT_AUDIT)]
    write_json(output / "historical-run-identities.json", runs)
    findings = []
    for identifier, severity, title, filename, symbol, evidence, disposition in GAPS:
        path = BASE / filename
        tree = ast.parse(path.read_text(encoding="utf-8"))
        function = next(node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol)
        findings.append({"id": identifier, "severity": severity, "title": title,
                         "observed_source": filename, "observed_source_sha256": sha(path),
                         "symbol": symbol, "start_line": function.lineno, "end_line": function.end_lineno,
                         "evidence": evidence, "disposition": disposition,
                         "historical_exact_source_not_recoverable": True})
    write_json(output / "measurement-gaps.json", findings)
    rows = csv_rows(CORE / "cases.csv")
    supplement = {row["case_id"]: row for row in csv_rows(SUPPLEMENT / "supplement.csv")}
    replay = {row["case_id"]: row for row in csv_rows(ARTIFACT_AUDIT / "artifact-replay.csv")}
    contracts = []
    for row in rows:
        case_id, k = row["case_id"], int(row["k"])
        key = hashlib.sha256(case_id.encode()).hexdigest()[:16]
        directory = CORE / "serialized" / key
        cm_path, bdd_path = directory / "cm-flat-packed.json", directory / "robdd.json"
        cm, bdd = read_json(cm_path), read_json(bdd_path)
        raw_packed = bytes.fromhex(cm["packed_hex"])
        packed = int.from_bytes(raw_packed, "little")
        rng = random.Random(int.from_bytes(hashlib.sha256((case_id + "|point").encode()).digest()[:8], "big"))
        points = list(range(256)) if k == 8 else [rng.randrange(1 << k) for _ in range(256)]
        if k == 8:
            rng.shuffle(points)
        nnf_path = SUPPLEMENT / "ddnnf" / f"{key}.nnf"
        universe_manifest = {"format": "d4-arc-nnf/v1", "k": k, "variable_order": [f"x{i}" for i in range(k)],
                             "assignment_order": "x0-lsb", "payload_sha256": sha(nnf_path)}
        contracts.append({"case_id": case_id, "k": k,
                          "cm_raw_json_bytes": cm_path.stat().st_size,
                          "cm_structure_only_compact_json_bytes": compact_bytes({name: value for name, value in cm.items() if name != "packed_hex"}),
                          "packed_vector_binary_bytes": len(raw_packed),
                          "bdd_raw_json_bytes": bdd_path.stat().st_size,
                          "bdd_compact_json_bytes": compact_bytes(bdd),
                          "ddnnf_raw_bytes": nnf_path.stat().st_size,
                          "ddnnf_minimal_universe_manifest_bytes": compact_bytes(universe_manifest),
                          "ddnnf_raw_plus_universe_bytes": nnf_path.stat().st_size + compact_bytes(universe_manifest),
                          "ddnnf_serialized_nodes": int(replay[case_id]["serialized_nodes"]),
                          "ddnnf_serialized_edges": int(replay[case_id]["serialized_edges"]),
                          "ddnnf_internal_reported_nodes": int(supplement[case_id]["ddnnf_nodes"]),
                          "saved_bdd_final_order_is_declared_order": all(int(level) == int(name[1:]) for name, level in bdd["level_of_var"].items()),
                          "point_queries": len(points), "valid_point_queries": sum(bool((packed >> point) & 1) for point in points)})
    write_csv(output / "artifact-contracts.csv", contracts)
    by_width = {}
    for k in (8, 12, 16):
        selected = [row for row in contracts if row["k"] == k]
        original = [row for row in rows if int(row["k"]) == k]
        native = [row for row in supplement.values() if int(row["k"]) == k]
        by_width[str(k)] = {
            "n": len(selected),
            **{name + "_median": statistics.median(row[name] for row in selected) for name in (
                "cm_raw_json_bytes", "cm_structure_only_compact_json_bytes", "packed_vector_binary_bytes",
                "bdd_raw_json_bytes", "bdd_compact_json_bytes", "ddnnf_raw_bytes", "ddnnf_raw_plus_universe_bytes",
                "ddnnf_serialized_nodes", "ddnnf_serialized_edges")},
            "valid_point_queries": sum(row["valid_point_queries"] for row in selected),
            "point_queries": sum(row["point_queries"] for row in selected),
            "warm_packed_count_ns_median_ONE_SHOT": statistics.median(float(row["packed_count_ns"]) for row in original),
            "warm_cudd_count_ns_median_ONE_SHOT": statistics.median(float(row["robdd_count_ns"]) for row in original),
            "cold_d4_process_count_ns_median": statistics.median(float(row["d4_count_wall_ns_median"]) for row in native),
            "cross_task_count_speedup_allowed": False,
        }
    write_json(output / "measurement-summary.json", by_width)
    summary = {"schema": "cm-fm-measurement-audit/v1", "status": "gaps_documented",
               "gap_count": len(findings), "high_priority_gaps": sum(row["severity"] == "high" for row in findings),
               "artifact_contract_rows": len(contracts),
               "saved_bdd_final_order_identity_cases": sum(row["saved_bdd_final_order_is_declared_order"] for row in contracts),
               "performance_rerun_performed": False, "historical_runs_modified": False,
               "external_primary_sources": [
                   "https://github.com/crillab/d4/blob/333370cc1e843dd0749c1efe88516e72b5239174/README.md",
                   "https://raw.githubusercontent.com/tulip-control/dd/v0.5.7/dd/cudd.pyx",
               ]}
    write_json(output / "summary.json", summary)
    finalize(output, observed, runs)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    audit(arguments.output.resolve())
