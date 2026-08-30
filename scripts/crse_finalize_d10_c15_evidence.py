"""Add bounded source fingerprints and immutable file manifests to retained runs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = {
    "d10-rule-engine-windows-20260830-002": [
        "cm_expr_serde.py", "cm_exprlib.py", "bitset_backend.py",
        "cmbench/recognition/d10_rule_engine.py",
        "cmbench/recognition/d10_rule_experiment.py",
        "cmbench/recognition/features.py", "cmbench/recognition/portfolio.py",
        "cmbench/recognition/teacher.py",
        "cmbench/recognition/yosys_composed_holdout_data.py",
        "scripts/cm_recognition_d10_rule_engine.py",
        "scripts/crse_d10_rule_engine_verify.py",
    ],
    "c15-exact-cm-gf2-windows-20260830-001": [
        "cm_expr_serde.py", "cm_exprlib.py",
        "cmbench/recognition/gf2_decomposition.py",
        "cmbench/recognition/gf2_decomposition_experiment.py",
        "cmbench/recognition/natural_decomposition.py",
        "cmbench/recognition/source_anf_hybrid.py",
        "cmbench/recognition/bdd_ordering.py",
        "cmbench/recognition/portfolio.py",
        "cmbench/recognition/yosys_composed_holdout_data.py",
        "scripts/cm_recognition_exact_gf2.py",
        "scripts/crse_exact_gf2_verify.py",
    ],
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def main() -> None:
    for run_id, sources in RUNS.items():
        run = ROOT / "docs/recognition/runs" / run_id
        if not run.is_dir():
            raise SystemExit(f"missing run {run_id}")
        fingerprints = {source: digest(ROOT / source) for source in sources}
        write_new(run / "source_fingerprints.json", {
            "schema": "crse-post-run-source-fingerprints/v1", "run_id": run_id,
            "capture": "immediately-after-retained-local-run-before-core-source-changes",
            "files": fingerprints,
            "payload_sha256": hashlib.sha256(json.dumps(fingerprints, sort_keys=True,
                separators=(",", ":")).encode("utf-8")).hexdigest(),
        })
        files = []
        for path in sorted(run.iterdir(), key=lambda item: item.name):
            if path.is_file() and path.name != "manifest.json":
                files.append({"path": path.name, "bytes": path.stat().st_size,
                              "sha256": digest(path)})
        write_new(run / "manifest.json", {"schema": "crse-bounded-run-manifest/v1",
            "run_id": run_id, "files": files,
            "payload_sha256": hashlib.sha256(json.dumps(files, sort_keys=True,
                separators=(",", ":")).encode("utf-8")).hexdigest()})
        print(json.dumps({"run_id": run_id, "source_files": len(sources),
                          "evidence_files": len(files)}, sort_keys=True))


if __name__ == "__main__":
    main()
