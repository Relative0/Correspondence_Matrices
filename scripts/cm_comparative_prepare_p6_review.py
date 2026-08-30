#!/usr/bin/env python3
"""Prepare the deterministic P6 candidate draft from already available sources."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.corpus_freeze import (
    DIMACS_SEMANTIC_COMMENT_DIRECTIVES,
    FREEZE_SCHEMA,
    PRIMARY_METRICS,
    dimacs_metadata,
)
from cmbench.comparative.evidence import publish_json
from cmbench.recognition.blif import parse_blif


SYNTHETIC = Path("deliverables_n22_24/CM_gap_e3_corrected_corpus_2026_08_02.jsonl")
EPFL_ROOT = Path("external/epfl-benchmarks")
D4_ROOT = Path("external/d4v2")
D4_LEGACY_ROOT = Path("external/d4")
PLAN = Path(
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/continuation-20260829-125214/"
    "CM-FAST-VARIANTS-COMPARATIVE-BENCHMARK-PLAN-20260829.md"
)
V20_FINAL = Path(
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/continuation-20260829-125214/"
    "EXTERNAL-NATIVE-GAP-V20-FINAL-VERIFICATION-20260829-170627-870230.json"
)
EPFL_COMMIT = "0060e156826e733d69bf5b3322d1bdd0d03a1f9a"
D4_COMMIT = "15eff31962466804a48374826b9e5a746fc2766e"
D4_LEGACY_COMMIT = "333370cc1e843dd0749c1efe88516e72b5239174"
CONFIRMATION_COUNT = 30


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def member_source(record):
    return {
        "path": SYNTHETIC.as_posix(),
        "member_id": record["id"],
        "member_sha256": hashlib.sha256(canonical_bytes(record)).hexdigest(),
        "license": "project-internal",
        "provenance": "E3 corrected corpus generator e3-corrected-2026-08-02.1; previously inspected",
    }


def synthetic_case(record, role):
    return {
        "case_id": f"{role}-e3-{record['id']}",
        "cluster_id": "e3/" + record["id"],
        "role": role,
        "origin": "synthetic",
        "family": record["op_family"],
        "kind": "expression_jsonl_member",
        "tasks": [
            "ir_preparation", "complete_relation", "exact_count", "sat_status",
            "structural_reload", "feasibility_frontier",
        ],
        "source": member_source(record),
        "strata": {
            "live_k": record["stratum_live_k"],
            "syntactic_support": record["syntactic_support_size"],
            "semantic_support": record["semantic_support_size"],
            "dag_nodes": record["structural_dag_nodes"],
            "depth": record["max_depth"],
            "shape": record["shape"],
            "sharing_ppm": round(record["sharing_factor"] * 1_000_000),
            "operator_mix": sorted(record["operator_mix_structural"]),
            "truth_density_ppm": None,
            "fixed_axes": 0,
            "contexts": 0,
            "versions": 0,
        },
    }


def epfl_cases(project):
    rows = []
    for folder, family in (("arithmetic", "arithmetic"), ("random_control", "control")):
        for path in sorted((project / EPFL_ROOT / folder).glob("*.blif")):
            relative = path.relative_to(project).as_posix()
            rows.append({
                "case_id": "development-epfl-" + path.stem,
                "cluster_id": "epfl/" + path.stem,
                "role": "development",
                "origin": "natural",
                "family": family,
                "kind": "blif",
                "tasks": [
                    "ir_preparation", "complete_relation", "exact_count", "sat_status",
                    "structural_reload", "feasibility_frontier",
                ],
                "source": {
                    "path": relative,
                    "member_id": None,
                    "member_sha256": None,
                    "license": "MIT",
                    "provenance": f"lsils/benchmarks commit {EPFL_COMMIT}; original BLIF",
                },
                "strata": {
                    "live_k": None, "syntactic_support": None, "semantic_support": None,
                    "dag_nodes": None, "depth": None, "shape": "circuit",
                    "sharing_ppm": None, "operator_mix": "unknown-before-translation",
                    "truth_density_ppm": None, "fixed_axes": None, "contexts": 0, "versions": 0,
                },
            })
    return rows


def epfl_output_cases(project):
    """Freeze one deterministic, bounded primary-output cone per eligible circuit."""
    rows = []
    rejected = []
    for folder, family in (("arithmetic", "arithmetic"), ("random_control", "control")):
        for path in sorted((project / EPFL_ROOT / folder).glob("*.blif")):
            netlist = parse_blif(path)
            selected = None
            for output in sorted(netlist.outputs):
                selected = netlist.bounded_metadata(
                    output, min_support=4, max_support=16, max_source_nodes=4096,
                )
                if selected is not None:
                    break
            relative = path.relative_to(project).as_posix()
            if selected is None:
                rejected.append({
                    "path": relative,
                    "reason": "no primary output has support 4..16 and at most 4096 source nodes",
                })
                continue
            root_digest = hashlib.sha256(selected.node.encode("utf-8")).hexdigest()[:12]
            rows.append({
                "case_id": f"development-epfl-{path.stem}-{root_digest}",
                "cluster_id": "epfl/" + path.stem,
                "role": "development",
                "origin": "natural",
                "family": family,
                "kind": "blif",
                "tasks": [
                    "ir_preparation", "complete_relation", "exact_count", "sat_status",
                    "structural_reload", "feasibility_frontier",
                ],
                "source": {
                    "path": relative,
                    "member_id": None,
                    "member_sha256": None,
                    "license": "MIT",
                    "provenance": (
                        f"lsils/benchmarks commit {EPFL_COMMIT}; original BLIF; "
                        "primary output selected bytewise before timing"
                    ),
                },
                "strata": {
                    "live_k": len(selected.support),
                    "syntactic_support": len(selected.support),
                    "semantic_support": None,
                    "dag_nodes": selected.source_nodes,
                    "source_edges": selected.source_edges,
                    "depth": selected.depth,
                    "shape": "circuit-output-cone",
                    "sharing_ppm": None,
                    "operator_mix": "unknown-before-translation",
                    "truth_density_ppm": None,
                    "fixed_axes": 0,
                    "contexts": 0,
                    "versions": 0,
                    "root": selected.node,
                    "support": list(selected.support),
                    "local_fanin": selected.local_fanin,
                    "local_cubes": selected.local_cubes,
                    "local_literals": selected.local_literals,
                    "selection_max_support": 16,
                    "selection_max_source_nodes": 4096,
                },
            })
    return rows, rejected


def cnf_case(project, filename, role):
    path = project / D4_ROOT / "instancesTest/cnfs" / filename
    if not path.is_file():
        raise FileNotFoundError(path)
    return {
        "case_id": f"{role}-d4-{path.stem}",
        "cluster_id": "d4v2/" + path.stem,
        "role": role,
        "origin": "adversarial",
        "family": "model-count-test",
        "kind": "cnf",
        "tasks": ["exact_count", "sat_status", "witness", "feasibility_frontier"],
        "source": {
            "path": path.relative_to(project).as_posix(),
            "member_id": None,
            "member_sha256": None,
            "license": "LGPL-2.1-only",
            "provenance": f"crillab/d4v2 commit {D4_COMMIT}; upstream test instance",
        },
        "strata": {
            "live_k": None, "syntactic_support": None, "semantic_support": None,
            "dag_nodes": None, "depth": None, "shape": "cnf",
            "sharing_ppm": None, "operator_mix": "cnf", "truth_density_ppm": None,
            "fixed_axes": None, "contexts": 0, "versions": 0,
        },
    }


def confirmation_cnfs(project):
    used = {
        "smallSAT.cnf", "smallUNSAT.cnf", "cnf2.cnf", "cnf3.cnf", "cnf4.cnf",
        "erosion2.cnf", "compas-25-1.cnf", "projectedCnf2.cnf", "cnf1.cnf",
        "cnf10.cnf", "cnf20.cnf", "graphCountingTest.cnf", "erosion1.cnf",
        "projectedCnf1.cnf", "minSharpCnf1.cnf", "maxSharpCnf1.cnf",
    }
    used_paths = [project / D4_ROOT / "instancesTest/cnfs" / name for name in sorted(used)]
    used_hashes = {sha256(path) for path in used_paths}
    selected_hashes = set(used_hashes)
    rejected = []

    def eligible_from(root, *, license_id, provenance, limit):
        rows = []
        for path in sorted(root.glob("*.cnf"), key=lambda item: item.name):
            if path.name in used and root == project / D4_ROOT / "instancesTest/cnfs":
                continue
            relative = path.relative_to(project).as_posix()
            try:
                metadata = dimacs_metadata(path)
            except (UnicodeDecodeError, ValueError) as exc:
                rejected.append({"path": relative, "reason": str(exc)})
                continue
            special = sorted(DIMACS_SEMANTIC_COMMENT_DIRECTIVES.intersection(metadata["comment_directives"]))
            if special:
                rejected.append({"path": relative, "reason": "semantic comment directives: " + ",".join(special)})
                continue
            digest = sha256(path)
            if digest in selected_hashes:
                rejected.append({"path": relative, "reason": "byte-identical to an earlier corpus case"})
                continue
            selected_hashes.add(digest)
            rows.append((path, metadata, license_id, provenance))
            if len(rows) == limit:
                break
        if len(rows) != limit:
            raise ValueError(f"confirmation source {root} supplied {len(rows)} of required {limit} cases")
        return rows

    selected = []
    selected.extend(eligible_from(
        project / D4_ROOT / "instancesTest/cnfs",
        license_id="LGPL-2.1-only",
        provenance=f"crillab/d4v2 commit {D4_COMMIT}; unused upstream test instance",
        limit=25,
    ))
    selected.extend(eligible_from(
        project / D4_LEGACY_ROOT / "benchTest",
        license_id="LGPL-3.0-only",
        provenance=f"crillab/d4 commit {D4_LEGACY_COMMIT}; unused upstream test instance",
        limit=3,
    ))
    selected.extend(eligible_from(
        project / D4_ROOT / "3rdParty/bipe/instanceTest",
        license_id="AGPL-3.0-only",
        provenance=f"crillab/bipe subtree at d4v2 commit {D4_COMMIT}; unused upstream test instance",
        limit=2,
    ))
    if len(selected) != CONFIRMATION_COUNT:
        raise ValueError("confirmation selection count mismatch")
    rows = []
    for path, metadata, license_id, provenance in selected:
        namespace = (
            "d4v2" if "instancesTest/cnfs" in path.as_posix()
            else "d4-legacy" if "external/d4/" in path.as_posix()
            else "bipe"
        )
        rows.append({
            "case_id": f"confirmation-{namespace}-{path.stem}",
            "cluster_id": f"{namespace}-confirmation/{path.stem}",
            "role": "confirmation",
            "origin": "adversarial",
            "family": "model-count-test",
            "kind": "cnf",
            "tasks": ["exact_count", "sat_status", "witness", "feasibility_frontier"],
            "source": {
                "path": path.relative_to(project).as_posix(),
                "member_id": None,
                "member_sha256": None,
                "license": license_id,
                "provenance": provenance + "; ordinary DIMACS semantics with comments ignored",
            },
            "strata": {
                "live_k": metadata["variables"],
                "syntactic_support": metadata["variables"],
                "semantic_support": None,
                "dag_nodes": None,
                "depth": None,
                "shape": "cnf",
                "sharing_ppm": None,
                "operator_mix": "cnf",
                "truth_density_ppm": None,
                "fixed_axes": None,
                "contexts": 0,
                "versions": 0,
                "clauses": metadata["clauses"],
                "literal_occurrences": metadata["literal_occurrences"],
                "maximum_clause_width": metadata["maximum_clause_width"],
                "empty_clauses": metadata["empty_clauses"],
                "comment_directives": metadata["comment_directives"],
            },
        })
    return rows, {
        "selection_rule": (
            "exclude the 16 regression/development files and all byte duplicates; strictly parse ordinary p cnf; "
            "reject ind/max/p-show/p-protected/p-weight comment dialects; sort filenames bytewise; select "
            "25 d4v2 main, 3 legacy d4, and 2 bipe cases; ignore remaining c-line comments semantically"
        ),
        "selected_paths": [path.relative_to(project).as_posix() for path, _metadata, _license, _provenance in selected],
        "rejected": rejected,
    }


def policy(policy_id, task, arms, seed, shard_cells):
    cycle = len(arms) * 2
    minimum = cycle if cycle >= 7 else cycle * 2
    return {
        "policy_id": policy_id,
        "task": task,
        "eligible_roles": ["regression", "development"],
        "arms": arms,
        "minimum_blocks": minimum,
        "maximum_blocks": minimum * 2,
        "locality": "round_robin",
        "seed": seed,
        "shard_cells": shard_cells,
        "noise_rule": {
            "metric": "mad_over_median",
            "threshold_ppm": 50_000,
            "step_blocks": cycle,
            "independent_units_first": True,
        },
    }


def prepare(project):
    corpus_path = project / SYNTHETIC
    records = []
    for line in corpus_path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record.get("id"):
            records.append(record)
    groups = {}
    for record in records:
        key = (record["stratum_live_k"], record["op_family"], record["shape"])
        groups.setdefault(key, []).append(record)
    if len(groups) != 24 or any(len(rows) < 2 for rows in groups.values()):
        raise ValueError("E3 corpus no longer provides two members in every expected stratum")
    cases = []
    for key in sorted(groups):
        rows = sorted(groups[key], key=lambda row: row["id"])
        cases.append(synthetic_case(rows[0], "regression"))
        cases.append(synthetic_case(rows[1], "development"))
    cases.extend(epfl_cases(project))
    regression_cnfs = [
        "smallSAT.cnf", "smallUNSAT.cnf", "cnf2.cnf", "cnf3.cnf",
        "cnf4.cnf", "erosion2.cnf", "compas-25-1.cnf", "projectedCnf2.cnf",
    ]
    development_cnfs = [
        "cnf1.cnf", "cnf10.cnf", "cnf20.cnf", "graphCountingTest.cnf",
        "erosion1.cnf", "projectedCnf1.cnf", "minSharpCnf1.cnf", "maxSharpCnf1.cnf",
    ]
    cases.extend(cnf_case(project, name, "regression") for name in regression_cnfs)
    cases.extend(cnf_case(project, name, "development") for name in development_cnfs)
    cases.sort(key=lambda row: (row["role"], row["case_id"]))
    return {
        "schema": FREEZE_SCHEMA,
        "freeze_id": "comparative-p6-candidate-v2-2026-08-30",
        "created_utc": "2026-08-29T17:10:00Z",
        "timing_results_inspected": False,
        "cases": cases,
        "exclusions": [
            {
                "exclusion_id": "source-identity",
                "scope": "all",
                "predicate": "source bytes or SHA-256 differ from freeze",
                "reason": "input identity is not the frozen case",
                "frozen_before_timing": True,
            },
            {
                "exclusion_id": "parse-contract",
                "scope": "all",
                "predicate": "bounded parser cannot produce the declared task input",
                "reason": "requested artifact is undefined for the unparsed source",
                "frozen_before_timing": True,
            },
            {
                "exclusion_id": "semantic-duplicate",
                "scope": "all",
                "predicate": "pre-timing semantic identity duplicates another case in the same cluster",
                "reason": "dependent duplicate remains one cluster and one retained representative",
                "frozen_before_timing": True,
            },
        ],
        "schedule_policies": [
            policy("p7-ir", "ir_preparation", [
                "cm-ir-current", "cm-ir-two-memo", "cm-cse-flat", "cm-raw-flat", "cm-compact-key"
            ], 61001, 250),
            policy("p7-relation", "complete_relation", [
                "cm-dense", "cm-packed-bigint", "cm-packed-words", "cm-no-reinflate",
                "cm-cse-flat", "cm-fast-frozen"
            ], 61003, 240),
            policy("p8-count", "exact_count", [
                "cm-packed-count", "cm-no-reinflate-count", "cudd-count", "d4-count"
            ], 61007, 256),
            policy("p8-sat", "sat_status", ["cm-vector-sat", "cadical195", "cudd-sat"], 61009, 240),
            policy("p8-reload", "structural_reload", ["cm-structural-reload", "cudd-graph-reload"], 61013, 256),
            policy("p7-frontier", "feasibility_frontier", [
                "cm-dense", "cm-packed-bigint", "cm-packed-words", "cm-no-reinflate", "cudd", "d4"
            ], 61019, 240),
        ],
        "primary_metrics": list(PRIMARY_METRICS),
        "secondary_metrics": [
            "construction_ns", "lowering_ns", "query_ns", "extraction_ns", "restoration_ns",
            "artifact_bytes", "page_faults", "cache_hits", "cache_misses", "cache_evictions",
            "instruction_count", "live_buffer_count", "live_support", "crossover_query_count",
        ],
        "confirmation": {
            "required": True,
            "selection_locked": True,
            "timing_results_inspected": False,
            "minimum_independent_clusters": 30,
        },
        "gate_requirements": {
            "minimum_independent_clusters": {"regression": 12, "development": 24, "confirmation": 30},
            "required_tasks": [
                "ir_preparation", "complete_relation", "exact_count", "sat_status",
                "witness", "structural_reload", "feasibility_frontier",
            ],
            "development_origins": ["natural", "synthetic", "adversarial"],
        },
        "provenance": {
            "benchmark_plan_path": PLAN.as_posix(),
            "benchmark_plan_sha256": sha256(project / PLAN),
            "native_readiness_path": V20_FINAL.as_posix(),
            "native_readiness_sha256": sha256(project / V20_FINAL),
            "native_readiness_completed": True,
            "comparative_timing_seen": False,
            "epfl_repository": {"url": "https://github.com/lsils/benchmarks.git", "commit": EPFL_COMMIT},
            "d4_repository": {"url": "https://github.com/crillab/d4v2.git", "commit": D4_COMMIT},
        },
    }


def prepare_v3(project):
    draft = copy.deepcopy(prepare(project))
    confirmation, selection = confirmation_cnfs(project)
    draft["freeze_id"] = "comparative-p6-candidate-v3-2026-08-30"
    draft["created_utc"] = "2026-08-29T17:26:59Z"
    draft["cases"].extend(confirmation)
    draft["cases"].sort(key=lambda row: (row["role"], row["case_id"]))
    for policy_row in draft["schedule_policies"]:
        policy_row["eligible_roles"] = ["regression", "development", "confirmation"]
    draft["provenance"]["confirmation_repository"] = {
        "sources": [
            {
                "url": "https://github.com/crillab/d4v2.git",
                "commit": D4_COMMIT,
                "scope": "instancesTest/cnfs",
                "license": "LGPL-2.1-only",
                "license_sha256": sha256(project / D4_ROOT / "LICENSE"),
            },
            {
                "url": "https://github.com/crillab/d4.git",
                "commit": D4_LEGACY_COMMIT,
                "scope": "benchTest",
                "license": "LGPL-3.0-only",
                "license_sha256": sha256(project / D4_LEGACY_ROOT / "LICENSE"),
            },
            {
                "url": "https://github.com/crillab/bipe.git",
                "commit": "bc9ba957e43327afc1c96ee2663a2c77adebbefb",
                "scope": "instanceTest",
                "license": "AGPL-3.0-only",
                "license_sha256": sha256(project / D4_ROOT / "3rdParty/bipe/LICENSE"),
            },
        ],
        **selection,
        "comparative_timing_seen": False,
    }
    draft["provenance"]["rejected_confirmation_source"] = {
        "url": "https://github.com/verilog-to-routing/vtr-verilog-to-routing.git",
        "commit": "d1591805ea0e2c52dd38b7775b1cb8845cfd1131",
        "reason": "benchmark-specific redistribution terms were not present in the BLIF files",
        "comparative_timing_seen": False,
    }
    return draft


def prepare_v4(project):
    """Supersede V3 with execution-ready BLIF roots and distinct P7 IR arms."""
    draft = copy.deepcopy(prepare_v3(project))
    output_cases, rejected = epfl_output_cases(project)
    draft["freeze_id"] = "comparative-p6-candidate-v4-2026-08-30"
    draft["created_utc"] = "2026-08-30T00:40:00Z"
    draft["cases"] = [
        row for row in draft["cases"]
        if not (row["kind"] == "blif" and row["cluster_id"].startswith("epfl/"))
    ]
    draft["cases"].extend(output_cases)
    draft["cases"].sort(key=lambda row: (row["role"], row["case_id"]))
    for row in draft["schedule_policies"]:
        if row["policy_id"] == "p7-ir":
            row["arms"] = [
                "cm-ir-current", "cm-ir-two-memo", "cm-cse-flat", "cm-raw-flat",
            ]
        elif row["policy_id"] == "p7-relation":
            # The combined arm is frozen only after this development ablation
            # identifies a distinct checked-in configuration.  A second label
            # for the current no-reinflation path would duplicate an arm.
            row["arms"] = [arm for arm in row["arms"] if arm != "cm-fast-frozen"]
        else:
            continue
        cycle = len(row["arms"]) * 2
        row["minimum_blocks"] = cycle
        row["maximum_blocks"] = cycle * 2
        row["noise_rule"]["step_blocks"] = cycle
    draft["exclusions"].append({
        "exclusion_id": "epfl-output-cone-bound",
        "scope": "development",
        "predicate": "no primary output has support 4..16 and at most 4096 source nodes",
        "reason": "complete-relation and scalar-oracle execution would exceed the frozen bounded cone contract",
        "frozen_before_timing": True,
    })
    draft["provenance"]["v4_execution_correction"] = {
        "supersedes": "comparative-p6-candidate-v3-2026-08-30",
        "reason": (
            "V3 did not identify an EPFL output cone and listed cm-compact-key even though "
            "compact interning is already part of cm-ir-current; it also named cm-fast-frozen "
            "before a distinct combined configuration had been frozen"
        ),
        "comparative_timing_seen": False,
    }
    draft["provenance"]["epfl_output_selection"] = {
        "rule": (
            "for each circuit sorted by path, select the first bytewise-sorted primary output "
            "with exact support 4..16 and at most 4096 driven source nodes"
        ),
        "selected": [
            {"path": row["source"]["path"], "root": row["strata"]["root"]}
            for row in output_cases
        ],
        "rejected": rejected,
        "comparative_timing_seen": False,
    }
    return draft


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-version", choices=("v2", "v3", "v4"), default="v2")
    args = parser.parse_args(argv)
    project = args.project_root.resolve()
    draft = (
        prepare_v4(project) if args.candidate_version == "v4"
        else prepare_v3(project) if args.candidate_version == "v3"
        else prepare(project)
    )
    publish_json(args.output.resolve(), draft)
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
