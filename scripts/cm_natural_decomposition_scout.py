"""Bounded read-only scout for exact XOR-decomposable natural EPFL cones."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.blif import parse_blif
from cmbench.recognition.natural_decomposition import analyze_decomposition, semantic_variables

EPFL_ROOT = ROOT / "external" / "epfl-benchmarks"
EPFL_COMMIT = "0060e156826e733d69bf5b3322d1bdd0d03a1f9a"
EPFL_URL = "https://github.com/lsils/benchmarks.git"


@dataclass(frozen=True)
class ScoutConfig:
    min_support: int = 4
    max_support: int = 10
    max_source_nodes: int = 128
    max_candidates_per_file: int = 256
    max_seconds: float = 120.0

    def validate(self):
        if (not 2 <= self.min_support <= self.max_support <= 10
                or not 16 <= self.max_source_nodes <= 256
                or not 16 <= self.max_candidates_per_file <= 512
                or not 0 < self.max_seconds <= 120):
            raise ValueError("invalid natural decomposition scout bounds")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files() -> list[tuple[str, str, Path]]:
    result = []
    for category in ("arithmetic", "random_control"):
        for path in sorted((EPFL_ROOT / category).glob("*.blif")):
            result.append(("original", path.stem, path))
    for variant in ("depth", "size"):
        for path in sorted((EPFL_ROOT / "best_results" / variant).glob("*.blif")):
            circuit = path.name.split(f"_{variant}_", 1)[0]
            result.append((variant, circuit, path))
    return result


def quantile_indices(length: int, cap: int) -> list[int]:
    if length <= cap:
        return list(range(length))
    return sorted(set(round(slot * (length - 1) / (cap - 1)) for slot in range(cap)))


def run(config: ScoutConfig, progress=print):
    config.validate()
    started = time.monotonic()
    rows = []
    files = []
    for variant, circuit, path in source_files():
        if time.monotonic() - started >= config.max_seconds:
            raise TimeoutError("natural decomposition scout wall budget exhausted")
        progress(f"Scanning {variant}/{circuit}")
        try:
            netlist = parse_blif(path)
        except (ValueError, TypeError, RecursionError) as exc:
            files.append({"variant": variant, "circuit": circuit,
                "source_path": str(path.relative_to(ROOT)).replace("\\", "/"), "source_sha256": sha(path),
                "eligible_candidates": 0, "scouted_candidates": 0, "retained_rows": 0,
                "outcomes": {"file_rejected": 1}, "rejection": str(exc)})
            continue
        candidates = sorted(netlist.candidate_metadata(min_support=config.min_support,
            max_support=config.max_support, max_source_nodes=config.max_source_nodes),
            key=lambda item: (item.source_nodes, item.depth, item.node))
        indices = quantile_indices(len(candidates), config.max_candidates_per_file)
        counts = Counter()
        selected_rows = []
        for index in indices:
            if time.monotonic() - started >= config.max_seconds:
                raise TimeoutError("natural decomposition scout wall budget exhausted")
            metadata = candidates[index]
            try:
                bits, support = netlist.packed_value(metadata.node)
                if len(support) != len(metadata.support):
                    raise ValueError("support identity mismatch")
                live = semantic_variables(bits, len(support))
                if live != tuple(range(len(support))):
                    counts["semantic_support_shrink"] += 1
                    continue
                analysis = analyze_decomposition(bits, len(support))
                counts["positive" if analysis.decomposable else "negative"] += 1
                row = {"schema": "crse-natural-decomposition-scout-row/v1",
                    "variant": variant, "circuit": circuit,
                    "source_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "source_sha256": sha(path), "root": metadata.node,
                    "support": list(support), "n_vars": len(support),
                    "source_nodes": metadata.source_nodes, "source_edges": metadata.source_edges,
                    "depth": metadata.depth, "decomposable": analysis.decomposable,
                    "components": [list(component) for component in analysis.components],
                    "row_variables": list(analysis.row_variables) if analysis.row_variables is not None else None,
                    "column_variables": list(analysis.column_variables) if analysis.column_variables is not None else None,
                    "truth_sha256": hashlib.sha256(bits.to_bytes(max(1, (1 << len(support)) // 8), "little")).hexdigest()}
                rows.append(row)
                selected_rows.append(row)
            except (ValueError, TypeError, RecursionError):
                counts["rejected"] += 1
        files.append({"variant": variant, "circuit": circuit,
            "source_path": str(path.relative_to(ROOT)).replace("\\", "/"), "source_sha256": sha(path),
            "eligible_candidates": len(candidates), "scouted_candidates": len(indices),
            "retained_rows": len(selected_rows), "outcomes": dict(counts)})
    totals = Counter("positive" if row["decomposable"] else "negative" for row in rows)
    by_variant = defaultdict(Counter)
    by_circuit = defaultdict(Counter)
    for row in rows:
        label = "positive" if row["decomposable"] else "negative"
        by_variant[row["variant"]][label] += 1
        by_circuit[row["circuit"]][label] += 1
    return {"schema": "crse-natural-decomposition-scout/v1", "status": "complete",
        "config": asdict(config), "source": {"name": "EPFL combinational benchmark suite",
            "commit": EPFL_COMMIT, "url": EPFL_URL, "license": "MIT License",
            "local_root": str(EPFL_ROOT.relative_to(ROOT)).replace("\\", "/")},
        "selection": "all candidates when <=cap, otherwise deterministic structural quantiles before labels",
        "files": files, "rows": rows, "totals": dict(totals),
        "by_variant": {key: dict(value) for key, value in sorted(by_variant.items())},
        "by_circuit": {key: dict(value) for key, value in sorted(by_circuit.items())},
        "wall_seconds": time.monotonic() - started}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-candidates-per-file", type=int, default=256)
    args = parser.parse_args(argv)
    config = ScoutConfig(max_candidates_per_file=args.max_candidates_per_file)
    result = run(config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
    print(json.dumps({"status": result["status"], "totals": result["totals"],
                      "by_variant": result["by_variant"], "wall_seconds": result["wall_seconds"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
