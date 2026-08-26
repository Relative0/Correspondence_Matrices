# CM Next-Agent Full Rerun and Implementation Prompt

This is the comprehensive copy-paste prompt for continuing the 2026-08-25 CM audit. It gives the next agent the audited history, current repository state, settled claims, exact rerun sequence, implementation gates, optional-work boundaries, and required deliverables.

> **2026-08-26 campaign note:** the corrected selector, V3 symmetric study,
> three-pod replication, guard boundary, and local one-memo studies described
> below have already completed on the consolidated implementation. For a
> non-duplicative next campaign, use
> `CM-POST-CONSOLIDATION-LOCAL-RUNPOD-PLAN-2026-08-26.md`. Keep this longer
> prompt as the full from-scratch audit/implementation contract.

```text
Work in C:\Users\brian\Documents\CM_Computation.

Mission

Take over the Correspondence Matrix (CM) deep-performance work from the consolidated and reconciled 2026-08-25 audit state. First preserve and understand the accepted evidence. Then run the post-consolidation correctness and performance campaign. If those gates are stable, implement and evaluate the next safe local preparation optimization. Run bounded cache, family, and partial-context diagnostics, but productize nothing from synthetic reuse alone. Keep guard-boundary, dependency/native, cloud, and cross-machine work explicitly opt-in.

Do not stop at recommendations where a safe local candidate can be measured and implemented. Do not keep an optimization that does not survive exactness, paired timing, allocation/memory, and untuned validation gates. Record negative findings and rejected experiments.

Expected repository state

- Repository: `C:\Users\brian\Documents\CM_Computation`
- Branch: `main`
- Required ancestor: `1fd3907dbc1986cb2d8a9f0f8cab2b5920a415ce` — `Audit and consolidate CM benchmark corrections`
- Expected local reconciliation commit or descendant: `0f833bc389778f7f915deb7acd4499d207e0ec21` — `Reconcile CM audit with consolidated evidence`
- At creation of this prompt, `origin/main` was at `1fd3907` and local `main` was one documentation commit ahead.
- Pre-existing untracked directories: `.claude/`, `external/`, and `tmp/`. Preserve them exactly; do not inspect secrets or attribute their contents to this work.

If the branch, ancestry, status, or commit graph differs, inspect it before acting. Do not pull, reset, clean, restore, rebase, merge, or overwrite work merely to force this expected state. Reconcile only after identifying ownership and exact byte-level differences.

Safety and authority

1. Read every applicable `AGENTS.md` before any task action.
2. Never read or expose `.env*`, credentials, tokens, private configuration, key material, or credential stores.
3. Preserve unrelated tracked and untracked work. Never use `git add .`, recursive cleanup, destructive reset, or broad restore.
4. Local read-only inspection, tests, benchmarks, new uniquely dated artifacts, and small evidence-backed production/test/tooling changes are authorized by this mission.
5. Do not install dependencies, build a new native toolchain, start paid/cloud/GPU/remote compute, change a production API's default refusal budget, commit, or push without Brian's explicit approval in the active task.
6. Use `.venv\Scripts\python.exe` for benchmark drivers. At the audited state, pytest was not installed in `.venv`; use the available global `python` for pytest unless current inspection proves otherwise. Do not install pytest just to change interpreters.
7. Every benchmark must write to a new nonexistent output prefix and refuse overwrite. Never replace accepted raw or historical artifacts.
8. Keep correctness/reference work and performance work separate. A timing improvement cannot excuse an exactness, ordering, cache identity, refusal, or artifact mismatch.

Required reading — in order

1. `README.md`
2. `deliverables_n22_24/CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md`
3. `deliverables_n22_24/CM_BENCHMARK_REFRESH_CLAIM_MAP_ADDENDUM_2026-08-03.md`
4. `deliverables_n22_24/CM_GAP_POST_ACCEPTANCE_OPTIMIZATION_DECISION_2026-08-03.md`
5. `deliverables_n22_24/CM_GAP_EPFL_VALIDATION_2026-08-03.md`
6. `deliverables_n22_24/b2_wrapper_2026_08_03/CM_B2_WRAPPER_BOUNDARY_REPORT_2026-08-03.md`
7. `deliverables_n22_24/b3_scaling_2026_08_03/CM_B3_COMPILE_SCALING_REPORT_2026-08-03.md`
8. `deliverables_n22_24/bx1_crossover_2026_08_03/CM_BX1_ENGINE_CROSSOVER_REPORT_2026-08-03.md`
9. `deliverables_n22_24/bx2_cudd_orders_2026_08_03/CM_BX2_CUDD_ORDERS_REPORT_2026-08-03.md`
10. `CM_persistent_cache_report.md`
11. `CM_experiment_A_related_families_report.md`
12. `CM_experiment_B_partial_contexts_report.md`
13. `CM_experiment_C_operator_difference_quotient_report.md`
14. `docs/audits/2026-07-26-cm-performance/CM-PERFORMANCE-AUDIT.md`
15. `docs/audits/2026-07-26-cm-performance/CM-OPTIMIZATION-BACKLOG.md`
16. `deliverables_n22_24/corrections_2026_08_25/CM_BENCHMARK_AUDIT_CORRECTION_REPORT_2026-08-25.md`
17. `docs/audits/2026-08-25-cm-deep-performance/README.md`
18. `docs/audits/2026-08-25-cm-deep-performance/CM-DEEP-PERFORMANCE-AUDIT.md`
19. `docs/audits/2026-08-25-cm-deep-performance/CM-BENCHMARK-RESULTS.md`
20. `docs/audits/2026-08-25-cm-deep-performance/CM-RESEARCH-LEDGER.md`
21. `docs/audits/2026-08-25-cm-deep-performance/CM-OPTIMIZATION-BACKLOG.md`
22. `docs/audits/2026-08-25-cm-deep-performance/audit_manifest.json`
23. `docs/audits/2026-08-25-cm-deep-performance/NEXT-AGENT-HANDOFF.md`
24. `docs/audits/2026-08-25-cm-deep-performance/CM-CONSOLIDATED-RERUN-PROMPT-2026-08-25.md`

Use older V3/V4 reports only as historical context. The current claim map, Aug-25 corrections, immutable source snapshots, tested current code, and this audit package are authoritative when an older claim conflicts.

Audit memory — what was found

1. CM and sharing-aware CSE-flat were kernel-equivalent on accepted B1/E3 evidence: external CM/CSE-flat `0.9998`, interval `[0.9747, 1.0249]`. Do not optimize or advertise that residual.
2. CM's older advantage over plain structural CSE came primarily from flattening/merging instructions. Giving CSE the corresponding sharing-aware flattening closed that gap on the parity workload.
3. The exactly counterbalanced V3 B2/B4 study supersedes V2 for the local strongest-comparator headline:
   - formula-balanced bare CM/CSE-flat overall `0.8905696773`, paired formula-cluster bootstrap interval `[0.8740654100, 0.9072717742]`;
   - at `k=16`, `0.9612336537`, interval `[0.9289740604, 0.9941768792]`;
   - row-weighted overall sensitivity result `0.8969499433`;
   - formula-balanced public CM wrapper/CSE-flat overall `3.0941361850`, interval `[2.8830826921, 3.3108182215]`;
   - formula-balanced bare CM/raw-AST overall `0.8224497460`, interval `[0.7894438587, 0.8554248922]`.
   V3 used 24 rounds, exact schedule counterbalancing, 264 timing rows, 216 unique formulas, and 10,000 deterministic paired formula-cluster bootstrap resamples. Its uncertainty represents formula variation conditional on this machine/run, not between-run or between-machine variation.
4. At the whole-call boundary, BitSet led every measured semantic support through `live_k=16`. CM preparation was roughly four times the comparison compiler and remains the leading general optimization surface.
5. Preparation scales with structural DAG nodes `s`, not unfolded tree nodes `t`. The remaining problem is distributed compiler constant factors, not a scaling catastrophe.
6. Profiled compile fractions were approximately: interning 21–26%, lowering 10–15%, live-support work 10–11%, structural hashing 9–12%, rewrite 7–11%, and canonicalization about 6%. No single pass justified broad fusion or an e-graph replacement.
7. Flat Python bigint remained fastest through `live_k=12`; word-packed won at `live_k=16`. The current `WORDS_AUTO_MIN_VARS=16` rule is conservative, not a theorem. A focused reused-validation case at `k=13..15` still had `2.174x` regret, and support-only thresholds transfer poorly across hosts.
8. Corrected selector evidence retained the current policy:
   - raw/BX1 tuning regret geomean `1.0047`, max `1.258`, no `>=2x` rows;
   - raw/reused validation `1.0112`, max `1.591`;
   - CM/BX1 tuning `1.0030`, max `1.193`;
   - CM/reused validation `1.0100`, max `1.900`.
   B2 and EPFL are reused validation, not untouched held-out evidence.
9. Complete explicit packed output requires `Omega(2^k / w)` output work and storage. A BDD, SAT result, factorized form, oracle, or stream is a different artifact until expanded. Raising a guard is not an optimization.
10. Existing cache, related-family, and partial-context experiments improve CM versus uncached CM but do not beat the strongest applicable BitSet/ROBDD/CSE-flat incumbents. Their economics remain real-workload questions.
11. CM operator/quotient artifacts are not semantic XOR. CUDD construction, canonical structure, restriction, symbolic query, and exhaustive truth extraction are distinct artifacts and timing windows.
12. Current structural keys and digests establish engineering identity under documented normalization and collision assumptions, not formal global semantic canonicality.
13. Kronecker/block/lazy-lift ideas apply only to proven independent support blocks or materialized layout operations. They cannot remove final exact-output work.
14. Multiprocessing, GPU, and distributed execution remain negative defaults because admitted workloads do not amortize startup, serialization/copying, synchronization, cache contention, and memory amplification.

Audit memory — what was implemented and validated

- `cm_ir.py`: on the default sharing-aware builder path, removed the redundant object-identity build memo while retaining the structural UID memo. The legacy `share_aware_flatten=False` path retains its identity memo for correctness/lifetime safety.
- `tests/test_build_memo.py`: added regression coverage for sharing-aware versus legacy memo behavior.
- `scripts/cm_prepare_memo_ablation.py`: added refuse-overwrite, paired explicit-arm preparation measurement with exact O(`s`) ordered-DAG signatures, packed-output checks, source/corpus manifests, and allocation measurement.
- Audit/provenance tooling was strengthened to use frozen truths, immutable listed-source snapshots, explicit corpus roles, bounded temporary estimates, and failure/refusal retention.
- Paired BX1+B2 result: 272 rows, 11 repetitions, candidate/baseline compile geomean `0.960113`, cluster interval `[0.950987, 0.972132]`, zero exact mismatches.
- Reused EPFL result: 129 roots, five repetitions in bounded chunks, ratio `0.976840`, circuit-cluster interval `[0.954748, 0.999534]`, zero exact mismatches. Treat this as smaller/noisier confirmation.
- Python-traced compile peak ratio `0.882005`; explicit-arm reproduction `0.882397`. This is temporary Python allocation, not retained RSS.
- Post-consolidation focused tests passed `73 passed, 4 subtests`; the full suite passed `363 passed, 4 subtests`.
- Reconciliation found no semantic code conflict. Relative to the immutable V3 snapshot, current `cm_ir.py` added explanatory legacy-memo comments and the current symmetric driver added uncertainty-provenance metadata; behavior was unchanged.

Claims that must not be resurrected

- no CM speed claim from the B1/E3 `0.9998` residual;
- no claim that B2 or EPFL is untouched held-out evidence;
- no universal `k=6`, `13`, `14`, `15`, or `16` crossover theorem;
- no shortcut around the complete-output lower bound;
- no quotient-as-XOR comparison;
- no blended CUDD build/restrict/extract timing;
- no formal global semantic canonicality claim from current keys/hashes;
- no cache/family/context dominance claim from current synthetic experiments;
- no production selector fitted and accepted on the same or previously reused corpus;
- no hardware-sensitive assertion in ordinary unit tests.

Execution rules

- Define `s` = structural DAG nodes, `t` = unfolded occurrences, `k` = semantic/live support, `m` = compiled instructions/primitive operations, `q` = repeated evaluations, `f` = related expressions/versions, `c` = partial contexts, `w` = word width, and `B` = memory/cache budget.
- Keep `T_prepare`, `q*T_evaluate`, wrapper/dispatch, output conversion, cache lookup/persistence, serialization, and family/context update costs separate.
- Compare identical formulas, semantic support, output ordering, and artifacts. Preserve paired per-formula rows and blocked versus round-robin schedules.
- Report medians and dispersion. Use formula/circuit/family clusters where rows share a generating unit. Never use V3's within-run formula interval as a between-run acceptance interval.
- Record all failures, refusals, timeouts, and skips; do not filter to survivors.
- Before any production edit, save the pre-change source hash, results, and environment. Make one coherent change at a time.

Phase 0 — preserve and inventory

From the repository root, record:

- branch, HEAD, `origin/main`, recent log, `git status --short`, tracked modifications, untracked paths, and ancestry of both `1fd3907` and `0f833bc`;
- available Python interpreters and dependency versions;
- OS, CPU, logical cores, affinity, memory, clock/power caveats, and current time zone;
- hashes of all run-defining source files and frozen corpora;
- current import status for optional `dd.cudd`, Numba, and other native backends, without installing anything.

Create one unique root for this campaign:

$cmStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$cmRunRoot = "docs\audits\2026-08-25-cm-deep-performance\reruns\full-$cmStamp"
if (Test-Path -LiteralPath $cmRunRoot) { throw "Refusing existing run root: $cmRunRoot" }
New-Item -ItemType Directory -Path $cmRunRoot | Out-Null

All following outputs must live below `$cmRunRoot` with unique prefixes. Verify that the frozen selector corpus exists at `deliverables_n22_24/followups_2026_08_24/selector_gap/selector_gap_corpus.jsonl`; replay it without `--build-corpus`.

Compare current run-defining sources against `deliverables_n22_24/corrections_2026_08_25/symmetric/audited_v3_source_snapshot`. Classify all differences as semantic, comment-only, metadata-only, or protocol-affecting before treating V3 as a current-code reference.

Phase 1 — mandatory correctness and fast acceptance

Run focused tests:

python -m pytest -q `
  tests\test_cm_benchmark_audit_integrity.py tests\test_build_memo.py `
  tests\test_bitset_cse.py tests\test_share_aware_flatten.py `
  tests\test_persistent_path_consistency.py tests\test_cm_ir_cost.py `
  --basetemp "$cmRunRoot\.pytest_focused"

Run the full suite:

python -m pytest -q --basetemp "$cmRunRoot\.pytest_full"

Run mixed-corpus smoke:

& .\.venv\Scripts\python.exe scripts\cm_deep_performance_audit.py `
  --suite smoke --corpora bx1,b2,epfl --prep-repetitions 3 `
  --kernel-rounds 5 --max-kernel-temporary-bytes 8388608 `
  --output-prefix "$cmRunRoot\deep_smoke"

