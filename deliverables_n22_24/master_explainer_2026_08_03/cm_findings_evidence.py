"""Curated application guide; measured values come from the checked site evidence."""
from __future__ import annotations

SOURCE_REVISION = "1145537c9e2274ae7622dad5b68a7d612b27bb7e"
REPO_URL = "https://github.com/Relative0/Correspondence_Matrices/blob/" + SOURCE_REVISION + "/"
DOWNLOAD = "results/2026-09-17/findings-cheat-sheet.json"


def build_findings(data):
    current = data["e25_latest_results"]
    research = current["september16_research"]
    panels = {p["id"]: p for p in current["panels"]}

    def row(panel, case, q, method):
        matches = [r for r in panels[panel]["rows"]
                   if r["case"] == case and r["q"] == q and r["method"] == method]
        if len(matches) != 1 or matches[0]["status"] != "complete":
            raise ValueError("Missing completed finding: " + str((panel, case, q, method)))
        return matches[0]

    def comparison(panel, case, q, control, candidate, metric="cold_ms"):
        a, b = row(panel, case, q, control), row(panel, case, q, candidate)
        return {"control": a[metric], "candidate": b[metric], "ratio": a[metric] / b[metric],
                "unit": "MiB" if metric == "peak_mib" else "ms", "metric": metric,
                "control_label": a["label"].replace("Â·", "·"), "candidate_label": b["label"].replace("Â·", "·"),
                "case": case, "q": q, "scope": panels[panel]["scope"],
                "source_href": current["sources"][a["source"]]["href"],
                "source_sha256": current["sources"][a["source"]]["sha256"],
                "selectors": [a["selector"], b["selector"]]}

    def code(path, label):
        return {"label": label, "href": REPO_URL + path, "path": path}

    def card(id, title, task, use, mechanism, takeaway, boundary, code_links, evidence, metrics):
        return dict(id=id, title=title, task=task, use=use, mechanism=mechanism,
                    takeaway=takeaway, boundary=boundary, code=code_links,
                    evidence=evidence, metrics=metrics)

    c40 = research["decomposition"]["c40"]["summary"]
    c39 = research["decomposition"]["c39"]["summary"]
    decomposition = []
    for name, summary in (("C40", c40), ("C39", c39)):
        times = summary["primary_median_case_sum_ns"]
        decomposition.append(dict(control=times["c15_exhaustive"] / 1e6,
            candidate=times["c16_screened"] / 1e6,
            ratio=times["c15_exhaustive"] / times["c16_screened"], unit="ms",
            control_label="C15 exhaustive", candidate_label="C16 screened",
            metric="sum of per-case analysis medians", case=name,
            scope="Windows; five balanced rounds; parsing and truth construction excluded",
            source_href="results/2026-09-16/exact-count-and-decomposition/" + name.lower() + "-aggregate.json",
            selectors=["summary.primary_median_case_sum_ns.c15_exhaustive",
                       "summary.primary_median_case_sum_ns.c16_screened"]))
    benchmark = next(r for r in research["cudd"]["benchmark"]["cases"] if r["case"] == "or_64_padded_128")
    methods = benchmark["methods"]
    cudd_metric = dict(control=methods["python_exact"]["median_ns"] / 1000,
        candidate=methods["apa_int"]["median_ns"] / 1000,
        ratio=methods["python_exact"]["median_ns"] / methods["apa_int"]["median_ns"],
        unit="µs", metric="resident-root count-only median", case=benchmark["case"],
        control_label="Python exact traversal", candidate_label="Native APA exact count",
        scope="Linux/WSL; nine rounds of 200 calls; same resident root; reordering disabled",
        source_href="results/2026-09-16/exact-count-and-decomposition/cudd-benchmark.json",
        selectors=["cases[or_64_padded_128].methods.python_exact.median_ns / 1000",
                   "cases[or_64_padded_128].methods.apa_int.median_ns / 1000"])
    cards = [
        card("decomposition", "Find the same exact decomposition with less repeated work", "decomposition",
             "You analyze small Boolean truth vectors and need a canonical factor artifact, not just a yes/no answer.",
             "Share one matrix layout per partition, rank exact candidate descriptors, then strictly validate and reconstruct only the leading candidates.",
             "C40's 20-case confirmation gives a 3.95× internal analysis speedup; C39's 19 public cones give 3.46×. Both select the same best artifact as the exhaustive control.",
             "Best means best within the bounded partition set and four artifact families. The implementation admits at most 10 variables. C40 is development-blind in source-family selection, on one host. This is not a comparison with ABC or a new general decomposition theorem; corpus redistribution remains unresolved.",
             [code("cmbench/recognition/gf2_decomposition.py", "analyze_screened_exact_gf2"), code("tests/test_gf2_decomposition.py", "Exactness examples and tests")],
             "latest-results.html#exact-count-and-decomposition", decomposition),
        card("packed-inputs", "Make packed Boolean input construction cheaper", "relation",
             "You really need the complete Boolean answer vector and spend substantial time building its input masks.",
             "Construct repeating packed masks efficiently before evaluating the expression. The shared constructor also benefits direct BitSet and common-subexpression elimination (CSE).",
             "A selected fresh 18-variable confirmation case drops from 14.03 ms to 1.33 ms for cold public packed-CM evaluation.",
             "This is an old/current implementation ablation, not a CM-versus-native claim or an aggregate across all cases. The full output still has 2^n bits; warm gains are smaller and some paths regress.",
             [code("bitset_backend.py", "build_bitset_env and packed evaluators"), code("tests/test_packed_mask_construction.py", "Mask construction checks")],
             "latest-results.html#packed-masks", [comparison("packed-masks", "confirmation-n18-s0", 1, "cm_public_baseline", "cm_public_candidate")]),
        card("cache", "Reuse positional masks across renamed inputs", "reuse",
             "Repeated requests share a variable count and order but use different variable names.",
             "A bounded positional cache can reuse the same masks without treating every renamed basis as a new allocation.",
             "On the selected renamed-input trace, cold q32 time falls from 30.36 ms with named LRU caching to 1.49 ms with positional caching.",
             "The warm named-LRU result is faster here (0.47 versus 0.58 ms). Memory bounds, eviction and request shape decide whether this helps; no universal cache policy was promoted.",
             [code("cmbench/backends/packed_mask_cache.py", "PackedMaskCache"), code("docs/research/CM_PACKED_QUERY_APIS_2026_09_11.md", "Packed query API guide")],
             "latest-results.html#bounded-cache", [comparison("bounded-cache", "confirmation-cache-n18-renamed", 32, "named_lru", "positional")]),
        card("streaming", "Deliver a full truth vector without keeping it all resident", "relation",
             "A file or downstream process needs every output bit, but peak memory and first delivery matter.",
             "Evaluate and deliver chunks with the same ordering and file obligations as the complete-output control.",
             "For the selected 24-variable cold file output, 32 KiB chunks take 32.17 ms versus 160.79 ms for complete packed output. A separate memory diagnostic reports 48.37 versus 147.34 MiB process peaks.",
             "Timing and memory were measured on different Linux hosts and must not be combined into one run. This still writes the complete exponential-size answer; small chunks and warm batches can regress. Tune against the real reader and durability contract.",
             [code("cmbench/backends/packed_stream_io.py", "write_packed_stream"), code("docs/research/CM_PACKED_STREAM_IO_2026_09_11.md", "Streaming API and contract")],
             "latest-results.html#streaming", [comparison("streaming", "cloud-stream-n24", 1, "complete", "stream_18"), comparison("file-memory", "file-n24", 1, "complete", "stream_18", "peak_mib")]),
        card("affine", "Count XOR-constrained solutions without enumerating assignments", "count",
             "Your constraints are affine equations over GF(2), as in coding matrices or parity checks.",
             "Use elimination and rank to count the solutions; indexed rows reduce repeated work under conditioning.",
             "On one public 1,800-variable matrix and eight queries, indexed Python takes 28.96 ms versus 103.91 ms for the original Python implementation. Indexed M4RI takes 41.43 ms on the same host and schedule.",
             "This is a structured counting algorithm and implementation result, not a generic CM representation advantage. It does not handle arbitrary nonlinear CNF. One matrix cannot establish a general Python-over-native ranking.",
             [code("cmbench/backends/affine_constraints.py", "AffineConstraintPlan"), code("docs/research/CM_SCALAR_QUERY_APIS_2026_09_11.md", "Exact scalar query APIs")],
             "latest-results.html#affine-count", [comparison("affine-count", "n_1800_k_0902_gap_28", 8, "rows_legacy", "rows_indexed")]),
        card("bucket", "Count overlapping CNF factors with exact arrays", "count",
             "You need exact full-CNF counts for a problem whose elimination width fits a bounded plan.",
             "Bucket elimination combines local factors. Object-dtype NumPy arrays accelerate the larger factors while preserving Python-integer exactness.",
             "On the public printer model and eight queries, arrays take 29.76 ms versus 121.17 ms for Python min-fill. Natural-order CUDD takes 4.66 ms on this same case.",
             "This example improves the Python control but loses to natural-order CUDD. Arrays lose on many narrow factors, and high-width plans explicitly refuse. Full assignments and distinct projected assignments require different counting contracts.",
             [code("cmbench/backends/bucket_numpy.py", "NumpyBucketCNFCountPlan"), code("cmbench/backends/projected_counts.py", "ProjectedCNFCountPlan"), code("docs/research/CM_BUCKET_COUNT_API_2026_09_11.md", "Bounded count API guide")],
             "latest-results.html#bucket-count", [comparison("bucket-count", "model-09", 8, "bucket_min_fill", "numpy_min_fill")]),
        card("cudd-exact", "Keep large BDD counts exact in Python", "count",
             "You already hold a CUDD BDD and need an exact integer when floating-point rounding or overflow is unacceptable.",
             "The dd 0.6.0 prototype calls Cudd_ApaCountMinterm, converts its binary digits to a Python integer, and frees the native allocation in finally.",
             "On OR-of-64 padded to 128 variables, native APA takes 12.60 µs versus 113.16 µs for Python exact traversal. The existing double call takes 11.13 µs but rounds this result.",
             "A local binding prototype, not an upstream dd release or a new counting algorithm. About 9–10× faster than Python on the three larger tested diagrams; trivial roots favor Python. Construction is excluded. A 1,100-variable padded literal overflows the double control. Allocation-failure injection remains untested.",
             [code("prototypes/cudd_apa/README.md", "Build the prototype and reproduce results"), code("prototypes/cudd_apa/patch_dd.py", "Exact count patch"), code("cmbench/comparative/exact_cudd_count.py", "Existing Python exact fallback")],
             "latest-results.html#exact-count-and-decomposition", [cudd_metric]),
        card("kernel", "Separate a faster kernel from a slower public call", "reuse",
             "You repeatedly evaluate a prepared full relation and can measure preparation, evaluation and delivery separately.",
             "CM compilation can reduce kernel work, but public wrappers and preparation can consume the saving. Compare the same evaluator and delivered output.",
             "The September 15 symmetric replay puts the bare CM/CSE-flat time ratio near 0.91 on both Windows and Linux: about 9% less kernel time. The public wrapper instead costs about 3.7–3.9× the CSE-flat time.",
             "Kernel-only gains are not end-to-end gains. Reuse break-even varies by formula and host; many formulas never amortize preparation versus CSE-flat. The matched biology pilot found no demonstrated CM-specific session advantage.",
             [code("bitset_backend.py", "Prepared flat evaluation and CSE controls"), code("docs/audits/2026-09-15-cm-time-attribution-deep-dive/TASK_FINDINGS.md", "Task and attribution audit"), code("docs/audits/2026-09-15-cm-biology-sessions/PORTFOLIO_DISPOSITION.md", "Matched-session findings")],
             "latest-results.html#post-integration-confirmation", []),
    ]
    return dict(schema="cm-findings-cheat-sheet/v1", reviewed="2026-09-17",
        source_revision=SOURCE_REVISION, cards=cards,
        selection="Curated useful mechanisms, not a global leaderboard. Numeric examples are selected disclosed cases, not estimates of typical user speedup. Ratios in the cards are control time divided by candidate time unless explicitly labelled otherwise.",
        article=dict(title="An exact winner, with less work validating losing candidates",
            recommendation="Best-supported software-note candidate: the bounded C16 decomposition workflow.",
            reason="The output contract is explicit, the selected artifact is preserved, C39/C40 extend the evidence, and C41 tests individual mechanisms. This supports an engineering article about exact software design and measured tradeoffs.",
            limits="The internal exhaustive control is the comparator. ABC's fixed 4-LUT ACD output has a different objective. A task-equivalent external comparison, redistributable replay inputs and a completed prior-art review would strengthen a research submission. Novelty and publication acceptance are not established.",
            secondary="A practical Python/CUDD article is also useful: exact integer counts, rounding examples, safe allocation cleanup and resident-root benchmarks. Credit CUDD's existing arbitrary-precision algorithm; the contribution here is the binding and evaluation.",
            evidence=research["report_href"]),
        stops=[
            {"title":"Cut fusion: keep it experimental", "text":"The frozen q64 whole-session gate measured only 0.493× speedup against CSE, below its 1.10× requirement. Exact outputs alone did not make the optimization worthwhile.", "href":research["report_href"]},
            {"title":"Native batching: a completed no-go", "text":"The prospective q96 gate reached about 1.078×, below its frozen 1.10× materiality requirement. No learned router or production default was promoted.", "href":"latest-results.html#native-batch"},
            {"title":"Do not reuse the historical SymPy headline", "text":"The historical approximately 76× observation timed unlike tasks. Supplied-row evaluation, a full truth table, SAT, counting and expression simplification need separate comparisons.", "href":REPO_URL+"docs/audits/2026-09-15-cm-time-attribution-deep-dive/TASK_FINDINGS.md"},
        ])
