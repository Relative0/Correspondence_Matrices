"""Independently verify the C38 Linux rebuild binding around a verified C37 run."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cm_c38_linux_replication import (
    EXPECTED_PARENT_DATASET_SHA256,
    EXPECTED_PARENT_DATASET_VERIFICATION_SHA256,
    EXPECTED_PARENT_FREEZE_SHA256,
    PARENT_DATASET,
    PARENT_DATASET_VERIFICATION,
    PARENT_FREEZE,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value: Any) -> None:
    with path.open("xb") as stream:
        stream.write(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")
            + b"\n"
        )


def restored_parent_dataset(child: dict[str, Any]) -> dict[str, Any]:
    restored = copy.deepcopy(child)
    provenance = restored["provenance"]
    provenance["freeze_path"] = provenance.pop("parent_c37_freeze_path")
    provenance["freeze_sha256"] = provenance.pop("parent_c37_freeze_sha256")
    provenance.pop("replication_rebinding_only")
    return restored


def restored_parent_verification(child: dict[str, Any]) -> dict[str, Any]:
    restored = copy.deepcopy(child)
    restored["dataset_sha256"] = restored.pop("parent_c37_dataset_sha256")
    restored["freeze_sha256"] = restored.pop("parent_c37_freeze_sha256")
    restored.pop("replication_rebinding_only")
    return restored


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    if not run_dir.is_relative_to(ROOT) or not run_dir.is_dir():
        raise ValueError("C38 run directory escaped the package root")

    result = load(run_dir / "results.json")
    c37_verification = load(run_dir / "independent_verification.json")
    binding = load(run_dir / "c38_runtime_binding.json")
    derived = binding["derived"]
    freeze_path = ROOT.joinpath(*Path(derived["freeze"]["path"]).parts)
    dataset_path = ROOT.joinpath(*Path(derived["dataset"]["path"]).parts)
    dataset_verification_path = ROOT.joinpath(
        *Path(derived["dataset_verification"]["path"]).parts
    )
    library_path = ROOT.joinpath(*Path(binding["native_library"]["path"]).parts)
    parent_freeze = load(PARENT_FREEZE)
    child_freeze = load(freeze_path)
    parent_dataset = load(PARENT_DATASET)
    child_dataset = load(dataset_path)
    parent_dataset_verification = load(PARENT_DATASET_VERIFICATION)
    child_dataset_verification = load(dataset_verification_path)

    failures = {
        "parent_identity_mismatches": int(
            sha256(PARENT_FREEZE) != EXPECTED_PARENT_FREEZE_SHA256
            or sha256(PARENT_DATASET) != EXPECTED_PARENT_DATASET_SHA256
            or sha256(PARENT_DATASET_VERIFICATION)
            != EXPECTED_PARENT_DATASET_VERIFICATION_SHA256
        ),
        "derived_identity_mismatches": sum(
            not path.is_file()
            or path.stat().st_size != identity["bytes"]
            or sha256(path) != identity["sha256"]
            for path, identity in (
                (freeze_path, derived["freeze"]),
                (dataset_path, derived["dataset"]),
                (dataset_verification_path, derived["dataset_verification"]),
                (library_path, binding["native_library"]),
            )
        ),
        "source_map_mismatches": int(child_freeze.get("sources") != parent_freeze.get("sources")),
        "dataset_rebinding_mismatches": int(
            restored_parent_dataset(child_dataset) != parent_dataset
        ),
        "verification_rebinding_mismatches": int(
            restored_parent_verification(child_dataset_verification)
            != parent_dataset_verification
        ),
        "freeze_binding_mismatches": int(
            child_freeze.get("status") != "frozen_before_dataset_and_timing"
            or child_freeze.get("parent_c37", {}).get("freeze_sha256")
            != EXPECTED_PARENT_FREEZE_SHA256
            or child_freeze.get("parent_c37", {}).get("dataset_sha256")
            != EXPECTED_PARENT_DATASET_SHA256
            or child_freeze.get("native_library", {}).get("sha256") != sha256(library_path)
            or child_freeze.get("native_library", {}).get("abi_version") != 1
            or child_freeze.get("native_library", {}).get("supports_multi_root") is not True
            or child_freeze.get("replication", {}).get("method_substitution") is not False
            or child_freeze.get("replication", {}).get("gate_refit") is not False
            or child_freeze.get("replication", {}).get("training") is not False
        ),
        "c37_verification_mismatches": int(
            c37_verification.get("status") != "verified"
            or c37_verification.get("raw_sessions_checked") != 954
            or c37_verification.get("single_root_queries_checked") != 44928
            or c37_verification.get("multi_root_output_queries_checked") != 48384
            or any(
                c37_verification.get(name) != 0
                for name in (
                    "artifact_mismatches", "source_mismatches", "binding_mismatches",
                    "native_mismatches", "structure_mismatches", "correctness_mismatches",
                    "native_identity_mismatches", "balance_mismatches", "summary_mismatches",
                    "decision_mismatches",
                )
            )
        ),
        "result_boundary_mismatches": int(
            result.get("status") != "complete"
            or result.get("config", {}).get("single_blocks") != 12
            or result.get("config", {}).get("multi_blocks") != 20
            or result.get("correctness", {}).get("canonical_delivery_mismatches") != 0
            or result.get("correctness", {}).get("single_root_exact_query_checks") != 44928
            or result.get("correctness", {}).get("multi_root_exact_output_query_checks") != 48384
            or result.get("decision", {}).get("training") is not False
            or result.get("decision", {}).get("policy_refit") is not False
            or result.get("decision", {}).get("gate_refit") is not False
            or result.get("decision", {}).get("production_promotion") is not False
        ),
    }
    if any(failures.values()):
        raise RuntimeError(f"C38 Linux replication verification failed: {failures}")
    verification = {
        "schema": "crse-c38-c37-native-linux-replication-independent-verification/v1",
        "status": "verified",
        "run_id": result["run_id"],
        "local_platform_validation_only": binding["local_platform_validation_only"],
        "compiler": binding["compiler"],
        "native_library_sha256": sha256(library_path),
        "c37_results_sha256": sha256(run_dir / "results.json"),
        "c37_independent_verification_sha256": sha256(
            run_dir / "independent_verification.json"
        ),
        "raw_sessions_checked": 954,
        "single_root_queries_checked": 44928,
        "multi_root_output_queries_checked": 48384,
        "all_predeclared_gates_passed": result["decision"]["all_predeclared_gates_passed"],
        "timing_gate_is_observational_not_verification_validity": True,
        "production_promotion": False,
        **failures,
    }
    write_new(run_dir / "c38_independent_verification.json", verification)
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
