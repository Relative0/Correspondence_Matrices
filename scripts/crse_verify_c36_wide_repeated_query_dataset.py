"""Independently verify the frozen C36 wide natural query dataset."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.contracts import canonical_bytes
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.yosys_unused_gf2_data import candidate_identity, scalar_bits
from cmbench.recognition.yosys_wide_restriction_data import (
    select_candidates, truth_sha256_wide,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def independent_trace(case_id: str, n_vars: int) -> list[dict]:
    rows = []
    choices = (6, 8, 10)
    for query in range(64):
        seed = hashlib.sha256(f"c36:{case_id}:{query}".encode("ascii")).digest()
        live = min(n_vars - 1, choices[seed[0] % 3])
        ordered = sorted(range(n_vars),
                         key=lambda index: hashlib.sha256(seed + bytes([index])).digest())
        fixed_indices = set(ordered[:n_vars - live])
        fixed = [{"variable": f"x{index}",
                  "value": (seed[1 + offset] >> (index % 8)) & 1}
                 for offset, index in enumerate(sorted(fixed_indices))]
        row = {"query": query, "fixed": fixed,
               "remaining_order": [f"x{i}" for i in range(n_vars) if i not in fixed_indices]}
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
    n_vars = case["n_vars"]
    rows = []
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
    return {"schema": "crse-c36-wide-partial-context-output/v1",
            "case_id": case["case_id"], "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path,
                        default=ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/recognition/c36_wide_repeated_query_dataset_verification.json")
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    provenance = dataset["provenance"]
    inventory = ROOT.joinpath(*Path(provenance["source_inventory"]).parts)
    prior = ROOT.joinpath(*Path(provenance["prior_dataset"]).parts)
    if (sha256(inventory) != provenance["source_inventory_sha256"]
            or sha256(prior) != provenance["prior_dataset_sha256"]):
        raise ValueError("C36 source binding mismatch")
    prior_document = json.loads(prior.read_text(encoding="utf-8"))
    prior_truth = {(row["n_vars"], row["truth_sha256"]) for row in prior_document["cases"]}
    candidate_map = {candidate_identity(candidate): candidate for candidate in select_candidates()}
    semantic_mismatches = trace_mismatches = selection_mismatches = 0
    semantics = set()
    for row in dataset["cases"]:
        candidate = candidate_map.get(row["selection_sha256"])
        selection_mismatches += int(
            candidate is None or len(candidate.variable_specs) != row["n_vars"]
            or candidate.family != row["family"] or candidate.parameters != row["parameters"])
        if candidate is None:
            continue
        scalar = scalar_bits(candidate)
        expression = reference_bits(candidate.expression, row["n_vars"])
        semantic = (row["n_vars"], truth_sha256_wide(scalar, row["n_vars"]))
        semantic_mismatches += int(
            scalar != expression or scalar != int(row["truth_bits_hex"], 16)
            or semantic[1] != row["truth_sha256"] or semantic in prior_truth
            or semantic in semantics)
        semantics.add(semantic)
        trace = independent_trace(row["case_id"], row["n_vars"])
        trace_mismatches += int(trace != row["c36_trace"])
        output = independent_output(row, trace)
        semantic_mismatches += int(
            hashlib.sha256(canonical_bytes(output)).hexdigest()
            != row["c36_required_output_sha256"])
    if (len(dataset.get("cases", [])) != 18 or len(candidate_map) != 18
            or any((semantic_mismatches, trace_mismatches, selection_mismatches))):
        raise RuntimeError("C36 dataset independent replay failed")
    result = {
        "schema": "crse-c36-wide-repeated-query-dataset-verification/v1",
        "status": "verified", "cases_replayed": 18, "queries_replayed": 1152,
        "scalar_oracles_replayed": 18, "semantic_mismatches": 0,
        "trace_mismatches": 0, "selection_mismatches": 0,
        "selection_recomputed": True, "timing_or_method_output_used": False,
        "dataset_sha256": sha256(args.dataset), "inventory_sha256": sha256(inventory),
        "prior_dataset_sha256": sha256(prior),
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
