# CM Post-Consolidation Rerun Prompt

Copy the text below into a new task when a fresh benchmark campaign is wanted. It is phased: complete and interpret each gate before starting expensive optional work.

```text
Work in C:\Users\brian\Documents\CM_Computation.

Mission: run a rigorous post-consolidation acceptance and performance campaign for the Correspondence Matrix repository, using current code while preserving every accepted historical artifact. Begin from a revision containing consolidation commit 1fd3907dbc1986cb2d8a9f0f8cab2b5920a415ce (`Audit and consolidate CM benchmark corrections`). A descendant documentation-only reconciliation commit is acceptable. Verify the current branch and worktree; do not assume they are clean.

Authority and preservation

1. Read all applicable AGENTS.md files and then read, in order:
   - README.md
   - deliverables_n22_24/CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md
   - deliverables_n22_24/CM_BENCHMARK_REFRESH_CLAIM_MAP_ADDENDUM_2026-08-03.md
   - deliverables_n22_24/CM_GAP_POST_ACCEPTANCE_OPTIMIZATION_DECISION_2026-08-03.md
   - deliverables_n22_24/corrections_2026_08_25/CM_BENCHMARK_AUDIT_CORRECTION_REPORT_2026-08-25.md
   - docs/audits/2026-08-25-cm-deep-performance/CM-DEEP-PERFORMANCE-AUDIT.md
   - docs/audits/2026-08-25-cm-deep-performance/CM-BENCHMARK-RESULTS.md
   - docs/audits/2026-08-25-cm-deep-performance/CM-OPTIMIZATION-BACKLOG.md
   - docs/audits/2026-08-25-cm-deep-performance/audit_manifest.json
2. Record branch, HEAD, `git status --short`, `git log -5 --oneline --decorate`, and whether `git merge-base --is-ancestor 1fd3907dbc1986cb2d8a9f0f8cab2b5920a415ce HEAD` succeeds.
3. Preserve `.claude/`, `external/`, `tmp/`, unrelated dirty files, source snapshots, and accepted raw/summary/audit artifacts. Never read `.env*`, credentials, token caches, or private configuration.
4. Do not pull, install dependencies, create cloud jobs, change remote state, commit, or push without Brian's explicit approval in that task. Do not use `git add .`. Do not modify production code merely to make a benchmark pass.
5. Use `.venv\Scripts\python.exe` for benchmark drivers. The virtual environment currently lacks pytest, so use global `python` for pytest unless inspection proves otherwise. Do not install pytest just to change that.
6. Make a unique run root and never overwrite accepted evidence:

   $cmStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
   $cmRunRoot = "docs\audits\2026-08-25-cm-deep-performance\reruns\$cmStamp"
   if (Test-Path -LiteralPath $cmRunRoot) { throw "Refusing existing run root: $cmRunRoot" }
   New-Item -ItemType Directory -Path $cmRunRoot | Out-Null

Claims that must remain settled

- Do not optimize or promote the B1/E3 CM/CSE-flat residual: `0.9998`, interval `[0.9747, 1.0249]`, is parity on that workload.
- Exactly counterbalanced local V3 supersedes V2 for the B2/B4 local headline: formula-balanced bare CM/CSE-flat `0.8905696773`, interval `[0.8740654100, 0.9072717742]`; at `k=16`, `0.9612336537`, interval `[0.9289740604, 0.9941768792]`. Formula-balanced public wrapper/CSE-flat is `3.0941361850`, interval `[2.8830826921, 3.3108182215]`. These estimates are conditional on the corpus, machine, and run; they do not model between-machine or between-run uncertainty.
- B2 and EPFL are reused validation evidence, not untouched held-out evidence.
- Keep `WORDS_AUTO_MIN_VARS=16` unless a genuinely new frozen corpus and cross-machine validation support a replacement. One corrected reused-validation row at `k=13..15` still had `2.174x` regret.
- Complete packed output requires `Omega(2^k / w)` work and storage. Never raise a support guard without a memory-safe, fail-closed protocol.
- Keep preparation, kernel, wrapper, conversion/extraction, cache, serialization, restriction, and BDD construction windows separate. A structural quotient is not semantic XOR.
- Do not claim global semantic canonicality from engineering keys or hashes.

Phase 0 — exact state

- Capture interpreter/dependency versions, OS, CPU, process affinity, source hashes, corpus hashes, commands, seeds, HEAD, and status into the new run root.
- Compare current run-defining sources with `deliverables_n22_24/corrections_2026_08_25/symmetric/audited_v3_source_snapshot`. Classify every difference as semantic or comment/metadata-only before using V3 as a current-code reference.
- Confirm the frozen selector corpus exists at `deliverables_n22_24/followups_2026_08_24/selector_gap/selector_gap_corpus.jsonl`. Do not rebuild it for a replay.

Phase 1 — mandatory correctness gates

python -m pytest -q `
  tests\test_cm_benchmark_audit_integrity.py tests\test_build_memo.py `
  tests\test_bitset_cse.py tests\test_share_aware_flatten.py `
  tests\test_persistent_path_consistency.py tests\test_cm_ir_cost.py `
  --basetemp "$cmRunRoot\.pytest_focused"

python -m pytest -q --basetemp "$cmRunRoot\.pytest_full"

Record passes, failures, skips, subtests, and elapsed time. If a correctness, provenance, overwrite, cache-invalidation, or exact-output test fails, stop performance claims and diagnose it as P0. Remove only task-owned pytest temporary directories after resolving and verifying that each is below `$cmRunRoot`; retain logs and metadata.

Phase 2 — mandatory quick local acceptance

& .\.venv\Scripts\python.exe scripts\cm_deep_performance_audit.py `
  --suite smoke --corpora bx1,b2,epfl --prep-repetitions 3 `
  --kernel-rounds 5 --max-kernel-temporary-bytes 8388608 `
  --output-prefix "$cmRunRoot\deep_smoke"

