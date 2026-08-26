# CM Post-Consolidation Local and Runpod Plan

Plan date: **2026-08-26**  
Repository: `C:\Users\brian\Documents\CM_Computation`  
Accepted code/evidence ancestor: `1fd3907dbc1986cb2d8a9f0f8cab2b5920a415ce`  
Current documentation reconciliation descendant when planned: `0f833bc389778f7f915deb7acd4499d207e0ec21`

## Decision summary

Do **not** repeat the whole Aug-24/Aug-25 campaign unchanged. Correctness,
current selector behavior, the focused crossover failure, the V3 strongest-
comparator result, three-pod replication, and the guarded `k=17..20` boundary
have already been rerun on the consolidated implementation.

The next high-value sequence is:

1. run a short local post-website health gate;
2. use Runpod to confirm the accepted one-memo preparation improvement on
   materially different hosts;
3. prototype compact canonical ordering locally and retain it only through a
   paired exactness/performance gate;
4. if retained, confirm that prototype on Runpod;
5. build and freeze a genuinely new held-out selector corpus before fitting a
   feature selector;
6. run cache, family, and partial-context economics only against a real or
   representative access/edit/context trace;
7. keep CUDD, native/SIMD, large-output, GPU, and distributed lanes conditional.

No paid compute is launched by this plan. Before a Runpod campaign, approve the
exact worker image/host choices, maximum spend, and termination behavior.

## What has already been rerun

| Area | Current evidence | Result | Rerun decision |
|---|---|---|---|
| Consolidated correctness | `audit_manifest.json`; post-consolidation handoff | focused `73 passed + 4 subtests`; full `363 passed + 4 subtests` | Do only a fast health gate after the website/source update; rerun full suite before retaining production code. |
| Mixed-corpus audit/profile | `baseline_smoke_*`, `profiled_smoke_*`, `post_memo_smoke_*` | Exact outputs; preparation profile captured on BX1/B2/EPFL | Do not repeat unless code or environment changes materially. |
| Strongest comparator, local | `deliverables_n22_24/corrections_2026_08_25/symmetric/audited_v3_*` | 24 rounds, 264 rows, 216 formulas, zero mismatches; bare CM/CSE-flat `0.890570` overall and `0.961234` at `k=16`; wrapper/CSE-flat `3.094136` overall | Accepted. Do not rerun merely to obtain another point estimate. |
| Strongest comparator, Runpod | `deliverables_n22_24/correction_runpod_2026_08_25/` | Three pods; bare overall about `0.903–0.913`, `k=16` about `0.975–0.977`; wrapper slower; all integrity gates passed | Accepted descriptive cross-host replication. Repeat only after semantic code changes. |
| Full selector | corrected local 401-row artifacts and three-pod campaign | Current `k=16` policy has low full-corpus regret; no truth mismatches | Keep current policy. Replaying the same corpus cannot create untouched validation. |
| Focused selector gap | corrected local 71-row artifacts and three-pod campaign | Every pod rejected a universal support-only retune at `k=13..15` | Closed against another scalar threshold. Next study must be feature-based and use new held-out data. |
| Guard boundary | Aug-24 `above_guard` follow-up | 16/16 production refusals; authorized direct kernels exact; no timeout/OOM; bounded estimates/RSS | Accepted local safety result. Cross-host repeat only if guard/budget policy changes. |
| Preparation implementation | `memo_ablation_*` | One-memo change: BX1+B2 `0.960113`; reused EPFL `0.976840`; traced peak `0.882`; zero exact mismatches | Production change accepted locally. **Second-machine confirmation remains valuable.** |
| Cache reuse | persistent-cache report and audit probes | Synthetic/all-hit warm behavior exists; no realistic byte/access distribution or cross-process economics | Do not rerun the same all-hit benchmark as a product claim. Obtain a trace first. |
| Related families | experiments A and later phase artifacts | CM improves versus uncached CM but does not beat strongest applicable incumbent | Reopen only with real edit/version traces. |
| Partial contexts | experiment B and phase artifacts | Cached/restricted CM improves versus itself but does not establish incumbent dominance | Reopen only for a real context stream; keep BDD build/restrict/query/extract separate. |
| CUDD/order studies | B5 and BX2 accepted artifacts | Construction, extraction, and order-search boundaries are separated; best-of-ten costs much more | No generic rerun. Reopen for context/query workloads with working native CUDD. |
| Parallel/GPU/distributed | historical negative evidence and deep audit | Current admitted complete-output workloads do not amortize overhead or memory amplification | Not a default campaign. |

