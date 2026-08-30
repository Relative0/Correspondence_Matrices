"""Independently verify the successful C12 package-v2 Linux confirmation."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN_DIR = HERE / "runpod-c12-linux-execute-006"
NO_CREATE_DIR = HERE / "runpod-c12-linux-execute-005"
STUDY = RUN_DIR / "evidence/run-output/yosys-c7-linux-confirmation"
DATASET = ROOT / "docs/recognition/runs/adaptive-exact-dispatcher-robust-20260830-002/c12_dataset.json"
MANIFEST = HERE / "c12_linux_upload_manifest_v2.json"
PROTOCOL = HERE / "C12_SECOND_MACHINE_TIMING_PACKAGE_V2_PROTOCOL_2026_08_30.md"
LOCAL_VALIDATION = HERE / "C12_PACKAGE_V2_LOCAL_VALIDATION_20260830.json"
AUTHORIZATION = HERE / "RUNPOD_C12_LINUX_PACKAGE_V2_AUTHORIZED_2026_08_30.json"
CONTROLLER = HERE / "runpod_c12_linux_controller_v6.py"
OUTPUT = HERE / "RUNPOD_C12_LINUX_PACKAGE_V2_FINAL_VERIFICATION_20260830.json"
FIRST_VERIFY = HERE / "RUNPOD_C12_LINUX_ATTEMPT_FINAL_VERIFICATION_20260830.json"
RETRY_VERIFY = HERE / "RUNPOD_C12_LINUX_RETRY_FINAL_VERIFICATION_20260830.json"

sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "c12_linux_confirmation", ROOT / "scripts/crse_adaptive_dispatcher_linux_confirmation.py")
confirmation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(confirmation)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def expected_semantics(documents: list[dict]) -> dict[tuple[str, str, str], dict]:
    expected = {}
    for split in confirmation.SPLITS:
        rows = [row for row in documents if row["split"] == split]
        for method in confirmation.METHODS:
            cache = confirmation.ProductCache(1024) if method != "set_source_anf" else None
            for row in rows:
                partition, selected = confirmation.solve(method, row, cache)
                bits = confirmation.reference_bits(
                    confirmation.expr_from_json(row["expression_v2"]), row["n_vars"])
                witness = (confirmation.partition_witness(bits, row["n_vars"], partition)
                           if partition is not None else None)
                canonical = (tuple(row["witness"]["row_variables"])
                             if row["witness"] is not None else None)
                expected[(method, split, row["case_id"])] = {
                    "selected_arm": selected,
                    "predicted": int(partition is not None),
                    "accepted": bool(partition is not None and witness is not None),
                    "row_variables": list(partition) if partition is not None else None,
                    "canonical_partition_match": partition == canonical,
                    "semantic_mismatch": bool(
                        partition is not None and witness is not None and not row["label"]),
                }
    return expected


def recompute_per_case(measurements: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for row in measurements:
        grouped[(row["method"], row["split"], row["case_id"])].append(row)
    result = []
    semantic_fields = ("selected_arm", "predicted", "accepted", "row_variables",
                       "canonical_partition_match", "semantic_mismatch")
    for (method, split, case_id), values in sorted(grouped.items()):
        require(len(values) == 16, "not every Linux method/case has 16 repetitions")
        first = values[0]
        require(all(all(row[field] == first[field] for field in semantic_fields)
                    for row in values[1:]), "Linux semantics changed between repetitions")
        result.append({
            "method": method, "split": split, "case_id": case_id,
            "n_vars": first["n_vars"], "label": first["label"],
            "selected_arm": first["selected_arm"], "predicted": first["predicted"],
            "accepted": first["accepted"], "row_variables": first["row_variables"],
            "canonical_partition_match": first["canonical_partition_match"],
            "semantic_mismatch": first["semantic_mismatch"],
            "median_solve_ns": int(statistics.median(row["solve_ns"] for row in values)),
            "median_exact_check_ns": int(statistics.median(
                row["exact_check_ns"] for row in values)),
            "median_total_ns": int(statistics.median(row["total_ns"] for row in values)),
        })
    return result


def recompute_summaries(per_case: list[dict]) -> tuple[dict, dict, dict]:
    method_summary = {}
    for method in confirmation.METHODS:
        for split in confirmation.SPLITS:
            values = [row for row in per_case
                      if row["method"] == method and row["split"] == split]
            totals = [row["median_total_ns"] for row in values]
            method_summary[f"{method}/{split}"] = {
                "cases": len(values), "sequence_total_ns": sum(totals),
                "median_total_ns": statistics.median(totals),
                "p95_total_ns": confirmation.percentile(totals, .95),
                "maximum_total_ns": max(totals),
                "selection_counts": dict(sorted(
                    Counter(row["selected_arm"] for row in values).items())),
            }
    split_summary = {}
    for split in confirmation.SPLITS:
        fixed = {method: method_summary[f"{method}/{split}"]["sequence_total_ns"]
                 for method in ("set_source_anf", "cached_packed_source_anf")}
        best = min(fixed, key=fixed.get)
        adaptive = method_summary[f"adaptive_one_pass/{split}"]
        staged = method_summary[f"staged_restart/{split}"]
        split_summary[split] = {
            "best_fixed_arm": best, "best_fixed_total_ns": fixed[best],
            "adaptive_total_ns": adaptive["sequence_total_ns"],
            "adaptive_speedup_over_best_fixed": fixed[best] / adaptive["sequence_total_ns"],
            "adaptive_p95_speedup_over_set": (
                method_summary[f"set_source_anf/{split}"]["p95_total_ns"]
                / adaptive["p95_total_ns"]),
            "adaptive_speedup_over_restart": (
                staged["sequence_total_ns"] / adaptive["sequence_total_ns"]),
            "adaptive_selection_counts": adaptive["selection_counts"],
        }
    exact = all(row["predicted"] == row["label"]
                and row["canonical_partition_match"]
                and not row["semantic_mismatch"] for row in per_case)
    no_regret = all(split_summary[split]["adaptive_speedup_over_best_fixed"] >= 1 / 1.05
                    for split in confirmation.SPLITS)
    return method_summary, split_summary, {
        "exact": exact, "no_material_regret": no_regret,
        "second_machine_promotion": exact and no_regret,
    }


def main() -> None:
    run = load(RUN_DIR / "RUN.json")
    no_create = load(NO_CREATE_DIR / "RUN.json")
    watchdog = load(RUN_DIR / "WATCHDOG-RESULT.json")
    freeze = load(RUN_DIR / "TRANSPORT-FREEZE.json")
    validation = load(RUN_DIR / "evidence/run-output/REMOTE-VALIDATION.json")
    runtime = load(RUN_DIR / "evidence/run-output/RUNTIME.json")
    dependencies = load(RUN_DIR / "evidence/run-output/DEPENDENCIES.json")
    summary = load(STUDY / "summary.json")
    per_case = load(STUDY / "per_case.json")
    artifacts = load(STUDY / "manifest.json")
    documents = load(DATASET)
    measurements = [json.loads(line) for line in
                    (STUDY / "measurements.jsonl").read_text(encoding="utf-8").splitlines()]
    manifest = load(MANIFEST)
    authorization = load(AUTHORIZATION)

    require(no_create.get("creation_attempted") is False
            and no_create.get("pod_created") is False
            and no_create.get("uploaded_source_files") == 0
            and no_create.get("cleanup", {}).get("owned_pod_absent") is True
            and no_create.get("cleanup", {}).get("inventories") == {"v1": [], "v2": []},
            "package-v2 preflight failure is not a verified no-create outcome")
    require(run.get("status") == "complete"
            and run.get("creation_attempted") is True
            and run.get("creation_uncertain") is False
            and run.get("pod_created") is True
            and run.get("uploaded_source_files") == 16
            and run.get("automatic_replacement_queued") is False
            and run.get("creation_http_status") == 201
            and run.get("health_checks_before_upload") == 2
            and run.get("payload_attempts") == [{
                "attempt": 1,
                "checked_utc": run["payload_attempts"][0]["checked_utc"],
                "status": "accepted",
            }]
            and run.get("remote_progress", {}).get("returncode") == 0
            and run.get("remote_progress", {}).get("remote_status") == "complete",
            "C12 package-v2 run did not satisfy one-create transport invariants")
    resources = run.get("actual_resources", {})
    require(resources.get("rate_usd_per_hour") <= .25
            and resources.get("vcpu_count") == 2
            and resources.get("ram_gb") >= 4
            and resources.get("container_disk_gb") == 12
            and resources.get("pod_volume_gb") == 0
            and resources.get("ports") == ["8080/http"]
            and resources.get("cloud_evidence") == ["SECURE"]
            and 0 <= run.get("estimated_compute_cost_usd", -1) <= .05,
            "actual Runpod resources or cost exceeded the authorized scope")
    require(run.get("cleanup", {}).get("owned_pod_absent") is True
            and run.get("cleanup", {}).get("inventories") == {"v1": [], "v2": []}
            and watchdog.get("status") == "controller_cleanup_verified"
            and watchdog.get("errors") == [],
            "owned pod deletion was not independently observed by both roles")

    require(manifest.get("file_count") == 16 and manifest.get("bytes") == 368532
            and all(sha(ROOT / item["source"]) == item["sha256"]
                    for item in manifest["files"]),
            "local frozen package no longer matches its manifest")
    require(run.get("authorization_record_sha256") == sha(AUTHORIZATION)
            and authorization.get("upload_manifest_sha256") == sha(MANIFEST)
            and authorization.get("proposal_sha256") == sha(PROTOCOL)
            and authorization.get("local_validation_sha256") == sha(LOCAL_VALIDATION)
            and freeze.get("authorization_sha256") == sha(AUTHORIZATION)
            and freeze.get("manifest_sha256") == sha(MANIFEST)
            and freeze.get("protocol_sha256") == sha(PROTOCOL)
            and freeze.get("controller_sha256") == sha(CONTROLLER)
            and freeze.get("source_files") == 16
            and freeze.get("source_bytes") == 368532,
            "authorization or transport freeze does not bind the retrieved run")

    measured_hashes = {name: sha(STUDY / name)
                       for name in ("measurements.jsonl", "per_case.json", "summary.json")}
    require(artifacts.get("files_sha256") == measured_hashes,
            "retrieved scientific artifact hashes do not match")
    require(len(documents) == 40 and sha(DATASET) == confirmation.EXPECTED_DATASET_SHA256
            and len(measurements) == 2560 and len(per_case) == 160,
            "retrieved C12 result has the wrong dataset or row counts")
    keys = {(row["repetition"], row["method"], row["split"], row["case_id"])
            for row in measurements}
    require(len(keys) == 2560
            and all(row.get("schema") == confirmation.MEASUREMENT_SCHEMA
                    and type(row.get("solve_ns")) is int and row["solve_ns"] >= 0
                    and type(row.get("exact_check_ns")) is int and row["exact_check_ns"] >= 0
                    and row.get("total_ns") == row["solve_ns"] + row["exact_check_ns"]
                    for row in measurements),
            "retrieved timing rows are incomplete, duplicated, or malformed")

    semantics = expected_semantics(documents)
    for row in measurements:
        expected = semantics[(row["method"], row["split"], row["case_id"])]
        require(all(row[field] == value for field, value in expected.items()),
                "retrieved Linux semantics do not replay locally")
    rebuilt_per_case = recompute_per_case(measurements)
    require(rebuilt_per_case == per_case, "per-case medians do not reproduce from raw timings")
    method_summary, split_summary, criteria = recompute_summaries(rebuilt_per_case)
    require(summary.get("method_summary") == method_summary
            and summary.get("split_summary") == split_summary
            and summary.get("criteria") == criteria
            and summary.get("semantic_mismatches") == 0
            and summary.get("runtime", {}).get("python") == "3.13.15"
            and validation.get("confirmation_summary", {}).get("criteria") == criteria
            and runtime.get("source_files") == 16
            and runtime.get("runpod_pod_id") == run.get("pod_id")
            and dependencies.get("numpy") == "2.3.2",
            "retrieved summary, runtime, or dependencies do not independently reproduce")
    require(criteria == {"exact": True, "no_material_regret": True,
                         "second_machine_promotion": True},
            "second-machine promotion gate did not pass")

    first, retry = load(FIRST_VERIFY), load(RETRY_VERIFY)
    combined_cost = (first["estimated_compute_cost_usd"]
                     + retry["estimated_compute_cost_usd"]
                     + run["estimated_compute_cost_usd"])
    result = {
        "schema": "crse-runpod-c12-package-v2-final-verification/v1",
        "status": "pass", "complete": True,
        "scientific_confirmation_complete": True,
        "second_machine_promotion": True,
        "create_requests_this_authorization": 1,
        "automatic_replacement_queued": False,
        "pod_created": True, "pod_id": run["pod_id"],
        "uploaded_source_files": 16,
        "measurement_rows": 2560, "per_case_rows": 160,
        "semantic_rows_replayed": 160, "semantic_mismatches": 0,
        "criteria": criteria, "split_summary": split_summary,
        "owned_pod_absent_verified": True,
        "final_inventories": {"v1": [], "v2": []},
        "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "combined_c12_cloud_cost_usd": combined_cost,
        "elapsed_since_create_s": run["elapsed_since_create_s"],
        "manifest_sha256": sha(MANIFEST),
        "authorization_sha256": sha(AUTHORIZATION),
        "controller_sha256": sha(CONTROLLER),
        "run_sha256": sha(RUN_DIR / "RUN.json"),
        "evidence_zip_sha256": sha(RUN_DIR / "evidence.zip"),
        "watchdog_sha256": sha(RUN_DIR / "WATCHDOG-RESULT.json"),
    }
    OUTPUT.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
