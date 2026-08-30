from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.d10_rule_engine import D10RulePack, compile_d10_rule_pack
from cmbench.recognition.features import structural_digest
from cmbench.recognition.portfolio import reference_bits


def bits_digest(bits: int, n_vars: int) -> str:
    return hashlib.sha256(bits.to_bytes((1 << n_vars) // 8 or 1, "little")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently replay a frozen D10 run")
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run
    result = json.loads((run / "results.json").read_text(encoding="utf-8"))
    dataset = json.loads((run / "dataset.json").read_text(encoding="utf-8"))
    pack = D10RulePack.load(run / "proved_motif_pack.json")
    matcher = compile_d10_rule_pack(pack)
    exact = 0
    case_outputs = {}
    rewrite_digests = {}
    for item in dataset["cases"]:
        expression = expr_from_json(item["expression_v2"])
        if structural_digest(expression) != item["structural_sha256"]:
            raise ValueError("D10 dataset structure changed")
        bits = reference_bits(expression, item["n_vars"])
        if bits_digest(bits, item["n_vars"]) != item["semantic_sha256"]:
            raise ValueError("D10 dataset semantics changed")
        rewrite = matcher.rewrite(expression, item["n_vars"])
        if reference_bits(rewrite.result, item["n_vars"]) != bits:
            raise ValueError("D10 rewrite semantic replay failed")
        case_outputs[item["case_id"]] = bits_digest(bits, item["n_vars"])
        rewrite_digests[item["case_id"]] = structural_digest(rewrite.result)
        exact += 1
    measurements = [json.loads(line) for line in
                    (run / "measurements.jsonl").read_text(encoding="utf-8").splitlines()]
    for row in measurements:
        if row["output_sha256"] != case_outputs[row["case_id"]] or row["mismatches"] != 0:
            raise ValueError("D10 measured output replay failed")
        expected_digest = (structural_digest(expr_from_json(next(item["expression_v2"] for item in
                           dataset["cases"] if item["case_id"] == row["case_id"])))
                           if row["arm"] == "no_rewrite" else rewrite_digests[row["case_id"]])
        if row["result_sha256"] != expected_digest:
            raise ValueError("D10 measured rewrite identity changed")
    verification = {"schema": "crse-d10-independent-verification/v1", "status": "verified",
                    "run_schema": result["schema"], "pack_sha256": pack.digest,
                    "cases_replayed": exact, "measurement_rows_replayed": len(measurements),
                    "semantic_mismatches": 0, "timings_recomputed": False,
                    "verifier_independent_of_timing_selection": True}
    target = run / "independent_verification.json"
    target.write_text(json.dumps(verification, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8", newline="\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
