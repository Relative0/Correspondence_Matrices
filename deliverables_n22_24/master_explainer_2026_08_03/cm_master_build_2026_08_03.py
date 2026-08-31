"""CM master knowledge-base builder (2026-08-03, evidence updated 2026-08-30).

Reads the refreshed evidence of the 2026-08-03 comprehensive benchmark
campaign (B1-B7 + BX1/BX2), the accepted 2026-08-25 symmetric V3 correction,
the 2026-08-26/27 repeatability, guard, preparation, held-out selector, cache,
family, context, tracing, workload-intake, dependency, memory-policy, and audit
reliability follow-ups, and the authored prose content file, then emits a
self-contained master page, three derived audience pages, and a use-case guide.

    cm_master_data_2026_08_03.json   data arrays, named numbers, provenance
    index.html                       master knowledge base (all depth layers)
    layperson.html                   plain-language cut
    investor.html                    problem / evidence / roadmap cut
    expert.html                      dense technical cut
    usecases.html                    field-oriented application hypotheses
    feature-model-evidence.html       saved real-model results and audit gaps

Every number rendered on any page is read from a raw or summary evidence file
by this script and carried in `_numbers` with a file+field provenance string.
Prose in `cm_master_content_2026_08_03.json` contains no hard-coded results:
it references numbers as `{{token}}` and the page resolves them from `_numbers`.

Read-only with respect to the repository: no evidence file is opened for
writing, and all output stays in this directory.

Usage:
    .venv\\Scripts\\python.exe deliverables_n22_24\\master_explainer_2026_08_03\\cm_master_build_2026_08_03.py
"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from cm_feature_model_evidence import build_feature_model_evidence

HERE = Path(__file__).resolve().parent
DELIV = HERE.parent
REPO = DELIV.parent

# The legacy campaign inputs are frozen at this revision. The feature-model
# follow-up has its own separately pinned run/checksum identities. Do not
# derive this value from the checkout's current HEAD: doing so makes a rebuild
# change its own output after the generated site is committed.
EVIDENCE_REVISION = "4dbfffc1db749e85401d533c5a07cb529a41eb37"

# ---------------------------------------------------------------- helpers


def rel(p: Path) -> str:
    return p.relative_to(REPO).as_posix()


def load_json(p: Path):
    with p.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_csv(p: Path) -> list[dict]:
    with p.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def fnum(x):
    """CSV cell -> float or None."""
    if x is None or x == "":
        return None
    return float(x)


def geomean(xs: list[float]) -> float:
    return math.exp(statistics.fmean(math.log(x) for x in xs))


def junit_counts(p: Path) -> dict:
    root = ET.parse(p).getroot()
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
    total = sum(int(s.attrib["tests"]) for s in suites)
    cases = len(root.findall(".//testcase"))
    return {
        "total": total,
        "testcases": cases,
        "subtests": total - cases,
        "failures": sum(int(s.attrib.get("failures", 0)) for s in suites),
        "errors": sum(int(s.attrib.get("errors", 0)) for s in suites),
        "skipped": sum(int(s.attrib.get("skipped", 0)) for s in suites),
    }


# ---------------------------------------------------------------- paths

P_B1_RES = DELIV / "b1_e3_replay_2026_08_03" / "cm_gap_e3_corrected_results_2026_08_02.json"
P_B1_SUM = DELIV / "b1_e3_replay_2026_08_03" / "CM_gap_e3_corrected_summary_2026_08_02.csv"
P_B1_ACC = DELIV / "b1_e3_replay_2026_08_03" / "b1_acceptance_check_results_2026_08_03.json"
P_B1_ARCH = DELIV / "CM_gap_e3_corrected_summary_2026_08_02.csv"
P_B1_ARCH_RES = DELIV / "cm_gap_e3_corrected_results_2026_08_02.json"
P_EPFL_RES = DELIV / "cm_gap_epfl_results_2026_08_03.json"
P_EPFL_SUM = DELIV / "CM_gap_epfl_summary_2026_08_03.csv"
P_EPFL_ANA = DELIV / "epfl_run_2026_08_03" / "cm_gap_epfl_analysis_2026_08_03.json"
P_EPFL_PROV = DELIV / "cm_gap_epfl_provenance_2026_08_03.json"
P_B2_RES = DELIV / "b2_wrapper_2026_08_03" / "cm_b2_wrapper_results_2026_08_03.json"
P_B2_SUM = DELIV / "b2_wrapper_2026_08_03" / "CM_b2_wrapper_summary_2026_08_03.csv"
P_B3_RES = DELIV / "b3_scaling_2026_08_03" / "cm_b3_scaling_results_2026_08_03.json"
P_B3_SUM = DELIV / "b3_scaling_2026_08_03" / "CM_b3_scaling_summary_2026_08_03.csv"
P_B4_RES = DELIV / "b4_sweep_2026_08_03" / "cm_b4_sweep_results_2026_08_03.json"
P_B4_HEAD = DELIV / "b4_sweep_2026_08_03" / "CM_b4_headline_summary_2026_08_03.csv"
P_B4_GUARD = DELIV / "b4_sweep_2026_08_03" / "CM_b4_guard_summary_2026_08_03.csv"
P_B5_RES = DELIV / "b5_cudd_2026_08_03_run5" / "cm_b5_cudd_matched_results_2026_08_03.json"
P_B5_SUM = DELIV / "b5_cudd_2026_08_03_run5" / "CM_b5_cudd_matched_summary_2026_08_03.csv"
P_B5_POD = DELIV / "b5_cudd_2026_08_03_run5" / "b5_pod_audit_2026_08_03.json"
P_B6_ANA = DELIV / "b6_pod_replication_2026_08_03" / "b6_analysis_2026_08_03.json"
P_MANIFEST = DELIV / "cm_benchmark_refresh_manifest_2026_08_03.json"
P_BX1_RES = DELIV / "bx1_crossover_2026_08_03" / "cm_bx1_crossover_results_2026_08_03.json"
P_BX1_SUM = DELIV / "bx1_crossover_2026_08_03" / "CM_bx1_crossover_summary_2026_08_03.csv"
P_BX2_RES = DELIV / "bx2_cudd_orders_2026_08_03" / "cm_bx2_cudd_orders_results_2026_08_03.json"
P_BX2_SUM = DELIV / "bx2_cudd_orders_2026_08_03" / "CM_bx2_cudd_orders_summary_2026_08_03.csv"
P_BX2_POD = DELIV / "bx2_cudd_orders_2026_08_03" / "bx2_pod_audit_2026_08_03.json"
P_SYM_V3_INF = DELIV / "corrections_2026_08_25" / "symmetric" / "audited_v3_inference.csv"
P_SYM_V3_AUDIT = DELIV / "corrections_2026_08_25" / "symmetric" / "audited_v3_audit.json"
P_RERUN = REPO / "docs" / "audits" / "2026-08-25-cm-deep-performance" / "reruns" / "campaign-20260826-132038"
P_SYM_REPEAT_AUDITS = [
    P_RERUN / "symmetric_v3_audit.json",
    P_RERUN / "symmetric_v3_r2_audit.json",
    P_RERUN / "symmetric_v3_r3_audit.json",
]
P_ABOVE_GUARD_AUDIT = P_RERUN / "above_guard_audit.json"
P_ABOVE_GUARD_RAW = P_RERUN / "above_guard_raw.csv"
P_DPR1_SUMMARY = P_RERUN / "dpr1_smoke_summary.json"
P_MEMO_RUNPOD_AUDIT = DELIV / "memo_runpod_2026_08_26" / "memo_runpod_audit_2026_08_26.json"
P_MEMO_RUNPOD_INVENTORY = DELIV / "memo_runpod_2026_08_26" / "postflight_runpod_inventory.json"
P_I10_SCREEN = DELIV / "heldout_abc_i10_2026_08_26" / "abc_i10_screening.json"
P_I10_SELECTOR_AUDIT = DELIV / "heldout_abc_i10_2026_08_26" / "abc_i10_selector_audit.json"
P_CACHE_PROCESS = P_RERUN / "cache_process_local_summary.csv"
P_CACHE_REUSE50 = P_RERUN / "cache_reuse50_summary.csv"
P_FAMILY_REUSE = P_RERUN / "family_high_reuse_summary.csv"
P_PARTIAL_SUMMARIES = sorted(P_RERUN.glob("partial_f*_summary.csv")) + [P_RERUN / "partial_sliding_100_summary.csv"]
P_REMAINING = REPO / "docs" / "audits" / "2026-08-25-cm-deep-performance" / "remaining-work"
P_TRACE_CAMPAIGN = P_REMAINING / "campaign-20260826-154541"
P_TRACE_V1 = P_TRACE_CAMPAIGN / "trace_overhead_summary.json"
P_TRACE_V2 = P_TRACE_CAMPAIGN / "trace_overhead_v2_summary.json"
P_TRACE_V3 = P_TRACE_CAMPAIGN / "trace_overhead_v3_sample16_summary.json"
P_TRACE_V3_AUDIT = P_TRACE_CAMPAIGN / "trace_overhead_v3_sample16_trace_audit.json"
P_DEP_AUDITS = [
    P_TRACE_CAMPAIGN / "runpod_dependency_feasibility" / "dependency_runpod_audit_2026_08_26.json",
    P_TRACE_CAMPAIGN / "runpod_dependency_feasibility_run2" / "dependency_runpod_audit_run2_2026_08_26.json",
    P_TRACE_CAMPAIGN / "runpod_dependency_feasibility_run3" / "dependency_runpod_audit_run3_2026_08_26.json",
]
P_DEP_POSTFLIGHT = P_TRACE_CAMPAIGN / "runpod_run3_postflight_inventory.json"
P_THREE_LANE = P_REMAINING / "three-lane-20260827-011536"
P_WORKLOAD_VALIDATION = P_THREE_LANE / "WORKLOAD-MANIFEST-TEMPLATE-VALIDATION.json"
P_MEMORY_PROBE = P_THREE_LANE / "DP-R2-OUTPUT-BUDGET-PROBE.json"
P_DPR3_SUMMARY = P_THREE_LANE / "dpr3_trace_overhead_smoke_summary.json"
P_FOCUSED_JUNIT = P_THREE_LANE / "focused_pytest.xml"
P_FULL_JUNIT = P_THREE_LANE / "full_pytest.xml"
P_LATE_EVIDENCE = HERE / "website_audit_2026-08-27" / "ACCEPTED-LATE-EVIDENCE.json"

P_CONTENT = HERE / "cm_master_content_2026_08_03.json"
P_USE_CASE_CATALOG = HERE / "use_case_benchmarks_2026-08-27" / "CM-USE-CASE-BENCHMARK-CATALOG.json"
P_C16_RESULTS = REPO / "docs" / "recognition" / "learning_milestone_c16_exact_screened_gf2_results.json"

# ---------------------------------------------------------------- load

b1_res = load_json(P_B1_RES)
b1_sum = load_csv(P_B1_SUM)
b1_acc = load_json(P_B1_ACC)
b1_arch_sum = load_csv(P_B1_ARCH)
b1_arch_res = load_json(P_B1_ARCH_RES)
epfl_res = load_json(P_EPFL_RES)
epfl_ana = load_json(P_EPFL_ANA)
epfl_prov = load_json(P_EPFL_PROV)
b2_res = load_json(P_B2_RES)
b2_sum = load_csv(P_B2_SUM)
b3_res = load_json(P_B3_RES)
b3_sum = load_csv(P_B3_SUM)
b4_res = load_json(P_B4_RES)
b4_head = load_csv(P_B4_HEAD)
b4_guard = load_csv(P_B4_GUARD)
b5_res = load_json(P_B5_RES)
b5_sum = load_csv(P_B5_SUM)
b5_pod = load_json(P_B5_POD)
b6_ana = load_json(P_B6_ANA)
manifest = load_json(P_MANIFEST)
bx1_res = load_json(P_BX1_RES)
bx1_sum = load_csv(P_BX1_SUM)
bx2_res = load_json(P_BX2_RES)
bx2_sum = load_csv(P_BX2_SUM)
bx2_pod = load_json(P_BX2_POD)
sym_v3_inf = load_csv(P_SYM_V3_INF)
sym_v3_audit = load_json(P_SYM_V3_AUDIT)
sym_repeat_audits = [load_json(path) for path in P_SYM_REPEAT_AUDITS]
above_guard_audit = load_json(P_ABOVE_GUARD_AUDIT)
above_guard_raw = load_csv(P_ABOVE_GUARD_RAW)
dpr1_summary = load_json(P_DPR1_SUMMARY)
memo_runpod_audit = load_json(P_MEMO_RUNPOD_AUDIT)
memo_runpod_inventory = load_json(P_MEMO_RUNPOD_INVENTORY)
i10_screen = load_json(P_I10_SCREEN)
i10_selector_audit = load_json(P_I10_SELECTOR_AUDIT)
cache_process = load_csv(P_CACHE_PROCESS)
cache_reuse50 = load_csv(P_CACHE_REUSE50)
family_reuse = load_csv(P_FAMILY_REUSE)
partial_summaries = {path: load_csv(path) for path in P_PARTIAL_SUMMARIES}
trace_v1 = load_json(P_TRACE_V1)
trace_v2 = load_json(P_TRACE_V2)
trace_v3 = load_json(P_TRACE_V3)
trace_v3_audit = load_json(P_TRACE_V3_AUDIT)
dep_audits = [load_json(path) for path in P_DEP_AUDITS]
dep_postflight = load_json(P_DEP_POSTFLIGHT)
workload_validation = load_json(P_WORKLOAD_VALIDATION)
memory_probe = load_json(P_MEMORY_PROBE)
dpr3_summary = load_json(P_DPR3_SUMMARY)
late_evidence = load_json(P_LATE_EVIDENCE)
content = load_json(P_CONTENT)
use_case_catalog = load_json(P_USE_CASE_CATALOG)
c16_results = load_json(P_C16_RESULTS)

D: dict = {}

# `_numbers` is the only channel through which a result reaches page prose.
# Every entry: value + display format + the file::field it came from.
NUM: dict = {}


def num(key: str, value, fmt: str, prov: str, note: str = "") -> None:
    if key in NUM:
        raise SystemExit("duplicate number token: %s" % key)
    NUM[key] = {"value": value, "fmt": fmt, "prov": prov, "note": note}


# The public master page points readers to the latest measured recognition
# milestone in main. Keep its headline figures on the same provenance-bearing
# number channel as the older benchmark results.
if c16_results["production_promotion"] is not False:
    raise SystemExit("C16 public status unexpectedly permits production promotion")
if c16_results["verification"]["status"] != "verified":
    raise SystemExit("C16 public result is not independently verified")
num("recognition.c16.source_cases", c16_results["verification"]["source_cases_replayed"], "int",
    "%s :: verification.source_cases_replayed" % rel(P_C16_RESULTS))
num("recognition.c16.controls", c16_results["verification"]["controls_replayed"], "int",
    "%s :: verification.controls_replayed" % rel(P_C16_RESULTS))
num("recognition.c16.rows", c16_results["verification"]["measurement_rows_checked"], "int",
    "%s :: verification.measurement_rows_checked" % rel(P_C16_RESULTS))
num("recognition.c16.whole_path_speedup",
    c16_results["summary"]["speedup"]["screened_whole_path_over_exhaustive"], "x3",
    "%s :: summary.speedup.screened_whole_path_over_exhaustive" % rel(P_C16_RESULTS),
    "local, task-equivalent whole path; timing is machine-specific")
num("recognition.c16.minimum_case_speedup",
    c16_results["summary"]["speedup"]["minimum_case_speedup"], "x3",
    "%s :: summary.speedup.minimum_case_speedup" % rel(P_C16_RESULTS),
    "minimum individual local case; below parity")


# ================================================================= E1
# Kernel headline: CM vs PLAIN structural CSE, three independent scopes.
# Never pooled across scopes; each row carries its own clustering basis.

e1_rows = [
    {
        "label": "Local synthetic (192 formulas)",
        "scope": "synthetic generator e3-corrected-2026-08-02.1 · Windows / Ryzen 5 PRO 5650U",
        "value": b1_acc["new_geomean_all_blocked"],
        "lo": b1_acc["new_ci95_stratified"][0],
        "hi": b1_acc["new_ci95_stratified"][1],
        "basis": "stratified-by-cell bootstrap (independent reaggregation, 4000 draws)",
        "group": "local",
    },
    {
        "label": "External EPFL (129 cones, 19 circuits)",
        "scope": "EPFL AND/INV combinational cones · Windows / Ryzen 5 PRO 5650U",
        "value": epfl_ana["secondary_blocked_cm_cse"]["geomean"],
        "lo": epfl_ana["secondary_blocked_cm_cse"]["ci95_lo"],
        "hi": epfl_ana["secondary_blocked_cm_cse"]["ci95_hi"],
        "basis": "circuit-clustered bootstrap (%d draws)" % epfl_ana["secondary_blocked_cm_cse"]["draws"],
        "group": "external",
    },
]
for pod in b6_ana["pods"]:
    name = Path(pod["pod_dir"]).name
    e1_rows.append({
        "label": "Pod %s" % name.split("_")[0],
        "scope": "Linux / AMD EPYC · %s · numpy %s" % (pod["platform"].split("-x86_64")[0], pod["numpy"]),
        "value": pod["blocked_geomean"],
        "lo": pod["ci95"][0],
        "hi": pod["ci95"][1],
        "basis": "per-pod stratified bootstrap (never pooled across pods)",
        "group": "pod",
    })

D["e1_kernel_vs_cse"] = {
    "rows": e1_rows,
    "provenance": [
        "%s :: new_geomean_all_blocked, new_ci95_stratified" % rel(P_B1_ACC),
        "%s :: secondary_blocked_cm_cse" % rel(P_EPFL_ANA),
        "%s :: pods[].blocked_geomean, pods[].ci95" % rel(P_B6_ANA),
    ],
}

num("kernel.local", b1_acc["new_geomean_all_blocked"], "ratio4",
    "%s :: new_geomean_all_blocked" % rel(P_B1_ACC))
num("kernel.local.lo", b1_acc["new_ci95_stratified"][0], "ratio3",
    "%s :: new_ci95_stratified[0]" % rel(P_B1_ACC))
num("kernel.local.hi", b1_acc["new_ci95_stratified"][1], "ratio3",
    "%s :: new_ci95_stratified[1]" % rel(P_B1_ACC))
num("kernel.local.pct", 100.0 * (1.0 - b1_acc["new_geomean_all_blocked"]), "pct0",
    "%s :: 100*(1-new_geomean_all_blocked)" % rel(P_B1_ACC))
num("kernel.epfl", epfl_ana["secondary_blocked_cm_cse"]["geomean"], "ratio4",
    "%s :: secondary_blocked_cm_cse.geomean" % rel(P_EPFL_ANA))
num("kernel.epfl.lo", epfl_ana["secondary_blocked_cm_cse"]["ci95_lo"], "ratio3",
    "%s :: secondary_blocked_cm_cse.ci95_lo" % rel(P_EPFL_ANA))
num("kernel.epfl.hi", epfl_ana["secondary_blocked_cm_cse"]["ci95_hi"], "ratio3",
    "%s :: secondary_blocked_cm_cse.ci95_hi" % rel(P_EPFL_ANA))
num("kernel.epfl.pct", 100.0 * (1.0 - epfl_ana["secondary_blocked_cm_cse"]["geomean"]), "pct0",
    "%s :: 100*(1-secondary_blocked_cm_cse.geomean)" % rel(P_EPFL_ANA))
num("kernel.pod.min", b6_ana["pod_to_pod"]["geomean_min"], "ratio3",
    "%s :: pod_to_pod.geomean_min" % rel(P_B6_ANA))
num("kernel.pod.max", b6_ana["pod_to_pod"]["geomean_max"], "ratio3",
    "%s :: pod_to_pod.geomean_max" % rel(P_B6_ANA))
num("kernel.pod.spread", b6_ana["pod_to_pod"]["geomean_spread"], "ratio3",
    "%s :: pod_to_pod.geomean_spread" % rel(P_B6_ANA))
num("kernel.pod.count", len(b6_ana["pods"]), "int",
    "%s :: len(pods)" % rel(P_B6_ANA))

# ================================================================= E2
# Kernel comparison vs CSE + sharing-aware flattening.  B1/E3 and EPFL remain
# the accepted parity workload.  The later symmetric V3 B2/B4 result is kept
# separate because it measures a distinct workload and shows a structural win.


def inference_row(scope: str, metric: str, *, corpus: str = "all", live_k: str = "all") -> dict:
    matches = [
        r for r in sym_v3_inf
        if r["scope"] == scope
        and r["metric"] == metric
        and r["corpus"] == corpus
        and r["live_k"] == live_k
    ]
    if len(matches) != 1:
        raise SystemExit(
            "expected one V3 inference row for %s/%s/%s/%s, found %d"
            % (scope, corpus, live_k, metric, len(matches))
        )
    return matches[0]


_sym_bare_all = inference_row("overall", "cm_current_over_cse_flat_current")
_sym_bare_k16 = inference_row("live_k", "cm_current_over_cse_flat_current", live_k="16")
_sym_wrap_all = inference_row("overall", "cm_wrapper_over_cse_flat_current")

e2_rows = [
    {
        "label": "Current B2/B4 V3 · formula-balanced",
        "scope": "B2/B4 frozen formulas · Windows · current selectors · exactly counterbalanced",
        "value": fnum(_sym_bare_all["paired_formula_cluster_geomean"]),
        "lo": fnum(_sym_bare_all["paired_formula_cluster_bootstrap_ci95_low"]),
        "hi": fnum(_sym_bare_all["paired_formula_cluster_bootstrap_ci95_high"]),
        "basis": "paired formula-cluster bootstrap (%s draws; one equal-weight contribution per formula)"
                 % _sym_bare_all["bootstrap_repetitions"],
        "group": "current",
    },
    {
        "label": "Local synthetic · blocked",
        "scope": "synthetic generator · Windows",
        "value": b1_acc["new_cm_vs_cse_flat_geomean"],
        "lo": None, "hi": None,
        "basis": "point geomean over %d paired rows (no CI computed in the acceptance check)" % b1_acc["n_flat_rows"],
        "group": "local",
    },
    {
        "label": "External EPFL · blocked (primary)",
        "scope": "EPFL AND/INV cones · Windows",
        "value": epfl_ana["primary_blocked_cm_cse_flat"]["geomean"],
        "lo": epfl_ana["primary_blocked_cm_cse_flat"]["ci95_lo"],
        "hi": epfl_ana["primary_blocked_cm_cse_flat"]["ci95_hi"],
        "basis": "circuit-clustered bootstrap (4000 draws)",
        "group": "external",
    },
    {
        "label": "External EPFL · round-robin",
        "scope": "EPFL AND/INV cones · Windows",
        "value": epfl_ana["round_robin_cm_cse_flat"]["geomean"],
        "lo": epfl_ana["round_robin_cm_cse_flat"]["ci95_lo"],
        "hi": epfl_ana["round_robin_cm_cse_flat"]["ci95_hi"],
        "basis": "circuit-clustered bootstrap (4000 draws) — reported beside blocked, never pooled",
        "group": "external",
    },
]
for pod in b6_ana["pods"]:
    name = Path(pod["pod_dir"]).name
    e2_rows.append({
        "label": "Pod %s" % name.split("_")[0],
        "scope": "Linux / AMD EPYC",
        "value": pod["cm_cse_flat_geomean"],
        "lo": None, "hi": None,
        "basis": "per-pod point geomean (no CI in the B6 analysis for this arm)",
        "group": "pod",
    })

D["e2_kernel_vs_cse_flat"] = {
    "rows": e2_rows,
    "materiality": epfl_ana["materiality"],
    "provenance": [
        "%s :: overall/all/all/cm_current_over_cse_flat_current" % rel(P_SYM_V3_INF),
        "%s :: acceptance, protocol, formula_count, row_count, statistical_inference" % rel(P_SYM_V3_AUDIT),
        "%s :: new_cm_vs_cse_flat_geomean, n_flat_rows" % rel(P_B1_ACC),
        "%s :: primary_blocked_cm_cse_flat, round_robin_cm_cse_flat, materiality" % rel(P_EPFL_ANA),
        "%s :: pods[].cm_cse_flat_geomean" % rel(P_B6_ANA),
    ],
}

_flat_pod = [p["cm_cse_flat_geomean"] for p in b6_ana["pods"]]
num("flat.local", b1_acc["new_cm_vs_cse_flat_geomean"], "ratio4",
    "%s :: new_cm_vs_cse_flat_geomean" % rel(P_B1_ACC))
num("flat.epfl", epfl_ana["primary_blocked_cm_cse_flat"]["geomean"], "ratio4",
    "%s :: primary_blocked_cm_cse_flat.geomean" % rel(P_EPFL_ANA))
num("flat.epfl.lo", epfl_ana["primary_blocked_cm_cse_flat"]["ci95_lo"], "ratio4",
    "%s :: primary_blocked_cm_cse_flat.ci95_lo" % rel(P_EPFL_ANA))
num("flat.epfl.hi", epfl_ana["primary_blocked_cm_cse_flat"]["ci95_hi"], "ratio4",
    "%s :: primary_blocked_cm_cse_flat.ci95_hi" % rel(P_EPFL_ANA))
num("flat.pod.min", min(_flat_pod), "ratio3", "%s :: min(pods[].cm_cse_flat_geomean)" % rel(P_B6_ANA))
num("flat.pod.max", max(_flat_pod), "ratio3", "%s :: max(pods[].cm_cse_flat_geomean)" % rel(P_B6_ANA))
num("flat.local.residual_pct", abs(100.0 * (b1_acc["new_cm_vs_cse_flat_geomean"] - 1.0)), "pct1",
    "%s :: |100*(new_cm_vs_cse_flat_geomean-1)|" % rel(P_B1_ACC))
num("mech.instr_ratio", epfl_ana["instr_ratio_cm_cse_flat_geomean"], "ratio3",
    "%s :: instr_ratio_cm_cse_flat_geomean" % rel(P_EPFL_ANA))
num("mech.execop_ratio", epfl_ana["execop_ratio_cm_cse_flat_geomean"], "ratio3",
    "%s :: execop_ratio_cm_cse_flat_geomean" % rel(P_EPFL_ANA))
num("symv3.bare.overall", fnum(_sym_bare_all["paired_formula_cluster_geomean"]), "ratio4",
    "%s :: overall/all/all/cm_current_over_cse_flat_current.paired_formula_cluster_geomean" % rel(P_SYM_V3_INF))
num("symv3.bare.overall.lo", fnum(_sym_bare_all["paired_formula_cluster_bootstrap_ci95_low"]), "ratio4",
    "%s :: overall/all/all/cm_current_over_cse_flat_current.paired_formula_cluster_bootstrap_ci95_low" % rel(P_SYM_V3_INF))
num("symv3.bare.overall.hi", fnum(_sym_bare_all["paired_formula_cluster_bootstrap_ci95_high"]), "ratio4",
    "%s :: overall/all/all/cm_current_over_cse_flat_current.paired_formula_cluster_bootstrap_ci95_high" % rel(P_SYM_V3_INF))
num("symv3.bare.k16", fnum(_sym_bare_k16["paired_formula_cluster_geomean"]), "ratio4",
    "%s :: live_k/all/16/cm_current_over_cse_flat_current.paired_formula_cluster_geomean" % rel(P_SYM_V3_INF))
num("symv3.bare.k16.lo", fnum(_sym_bare_k16["paired_formula_cluster_bootstrap_ci95_low"]), "ratio4",
    "%s :: live_k/all/16/cm_current_over_cse_flat_current.paired_formula_cluster_bootstrap_ci95_low" % rel(P_SYM_V3_INF))
num("symv3.bare.k16.hi", fnum(_sym_bare_k16["paired_formula_cluster_bootstrap_ci95_high"]), "ratio4",
    "%s :: live_k/all/16/cm_current_over_cse_flat_current.paired_formula_cluster_bootstrap_ci95_high" % rel(P_SYM_V3_INF))
num("symv3.wrapper.overall", fnum(_sym_wrap_all["paired_formula_cluster_geomean"]), "ratio4",
    "%s :: overall/all/all/cm_wrapper_over_cse_flat_current.paired_formula_cluster_geomean" % rel(P_SYM_V3_INF))
num("symv3.wrapper.overall.lo", fnum(_sym_wrap_all["paired_formula_cluster_bootstrap_ci95_low"]), "ratio4",
    "%s :: overall/all/all/cm_wrapper_over_cse_flat_current.paired_formula_cluster_bootstrap_ci95_low" % rel(P_SYM_V3_INF))
num("symv3.wrapper.overall.hi", fnum(_sym_wrap_all["paired_formula_cluster_bootstrap_ci95_high"]), "ratio4",
    "%s :: overall/all/all/cm_wrapper_over_cse_flat_current.paired_formula_cluster_bootstrap_ci95_high" % rel(P_SYM_V3_INF))
num("symv3.formulas", sym_v3_audit["formula_count"], "int",
    "%s :: formula_count" % rel(P_SYM_V3_AUDIT))
num("symv3.rows", sym_v3_audit["row_count"], "int",
    "%s :: row_count" % rel(P_SYM_V3_AUDIT))
_sym_repeat_values = [
    audit["statistical_inference"]["headline"]["paired_formula_cluster_geomean"]
    for audit in sym_repeat_audits
]
num("symv3.repeat.runs", len(_sym_repeat_values), "int",
    "%s :: statistical_inference.headline across three fresh audits" % rel(P_RERUN))
num("symv3.repeat.min", min(_sym_repeat_values), "ratio4",
    "%s :: min statistical_inference.headline.paired_formula_cluster_geomean" % rel(P_RERUN))
num("symv3.repeat.max", max(_sym_repeat_values), "ratio4",
    "%s :: max statistical_inference.headline.paired_formula_cluster_geomean" % rel(P_RERUN))
num("symv3.repeat.geomean", geomean(_sym_repeat_values), "ratio4",
    "%s :: geomean of three fresh headline paired_formula_cluster_geomean values" % rel(P_RERUN))

_memo_bx1b2 = [pod["acceptance"]["bx1_b2"]["candidate_over_baseline_geomean"]
                for pod in memo_runpod_audit["pods"]]
_memo_epfl = [pod["acceptance"]["epfl"]["candidate_over_baseline_geomean"]
              for pod in memo_runpod_audit["pods"]]
_memo_mismatches = sum(
    len(pod["acceptance"][scope][field])
    for pod in memo_runpod_audit["pods"]
    for scope in ("bx1_b2", "epfl")
    for field in ("canonical_failures", "packed_failures")
)
num("memo.pods", len(memo_runpod_audit["pods"]), "int",
    "%s :: len(pods)" % rel(P_MEMO_RUNPOD_AUDIT))
num("memo.bx1b2.min", min(_memo_bx1b2), "ratio4",
    "%s :: min pods[].acceptance.bx1_b2.candidate_over_baseline_geomean" % rel(P_MEMO_RUNPOD_AUDIT))
num("memo.bx1b2.max", max(_memo_bx1b2), "ratio4",
    "%s :: max pods[].acceptance.bx1_b2.candidate_over_baseline_geomean" % rel(P_MEMO_RUNPOD_AUDIT))
num("memo.epfl.min", min(_memo_epfl), "ratio4",
    "%s :: min pods[].acceptance.epfl.candidate_over_baseline_geomean" % rel(P_MEMO_RUNPOD_AUDIT))
num("memo.epfl.max", max(_memo_epfl), "ratio4",
    "%s :: max pods[].acceptance.epfl.candidate_over_baseline_geomean" % rel(P_MEMO_RUNPOD_AUDIT))
num("memo.mismatches", _memo_mismatches, "int",
    "%s :: total canonical_failures and packed_failures across both scopes and every pod" % rel(P_MEMO_RUNPOD_AUDIT))
num("memo.cost", memo_runpod_audit["total_cost_usd"], "usd",
    "%s :: total_cost_usd" % rel(P_MEMO_RUNPOD_AUDIT))
num("memo.postflight_pods", memo_runpod_inventory["pod_count"], "int",
    "%s :: pod_count" % rel(P_MEMO_RUNPOD_INVENTORY))

_dpr1_all = next(row for row in dpr1_summary["summaries"] if row["group"] == "all")
num("dpr1.rows", _dpr1_all["rows"], "int",
    "%s :: summaries[group=all].rows" % rel(P_DPR1_SUMMARY))
num("dpr1.time", _dpr1_all["candidate_over_baseline_geomean"], "ratio4",
    "%s :: summaries[group=all].candidate_over_baseline_geomean" % rel(P_DPR1_SUMMARY))
num("dpr1.peak", _dpr1_all["peak_bytes_ratio_geomean"], "ratio4",
    "%s :: summaries[group=all].peak_bytes_ratio_geomean" % rel(P_DPR1_SUMMARY))

def _i10_summary(arm: str, policy: str) -> dict:
    rows = [row for row in i10_selector_audit["summaries"]
            if row["arm"] == arm and row["policy"] == policy]
    if len(rows) != 1:
        raise SystemExit("expected one i10 selector summary for %s/%s" % (arm, policy))
    return rows[0]

_i10_current_raw = _i10_summary("raw", "current_k16")
_i10_feature_raw = _i10_summary("raw", "feature_ridge")
_i10_current_cm = _i10_summary("cm", "current_k16")
_i10_feature_cm = _i10_summary("cm", "feature_ridge")
num("i10.rows", i10_screen["selected_rows"], "int",
    "%s :: selected_rows" % rel(P_I10_SCREEN))
num("i10.min_k", min(i10_screen["represented_k"]), "int",
    "%s :: min(represented_k)" % rel(P_I10_SCREEN))
num("i10.max_k", max(i10_screen["represented_k"]), "int",
    "%s :: max(represented_k)" % rel(P_I10_SCREEN))
num("i10.current.raw", _i10_current_raw["regret_geomean"], "ratio4",
    "%s :: summaries[raw/current_k16].regret_geomean" % rel(P_I10_SELECTOR_AUDIT))
num("i10.current.cm", _i10_current_cm["regret_geomean"], "ratio4",
    "%s :: summaries[cm/current_k16].regret_geomean" % rel(P_I10_SELECTOR_AUDIT))
num("i10.feature.raw", _i10_feature_raw["regret_geomean"], "ratio4",
    "%s :: summaries[raw/feature_ridge].regret_geomean" % rel(P_I10_SELECTOR_AUDIT))
num("i10.feature.cm", _i10_feature_cm["regret_geomean"], "ratio4",
    "%s :: summaries[cm/feature_ridge].regret_geomean" % rel(P_I10_SELECTOR_AUDIT))
num("i10.feature.raw.cat", _i10_feature_raw["catastrophic_ge_2_count"], "int",
    "%s :: summaries[raw/feature_ridge].catastrophic_ge_2_count" % rel(P_I10_SELECTOR_AUDIT))
num("i10.feature.cm.cat", _i10_feature_cm["catastrophic_ge_2_count"], "int",
    "%s :: summaries[cm/feature_ridge].catastrophic_ge_2_count" % rel(P_I10_SELECTOR_AUDIT))

# ================================================================= E3
# Local synthetic strata: live_k, then the family x shape interaction grid.
# The B1 summary carries `live_k=K`, `live_k=K/family=F`, `live_k=K/shape=S`,
# `family=F/shape=S` and `all`. There are NO family-only or shape-only marginal
# rows, so the family/shape view is the interaction grid that actually exists.

strata, cross = [], []
for r in b1_sum:
    if r["schedule"] != "blocked":
        continue
    g = r["group"]
    rec = {
        "group": g,
        "n": int(r["n_formulas"]),
        "geomean": fnum(r["geomean"]),
        "lo": fnum(r["ci95_lo"]),
        "hi": fnum(r["ci95_hi"]),
        "basis": r["bootstrap"],
    }
    if g.startswith("live_k=") and "/" not in g:
        rec["live_k"] = int(g.split("=")[1])
        strata.append(rec)
    elif g.startswith("family=") and "/shape=" in g:
        fam, shp = g.split("/")
        rec["family"] = fam.split("=")[1]
        rec["shape"] = shp.split("=")[1]
        cross.append(rec)

D["e3_local_strata"] = {
    "by_live_k": sorted(strata, key=lambda r: r["live_k"]),
    "by_family_shape": cross,
    "families": sorted({c["family"] for c in cross}),
    "shapes": sorted({c["shape"] for c in cross}),
    "headline": {
        "geomean": b1_acc["new_geomean_all_blocked"],
        "lo": b1_acc["new_ci95_stratified"][0],
        "hi": b1_acc["new_ci95_stratified"][1],
        "identity_exact": b1_acc["identity_fields_exact"],
        "n_identity_mismatches": b1_acc["n_identity_mismatches"],
        "archived_recomputed": b1_acc["archived_geomean_recomputed_from_raw"],
        "archived_ci": b1_acc["archived_ci"],
        "ci_overlap_vs_archive": b1_acc["ci_overlap_vs_archive"],
    },
    "provenance": [
        "%s :: rows where schedule=blocked, group in {live_k=K, family=F/shape=S}" % rel(P_B1_SUM),
        "%s :: headline block" % rel(P_B1_ACC),
    ],
}
num("b1.n_formulas", len(b1_res["formulas"]), "int", "%s :: len(formulas)" % rel(P_B1_RES))
num("b1.identity_mismatches", b1_acc["n_identity_mismatches"], "int",
    "%s :: n_identity_mismatches" % rel(P_B1_ACC))

# ================================================================= E4
# EPFL per-circuit (both arms), plus semantic-support buckets.

D["e4_epfl_per_circuit"] = {
    "circuits": [
        {
            "circuit": c["circuit"],
            "category": c["category"],
            "n": c["n_formulas"],
            "cm_cse_flat": c["geomean_cm_cse_flat"],
            "cm_cse": c["geomean_cm_cse"],
        }
        for c in epfl_ana["per_circuit"]
    ],
    "by_sem_bucket": [
        {"bucket": k, "n": v["n"], "cm_cse_flat": v["geomean_cm_cse_flat"]}
        for k, v in epfl_ana["by_sem_bucket"].items()
    ],
    "mechanism": {
        "instr_ratio_cm_cse_flat": epfl_ana["instr_ratio_cm_cse_flat_geomean"],
        "execop_ratio_cm_cse_flat": epfl_ana["execop_ratio_cm_cse_flat_geomean"],
    },
    "n_ok": epfl_ana["n_ok"],
    "n_circuits": epfl_ana["n_circuits"],
    "n_guard_skipped": epfl_ana["n_guard_skipped"],
    "provenance": [
        "%s :: per_circuit[], by_sem_bucket, instr_ratio_cm_cse_flat_geomean, execop_ratio_cm_cse_flat_geomean" % rel(P_EPFL_ANA),
        "%s :: same values, CSV mirror" % rel(P_EPFL_SUM),
    ],
}
num("epfl.n_cones", epfl_ana["n_ok"], "int", "%s :: n_ok" % rel(P_EPFL_ANA))
num("epfl.n_circuits", epfl_ana["n_circuits"], "int", "%s :: n_circuits" % rel(P_EPFL_ANA))
num("epfl.n_aig_files", len(epfl_prov["aig_files"]), "int",
    "%s :: len(aig_files)" % rel(P_EPFL_PROV))
num("epfl.clone_commit", epfl_prov["clone_commit_sha"][:10], "text",
    "%s :: clone_commit_sha" % rel(P_EPFL_PROV))
num("epfl.corpus_sha", manifest["corpora_sha256"]["epfl_corpus"][:12], "text",
    "%s :: corpora_sha256.epfl_corpus" % rel(P_MANIFEST))

# ================================================================= E5
# Cross-platform pod replication (per-pod, never pooled).

D["e5_pods"] = {
    "pods": [
        {
            "label": Path(p["pod_dir"]).name.split("_")[0],
            "dir": p["pod_dir"].replace("\\", "/"),
            "blocked": p["blocked_geomean"],
            "lo": p["ci95"][0],
            "hi": p["ci95"][1],
            "rr": p["rr_geomean"],
            "cm_cse_flat": p["cm_cse_flat_geomean"],
            "identity_exact": p["identity_exact"],
            "corpus_sha_ok": p["corpus_sha256_ok"],
            "ci_excludes_parity": p["ci_excludes_parity"],
            "platform": p["platform"],
            "numpy": p["numpy"],
            "n_formulas": p["n_formulas"],
        }
        for p in b6_ana["pods"]
    ],
    "local_reference": b6_ana["local_reference_geomean"],
    "spread": b6_ana["pod_to_pod"],
    "verdict": b6_ana["verdict"],
    "provenance": ["%s :: pods[], pod_to_pod, local_reference_geomean, verdict" % rel(P_B6_ANA)],
}

# ================================================================= E6/E7
# Wrapper boundary (REVISED claim). CM wrapper / bare BitSet, by live_k.

b2_cached = [r for r in b2_sum if r["regime"] == "cached"]
b2_unc = {int(r["live_k"]): r for r in b2_sum if r["regime"] == "uncached_warmenv"}

D["e6_wrapper_ratio"] = {
    "rows": [
        {
            "live_k": int(r["live_k"]),
            "n": int(r["n_formulas"]),
            "cached_median": fnum(r["ratio_median"]),
            "cached_geomean": fnum(r["ratio_geomean"]),
            "cached_p10": fnum(r["ratio_p10"]),
            "cached_p90": fnum(r["ratio_p90"]),
            "uncached_median": fnum(b2_unc[int(r["live_k"])]["ratio_median"]) if int(r["live_k"]) in b2_unc else None,
            "uncached_geomean": fnum(b2_unc[int(r["live_k"])]["ratio_geomean"]) if int(r["live_k"]) in b2_unc else None,
        }
        for r in b2_cached
    ],
    "engine_note": "k=4 rows run the bigint/BitSet fallback (words engine engages at k>=6); uncached warmenv is not separable at k=4 and is recorded skipped.",
    "provenance": ["%s :: regime in {cached, uncached_warmenv}" % rel(P_B2_SUM)],
}

D["e7_wrapper_cost"] = {
    "rows": [
        {
            "live_k": int(r["live_k"]),
            "cm_wrapper_us": fnum(r["cm_wrapper_us_median"]),
            "bitset_us": fnum(r["bitset_us_median"]),
            "overhead_us": fnum(r["wrapper_overhead_us_median"]),
        }
        for r in b2_cached
    ],
    "provenance": [
        "%s :: cm_wrapper_us_median, bitset_us_median, wrapper_overhead_us_median (cached rows)" % rel(P_B2_SUM),
        "%s :: formulas[].cached_cm_wrapper_us / cached_bitset_us (raw)" % rel(P_B2_RES),
    ],
}

_b2_by_k = {r["live_k"]: r for r in D["e6_wrapper_ratio"]["rows"]}
_ovh = [r["overhead_us"] for r in D["e7_wrapper_cost"]["rows"] if r["overhead_us"] is not None]
num("wrap.k4.median", _b2_by_k[4]["cached_median"], "x1", "%s :: live_k=4 cached ratio_median" % rel(P_B2_SUM))
num("wrap.k16.median", _b2_by_k[16]["cached_median"], "x2", "%s :: live_k=16 cached ratio_median" % rel(P_B2_SUM))
num("wrap.k16.geomean", _b2_by_k[16]["cached_geomean"], "x2", "%s :: live_k=16 cached ratio_geomean" % rel(P_B2_SUM))
num("wrap.min_median", min(r["cached_median"] for r in D["e6_wrapper_ratio"]["rows"]), "x2",
    "%s :: min over cached rows of ratio_median" % rel(P_B2_SUM))
num("wrap.max_k", max(r["live_k"] for r in D["e6_wrapper_ratio"]["rows"]), "int",
    "%s :: max(live_k)" % rel(P_B2_SUM))
num("wrap.ovh.min", min(_ovh), "us0", "%s :: min(wrapper_overhead_us_median)" % rel(P_B2_SUM))
num("wrap.ovh.max", max(_ovh), "us0", "%s :: max(wrapper_overhead_us_median)" % rel(P_B2_SUM))
num("wrap.k16.bitset_us", D["e7_wrapper_cost"]["rows"][-1]["bitset_us"], "us0",
    "%s :: live_k=16 bitset_us_median" % rel(P_B2_SUM))
num("wrap.k16.cm_us", D["e7_wrapper_cost"]["rows"][-1]["cm_wrapper_us"], "us0",
    "%s :: live_k=16 cm_wrapper_us_median" % rel(P_B2_SUM))
num("wrap.uncached.min", min(r["uncached_median"] for r in D["e6_wrapper_ratio"]["rows"] if r["uncached_median"]), "x1",
    "%s :: min(uncached_warmenv ratio_median)" % rel(P_B2_SUM))
num("wrap.uncached.max", max(r["uncached_median"] for r in D["e6_wrapper_ratio"]["rows"] if r["uncached_median"]), "x1",
    "%s :: max(uncached_warmenv ratio_median)" % rel(P_B2_SUM))

# ================================================================= E8
# Ambient-n irrelevance (B4, same protocol as the V4 C1 experiment).

D["e8_ambient_n"] = {
    "rows": [
        {
            "live_k": int(r["live_k"]),
            "ambient_n": int(r["ambient_n"]),
            "n": int(r["n_formulas"]),
            "geomean": fnum(r["paired_ratio_geomean"]),
            "median": fnum(r["paired_ratio_median"]),
            "p10": fnum(r["paired_ratio_p10"]),
            "p90": fnum(r["paired_ratio_p90"]),
            "cm_us": fnum(r["cm_us_median"]),
            "bitset_us": fnum(r["bitset_us_median"]),
        }
        for r in b4_head
    ],
    "provenance": ["%s :: all rows" % rel(P_B4_HEAD)],
}
_b4g = [r["geomean"] for r in D["e8_ambient_n"]["rows"]]
num("b4.geomean.min", min(_b4g), "x2", "%s :: min(paired_ratio_geomean)" % rel(P_B4_HEAD))
num("b4.geomean.max", max(_b4g), "x2", "%s :: max(paired_ratio_geomean)" % rel(P_B4_HEAD))
_b4_k16 = [r["geomean"] for r in D["e8_ambient_n"]["rows"] if r["live_k"] == 16]
num("b4.k16.spread", max(_b4_k16) - min(_b4_k16), "ratio3",
    "%s :: max-min of paired_ratio_geomean at live_k=16 across ambient n" % rel(P_B4_HEAD))
num("b4.ambient_ns", ", ".join(str(x) for x in sorted({r["ambient_n"] for r in D["e8_ambient_n"]["rows"]})),
    "text", "%s :: distinct ambient_n" % rel(P_B4_HEAD))

# ================================================================= E9
# Guard / decline correctness.

guard_rows = [
    {
        "n": int(r["n"]),
        "depth": int(r["depth"]),
        "trials": int(r["trials"]),
        "median_live_k": fnum(r["median_live_k"]),
        "min_live_k": int(r["min_live_k"]),
        "max_live_k": int(r["max_live_k"]),
        "declined_rate": fnum(r["declined_rate"]),
        "wrong_guard": int(r["wrong_guard_count"]),
        "oversized": int(r["oversized_output_count"]),
    }
    for r in b4_guard
]
D["e9_guard"] = {
    "rows": guard_rows,
    "totals": {
        "trials": sum(r["trials"] for r in guard_rows),
        "wrong_guard": sum(r["wrong_guard"] for r in guard_rows),
        "oversized": sum(r["oversized"] for r in guard_rows),
    },
    "provenance": ["%s :: all rows (totals summed by this script)" % rel(P_B4_GUARD)],
}
num("guard.trials", D["e9_guard"]["totals"]["trials"], "int",
    "%s :: sum(trials) over 15 cells" % rel(P_B4_GUARD))
num("guard.wrong", D["e9_guard"]["totals"]["wrong_guard"], "int",
    "%s :: sum(wrong_guard_count)" % rel(P_B4_GUARD))
num("guard.oversized", D["e9_guard"]["totals"]["oversized"], "int",
    "%s :: sum(oversized_output_count)" % rel(P_B4_GUARD))
_d8 = [r["declined_rate"] for r in guard_rows if r["depth"] == 8]
num("guard.depth8.min_pct", 100.0 * min(_d8), "pct0",
    "%s :: min(declined_rate) at depth=8" % rel(P_B4_GUARD))
num("guard.depth8.max_pct", 100.0 * max(_d8), "pct0",
    "%s :: max(declined_rate) at depth=8" % rel(P_B4_GUARD))
_d4 = [r["median_live_k"] for r in guard_rows if r["depth"] == 4]
num("guard.depth4.medk.min", min(_d4), "num1", "%s :: min(median_live_k) at depth=4" % rel(P_B4_GUARD))
num("guard.depth4.medk.max", max(_d4), "num1", "%s :: max(median_live_k) at depth=4" % rel(P_B4_GUARD))
# The guard threshold is a protocol constant rather than a measurement, so read
# it out of the driver instead of hard-coding it here — a driver change then
# either updates the page or fails the build.
P_B4_DRIVER = DELIV / "cm_b4_guard_family_sweep_2026_08_03.py"
_guard_k = re.search(r"max_full_output_vars\s*=\s*(\d+)", P_B4_DRIVER.read_text(encoding="utf-8"))
if not _guard_k:
    raise SystemExit("could not read max_full_output_vars from %s" % rel(P_B4_DRIVER))
num("guard.k", int(_guard_k.group(1)), "int",
    "%s :: max_full_output_vars (the explicit-output guard; the same driver's "
    "wrong-guard predicate is `live_k <= 16`)" % rel(P_B4_DRIVER))
_above_ks = sorted({int(row["live_k"]) for row in above_guard_raw})
num("guard.followup.cases", above_guard_audit["acceptance"]["completed_cases"], "int",
    "%s :: acceptance.completed_cases" % rel(P_ABOVE_GUARD_AUDIT))
num("guard.followup.min_k", min(_above_ks), "int",
    "%s :: min(live_k)" % rel(P_ABOVE_GUARD_RAW))
num("guard.followup.max_k", max(_above_ks), "int",
    "%s :: max(live_k)" % rel(P_ABOVE_GUARD_RAW))
num("guard.followup.mismatches", above_guard_audit["acceptance"]["mismatch_count"], "int",
    "%s :: acceptance.mismatch_count" % rel(P_ABOVE_GUARD_AUDIT))
num("guard.followup.timeouts", above_guard_audit["acceptance"]["timeout_count"], "int",
    "%s :: acceptance.timeout_count" % rel(P_ABOVE_GUARD_AUDIT))
num("guard.followup.wrapper_non_refusals",
    above_guard_audit["acceptance"]["wrapper_non_refusal_count"], "int",
    "%s :: acceptance.wrapper_non_refusal_count" % rel(P_ABOVE_GUARD_AUDIT))

# ================================================================= E10
# Compile / DAG scaling: prep vs unfolded occurrences and vs structural nodes.

b3_cases = [
    {
        "id": r["id"],
        "family": r["case_family"],
        "structural_nodes": int(r["structural_dag_nodes"]),
        "unfolded": int(r["unfolded_occurrences"]),
        "sharing_factor": fnum(r["sharing_factor"]),
        "cm_prep_us": fnum(r["cm_prep_us"]),
        "cse_flat_prep_us": fnum(r["cse_flat_prep_us"]),
        "prep_ratio_cm_vs_cse": fnum(r["prep_ratio_cm_vs_cse"]),
        "packed_equal": r["packed_equal_all_arms"] == "True",
    }
    for r in b3_sum
]
ladder = [c for c in b3_cases if c["family"] == "shared_ladder"]
pathological = max(ladder, key=lambda c: c["unfolded"])
D["e10_compile_scaling"] = {
    "cases": b3_cases,
    "pathological": pathological,
    "prep_ratio_range": [
        min(c["prep_ratio_cm_vs_cse"] for c in b3_cases),
        max(c["prep_ratio_cm_vs_cse"] for c in b3_cases),
    ],
    "n_cases": len(b3_cases),
    "all_packed_equal": all(c["packed_equal"] for c in b3_cases),
    "families": sorted({c["family"] for c in b3_cases}),
    "provenance": [
        "%s :: id, case_family, structural_dag_nodes, unfolded_occurrences, cm_prep_us, cse_flat_prep_us, prep_ratio_cm_vs_cse, packed_equal_all_arms" % rel(P_B3_SUM),
        "%s :: cases[] (same rows)" % rel(P_B3_RES),
    ],
}
num("b3.ladder.unfolded", pathological["unfolded"], "big",
    "%s :: unfolded_occurrences for %s" % (rel(P_B3_SUM), pathological["id"]))
num("b3.ladder.nodes", pathological["structural_nodes"], "int",
    "%s :: structural_dag_nodes for %s" % (rel(P_B3_SUM), pathological["id"]))
num("b3.ladder.prep_us", pathological["cm_prep_us"], "us0",
    "%s :: cm_prep_us for %s" % (rel(P_B3_SUM), pathological["id"]))
num("b3.ladder.sharing", pathological["sharing_factor"], "big",
    "%s :: sharing_factor for %s" % (rel(P_B3_SUM), pathological["id"]))
num("b3.prep_ratio.min", D["e10_compile_scaling"]["prep_ratio_range"][0], "x1",
    "%s :: min(prep_ratio_cm_vs_cse)" % rel(P_B3_SUM))
num("b3.prep_ratio.max", D["e10_compile_scaling"]["prep_ratio_range"][1], "x1",
    "%s :: max(prep_ratio_cm_vs_cse)" % rel(P_B3_SUM))
num("b3.n_cases", len(b3_cases), "int", "%s :: row count" % rel(P_B3_SUM))

# ================================================================= E11
# Prep / break-even economics. Recomputed from raw rows in BOTH corpora.

b1_forms = b1_res["formulas"]
b1_never = [f for f in b1_forms if f["never_breaks_even_vs_cse"]]
b1_finite = [f["breakeven_evals_vs_cse"] for f in b1_forms
             if not f["never_breaks_even_vs_cse"] and f["breakeven_evals_vs_cse"] is not None]
b1_prep_ratios = [f["prep_ratio_cm_vs_cse"] for f in b1_forms if f["prep_ratio_cm_vs_cse"]]

epfl_rows = [r for r in epfl_res["rows"] if r["status"] == "ok"]
epfl_never = [r for r in epfl_rows if r["never_breaks_even_vs_cse_flat"]]
epfl_finite = [r["breakeven_evals_vs_cse_flat"] for r in epfl_rows
               if not r["never_breaks_even_vs_cse_flat"] and r["breakeven_evals_vs_cse_flat"] is not None]
# Matched-baseline arm. The synthetic corpus's break-even is measured against
# PLAIN CSE; comparing it to the EPFL CSE-flat arm would be baseline-mismatched.
# The vs-plain-CSE EPFL arm is the only like-for-like comparison, and both are
# carried so neither chart has to make an unmatched claim.
epfl_never_cse = [r for r in epfl_rows if r["never_breaks_even_vs_cse"]]
epfl_finite_cse = [r["breakeven_evals_vs_cse"] for r in epfl_rows
                   if not r["never_breaks_even_vs_cse"] and r["breakeven_evals_vs_cse"] is not None]
epfl_prep_cse = geomean([r["prep_ratio_cm_vs_cse"] for r in epfl_rows if r["prep_ratio_cm_vs_cse"]])

BINS = [(0, 25), (25, 50), (50, 100), (100, 200), (200, 400), (400, 800), (800, 1e18)]
BIN_LABELS = ["0–25", "25–50", "50–100", "100–200", "200–400", "400–800", "800+"]


def histo(vals):
    out = [0] * len(BINS)
    for v in vals:
        for i, (lo, hi) in enumerate(BINS):
            if lo <= v < hi:
                out[i] += 1
                break
    return out


D["e11_breakeven"] = {
    "bin_labels": BIN_LABELS,
    "synthetic": {
        "baseline": "plain structural CSE",
        "scope": "192 synthetic formulas (B1 fresh replay)",
        "hist": histo(b1_finite),
        "n_total": len(b1_forms),
        "n_finite": len(b1_finite),
        "n_never": len(b1_never),
        "median_finite": statistics.median(b1_finite),
        "prep_multiple_geomean": geomean(b1_prep_ratios),
        "driver_reported": {
            "n_never": b1_res["breakeven"]["n_never_breaks_even_vs_cse"],
            "median": b1_res["breakeven"]["breakeven_evals_median"],
        },
    },
    "epfl": {
        "baseline": "CSE + sharing-aware flattening",
        "scope": "129 EPFL AND/INV cones",
        "hist": histo(epfl_finite),
        "n_total": len(epfl_rows),
        "n_finite": len(epfl_finite),
        "n_never": len(epfl_never),
        "median_finite": statistics.median(epfl_finite),
        "prep_multiple_geomean": epfl_ana["prep_multiple_cm_vs_cse_flat_geomean"],
        "analysis_reported": epfl_ana["breakeven_vs_cse_flat"],
    },
    "epfl_vs_plain_cse": {
        "baseline": "plain structural CSE",
        "scope": "129 EPFL AND/INV cones — the arm that matches the synthetic corpus's baseline",
        "hist": histo(epfl_finite_cse),
        "n_total": len(epfl_rows),
        "n_finite": len(epfl_finite_cse),
        "n_never": len(epfl_never_cse),
        "median_finite": statistics.median(epfl_finite_cse),
        "prep_multiple_geomean": epfl_prep_cse,
    },
    "baseline_warning": (
        "The synthetic arm is measured against plain CSE and the EPFL primary arm against CSE-flat. "
        "Those two are NOT comparable to each other. The matched comparison is synthetic-vs-plain-CSE "
        "against EPFL-vs-plain-CSE; both are plotted so no unmatched pair has to be quoted."
    ),
    "provenance": [
        "%s :: formulas[].breakeven_evals_vs_cse, .never_breaks_even_vs_cse, .prep_ratio_cm_vs_cse (histogram + median recomputed here)" % rel(P_B1_RES),
        "%s :: rows[].breakeven_evals_vs_cse_flat, .never_breaks_even_vs_cse_flat (status=ok)" % rel(P_EPFL_RES),
        "%s :: rows[].breakeven_evals_vs_cse, .never_breaks_even_vs_cse, .prep_ratio_cm_vs_cse (matched-baseline arm, recomputed here)" % rel(P_EPFL_RES),
        "%s :: prep_multiple_cm_vs_cse_flat_geomean, breakeven_vs_cse_flat" % rel(P_EPFL_ANA),
    ],
}
_bs, _be = D["e11_breakeven"]["synthetic"], D["e11_breakeven"]["epfl"]
num("be.syn.median", _bs["median_finite"], "num1s", "%s :: median of finite breakeven_evals_vs_cse" % rel(P_B1_RES))
num("be.syn.never", _bs["n_never"], "int", "%s :: count never_breaks_even_vs_cse" % rel(P_B1_RES))
num("be.syn.total", _bs["n_total"], "int", "%s :: len(formulas)" % rel(P_B1_RES))
num("be.syn.finite", _bs["n_finite"], "int", "%s :: count finite breakeven" % rel(P_B1_RES))
num("be.syn.prep", _bs["prep_multiple_geomean"], "x2", "%s :: geomean(prep_ratio_cm_vs_cse)" % rel(P_B1_RES))
num("be.epfl.median", _be["median_finite"], "num1s", "%s :: median of finite breakeven_evals_vs_cse_flat" % rel(P_EPFL_RES))
num("be.epfl.never", _be["n_never"], "int", "%s :: count never_breaks_even_vs_cse_flat" % rel(P_EPFL_RES))
num("be.epfl.total", _be["n_total"], "int", "%s :: count rows status=ok" % rel(P_EPFL_RES))
num("be.epfl.finite", _be["n_finite"], "int", "%s :: count finite breakeven" % rel(P_EPFL_RES))
num("be.epfl.prep", _be["prep_multiple_geomean"], "x2",
    "%s :: prep_multiple_cm_vs_cse_flat_geomean" % rel(P_EPFL_ANA))
num("be.epfl.never_pct", 100.0 * _be["n_never"] / _be["n_total"], "pct0",
    "%s :: 100*never/total (vs CSE-flat)" % rel(P_EPFL_RES))
_bx = D["e11_breakeven"]["epfl_vs_plain_cse"]
num("be.epfl.median.matched", _bx["median_finite"], "num1s",
    "%s :: median of finite breakeven_evals_vs_cse (matched to the synthetic arm's plain-CSE baseline)" % rel(P_EPFL_RES))
num("be.epflcse.never", _bx["n_never"], "int",
    "%s :: count never_breaks_even_vs_cse (matched baseline)" % rel(P_EPFL_RES))
num("be.epflcse.finite", _bx["n_finite"], "int",
    "%s :: count finite breakeven_evals_vs_cse" % rel(P_EPFL_RES))
num("be.epflcse.prep", _bx["prep_multiple_geomean"], "x2",
    "%s :: geomean(prep_ratio_cm_vs_cse) over status=ok rows" % rel(P_EPFL_RES))
_arch_prep = geomean([f["prep_ratio_cm_vs_cse"] for f in b1_arch_res["formulas"]
                      if f["prep_ratio_cm_vs_cse"]])
_PREP_PROV = (
    "%s :: geomean(formulas[].prep_ratio_cm_vs_cse) · "
    "%s :: geomean(formulas[].prep_ratio_cm_vs_cse) (archived run) · "
    "%s :: prep_multiple_cm_vs_cse_flat_geomean"
) % (rel(P_B1_RES), rel(P_B1_ARCH_RES), rel(P_EPFL_ANA))
num("prep.min", min(_bs["prep_multiple_geomean"], _be["prep_multiple_geomean"], _arch_prep), "x1",
    "min over the three prep-multiple geomeans — " + _PREP_PROV)
num("prep.max", max(_bs["prep_multiple_geomean"], _be["prep_multiple_geomean"], _arch_prep), "x1",
    "max over the three prep-multiple geomeans — " + _PREP_PROV)

# ================================================================= E12
# CUDD matched: CONSTRUCTION and EVALUATION are separate panels, always.

b5_rows_sum = [
    {
        "live_k": int(r["live_k"]),
        "n": int(r["n"]),
        "cm_prep_us": fnum(r["cm_prep_us_median"]),
        "cse_flat_prep_us": fnum(r["cse_flat_prep_us_median"]),
        "cudd_build_us": fnum(r["cudd_build_us_median"]),
        "cm_kernel_us": fnum(r["cm_kernel_us_median"]),
        "cse_flat_kernel_us": fnum(r["cse_flat_kernel_us_median"]),
        "cudd_eval256_us": fnum(r["cudd_eval256_us_median"]),
        "cudd_extract_full_us": fnum(r["cudd_extract_full_us_median"]),
        "cudd_dag_size": fnum(r["cudd_dag_size_median"]),
    }
    for r in b5_sum
]
b5_raw = b5_res["rows"]
D["e12_cudd"] = {
    "rows": b5_rows_sum,
    "integrity": {
        "n_rows": len(b5_raw),
        "robdd_is_cudd_all": all(r["robdd_is_cudd"] for r in b5_raw),
        "full_extraction_equal_all": all(r["cudd_full_extraction_equal"] for r in b5_raw),
        "packed_equal_cm_cse_flat_all": all(r["packed_equal_cm_cse_flat"] for r in b5_raw),
    },
    "extract_vs_kernel": [
        {"live_k": r["live_k"], "factor": r["cudd_extract_full_us"] / r["cm_kernel_us"]}
        for r in b5_rows_sum
    ],
    "pod": {
        "cpu_model": b5_pod["state"]["env"]["cpu_model"],
        "platform": b5_pod["state"]["env"]["platform"],
        "vcpu": b5_pod["vcpu_count"],
        "flavor": b5_pod["cpu_flavor"],
        "terminated": b5_pod["terminated"],
        "cudd_version": b5_res["_meta"]["cudd_version"],
        "dd_cudd": b5_res["_meta"]["dd_cudd"],
        "conventions": b5_res["_meta"]["conventions"],
        "eval_samples": b5_res["_meta"]["eval_samples"],
    },
    "provenance": [
        "%s :: all rows (medians per stratum)" % rel(P_B5_SUM),
        "%s :: rows[].robdd_is_cudd, .cudd_full_extraction_equal, .packed_equal_cm_cse_flat; _meta" % rel(P_B5_RES),
        "%s :: cpu_flavor, vcpu_count, terminated, state.env" % rel(P_B5_POD),
    ],
}
_xf = [r["factor"] for r in D["e12_cudd"]["extract_vs_kernel"]]
num("cudd.extract.min_x", min(_xf), "x0",
    "%s :: min(cudd_extract_full_us_median / cm_kernel_us_median)" % rel(P_B5_SUM))
num("cudd.extract.max_x", max(_xf), "xcomma",
    "%s :: max(cudd_extract_full_us_median / cm_kernel_us_median)" % rel(P_B5_SUM))
num("cudd.build.min_us", min(r["cudd_build_us"] for r in b5_rows_sum), "us0",
    "%s :: min(cudd_build_us_median)" % rel(P_B5_SUM))
num("cudd.build.max_us", max(r["cudd_build_us"] for r in b5_rows_sum), "us0",
    "%s :: max(cudd_build_us_median)" % rel(P_B5_SUM))
num("cudd.nodes.k16", [r for r in b5_rows_sum if r["live_k"] == 16][0]["cudd_dag_size"], "int",
    "%s :: live_k=16 cudd_dag_size_median" % rel(P_B5_SUM))
num("cudd.rows", len(b5_raw), "int", "%s :: len(rows)" % rel(P_B5_RES))
num("cudd.kernel.min_us", min(r["cm_kernel_us"] for r in b5_rows_sum), "us0",
    "%s :: min(cm_kernel_us_median)" % rel(P_B5_SUM))
num("cudd.kernel.max_us", max(r["cm_kernel_us"] for r in b5_rows_sum), "us0",
    "%s :: max(cm_kernel_us_median)" % rel(P_B5_SUM))
num("cudd.extract.k16_ms", [r for r in b5_rows_sum if r["live_k"] == 16][0]["cudd_extract_full_us"] / 1000.0,
    "ms0", "%s :: live_k=16 cudd_extract_full_us_median / 1000" % rel(P_B5_SUM))

# ================================================================= E14
# Schedule agreement: blocked vs round-robin, reported side by side, never pooled.

b1_all_blocked = next(r for r in b1_sum if r["schedule"] == "blocked" and r["group"] == "all")
b1_all_rr = next(r for r in b1_sum if r["schedule"] == "round_robin" and r["group"] == "all")
arch_blocked = next(r for r in b1_arch_sum if r["schedule"] == "blocked" and r["group"] == "all")
arch_rr = next(r for r in b1_arch_sum if r["schedule"] == "round_robin" and r["group"] == "all")

sched = [
    {"source": "Local synthetic (B1 replay)", "blocked": fnum(b1_all_blocked["geomean"]),
     "rr": fnum(b1_all_rr["geomean"]), "arm": "CM / plain CSE"},
    {"source": "Local synthetic (2026-08-02 archive)", "blocked": fnum(arch_blocked["geomean"]),
     "rr": fnum(arch_rr["geomean"]), "arm": "CM / plain CSE"},
    {"source": "External EPFL (B7)", "blocked": epfl_ana["primary_blocked_cm_cse_flat"]["geomean"],
     "rr": epfl_ana["round_robin_cm_cse_flat"]["geomean"], "arm": "CM / CSE-flat"},
]
for p in b6_ana["pods"]:
    sched.append({
        "source": "Pod %s (B6)" % Path(p["pod_dir"]).name.split("_")[0],
        "blocked": p["blocked_geomean"], "rr": p["rr_geomean"], "arm": "CM / plain CSE",
    })
for s in sched:
    s["delta_pct"] = 100.0 * (s["rr"] / s["blocked"] - 1.0)

per_cell = []
for br in b1_sum:
    if br["schedule"] != "blocked":
        continue
    rr = next((x for x in b1_sum if x["schedule"] == "round_robin" and x["group"] == br["group"]), None)
    if rr is None:
        continue
    per_cell.append({
        "group": br["group"],
        "blocked": fnum(br["geomean"]),
        "rr": fnum(rr["geomean"]),
        "delta_pct": 100.0 * (fnum(rr["geomean"]) / fnum(br["geomean"]) - 1.0),
    })

D["e14_schedule"] = {
    "rows": sched,
    "per_cell_b1": per_cell,
    "max_abs_delta_pct": max(abs(s["delta_pct"]) for s in sched),
    "max_abs_cell_delta_pct": max(abs(c["delta_pct"]) for c in per_cell),
    "provenance": [
        "%s :: schedule=blocked|round_robin, group=all and per-cell groups" % rel(P_B1_SUM),
        "%s :: schedule=blocked|round_robin, group=all (archived 2026-08-02 run, for contrast)" % rel(P_B1_ARCH),
        "%s :: primary_blocked_cm_cse_flat, round_robin_cm_cse_flat" % rel(P_EPFL_ANA),
        "%s :: pods[].blocked_geomean, pods[].rr_geomean" % rel(P_B6_ANA),
    ],
}
_pod_deltas = [s["delta_pct"] for s in sched if s["source"].startswith("Pod")]
num("sched.b1.delta_pct", [s for s in sched if "B1 replay" in s["source"]][0]["delta_pct"], "pctsign2",
    "%s :: 100*(round_robin/blocked-1), group=all" % rel(P_B1_SUM))
num("sched.b1.cell_max_pct", max(abs(c["delta_pct"]) for c in per_cell), "pct2",
    "%s :: max |100*(rr/blocked-1)| over per-cell groups" % rel(P_B1_SUM))
num("sched.arch.delta_pct", [s for s in sched if "archive" in s["source"]][0]["delta_pct"], "pctsign2",
    "%s :: 100*(round_robin/blocked-1), group=all" % rel(P_B1_ARCH))
num("sched.epfl.delta_pct", [s for s in sched if "EPFL" in s["source"]][0]["delta_pct"], "pctsign2",
    "%s :: 100*(round_robin/blocked-1)" % rel(P_EPFL_ANA))
num("sched.pod.min_pct", min(_pod_deltas), "pctsign2", "%s :: min over pods" % rel(P_B6_ANA))
num("sched.pod.max_pct", max(_pod_deltas), "pctsign2", "%s :: max over pods" % rel(P_B6_ANA))

# ================================================================= E17/E18 publication summaries
# Two visual summaries requested for the publication pages.  E17 makes the two
# claim-map discrepancies graphical; E18 derives the explicit-output growth
# curve from the guard's own live-k limit.  Neither introduces a new benchmark
# result.

_arch_be_finite = [
    f["breakeven_evals_vs_cse"] for f in b1_arch_res["formulas"]
    if not f["never_breaks_even_vs_cse"] and f["breakeven_evals_vs_cse"] is not None
]
_arch_be_never = sum(bool(f["never_breaks_even_vs_cse"]) for f in b1_arch_res["formulas"])
_sched_replay = next(s for s in sched if "B1 replay" in s["source"])
_sched_archive = next(s for s in sched if "archive" in s["source"])
_sched_epfl = next(s for s in sched if "EPFL" in s["source"])

D["e17_discrepancies"] = {
    "schedule_rows": [
        {"label": "B1 largest cell", "delta_pct": max(abs(c["delta_pct"]) for c in per_cell),
         "scope": "largest absolute per-cell schedule shift in the fresh synthetic replay"},
        {"label": "B1 all formulas", "delta_pct": abs(_sched_replay["delta_pct"]),
         "scope": "all-corpus schedule shift in the fresh synthetic replay"},
        {"label": "Archived synthetic", "delta_pct": abs(_sched_archive["delta_pct"]),
         "scope": "all-corpus schedule shift in the archived synthetic run"},
        {"label": "External EPFL", "delta_pct": abs(_sched_epfl["delta_pct"]),
         "scope": "external circuit-clustered campaign"},
        {"label": "Largest pod", "delta_pct": max(abs(x) for x in _pod_deltas),
         "scope": "largest all-corpus shift across the five Linux pods"},
    ],
    "replay_vs_archive": [
        {"metric": "Preparation multiple", "archived": _arch_prep,
         "replay": _bs["prep_multiple_geomean"], "format": "multiple"},
        {"metric": "Finite break-even median", "archived": statistics.median(_arch_be_finite),
         "replay": _bs["median_finite"], "format": "evaluations"},
        {"metric": "Never break even", "archived": _arch_be_never,
         "replay": _bs["n_never"], "format": "count", "total": _bs["n_total"]},
    ],
    "provenance": [
        "%s :: blocked|round_robin all-corpus and per-cell geomeans" % rel(P_B1_SUM),
        "%s :: blocked|round_robin all-corpus geomeans" % rel(P_B1_ARCH),
        "%s :: primary blocked and round-robin geomeans" % rel(P_EPFL_ANA),
        "%s :: pods[].blocked_geomean, pods[].rr_geomean" % rel(P_B6_ANA),
        "%s :: formulas[].prep_ratio_cm_vs_cse, .breakeven_evals_vs_cse, .never_breaks_even_vs_cse" % rel(P_B1_RES),
        "%s :: same fields (archived comparison)" % rel(P_B1_ARCH_RES),
    ],
}

_guard_limit = int(_guard_k.group(1))
_growth_k = sorted(set([4, 8, 12, _guard_limit]))
D["e18_assignment_growth"] = {
    "rows": [{"live_k": k, "assignments": 2 ** k} for k in _growth_k],
    "guard_limit": _guard_limit,
    "provenance": [
        "%s :: max_full_output_vars" % rel(P_B4_DRIVER),
        "Boolean truth-vector definition :: explicit assignments = 2^live_k",
    ],
}

# ================================================================= E15 (BX1)
# Engine crossover: recursive bigint / flat bigint / words, by live_k.

D["e15_engines"] = {
    "rows": [
        {
            "live_k": int(r["live_k"]),
            "n": int(r["n_formulas"]),
            "recursive_us": fnum(r["recursive_bigint_us_median"]),
            "flat_us": fnum(r["flat_bigint_us_median"]),
            "words_us": fnum(r["words_us_median"]),
            "flat_vs_recursive": fnum(r["flat_vs_recursive_ratio_geomean"]),
            "words_vs_flat": fnum(r["words_vs_flat_ratio_geomean"]),
            "fastest": r["fastest_engine_by_median"],
        }
        for r in bx1_sum
    ],
    "meta": {
        "n_formulas": len(bx1_res["formulas"]),
        "generator": bx1_res["_meta"]["generator_version"],
        "corpus_sha256": bx1_res["_meta"]["corpus_sha256"],
        "engines": bx1_res["_meta"]["engines"],
        "rounds": bx1_res["_meta"]["rounds"],
    },
    "provenance": [
        "%s :: all rows" % rel(P_BX1_SUM),
        "%s :: _meta, formulas[]" % rel(P_BX1_RES),
    ],
}
_bx1 = D["e15_engines"]["rows"]
_wvf = [r for r in _bx1 if r["words_vs_flat"] is not None]
num("bx1.fvr.min", min(r["flat_vs_recursive"] for r in _bx1), "ratio2",
    "%s :: min(flat_vs_recursive_ratio_geomean)" % rel(P_BX1_SUM))
num("bx1.fvr.max", max(r["flat_vs_recursive"] for r in _bx1), "ratio2",
    "%s :: max(flat_vs_recursive_ratio_geomean)" % rel(P_BX1_SUM))
num("bx1.k16.wvf", [r for r in _bx1 if r["live_k"] == 16][0]["words_vs_flat"], "ratio2",
    "%s :: live_k=16 words_vs_flat_ratio_geomean" % rel(P_BX1_SUM))
num("bx1.k6.wvf", [r for r in _bx1 if r["live_k"] == 6][0]["words_vs_flat"], "x1",
    "%s :: live_k=6 words_vs_flat_ratio_geomean" % rel(P_BX1_SUM))
num("bx1.wvf.max", max(r["words_vs_flat"] for r in _wvf), "x1",
    "%s :: max(words_vs_flat_ratio_geomean)" % rel(P_BX1_SUM))
num("bx1.last_flat_k", max(r["live_k"] for r in _bx1 if r["fastest"] == "flat_bigint"), "int",
    "%s :: max live_k where fastest_engine_by_median == flat_bigint" % rel(P_BX1_SUM))
num("bx1.first_words_k", min(r["live_k"] for r in _bx1 if r["fastest"] == "words"), "int",
    "%s :: min live_k where fastest_engine_by_median == words" % rel(P_BX1_SUM))
num("bx1.n_formulas", len(bx1_res["formulas"]), "int", "%s :: len(formulas)" % rel(P_BX1_RES))

# ================================================================= E16 (BX2)
# CUDD order sensitivity. Build window here = conversion only (Audit V4
# convention) - NOT comparable to B5's manager-inclusive cudd_build_us.

bx2_pure = {}
for k in (8, 12, 16):
    sums = [sum(p["build_us"] for p in row["per_order"])
            for row in bx2_res["rows"] if row["stratum_live_k"] == k]
    bx2_pure[k] = statistics.median(sums)

D["e16_cudd_orders"] = {
    "rows": [
        {
            "live_k": int(r["live_k"]),
            "n": int(r["n"]),
            "fixed_build_us": fnum(r["fixed_build_us_median"]),
            "fixed_nodes": fnum(r["fixed_nodes_median"]),
            "best10_build_us": fnum(r["best10_selected_build_us_median"]),
            "best10_nodes": fnum(r["best10_selected_nodes_median"]),
            "reorder_build_us": fnum(r["reorder_build_us_median"]),
            "reorder_nodes": fnum(r["reorder_nodes_median"]),
            "node_ratio_best10": fnum(r["node_ratio_best10_vs_fixed_median"]),
            "node_ratio_reorder": fnum(r["node_ratio_reorder_vs_fixed_median"]),
            "pure_10build_sum_us": bx2_pure[int(r["live_k"])],
            "search_total_recorded_us": fnum(r["order_search_total_us_median"]),
        }
        for r in bx2_sum
    ],
    "integrity": {
        "n_rows": len(bx2_res["rows"]),
        "robdd_is_cudd_all": all(r["robdd_is_cudd"] for r in bx2_res["rows"]),
        "sampled_checks_all_ok": all(r["sampled_checks_all_ok"] for r in bx2_res["rows"]),
        "n_orders": bx2_res["_meta"]["n_orders"],
        "correctness_mode": bx2_res["_meta"]["correctness_mode"],
        "selection_rule": bx2_res["_meta"]["selection_rule"],
    },
    "build_window_note": (
        "Build window here is expression-to-BDD conversion only (Audit V4 convention), "
        "AFTER manager creation and variable declaration. B5's cudd_build_us includes "
        "fresh-manager creation and declaration. Both are real costs answering different "
        "questions and are never plotted on the same axis."
    ),
    "pod": {
        "platform": bx2_res["_meta"]["platform"],
        "terminated": bx2_pod.get("terminated"),
        "cpu_flavor": bx2_pod.get("cpu_flavor"),
    },
    "provenance": [
        "%s :: all rows" % rel(P_BX2_SUM),
        "%s :: rows[].per_order[].build_us (pure 10-build sums computed here), _meta" % rel(P_BX2_RES),
        "%s :: terminated, cpu_flavor" % rel(P_BX2_POD),
    ],
}
_bx2 = D["e16_cudd_orders"]["rows"]
num("bx2.node_saving.min_pct", 100.0 * (1.0 - max(r["node_ratio_best10"] for r in _bx2)), "pct0",
    "%s :: 100*(1-max(node_ratio_best10_vs_fixed_median))" % rel(P_BX2_SUM))
num("bx2.node_saving.max_pct", 100.0 * (1.0 - min(r["node_ratio_best10"] for r in _bx2)), "pct0",
    "%s :: 100*(1-min(node_ratio_best10_vs_fixed_median))" % rel(P_BX2_SUM))
num("bx2.search_x.min", min(r["pure_10build_sum_us"] / r["fixed_build_us"] for r in _bx2), "x1",
    "%s + %s :: median(sum per_order build_us) / fixed_build_us_median" % (rel(P_BX2_RES), rel(P_BX2_SUM)))
num("bx2.search_x.max", max(r["pure_10build_sum_us"] / r["fixed_build_us"] for r in _bx2), "x1",
    "%s + %s :: median(sum per_order build_us) / fixed_build_us_median" % (rel(P_BX2_RES), rel(P_BX2_SUM)))
num("bx2.reorder_ratio", max(r["node_ratio_reorder"] for r in _bx2), "ratio2",
    "%s :: node_ratio_reorder_vs_fixed_median (identical at every stratum)" % rel(P_BX2_SUM))
num("bx2.max_nodes", max(r["fixed_nodes"] for r in _bx2), "int",
    "%s :: max(fixed_nodes_median)" % rel(P_BX2_SUM))
num("bx2.n_orders", bx2_res["_meta"]["n_orders"], "int", "%s :: _meta.n_orders" % rel(P_BX2_RES))

# ================================================================= E19
# Accepted 2026-08-26/27 evidence that narrows formerly open website claims.
# These are synthetic/reliability/safety/dependency results, not a new kernel
# headline.  Keep their evidence roles explicit and do not blend their windows.

_cache_process_rows = {int(r["n_vars"]): r for r in cache_process}
_cache_reuse_rows = {int(r["n_vars"]): r for r in cache_reuse50}
_cache_whole = {
    k: fnum(r["cm_persistent_cache_no_reinflate_time_s_median"]) / fnum(r["bitset_time_s_median"])
    for k, r in _cache_process_rows.items()
}
_cache_exec = {
    k: fnum(r["ratio_cm_hybrid_no_reinflate_cached_over_bitset_cached"])
    for k, r in _cache_reuse_rows.items()
}
_family_ratios = [fnum(r["ratio_cm_cache_over_bitset_median"]) for r in family_reuse]
_partial_rows = [(path, r) for path, rows in partial_summaries.items() for r in rows]
_partial_speedups = [fnum(r["speedup_cm_cache_vs_cm_no_cache_median"]) for _, r in _partial_rows]

def partial_k16(fraction: float) -> tuple[Path, dict]:
    matches = [
        (path, r) for path, r in _partial_rows
        if int(r["n_vars"]) == 16
        and int(float(r["partial_context_count"])) == 500
        and abs(fnum(r["partial_fixed_var_fraction_median_median"]) - fraction) < 1e-12
    ]
    if len(matches) != 1:
        raise SystemExit("expected one n=16,c=500 partial-context row for fraction %s; got %d" % (fraction, len(matches)))
    return matches[0]


_partial_near = {}
for _fraction in (0.25, 0.50, 0.75):
    _path, _row = partial_k16(_fraction)
    _partial_near[_fraction] = {
        "source": rel(_path),
        "remaining_vars": int(float(_row["partial_remaining_var_count_median_median"])),
        "bitset_total_s": fnum(_row["partial_bitset_full_recompute_total_s_median"]),
        "cm_cache_total_s": fnum(_row["partial_cm_cache_total_s_median"]),
        "ratio": fnum(_row["partial_cm_cache_total_s_median"]) / fnum(_row["partial_bitset_full_recompute_total_s_median"]),
        "trials": int(float(_row["trials"])),
    }

_final_dep = dep_audits[-1]
_final_dep_commands = _final_dep["pods"][0]["state"]["commands"]
_memory_multiples = [case["peak_over_estimated_temporary_median"] for case in memory_probe["cases"]]
_memory_refusals = sum(bool(case["refusal_before_materialization"]) for case in memory_probe["cases"])
_focused = junit_counts(P_FOCUSED_JUNIT)
_full = junit_counts(P_FULL_JUNIT)

D["e19_current_evidence"] = {
    "cache": {
        "kind": "process-local synthetic all-hit cache; not durable persistence",
        "whole_call_cm_over_bitset": _cache_whole,
        "execution_only_cm_over_bitset_50": _cache_exec,
        "evaluations": int(float(next(iter(_cache_reuse_rows.values()))["cm_eval_repeat_median"])),
    },
    "family": {
        "kind": "synthetic related-expression families",
        "cm_cache_over_bitset": [
            {
                "live_k": int(r["n_vars"]),
                "family_size": int(r["family_size"]),
                "ratio": fnum(r["ratio_cm_cache_over_bitset_median"]),
            }
            for r in family_reuse
        ],
    },
    "partial_context": {
        "kind": "three-trial synthetic sliding-window grid; no native CUDD restriction comparator",
        "cache_vs_uncached_speedup_min": min(_partial_speedups),
        "cache_vs_uncached_speedup_max": max(_partial_speedups),
        "near_parity_n16_c500": _partial_near,
    },
    "tracing": {
        "kind": "anonymous metrics-only diagnostic; not replayable workload capture",
        "full_rate_ratios": [trace_v1["ratio_median"], trace_v2["ratio_median"]],
        "sample_every": trace_v3["sample_every"],
        "sampled_ratio": trace_v3["ratio_median"],
        "sampled_ratio_gate_pass": trace_v3["ratio_gate_pass"],
        "event_gate_pass": trace_v3["event_overhead_gate_pass"],
        "exact_mismatches": trace_v3["exact_mismatches"],
        "drops": trace_v3["trace_dropped_events"],
        "io_errors": trace_v3["trace_io_errors"],
        "content_modes": trace_v3_audit["content_modes"],
        "logical_replay_only": trace_v3_audit["logical_replay_only"],
    },
    "workload_intake": workload_validation,
    "dependency_feasibility": {
        "attempts": sum(len(a["pods"]) for a in dep_audits),
        "cumulative_cost_usd": _final_dep["total_cost_usd"],
        "postflight_pods": dep_postflight["pod_count"],
        "astutils_wheel_built": _final_dep_commands["build_astutils_wheel"]["returncode"] == 0,
        "target_resolution_returncode": _final_dep_commands["download_binary_targets"]["returncode"],
        "verdict": _final_dep["verdict"],
    },
    "temporary_memory": {
        "measurement_scope": memory_probe["measurement_scope"],
        "cases": memory_probe["cases"],
        "refusal_before_materialization_count": _memory_refusals,
        "policy": late_evidence["temporary_memory_policy"],
    },
    "provenance_consolidation": {
        **late_evidence["provenance_consolidation"],
        "smoke_ratio": dpr3_summary["ratio_median"],
        "exact_mismatches": dpr3_summary["exact_mismatches"],
        "ratio_gate_pass": dpr3_summary["ratio_gate_pass"],
        "event_gate_pass": dpr3_summary["event_overhead_gate_pass"],
    },
    "validation": {"focused": _focused, "full": _full},
    "canonicality_boundary": late_evidence["canonicality_boundary"],
    "provenance": [
        "%s :: cm_persistent_cache_no_reinflate_time_s_median / bitset_time_s_median" % rel(P_CACHE_PROCESS),
        "%s :: ratio_cm_hybrid_no_reinflate_cached_over_bitset_cached" % rel(P_CACHE_REUSE50),
        "%s :: ratio_cm_cache_over_bitset_median" % rel(P_FAMILY_REUSE),
        "partial context summary CSVs :: speedup and total-time fields, selected by n/context count/fixed fraction",
        "%s, %s, %s :: ratio_median and gate fields" % (rel(P_TRACE_V1), rel(P_TRACE_V2), rel(P_TRACE_V3)),
        "%s :: validation and readiness fields" % rel(P_WORKLOAD_VALIDATION),
        "%s :: pods, total_cost_usd, build_astutils_wheel, download_binary_targets" % rel(P_DEP_AUDITS[-1]),
        "%s :: cases[] and measurement_scope" % rel(P_MEMORY_PROBE),
        "%s :: ratio and exactness/gate fields" % rel(P_DPR3_SUMMARY),
        "%s and %s :: testsuite attributes plus testcase count" % (rel(P_FOCUSED_JUNIT), rel(P_FULL_JUNIT)),
        "%s :: section-level accepted non-benchmark evidence extraction" % rel(P_LATE_EVIDENCE),
    ],
}

num("cache.whole.min", min(_cache_whole.values()), "x2", "%s :: min(cm_persistent_cache_no_reinflate_time_s_median / bitset_time_s_median)" % rel(P_CACHE_PROCESS))
num("cache.whole.max", max(_cache_whole.values()), "x2", "%s :: max(cm_persistent_cache_no_reinflate_time_s_median / bitset_time_s_median)" % rel(P_CACHE_PROCESS))
for _k in sorted(_cache_exec):
    num("cache.exec.k%d" % _k, _cache_exec[_k], "x2", "%s :: n_vars=%d ratio_cm_hybrid_no_reinflate_cached_over_bitset_cached" % (rel(P_CACHE_REUSE50), _k))
num("cache.evals", D["e19_current_evidence"]["cache"]["evaluations"], "int", "%s :: cm_eval_repeat_median" % rel(P_CACHE_REUSE50))
num("family.bitset.min", min(_family_ratios), "x2", "%s :: min(ratio_cm_cache_over_bitset_median)" % rel(P_FAMILY_REUSE))
num("family.bitset.max", max(_family_ratios), "x2", "%s :: max(ratio_cm_cache_over_bitset_median)" % rel(P_FAMILY_REUSE))
num("context.speedup.min", min(_partial_speedups), "x2", "partial context summary CSVs :: min(speedup_cm_cache_vs_cm_no_cache_median)")
num("context.speedup.max", max(_partial_speedups), "x2", "partial context summary CSVs :: max(speedup_cm_cache_vs_cm_no_cache_median)")
for _fraction, _item in _partial_near.items():
    _name = str(_fraction).replace("0.", "f")
    num("context.%s.ratio" % _name, _item["ratio"], "ratio3", "%s :: n_vars=16,c=500 cm_cache_total / bitset_full_recompute_total" % _item["source"])
num("context.trials", min(item["trials"] for item in _partial_near.values()), "int", "selected n=16,c=500 partial context rows :: trials")
num("trace.v1.ratio", trace_v1["ratio_median"], "ratio4", "%s :: ratio_median" % rel(P_TRACE_V1))
num("trace.v2.ratio", trace_v2["ratio_median"], "ratio4", "%s :: ratio_median" % rel(P_TRACE_V2))
num("trace.v3.ratio", trace_v3["ratio_median"], "ratio4", "%s :: ratio_median" % rel(P_TRACE_V3))
num("trace.sample_every", trace_v3["sample_every"], "int", "%s :: sample_every" % rel(P_TRACE_V3))
num("trace.mismatches", trace_v3["exact_mismatches"], "int", "%s :: exact_mismatches" % rel(P_TRACE_V3))
num("trace.drops", trace_v3["trace_dropped_events"], "int", "%s :: trace_dropped_events" % rel(P_TRACE_V3))
num("trace.io_errors", trace_v3["trace_io_errors"], "int", "%s :: trace_io_errors" % rel(P_TRACE_V3))
num("workload.blockers", len(workload_validation["blockers"]), "int", "%s :: len(blockers)" % rel(P_WORKLOAD_VALIDATION))
num("dependency.attempts", D["e19_current_evidence"]["dependency_feasibility"]["attempts"], "int", "three dependency audit JSON files :: sum(len(pods))")
num("dependency.cost", _final_dep["total_cost_usd"], "usd", "%s :: total_cost_usd" % rel(P_DEP_AUDITS[-1]))
num("dependency.postflight_pods", dep_postflight["pod_count"], "int", "%s :: pod_count" % rel(P_DEP_POSTFLIGHT))
num("memory.cases", len(memory_probe["cases"]), "int", "%s :: len(cases)" % rel(P_MEMORY_PROBE))
num("memory.multiple.min", min(_memory_multiples), "x2", "%s :: min(cases[].peak_over_estimated_temporary_median)" % rel(P_MEMORY_PROBE))
num("memory.multiple.max", max(_memory_multiples), "x2", "%s :: max(cases[].peak_over_estimated_temporary_median)" % rel(P_MEMORY_PROBE))
num("memory.refusals", _memory_refusals, "int", "%s :: count(cases[].refusal_before_materialization)" % rel(P_MEMORY_PROBE))
num("memory.proposed.benchmark_mib", late_evidence["temporary_memory_policy"]["proposed_benchmark_remote_mib"], "int", "%s :: temporary_memory_policy.proposed_benchmark_remote_mib" % rel(P_LATE_EVIDENCE))
num("memory.proposed.direct_mib", late_evidence["temporary_memory_policy"]["proposed_direct_mib"], "int", "%s :: temporary_memory_policy.proposed_direct_mib" % rel(P_LATE_EVIDENCE))
num("dpr3.helpers.before", late_evidence["provenance_consolidation"]["duplicate_helpers_before"], "int", "%s :: provenance_consolidation.duplicate_helpers_before" % rel(P_LATE_EVIDENCE))
num("dpr3.helpers.after", late_evidence["provenance_consolidation"]["streaming_helpers_after"], "int", "%s :: provenance_consolidation.streaming_helpers_after" % rel(P_LATE_EVIDENCE))
num("dpr3.smoke.ratio", dpr3_summary["ratio_median"], "ratio4", "%s :: ratio_median" % rel(P_DPR3_SUMMARY))
num("tests.focused", _focused["testcases"], "int", "%s :: count(testcase)" % rel(P_FOCUSED_JUNIT))
num("tests.full", _full["testcases"], "int", "%s :: count(testcase)" % rel(P_FULL_JUNIT))
num("tests.full.subtests", _full["subtests"], "int", "%s :: testsuite.tests - count(testcase)" % rel(P_FULL_JUNIT))

# ================================================================= campaign

D["_campaign"] = {
    "evidence_revision": EVIDENCE_REVISION,
    "campaign_revision": manifest["git_head"],
    "campaign": manifest["campaign"],
    "cost_usd": manifest["pods"]["total_cost_usd"] + bx2_pod["cost_usd_actual"],
    "cost_cap_usd": manifest["pods"]["budget_cap_usd"],
    "all_pods_terminated": manifest["pods"]["all_pods_terminated"],
    "tests": "%d focused tests; %d tests plus %d subtests in the full suite" % (
        _focused["testcases"], _full["testcases"], _full["subtests"]),
    "verdicts": dict(
        [(k, v["verdict"]) for k, v in manifest["benchmarks"].items()]
        + [("BX1", "COMPLETE — words crossover REVISED to workload-dependent"),
           ("BX2", "COMPLETE — best-of-10 smaller BDDs at ~8–10× search cost; reorder never triggers")]
    ),
    "corpora_sha256": manifest["corpora_sha256"],
    "local_env": {
        "python": b1_res["_meta"]["python"].split(" (")[0],
        "numpy": b1_res["_meta"]["numpy"],
        "cpu": b1_res["_meta"]["cpu"],
        "platform": b1_res["_meta"]["platform"],
    },
    "epfl_source": {
        "url": manifest["downloads"][0]["url"],
        "commit": manifest["downloads"][0]["commit"],
        "staged_or_committed": manifest["downloads"][0]["staged_or_committed"],
    },
    "provenance": [
        "%s :: whole file" % rel(P_MANIFEST),
        "%s :: _meta" % rel(P_B1_RES),
        "%s and %s :: current testsuite/testcase counts" % (rel(P_FOCUSED_JUNIT), rel(P_FULL_JUNIT)),
    ],
}
num("meta.tests", "%d focused / %d full + %d subtests" % (
        _focused["testcases"], _full["testcases"], _full["subtests"]), "text",
    "%s and %s :: current testsuite/testcase counts" % (rel(P_FOCUSED_JUNIT), rel(P_FULL_JUNIT)))
num("meta.cost", D["_campaign"]["cost_usd"], "usd",
    "%s :: pods.total_cost_usd + %s :: cost_usd_actual" % (rel(P_MANIFEST), rel(P_BX2_POD)))
num("meta.evidence_revision", EVIDENCE_REVISION[:7], "text",
    "evidence revision pinned by the site builder")
num("meta.campaign_revision", manifest["git_head"][:7], "text",
    "%s :: git_head" % rel(P_MANIFEST))

# ---------------------------------------------------------------- superseded
# Numbers that must NEVER appear on a chart. They are rendered only in the
# corrections ledger, explicitly labelled superseded, with their replacement.

D["_superseded"] = content["corrections"]

# ---------------------------------------------------------------- flags
# Discrepancies between claim-map prose and the raw evidence it points at.
# Surfaced on the page rather than silently smoothed over.

D["_flags"] = [
    {
        "claim_row": "16 — “blocked and round-robin agree within ~1–2%, never pooled”",
        "finding": (
            "The ~2%% figure holds for the archived 2026-08-02 run (%+.2f%%), for EPFL (%+.2f%%) and for "
            "all five pods (%+.2f%% to %+.2f%%) — but NOT for the B1 fresh replay, where the all-corpus "
            "gap is %+.2f%% and per-cell gaps reach %.2f%%."
        ) % (
            [s for s in sched if "archive" in s["source"]][0]["delta_pct"],
            [s for s in sched if "EPFL" in s["source"]][0]["delta_pct"],
            min(_pod_deltas), max(_pod_deltas),
            [s for s in sched if "B1 replay" in s["source"]][0]["delta_pct"],
            max(abs(c["delta_pct"]) for c in per_cell),
        ),
        "consequence": (
            "The “never pooled” half of the claim is unaffected and is honoured on every page here. "
            "The “agree within ~1–2%” half should be narrowed to the external and pod evidence, or "
            "restated as “agree within ~2% except on the synthetic corpus, where the schedule effect "
            "is itself run-variable”."
        ),
    },
    {
        "claim_row": "9 — “prep 4.30×, break-even median 78.5, 30/192 never”",
        "finding": (
            "Those are the archived 2026-08-02 numbers. Recomputed from the raw rows of the B1 fresh "
            "replay that this campaign designates as the reference workload: prep multiple %.2f× "
            "(archive %.2f×), break-even median %.1f over %d finite, %d/%d never (archive %s / %d). "
            "The headline kernel ratio itself is unaffected — the replay and the archive agree to "
            "%.4f (%.4f vs %.4f) with overlapping intervals."
        ) % (
            _bs["prep_multiple_geomean"], _arch_prep,
            _bs["median_finite"], _bs["n_finite"], _bs["n_never"], _bs["n_total"],
            b1_arch_res["breakeven"]["breakeven_evals_median"],
            b1_arch_res["breakeven"]["n_never_breaks_even_vs_cse"],
            abs(b1_acc["new_geomean_all_blocked"] - b1_acc["archived_geomean_recomputed_from_raw"]),
            b1_acc["new_geomean_all_blocked"], b1_acc["archived_geomean_recomputed_from_raw"],
        ),
        "consequence": (
            "Break-even is a prep-delta ÷ per-evaluation-gain ratio and the prep multiple is a ratio of "
            "two small timings, so both move with ordinary run-to-run variation while the kernel ratio "
            "does not. Every page here uses the replay values, matching the replay headline, and states "
            "prep as a range across corpora rather than a single figure. The workload-dependence "
            "conclusion is identical under either run."
        ),
    },
]

# ---------------------------------------------------------------- feature-model audit (separately pinned)

D["e20_feature_model_audit"], feature_model_numbers = build_feature_model_evidence(HERE)
for key, record in feature_model_numbers.items():
    num(key, record["value"], record["fmt"], record["prov"], record["note"])

# ---------------------------------------------------------------- content

content["use_case_benchmark_catalog"] = use_case_catalog
D["_content"] = content
D["_numbers"] = NUM

# ---------------------------------------------------------------- token check
# Every {{token}} used anywhere in the authored prose must resolve to a number
# this script actually read from evidence. Fail the build otherwise.

TOKEN_RE = re.compile(r"\{\{([a-zA-Z0-9_.]+)\}\}")
# Templates and the library also reach numbers through the T("…") / TV("…")
# helpers. Those call sites are held to the same rule, otherwise a mistyped
# token there would pass the build and ship a page rendering a runtime marker.
CALL_RE = re.compile(r'(?<![A-Za-z0-9_.$])TV?\(\s*"([a-zA-Z0-9_.]+)"\s*\)')


def walk_strings(node):
    """All prose strings in the content file. Keys beginning with `_` are
    build-time documentation, not page copy, and are skipped so that a
    `{{token}}` written there as an example does not fail the check."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str) and k.startswith("_"):
                continue
            yield from walk_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_strings(v)


