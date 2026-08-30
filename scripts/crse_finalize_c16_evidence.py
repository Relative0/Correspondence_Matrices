"""Add bounded source fingerprints and an immutable manifest to the C16 run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "c16-gf2-screened-tail-windows-20260830-001"
SOURCES = (
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cmbench/recognition/gf2_decomposition.py",
    "cmbench/recognition/gf2_decomposition_experiment.py",
    "cmbench/recognition/gf2_screening_experiment.py",
    "cmbench/recognition/natural_decomposition.py",
    "cmbench/recognition/portfolio.py",
    "cmbench/recognition/source_anf_hybrid.py",
    "cmbench/recognition/yosys_composed_holdout_data.py",
    "cmbench/recognition/yosys_human_decomposition_data.py",
    "docs/recognition/source_fixtures/yosys-bench-human-decomposition-20260830/SOURCE_MANIFEST.json",
    "scripts/cm_recognition_gf2_screening.py",
    "scripts/crse_gf2_screening_verify.py",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def main() -> None:
    run = ROOT / "docs/recognition/runs" / RUN_ID
    fingerprints = {source: digest(ROOT / source) for source in SOURCES}
    write_new(run / "source_fingerprints.json", {
        "schema": "crse-post-run-source-fingerprints/v1",
        "run_id": RUN_ID,
        "capture": "immediately-after-retained-local-run-before-core-source-changes",
        "files": fingerprints,
        "payload_sha256": hashlib.sha256(json.dumps(
            fingerprints, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest(),
    })
    files = []
    for path in sorted(run.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "manifest.json":
            files.append({"path": path.name, "bytes": path.stat().st_size,
                          "sha256": digest(path)})
    write_new(run / "manifest.json", {
        "schema": "crse-bounded-run-manifest/v1",
        "run_id": RUN_ID,
        "files": files,
        "payload_sha256": hashlib.sha256(json.dumps(
            files, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest(),
    })
    print(json.dumps({"run_id": RUN_ID, "source_files": len(SOURCES),
                      "evidence_files": len(files)}, sort_keys=True))


if __name__ == "__main__":
    main()