Run exactly counterbalanced symmetric V3:

& .\.venv\Scripts\python.exe scripts\cm_symmetric_wrapper_followup.py `
  --rounds 24 --output-prefix "$cmRunRoot\symmetric_v3"

Run explicit-arm one-memo ablation smoke:

& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite smoke --corpora bx1,b2,epfl --repetitions 11 `
  --output-prefix "$cmRunRoot\memo_smoke"

Gate 1:

- Stop performance claims and diagnose as P0 if any exact output, canonical ordered-DAG signature, frozen truth, arm equivalence, cache invalidation, provenance, overwrite, or refusal behavior fails.
- Require exact schedule counterbalancing and expected row counts.
- Smoke timing is a health/drift/allocation diagnostic, not acceptance evidence for a 2–4% optimization.
- Compare the new symmetric point estimates with V3, but do not call a run a failure merely because it leaves V3's formula-cluster interval; that interval does not model between-run drift. Use paired row distributions, environment changes, and repeated schedules to diagnose material movement.
- Write `PHASE-1-DECISION.md` before continuing.

Phase 2 — mandatory representative selector and preparation studies

Run representative mixed-corpus profiling/selection data:

& .\.venv\Scripts\python.exe scripts\cm_deep_performance_audit.py `
  --suite representative --corpora bx1,b2,epfl --prep-repetitions 3 `
  --kernel-rounds 5 --max-kernel-temporary-bytes 8388608 `
  --output-prefix "$cmRunRoot\deep_representative"

Replay the immutable selector-gap corpus; do not regenerate it:

& .\.venv\Scripts\python.exe scripts\cm_selector_gap_study.py `
  --corpus deliverables_n22_24\followups_2026_08_24\selector_gap\selector_gap_corpus.jsonl `
  --prep-repetitions 3 --kernel-rounds 5 `
  --max-kernel-temporary-bytes 16777216 `
  --output-prefix "$cmRunRoot\selector_replay"

Run representative BX1+B2 memo ablation:

& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite representative --corpora bx1,b2 --repetitions 11 --skip-allocation `
  --output-prefix "$cmRunRoot\memo_bx1_b2"

