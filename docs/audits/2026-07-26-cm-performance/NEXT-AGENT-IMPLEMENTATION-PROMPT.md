# Next-Agent Implementation Prompt

Updated: 2026-07-26

Copy the prompt below into the next implementation thread. It assumes the
current working tree, including the output-budget continuation, is available.

---

You are continuing the Correspondence Matrix performance and resource-safety
work in:

`C:\Users\brian\Documents\CM_Computation`

## Objective

Implement the next coherent package:

1. byte-budgeted caches with retained-byte telemetry and deterministic
   eviction; and
2. bounded remote-worker concurrency with aggregate memory admission,
   backpressure/refusal status, and load tests.

Do not mix unrelated algorithm, CLI-import, corpus, or research changes into
this package. When this package is complete, update the audit documents and
write a ready-to-paste prompt for the following agent covering everything that
still remains.

## Read before changing code

Read these files completely:

1. `AGENTS.md` files that apply to the workspace, if any.
2. `docs/audits/2026-07-26-cm-performance/CM-PERFORMANCE-AUDIT.md`
3. `docs/audits/2026-07-26-cm-performance/CM-BENCHMARK-RESULTS.md`
4. `docs/audits/2026-07-26-cm-performance/CM-OPTIMIZATION-BACKLOG.md`
5. `docs/audits/2026-07-26-cm-performance/FINAL-IMPLEMENTATION-SUMMARY.md`
6. `docs/audits/2026-07-26-cm-performance/OUTPUT-BUDGET-CONTINUATION.md`
7. `cmbench/output_budget.py`
8. The relevant cache/worker implementations:
   - `bitset_backend.py`
   - `cm_ir.py`
   - `cmbench/context.py`
   - `cm_parallel.py`
   - `cm_remote_worker.py`
   - `cm_remote_executor.py`
   - `cm_runpod_protocol.py`
   - `cmbench/config.py`

The worktree was already heavily dirty before the audit. Do not revert,
reformat, commit, push, or attribute unrelated V4 changes to this package.
Start with `git status --short` and preserve all existing changes.

## Current implemented baseline

The current tree includes:

- all three P0 correctness fixes from the audit;
- linear-time complement detection for wide AND/OR compilation;
- thread-local words scratch, eliminating shared concurrent corruption;
- `cmbench.output_budget` with:
  - `OutputStatus`;
  - `OutputBudget`;
  - deterministic output/temporary estimates;
  - typed `OutputBudgetExceeded`;
  - full/reduced/refused decisions;
- representation-aware direct-API default output limits;
- stricter benchmark/remote limits carried through config and protocol;
- typed `ok`, `reduced`, `refused`, and `oom` reporting at relevant workflow
  boundaries;
- dense, packed, reduced, equivalence, remote, and boundary regression tests.

Current verification:

```text
python -m pytest -q
223 passed in 135.56s
```

Scoped code commit:

```text
4be1543 feat(cm): harden evaluation and output admission
188 passed in 109.57s in an isolated Git-index snapshot
```

The direct API permits up to 256 KiB so the supported dense `n=18` parallel
test remains valid. Benchmark and remote defaults remain 64 KiB plus the legacy
`cm_max_full_output_vars=16` guard.

## Required package 1: byte-budgeted caches

Inventory every retained cache and distinguish process-global, run-scoped,
program-scoped, thread-local, and process-pool resources.

At minimum address:

- `_build_bitset_env_cached` in `bitset_backend.py`;
- `_build_words_env_cached` and `_words_const` in `bitset_backend.py`;
- `FlatProgram.bound_cache`;
- per-thread `FlatProgram.word_scratch_local.by_width`;
- `_COMPILED_IR_CACHE` and `_PERSISTENT_IR_CACHE` in `cm_ir.py`;
- `_alignment_plan` or explicitly justify why count-bounding is sufficient;
- `BenchmarkRunContext.truth_table_by_key`, grids, and retained bitset
  environments;
- `_POOL_CACHE` in `cm_parallel.py` (lifecycle telemetry at minimum).

Requirements:

1. Define one reusable, thread-safe byte-LRU policy rather than several
   unrelated eviction implementations.
2. Retain entry caps as secondary protection.
3. Track at least:
   - hits;
   - misses;
   - current entries;
   - estimated retained bytes;
   - maximum bytes;
   - evictions;
   - rejected/uncached oversize entries.
4. State what each size estimate includes and excludes. Python integer/object
   graph estimates may be approximate but must be deterministic and
   conservative enough for admission.
