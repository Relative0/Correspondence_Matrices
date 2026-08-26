#!/usr/bin/env python3
"""Frozen k=13..15 selector study with tuning/validation separation.

The tuning side is a deterministic, balanced synthetic corpus. The external
validation side is the exact-support k=13..15 slice of the frozen EPFL corpus.
EPFL influenced the earlier threshold decision, so it is explicitly labelled
reused validation rather than untouched held-out evidence. Both raw AST and
CM-node flat/words kernels are measured by the deep-audit protocol.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import cm_deep_performance_audit as audit  # noqa: E402
from scripts.cm_benchmark_provenance import capture_source_snapshot  # noqa: E402
from cmbench.backends.bitset_engine import WORDS_AUTO_MIN_VARS  # noqa: E402

EPFL = ROOT / "deliverables_n22_24/CM_gap_epfl_corpus_2026_08_03.jsonl"
GAP_K = (13, 14, 15)
GENERATOR_VERSION = "selector-gap-2026-08-24.1"
SOURCE_PATHS = audit.SOURCE_PATHS + ("scripts/cm_selector_gap_study.py",)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _records(path: Path) -> list[dict]:
    return [
        row for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
        if "expression_v2" in row
    ]


def _build_corpus(path: Path, per_cell: int, max_attempts: int) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    spec = importlib.util.spec_from_file_location(
        "b2_gap_generator", ROOT / "deliverables_n22_24/cm_b2_wrapper_boundary_2026_08_03.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.STRATA = GAP_K
    module.GENERATOR_VERSION = GENERATOR_VERSION
    records, rejections = module.build_corpus(per_cell, max_attempts)
    for record in records:
        record["id"] = record["id"].replace("b2-", "selector-gap-", 1)
        record["generator_version"] = GENERATOR_VERSION
    metadata = {
        "record_type": "selector_gap_corpus_meta",
        "generator_version": GENERATOR_VERSION,
        "strata": GAP_K,
        "per_family_shape_cell": per_cell,
        "rejection_stats": rejections,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n")
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"Wrote {path} ({len(records)} formulas, sha256={_sha(path)})")


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _acceptance(selector: list[dict]) -> dict:
    current = [row for row in selector if row["is_current_policy"]]
    checks = []
    for row in current:
        checks.append({
            "arm": row["arm"],
            "role": row["role"],
            "n": row["n"],
            "regret_geomean": row["regret_geomean"],
            "regret_max": row["regret_max"],
            "catastrophic_ge_2_count": row["catastrophic_ge_2_count"],
            "pass": row["regret_geomean"] <= 1.10 and row["catastrophic_ge_2_count"] == 0,
        })
    return {
        "gate": {"regret_geomean_max": 1.10, "catastrophic_ge_2_count": 0},
        "checks": checks,
        "pass": len(checks) == 4 and all(check["pass"] for check in checks),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--build-corpus", action="store_true")
    parser.add_argument("--per-cell", type=int, default=2)
    parser.add_argument("--max-attempts", type=int, default=10000)
    parser.add_argument("--output-prefix", type=Path)
    parser.add_argument("--prep-repetitions", type=int, default=3)
    parser.add_argument("--kernel-rounds", type=int, default=5)
    parser.add_argument("--max-kernel-temporary-bytes", type=int, default=1 << 24)
    args = parser.parse_args()
    corpus = args.corpus if args.corpus.is_absolute() else ROOT / args.corpus
    if args.build_corpus:
        _build_corpus(corpus, args.per_cell, args.max_attempts)
    if args.output_prefix is None:
        return 0
    if not corpus.is_file():
        parser.error(f"missing corpus: {corpus}")
    prefix = args.output_prefix if args.output_prefix.is_absolute() else ROOT / args.output_prefix
    paths = {
        "raw": prefix.with_name(prefix.name + "_raw.csv"),
        "selector": prefix.with_name(prefix.name + "_selector.csv"),
        "audit": prefix.with_name(prefix.name + "_audit.json"),
        "environment": prefix.with_name(prefix.name + "_environment.json"),
    }
    snapshot_dir = prefix.with_name(prefix.name + "_source_snapshot")
    existing = [str(path) for path in (*paths.values(), snapshot_dir) if path.exists()]
    if existing:
        parser.error("refusing to overwrite: " + ", ".join(existing))
    prefix.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    tuning = _records(corpus)
    validation_reused = [
        record for record in _records(EPFL)
        if int(record.get("sem_support_size") or record.get("live_k")) in GAP_K
    ]
    for index, record in enumerate(tuning, 1):
        row = audit._measure_record(
            "selector_gap", record, args.prep_repetitions, args.kernel_rounds,
            args.max_kernel_temporary_bytes,
        )
        row["corpus"] = "synthetic_gap"
        row["role"] = "tuning"
        rows.append(row)
        print(f"tuning {index}/{len(tuning)} {row['id']}", flush=True)
    for index, record in enumerate(validation_reused, 1):
        row = audit._measure_record(
            "epfl", record, args.prep_repetitions, args.kernel_rounds,
            args.max_kernel_temporary_bytes,
        )
        row["corpus"] = "epfl_gap"
        row["role"] = "validation_reused"
        rows.append(row)
        print(
            f"validation_reused {index}/{len(validation_reused)} {row['id']}",
            flush=True,
        )

    selector = audit._selector_summary(rows, "raw") + audit._selector_summary(rows, "cm")
    acceptance = _acceptance(selector)
    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "words_auto_min_vars": WORDS_AUTO_MIN_VARS,
        "protocol": (
            "paired alternating medians; synthetic tuning and reused EPFL "
            "selection validation; thresholds frozen before this timing run"
        ),
        "validation_status": (
            "EPFL influenced earlier selector selection and is not untouched held-out data"
        ),
        "corpus_sha256": {"synthetic_gap": _sha(corpus), "epfl": _sha(EPFL)},
        "counts": {
            "tuning": len(tuning),
            "validation_reused": len(validation_reused),
        },
    }
    environment["source_snapshot"] = capture_source_snapshot(
        ROOT, snapshot_dir, SOURCE_PATHS
    )
    _write_csv(paths["raw"], rows)
    _write_csv(paths["selector"], selector)
    paths["environment"].write_text(json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["audit"].write_text(json.dumps({"environment": environment, "acceptance": acceptance}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"paths": {key: str(value) for key, value in paths.items()}, "acceptance": acceptance}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
