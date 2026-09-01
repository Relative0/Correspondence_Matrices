"""Freeze the C27 corpus after the transparent support policy is sealed."""
from __future__ import annotations

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
from cmbench.recognition.gf2_support_aware_policy import load_support_aware_policy
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.yosys_c27_gf2_data import (
    SOURCE_COMMIT, SOURCE_FILES, SOURCE_GENERATORS, SOURCE_URL,
    admitted_rows, dataset_document, validate_dataset,
)

REPOSITORY = ROOT / "external/yosys-bench-confirmation-20260830"
POLICY = ROOT / "docs/recognition/c27_support_aware_policy.json"
INVENTORY = ROOT / "docs/recognition/c27_yosys_source_inventory.json"
OUTPUT = ROOT / "docs/recognition/c27_yosys_fresh_gf2_dataset.json"
PRIOR = (
    ROOT / "docs/recognition/c16_linux_confirmation/c16_dataset.json",
    ROOT / "docs/recognition/c18_independent_cone_dataset.json",
    ROOT / "docs/recognition/c19_logikbench_small_cone_dataset.json",
    ROOT / "docs/recognition/runs/yosys-source-anf-confirmation-20260830-002/dataset.json",
    ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset_v2.json",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=REPOSITORY, check=True,
                          stdout=subprocess.PIPE).stdout


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def prior_truths() -> tuple[set[tuple[int, str]], dict[str, int], set[str]]:
    result, counts, generators = set(), {}, set()
    for path in PRIOR:
        rows = load(path)
        rows = rows if isinstance(rows, list) else rows["cases"]
        before = len(result)
        for row in rows:
            n_vars = row["n_vars"]
            digest = row.get("truth_sha256")
            if digest is None:
                bits = reference_bits(expr_from_json(row["expression_v2"]), n_vars)
                digest = truth_sha256(bits, n_vars)
            result.add((n_vars, digest))
            source = row.get("source_generator")
            generators.update(source if isinstance(source, list) else [source] if source else [])
        counts[str(path.relative_to(ROOT)).replace("\\", "/")] = len(result) - before
    return result, counts, generators


def write_new(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def main() -> int:
    if INVENTORY.exists() or OUTPUT.exists():
        raise SystemExit("refusing to overwrite frozen C27 corpus inputs")
    policy = load_support_aware_policy(POLICY)
    if policy.get("fresh_confirmation_complete") is not False:
        raise ValueError("C27 policy must be pre-confirmation")
    head = git("rev-parse", "HEAD").decode().strip()
    if head != SOURCE_COMMIT:
        raise ValueError("pinned Yosys-bench checkout changed")
    prior, prior_counts, used_generators = prior_truths()
    if used_generators & set(SOURCE_GENERATORS):
        raise ValueError("C27 generator group overlaps prior evidence")
    files = []
    for name in ("LICENSE.txt", *SOURCE_FILES):
        content = git("show", f"HEAD:{name}")
        files.append({
            "path": name, "bytes": len(content), "sha256": sha256_bytes(content),
            "git_blob_sha1": git("rev-parse", f"HEAD:{name}").decode().strip(),
        })
    inventory = {
        "schema": "crse-c27-yosys-unused-generator-source-inventory/v1",
        "status": "frozen", "repository": SOURCE_URL, "commit": SOURCE_COMMIT,
        "license": "ISC", "files": files,
        "prior_generators": sorted(used_generators),
        "c27_generators": list(SOURCE_GENERATORS),
        "generator_path_overlap_with_prior": 0,
        "network_used": False, "checkout_modified": False,
    }
    rows, rejected = admitted_rows(prior)
    inventory_bytes = (json.dumps(
        inventory, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False,
    ) + "\n").encode("utf-8")
    dataset = dataset_document(
        rows, rejected,
        inventory_path=str(INVENTORY.relative_to(ROOT)).replace("\\", "/"),
        inventory_sha256=sha256_bytes(inventory_bytes),
        policy_path=str(POLICY.relative_to(ROOT)).replace("\\", "/"),
        policy_file_sha256=sha256(POLICY),
        policy_sha256=policy["policy_sha256"],
    )
    dataset["prior_truth_exclusion"] = {
        "identities": len(prior), "new_identities_by_source": prior_counts,
        "sources": [str(path.relative_to(ROOT)).replace("\\", "/") for path in PRIOR],
        "source_sha256": {str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path)
                          for path in PRIOR},
    }
    validate_dataset(dataset)
    write_new(INVENTORY, inventory)
    write_new(OUTPUT, dataset)
    print(json.dumps(dataset["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
