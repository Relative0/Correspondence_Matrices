"""Freeze fresh C23 GF(2) cases from unused pinned Yosys-bench generators."""
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
from cmbench.recognition.gf2_decomposition import truth_sha256
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.yosys_unused_gf2_data import (
    SOURCE_COMMIT,
    SOURCE_GENERATORS,
    SOURCE_URL,
    admitted_rows,
    dataset_document,
    validate_dataset,
)

REPOSITORY = ROOT / "external/yosys-bench-confirmation-20260830"
C7_DATASET = ROOT / "docs/recognition/runs/yosys-source-anf-confirmation-20260830-002/dataset.json"
C16_DATASET = ROOT / "docs/recognition/c16_linux_confirmation/c16_dataset.json"
C18_DATASET = ROOT / "docs/recognition/c18_independent_cone_dataset.json"
C19_DATASET = ROOT / "docs/recognition/c19_logikbench_small_cone_dataset.json"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=REPOSITORY, check=True, stdout=subprocess.PIPE,
    ).stdout


def prior_truth_identities() -> tuple[set[tuple[int, str]], dict[str, int]]:
    result: set[tuple[int, str]] = set()
    counts = {}
    for name, path in (("c16", C16_DATASET), ("c18", C18_DATASET), ("c19", C19_DATASET)):
        document = load(path)
        before = len(result)
        for row in document["cases"]:
            if "truth_sha256" in row:
                digest = row["truth_sha256"]
            else:
                bits = reference_bits(expr_from_json(row["expression_v2"]), row["n_vars"])
                digest = truth_sha256(bits, row["n_vars"])
            result.add((row["n_vars"], digest))
        counts[name] = len(result) - before
    c7 = load(C7_DATASET)
    before = len(result)
    for row in c7:
        bits = reference_bits(expr_from_json(row["expression_v2"]), row["n_vars"])
        result.add((row["n_vars"], truth_sha256(bits, row["n_vars"])))
    counts["c7"] = len(result) - before
    return result, counts


def write_new(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze fresh C23 Yosys generator cases")
    parser.add_argument("--target", type=int, default=48)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset.json")
    parser.add_argument("--inventory", type=Path,
                        default=ROOT / "docs/recognition/c23_yosys_fresh_source_inventory.json")
    args = parser.parse_args()
    if args.output.exists() or args.inventory.exists():
        raise SystemExit("refusing to overwrite frozen C23 inputs")
    head = git("rev-parse", "HEAD").decode().strip()
    if head != SOURCE_COMMIT:
        raise ValueError("pinned Yosys-bench checkout changed")
    paths = ("LICENSE.txt", *SOURCE_GENERATORS)
    files = []
    for path in paths:
        content = git("show", f"HEAD:{path}")
        blob = git("rev-parse", f"HEAD:{path}").decode().strip()
        files.append({"path": path, "bytes": len(content), "sha256": sha256_bytes(content),
                      "git_blob_sha1": blob})
    c7 = load(C7_DATASET)
    c7_generators = {row["source_generator"] for row in c7}
    if c7_generators & set(SOURCE_GENERATORS):
        raise ValueError("C23 generator family overlaps C7")
    prior, prior_counts = prior_truth_identities()
    rows, rejected = admitted_rows(prior)
    inventory = {
        "schema": "crse-c23-yosys-unused-generator-source-inventory/v1",
        "status": "frozen",
        "repository": SOURCE_URL,
        "commit": SOURCE_COMMIT,
        "license": "ISC",
        "files": files,
        "c7_generators": sorted(c7_generators),
        "c23_generators": list(SOURCE_GENERATORS),
        "generator_path_overlap_with_c7": 0,
        "network_used": False,
        "checkout_modified": False,
    }
    write_new(args.inventory, inventory)
    inventory_relative = str(args.inventory.relative_to(ROOT)).replace("\\", "/")
    dataset = dataset_document(rows, rejected, inventory_relative, sha256(args.inventory), args.target)
    dataset["prior_truth_exclusion"] = {
        "identities": len(prior),
        "new_identities_by_source": prior_counts,
        "sources": {
            "c16": str(C16_DATASET.relative_to(ROOT)).replace("\\", "/"),
            "c18": str(C18_DATASET.relative_to(ROOT)).replace("\\", "/"),
            "c19": str(C19_DATASET.relative_to(ROOT)).replace("\\", "/"),
            "c7": str(C7_DATASET.relative_to(ROOT)).replace("\\", "/"),
        },
        "source_sha256": {name: sha256(path) for name, path in (
            ("c16", C16_DATASET), ("c18", C18_DATASET),
            ("c19", C19_DATASET), ("c7", C7_DATASET))},
    }
    validate_dataset(dataset)
    write_new(args.output, dataset)
    print(json.dumps(dataset["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
