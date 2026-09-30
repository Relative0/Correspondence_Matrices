# Computation validity audit

## Evidence classes and identity

The frozen baseline, original Theory bundle, and external Astra audit are unchanged under `inputs/`; their archive hashes appear in `INPUT_PROVENANCE.json`. The external checker is imported with its original source and result. New local executions live under `runs/`. Source identity for the dirty working repository is the file-hash set in `MAIN_SOURCE_PIN.json`, supplemented by HEAD, not a claim that HEAD alone reproduces current files. Thirteen loaded main-project modules were copied into `main_source_snapshot/` for portable regression.

The scope of this audit includes the strongest exact checks and the complete original 38-case timing replay. It does not claim to rerun historical C35/C36/P14 remote campaigns or the separate pair-compiler study. Historical Runpod scripts in an archive do not establish a new cloud execution.

## Exact and empirical replay

`runs/baseline_replay/` records eight clean child-process commands with frozen inputs. The reproduced coverage includes 105,292 conditioning checks, all 65,536 binary 4x4 matrices in the extension suite, 2,000 recompressions, 6,750 legacy-adapter queries and 7,070 fresh-instance query comparisons. Labels such as corruption rejection must be read with their source tests: changed external-source semantics are not equivalent to hostile parser fuzzing.

`runs/independent_replay/` reruns the external oracle. Its substantive result object matches the original. Exact operator ranks cover all 0<=k<=n<=6; fibres exhaust all Boolean functions through n=4; class-level injectivity includes all rank<=1 and rank<=2 functions on the six nonempty cuts through n=4 and complete rank-one classes for (2,3) and (3,3). Restricted profiles exhaust 7,576 rank<=2 matrices times 81 restrictions. These are finite checks and do not establish theorem priority.

`runs/theory_replay/` reruns the supplied SymPy verifier through the external audit's output-path-only portability wrapper. No mathematical change is hidden in the wrapper.

`runs/benchmark_replay/` executes all 38 cases, three methods, five repetitions and 128 queries: 570 trials, 72,960 measured query calls. Artifact per-case median lifecycle wins versus packed remain **0/38**. These times are machine-specific and were not collected on an isolated host; no new speedup estimate, confidence interval, or hardware-general ratio is asserted. Original query hashes and case IDs are checked in the delivery validation. The source universe is still 26 outputs of one control design plus 12 synthetic controls.

The old endpoint starts from a prepared truth integer. It is a same-process fresh-object replay; imports and OS caches are warm/uncontrolled. Its packed persistence is JSON, not the new matched binary format. Its Python ROBDD is not CUDD. Earlier extrapolated 1,000-query estimates and parse-only reload proxies remain historical; no new result is retroactively substituted into those arms.

## C1 integration — completed

The adapter translates oracle coordinate j to project coordinate n-1-j; truth integer bit positions are unchanged. It compares independent counts with the main factorization, the frozen baseline's conditioned artifact, fused count and Walsh count. Coverage is 65,536 factorizations, 613,656 restricted low-rank profiles, and 42,192 noncontiguous/reversed/unequal-cut and cumulative-update comparisons. It includes n=0/1, constants, zero-rank states, residual coordinate names and original parity/histogram counterexamples. Source and query hashes accompany the new result.

An initial new-test failure misused `partitioned_bits`, whose return is `(bits,p,q)`, as an integer. The adapter was fixed; original implementation and frozen research results were untouched. `FAILURE_AND_CONTINUATION_LOG.md` records this and subsequent infrastructure repairs.

## C3 corpus and comparator infrastructure — bounded version completed

`corpus_v1/PROTOCOL.json` and its hash predate extraction. All original arithmetic and random/control BLIF designs from the local pinned EPFL snapshot are included: 20 designs, two families, 2,861 outputs. No best-results variants are counted as extra designs. Every output receives status. Structural support <=12 admits 1,088 outputs from 11 designs; 1,773 are explicitly excluded. The structural support bound is conservative, and semantically irrelevant axes remain declared. There are no hidden success-only denominators.

