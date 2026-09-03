"""Independently replay the C34 natural-corpus role manifest and exact truths."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.comparative.gf2_natural_headroom import (
    select_decomposition_case_ids,
    validate_dataset_manifest,
)
from cmbench.recognition.gf2_decomposition import truth_sha256
from cmbench.recognition.portfolio import reference_bits


DEFAULT_MANIFEST = ROOT / "docs/recognition/c34_natural_headroom_dataset.json"
DEFAULT_OUTPUT = ROOT / "docs/recognition/c34_natural_headroom_dataset_verification.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_bound(relative: str) -> Path:
    path = ROOT.joinpath(*Path(relative).parts).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError("C34 bound path escaped or is missing")
    return path


def write_new(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    source_path = resolve_bound(manifest["source"]["path"])
    source_verification_path = resolve_bound(manifest["source"]["verification_path"])
    if (sha256(source_path) != manifest["source"]["sha256"]
            or sha256(source_verification_path) != manifest["source"]["verification_sha256"]):
        raise ValueError("C34 source binding changed")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source_verification = json.loads(source_verification_path.read_text(encoding="utf-8"))
    validate_dataset_manifest(manifest, source)
    mismatches = 0
    for case in source["cases"]:
        expression = expr_from_json(case["expression_v2"])
        bits = reference_bits(expression, case["n_vars"])
        mismatches += int(
            bits != int(case["truth_bits_hex"], 16)
            or truth_sha256(bits, case["n_vars"]) != case["truth_sha256"]
        )
    decomposition_ids = set(select_decomposition_case_ids(source["cases"]))
    selected = [row for row in manifest["cases"] if row["decomposition_role"]]
    selection_mismatches = int({row["case_id"] for row in selected} != decomposition_ids)
    status = "verified" if not mismatches and not selection_mismatches else "failed"
    result = {
        "schema": "crse-c34-natural-headroom-dataset-verification/v1",
        "status": status,
        "manifest_sha256": sha256(args.manifest),
        "source_dataset_sha256": sha256(source_path),
        "source_verification_sha256": sha256(source_verification_path),
        "source_verification_status": source_verification.get("status"),
        "cases_replayed": len(source["cases"]),
        "widths_replayed": dict(sorted(Counter(case["n_vars"] for case in source["cases"]).items())),
        "decomposition_cases_reselected": len(decomposition_ids),
        "semantic_mismatches": mismatches,
        "selection_mismatches": selection_mismatches,
        "timing_or_method_output_used": False,
        "training_use": False,
        "policy_selection_use": False,
        "fresh_confirmation": False,
        "source_dataset_reused": True,
        "network_used": False,
        "production_promotion": False,
    }
    if status != "verified":
        raise RuntimeError(f"C34 dataset verification failed: {result}")
    write_new(args.output, result)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
