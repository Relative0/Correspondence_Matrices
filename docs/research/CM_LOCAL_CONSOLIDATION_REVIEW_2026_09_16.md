# Local CM consolidation review — 2026-09-16

## Disposition

This isolated worktree starts at the current integrated baseline:

`main == origin/main == e35f352a2036db403f5e28ecca2f61550d1db0c7`

It contains two deliberately selected, still-uncommitted change groups:

1. The maintained Windows pytest profile copied byte-for-byte from
   `tmp/cm-consolidation-20260914` (one tracked workflow edit and 15 new files).
2. Five compiler/test files initially copied byte-for-byte from the protected
   root worktree, then reviewed as a semantic delta from current `main`. The
   consolidation contains one targeted legacy-metrics compatibility correction
   described below; the protected source remains unchanged.

No root `.gitattributes`, `.gitignore`, publication workflow, website source,
generated website output, paper-workbench file, audit package, cache, or build
output was copied. No commit or push has been made.

## Compiler review

Current `main` already contains the reviewed signed-pair implementation from
`4b47c6d3`. The retained delta extends that implementation rather than replacing
it with the older pre-integration source:

- direct packed-expression evaluation accepts explicit fixed variables and
  refuses missing live/fixed inputs instead of silently returning a false value;
- the token API exposes one validated representation-neutral bit query;
- row and column layouts reject duplicate or overlapping axes;
- pair compilation distinguishes pure structural, hybrid local-retabulation,
  full-root retabulation, and ordinary fallback outcomes;
- the former `structural` spelling remains a compatibility alias for the old
  hybrid behavior;
- diagnostics separate unfolded AST occurrences, identity-DAG nodes, height,
  compiler calls, negation scans, and root provenance; and
- focused tests cover fixed variables, missing values, strategy compatibility,
  axis validation, repeated-variable refusal, provenance, and metrics.

The existing benchmark consumer reads only the retained numeric legacy fields
(`pair_attempts`, `pair_collapses`, `pairable_ratio`, and `nodes_total`). Review
found and repaired an experimental compatibility defect: `nodes_total` had been
changed to AST occurrences even though `pairable_ratio` retained compiler calls
as its denominator. Both legacy fields now preserve their historical compiler-call
meaning, while `ast_occurrences` and `unique_object_nodes` are additive diagnostics.
The new string-valued provenance fields are also additive. The default spelling changes from
`structural` to `hybrid`, but the execution behavior is the same because the old
`structural` path already allowed local two-variable retabulation.

The review found no stale configuration or website dependency in these five
files. Exact source SHA-256 values before extraction were:

```text
d187c4301231a3a6b2fd1c9bc19fdf5e0bbfadbc486724841a3027b8a0c3f4a5  bitset_backend.py
9a0c14cb412fda4ebd039f9e18c5bdd0df4bbc9f9db88983157617226b5791c3  cm_build_pair.py
1ec0d6a18444a4ed4fca9deedb77eb655dc56e406c59429c589e32c8a967f403  cm_token.py
917dee55c365fa77483f08b1a412b3ca5f3dc8da67a8f30436ad4780b96f73b8  tests/test_bitset_backend.py
e71e1a6fdb57a3ff8653a17462e523aa4918121b74f7e638c25fc72261e8f235  tests/test_cm_pair_alignment.py
```

## Verification

- Windows profile inventory verifier: passed; 76 historical replay tests and
  nine optional/refusal modules remain exactly bound.
- Windows profile focused tests: 4 passed.
- Full `windows-supported` collection against the current `main` tree: passed.
- Compiler/backend/output-budget/measurement/partial-context affected suites:
  146 passed and 102 subtests passed; the same selection passed again after the
  compatibility correction (6.94 seconds in the final run).
- `git diff --check`: passed for every tracked file in this consolidation.

The first profile-test invocation failed only because the new worktree lacked a
`tmp/` parent for `--basetemp`. Creating that workspace-local directory and
repeating the same test selection passed all four tests. This reproduces the
environmental temp-path constraint already documented by the profile audit.

## Research baseline

The local branch `codex/cm-research-baseline-20260916` points exactly to the clean
integrated commit `e35f352a2036db403f5e28ecca2f61550d1db0c7`. It intentionally
excludes every uncommitted change in this consolidation. A Codex-managed worktree
created from that branch should start detached at this commit; the task must still
verify its HEAD and status before research.
