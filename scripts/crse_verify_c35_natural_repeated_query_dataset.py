"""Independently verify the frozen C35 natural repeated-query dataset."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.comparative.contracts import canonical_bytes
from cmbench.recognition.portfolio import reference_bits


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def independent_trace(case_id: str, n_vars: int) -> list[dict]:
    rows = []
    for query in range(64):
        seed = hashlib.sha256(f"c35:{case_id}:{query}".encode("ascii")).digest()
        count = 1 + seed[0] % min(4, n_vars - 1)
        selected = sorted(
            range(n_vars), key=lambda index: hashlib.sha256(seed + bytes([index])).digest()
        )[:count]
        fixed = [{"variable": f"x{index}",
                  "value": (seed[1 + offset] >> (index % 8)) & 1}
                 for offset, index in enumerate(sorted(selected))]
        row = {"query": query, "fixed": fixed,
               "remaining_order": [f"x{i}" for i in range(n_vars) if i not in selected]}
        row["query_sha256"] = hashlib.sha256(canonical_bytes(row)).hexdigest()
        rows.append(row)
    return rows


def independent_reduced(bits: int, n_vars: int, fixed_rows: list[dict]) -> int:
    fixed = {int(row["variable"][1:]): row["value"] for row in fixed_rows}
    remaining = [index for index in range(n_vars) if index not in fixed]
    output = 0
    for residual in range(1 << len(remaining)):
        values = dict(fixed)
        for position, index in enumerate(remaining):
            values[index] = (residual >> (len(remaining) - 1 - position)) & 1
        original = 0
        for index in range(n_vars):
            original = (original << 1) | values[index]
        output |= ((bits >> original) & 1) << residual
    return output


def independent_output(case: dict, trace: list[dict]) -> dict:
    rows = []
    n_vars = case["n_vars"]
    for query in trace:
        reduced = independent_reduced(int(case["truth_bits_hex"], 16), n_vars, query["fixed"])
        remaining = query["remaining_order"]
        byte_count = max(1, ((1 << len(remaining)) + 7) // 8)
        if reduced:
            residual = (reduced & -reduced).bit_length() - 1
            values = {row["variable"]: row["value"] for row in query["fixed"]}
            for position, name in enumerate(remaining):
                values[name] = (residual >> (len(remaining) - 1 - position)) & 1
            witness = [{"variable": f"x{i}", "value": values[f"x{i}"]}
                       for i in range(n_vars)]
        else:
            witness = None
        rows.append({
            "query": query["query"], "query_sha256": query["query_sha256"],
            "fixed": query["fixed"], "remaining_order": remaining,
            "truth_bits_hex": format(reduced, "x"),
            "truth_sha256": hashlib.sha256(reduced.to_bytes(byte_count, "little")).hexdigest(),
            "exact_count": reduced.bit_count(), "satisfiable": bool(reduced),
            "canonical_witness": witness,
        })
    return {"schema": "crse-c35-partial-context-output/v1",
            "case_id": case["case_id"], "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path,
                        default=ROOT / "docs/recognition/c35_natural_repeated_query_dataset.json")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/recognition/c35_natural_repeated_query_dataset_verification.json")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    source_path = ROOT.joinpath(*Path(manifest["source"]["dataset_path"]).parts)
    c34_path = ROOT.joinpath(*Path(manifest["source"]["c34_manifest_path"]).parts)
    c34_verification_path = ROOT.joinpath(
        *Path(manifest["source"]["c34_verification_path"]).parts)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source_map = {case["case_id"]: case for case in source["cases"]}
    if (manifest.get("schema") != "crse-c35-natural-repeated-query-dataset/v1"
            or manifest.get("status") != "frozen"
            or sha256(source_path) != manifest["source"]["dataset_sha256"]
            or sha256(c34_path) != manifest["source"]["c34_manifest_sha256"]
            or sha256(c34_verification_path) != manifest["source"]["c34_verification_sha256"]):
        raise ValueError("C35 dataset/input binding mismatch")
    semantic_mismatches = trace_mismatches = 0
    selected = []
    for n_vars in range(3, 11):
        group = [case for case in source["cases"] if case["n_vars"] == n_vars]
        selected.append(min(group, key=lambda row: (row["selection_sha256"],
                                                     row["case_id"]))["case_id"])
    if selected != [row["case_id"] for row in manifest["cases"]]:
        raise ValueError("C35 selection mismatch")
    for row in manifest["cases"]:
        case = source_map[row["case_id"]]
        replayed = reference_bits(expr_from_json(case["expression_v2"]), case["n_vars"])
        semantic_mismatches += int(replayed != int(case["truth_bits_hex"], 16))
        trace = independent_trace(case["case_id"], case["n_vars"])
        trace_mismatches += int(trace != row["trace"])
        output = independent_output(case, trace)
        semantic_mismatches += int(
            hashlib.sha256(canonical_bytes(output)).hexdigest()
            != row["required_output_sha256"])
    if semantic_mismatches or trace_mismatches:
        raise RuntimeError("C35 dataset independent replay failed")
    result = {
        "schema": "crse-c35-natural-repeated-query-dataset-verification/v1",
        "status": "verified", "cases_replayed": 8, "queries_replayed": 512,
        "semantic_mismatches": 0, "trace_mismatches": 0,
        "selection_recomputed": True, "outcome_or_timing_used": False,
        "manifest_sha256": sha256(args.manifest), "source_sha256": sha256(source_path),
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
