# CM-family repairs and bounded speed investigation

## Outcome

Phases 0–6 of the supplied repair plan are implemented in the separate worktree
`tmp/cm-family-repair-20260915`, branch `codex/cm-family-repair-20260915`, based on
`4d9b869fb7b22eb6263ef613b5a9d41fcbbb78dd`. Its implementation baseline is
`e334de594262059cc18cf37eaab56b0f79e94843`.

The changes fix explicit evaluator configuration, make family timing and output
provenance observable, remove duplicate fallback planning and reuse one sharing
analysis on persistent root misses. They preserve output guards, canonical CM
structure, engine precedence, cache policy and the public result contract.

These are **local development diagnostics**, not confirmation benchmarks. No
scientific disposition changed. Nothing was committed, pushed or merged.

## What changed and why

### 1. Explicit configuration and truthful results

Family and partial workloads now forward `cm_flat_eval`; equivalence forwards
both flat and words settings. `evaluate_compiled` accepts an explicit optional
`flat_eval` argument while retaining module-default behavior when omitted.
Words still takes precedence and still selects the conservative existing engine
from the actual output width.

Tests deliberately set module defaults opposite to the supplied configuration.
Mathematical correctness had generally survived the old mismatch; the defect
was that a purportedly matched comparison could run different engines.

Family rows now report actual engines, widths/statuses and completed, checked
and correct variant counts. Unequal variant/reference lists raise rather than
silently truncating. Small reduced outputs are expanded only for their full
oracle comparison, so the benchmark checks independence of omitted variables
without changing the public reduced result.

Summary groups preserve schema, engine distributions and output/configuration
contracts. Disabled backends remain visible. Configuration repairs are not
counted as unchanged-engine performance improvements.

### 2. Explicit observation boundaries

The default-off `family_profile_timing` option (CLI `--family-profile-timing`)
records nested wall/process-CPU spans, exclusive partitions, parent/boundary
metadata and failure status. Reference construction, structural diagnostics,
cache reset, compile, evaluation, conversion and correctness checks have separate
spans. Legacy fields remain available with their original boundaries.

The independently measured caller covers the additional returned-row and trace
serialization work outside the nested capture. Its residual remains named as
such. It is not relabeled as kernel time or mechanically distributed over phases.
Raw timings, cProfile observations and memory passes are separate.

Core CM receives a caller-supplied observer and has no dependency on the new
benchmark module. This also preserves the standalone import closure. A temporary
dependency regression was detected by the research check, corrected, and its
failed record retained.

### 3. One public admission plan

The wrapper now shares fixed-variable handling, basis selection, output
estimation and budget admission. Previously a diagnostics-off, flat-enabled
call that needed NumPy fallback could plan once in the preliminary fast block,
then plan again in the generic block.

`flat_fast_path=False` remains supported. Both paths retain their historical
invalid-threshold/refusal precedence, complete/reduced output behavior and
diagnostic accumulation/refusal cleanup. This cleanup does add a small amount
of generic control to packed fast calls; it is not universally faster.

### 4. One sharing analysis on root-only cache misses

Persistent compilation already computed structural UIDs and shared associative
classes to choose its safe reuse regime. The builder now consumes that same
call's plan on a root-only miss. The plan pins the immutable source root and is
discarded/restored after the synchronous build. A different root or different
sharing option does not consume it.

The normal builder, reentrant/subclass dispatch, canonical keys/flat programs,
foreign-node adoption, option separation, eviction and GC/id safety remain
covered by tests. No persistent source-plan cache was added. Digest preparation
and eligibility still recur on warm calls.

Optional cache diagnostics distinguish hit position (root/subtree), origin
(same/prior call), regime, eviction and extent. The two hit axes must not be
added together. The separate memory pass measures reachable graph weights and
Python-visible retention without retaining observer references to nodes.

## What the measurements support

The final resident comparisons alternate independent baseline/candidate CM
modules and caches in one process, with 21 blocks and two warmup blocks. This
controls short-term host drift more closely than the separate fresh workers.
Exact inputs, settings and output contracts are shared; family row delivery now
also includes the required provenance.

| Mechanism/case | Final resident result, two runs | Interpretation |
|---|---|---|
| Shared-root cold persistent compile | 9–11% lower; 14–17 us saved | **Measured.** Prepasses fall from two to one; normal compilation stays near parity. |
| Flat-enabled NumPy fallback | 5–10% lower; 8–14 us saved | **Measured.** Admission occurs once; generic control changes are much smaller. |
| Zero-reuse composition family, cache enabled | 6–13% lower; 135–315 us saved per five variants | **Measured** caller change including new reporting. Persistent execution still costs more than no-cache on this family. |
| Packed/words/reduced fast wrapper | Approximately 0.7–1.6 us added | **Measured.** Small cost of consolidated control, below the declared repeatable material-regression margin. |
| Identical cached family | 41–51 us added per eight variants | **Measured.** Extra accounting/reporting costs time even when compilation hits; exact metadata-only share is unresolved. One run crosses the margin; the other does not. |
| Shared-subtree family | Small/noisy caller increase | No speed claim. The cache's expensive integration path remains. |

