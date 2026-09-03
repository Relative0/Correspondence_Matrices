"""Freeze C36 fresh wide natural functions and output-blind query traces."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_wide_repeated_queries import attach_query_contracts
from cmbench.recognition.yosys_wide_restriction_data import build_dataset


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json")
    args = parser.parse_args()
    inventory = ROOT / "docs/recognition/c23_yosys_fresh_source_inventory.json"
    prior = ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset.json"
    prior_document = json.loads(prior.read_text(encoding="utf-8"))
    prior_truth = {(row["n_vars"], row["truth_sha256"]) for row in prior_document["cases"]}
    document = build_dataset(
        inventory_path=inventory.relative_to(ROOT).as_posix(),
        inventory_sha256=sha256(inventory),
        prior_dataset_path=prior.relative_to(ROOT).as_posix(),
        prior_dataset_sha256=sha256(prior),
        prior_truth_identities=prior_truth,
    )
    document = attach_query_contracts(document)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({**document["counts"], "queries": 18 * 64,
                      "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
