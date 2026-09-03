"""Create the prospective C37 dataset only after the native package is frozen."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_multi_root import prospective_sibling_output_workloads
from cmbench.comparative.gf2_multi_root_experiment import _oracle
from cmbench.comparative.contracts import canonical_bytes
from cmbench.recognition.yosys_native_confirmation_data import build_dataset


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--freeze", type=Path,
        default=ROOT / "docs/recognition/c37_native_exact_confirmation/freeze_v3.json",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "docs/recognition/c37_native_exact_confirmation_dataset.json",
    )
    args = parser.parse_args()
    freeze_path = args.freeze.resolve()
    output = args.output.resolve()
    if not freeze_path.is_relative_to(ROOT) or not output.is_relative_to(ROOT):
        raise ValueError("C37 paths must stay inside the project")
    freeze = load(freeze_path)
    if (
        freeze.get("status") != "frozen_before_dataset_and_timing"
        or freeze.get("scientific_boundary", {}).get("dataset_created") is not False
        or freeze.get("scientific_boundary", {}).get("prospective_timing_run") is not False
    ):
        raise ValueError("C37 package was not frozen before dataset creation")
    for relative, identity in freeze["sources"].items():
        path = ROOT.joinpath(*Path(relative).parts)
        if (not path.is_file() or path.stat().st_size != identity["bytes"]
                or sha256(path) != identity["sha256"]):
            raise ValueError(f"C37 frozen source changed: {relative}")
    library = ROOT.joinpath(*Path(freeze["native_library"]["path"]).parts)
    if sha256(library) != freeze["native_library"]["sha256"]:
        raise ValueError("C37 frozen native library changed")
    document = build_dataset(
        freeze_path=freeze_path.relative_to(ROOT).as_posix(),
        freeze_sha256=sha256(freeze_path),
    )
    c36 = load(ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json")
    c36_semantics = {(row["n_vars"], row["truth_sha256"]) for row in c36["cases"]}
    overlaps = [row["case_id"] for row in document["cases"]
                if (row["n_vars"], row["truth_sha256"]) in c36_semantics]
    if overlaps:
        raise RuntimeError(f"C37 truth identity overlaps C36: {overlaps}")
    workloads = prospective_sibling_output_workloads()
    document["multi_root"] = {
        "schema": "crse-c37-native-multi-root-confirmation-dataset/v1",
        "selection_uses_outputs_or_timings": False,
        "workloads": [
            {
                "workload_id": workload.workload_id,
                "family": workload.family,
                "n_vars": workload.n_vars,
                "roots": len(workload.roots),
                "trace_sha256": hashlib.sha256(canonical_bytes(workload.trace)).hexdigest(),
                "union_document": workload.union_document,
                "separate_document_sha256": [
                    hashlib.sha256(canonical_bytes(value)).hexdigest()
                    for value in workload.separate_documents
                ],
                "sum_separate_nodes": sum(len(value["nodes"])
                                          for value in workload.separate_documents),
                "union_nodes": len(workload.union_document["nodes"]),
                "required_output_sha256": _oracle(workload)[0],
            }
            for workload in workloads
        ],
    }
    document["provenance"]["c36_dataset_path"] = (
        "docs/recognition/c36_wide_repeated_query_dataset.json"
    )
    document["provenance"]["c36_dataset_sha256"] = sha256(
        ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json"
    )
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")
    print(json.dumps({
        "status": "frozen", "single_root_cases": len(document["cases"]),
        "multi_root_workloads": len(workloads), "dataset_sha256": sha256(output),
        "output": str(output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
