# CM Comprehensive Benchmark Campaign — Execution Prompt (2026-08-03)

Copy-paste prompt for a new agent session. Authored after the
post-acceptance pass (independent reaggregation PASSED). Purpose: refresh
every benchmark family the slide deck (frozen at Audit V4, 2026-07-24)
draws on, on the current repaired code, and execute the two never-run
external legs (EPFL corpus, RunPod cross-platform), so the deck can be
rebuilt from one coherent, post-repair evidence set.

---

## PROMPT (copy everything below into the new session)

Act as an independent benchmark-campaign agent for the CM project. Prefer
falsification over confirmation. Preserve all archived evidence; never
overwrite an existing artifact; write every new output to new dated paths.

**Repository:** `C:\Users\brian\Documents\CM_Computation`, branch `main`.
Record `git status --short`, `git rev-parse HEAD origin/main`,
`git log -5 --oneline`, and interpreter versions before anything else.
Benchmarks run on `.venv\Scripts\python.exe` (3.13.5, numpy 2.3.2); tests
on system Python 3.10 with `--basetemp tmp\pytest_cm_bench_<date>` (create
`tmp\` parent first). Do not modify, stage, or commit anything without
explicit approval (`COMMIT_PUSH_APPROVED = NO`). Never stage `.claude\`,
`tmp\`, `external\`, or historical prompts.

**Authorization granted by Brian for this campaign:**
- `EPFL_DOWNLOAD_APPROVED = YES` (~50 MB clone of
  `https://github.com/lsils/benchmarks.git` into `external\epfl-benchmarks`).
- `POD_REPLICATION_APPROVED = YES` within a **hard budget cap of $5 total
  pod spend**; terminate every pod after evidence collection, including on
  failure; report actual cost per pod.
- `DEPENDENCY_INSTALL_APPROVED = NO` locally. On RunPod pods only, you may
  install what the pod needs (e.g. `dd` with CUDD on Linux) — record exact
  versions in provenance.

**Read first, in order:**
1. `deliverables_n22_24\CM_GAP_NEXT_PHASE_MASTER_HANDOFF_2026-08-03.md`
2. `deliverables_n22_24\CM_GAP_CONSOLIDATED_AUDIT_AND_ERRATUM_2026-08-02.md`
   (claim disposition table — which deck-era numbers are superseded)
3. `deliverables_n22_24\CM_GAP_EPFL_PROTOCOL_2026-08-03.md` (frozen; execute
   as written)
4. `deliverables_n22_24\CM_GAP_POST_ACCEPTANCE_OPTIMIZATION_DECISION_2026-08-03.md`
5. `CM_LATENT_FIXES_2026-07-23.md` (worker redeploy note, fix 2)
6. `CM_AUDIT_V4_2026-07-24.md` and the deck-era drivers in
   `deliverables_n22_24\` (headline/guard/scaling/wrapper benchmarks) for
   the harness conventions to reuse — reuse *protocols*, write *new
   drivers/outputs*; never run archived fixed-output drivers directly.

**Standing rules for every benchmark below:** packed-equality assertion
across all arms before every timing measurement; blocked and round-robin
schedules reported separately, never pooled; per-formula paired ratios,
geomeans with stratified/clustered bootstrap CIs; live_k (semantic
support) as the x-axis, never nominal n; corpus provenance (seeds, hashes)
in every results `_meta`; deterministic pilot + runtime estimate before
each full run with a 60-minute widening gate per benchmark; all skips
recorded with reasons; summaries independently reaggregated from raw rows
before being cited. Superseded numbers (0.843, 128×/240×, V4 C1, pre-C3-fix
n≥18 ratios) must never be cited except as "superseded".

### B1 — Corrected E3 kernel benchmark (fresh replay, local)
Frozen corpus `CM_gap_e3_corrected_corpus_2026_08_02.jsonl` (SHA
`8a6da87c…f6e68a`) through the corrected driver
`cm_gap_e3_corrected_2026_08_02.py` with `--corpus <frozen> --out-dir`
pointing at a **new** directory. Arms: repaired CM, structural CSE,
CSE+sharing-aware-flatten, raw ablation. Acceptance: identity fields exact
vs archive; geomean within CI overlap of 0.888 [0.876, 0.899]; cm/cse_flat
≈ 0.985. This is the reference workload for B6.

### B2 — Wrapper-boundary benchmark (harness-level, local)
The deck's "BitSet dominates tiny support; 8–12 transitional; CM modestly
ahead at controlled live_k=16" claim, re-measured post-repair: CM wrapper
total vs bare BitSet at live_k ∈ {4, 6, 8, 10, 12, 16}, cached and
uncached regimes, wrapper-overhead decomposition (archived median 23 µs).
Report where the crossover sits now that prep is 4.30× CSE and kernels are
0.888/0.985.

### B3 — Compile/DAG scaling (local)
Prep-time scaling vs structural nodes, depth, and unfolding factor,
including the pathological shared-chain case (historical 403 ms → 3.0 ms)
and the unshared-tree 152 µs class; confirm the compile-scaling claim
retained by the disposition table still holds on current code.

### B4 — Guard/decline and n=16–24 family sweep (local; supersedes-check)
Post-repair refresh of the deck-era headline/guard-rate/decline-by-depth
sweeps at n=16–24 (live_k-controlled, C3 fairness fix in place, engine
symmetry per latent fix 1). Purpose: replace the deck's pre-repair n≥18
numbers, which the audit marked superseded. Use fresh corpora with
recorded seeds; family/shape balance per the corrected-E3 admission style.

### B5 — CUDD matched comparison (RunPod, Linux-only)
`dd.cudd` does not build on Windows; use one RunPod pod (Docker image with
python3 + dd/CUDD). Re-run the §7e matched-cost protocol from
`CM_AUDIT_V4_2026-07-24.md` on current code: CM/BitSet vs native-CUDD
construction and evaluation costs measured separately, matched formula
corpus, `robdd_is_cudd` verified true on every row (the cudd request never
silently falls back — fail closed). Record pod CPU model, image digest,
package versions, cost.

### B6 — Cross-platform replication of B1 (RunPod, E8 gate)
First **verify or redeploy the remote worker from current
`cm_remote_worker.py`** — the deployed worker predates the
`remote_words_eval` echo protocol and words runs fail closed against it.
Then 5 × `cpu3c` pods, frozen B1 corpus + driver, ~5 pod-minutes each,
est. < $1: per pod record CPU model, cgroup quota, memory, image digest,
setup time, runtime, raw results, cost. Abort a pod at 15 min setup or 2×
local runtime. Pod-clustered analysis; report pod-to-pod variance, never
pool it away; no local-fallback rows accepted as pod evidence. Verdict:
CROSS-PLATFORM REPLICATION PASSED / FAILED / INCONCLUSIVE.

### B7 — EPFL external validation (local timing; download approved above)
Execute `CM_GAP_EPFL_PROTOCOL_2026-08-03.md` **exactly as pre-registered**
(cone selection, arms, circuit-clustered analysis, and the frozen
materiality rule: CM/CSE-flat geomean ≤ 0.95 + clustered CI excluding
parity + break-even ≤ 1000 evals, else declare kernel-equivalence). Do not
revise the protocol after seeing data; a defect stops the run and versions
a successor. Verdict: SUPPORTS / DOES NOT SUPPORT GENERALIZATION /
INCONCLUSIVE / BLOCKED.

### Deliverables
Per benchmark: new dated driver, corpus (where applicable), raw results
JSON, summary CSV, and a report ending in a one-line verdict — all under
`deliverables_n22_24\`, refuse-overwrite. Then:
- `CM_BENCHMARK_REFRESH_CLAIM_MAP_<date>.md` — every deck (V4) claim
  mapped to its refreshed number: CONFIRMED / REVISED (old → new) /
  SUPERSEDED / NOT RE-RUN, so the deck can be rebuilt slide-by-slide;
- machine-readable provenance + cost manifest (downloads, pods, $ actuals);
- run the full test suite (system 3.10) if any Python file was added;
- `CM_BENCHMARK_REFRESH_HANDOFF_<date>.md` — self-contained, with proposed
  commit decomposition (do not execute), ending with exactly one of:
  `BENCHMARK REFRESH COMPLETE` / `REVISE AND RE-RUN` / `BLOCKED`.

Final chat response: lead with the claim-map deltas (what changed vs the
deck), then per-benchmark verdicts, costs, exact file paths, git state,
and remaining decisions for Brian.