Run EPFL in bounded non-overlapping chunks. Confirm the record count first. For the historical 129-root corpus, use starts `0,20,40,60,80,100,120` and limits `20,20,20,20,20,20,9`, changing the output prefix for every chunk:

& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite representative --corpora epfl --repetitions 5 --skip-allocation `
  --record-start 0 --record-limit 20 `
  --output-prefix "$cmRunRoot\memo_epfl_000"

Aggregate EPFL chunks into new summary files without changing raw outputs. Verify no missing or duplicate roots. Preserve per-root data and use circuit clusters.

Gate 2 reporting:

- separate BX1 tuning from B2/EPFL reused validation;
- for raw and CM selectors, report regret geomean, maximum regret, `>=2x` catastrophic count/rate, selector overhead, refusals, memory-limit behavior, and `k=13..16` slices;
- keep `WORDS_AUTO_MIN_VARS=16` unless a separate future study supplies a new untouched corpus and cross-machine validation;
- compare memo results with `0.960113` BX1+B2 and `0.976840` EPFL, without pooling machines/protocols;
- write `PHASE-2-DECISION.md` and state whether the implementation phase is still justified.

Phase 3 — profile only what moved

If preparation, wrapper, selector, or allocation behavior materially changed, capture a bounded profile:

& .\.venv\Scripts\python.exe -m cProfile `
  -o "$cmRunRoot\deep_smoke.prof" scripts\cm_deep_performance_audit.py `
  --suite smoke --corpora bx1,b2,epfl --prep-repetitions 3 `
  --kernel-rounds 3 --max-kernel-temporary-bytes 8388608 `
  --output-prefix "$cmRunRoot\profile_smoke"