Two predefined cuts per output, deduplicated when identical, yield 2,119 rank observations. Zero/constant cases and trivial cuts remain labeled and cannot be used as evidence for the nonempty-cut Q13/Q14 theorem. Rank histograms are reported separately for each design. High-support exclusions prevent general incidence claims for the entire benchmark suite. In particular, two designs account for many admitted cases; output counts are not independent sample counts.

Design-disjoint splits use a deterministic hash ordering within each family. The suite has historical project exposure, so the split is prospective for this campaign rather than a claim of blind discovery. No main holdout timings were run. One small development output is used only to validate raw-source lifecycle plumbing.

Independent natural extraction validation checks all 1,088 admitted functions against the existing repository BLIF parser/evaluator. The 31 constant outputs use an independent scalar evaluation of that parser's node graph because its packed API excludes constants. All hashes agree.

The comparator set now contains:

- Matched packed **binary** persistence, including header, named coordinate scope and truth payload; index construction is explicit.
- The prior coordinate-indexed GF(2) factor implementation, with per-query selector/grouping work charged. This is a baseline, not a T3 solution.
- `dd==0.6.0` compiled CUDD, fixed variable order with dynamic reordering disabled, exact integer traversal, and an attributed task-local binary DAG serializer. Compilation, traversal, serialization and reload costs are charged. It is a credible compiled representation comparator, not an optimized C-native counting loop.

No decomposition-quality superiority is claimed. If future work makes such a claim, an established decomposition method and matched cut/order search budgets are still required; the present CUDD endpoint cannot substitute for that additional comparison.

## C4 lifecycle infrastructure — completed with declared cache limitation

Every record preserves n,p,q,actual rank,stored width,cut/order,k,cumulative budget,state type,query count,reuse mode,source/query/artifact hashes and per-query residual dimensions. Source extraction is charged from BLIF when a raw source is provided. The phases include compile/discover, source verification before save and after load, serialization/file write, load, indexing, update and query. Oracle and metadata overhead is separately recorded, not hidden in one method's query time.

Independent queries use the original state. Sequential queries update a residual state under a cumulative per-episode budget; starting a new episode explicitly returns to the original state. This is not the false reset-horizon summary guarantee. Each requested batch is actually executed. Warm-up counts are explicit and charged.

Same-process fresh-object, separate-process load, and warm reuse are distinct modes. Separate-process load retains both producer and consumer receipts for complete lifecycle totals. Linux advisory cold-load support uses file-specific fsync/fadvise; cache-preparation time is recorded. The filesystem/host may ignore eviction, so physical cold-cache status remains unproven. No global cache flush or system tuning is performed.

Peak memory is absolute process high-water RSS (Windows PeakWorkingSetSize or Linux ru_maxrss), measured separately from serialized bytes. It includes interpreter/input/verification overhead and is not an isolated allocation delta. Child timeouts are 90 seconds and leave command, stdout, stderr and failure records. The final scientific campaign must also freeze hardware isolation, resources, method ordering and T3-specific phases.

All three backends pass 7,070 exhaustive original/residual/reloaded-residual query cases each through n=3, with binary round-trip and trailing-byte rejection tests. Windows and Linux lifecycle smoke records are preparation evidence only. The final acceptance run additionally covers raw-source preparation and separate-process advisory-load paths.

## C2 — intentionally not run

Final clean-environment checking exposed an undeclared legacy NumPy import: the old baseline's standard-library-only documentation is inaccurate for its legacy-adapter correctness test. The failed Linux receipt is preserved, NumPy 2.3.2 is pinned and bundled, and the retry is separate. This changes dependency accounting, not the mathematical results.

The user confirmed T3 is not frozen and prohibited the main campaign. `PROTOCOL_C2_PENDING.json` preserves proposed grids and required fields but is explicitly **not** a preregistered scientific hypothesis. No timing result here is described as confirmation or falsification of T3. No Runpod job or paid service was launched.

**Next: SEND RESULTS/QUESTION TO THEORY**, then CONTINUE IN COMPUTATION here once the target arrives. Reopen the stronger-paper gate only after the frozen prediction has corresponding executed evidence.