No final resident sentinel exceeds **both** its percentage and absolute
regression margin in both runs. This is a bounded review criterion, not proof
that every workload improves. Fresh-worker records sometimes disagree strongly,
including unchanged controls; they are retained and cannot establish a broad
causal speed claim. The final fresh runs bind all 41 worker cells to final source.

The measured family cache structures explain why hit counts remain misleading:

| Family | Root / subtree hits | Cache entries / reachable CM nodes | Python retained bytes |
|---|---:|---:|---:|
| Identical | 7 / 0 | 7 / 7 | See final mechanism record |
| Shared-block mix | 0 / 52 | 58 / 61 | See final mechanism record |
| Composition mix | 0 / 0 | 5 / 75 | See final mechanism record |

These counts are separate from timings. Cached subtree integration still calls
foreign adoption/interner helpers, while a root hit avoids construction. The
five composition roots retain the same graph extent over 64 additional resident
rounds. Native/RSS retention and production-session distributions remain unknown.

All worker blocks, CPU samples, profile counts, per-helper costs, Python peak and
retained bytes, CM/source/program/support sizes and phase percentages are in
[PROFILE_RESULTS-v2.json](PROFILE_RESULTS-v2.json), [TIME_LEDGER-v2.md](TIME_LEDGER-v2.md),
and the linked raw records. The observed fresh-worker execution sum is about
73 seconds including imports/profile/memory; all diagnostic execution remained
under five minutes, well inside the two-hour bound.

## What still costs time

The full-information nature of an explicit relation still matters when the
requested output enumerates all assignments: a full k16 packed result occupies
8192 bytes, even if only four variables affect it. It does not explain duplicate
UID walks, duplicate admission, Python dictionary/tuple work, or incorrect
configuration forwarding. Those belong to this implementation and its wrapper.

CSE-flat still preserves useful sharing while retaining a smaller execution
representation than CM. This repair does not change that predecessor finding,
nor does it establish a new CM-versus-CSE advantage. The prepared k4 bare kernels
remain small relative to the public wrapper. The words16 bare control in the
worker is bigint, so its gap from a public words call is not pure wrapper cost.

Raw CM and family CM share public output/binding work. Persistent family CM also
pays eligibility, digests, cache policy, adoption and retained-graph management.
Eliminating one duplicate walk does not eliminate those costs. Explicit output
work recurs with output size; prepared programs, bindings and retained roots can
amortize under their existing lifetimes.

SAT, exact count, equivalence status and supplied assignments can request much
less information than a complete relation. Mathematical expressiveness alone
does not make full-relation execution an appropriate representation for those
tasks. The frozen task-matched comparisons, Y02–Y05 boundary audit and no-go
dispositions remain governing. No held-out inputs were loaded or executed.

## Remaining opportunities and uncertainty

[OPPORTUNITIES.md](OPPORTUNITIES.md) closes the bounded queue with keep/defer/reject
decisions. Repeated warm digests and foreign adoption remain useful mechanisms
to study if a real workload justifies their cost. Another node-count cache is
unwarranted because one already exists. Further budget/binding caches, byte
capacity policies, compact-IR redesign and task-specific routing remain deferred.

We cannot infer a cross-machine win, native memory use, exact startup/import/
transport shares, production reuse distribution, or an additive metadata-only
percentage from these data. Tracer overhead resides in the measured capture;
cProfile cumulative entries overlap; Windows process CPU has coarse resolution.
Early records did not snapshot native-thread environment values. The resident
comparisons share one process and its settings. No scientific conclusion relies
on an assumed environment equality between historical workers.

## Verification and delivery

- Final combined affected, focused-research and package tests: **448 passed,
  one skipped, four subtests passed**. Its one chart-data identity failure also
  reproduces on the untouched baseline. All repair-specific tests passed.
- The final eviction/reinsertion origin correction passed **63 targeted tests
  plus four subtests**, and final-source measurements were refreshed without
  overwriting earlier records.
- Research reproducibility: **286 current + 121 frozen-snapshot tests passed**
  after fixing the new dependency regression.
- Application and count-closure verifiers stop on source-identity mismatches
  that also reproduce on the baseline. Their frozen evidence was not regenerated.
- Both predecessor manifests verify: 57 primary audit artifacts, 46 predecessor/
  input bindings, 14 baseline bindings, and 19 follow-on artifacts.

See [CHECKS.md](CHECKS.md) for exact commands, failures and retries,
[ROOT_CAUSE_MATRIX.md](ROOT_CAUSE_MATRIX.md) for classification, and
[AUDIT_MANIFEST.json](AUDIT_MANIFEST.json) for hashes and protected-worktree review.
The dirty repository root, consolidation worktree and predecessor evidence are
preserved. All repair work is uncommitted and unpushed. **No scientific disposition
changed.**