## Evidence rules for every new run

- Preserve historical artifacts; every output prefix must be new and refuse
  overwrite.
- Freeze run-defining sources and corpora by SHA-256 before timing.
- Compare identical formulas, semantic support, output ordering, and artifacts.
- Keep preparation, kernel, wrapper/dispatch, materialization/conversion,
  persistence/serialization, restriction, and BDD extraction windows separate.
- Preserve paired per-formula/per-root rows and all failure, refusal, timeout,
  OOM, and skipped rows.
- Treat BX1 as tuning and B2/EPFL as reused validation. Neither can serve as a
  new untouched selector gate.
- Report formula/circuit/family-cluster inference and machine-stratified
  results. Do not pool hosts or schedules without an explicit model.
- V3 formula-cluster intervals describe conditional formula variation; they do
  not measure between-run or between-machine uncertainty.
- Exact complete output remains `Omega(2^k / w)` packed words. A BDD, stream,
  factorization, SAT result, or quotient is a different artifact.

## Phase 0 — freeze the campaign state

Create one dated root after recording branch, HEAD, status, recent commits,
Python/dependency versions, OS/CPU/memory, affinity, run-defining source hashes,
and corpus hashes:

```powershell
$cmStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$cmRunRoot = "docs\audits\2026-08-25-cm-deep-performance\reruns\campaign-$cmStamp"
if (Test-Path -LiteralPath $cmRunRoot) { throw "Refusing existing run root: $cmRunRoot" }
New-Item -ItemType Directory -Path $cmRunRoot | Out-Null
```

Compare current semantic source bytes with the V3 and memo-ablation source
snapshots. Classify differences as semantic, protocol-affecting, metadata-only,
comment-only, or website-only. A website-only change does not justify repeating
the compute campaign.

## Phase 1 — short local acceptance

Run after the generated website update, and before packaging any remote worker:

```powershell
python -m pytest -q `
  tests\test_cm_benchmark_audit_integrity.py tests\test_build_memo.py `
  tests\test_bitset_cse.py tests\test_share_aware_flatten.py `
  tests\test_persistent_path_consistency.py tests\test_cm_ir_cost.py `
  --basetemp "$cmRunRoot\.pytest_focused"

& .\.venv\Scripts\python.exe scripts\cm_deep_performance_audit.py `
  --suite smoke --corpora bx1,b2,epfl --prep-repetitions 3 `
  --kernel-rounds 5 --max-kernel-temporary-bytes 8388608 `
  --output-prefix "$cmRunRoot\deep_smoke"

& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite smoke --corpora bx1,b2,epfl --repetitions 11 `
  --output-prefix "$cmRunRoot\memo_smoke"
```

Gate: zero exact output, ordered-DAG, frozen-truth, cache-identity, provenance,
and overwrite/refusal failures. Smoke timing is a drift/allocation diagnostic,
not acceptance evidence for a small optimization. The full symmetric V3 study
is unnecessary unless semantic evaluator/compiler code differs from its frozen
snapshot.

## Phase 2 — Runpod confirmation of the accepted preparation change

### Purpose

This is DP-R4: establish whether removing the redundant sharing-aware identity
memo retains its direction on Linux and materially different CPUs. It is not an
untouched selector validation and must not be pooled with local Windows ratios.

### Remote package

Create a new dated worker/campaign pair based on the fail-closed Aug-25 Runpod
campaign. Package only the listed run-defining sources, frozen BX1/B2/EPFL
corpora, `scripts/cm_prepare_memo_ablation.py`, and its transitive imports.
Require archive SHA-256 verification before extraction and source-manifest
verification after each run.

Run on the worker:

```powershell
& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite representative --corpora bx1,b2 --repetitions 11 --skip-allocation `
  --output-prefix deliverables_n22_24\pod_out\memo_bx1_b2
