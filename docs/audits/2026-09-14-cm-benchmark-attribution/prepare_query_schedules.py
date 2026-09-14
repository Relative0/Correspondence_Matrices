"""Freeze local prospective perturbations without executing benchmarks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from cmbench.biology_bnet import parse_bnet

SEED = "cm-biology-clamp-session-v1-20260914"


def schedules(functions, input_hash):
    targets = sorted(f.target for f in functions)
    if len(targets) < 3:
        raise ValueError("frozen corpus schedule requires at least three targets")
    queries, seen = [{}], {()}
    # Round-robin clamp cardinalities. Hash-sort targets for each proposal;
    # SHA parity independently chooses values. Duplicate queries are skipped.
    for attempt in range(10000):
        prefix = f"{SEED}:{input_hash}:{attempt}:"
        selected = sorted(targets, key=lambda t: hashlib.sha256((prefix + t).encode()).digest())[:1 + attempt % 3]
        query = {t: hashlib.sha256((prefix + "value:" + t).encode()).digest()[0] % 2 for t in sorted(selected)}
        key = tuple(query.items())
        if key not in seen:
            seen.add(key)
            queries.append(query)
        if len(queries) == 64:
            return queries
    raise ValueError("could not construct 64 distinct perturbations")


def main():
    controls = json.loads((HERE / "LOCAL_CONTROL_RESULTS.json").read_text())
    models = []
    for case in controls["cases"]:
        source = HERE / "control-inputs" / (case["model_id"] + ".bnet")
        if hashlib.sha256(source.read_bytes()).hexdigest() != case["bnet_sha256"]:
            raise ValueError("model bytes differ from controls")
        queries = schedules(parse_bnet(source.read_text(encoding="utf-8")), case["bnet_sha256"])
        encoded = json.dumps(queries, sort_keys=True, separators=(",", ":")).encode()
        models.append({"model_id": case["model_id"], "input_sha256": case["bnet_sha256"],
                       "cluster_id": case["cluster_id"], "queries": queries,
                       "query_schedule_sha256": hashlib.sha256(encoded).hexdigest()})
    result = {"schema": "cm-biology-query-schedules/v1", "seed": SEED,
              "status": "prospective_not_executed", "semantics": "clamp",
              "session_prefix_lengths": [1, 8, 64], "models": models,
              "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (HERE / "QUERY_SCHEDULES.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