used: set[str] = set()
for s in walk_strings(content):
    used.update(TOKEN_RE.findall(s))

# Templates and the shared library may also write {{token}} inside their prose
# strings; hold them to the same rule.
for tpl in sorted(HERE.glob("cm_*_template.html")) + [HERE / "cm_master_shared.js"]:
    if tpl.exists():
        text = tpl.read_text(encoding="utf-8")
        used.update(TOKEN_RE.findall(text))
        used.update(CALL_RE.findall(text))

missing = sorted(used - set(NUM))
if missing:
    raise SystemExit("prose references unknown number tokens: %s" % ", ".join(missing))
unused = sorted(set(NUM) - used)

# ---------------------------------------------------------------- emit

PAGES = [
    ("cm_master_template.html", "index.html"),
    ("cm_layperson_template.html", "layperson.html"),
    ("cm_investor_template.html", "investor.html"),
    ("cm_expert_template.html", "expert.html"),
    ("cm_usecases_template.html", "usecases.html"),
    ("cm_feature_model_template.html", "feature-model-evidence.html"),
]

out_json = HERE / "cm_master_data_2026_08_03.json"
with out_json.open("w", encoding="utf-8", newline="\n") as fh:
    json.dump(D, fh, indent=2, ensure_ascii=False)
    fh.write("\n")