```

Run reused EPFL in bounded non-overlapping chunks with five repetitions. For
the accepted 129-root corpus, use starts `0,20,40,60,80,100,120` and limits
`20,20,20,20,20,20,9`, with a distinct prefix per chunk. Aggregate only after
download and verify no missing or duplicate roots.

### Host schedule

1. One low-cost pilot pod on one CPU flavor.
2. If archive, correctness, download, and deletion gates pass, run at least two
   materially different advertised CPU models/flavors.
3. Use three independent pods per host class if the pilot shows ordinary
   between-pod noise could obscure the small preparation effect. Otherwise use
   a preregistered smaller replication count and state the limitation.
4. Run one pod at a time, download and hash-verify all outputs, then terminate
   and confirm deletion before starting the next.
5. Finish with a provider inventory proving zero live campaign pods.

Record exact CPU model, logical cores, RAM, Linux/kernel, Python, dependencies,
container image/digest, affinity, clock/governor visibility, steal-time caveat,
pod ID, timestamps, rate, elapsed time, estimated exposure, and deletion result.

### Gate

- zero ordered-DAG and packed-output mismatches;
- no missing/duplicate rows or source/corpus hash mismatch;
- report each machine separately;
- require no material aggregate regression and a direction consistent with
  reduced temporary allocation;
- call a host result inconclusive when its interval overlaps ordinary noise;
- retain the production change unless a reproducible correctness or material
  performance regression appears.

## Phase 3 — compact canonical ordering prototype (DP-R1)

Do this locally before spending more cloud money. Save a pre-change source
snapshot and baseline. Add only a builder-local compact exact ordering/rank that
avoids repeated deep tuple comparison. It must not change public `CMNode.key`,
canonical child order, structural/persistent digests, cache keys, serialization,
foreign adoption, live support, lowering, or packed output.

Validate on:

- BX1 tuning;
- B2 and EPFL reused validation;
- high-sharing B3 cases selected before implementation;
- explicit adversarial equal-prefix/deep-sharing ordering cases.

Use alternating paired order, exact O(`s`) ordered-DAG signatures, packed truth,
11 preparation repetitions for BX1/B2, bounded five-repetition EPFL chunks,
and `tracemalloc` smoke. Pre-register a maintenance-aware keep threshold before
timing. A reasonable default is: at least a 2% representative cold-preparation
gain with the paired cluster interval below parity, no greater than 2% regression
on any validation aggregate, no meaningful high-sharing tail regression, and no
temporary/retained-memory increase. Reject and revert only the prototype if the
effect is noise or any compatibility gate fails.

If retained, run the full test suite locally, then repeat the Phase-2 Runpod
confirmation with baseline = accepted one-memo path and candidate = DP-R1.

## Phase 4 — new held-out feature selector

Do not fit another support-only threshold and do not reuse B2/EPFL as the final
gate.

### Corpus protocol

1. Identify sources before feature or outcome inspection. Prefer independently
   maintained circuit/policy families not used in B1/B2/B3/B4/BX1/EPFL.
2. Obtain explicit approval before downloading a new corpus into the repository.
3. Freeze source URLs/commits/licenses, selected roots, formula IDs, exact truths,
   semantic support, and SHA-256 manifests.
4. Split by whole circuit/family, never by timing row. Freeze tuning,
   development, and untouched test partitions before fitting.
5. Cover `k=13..16`, structural size, sharing, operator mix, instruction count,
   primitive work, and peak live word buffers. Retain refusals and infeasible
   arms rather than selecting survivors.

Candidate features: `k`, structural nodes, flat instruction/primitive-op counts,
operator mix, sharing factor, peak live buffers, requested output, cache state,
expected evaluation count `q`, and memory budget `B`. Begin with an interpretable
rule or shallow tree; selector overhead is part of the timing boundary.

### Acceptance

Compare against the current `k=16` policy and the per-row oracle. On untouched
test and on each Runpod host class report geomean, p95 and maximum regret,
`>=2x` misroute count/rate, selector overhead, admission/refusal correctness,
blocked/round-robin stability, and behavior near memory limits. Pre-register the
gate before opening test labels. Require zero catastrophic misroutes and a
material reduction in excess regret without worsening the current full-corpus
policy. If transfer fails, keep `WORDS_AUTO_MIN_VARS=16` and retain the negative
result.

## Phase 5 — real reuse trace, then cache/family/context replay

This phase is blocked until a caller or representative trace exists. Instrument
before optimizing. A trace record should contain:

- compiler/schema/options identity and structural digest;
- artifact/retained bytes, build, lookup, serialize/deserialize cost;
- process/cold-start boundary, hit/miss/eviction, and cache budget;
- family/version/context ID and changed structural region;
- original and remaining live support, context overlap/locality and phase;
- subsequent evaluation count, output kind, and memory/refusal status.

Replay the same immutable trace against:

1. no cache;
2. current entry-count LRU;
3. byte-budgeted LRU;
4. size/cost-aware admission only if the trace supports it;
5. cold CSE-flat/hash-consed compilation;
6. task-matched BDD restriction/query for context streams.

Report saved wall time, hit and byte-hit rate, serialization cost, eviction
churn, invalidation failures, working-set sensitivity, retained bytes/RSS
plateau, cold/warm process boundaries, and total task work. Use locality-heavy,
phase-changing, and adversarial streams. Synthetic family/context generators
may remain smoke tests but cannot authorize a production policy.

## Phase 6 — conditional specialist lanes

| Lane | Open only when | Required boundary |
|---|---|---|
| Native CUDD context frontier | a real repeated restriction/query stream exists and `dd.cudd` is already available or dependency approval is given | Separate manager/build, reorder, restrict, symbolic query, sampled evaluation, and exhaustive extraction. |
| Native/JIT/SIMD words kernel | a real repeated batch makes word-kernel time dominate preparation, dispatch, copies, and output | Include cold/warm compilation, CPU dispatch, copies/conversion, exact fallback, per-thread scratch, and peak memory. |
| Large-output/guard | API budget defaults or output interface are being changed | One subprocess per case, fail-closed estimate, timeout/RSS cap, no guard increase from speed alone. |
| Streamed output | caller accepts chunks instead of one packed integer | Claim bounded peak memory or time-to-first-chunk only; total output work remains exponential. |
| Multiprocessing/GPU/distributed | a measured large batch amortizes startup/transfer and aggregate memory fits | Include serialization, copies, synchronization, cache contention, failures, and total cost. |
| Independent-block algebra | inputs prove disjoint support blocks and layout/lift materialization dominates | Prove decomposition and exact final layout; final complete materialization remains exponential. |

## Runpod safety and budget contract

Before launch, record the exact approved maximum spend and hard-stop behavior.
The campaign must:

- use existing credential-loading code without reading or printing secrets;
- fail if the output directory exists;
- create at most one pilot pod initially;
- verify source/corpus archive hashes remotely;
- refuse unbounded support or memory estimates;
- retrieve failures and partial outputs as well as successes;
- delete each pod in `finally` behavior;
- stop on integrity, budget, or deletion failure;
- keep a running estimated-exposure ledger without calling it an invoice;
- perform a final zero-pod inventory.

Suggested approval checkpoints are one pilot budget first, then a separate cap
for the full CPU replication. GPU instances are unnecessary for Phases 2–4.

## Required outputs

Under the unique run root, produce:

- `RUN-ENVIRONMENT.json` with repository state, commands, hardware, versions,
  source/corpus hashes, seeds, affinity, and artifact inventory;
- raw paired CSV/JSON/JSONL including failures/refusals;
- immutable source/corpus manifests;
- `RUN-RESULTS.md` with timing windows, schedules, repetitions, dispersion,
  cluster inference, memory, and host-stratified interpretation;
- `RUN-DECISIONS.md` separating confirmed, changed, inconclusive, negative,
  deferred, and approval-blocked findings;
- `RUNPOD-AUDIT.json` and zero-pod postflight inventory for cloud phases;
- rejection records for every tested candidate not retained;
- an updated optimization backlog and next-agent handoff.

Before reporting completion, run focused/full tests appropriate to changed code,
`git diff --check`, `git diff --stat`, and `git status --short`. Identify exactly
which changes belong to the campaign. Do not commit or push unless Brian asks.

