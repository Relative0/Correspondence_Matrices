from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.gf2_decomposition import (
    ExactGF2Artifact,
    analyze_exact_gf2,
    analyze_screened_exact_gf2,
    truth_sha256,
)
from cmbench.recognition.gf2_decomposition_experiment import make_gf2_controls
from cmbench.recognition.gf2_screening_experiment import METHODS, summarize
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.source_anf_hybrid import packed_truth_bits, source_anf_packed
from cmbench.recognition.yosys_composed_holdout_data import make_yosys_composed_holdout


def _best(analysis):
    return analysis.best.to_dict() if analysis.best else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently replay C16 GF(2) screening evidence")
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run
    dataset = json.loads((run / "dataset.json").read_text(encoding="utf-8"))
    artifact_set = json.loads((run / "artifacts.json").read_text(encoding="utf-8"))
    results = json.loads((run / "results.json").read_text(encoding="utf-8"))
    config = results["config"]

    regenerated, provenance = make_yosys_composed_holdout()
    if dataset["cases"] != regenerated or dataset["provenance"] != provenance:
        raise ValueError("C16 frozen Yosys dataset regeneration mismatch")
    controls = make_gf2_controls(config["seed"])
    expected_control_documents = [
        {key: value for key, value in row.items() if key != "bits"}
        | {"source_sha256": truth_sha256(row["bits"], row["n_vars"])}
        for row in controls
    ]
    if dataset["controls"] != expected_control_documents:
        raise ValueError("C16 control regeneration mismatch")

    stored_artifacts = {row["case_id"]: row["artifact"] for row in artifact_set["artifacts"]}
    expected_hashes = {}
    expected_best = {}
    case_replays = 0
    for case in regenerated:
        expression = expr_from_json(case["expression_v2"])
        bits = reference_bits(expression, case["n_vars"])
        polynomial, _stats = source_anf_packed(case["expression_v2"], case["n_vars"])
        if packed_truth_bits(polynomial, case["n_vars"]) != bits:
            raise ValueError("C16 packed source ANF replay mismatch")
        exhaustive = analyze_exact_gf2(bits, case["n_vars"],
                                       max_partitions=config["max_partitions"])
        screened = analyze_screened_exact_gf2(
            bits, case["n_vars"], max_partitions=config["max_partitions"],
            materialize_budget=config["materialize_budget"]
        )
        if _best(screened) != _best(exhaustive):
            raise ValueError("C16 screened/exhaustive best mismatch")
        if any(candidate.reconstruct() != bits for candidate in screened.candidates):
            raise ValueError("C16 screened artifact replay mismatch")
        if ((case["case_id"] in stored_artifacts) != (screened.best is not None)
                or screened.best is not None
                and stored_artifacts[case["case_id"]] != screened.best.to_dict()):
            raise ValueError("C16 retained best artifact mismatch")
        expected_hashes[case["case_id"]] = truth_sha256(bits, case["n_vars"])
        expected_best[case["case_id"]] = _best(screened)
        case_replays += 1

    control_replays = 0
    for control in controls:
        kwargs = ({"row_partitions": control["row_partitions"]}
                  if control["row_partitions"] is not None else {"max_partitions": 32})
        exhaustive = analyze_exact_gf2(control["bits"], control["n_vars"], **kwargs)
        screened = analyze_screened_exact_gf2(
            control["bits"], control["n_vars"],
            materialize_budget=config["materialize_budget"], **kwargs
        )
        if _best(screened) != _best(exhaustive):
            raise ValueError("C16 control best identity mismatch")
        if any(candidate.reconstruct() != control["bits"] for candidate in screened.candidates):
            raise ValueError("C16 control reconstruction mismatch")
        if control["required_kind"] is None and screened.best is not None:
            raise ValueError("C16 dense control was compressed")
        control_replays += 1

    for row in artifact_set["artifacts"]:
        artifact = ExactGF2Artifact.from_dict(row["artifact"])
        if artifact.reconstruct() != reference_bits(
                expr_from_json(next(case for case in regenerated
                                    if case["case_id"] == row["case_id"])["expression_v2"]),
                artifact.document["n_vars"]):
            raise ValueError("C16 serialized artifact replay mismatch")

    measurements = [json.loads(line) for line in
                    (run / "measurements.jsonl").read_text(encoding="utf-8").splitlines()]
    expected_rows = len(regenerated) * config["rounds"] * len(METHODS)
    if len(measurements) != expected_rows:
        raise ValueError("C16 measurement row count mismatch")
    groups = set()
    for row in measurements:
        identity = (row["case_id"], row["method"], row["round"])
        if identity in groups or row["method"] not in METHODS:
            raise ValueError("C16 duplicate or unknown measurement")
        groups.add(identity)
        best = expected_best[row["case_id"]]
        if (row["output_sha256"] != expected_hashes[row["case_id"]]
                or row["semantic_mismatches"] or row["artifact_mismatches"]
                or row["best_artifact_sha256"] != (best["payload_sha256"] if best else None)):
            raise ValueError("C16 measured identity mismatch")

    recomputed = summarize(
        measurements,
        artifact_set["functional"],
        artifact_set["controls"],
        config["materialize_budget"],
    )
    if recomputed != results["summary"]:
        raise ValueError("C16 summary recomputation mismatch")
    verification = {
        "schema": "crse-c16-gf2-screened-tail-independent-verification/v1",
        "status": "verified",
        "run_schema": results["schema"],
        "source_cases_replayed": case_replays,
        "controls_replayed": control_replays,
        "artifacts_replayed": len(artifact_set["artifacts"]),
        "measurement_rows_checked": len(measurements),
        "exact_best_identity_mismatches": 0,
        "semantic_mismatches": 0,
        "summary_recomputed": True,
        "timings_rerun": False,
    }
    path = run / "independent_verification.json"
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