5. Never cache one entry whose estimated size exceeds its cache budget.
6. Evict least-recently-used entries until both byte and count limits hold.
7. Provide explicit clear/reset methods that also reset byte accounting.
8. Do not make cache telemetry mutate result correctness or public artifact
   formats.
9. Ensure concurrent lookups/inserts cannot corrupt LRU/accounting state.
10. Keep configuration defaults conservative and backward compatible where
    practical. Document every default.

Suggested order:

1. Implement and unit-test a small reusable byte-LRU utility.
2. Convert bigint and words environment caches.
3. Bound program-bound templates and thread-local words scratch by bytes.
4. Convert IR caches.
5. Add run-context retained-byte accounting.
6. Add pool lifecycle telemetry; do not invent a byte size for external worker
   processes.

Validation must include:

- exact hit/miss and LRU eviction sequences;
- oversize-entry bypass;
- replacement accounting;
- clear/reset;
- repeated mixed widths;
- concurrent access;
- RSS plateau probe in a fresh subprocess;
- unchanged exact truth digests.

## Required package 2: bounded worker admission

The remote worker uses `ThreadingHTTPServer`. Thread-local scratch fixed data
corruption, but memory now scales with active requests.

Implement:

1. A configurable maximum active evaluation count.
2. A configurable aggregate admitted-memory budget.
3. Request admission using the existing `OutputBudget` estimates plus a clearly
   documented evaluator/cache reserve.
4. A defined policy for busy requests:
   - bounded queue with timeout, or
   - immediate typed refusal.
   Do not silently create unlimited threads.
5. Stable response statuses. Preserve `refused`, distinguish capacity/busy
   refusal from invalid input, and map `MemoryError` to `oom`.
6. Telemetry for:
   - active requests;
   - queued requests, if queueing is used;
   - admitted estimated bytes;
   - peak active requests;
   - peak admitted bytes;
   - capacity refusals;
   - completed and failed requests.
7. Release reservations in `finally` for success, evaluation errors, client
   disconnects, and serialization failures.
8. `/health` should expose safe worker-capacity telemetry without secrets.

Keep the pure admission controller independently unit-testable; do not require
opening sockets for all policy tests.

Validation must include:

- identical and different expressions under concurrency;
- a synchronized load above worker capacity;
- aggregate-memory rejection even when worker slots remain;
- reservation release after exceptions;
- bounded active count and bounded admitted bytes;
- exact result equivalence for admitted requests;
- remote protocol round trips with old fields absent;
- local mock and HTTP worker behavior;
- no recurrence of the shared-scratch corruption test.

Do not deploy or contact RunPod. Use local/mock execution only unless the user
explicitly authorizes external operations.

## Compatibility and review gates

- Preserve existing CSV columns and remote fields; additive fields are allowed.
- Old remote requests missing new fields must receive conservative defaults.
- Do not silently turn exact output into reduced output.
- Do not add unstable wall-time assertions to pytest.
- Run focused tests after each layer.
- Run `python -m pytest -q` before completion.
- Run `git diff --check`, `git status --short`, and `git diff --stat`.
- Report pre-existing failures and dirty files separately.

## Remaining work after this package

Do not lose these backlog items:

1. frozen distinct-expression regression corpus;
2. corpus replay for equivalence, partial-context, family, and
   operator-difference workflows;
3. lazy CLI/workflow/backend imports;
4. prepared-evaluation break-even campaign and guarded dispatcher policy;
5. fast/full/remote/performance test tiers and Windows/Ubuntu CI;
6. explicit `n=0` contract (do not guess; recommend rejecting it unless the
   user chooses public constant AST nodes);
7. tiled/streaming exact-output research;
8. real public workloads and task-matched CUDD/AIG/SAT comparisons;
9. cross-platform and multiple-machine validation.

## Required handoff

At the end:

1. Update the dated audit, backlog, implementation summary, and artifact index.
2. Record exact commands, test counts, and any RSS/load evidence.
3. Create
   `docs/audits/2026-07-26-cm-performance/FOLLOWING-AGENT-PROMPT.md`.
4. That prompt must include:
   - what this package implemented;
   - exact current test/baseline state;
   - all remaining items above;
   - the recommended next coherent package;
   - relevant files and prerequisites;
   - explicit stop points for product/API decisions;
   - an instruction to create another follow-on prompt if work still remains.

Do not claim completion merely because cache counts are bounded. Completion
requires byte accounting, concurrency admission, failure-safe reservation
release, telemetry, exact-output regression coverage, and the full-suite gate.

---