Export cumulative and self-time summaries. Use the ablation tool's existing `tracemalloc` arm where allocation is relevant. Distinguish Python-traced temporary peak, native/NumPy allocation, retained compiled artifacts, and RSS plateau. Report absolute time, percentage of the appropriate window, call count, and scaling with `s`, `k`, and `m`.

Phase 4 — implement the next safe local candidate, DP-R1

Only start after Gates 1 and 2 pass and the current profile still supports preparation/canonical comparison work.

Candidate: a builder-local compact canonical ordering/rank used to avoid repeated deep tuple comparison in `CMIRBuilder._canonicalize_commutative_args`, `make_xor`, `make_eqv`, and related interning paths.

Hard semantic constraints:

- do not change public `CMNode.key` values or representation;
- do not change canonical child order, node fields, node UID semantics, structural/persistent digests, cache keys, serialized artifacts, foreign adoption, associative splice suppression, live support, lowering, output ordering, or exact packed output;
- preserve legacy and sharing-aware behavior;
- do not rely on hash equality as proof of exact ordering/equality;
- use exact O(`s`) ordered-DAG signatures for cross-arm validation, never recursive deep `CMNode.key` equality on sharing-heavy graphs.

Implementation protocol:

1. Inspect current symbols, tests, and commit history explaining ordering/adoption behavior.
2. Save a pre-change source snapshot, hash, phase profile, exact outputs, allocation data, and paired timing.
3. Pre-register the primary corpus/metric, validation slices, schedule, repetitions, and a minimal worthwhile effect based on measured baseline noise and maintenance cost.
4. Implement one small builder-local mechanism. Prefer an ephemeral exact rank/order surrogate whose equivalence to the existing ordering is testable. Do not expose a new public key contract unless separately approved.
5. Add focused tests for commutative ordering, duplicate operands, constants, nested associative sharing, foreign adoption, serialization/persistent paths, legacy mode, and adversarial equal-prefix/deep-sharing cases.
6. Run focused exactness tests before timing.
7. Run alternating/counterbalanced paired cold-compile A/B on identical BX1+B2 formulas. Validate reused EPFL and a high-sharing B3 slice not used to tune the mechanism.
8. Measure phase time, external cold compile, end-to-end wrapper, `tracemalloc`, retained state, and high-sharing tails. Ensure benchmark/helper cost is outside the production window.
9. Run the full test suite and at least one untuned workload.
10. Keep the change only if the effect is reproducibly useful relative to pre-registered noise/maintenance cost, exact signatures and packed outputs all match, and no material validation/high-sharing/memory regression appears. Otherwise revert only this task's experimental edit and retain the negative result under `$cmRunRoot`.

