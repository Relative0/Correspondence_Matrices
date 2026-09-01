"""Freeze canonical expression inputs for the C21 task-matched GF(2) table."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_to_json_dag
from cmbench.comparative.contracts import canonical_bytes
from cmbench.recognition.blif import parse_blif
from cmbench.recognition.portfolio import reference_bits

SOURCE = ROOT / "docs/recognition/c19_logikbench_small_cone_dataset.json"
SOURCE_VERIFY = ROOT / "docs/recognition/c19_logikbench_small_cone_verification.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze C21 decomposition-table expression inputs")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/recognition/c21_decomposition_table_dataset.json")
    args = parser.parse_args()
    source, verification = load(SOURCE), load(SOURCE_VERIFY)
    if (
        source.get("status") != "frozen"
        or len(source.get("cases", [])) != 96
        or verification.get("status") != "verified"
        or verification.get("cases_replayed") != 96
        or verification.get("split_cluster_overlap") != 0
        or verification.get("truth_or_metadata_mismatches") != 0
    ):
        raise ValueError("C21 requires the verified frozen C19 source corpus")
    netlists = {}
    cases = []
    for case in source["cases"]:
        path = ROOT / case["blif_path"]
        if sha256(path) != case["blif_sha256"]:
            raise ValueError("C21 source BLIF fingerprint mismatch")
        netlist = netlists.setdefault(case["blif_path"], parse_blif(path))
        expression, support = netlist.build_expr(case["root_node"], max_identity_nodes=4096)
        document = expr_to_json_dag(expression)
        bits = reference_bits(expression, case["n_vars"])
        if tuple(support) != tuple(case["support"]) or bits != int(case["truth_bits_hex"], 16):
            raise ValueError("C21 expression/source truth replay mismatch")
        cases.append({
            **case,
            "expression_v2": document,
            "expression_v2_sha256": hashlib.sha256(canonical_bytes(document)).hexdigest(),
            "c21_training_use": False,
            "c21_policy_selection_use": False,
            "c21_benchmark_only": True,
        })
    result = {
        "schema": "crse-c21-task-matched-gf2-dataset/v1",
        "status": "frozen",
        "cases": cases,
        "counts": {
            "cases": len(cases),
            "source_files": len({case["blif_path"] for case in cases}),
            "source_clusters": len({case["cluster_id"] for case in cases}),
            "by_original_split": {
                split: sum(case["split"] == split for case in cases)
                for split in ("development", "validation", "confirmation")
            },
            "by_n_vars": {
                str(n_vars): sum(case["n_vars"] == n_vars for case in cases)
                for n_vars in range(3, 7)
            },
        },
        "provenance": {
            "source_dataset": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
            "source_dataset_sha256": sha256(SOURCE),
            "source_verification": str(SOURCE_VERIFY.relative_to(ROOT)).replace("\\", "/"),
            "source_verification_sha256": sha256(SOURCE_VERIFY),
            "derivation": "reparse frozen BLIF root; build canonical expression DAG; replay packed truth/v1",
            "timing_based_selection": False,
            "fresh_confirmation": False,
            "production_promotion": False,
        },
    }
    write(args.output, result)
    print(json.dumps(result["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
