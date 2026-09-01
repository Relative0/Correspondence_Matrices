"""Freeze a bounded source-independent VTR BLIF cone corpus for C18."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.blif import parse_blif
from cmbench.recognition.gf2_decomposition import truth_sha256
from cmbench.recognition.portfolio import reference_bits

SCHEMA = "crse-c18-independent-vtr-cone-dataset/v1"
EXPECTED_VTR_COMMIT = "d1591805ea0e2c52dd38b7775b1cb8845cfd1131"
EXPECTED_LOGIKBENCH_COMMIT = "891ced851ea4c2f9a46f6ab991eeee199e2fd516"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head(path: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, check=True,
                          text=True, capture_output=True).stdout.strip()


def write(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def c16_truth_hashes(path: Path) -> set[str]:
    source = json.loads(path.read_text(encoding="utf-8"))
    result = set()
    for case in source["cases"]:
        bits = reference_bits(expr_from_json(case["expression_v2"]), case["n_vars"])
        result.add(truth_sha256(bits, case["n_vars"]))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze C18 independent VTR BLIF cones")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/recognition/c18_independent_cone_dataset.json")
    parser.add_argument("--inventory", type=Path,
                        default=ROOT / "docs/recognition/c18_independent_corpus_source_inventory.json")
    parser.add_argument("--target", type=int, default=80)
    parser.add_argument("--per-circuit", type=int, default=4)
    args = parser.parse_args()
    if not 40 <= args.target <= 160 or not 1 <= args.per_circuit <= 8:
        raise ValueError("invalid C18 freeze bounds")
    vtr = ROOT / "external/vtr-confirmation-20260830"
    logikbench = ROOT / "external/logikbench-confirmation-20260830"
    vtr_commit, logikbench_commit = git_head(vtr), git_head(logikbench)
    if vtr_commit != EXPECTED_VTR_COMMIT or logikbench_commit != EXPECTED_LOGIKBENCH_COMMIT:
        raise ValueError("C18 local source checkout changed")
    blif_root = vtr / "vtr_flow/benchmarks/blif"
    files = sorted(blif_root.glob("*.blif"), key=lambda path: path.name.lower())
    c16_hashes = c16_truth_hashes(
        ROOT / "docs/recognition/c16_linux_confirmation/c16_dataset.json")
    inventory_rows = []
    candidates = []
    for path in files:
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        row = {"path": rel, "bytes": path.stat().st_size, "source_sha256": sha(path)}
        try:
            netlist = parse_blif(path)
            metadata = netlist.candidate_metadata(min_support=3, max_support=10,
                                                  max_source_nodes=256)
            row.update({"parse_status": "admitted", "model": netlist.model,
                        "inputs": len(netlist.inputs), "outputs": len(netlist.outputs),
                        "nodes": len(netlist.nodes), "eligible_cones": len(metadata)})
            for item in metadata:
                stable = hashlib.sha256(f"c18/v1:{rel}:{item.node}".encode()).hexdigest()
                candidates.append((stable, path, row["source_sha256"], item))
        except (ValueError, OSError) as exc:
            row.update({"parse_status": "rejected", "reason_type": type(exc).__name__,
                        "reason": str(exc)[:240], "eligible_cones": 0})
        inventory_rows.append(row)

    by_file: dict[Path, list[tuple]] = {}
    for candidate in candidates:
        by_file.setdefault(candidate[1], []).append(candidate)
    pool = []
    for path in sorted(by_file, key=lambda value: value.name.lower()):
        pool.extend(sorted(by_file[path])[:args.per_circuit])
    # A second stable sort prevents circuit ordering from biasing support/kind distribution.
    pool.sort(key=lambda row: row[0])
    cases, seen_truth = [], set()
    parsed = {}
    overlap_excluded = duplicate_excluded = 0
    for stable, path, source_sha, item in pool:
        netlist = parsed.setdefault(path, parse_blif(path))
        bits, support = netlist.packed_value(item.node)
        digest = truth_sha256(bits, len(support))
        if digest in c16_hashes:
            overlap_excluded += 1
            continue
        if (len(support), digest) in seen_truth:
            duplicate_excluded += 1
            continue
        seen_truth.add((len(support), digest))
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        case_id = f"vtr-{path.stem}-{stable[:16]}"
        cases.append({
            "case_id": case_id, "split": "independent_evaluation",
            "source_kind": "vtr_blif_cone", "source_file": rel,
            "source_sha256": source_sha, "root_node": item.node,
            "n_vars": len(support), "support": list(support),
            "source_nodes": item.source_nodes, "source_edges": item.source_edges,
            "depth": item.depth, "local_fanin": item.local_fanin,
            "local_cubes": item.local_cubes, "local_literals": item.local_literals,
            "truth_bits_hex": format(bits, "x"), "truth_sha256": digest,
            "c16_truth_overlap": False, "training_use": False,
        })
        if len(cases) == args.target:
            break
    if len(cases) < 40:
        raise RuntimeError(f"only {len(cases)} independent C18 cases survived freeze")

    inventory = {
        "schema": "crse-c18-independent-source-inventory/v1", "status": "frozen",
        "vtr": {"upstream": "verilog-to-routing/vtr-verilog-to-routing",
                "commit": vtr_commit, "license": "MIT with documented bundled exceptions",
                "license_path": "external/vtr-confirmation-20260830/LICENSE.md",
                "license_sha256": sha(vtr / "LICENSE.md"), "blif_files": len(files),
                "files": inventory_rows},
        "logikbench_phase2": {
            "upstream": "jpsety/logikbench", "commit": logikbench_commit,
            "license": "MIT at repository level; per-benchmark licenses retained",
            "license_path": "external/logikbench-confirmation-20260830/LICENSE",
            "license_sha256": sha(logikbench / "LICENSE"),
            "status": "inventoried_not_synthesized",
            "reason": "C18 phase 1 uses already materialized VTR BLIF; RTL synthesis is a separate frozen transform",
        },
        "network_used": False, "downloads": 0,
    }
    dataset = {
        "schema": SCHEMA, "status": "frozen", "cases": cases,
        "provenance": {"source_family": "VTR BLIF benchmarks", "upstream_commit": vtr_commit,
                       "source_inventory": str(args.inventory.relative_to(ROOT)).replace("\\", "/"),
                       "independent_of_c16_generator_family": True,
                       "selection_contract": f"stable sha256 order; max {args.per_circuit} cones/circuit; support 3..10; <=256 source nodes/v1",
                       "training_use": False, "policy_refit_allowed": False},
        "counts": {"cases": len(cases), "source_files_used": len({row["source_file"] for row in cases}),
                   "candidate_cones": len(candidates), "pool_after_per_circuit_cap": len(pool),
                   "c16_truth_overlaps_excluded": overlap_excluded,
                   "within_c18_truth_duplicates_excluded": duplicate_excluded,
                   "support_histogram": {str(n): sum(row["n_vars"] == n for row in cases)
                                         for n in range(3, 11)}},
        "c16_reference": {"path": "docs/recognition/c16_linux_confirmation/c16_dataset.json",
                          "truth_hashes": len(c16_hashes)},
    }
    write(args.inventory, inventory)
    write(args.output, dataset)
    print(json.dumps(dataset["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