& .\.venv\Scripts\python.exe scripts\cm_symmetric_wrapper_followup.py `
  --rounds 24 --output-prefix "$cmRunRoot\symmetric_v3"

& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite smoke --corpora bx1,b2,epfl --repetitions 11 `
  --output-prefix "$cmRunRoot\memo_smoke"

Require zero exact-output/canonical/frozen-truth/arm-equivalence mismatches, exact schedule counterbalancing, complete rows including failures/refusals, and valid source/corpus manifests. Preserve per-formula paired rows. Report medians, dispersion, formula-balanced estimates, row-weighted sensitivity estimates, and cluster-aware intervals. Compare with committed evidence without replacing it. Treat effects near ordinary noise as inconclusive.

Write an interim decision here. Do not automatically run every later phase; continue only where the result or intended use justifies the cost.

Phase 3 — representative engine and selector replay

& .\.venv\Scripts\python.exe scripts\cm_deep_performance_audit.py `
  --suite representative --corpora bx1,b2,epfl --prep-repetitions 3 `
  --kernel-rounds 5 --max-kernel-temporary-bytes 8388608 `
  --output-prefix "$cmRunRoot\deep_representative"

& .\.venv\Scripts\python.exe scripts\cm_selector_gap_study.py `
  --corpus deliverables_n22_24\followups_2026_08_24\selector_gap\selector_gap_corpus.jsonl `
  --prep-repetitions 3 --kernel-rounds 5 `
  --max-kernel-temporary-bytes 16777216 `
  --output-prefix "$cmRunRoot\selector_replay"

Analyze tuning (BX1) and reused validation (B2/EPFL) separately. For raw and CM windows report geometric-mean regret, maximum regret, `>=2x` catastrophic misroutes, selector overhead, refusals, and results near `k=13..16`. Do not integrate a feature selector from this replay; the corpus is no longer untouched.

Phase 4 — representative preparation validation

& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite representative --corpora bx1,b2 --repetitions 11 --skip-allocation `
  --output-prefix "$cmRunRoot\memo_bx1_b2"