css = (HERE / "cm_master_shared.css").read_text(encoding="utf-8")
lib = (HERE / "cm_master_shared.js").read_text(encoding="utf-8")
payload = json.dumps(D, separators=(",", ":"), ensure_ascii=False)

written = []
for tpl_name, out_name in PAGES:
    tpl = HERE / tpl_name
    if not tpl.exists():
        print("SKIP (template missing): %s" % tpl_name)
        continue
    html = tpl.read_text(encoding="utf-8")
    html = html.replace("/*__CM_CSS__*/", css)
    html = html.replace("/*__CM_LIB__*/", lib)
    html = html.replace("/*__CM_DATA__*/null", payload)
    out = HERE / out_name
    out.write_text(html, encoding="utf-8", newline="\n")
    written.append((out_name, out.stat().st_size))

# ---------------------------------------------------------------- report

print("wrote %s (%d bytes)" % (out_json.name, out_json.stat().st_size))
for name, size in written:
    print("wrote %-16s (%d bytes)" % (name, size))
print()
print("evidence revision:", D["_campaign"]["evidence_revision"])
print("campaign revision:", D["_campaign"]["campaign_revision"])
print("number tokens: %d defined, %d referenced by prose, %d unused"
      % (len(NUM), len(used), len(unused)))
if unused:
    print("               unused:", ", ".join(unused))
