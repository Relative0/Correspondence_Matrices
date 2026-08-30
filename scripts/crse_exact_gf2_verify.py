from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.bdd_ordering import ExactBddArtifact
from cmbench.recognition.gf2_decomposition import ExactGF2Artifact, truth_sha256
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.source_anf_hybrid import packed_truth_bits, source_anf_packed


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently replay frozen exact CM/GF(2) output")
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run
    dataset = json.loads((run / "dataset.json").read_text(encoding="utf-8"))
    artifact_set = json.loads((run / "artifacts.json").read_text(encoding="utf-8"))
    results = json.loads((run / "results.json").read_text(encoding="utf-8"))
    expected = {}
    method_replays = 0
    for case in dataset["cases"]:
        expression = expr_from_json(case["expression_v2"])
        bits = reference_bits(expression, case["n_vars"])
        if truth_sha256(bits, case["n_vars"]) != case["semantic_sha256"]:
            raise ValueError("C15 dataset semantic replay failed")
        polynomial, _stats = source_anf_packed(case["expression_v2"], case["n_vars"])
        if packed_truth_bits(polynomial, case["n_vars"]) != bits:
            raise ValueError("C15 packed source ANF replay failed")
        with ExactBddArtifact.build(expression, case["n_vars"],
                                    tuple(f"x{i}" for i in range(case["n_vars"])),
                                    backend="autoref") as bdd:
            bdd_bits = sum(value << index for index, value in enumerate(bdd.truth_bits()))
        if bdd_bits != bits:
            raise ValueError("C15 ROBDD replay failed")
        expected[case["case_id"]] = truth_sha256(bits, case["n_vars"])
        method_replays += 3
    artifact_replays = 0
    for row in artifact_set["artifacts"]:
        artifact = ExactGF2Artifact.from_dict(row["artifact"])
        if truth_sha256(artifact.reconstruct(), artifact.document["n_vars"]) != artifact.document["source_sha256"]:
            raise ValueError("C15 artifact replay failed")
        if row["case_id"] in expected and artifact.document["source_sha256"] != expected[row["case_id"]]:
            raise ValueError("C15 artifact/source identity mismatch")
        artifact_replays += 1
    measurements = [json.loads(line) for line in
                    (run / "measurements.jsonl").read_text(encoding="utf-8").splitlines()]
    for row in measurements:
        if row["output_sha256"] != expected[row["case_id"]] or row["mismatches"]:
            raise ValueError("C15 measured output identity mismatch")
    verification = {"schema": "crse-c15-exact-cm-gf2-independent-verification/v1",
                    "status": "verified", "run_schema": results["schema"],
                    "source_cases_replayed": len(dataset["cases"]),
                    "exact_method_replays": method_replays,
                    "artifacts_replayed": artifact_replays,
                    "measurement_rows_checked": len(measurements),
                    "semantic_mismatches": 0, "timings_recomputed": False}
    (run / "independent_verification.json").write_text(
        json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
