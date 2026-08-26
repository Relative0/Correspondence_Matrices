# DP-R2 Temporary-Memory Policy Decision Memo

Date: 2026-08-27  
Decision state: **measurement complete; no default changed; policy approval deferred**

## Executive decision

Do not set a production default `max_temporary_bytes` against the current
dense-output estimate. The estimate is described as conservative, but the
bounded diagnostic shows that it is not a conservative Python-allocation upper
bound for dense NumPy materialization. A numeric default applied now would look
like a memory guarantee without providing one.

The recommended path is two-stage:

1. harden and validate representation-specific estimates, including a dense
   DAG/liveness term and fixed allocation overhead; then
2. with Brian's explicit approval, introduce a versioned production policy with
   resolved local/remote numeric limits and legacy compatibility.

Explicit output-byte guards remain useful and unchanged. No output ordering,
exactness, artifact, caller default, or remote protocol behavior was changed by
this campaign.

## Current behavior inventory

| Boundary | Output default | Temporary default | Variable guard | `None` behavior |
|---|---:|---:|---:|---|
| Direct `materialize_cm` / no-reinflate APIs | 256 KiB (`DEFAULT_OUTPUT_BUDGET`) | none | none unless supplied | An explicit `output_budget=None` plus no variable limit disables admission limits |
| `BenchmarkConfig` / `cm_bench.py` CLI | 64 KiB | none | 16 | Per-field `None` is unbounded; config values are propagated to local and remote calls |
| `CMRemoteRequest` / worker | 64 KiB | none | none unless supplied | Missing or JSON `null` temporary limit becomes `None`; worker constructs an `OutputBudget` with those values |
| Pair builder public entry | 256 KiB | none | none | The public call checks once; internal fallbacks pass `None` to avoid duplicate checks |

Relevant paths are `cmbench/output_budget.py`, `cm_ir.py`, `cm_build_pair.py`,
`cmbench/config.py`, `cm_bench.py`, `cm_runpod_protocol.py`,
`cm_remote_executor.py`, `cm_remote_worker.py`, and
`tests/test_output_budget.py`.

The typed vocabulary already distinguishes `ok`, `reduced`, `refused`,
`timeout`, `oom`, and `unvalidated`. `OutputBudgetExceeded` is mapped to
`refused` by the remote worker. Existing tests prove output-limit and tiny
temporary-limit refusal before the large artifact is materialized, reduced
output status, remote round-trip, and exact-result behavior.

## Estimator audit and new measurement

`estimate_explicit_output` currently computes:

- packed output: `ceil(2^k / 8)` output bytes and
  `output_bytes * (operation_slots + k + 2)` temporary bytes;
- dense Boolean/uint8 output: `2^k` output bytes and exactly
  `2 * output_bytes` temporary bytes.

Although `materialize_cm` passes structural CM node count as
`operation_slots`, the dense branch ignores it. The NumPy materializer memoizes
node arrays, aligns/broadcasts operands, creates ufunc results, and copies the
final output, so a two-buffer estimate cannot generally bound the path.

The reproducible diagnostic is `scripts/cm_output_budget_policy_probe.py`; raw
results are in `DP-R2-OUTPUT-BUDGET-PROBE.json`. It used Python 3.13.5 and the
repository virtual environment, forced dense NumPy materialization, ran seven
repetitions per case, and measured Python `tracemalloc` peak. It is explicitly
not an RSS or native-allocator upper bound.

| `k` | CM nodes | Output bytes | Current temporary estimate | Median traced peak | Peak / estimate |
|---:|---:|---:|---:|---:|---:|
| 8 | 40 | 256 | 512 | 19,830 | 38.73x |
| 10 | 52 | 1,024 | 2,048 | 29,466 | 14.39x |
| 12 | 64 | 4,096 | 8,192 | 49,646 | 6.06x |
| 14 | 76 | 16,384 | 32,768 | 115,170 | 3.51x |

The first measured repetition was generally higher, reinforcing the need to
separate cold allocator behavior. In all four cases a limit one byte below the
current estimate produced typed refusal before materialization. That validates
the admission control sequence, not the accuracy of the admitted estimate.

## Policy options

### A. Set a numeric temporary default now

Rejected. This would newly refuse some callers while the admission quantity is
not a conservative bound. It creates false confidence and makes compatibility
cost impossible to estimate honestly.

### B. Retain no temporary default indefinitely

Safe for compatibility but incomplete for productization. Output-size guards
do not bound all evaluator intermediates, and catching `MemoryError` after an
allocation attempt is not a fail-closed resource policy.

### C. Harden the estimate, then adopt a versioned profile

Recommended. A conservative first implementation can account for structural
operation slots, maximum full-width live buffers, per-array/fixed overhead,
final copying, and representation-specific Python/native storage. It may begin
with a deliberately conservative bound and be reduced only after held-out RSS
and allocator measurements show that it is safe. Packed bigint and word-packed
paths need separate validation; the dense probe must not be generalized to
them.

## Proposed post-validation policy requiring approval

The proposed profile is `production-balanced-v1`:

| Surface | Maximum explicit output | Maximum estimated temporary memory | Variable guard |
|---|---:|---:|---:|
| Benchmark and new remote requests | 64 KiB | 16 MiB | 16 |
| Direct public materializers | 256 KiB | 64 MiB | preserve current representation-aware output behavior |

These are admission limits, not a process RSS quota. Larger work remains
possible only through an explicit caller-supplied override, with the selected
limits recorded in diagnostics. Reduced output remains opt-in. A refusal must
occur before material allocation and return no partial artifact.

For remote compatibility, new request builders should include both a policy ID
and resolved numeric values. Requests without a policy ID remain legacy and
retain their current missing/`null` semantics. This avoids silently changing
old serialized requests. Local and new remote calls must resolve to identical
limits and typed outcomes.

**Approval boundary:** Brian must explicitly approve both the two numeric
profiles above and the fact that previously admitted calls may become typed
refusals. This campaign does not request or assume that approval.

## Staged implementation and validation plan

1. Add estimator-only tests for dense, packed bigint, and word-packed
   representations across `k`, structural node count, operator mix, and fixed
   contexts. Measure cold/warm `tracemalloc`, process RSS/high-water mark, and
   native allocations where the platform exposes them.
2. Replace the dense two-buffer rule with a documented conservative model.
   Retain an estimator version in diagnostics and raw artifacts. Do not change
   defaults in this step.
3. Prove refusal-before-allocation for each materializer and conversion path,
   including pair, partial/reduced, equivalence, parallel, and serialization
   boundaries. Verify no partial output or cache insertion on refusal.
4. Add a remote protocol policy ID, resolved-limit echo, and legacy request
   fixtures. Validate local/mock/worker parity for `ok`, `reduced`, and
   `refused`.
5. Replay accepted corpora plus a held-out structural-stress slice to count
   newly refused calls and false admissions under the candidate profiles.
6. Present those compatibility results for approval. Only then change defaults
   in one reviewable commit and rerun focused/full correctness plus memory
   probes.

## Limitations

- `tracemalloc` is diagnostic evidence, not a total-process memory bound.
- The four measured formulas establish that the current dense estimate is not
  conservative; they do not calibrate a universal multiplier.
- No real caller/workload trace exists in the repository, so the compatibility
  rate of any new production profile is currently unknown.
- Operating-system or container memory limits remain the final protection
  against allocator behavior outside the model.
