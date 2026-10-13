"""Replay ordered output hashes, schedules, paired summaries, and source snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import cm_packed_mask_audit as audit


def verify(output):
    frozen = json.loads((output / "freeze.json").read_text())
    assert audit.sha(output / "fixtures.json") == frozen["fixtures_sha256"]
    assert audit.sha(output / "baseline_bitset_backend.py") == frozen["sources"]["bitset_backend.py"]
    candidate = json.loads((output / "candidate_manifest.json").read_text())
    for relative, expected in candidate.items():
        assert audit.sha(output / "source_candidate" / relative) == expected, relative
        if relative != "scripts/cm_packed_mask_lifecycle.py":
            assert audit.sha(ROOT / relative) == expected, ("live source drift", relative)
    # The lifecycle extension has its original diagnostic source retained and
    # separately reports a timing-only run; it is not a change to timed kernels.
    assert audit.sha(output / "lifecycle_diagnostic.py") == candidate["scripts/cm_packed_mask_lifecycle.py"]
    fixtures = json.loads((output / "fixtures.json").read_text())
    audit.load_baseline(output)
    checked_rows = 0
    checked_outputs = 0
    metrics = []
    for label, cohort, methods in (
        ("development", "development", ("direct", "cse", "cm_flat", "cm_words", "cm_public", "dense")),
        ("development_strong", "development", ("cse_flat",)),
        ("confirmation", "confirmation", ("direct", "cse", "cse_flat", "cm_flat", "cm_words", "cm_public", "dense")),
    ):
        rows = [json.loads(line) for line in (output / f"{label}_raw.jsonl").read_text().splitlines()]
        summaries = json.loads((output / f"{label}_summary.json").read_text())
        seen = set()
        cases = {case["id"]: case for case in fixtures[cohort]}
        expected_digests = {}
        for case in cases.values():
            for q, restricted in ((1, False), (64, False), (16, True)):
                queries = audit.queries_for(case, q, restricted)
                expected = audit.oracle(case, queries)
                expected_digests[(case["id"], q, restricted)] = hashlib.sha256(b"".join(expected)).hexdigest()
        for row in rows:
            key = (row["case"], row["backend"], row["q"], row["restricted"], row["repeat"], row["arm"])
            assert key not in seen
            seen.add(key)
            assert row["case"] in cases and row["backend"] in methods
            assert (row["q"], row["restricted"]) in ((1, False), (64, False), (16, True))
            assert row["repeat"] in range(9) and row["arm"] in ("baseline", "candidate")
            assert row["n"] == cases[row["case"]]["n"] and row["exact"] is True
            assert row["total_ns"] > 0 and row["warm_ns"] > 0
            assert row["output_sha256"] == expected_digests[(row["case"], row["q"], row["restricted"])]
            checked_outputs += row["q"]
        expected_cells = {(case, method, q, restricted) for case in cases for method in methods
                          for q, restricted in ((1, False), (64, False), (16, True))}
        assert len(rows) == len(expected_cells) * 18
        assert len(summaries) == len(expected_cells)
        assert {(r["case"], r["backend"], r["q"], r["restricted"]) for r in summaries} == expected_cells
        for summary in summaries:
            cell = (summary["case"], summary["backend"], summary["q"], summary["restricted"])
            group = [row for row in rows if (row["case"], row["backend"], row["q"], row["restricted"]) == cell]
            for metric in ("total_ns", "warm_ns"):
                arms = {arm: sorted((row for row in group if row["arm"] == arm), key=lambda row: row["repeat"])
                        for arm in ("baseline", "candidate")}
                ratios = [a[metric] / b[metric] for a, b in zip(arms["baseline"], arms["candidate"])]
                got = summary[metric]
                assert got["baseline"] == statistics.median(row[metric] for row in arms["baseline"])
                assert got["candidate"] == statistics.median(row[metric] for row in arms["candidate"])
                assert math.isclose(got["speedup"], math.exp(sum(map(math.log, ratios)) / 9), rel_tol=1e-12)
                assert got["min_paired_speedup"] == min(ratios)
                assert got["baseline_max"] == max(row[metric] for row in arms["baseline"])
                assert got["candidate_max"] == max(row[metric] for row in arms["candidate"])
                assert got["ci95"] == audit.interval(ratios)
        checked_rows += len(rows)
        if label == "confirmation":
            metrics = summaries
    env = json.loads((output / "env.json").read_text())
    env_ratios = []
    for n in (11, 13, 16, 18, 20, 22):
        times = {arm: statistics.median(r["total_ns"] for r in env
                 if r["n"] == n and r["arm"] == arm and "repeat" in r)
                 for arm in ("baseline", "candidate")}
        env_ratios.append(times["baseline"] / times["candidate"])
    targeted = [r for r in metrics if r["backend"].startswith("cm_")]
    minimum_cold_median = min(r["total_ns"]["baseline"] / r["total_ns"]["candidate"] for r in targeted)
    env_geomean = math.exp(statistics.mean(map(math.log, env_ratios)))
    assert minimum_cold_median >= 0.95 and env_geomean > 1.2
    for filename in ("fresh_process.json", "fresh_process_timing.json"):
        fresh = json.loads((output / filename).read_text())
        assert len(fresh) == 20
        for n in (16, 22):
            assert len({r["output_sha256"] for r in fresh if r["n"] == n}) == 1
            for arm in ("baseline", "candidate"):
                assert {r["repeat"] for r in fresh if r["n"] == n and r["arm"] == arm} == set(range(5))
    query = json.loads((output / "query_controls.json").read_text())
    assert len(query["rows"]) == 320
    for row in query["rows"]:
        if "repeat" in row:
            case = next(c for c in fixtures["development"] if c["id"] == row["case"])
            expected = int.from_bytes(audit.oracle(case, [{}])[0], "little").bit_count()
            assert row["exact"] and row["count"] == expected
    result = {"status": "verified", "paired_cold_sessions": checked_rows,
              "cold_relation_outputs_replayed": checked_outputs,
              "warm_sessions_checked_in_campaign": checked_rows,
              "environment_cold_geomean": env_geomean,
              "minimum_targeted_cold_cm_ratio_of_medians": minimum_cold_median,
              "query_control_timing_rows": 288,
              "note": "warm exact outputs asserted in campaign; saved hashes replay cold outputs; bootstrap helper shared",
              "sha256": {path.name: audit.sha(path) for path in output.iterdir()
                         if path.is_file() and path.suffix in (".json", ".jsonl", ".py")}}
    audit.write_json(output / "verification_all_sessions.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "sha256"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args().output)
