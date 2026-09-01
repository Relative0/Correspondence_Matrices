"""Replay every frozen C18 VTR cone from its original local BLIF source."""
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


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the frozen C18 independent corpus")
    parser.add_argument("--dataset", type=Path,
                        default=ROOT / "docs/recognition/c18_independent_cone_dataset.json")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/recognition/c18_independent_corpus_verification.json")
    args = parser.parse_args()
    dataset = load(args.dataset)
    inventory = load(ROOT / dataset["provenance"]["source_inventory"])
    head = subprocess.run(["git", "rev-parse", "HEAD"],
                          cwd=ROOT / "external/vtr-confirmation-20260830", check=True,
                          capture_output=True, text=True).stdout.strip()
    if head != inventory["vtr"]["commit"] or len(dataset["cases"]) < 40:
        raise ValueError("C18 source commit or case bound mismatch")
    c16 = load(ROOT / dataset["c16_reference"]["path"])
    c16_hashes = set()
    for case in c16["cases"]:
        bits = reference_bits(expr_from_json(case["expression_v2"]), case["n_vars"])
        c16_hashes.add(truth_sha256(bits, case["n_vars"]))

    netlists = {}
    identities = set()
    for case in dataset["cases"]:
        path = ROOT / case["source_file"]
        if (hashlib.sha256(path.read_bytes()).hexdigest() != case["source_sha256"]
                or case["case_id"] in identities or case["training_use"] is not False):
            raise ValueError("C18 source fingerprint, identity, or training flag mismatch")
        identities.add(case["case_id"])
        netlist = netlists.setdefault(path, parse_blif(path))
        bits, support = netlist.packed_value(case["root_node"])
        metadata = netlist.metadata(case["root_node"])
        if (list(support) != case["support"] or len(support) != case["n_vars"]
                or format(bits, "x") != case["truth_bits_hex"]
                or truth_sha256(bits, len(support)) != case["truth_sha256"]
                or case["truth_sha256"] in c16_hashes
                or metadata.source_nodes != case["source_nodes"]
                or metadata.source_edges != case["source_edges"]
                or metadata.depth != case["depth"]):
            raise ValueError("C18 exact cone replay or overlap check failed")
    verification = {
        "schema": "crse-c18-independent-vtr-cone-verification/v1", "status": "verified",
        "cases_replayed": len(dataset["cases"]), "source_files_replayed": len(netlists),
        "source_fingerprint_mismatches": 0, "truth_vector_mismatches": 0,
        "metadata_mismatches": 0, "c16_truth_overlaps": 0,
        "training_use": False, "policy_refit_allowed": False,
        "network_used": False,
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
