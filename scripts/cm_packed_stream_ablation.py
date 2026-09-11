"""Post-confirmation mechanism diagnostic on every previously exposed stream case.

The single-chunk positional control shares cache, binding and dead-slot-release
behavior with tiled output. This is descriptive reused-data evidence; it cannot
be relabeled as new confirmation or used to retune the earlier frozen panels.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import tracemalloc

from scripts import cm_packed_queries_campaign as panel


ARMS = ("complete_positional", "stream_12", "stream_16")


def summaries(rows):
    mapped = [dict(row, method="complete" if row["method"] == "complete_positional" else row["method"])
              for row in rows]
    return [dict(row, baseline="complete_positional",
                 method="complete_positional" if row["method"] == "complete" else row["method"])
            for row in panel.summarize(mapped)]


def inputs(panels):
    panel.check_sources(panels)
    fixtures = json.loads((panels / "FIXTURES.json").read_text())
    return [case for cases in fixtures.values() for case in cases if case["task"] == "stream"]


def run(panels, output):
    cases = inputs(panels)
    schedule = [dict(case=case["id"], q=q, repeat=repeat, method=method)
                for case in cases for q in (1, 16) for repeat in range(9)
                for method in (ARMS if repeat % 2 == 0 else tuple(reversed(ARMS)))]
    output.mkdir(parents=True, exist_ok=False)
    panel.write(output / "FREEZE.json", {
        "schema": "cm-packed-stream-mechanism-diagnostic/v1", "scope": __doc__,
        "panel_freeze_sha256": panel.sha(panels / "FREEZE.json"),
        "source_sha256": panel.sha(Path(__file__)), "schedule": schedule,
        "complete_positional": "same PackedStreamPlan at chunk_vars=20, one chunk at all measured live widths",
        "budget": "same 2 MiB admitted column payload and max_width=20 for all arms",
    })
    indexed = {case["id"]: case for case in cases}
    targets = {(case["id"], q): panel.expected(case, q) for case in cases for q in (1, 16)}
    rows = []
    with (output / "RAW.jsonl").open("x", encoding="utf-8") as stream:
        for cell in schedule:
            panel.bs.clear_bitset_env_cache()
            gc.collect()
            execution = "stream_20" if cell["method"] == "complete_positional" else cell["method"]
            result, measured = panel.session(indexed[cell["case"]], execution, cell["q"])
            row = dict(cell, **measured, exact=result == targets[cell["case"], cell["q"]],
                       result_sha256=hashlib.sha256(result.encode()).hexdigest())
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()
            if not row["exact"]: raise AssertionError(cell)
            rows.append(row)
    memory = []
    for case in cases:
        for q in (1, 16):
            for method in ARMS:
                panel.bs.clear_bitset_env_cache()
                gc.collect()
                tracemalloc.start()
                result, measured = panel.session(case, "stream_20" if method == "complete_positional" else method,
                                                 q, warm=False)
                retained, peak = tracemalloc.get_traced_memory()
                del result
                gc.collect()
                released, _ = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                memory.append(dict(case=case["id"], q=q, method=method, peak_bytes=peak,
                                   after_session_bytes=retained, after_gc_bytes=released, cache=measured["cache"]))
    panel.write(output / "MEMORY.json", memory)
    panel.write(output / "SUMMARY.json", summaries(rows))
    print(len(rows), "exact reused-data timing cells", flush=True)


def verify(panels, output):
    cases = inputs(panels)
    freeze = json.loads((output / "FREEZE.json").read_text())
    if freeze["panel_freeze_sha256"] != panel.sha(panels / "FREEZE.json") or freeze["source_sha256"] != panel.sha(Path(__file__)):
        raise ValueError("source identity mismatch")
    rows = [json.loads(line) for line in (output / "RAW.jsonl").read_text().splitlines()]
    if [{key: row[key] for key in ("case", "q", "repeat", "method")} for row in rows] != freeze["schedule"]:
        raise ValueError("schedule mismatch")
    targets = {(case["id"], q): panel.expected(case, q) for case in cases for q in (1, 16)}
    for row in rows:
        if not row["exact"] or row["result_sha256"] != hashlib.sha256(targets[row["case"], row["q"]].encode()).hexdigest():
            raise ValueError("output mismatch")
        if row["total_ns"] != row["setup_ns"] + row["query_delivery_ns"] + row["cleanup_ns"]:
            raise ValueError("accounting mismatch")
    if summaries(rows) != json.loads((output / "SUMMARY.json").read_text()):
        raise ValueError("summary mismatch")
    panel.write(output / "VERIFICATION.json", {"status": "verified", "timing_rows": len(rows),
                                               "scope": "post-confirmation reused-data diagnostic",
                                               "artifacts": {p.name: panel.sha(p) for p in output.iterdir() if p.is_file()}})
    print("mechanism diagnostic verified", len(rows), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "verify"))
    parser.add_argument("--panels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    (run if args.action == "run" else verify)(args.panels, args.output)


if __name__ == "__main__":
    main()
