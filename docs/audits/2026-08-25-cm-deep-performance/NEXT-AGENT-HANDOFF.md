# Next-Agent Handoff

Use this only if Brian chooses to continue a deferred workstream. The 2026-08-25 audit itself is complete.

## Exact audited state

- Repository: `C:\Users\brian\Documents\CM_Computation`
- Starting branch / HEAD: `main` / `1ba3a7312fa99439b57ddb3b4433ead7e86b2c74`
- No commit, stage, push, dependency installation, or cloud job was performed.
- The pre-audit worktree was already heavily dirty. Its exact original `git status --short`, dependency versions, process affinity, source hashes, and corpus hashes are in `baseline_smoke_environment.json`.
- Audit-owned production/test edits: `cm_ir.py`, `tests/test_build_memo.py`.
- Audit-owned tooling: `scripts/cm_prepare_memo_ablation.py`.
- Audit-owned evidence/documentation: `docs/audits/2026-08-25-cm-deep-performance/`.
- All other modified/untracked files are pre-existing and must be preserved exactly unless Brian gives a separate instruction.

## Completed validation and results

- Removed the redundant id-keyed memo only from default sharing-aware builds; legacy non-sharing-aware builds keep it.
- Paired BX1+B2: 272 rows, 11 repetitions, candidate/baseline geomean `0.960113`, cluster interval `[0.950987, 0.972132]`, 0 exact mismatches.
- Paired EPFL reused validation: 129 roots, 5 repetitions in bounded chunks, geomean `0.976840`, circuit-cluster interval `[0.954748, 0.999534]`, 0 exact mismatches.
- `tracemalloc` smoke peak ratio: `0.882005`; explicit-arm reproduction `0.882397`.
- Focused tests: `33 passed, 4 subtests passed in 4.34s`.
- Full suite: `359 passed, 4 subtests passed in 204.62s`.
- Selector: no change. Keep `WORDS_AUTO_MIN_VARS=16` as conservative current policy; it is not a universal crossover.
- Cache/family/context, native/JIT, algebraic, and parallel candidates were evaluated and deferred/rejected according to the audit/backlog.

## Unresolved hypotheses

1. Compact builder-local canonical ordering/ranks may reduce deep-key comparison and interning/canonicalization allocation without changing public `CMNode.key` semantics.
2. Default temporary-memory budgets need a product/API decision.
3. Byte/cost-aware cache and incremental pass queries need real access/edit traces.
4. A feature selector needs production volume at `k=13..15`, a newly frozen untouched corpus, and cross-machine validation.
5. A fused native/JIT `uint64` kernel needs a real repeated batch and dependency approval.

## Approvals required

- Brian’s explicit approval before installing Numba/LLVM, building new native dependencies, using paid/cloud compute, changing default API refusal budgets, committing, or pushing.
- No approval is needed for read-only analysis or a local compact-key prototype confined to new audit outputs, provided unrelated dirty files are preserved.

## Suggested next commands

```powershell
Set-Location C:\Users\brian\Documents\CM_Computation
git status --short
git diff -- cm_ir.py tests/test_build_memo.py scripts/cm_prepare_memo_ablation.py

# Reproduce the current explicit-arm quick check with a new prefix.
& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite smoke --corpora bx1,b2,epfl --repetitions 11 `
  --output-prefix docs\audits\YYYY-MM-DD-cm-followup\memo_ablation_smoke

# Before a compact-ordering prototype, run the focused exactness tests.
python -m pytest -q tests\test_build_memo.py tests\test_share_aware_flatten.py `
  tests\test_persistent_path_consistency.py tests\test_cm_ir_cost.py `
  --basetemp docs\audits\YYYY-MM-DD-cm-followup\.pytest_tmp_before
```

Use a new dated directory/prefix; every evidence writer must refuse overwrite. For compact-ordering work, save a pre-change source snapshot and pair the prototype against the current accepted one-memo production path on identical formulas.

## Files and claims to preserve

Preserve all pre-existing README/website/correction/audit/benchmark work and every source snapshot/raw artifact. Do not modify accepted historical data.

Do not resurrect these claims:

- no CM speed claim from the `0.9998` CM/CSE-flat residual;
- no claim that B2/EPFL are untouched held-out evidence;
- no universal `k=13`, `14`, `15`, or `16` crossover theorem;
- no removal of the `2^k` complete-output lower bound;
- no quotient-as-XOR comparison;
- no blended CUDD build/restrict/extract timing;
- no formal global semantic canonicality from current hashes/keys;
- no family/context/cache dominance over strongest incumbents from existing synthetic experiments.

## Copy-paste continuation prompt

```text
Continue the Correspondence Matrix performance work in
C:\Users\brian\Documents\CM_Computation from main at audited HEAD
1ba3a7312fa99439b57ddb3b4433ead7e86b2c74. Read the complete 2026-08-25
audit package under docs/audits/2026-08-25-cm-deep-performance first,
especially CM-DEEP-PERFORMANCE-AUDIT.md, CM-BENCHMARK-RESULTS.md,
CM-OPTIMIZATION-BACKLOG.md, and baseline_smoke_environment.json.

The worktree contains extensive pre-existing README, website, correction,
benchmark, audit, and generated work. Preserve it exactly. The 2026-08-25 audit
owns only cm_ir.py, tests/test_build_memo.py,
scripts/cm_prepare_memo_ablation.py, and its dated audit directory. Do not
stage, commit, push, install dependencies, use cloud compute, read secrets, or
change API budget defaults without Brian's explicit approval.

The accepted change removed the redundant identity memo on the sharing-aware
builder path. It produced candidate/baseline compile ratios 0.960113 on 272
BX1+B2 rows and 0.976840 on 129 reused-EPFL roots, about 11.8% lower traced
compile peak, zero canonical/output mismatches, and a full result of 359 passed
plus 4 subtests. Preserve the legacy identity memo when
share_aware_flatten=False.

Next, prototype only DP-R1: a builder-local compact canonical ordering/rank that
reduces deep CMNode.key comparison without changing public CMNode.key, child
order, structural/persistent digests, foreign adoption, exact output, or cache
identity. Save the pre-change result, use one coherent edit, pair timing per
formula with alternating order, validate BX1 plus reused B2/EPFL and a
high-sharing B3 slice, measure allocations, use an exact O(s) ordered DAG
signature, and write only to a new dated refuse-overwrite directory. Reject the
prototype if the effect is noise, high-sharing tails worsen, or any canonical
or packed output differs.

Keep WORDS_AUTO_MIN_VARS=16; do not retune a scalar selector. Do not claim B2 or
EPFL are untouched held out, do not optimize the CM/CSE-flat residual, do not
equate quotient with XOR, do not blend CUDD artifacts, and do not claim global
semantic canonicality or a shortcut around complete-output Omega(2^k/w).
```