print()
print("sanity — kernel vs plain CSE       local %.4f [%.3f, %.3f] · EPFL %.4f · pods %.4f–%.4f" % (
    b1_acc["new_geomean_all_blocked"], *b1_acc["new_ci95_stratified"],
    epfl_ana["secondary_blocked_cm_cse"]["geomean"],
    b6_ana["pod_to_pod"]["geomean_min"], b6_ana["pod_to_pod"]["geomean_max"]))
print("sanity — kernel vs CSE-flat        local %.4f · EPFL %.4f [%.4f, %.4f] · pods %.4f–%.4f" % (
    b1_acc["new_cm_vs_cse_flat_geomean"],
    epfl_ana["primary_blocked_cm_cse_flat"]["geomean"],
    epfl_ana["primary_blocked_cm_cse_flat"]["ci95_lo"],
    epfl_ana["primary_blocked_cm_cse_flat"]["ci95_hi"],
    min(_flat_pod), max(_flat_pod)))
print("sanity — current B2/B4 V3 bare     overall %.4f [%.4f, %.4f] · k16 %.4f [%.4f, %.4f]" % (
    fnum(_sym_bare_all["paired_formula_cluster_geomean"]),
    fnum(_sym_bare_all["paired_formula_cluster_bootstrap_ci95_low"]),
    fnum(_sym_bare_all["paired_formula_cluster_bootstrap_ci95_high"]),
    fnum(_sym_bare_k16["paired_formula_cluster_geomean"]),
    fnum(_sym_bare_k16["paired_formula_cluster_bootstrap_ci95_low"]),
    fnum(_sym_bare_k16["paired_formula_cluster_bootstrap_ci95_high"])))
