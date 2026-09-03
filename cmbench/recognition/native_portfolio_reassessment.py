"""Versioned no-training reassessment after native exact-portfolio closure."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
from typing import Any

from cmbench.comparative.gf2_native_portfolio_experiment import METHODS
from cmbench.recognition.neural_reassessment import (
    DEVELOPMENT_HEADROOM_GATE,
    PROSPECTIVE_CHARGED_GATE,
    canonical,
    file_sha256,
    read_json,
    verify_development_artifact as verify_prior_reassessment,
)
from scripts.crse_native_portfolio_development_verify import verify_run


ROOT = Path(__file__).resolve().parents[2]
PRIOR_RUN = ROOT / "docs/recognition/runs/neural-architecture-reassessment-development-20260902-001"
NATIVE_RUN = ROOT / "docs/recognition/runs/native-portfolio-development-20260903-001"
ASSESSMENT_SCHEMA = "crse-neural-architecture-reassessment/native-portfolio-v2"
LABEL_SCHEMA = "crse-exact-backend-development-labels/native-portfolio-v2"
ARTIFACT_SCHEMA = "crse-neural-native-portfolio-reassessment-artifacts/v1"
VERIFICATION_SCHEMA = "crse-neural-native-portfolio-reassessment-independent-verification/v1"
SOURCE_PATHS = (
    "cmbench/comparative/gf2_native_portfolio_experiment.py",
    "cmbench/recognition/native_portfolio_reassessment.py",
    "cmbench/recognition/neural_reassessment.py",
    "scripts/crse_native_portfolio_development_verify.py",
    "scripts/crse_neural_native_portfolio_reassessment_verify.py",
    "scripts/cm_neural_native_portfolio_reassessment.py",
)


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def _write_text(path: Path, value: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(value)


def _load_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    prior_verification = verify_prior_reassessment(PRIOR_RUN)
    stored_prior = read_json(PRIOR_RUN / "independent_verification.json")
    if prior_verification != stored_prior:
        raise ValueError("prior reassessment verification drift")
    native_verification = verify_run(NATIVE_RUN)
    stored_native = read_json(NATIVE_RUN / "independent_verification.json")
    if native_verification != stored_native:
        raise ValueError("native portfolio verification drift")
    return (
        read_json(PRIOR_RUN / "assessment.json"),
        read_json(NATIVE_RUN / "results.json"),
        native_verification,
    )


def build_assessment() -> dict[str, Any]:
    prior, native, native_verification = _load_inputs()
    if (
        native.get("status") != "complete"
        or tuple(native.get("methods", ())) != METHODS
        or native.get("dataset", {}).get("classification")
        != "development_exposed_c36_not_confirmation"
    ):
        raise ValueError("native portfolio is incomplete or stale")
    summary = native.get("summary", {})
    totals = summary.get("q64_accounted_total_ns", {})
    if set(totals) != set(METHODS):
        raise ValueError("native portfolio method totals are incomplete")
    best = min(METHODS, key=lambda method: (totals[method], method))
    oracle = summary.get("per_case_oracle_total_ns")
    if type(oracle) is not int or oracle <= 0:
        raise ValueError("native portfolio oracle is invalid")
    headroom = totals[best] / oracle
    if (
        best != summary.get("best_fixed_method")
        or not math.isclose(
            headroom, summary.get("oracle_speedup_over_best_fixed", 0.0),
            rel_tol=1e-12)
    ):
        raise ValueError("native portfolio economics do not recompute")
    winners = summary.get("per_case_winners", {})
    counts = dict(sorted(Counter(winners.values()).items()))
    if len(winners) != 18 or counts != summary.get("per_case_winner_counts"):
        raise ValueError("native portfolio labels are incomplete")
    recognition_ns = prior["economics"]["charged_boundary"][
        "historical_feature_or_recognition_ns_per_case"]
    charged_ns = 18 * recognition_ns
    charged_upper = totals[best] / (oracle + charged_ns)
    training_allowed = headroom >= DEVELOPMENT_HEADROOM_GATE
    if training_allowed:
        raise ValueError("unexpected native selector headroom requires a new protocol")
    return {
        "schema": ASSESSMENT_SCHEMA,
        "status": "complete",
        "classification": "development_only_exposed_c36_no_training",
        "supersedes_for_current_decision": prior["schema"],
        "evidence": {
            "prior_reassessment": {
                "path": PRIOR_RUN.relative_to(ROOT).as_posix(),
                "assessment_sha256": file_sha256(PRIOR_RUN / "assessment.json"),
                "manifest_sha256": file_sha256(PRIOR_RUN / "manifest.json"),
                "verification_sha256": file_sha256(PRIOR_RUN / "independent_verification.json"),
            },
            "native_portfolio": {
                "path": NATIVE_RUN.relative_to(ROOT).as_posix(),
                "results_sha256": native_verification["results_sha256"],
                "manifest_sha256": native_verification["manifest_sha256"],
                "verification_sha256": file_sha256(NATIVE_RUN / "independent_verification.json"),
            },
        },
        "labels": {
            "schema": LABEL_SCHEMA,
            "dataset_sha256": native["dataset"]["sha256"],
            "cases": 18,
            "methods": list(METHODS),
            "counts": counts,
            "complete_current_portfolio_in_one_run": True,
            "source_closed_and_independently_verified": True,
            "training_label_ready": True,
            "training_eligible": False,
            "reason": "all exposed cases select one fixed native method; there is no decision to learn",
        },
        "economics": {
            "development_headroom_gate": DEVELOPMENT_HEADROOM_GATE,
            "prospective_charged_gate": PROSPECTIVE_CHARGED_GATE,
            "best_fixed_method": best,
            "best_fixed_ns": totals[best],
            "oracle_ns": oracle,
            "gross_headroom_ns": totals[best] - oracle,
            "gross_headroom_speedup": headroom,
            "historical_feature_or_recognition_ns_total": charged_ns,
            "optimistic_feature_only_charged_speedup": charged_upper,
            "model_inference_ns_assumed": 0,
            "verification_ns_assumed": 0,
            "fallback_ns_assumed": 0,
        },
        "decision": {
            "training_allowed": False,
            "training_performed": False,
            "advice_enabled": False,
            "abstention": "all cases",
            "exact_fallback": "unchanged exact path",
            "prospective_confirmation_allowed": False,
            "prospective_data_consumed": False,
            "production_write": False,
            "production_promotion": False,
            "reason": (
                "the source-closed native portfolio has exactly 1.000000x exposed-development "
                "oracle headroom"
            ),
        },
    }


def render_report(assessment: dict[str, Any]) -> str:
    economics = assessment["economics"]
    labels = assessment["labels"]
    return "\n".join((
        "# Neural readiness update after native portfolio closure",
        "",
        "Status: **training and prospective confirmation remain stopped**",
        "",
        f"All {labels['cases']} exposed cases select `{economics['best_fixed_method']}`. "
        f"The best fixed total and per-case oracle are both "
        f"{economics['best_fixed_ns']:,} ns, giving "
        f"{economics['gross_headroom_speedup']:.6f}x gross headroom.",
        "",
        f"Charging only the historical feature allowance gives an optimistic upper bound "
        f"of {economics['optimistic_feature_only_charged_speedup']:.6f}x.",
        "",
        "No model was trained, no prospective data was consumed, and no production route "
        "or backend was promoted.",
        "",
    ))


def create_development_artifact(output: Path) -> dict[str, Any]:
    output = output.resolve()
    if not output.is_relative_to(ROOT.resolve()):
        raise ValueError("reassessment output escaped the project")
    output.mkdir(parents=True, exist_ok=False)
    assessment = build_assessment()
    _write_json(output / "assessment.json", assessment)
    _write_json(output / "labels.json", assessment["labels"])
    _write_text(output / "report.md", render_report(assessment))
    _write_json(output / "environment.json", {
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "classification": "local_development_only",
    })
    artifacts = {
        name: {"bytes": (output / name).stat().st_size,
               "sha256": file_sha256(output / name)}
        for name in ("assessment.json", "labels.json", "report.md", "environment.json")
    }
    sources = {}
    for relative in SOURCE_PATHS:
        path = ROOT.joinpath(*Path(relative).parts)
        if not path.is_file():
            raise FileNotFoundError(relative)
        sources[relative] = {"bytes": path.stat().st_size, "sha256": file_sha256(path)}
    inputs = {}
    for prefix, run in (("prior", PRIOR_RUN), ("native", NATIVE_RUN)):
        for name in ("results.json", "manifest.json", "independent_verification.json"):
            path = run / name
            if path.is_file():
                inputs[f"{prefix}/{name}"] = {
                    "path": path.relative_to(ROOT).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": file_sha256(path),
                }
        assessment_path = run / "assessment.json"
        if assessment_path.is_file():
            inputs[f"{prefix}/assessment.json"] = {
                "path": assessment_path.relative_to(ROOT).as_posix(),
                "bytes": assessment_path.stat().st_size,
                "sha256": file_sha256(assessment_path),
            }
    _write_json(output / "manifest.json", {
        "schema": ARTIFACT_SCHEMA,
        "artifacts": artifacts,
        "sources": sources,
        "inputs": inputs,
    })
    return assessment


def verify_development_artifact(run: Path) -> dict[str, Any]:
    run = run.resolve()
    manifest = read_json(run / "manifest.json")
    if manifest.get("schema") != ARTIFACT_SCHEMA:
        raise ValueError("invalid native reassessment manifest schema")
    for group, base in (
        (manifest.get("artifacts"), run),
        (manifest.get("sources"), ROOT),
    ):
        if type(group) is not dict or not group:
            raise ValueError("native reassessment manifest group is empty")
        for relative, identity in group.items():
            path = base.joinpath(*Path(relative).parts)
            if (
                not path.is_file()
                or path.stat().st_size != identity.get("bytes")
                or file_sha256(path) != identity.get("sha256")
            ):
                raise ValueError(f"native reassessment hash mismatch: {relative}")
    for name, identity in manifest.get("inputs", {}).items():
        path = ROOT.joinpath(*Path(identity.get("path", "")).parts)
        if (
            not path.is_file()
            or path.stat().st_size != identity.get("bytes")
            or file_sha256(path) != identity.get("sha256")
        ):
            raise ValueError(f"native reassessment input mismatch: {name}")
    expected = build_assessment()
    actual = read_json(run / "assessment.json")
    if canonical(expected) != canonical(actual):
        raise ValueError("native reassessment replay mismatch")
    if canonical(actual["labels"]) != canonical(read_json(run / "labels.json")):
        raise ValueError("native reassessment label mismatch")
    return {
        "schema": VERIFICATION_SCHEMA,
        "status": "verified",
        "assessment_sha256": file_sha256(run / "assessment.json"),
        "manifest_sha256": file_sha256(run / "manifest.json"),
        "backend_labels_replayed": 18,
        "training_performed": False,
        "prospective_data_consumed": False,
        "production_write": False,
        "production_promotion": False,
    }
