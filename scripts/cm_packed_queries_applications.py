"""Development-only applicability replay on all eight historical k8 FM slices.

This changes the requested task to counts/streaming for diagnostics. The original
task returned two complete vectors; these are consumed inputs, not confirmation
data or evidence that a deployed consumer requests scalar counts.
"""
from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path
import random

from cm_exprlib import And, Not, Or, Var
from cm_ir import compile_expr_to_cm_ir
from cmbench.backends.packed_mask_cache import PackedMaskCache
from cmbench.backends.packed_queries import IndependentCountPlan, PackedStreamPlan
from scripts.cm_packed_queries_campaign import ROOT, sha, tree, write


SOURCE = "docs/research/verification/fresh-process-persistence-v2-2026-08-29/plan.json"


def expression(clauses):
    terms = []
    for clause in clauses:
        literals = [Var(abs(value) - 1) if value > 0 else Not(Var(abs(value) - 1))
                    for value in clause]
        terms.append(tree(literals, Or) if literals else And(Var(0), Not(Var(0))))
    return tree(terms, And) if terms else Or(Var(0), Not(Var(0)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = ROOT / SOURCE
    plan = json.loads(source.read_text(encoding="utf-8"))
    rows = []
    rng = random.Random(2026091177)
    for case_id, case in sorted(plan["scenarios"].items()):
        basis = tuple(f"x{i}" for i in range(case["k"]))
        for version in case["versions"]:
            clauses = version["clauses"]
            if any(type(value) is not int or not 1 <= abs(value) <= case["k"]
                   for clause in clauses for value in clause):
                raise ValueError("invalid saved CNF literal")
            expr = expression(clauses)
            node = compile_expr_to_cm_ir(expr)
            pool = PackedMaskCache(max_bytes=1 << 16, max_width=8)
            raw = IndependentCountPlan.from_expr(expr, basis, cache=pool)
            normalized = IndependentCountPlan.from_cm_node(node, basis, cache=pool)
            stream = PackedStreamPlan.from_cm_node(node, basis, cache=pool)
            contexts = [{}] + [{name: rng.randrange(2) for name in rng.sample(basis, 2)} for _ in range(8)]
            for index, context in enumerate(contexts):
                live = tuple(name for name in basis if name not in context)
                truth = []
                for assignment in product((0, 1), repeat=len(live)):
                    values = dict(zip(live, assignment)) | context
                    truth.append(all(any(bool(values[f"x{abs(lit) - 1}"]) == (lit > 0)
                                         for lit in clause) for clause in clauses))
                expected_count = sum(truth)
                expected_bits = sum(int(value) << row for row, value in enumerate(truth))
                expected_bytes = expected_bits.to_bytes((len(truth) + 7) // 8, "little")
                chunks = tuple(stream.iter_chunks(chunk_vars=3, max_total_bits=256, fixed=context))
                if (raw.count(context) != expected_count or normalized.count(context) != expected_count
                        or normalized.exists(context) != bool(expected_count)
                        or b"".join(c.data for c in chunks) != expected_bytes):
                    raise AssertionError((case_id, version["id"], context))
                rows.append({"case": case_id, "version": version["id"], "context_index": index,
                             "fixed": context, "history": case["source"]["history"],
                             "source_kind": case["source"]["kind"], "width": case["k"],
                             "raw_component_widths": sorted(map(len, raw.component_supports)),
                             "cm_component_widths": sorted(map(len, normalized.component_supports)),
                             "count": expected_count, "exact_count_and_stream": True})
            pool.clear()
    write(args.output, {"schema": "cm-packed-queries-historical-applicability/v1",
                        "scope": __doc__, "source": SOURCE, "source_sha256": sha(source),
                        "script_sha256": sha(Path(__file__)), "case_count": len(plan["scenarios"]),
                        "query_context_count": len(rows), "rows": rows,
                        "adoption": "No production admission: k8 conditioned slices and derived contracts only."})
    print(len(rows), "historical contexts exact; development-only applicability", flush=True)


if __name__ == "__main__":
    main()