print("sanity — current B2/B4 V3 wrapper  overall %.4f [%.4f, %.4f]" % (
    fnum(_sym_wrap_all["paired_formula_cluster_geomean"]),
    fnum(_sym_wrap_all["paired_formula_cluster_bootstrap_ci95_low"]),
    fnum(_sym_wrap_all["paired_formula_cluster_bootstrap_ci95_high"])))
print("sanity — materiality conditions    %s  => optimization_worthy=%s" % (
    {k: v for k, v in epfl_ana["materiality"].items() if k != "optimization_worthy"},
    epfl_ana["materiality"]["optimization_worthy"]))
print("sanity — wrapper CM/BitSet         %s" % " ".join(
    "k%d:%.2f" % (r["live_k"], r["cached_median"]) for r in D["e6_wrapper_ratio"]["rows"]))
print("sanity — break-even                synthetic median %.1f, %d/%d never · EPFL median %.1f, %d/%d never" % (
    _bs["median_finite"], _bs["n_never"], _bs["n_total"],
    _be["median_finite"], _be["n_never"], _be["n_total"]))
print("sanity — prep multiple             synthetic %.2f× · EPFL %.2f×" % (
    _bs["prep_multiple_geomean"], _be["prep_multiple_geomean"]))
print("sanity — guard totals              %d trials, %d wrong, %d oversized" % (
    D["e9_guard"]["totals"]["trials"], D["e9_guard"]["totals"]["wrong_guard"],
    D["e9_guard"]["totals"]["oversized"]))
