"""Freeze source-disjoint small-support LogikBench cones for C19 policy fitting."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.blif import parse_blif
from cmbench.recognition.gf2_decomposition import truth_sha256

BASE = ROOT / (
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/continuation-20260829-125214")
CONVERSION = BASE / "w8-logikbench-conversion-v4-001/evidence/run-output/w8-conversion"
CONVERSIONS = CONVERSION / "conversions.json"
ADMISSION = BASE / "W8-LOGIKBENCH-STATIC-ADMISSION.json"
ACQUISITION = BASE / "W8-LOGIKBENCH-ACQUISITION.json"
FINAL_AUDIT = BASE / "W8-LOGIKBENCH-CONVERSION-FINAL-AUDIT.json"
EXPECTED_COMMIT = "891ced851ea4c2f9a46f6ab991eeee199e2fd516"
QUOTAS = {"development": 48, "validation": 24, "confirmation": 24}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def split_for(cluster_id: str) -> str:
    bucket = int(hashlib.sha256(f"c19-source-split/v1:{cluster_id}".encode()).hexdigest()[:8], 16) % 10
    return "development" if bucket < 6 else "validation" if bucket < 8 else "confirmation"


def previous_truth_identities() -> set[tuple[int, str]]:
    result = set()
    c18 = load(ROOT / "docs/recognition/c18_independent_cone_dataset.json")
    result.update((row["n_vars"], row["truth_sha256"]) for row in c18["cases"])
    # C16 hashes alone are width-unambiguous for n>=3 because the byte count is fixed by width.
    c16 = load(ROOT / "docs/recognition/c16_linux_confirmation/c16_dataset.json")
    from cm_expr_serde import expr_from_json
    from cmbench.recognition.portfolio import reference_bits
    for row in c16["cases"]:
        bits = reference_bits(expr_from_json(row["expression_v2"]), row["n_vars"])
        result.add((row["n_vars"], truth_sha256(bits, row["n_vars"])))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze C19 LogikBench small-support cones")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/recognition/c19_logikbench_small_cone_dataset.json")
    parser.add_argument("--inventory", type=Path,
                        default=ROOT / "docs/recognition/c19_logikbench_small_cone_inventory.json")
    parser.add_argument("--per-cluster", type=int, default=6)
    args = parser.parse_args()
    if not 1 <= args.per_cluster <= 8:
        raise ValueError("invalid C19 per-cluster cap")
    conversions, admission, acquisition, audit = (
        load(CONVERSIONS), load(ADMISSION), load(ACQUISITION), load(FINAL_AUDIT))
    if (conversions.get("converted") != 64 or conversions.get("rejected") != 6
            or admission.get("source_commit") != EXPECTED_COMMIT
            or acquisition.get("commit") != EXPECTED_COMMIT
            or audit.get("verified") is not True
            or audit["fixtures"].get("semantic_equivalence") is not True
            or audit["conversion"].get("converted") != 64
            or audit.get("source_unchanged") is not True):
        raise ValueError("C19 frozen LogikBench conversion evidence incomplete")
    admitted = {row["cluster_id"]: row for row in admission["clusters"]}
    prior = previous_truth_identities()
    inventory_rows, pools = [], {split: [] for split in QUOTAS}
    for row in sorted((item for item in conversions["rows"] if item["status"] == "converted"),
                      key=lambda item: item["cluster_id"]):
        cluster_id = row["cluster_id"]
        path = CONVERSION / "converted" / f"{cluster_id}.blif"
        if sha(path) != row["sha256"] or row["source_set_sha256"] != admitted[cluster_id]["source_set_sha256"]:
            raise ValueError("C19 converted BLIF or RTL source identity mismatch")
        split = split_for(cluster_id)
        base_inventory = {
            "cluster_id": cluster_id, "group": row["group"], "name": row["name"],
            "split": split, "blif_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "blif_bytes": path.stat().st_size, "blif_sha256": row["sha256"],
            "source_set_sha256": row["source_set_sha256"],
        }
        try:
            netlist = parse_blif(path)
            candidates = netlist.candidate_metadata(min_support=3, max_support=6,
                                                     max_source_nodes=128)
        except ValueError as exc:
            inventory_rows.append({**base_inventory, "parser_status": "rejected",
                                   "reason": str(exc)[:240], "eligible_small_cones": 0})
            continue
        inventory_rows.append({
            **base_inventory, "parser_status": "admitted",
            "eligible_small_cones": len(candidates),
        })
        ranked = sorted(candidates, key=lambda item: hashlib.sha256(
            f"c19-cone/v1:{cluster_id}:{item.node}".encode()).hexdigest())[:args.per_cluster]
        for item in ranked:
            bits, support = netlist.packed_value(item.node)
            digest = truth_sha256(bits, len(support))
            stable = hashlib.sha256(f"c19-case/v1:{cluster_id}:{item.node}".encode()).hexdigest()
            pools[split].append((stable, {
                "case_id": f"c19-{cluster_id.removeprefix('logikbench-')}-{stable[:16]}",
                "split": split, "cluster_id": cluster_id, "group": row["group"],
                "source_kind": "logikbench_yosys_blif_cone",
                "blif_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "blif_sha256": row["sha256"], "source_set_sha256": row["source_set_sha256"],
                "rtl_paths": admitted[cluster_id]["rtl_paths"],
                "rtl_sha256": admitted[cluster_id]["rtl_sha256"],
                "license_ids": admitted[cluster_id]["license_ids"],
                "license_paths": admitted[cluster_id]["license_paths"],
                "root_node": item.node, "n_vars": len(support), "support": list(support),
                "source_nodes": item.source_nodes, "source_edges": item.source_edges,
                "depth": item.depth, "local_fanin": item.local_fanin,
                "local_cubes": item.local_cubes, "local_literals": item.local_literals,
                "truth_bits_hex": format(bits, "x"), "truth_sha256": digest,
                "prior_truth_overlap": (len(support), digest) in prior,
                "training_use": split == "development",
                "threshold_selection_use": split == "validation",
                "sealed_confirmation": split == "confirmation",
            }))
    cases, seen = [], set(prior)
    excluded_overlap = excluded_duplicate = 0
    for split, quota in QUOTAS.items():
        accepted = 0
        for _stable, case in sorted(pools[split]):
            identity = (case["n_vars"], case["truth_sha256"])
            if identity in prior:
                excluded_overlap += 1
                continue
            if identity in seen:
                excluded_duplicate += 1
                continue
            seen.add(identity)
            cases.append(case)
            accepted += 1
            if accepted == quota:
                break
        if accepted != quota:
            raise RuntimeError(f"C19 {split} supplied {accepted}/{quota} unique cases")
    cases.sort(key=lambda row: (row["split"], row["case_id"]))
    inventory = {
        "schema": "crse-c19-logikbench-small-cone-inventory/v1", "status": "frozen",
        "conversion": {"path": str(CONVERSIONS.relative_to(ROOT)).replace("\\", "/"),
                       "sha256": sha(CONVERSIONS), "converted": 64, "rejected": 6,
                       "yosys": "Yosys 0.23 (git sha1 7ce5011c24b)",
                       "command_contract": "read_verilog -sv; hierarchy; proc/opt/memory/fsm; techmap; abc -g AND; write_blif -noalias",
                       "performance_measurement": False},
        "admission": {"path": str(ADMISSION.relative_to(ROOT)).replace("\\", "/"),
                      "sha256": sha(ADMISSION), "commit": EXPECTED_COMMIT},
        "acquisition_sha256": sha(ACQUISITION), "final_audit_sha256": sha(FINAL_AUDIT),
        "fixture_semantic_equivalence": True, "source_unchanged": True,
        "files": inventory_rows, "network_used": False, "new_synthesis_run": False,
    }
    dataset = {
        "schema": "crse-c19-logikbench-small-cone-dataset/v1", "status": "frozen",
        "cases": cases,
        "provenance": {"source_family": "LogikBench RTL via frozen Yosys 0.23 BLIF conversion",
                       "upstream_commit": EXPECTED_COMMIT,
                       "inventory": str(args.inventory.relative_to(ROOT)).replace("\\", "/"),
                       "split_contract": "cluster-sha256 60/20/20 before cone timing/v1",
                       "selection_contract": f"support 3..6; <=128 source nodes; max {args.per_cluster} stable-hash cones/cluster/v1",
                       "confirmation_policy_refit_allowed": False},
        "counts": {"cases": len(cases), "by_split": {split: sum(row["split"] == split for row in cases) for split in QUOTAS},
                   "clusters_by_split": {split: len({row["cluster_id"] for row in cases if row["split"] == split}) for split in QUOTAS},
                   "support_histogram": {str(n): sum(row["n_vars"] == n for row in cases) for n in range(3, 7)},
                   "prior_overlaps_excluded": excluded_overlap,
                   "within_c19_duplicates_excluded": excluded_duplicate},
    }
    write(args.inventory, inventory)
    write(args.output, dataset)
    print(json.dumps(dataset["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