Do not proceed from DP-R1 directly into broad pass fusion or an e-graph rewrite. A separate candidate requires a separate baseline and attribution cycle.

Phase 5 — bounded cache, family, and partial-context diagnostics

First determine whether the repository or user has supplied a real access/version/context trace. Do not inspect private databases or configuration. If a real trace exists and is authorized, document its provenance, privacy constraints, fields, duration, process boundaries, and representativeness. If none exists, run the bounded synthetic diagnostics below, label them synthetic, and do not implement an admission, eviction, incremental, or context policy from them.

Cache baseline and paired persistent-cache runs:

& .\.venv\Scripts\python.exe cm_bench.py `
  --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 123 `
  --cm-layout balanced --cm-compare-hybrid --cm-compare-no-reinflate `
  --cm-hybrid-threshold 7 --no-dd --no-espresso --print-summary `
  --out-prefix "$cmRunRoot\cache_baseline"

& .\.venv\Scripts\python.exe cm_bench.py `
  --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 123 `
  --cm-layout balanced --cm-compare-hybrid --cm-compare-no-reinflate `
  --cm-hybrid-threshold 7 --cm-use-persistent-cache `
  --no-dd --no-espresso --print-summary `
  --out-prefix "$cmRunRoot\cache_persistent"

& .\.venv\Scripts\python.exe cm_bench.py `
  --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 123 `
  --cm-layout balanced --cm-compare-no-reinflate --cm-hybrid-threshold 7 `
  --cm-use-persistent-cache --cm-eval-repeat 50 `
  --no-dd --no-espresso --print-summary `
  --out-prefix "$cmRunRoot\cache_execute_50"

