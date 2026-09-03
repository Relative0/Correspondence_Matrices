"""Independently verify C33 bounded asynchronous shadow evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_async_shadow_experiment import (
    ASYNC_FULL,
    ASYNC_QUARTER,
    DISABLED,
    METHODS,
    SYNCHRONOUS,
    C33Config,
    build_schedule,
    control_signature,
    run_controls,
    summarize,
)
from cmbench.comparative.gf2_table_experiment import build_oracles
from cmbench.recognition.gf2_async_shadow_boundary import (
    verify_async_shadow_observation,
    verify_async_shadow_serve_result,
)
from cmbench.recognition.gf2_prepared_shadow_boundary import (
    verify_prepared_policy_shadow_result,
)
from cmbench.recognition.yosys_c27_gf2_data import validate_dataset


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_input(spec: dict, key: str) -> Path:
    path = (ROOT / spec[key]).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"C33 input escapes repository: {key}") from exc
    return path


def verify_manifest(run: Path, manifest: dict, spec: dict) -> tuple[int, int, int]:
    source_count = artifact_count = input_count = 0
    for relative, expected in manifest.get("sources", {}).items():
        path = (ROOT / relative).resolve()
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"C33 source hash mismatch: {relative}")
        source_count += 1
    for relative, expected in manifest.get("artifacts", {}).items():
        path = run / relative
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"C33 artifact hash mismatch: {relative}")
        artifact_count += 1
    input_pairs = (
        ("dataset_path", "dataset_sha256"),
        ("dataset_verification_path", "dataset_verification_sha256"),
        ("c27_policy_path", "c27_policy_file_sha256"),
        ("c22_policy_path", "c22_policy_file_sha256"),
        ("c31_final_path", "c31_final_sha256"),
        ("c31_adjudication_path", "c31_adjudication_sha256"),
        ("c32_summary_path", "c32_summary_sha256"),
    )
    for path_key, hash_key in input_pairs:
        path = resolve_input(spec, path_key)
        expected = spec[hash_key]
        if manifest["inputs"].get(hash_key) != expected or sha256(path) != expected:
            raise ValueError(f"C33 input hash mismatch: {path_key}")
        input_count += 1
    return source_count, artifact_count, input_count


def verify_rows(
    rows: list[dict], dataset: dict, oracles: dict[str, dict], config: C33Config,
) -> tuple[int, int, int]:
    schedule = build_schedule(config)
    if len(rows) != len(schedule):
        raise ValueError("C33 measurement row count changed")
    case_by_id = {case["case_id"]: case for case in dataset["cases"]}
    served = async_observations = synchronous_observations = 0
    schedule_fields = (
        "block", "group_id", "n_vars", "width_position", "arm_position", "method")
    for row, expected_cell in zip(rows, schedule):
        if any(row.get(field) != expected_cell[field] for field in schedule_fields):
            raise ValueError("C33 schedule row changed")
        method = row["method"]
        records = row.get("query_records", [])
        observations = row.get("observations", [])
        if len(records) != config.query_count:
            raise ValueError("C33 query record count changed")
        observations_by_index = {
            observation["request_index"]: observation for observation in observations}
        if len(observations_by_index) != len(observations):
            raise ValueError("duplicate C33 asynchronous observation index")
        for record in records:
            case = case_by_id.get(record.get("case_id"))
            if case is None or case["n_vars"] != row["n_vars"]:
                raise ValueError("C33 measurement case identity changed")
            required = oracles[case["case_id"]]["best_artifact"]
            if method == SYNCHRONOUS:
                verify_prepared_policy_shadow_result(
                    record, case, required_best=required)
                if (
                    record["candidate_status"] != "observed"
                    or record["candidate_best_identity_match"] is not True
                ):
                    raise ValueError("C33 synchronous candidate record changed")
                synchronous_observations += 1
            else:
                verify_async_shadow_serve_result(record, case, required_best=required)
                observation = observations_by_index.get(record["request_index"])
                if record["shadow_disposition"] == "staged_pending_delivery_ack":
                    if observation is None:
                        raise ValueError("C33 acknowledged observation missing")
                    verify_async_shadow_observation(
                        observation,
                        case,
                        required_best=required,
                        envelope_sha256=record["shadow_envelope_sha256"],
                    )
                    if (
                        observation["candidate_status"] != "observed"
                        or observation["candidate_best_identity_match"] is not True
                    ):
                        raise ValueError("C33 asynchronous candidate record changed")
                    async_observations += 1
                elif observation is not None:
                    raise ValueError("C33 unsampled request acquired an observation")
            served += 1
        if method == DISABLED and observations:
            raise ValueError("C33 disabled batch has observations")
        if method == ASYNC_FULL and len(observations) != config.query_count:
            raise ValueError("C33 full-shadow coverage changed")
        if method == ASYNC_QUARTER and len(observations) != config.query_count // 4:
            raise ValueError("C33 sampled-shadow coverage changed")
    return served, async_observations, synchronous_observations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    destination = run / "independent_verification.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")

    manifest = load(run / "manifest.json")
    result = load(run / "results.json")
    spec = load(run / "run_spec.json")
    controls = load(run / "functional_controls.json")
    rows = load_rows(run / "measurements.jsonl")
    if (
        manifest.get("schema") != "crse-c33-async-shadow-run-manifest/v1"
        or result.get("schema")
        != "crse-c33-prepared-policy-async-shadow-experiment/v1"
        or spec.get("schema")
        != "crse-c33-prepared-policy-async-shadow-experiment/v1"
        or spec.get("methods") != list(METHODS)
        or spec.get("delivery_ack_required_before_candidate") is not True
        or spec.get("candidate_observed_only") is not True
        or any(document.get(key) is not False for document in (manifest, result, spec)
               for key in ("policy_refit", "training", "production_write",
                           "shadow_promotion", "production_promotion"))
    ):
        raise ValueError("C33 evidence contract changed")

    config = C33Config(**spec["config"])
    config.validate()
    source_count, artifact_count, input_count = verify_manifest(
        run, manifest, spec)
    dataset_path = resolve_input(spec, "dataset_path")
    dataset = load(dataset_path)
    validate_dataset(dataset)
    verification = load(resolve_input(spec, "dataset_verification_path"))
    if (
        len(dataset.get("cases", [])) != 48
        or verification.get("status") != "verified"
        or verification.get("cases_replayed") != 48
        or verification.get("expression_truth_mismatches") != 0
        or verification.get("scalar_oracle_mismatches") != 0
        or verification.get("prior_truth_overlaps") != 0
    ):
        raise ValueError("C33 dataset verification changed")
    functional, oracles = build_oracles(dataset["cases"], config.oracle_config())
    if not functional["all_exact"]:
        raise ValueError("C33 exhaustive oracle replay failed")

    served, async_observations, synchronous_observations = verify_rows(
        rows, dataset, oracles, config)
    recomputed = summarize(rows, controls, config)
    if recomputed != result.get("summary"):
        raise ValueError("C33 summary recomputation mismatch")

    with tempfile.TemporaryDirectory(prefix="c33-control-replay-") as temporary:
        replayed_controls = run_controls(
            output=Path(temporary),
            cases=dataset["cases"],
            oracles=oracles,
            c27_policy_path=resolve_input(spec, "c27_policy_path"),
            c22_policy_path=resolve_input(spec, "c22_policy_path"),
        )
    if control_signature(replayed_controls) != control_signature(controls):
        raise ValueError("C33 functional-control replay mismatch")

    summary = result["summary"]
    if (
        result.get("status") != "complete"
        or controls.get("all_passed") is not True
        or summary.get("measurement_batches") != 256
        or summary.get("counterbalanced_groups") != 64
        or served != summary.get("served_exact_queries")
        or served != 2048
        or async_observations != 640
        or synchronous_observations != 512
        or summary.get("candidate_observations") != 1152
        or summary.get("semantic_or_artifact_mismatches") != 0
        or summary.get("candidate_results_served") != 0
        or summary.get("pre_ack_candidate_observations") != 0
        or summary.get("exact_containment_gate") is not True
    ):
        raise ValueError("C33 final evidence gate changed")

    output = {
        "schema": "crse-c33-independent-verification/v1",
        "status": "verified",
        "source_files_checked": source_count,
        "artifact_files_checked": artifact_count,
        "input_files_checked": input_count,
        "measurement_batches_checked": len(rows),
        "counterbalanced_groups_checked": len(rows) // len(METHODS),
        "served_exact_queries_replayed": served,
        "async_candidate_observations_replayed": async_observations,
        "synchronous_candidate_observations_replayed": synchronous_observations,
        "functional_controls_replayed": 10,
        "schedule_recomputed": True,
        "summary_recomputed": True,
        "semantic_or_artifact_mismatches": 0,
        "candidate_results_served": 0,
        "pre_ack_candidate_observations": 0,
        "production_writes": 0,
        "policy_refit": False,
        "training": False,
        "shadow_promotion": False,
        "production_promotion": False,
        "results_sha256": sha256(run / "results.json"),
        "manifest_sha256": sha256(run / "manifest.json"),
    }
    destination.write_bytes(json.dumps(
        output, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
