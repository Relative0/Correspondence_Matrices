"""Replay the frozen C19 small-support dataset from converted BLIF and RTL hashes."""
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


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify C19 LogikBench small cones")
    parser.add_argument("--dataset", type=Path,
                        default=ROOT / "docs/recognition/c19_logikbench_small_cone_dataset.json")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/recognition/c19_logikbench_small_cone_verification.json")
    args = parser.parse_args()
    dataset = load(args.dataset)
    inventory = load(ROOT / dataset["provenance"]["inventory"])
    if (dataset["counts"]["by_split"] != {"development": 48, "validation": 24, "confirmation": 24}
            or inventory.get("fixture_semantic_equivalence") is not True
            or inventory.get("source_unchanged") is not True
            or inventory.get("new_synthesis_run") is not False):
        raise ValueError("C19 freeze prerequisites changed")
    netlists, identities, clusters = {}, set(), {"development": set(), "validation": set(), "confirmation": set()}
    for case in dataset["cases"]:
        path = ROOT / case["blif_path"]
        if sha(path) != case["blif_sha256"]:
            raise ValueError("C19 BLIF fingerprint mismatch")
        for rel, digest in zip(case["rtl_paths"], case["rtl_sha256"]):
            rtl = ROOT / "external/logikbench-confirmation-20260830" / rel
            if sha(rtl) != digest:
                raise ValueError("C19 RTL fingerprint mismatch")
        identity = (case["n_vars"], case["truth_sha256"])
        if identity in identities or case["prior_truth_overlap"] is not False:
            raise ValueError("C19 duplicate or prior-overlap identity")
        identities.add(identity)
        clusters[case["split"]].add(case["cluster_id"])
        netlist = netlists.setdefault(path, parse_blif(path))
        bits, support = netlist.packed_value(case["root_node"])
        metadata = netlist.metadata(case["root_node"])
        if (format(bits, "x") != case["truth_bits_hex"]
                or truth_sha256(bits, len(support)) != case["truth_sha256"]
                or list(support) != case["support"] or len(support) != case["n_vars"]
                or metadata.source_nodes != case["source_nodes"]
                or metadata.source_edges != case["source_edges"]
                or metadata.depth != case["depth"]
                or case["training_use"] != (case["split"] == "development")
                or case["threshold_selection_use"] != (case["split"] == "validation")
                or case["sealed_confirmation"] != (case["split"] == "confirmation")):
            raise ValueError("C19 exact replay, metadata, or split-use mismatch")
    if any(clusters[a] & clusters[b] for a, b in (("development", "validation"),
                                                   ("development", "confirmation"),
                                                   ("validation", "confirmation"))):
        raise ValueError("C19 cluster split leakage")
    result = {
        "schema": "crse-c19-logikbench-small-cone-verification/v1", "status": "verified",
        "cases_replayed": len(dataset["cases"]), "blif_files_replayed": len(netlists),
        "clusters_by_split": {key: len(value) for key, value in clusters.items()},
        "truth_or_metadata_mismatches": 0, "rtl_or_blif_fingerprint_mismatches": 0,
        "prior_truth_overlaps": 0, "split_cluster_overlap": 0,
        "confirmation_policy_refit_allowed": False, "network_used": False,
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