Related-family smoke:

& .\.venv\Scripts\python.exe cm_bench.py `
  --bench-expression-family --sizes 4,8 --trials 2 --max-depth 4 `
  --expr-style mixed_no_constants --family-size 10 `
  --family-variant-style composition_mix --family-shared-blocks 3 `
  --family-force-shared-substructure --cm-layout balanced `
  --cm-compare-no-reinflate --cm-use-persistent-cache `
  --robdd-dd-backend autoref --robdd-order-policy best-of-k `
  --robdd-order-sweeps 5 --family-report-hashes --print-summary `
  --out-prefix "$cmRunRoot\family_smoke"

Only if the intended workload plausibly has high family reuse, run:

& .\.venv\Scripts\python.exe cm_bench.py `
  --bench-expression-family --sizes 8,12,16 --trials 3 --max-depth 4 `
  --expr-style mixed_no_constants --family-size 25 `
  --family-variant-style shared_block_mix --family-shared-blocks 3 `
  --family-force-shared-substructure --family-report-hashes `
  --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache `
  --family-no-robdd --print-summary `
  --out-prefix "$cmRunRoot\family_high_reuse"

Partial-context diagnostic, only if partial assignments match a plausible caller:

& .\.venv\Scripts\python.exe cm_bench.py `
  --bench-partial-contexts --sizes 8,12,16 --trials 3 --max-depth 4 `
  --expr-style mixed_no_constants --partial-contexts 100 `
  --partial-fixed-var-fraction 0.5 --partial-context-style sliding_window `
  --partial-output-mode remaining-vars --partial-reuse-compiled-ir `
  --partial-report-live-vars --cm-layout balanced --cm-compare-no-reinflate `
  --cm-use-persistent-cache --robdd-dd-backend autoref `
  --robdd-order-policy fixed --print-summary `
  --out-prefix "$cmRunRoot\partial_sliding_100"

If justified, sweep fixed fractions `0.25,0.5,0.75` and context counts `25,100,500`, each with a separate prefix. Report original/remaining support, overlap/locality, phase changes, output artifact, cache and BDD manager lifetime, cold versus warm/steady state, and all strongest task-matched baselines.

Required cache/reuse telemetry:

- compiler/schema/options key and structural key scope;
- artifact, retained, serialized, and RSS bytes;
- build, lookup, serialization, deserialization, validation, evaluation, and conversion times;
- hits, misses, wrong-hit checks, evictions, churn, process restarts, cache budget, subsequent `q`, family/version/context IDs, and output type;
- no-cache, current entry-LRU, and serious task-matched incumbent comparisons.

Do not implement byte-LRU, cost-aware admission, TinyLFU, incremental query machinery, BDD manager policy, or context-specific production routing unless a real representative trace supplies the necessary distribution. Preserve a clear negative/deferred conclusion when it does not.

Phase 6 — tooling and memory-policy follow-up

DP-R3, audit-tooling consolidation, may be implemented only after the reruns reveal concrete duplicated or fragile benchmark logic. Keep it separate from DP-R1 and measure harness/runtime impact independently. A valid change may expose shared helpers for timing-window schema, corpus roles, frozen truth verification, source manifests, cluster summaries, typed refusals, and refuse-overwrite behavior. Gate it with deterministic schemas, a quick smoke around 30 seconds, and unit tests that assert behavior rather than hardware speed.

DP-R2, production temporary-memory defaults, is an API/product decision. Without Brian's explicit approval, do not change defaults. You may prepare a decision memo covering proposed `max_output_bytes`, `max_temporary_bytes`, representation scope, override rules, local/remote parity, compatibility impact, and typed pre-allocation refusal tests. If approval is granted, implement the smallest compatible policy with refusal before allocation, no partial artifact, and explicit status propagation.

Phase 7 — explicit opt-in lanes; stop and request approval

Do not run or implement these merely because earlier phases pass:

1. Guard boundary: requires explicit confirmation because complete outputs near/above the guard can consume substantial memory. If approved, use one subprocess per case, pre-allocation estimates, a 45-second hard timeout, 64 MiB estimate cap, 512 MiB RSS cap, three repetitions, and a unique prefix with `scripts/cm_above_guard_boundary.py`. Never run an unbounded `k` sweep.
2. Native CUDD: first check import status without installation. If unavailable, request dependency approval. If available and approved for the study, keep build, order/reorder, node count, manager reuse, restriction, symbolic query, and exhaustive extraction separate.
3. Native/JIT/SIMD: requires a real repeated batch whose word kernel dominates preparation, binding, copying, and output, plus approval for Numba/LLVM or a native build. Use flat opcode/operand arrays and explicit `uint64` buffers, exact scalar equality, cold/warm compile, AVX2 baseline, optional AVX-512 feature dispatch, scalar fallback, concurrency, and peak-memory gates. Never JIT arbitrary Python bigints as fixed-width integers.
4. Cloud/Runpod/GPU/distributed/cross-machine: request approval for exact provider/host, target, expected cost, duration, and external writes. Use immutable source/corpus bundles and unique remote roots. Retrieve failures and environment metadata. Report machines separately unless an explicit hierarchical model justifies pooling.
5. Streamed/chunked large output: requires a caller that accepts a changed output interface. It may reduce peak memory or latency-to-first-chunk, never total `Omega(2^k/w)` work.

Existing Runpod symmetric results are descriptive replications: overall approximately `0.903–0.913`, `k=16` approximately `0.975–0.977`; public wrapper remained slower. Do not pool them as exchangeable local rows.

Statistics and reproducibility requirements

- Record exact commands, environment, affinity, seeds, source/corpus hashes, timing-window definitions, schedule, warmup, repetitions, and output inventory.
- Preserve raw per-formula/per-root rows and formula/circuit/family identifiers.
- Use medians plus appropriate dispersion; geometric means for paired ratios; deterministic cluster-aware bootstrap where generating units repeat.
- Keep row-weighted estimates as sensitivity results when formulas have unequal ambient repeats; the primary V3 weighting gives each formula equal influence.
- Analyze cold and warm runs separately. Do not pool blocked and round-robin schedules, machines, protocols, artifacts, failures, or support regimes without an explicit model.
- Report selector overhead and all non-admissions, refusals, timeouts, dependency absences, and skips.
- Test at least one workload not used to tune each implementation.
- No performance assertion belongs in ordinary unit tests.

Required campaign deliverables under `$cmRunRoot`

1. `RUN-ENVIRONMENT.json`: repository state, commits/ancestry, status, hardware, interpreters/dependencies, affinity, seeds, commands, source/corpus hashes, and artifact inventory.
2. `AUDIT-MEMORY.md`: concise durable record of accepted claims, implemented one-memo change, V3 correction, evidence roles, rejected ideas, and lower bounds.
3. `RUN-RESULTS.md`: exact timing windows, schedules, repetitions, medians/dispersion, paired/cluster inference, selector regret, allocation/memory, cache/reuse results, and historical comparison.
4. `RUN-DECISIONS.md`: confirmed, changed, inconclusive, negative, deferred, approval-blocked, and superseded findings.
5. Raw CSV/JSON/JSONL for every attempted case, including failure/refusal rows and immutable source manifests.
6. If DP-R1 is attempted: `DP-R1-PRECHANGE.md`, source snapshot, paired raw data, exactness report, allocation/memory report, before/after summary, and rejection record if not kept.
7. `OPTIMIZATION-BACKLOG-UPDATE.md`: ready now, needs real workload, needs approval/dependency/hardware, theoretically blocked, and tested/rejected.
8. `NEXT-AGENT-HANDOFF.md`: exact final repository state, owned files, tests/benchmarks, results, unresolved hypotheses, approvals, exact next commands, preservation list, and claims that must not be resurrected.

Completion standard

The task is complete only when:

- repository preservation and evidence ancestry are documented;
- focused and full correctness gates pass or a P0 is diagnosed and resolved;
- mixed smoke, symmetric V3, and memo smoke are rerun;
- representative selector and preparation studies are completed without survivor bias;
- bounded cache/family/context diagnostics are run where their workload assumptions are plausible and are not overclaimed;
- DP-R1 is either implemented and retained through every gate or rejected with reproducible negative evidence;
- DP-R3 and DP-R2 are handled according to evidence and approval boundaries;
- exact outputs, canonical ordering, cache/persistent identity, refusal behavior, and memory are revalidated;
- superseded claims remain superseded;
- all outputs are reproducible and uniquely named;
- `git status --short`, `git diff --check`, `git diff --stat`, and the exact owned-file list are reviewed before reporting done.

Do not commit or push unless Brian explicitly requests it in the active task. Lead the final report with what was confirmed, what changed, whether DP-R1 was kept, and what remains gated by real workloads or approval.
```
