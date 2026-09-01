"""Independent integrity, phase-order, and exactness verifier for C19."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.gf2_task_dispatcher import EXHAUSTIVE, SCREENED
from cmbench.recognition.gf2_work_policy import (
    cheap_truth_features,
    evaluate_tree,
    fit_cost_tree,
    fixed_tree,
    freeze_policy,
    load_policy,
)
from cmbench.recognition.gf2_work_policy_experiment import (
    CALIBRATION_METHODS,
    CANDIDATES,
    CONFIRMATION_METHODS,
    C19Config,
    _candidate_summary,
    _confirmation_summary,
    _fit_rows,
    _functional,
)

DATASET_PATH = ROOT / "docs/recognition/c19_logikbench_small_cone_dataset.json"
CORPUS_VERIFICATION_PATH = ROOT / "docs/recognition/c19_logikbench_small_cone_verification.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_arm(method: str, case: dict, trees: dict[str, dict], selected: str) -> str:
    if method == "direct_exhaustive":
        return EXHAUSTIVE
    if method == "direct_screened":
        return SCREENED
    if method == "c17_wrapper":
        return EXHAUSTIVE if case["n_vars"] <= 3 else SCREENED
    candidate = {
        "direct_n3": "fixed_n3",
        "direct_n4": "fixed_n4",
        "c19_selected": selected,
    }.get(method, method)
    features = cheap_truth_features(int(case["truth_bits_hex"], 16), case["n_vars"])
    return evaluate_tree(trees[candidate], features)


def check_rows(
    rows: list[dict], *, cases: dict[str, dict], methods: tuple[str, ...], rounds: int,
    expected_best: dict[str, dict | None], trees: dict[str, dict], selected: str,
) -> None:
    expected_count = len(cases) * len(methods) * rounds
    if len(rows) != expected_count:
        raise ValueError(f"C19 measurement count mismatch: {len(rows)} != {expected_count}")
    identities: set[tuple[str, str, int]] = set()
    for row in rows:
        identity = (row.get("case_id"), row.get("method"), row.get("round"))
        if identity in identities or row.get("method") not in methods:
            raise ValueError("C19 duplicate or unknown measurement")
        identities.add(identity)
        case = cases.get(row["case_id"])
        if case is None:
            raise ValueError("C19 measurement references an unknown case")
        best = expected_best[row["case_id"]]
        features = cheap_truth_features(int(case["truth_bits_hex"], 16), case["n_vars"])
        if (
            row.get("split") != case["split"]
            or row.get("cluster_id") != case["cluster_id"]
            or row.get("n_vars") != case["n_vars"]
            or row.get("features") != features
            or row.get("selected_arm") != expected_arm(row["method"], case, trees, selected)
            or row.get("best_artifact_sha256") != (best["payload_sha256"] if best else None)
            or row.get("semantic_mismatches") != 0
            or row.get("artifact_mismatches") != 0
            or any(type(row.get(field)) is not int or row[field] < 1
                   for field in ("analysis_ns", "exact_check_ns", "total_ns"))
            or type(row.get("decision_ns")) is not int
            or row["decision_ns"] < 0
        ):
            raise ValueError("C19 measured exactness, selection, or metadata mismatch")
        if row["method"] != "c17_wrapper":
            if row["total_ns"] != row["decision_ns"] + row["analysis_ns"] + row["exact_check_ns"]:
                raise ValueError("C19 direct timing invariant mismatch")
        elif row["total_ns"] <= row["decision_ns"]:
            raise ValueError("C19 wrapper timing invariant mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify C19 cheap exact GF(2) work policy")
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest, spec, result = load(run / "manifest.json"), load(run / "run_spec.json"), load(run / "results.json")

    if sha256(DATASET_PATH) != manifest["dataset_sha256"] or spec["dataset_sha256"] != manifest["dataset_sha256"]:
        raise ValueError("C19 frozen dataset fingerprint mismatch")
    for name, digest in manifest["sources"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"C19 source fingerprint mismatch: {name}")
    for name, digest in manifest["artifacts"].items():
        if sha256(run / name) != digest:
            raise ValueError(f"C19 artifact fingerprint mismatch: {name}")

    corpus = load(CORPUS_VERIFICATION_PATH)
    if (
        corpus.get("status") != "verified"
        or corpus.get("cases_replayed") != 96
        or corpus.get("truth_or_metadata_mismatches") != 0
        or corpus.get("rtl_or_blif_fingerprint_mismatches") != 0
        or corpus.get("prior_truth_overlaps") != 0
        or corpus.get("split_cluster_overlap") != 0
        or corpus.get("confirmation_policy_refit_allowed") is not False
    ):
        raise ValueError("C19 source-corpus verification incomplete")

    dataset = load(DATASET_PATH)
    cases = dataset["cases"]
    by_split = {split: {case["case_id"]: case for case in cases if case["split"] == split}
                for split in ("development", "validation", "confirmation")}
    if {split: len(group) for split, group in by_split.items()} != {
        "development": 48, "validation": 24, "confirmation": 24,
    }:
        raise ValueError("C19 split size mismatch")
    clusters = {split: {case["cluster_id"] for case in group.values()} for split, group in by_split.items()}
    if any(clusters[left] & clusters[right]
           for left, right in (("development", "validation"), ("development", "confirmation"),
                               ("validation", "confirmation"))):
        raise ValueError("C19 source cluster leaked across phases")

    config = C19Config(**spec["config"])
    config.validate()
    functional, expected_best = _functional(cases, config)
    if load(run / "functional.json") != functional or not functional["all_exact"]:
        raise ValueError("C19 functional replay mismatch")

    development_rows = load_rows(run / "development_measurements.jsonl")
    fit_rows = _fit_rows(development_rows)
    stump, _ = fit_cost_tree(fit_rows, 1)
    depth2, _ = fit_cost_tree(fit_rows, 2)
    trees = {
        "always_exhaustive": {"kind": "leaf", "arm": EXHAUSTIVE},
        "fixed_n3": fixed_tree(3),
        "fixed_n4": fixed_tree(4),
        "learned_stump": stump,
        "learned_depth2": depth2,
    }
    check_rows(
        development_rows, cases=by_split["development"], methods=CALIBRATION_METHODS,
        rounds=config.rounds, expected_best=expected_best, trees=trees,
        selected="always_exhaustive",
    )

    validation_rows = load_rows(run / "validation_measurements.jsonl")
    validation_methods = (*CALIBRATION_METHODS, *CANDIDATES)
    check_rows(
        validation_rows, cases=by_split["validation"], methods=validation_methods,
        rounds=config.rounds, expected_best=expected_best, trees=trees,
        selected="always_exhaustive",
    )
    validation = _candidate_summary(validation_rows)
    if validation != result["validation"]["methods"]:
        raise ValueError("C19 validation summary recomputation mismatch")
    gate = spec["selection_gate"]
    eligible = [name for name in CANDIDATES
                if validation[name]["minimum_case_speedup_over_exhaustive"] >= gate["minimum_case_speedup_over_exhaustive"]
                and validation[name]["aggregate_speedup_over_exhaustive"] >= gate["aggregate_speedup_over_exhaustive"]]
    selected = max(eligible, key=lambda name: (validation[name]["aggregate_speedup_over_exhaustive"], name)) if eligible else "always_exhaustive"
    if eligible != result["validation"]["eligible_candidates"] or selected != result["policy"]["selected_candidate"]:
        raise ValueError("C19 validation selection mismatch")

    calibration_sha = hashlib.sha256(
        (run / "development_measurements.jsonl").read_bytes()
        + (run / "validation_measurements.jsonl").read_bytes()
    ).hexdigest()
    rebuilt_policy = freeze_policy(
        selected_candidate=selected, tree=trees[selected],
        dataset_sha256=manifest["dataset_sha256"], calibration_sha256=calibration_sha,
        development_rows=48, validation_rows=24, candidate_validation=validation,
    )
    policy = load_policy(run / "policy.json")
    if policy != rebuilt_policy or policy["policy_sha256"] != result["policy"]["policy_sha256"]:
        raise ValueError("C19 frozen policy reconstruction mismatch")
    freeze_event = load(run / "freeze_event.json")
    if freeze_event != {
        "schema": "crse-c19-policy-freeze-event/v1",
        "policy_sha256": policy["policy_sha256"],
        "confirmation_rows_existing_at_freeze": False,
        "confirmation_policy_refit_allowed": False,
    }:
        raise ValueError("C19 freeze event mismatch")

    confirmation_rows = load_rows(run / "confirmation_measurements.jsonl")
    check_rows(
        confirmation_rows, cases=by_split["confirmation"], methods=CONFIRMATION_METHODS,
        rounds=config.rounds, expected_best=expected_best, trees=trees, selected=selected,
    )
    confirmation = _confirmation_summary(confirmation_rows)
    if confirmation != result["confirmation"]["methods"]:
        raise ValueError("C19 confirmation summary recomputation mismatch")
    chosen = confirmation["c19_selected"]
    confirmation_gate = (
        chosen["minimum_case_speedup_over_exhaustive"] >= gate["minimum_case_speedup_over_exhaustive"]
        and chosen["aggregate_speedup_over_exhaustive"] >= gate["aggregate_speedup_over_exhaustive"]
    )
    if (
        result.get("status") != "complete"
        or result.get("semantic_or_artifact_mismatches") != 0
        or result["confirmation"].get("gate") is not confirmation_gate
        or result["claims"].get("learned_truth_values") is not False
        or result["claims"].get("exact_arm_selection_only") is not True
        or result["claims"].get("production_promotion") is not False
        or result["dataset"].get("confirmation_policy_refit") is not False
        or result["runpod"].get("used") is not False
        or result["runpod"].get("cost_usd") != 0.0
    ):
        raise ValueError("C19 final claim mismatch")

    verification = {
        "schema": "crse-c19-gf2-cheap-work-policy-verification/v1",
        "status": "verified",
        "functional_cases_replayed": 96,
        "development_rows_checked": len(development_rows),
        "validation_rows_checked": len(validation_rows),
        "confirmation_rows_checked": len(confirmation_rows),
        "source_fingerprints_checked": len(manifest["sources"]),
        "artifact_fingerprints_checked": len(manifest["artifacts"]),
        "corpus_source_replay_required_and_present": True,
        "split_cluster_overlap": 0,
        "policy_rebuilt_from_development_and_validation": True,
        "selected_candidate": selected,
        "selected_tree": policy["tree"],
        "validation_summary_recomputed": True,
        "confirmation_summary_recomputed": True,
        "semantic_or_artifact_mismatches": 0,
        "timings_rerun": False,
        "confirmation_policy_refit": False,
        "production_promotion": False,
    }
    with (run / "independent_verification.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