print("sanity — CUDD integrity            robdd_is_cudd=%s full_extraction_equal=%s (%d rows)" % (
    D["e12_cudd"]["integrity"]["robdd_is_cudd_all"],
    D["e12_cudd"]["integrity"]["full_extraction_equal_all"],
    D["e12_cudd"]["integrity"]["n_rows"]))
print("sanity — CUDD extract vs kernel    %s" % " ".join(
    "k%d:%.0f×" % (r["live_k"], r["factor"]) for r in D["e12_cudd"]["extract_vs_kernel"]))
print("sanity — BX1 fastest engine        %s" % " ".join(
    "k%d:%s" % (r["live_k"], r["fastest"].replace("_bigint", "")) for r in D["e15_engines"]["rows"]))
print("sanity — BX2 best-10 node ratio    %s" % " / ".join(
    "%.2f" % r["node_ratio_best10"] for r in _bx2))
print("sanity — schedule max |delta|      %.2f%% all-corpus, %.2f%% per-cell (B1)" % (
    D["e14_schedule"]["max_abs_delta_pct"], D["e14_schedule"]["max_abs_cell_delta_pct"]))
print()
for fl in D["_flags"]:
    print("FLAG  claim row %s\n      %s" % (fl["claim_row"], fl["finding"]))

if "--check-only" in sys.argv:
    sys.exit(0)