Run EPFL in bounded, non-overlapping chunks. Determine current record count from the frozen corpus. For the historical 129-root corpus, use starts `0,20,40,60,80,100,120` with limits `20,20,20,20,20,20,9`, changing prefix for every chunk:

& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite representative --corpora epfl --repetitions 5 --skip-allocation `
  --record-start 0 --record-limit 20 `
  --output-prefix "$cmRunRoot\memo_epfl_000"

Aggregate without changing raw files. Check missing/duplicate roots, preserve per-root rows, and use circuit clusters for EPFL uncertainty. Compare with accepted ratios `0.960113` on 272 BX1+B2 rows and `0.976840` on 129 reused-EPFL roots, but never pool different protocols or machines.

Phase 5 — profiler and allocation diagnostics

Only if preparation or wrapper behavior materially moved:

& .\.venv\Scripts\python.exe -m cProfile `
  -o "$cmRunRoot\deep_smoke.prof" scripts\cm_deep_performance_audit.py `
  --suite smoke --corpora bx1,b2,epfl --prep-repetitions 3 `
  --kernel-rounds 3 --max-kernel-temporary-bytes 8388608 `
  --output-prefix "$cmRunRoot\profile_smoke"

Export cumulative and self-time summaries. Use the existing ablation allocation arm for `tracemalloc`; distinguish retained memory from temporary peak. Report absolute time, relevant-window percentage, call count, scaling with `s/k/m`, and realistic versus constructed occurrence.

Phase 6 — cache cold/warm and reuse economics

These are diagnostics, not production-claim gates. Use identical seeds/expressions for paired runs, isolate task-owned cache state between cold runs, record cache bytes and RSS, and never delete an unverified cache location.

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

Report cold miss, warm hit, lookup, serialization/deserialization, evaluation, conversion, hit/miss/eviction counts, resident bytes, temporary peak, and RSS plateau separately. Entry-count-only evidence cannot justify a byte-budgeted policy.

Phase 7 — related-family reuse

Reproduce the historical small shape:

& .\.venv\Scripts\python.exe cm_bench.py `
  --bench-expression-family --sizes 4,8 --trials 2 --max-depth 4 `
  --expr-style mixed_no_constants --family-size 10 `
  --family-variant-style composition_mix --family-shared-blocks 3 `
  --family-force-shared-substructure --cm-layout balanced `
  --cm-compare-no-reinflate --cm-use-persistent-cache `
  --robdd-dd-backend autoref --robdd-order-policy best-of-k `
  --robdd-order-sweeps 5 --family-report-hashes --print-summary `
  --out-prefix "$cmRunRoot\family_smoke"

Only if the intended workload plausibly has high family reuse, run a larger non-ROBDD diagnostic:

& .\.venv\Scripts\python.exe cm_bench.py `
  --bench-expression-family --sizes 8,12,16 --trials 3 --max-depth 4 `
  --expr-style mixed_no_constants --family-size 25 `
  --family-variant-style shared_block_mix --family-shared-blocks 3 `
  --family-force-shared-substructure --family-report-hashes `
  --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache `
  --family-no-robdd --print-summary `
  --out-prefix "$cmRunRoot\family_high_reuse"

Report reuse distributions, unique/repeated subtree hashes, cold/warm totals, compilation avoided, cache bytes, and task-matched memoization/ROBDD comparators where applicable. Do not infer real policy-version economics from synthetic family generation.

Phase 8 — partial contexts

Run only if partial-assignment streams matter to the intended caller:

& .\.venv\Scripts\python.exe cm_bench.py `
  --bench-partial-contexts --sizes 8,12,16 --trials 3 --max-depth 4 `
  --expr-style mixed_no_constants --partial-contexts 100 `
  --partial-fixed-var-fraction 0.5 --partial-context-style sliding_window `
  --partial-output-mode remaining-vars --partial-reuse-compiled-ir `
  --partial-report-live-vars --cm-layout balanced --cm-compare-no-reinflate `
  --cm-use-persistent-cache --robdd-dd-backend autoref `
  --robdd-order-policy fixed --print-summary `
  --out-prefix "$cmRunRoot\partial_sliding_100"

If justified, sweep fixed fractions `0.25,0.5,0.75` and context counts `25,100,500` with separate prefixes. Preserve output-artifact equivalence. Report original `k`, remaining live `k`, overlap, context count, cache state, cold/steady-state totals, CM no-cache/cache, BitSet full/restricted, and ROBDD build-once/restrict/extract windows. Existing evidence says cached CM improves over uncached CM but does not beat BitSet or ROBDD at `n<=16`; require new evidence to change that conclusion.

Phase 9 — guarded output boundary

This is opt-in because complete outputs near or above the guard can consume significant memory. Use one subprocess per case, pre-allocation estimates, hard timeouts, an RSS cap, and fail-closed wrapper checks:

& .\.venv\Scripts\python.exe scripts\cm_above_guard_boundary.py `
  --timeout-seconds 45 --estimate-cap-bytes 67108864 `
  --rss-cap-bytes 536870912 --repetitions 3 `
  --output-prefix "$cmRunRoot\above_guard"

Do not run an unbounded `k` sweep. Do not interpret guard refusal as a correctness failure. Report every completed, refused, timed-out, and RSS-limited case.

Phase 10 — BDD/CUDD, native/JIT/SIMD, and external machines

- Check imports without installing anything. If `dd.cudd` is unavailable, record it and stop the CUDD lane unless Brian approves dependency work. If available, keep construction, canonical structure, restriction, and exhaustive extraction as separate artifacts and timing windows.
- Do not add Numba, LLVM, C/C++, Rust, or SIMD code unless profiling shows Python dispatch or temporary word arrays dominate a real repeated workload and Brian approves dependencies/build work. Include compilation/startup/copy/conversion costs and a trusted exact reference.
- Do not start Runpod, paid/cloud compute, GPU work, or distributed workers without explicit approval of target, cost, and effect. If approved, use corrected immutable corpus/source bundles, unique remote roots, instance metadata, exact hashes, and retrieve failures as well as successes. Report machine-stratified results; never pool machines without an explicit model.
- Existing Runpod symmetric results are descriptive replications (overall about `0.903-0.913`, `k=16` about `0.975-0.977`). They do not replace the local formula-cluster interval.

Phase 11 — synthesis and change gate

Create new, dated, non-overwriting outputs under `$cmRunRoot`:

- `RUN-ENVIRONMENT.json`: commands, versions, hardware, affinity, seeds, HEAD, status, source/corpus hashes, output inventory;
- `RUN-RESULTS.md`: timing definitions, repetitions, schedule, medians, dispersion, paired/cluster-aware inference, refusals, failures, comparison to committed evidence;
- raw CSV/JSON/JSONL from every attempted case, including failures/skips;
- `RUN-DECISION.md`: confirmed, changed, inconclusive, negative, and blocked findings;
- `NEXT-RUN-HANDOFF.md`: exact state, remaining work, and approval gates.

Do not change production code unless a measured bottleneck or P0 defect survives acceptance, exact reference outputs exist, the edit is small and attributable, and same-formula validation can demonstrate benefit. For every candidate: save pre-change evidence; make one coherent change; run focused correctness; run alternating/counterbalanced paired benchmarks; check temporary and retained memory; validate an untuned workload; keep it only for a reproducible useful gain or a real defect fix. Revert only your own rejected experiment.

Before reporting completion, run `git status --short`, `git diff --check`, and `git diff --stat`. Identify exactly which files the task created or changed. Do not commit or push unless Brian explicitly asks in that task.
```
