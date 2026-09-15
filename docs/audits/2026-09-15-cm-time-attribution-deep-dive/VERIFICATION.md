# Final verification

## Implementation and diagnostic checks

No production code, routing, default or tracked baseline file was changed.
All additions are in this audit directory. The initial isolated checkout was
clean and detached at `e334de594262059cc18cf37eaab56b0f79e94843`.

The existing project virtual environment was used with `python -B` and pytest
cache output disabled. Two focused test invocations completed:

1. **90 passed in 13.62 seconds**: audit tracer, frozen-record and task-harness
   tests plus project CSE, prepared evaluation, expression-family,
   sharing-aware flattening and foreign-node interning tests.
2. **7 passed in 0.74 seconds**: saved-summary reproducibility and cross-artifact
   conservation, input/output equivalence and unknown/contract handling tests.

The tests cover nested/recursive exclusive spans; restoration on exceptions;
staticmethod and imported evaluator aliases; preserving the public
diagnostics-off path and evaluation defaults; same-executor mask/basis behavior;
complete outputs; immutable source binding; refusing evidence overwrite; all
declared cells surviving synthesis; own-denominator phase conservation; and
retaining nulls for genuinely unresolved quantities. No broad test failure was
hidden: the repository-wide suite was not run because production code was not
modified. Existing unrelated pytest-profile work was not used or changed.

Commands (paths relative to this isolated worktree):

```text
python -B -m pytest docs/audits/2026-09-15-cm-time-attribution-deep-dive/test_ladder_diagnostics.py docs/audits/2026-09-15-cm-time-attribution-deep-dive/test_frozen_records.py docs/audits/2026-09-15-cm-time-attribution-deep-dive/test_task_diagnostics.py tests/test_bitset_cse.py tests/test_prepared_flat_evaluation.py tests/test_expression_family_bench.py tests/test_share_aware_flatten.py tests/test_foreign_node_interning.py -q -p no:cacheprovider
python -B -m pytest docs/audits/2026-09-15-cm-time-attribution-deep-dive/test_profile_integrity.py docs/audits/2026-09-15-cm-time-attribution-deep-dive/test_ladder_summary.py -q -p no:cacheprovider
python -B docs/audits/2026-09-15-cm-time-attribution-deep-dive/recompute_frozen_evidence.py --verify
python -B docs/audits/2026-09-15-cm-time-attribution-deep-dive/make_manifest.py --verify
```

## Evidence and run accounting

- Primary corrected ladder: **137/137 exact complete outputs**, seven whole-call
  repetitions and separate phase/profile/memory passes; suite 7.18 seconds.
- Task/family suite: **70/70 exact cells**, five whole-call repetitions and
  separate phase/profile/memory passes; suite 44.12 seconds.
- Earlier ladder smoke and run001 remain preserved, explicitly superseded by
  run002 after a diagnostic alias/metadata defect. Their measurements are not
  used in synthesis. No predecessor or earlier raw diagnostic file was rewritten.
- Frozen-evidence verification recomputed **186 SymPy rows and all nine gate
  ratios**, rehashed **45 source files**, and matched **26 existing predecessor
  bindings**, with zero mismatches. The verifier does not write evidence.
- The historical batch helper and disclosed input file were hash-bound and
  reverified. Their source origin is distinct from the exact-commit baseline.
- Profile/ledger synthesis conserves phase-pass wall time. CPU zeros remain
  visible. No new held-out inputs, optional installs, external spending,
  network service, or cloud resource was used.
- All runs stayed well within the predeclared time/size bounds. Structural and
  output caps and supervisory/cooperative time bounds are documented; no
  OS-enforced memory ceiling is claimed.

## Git and protected worktrees

Final `git status --short` in the isolated worktree lists only:

```text
?? docs/audits/2026-09-15-cm-time-attribution-deep-dive/
```

`git diff --stat` is empty; `git diff --check` passes. Both isolated HEAD and
the existing `main` ref remain the requested commit. The task required Git to
register the new worktree; sandbox access was granted for that metadata write.
No working files in either protected worktree were edited.

The original root retains its same 34 tracked dirty paths; the consolidation
worktree retains its tracked workflow edit. A synthesis-time read-only
checkpoint and final verification show all 35 dirty tracked-file hashes and
both tracked-status lists unchanged. The initial pre-creation status is also
in the task tool log; the checkpoint is not misrepresented as an initial
before-byte snapshot. Untracked unrelated pytest-profile files were not edited.
See `PRESERVATION_CHECKPOINT.json` and `WORKTREE_REVIEW.json`.

The final manifest hashes every new diagnostic artifact except itself (a
self-hash would be circular), records baseline code/fixture hashes and exact
predecessor references, and supports a read-only recheck. Relative links in
the report and ledger are checked against their actual artifacts.

The evidence was sealed before version-control mutation. The user subsequently
authorized one commit containing only this additive audit directory. Nothing
was pushed. **No scientific disposition changed.**
