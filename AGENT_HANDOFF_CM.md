## Context

This repo is `C:\Users\brian\Documents\CM_Computation`.

Work completed in this thread focused on:

- porting missing functionality from the local `Correspondence_Matrices` working tree
- wiring the pair-aware CM path into benchmarking
- fixing the remaining Espresso correctness path
- cleaning up the `README.md` / `Readme.md` casing situation

No commits were created in this thread.

## Files Added

- `cm_token.py`
- `cm_lm.py`
- `cm_pair.py`
- `cm_build_pair.py`
- `cm_render.py`

These files did not exist in `CM_Computation` before. They were ported from the local `Correspondence_Matrices` worktree, with duplicate-code cleanup where needed.

## Files Modified

- `cm_bench.py`
- `cm_normalize.py`
- `README.md`
- `Readme.md` is intended to be removed in favor of `README.md`

## What Was Implemented

### 1) Pair-aware benchmark path

`cm_bench.py` now supports:

- `--cm-pair`

Behavior:

- only affects the **baseline CM run**
- does **not** replace hybrid / partial-hybrid / parallel modes
- uses `compile_expr_to_cm_pair(...)` from `cm_build_pair.py`
- records these metrics into raw rows and summary output:
  - `pair_attempts`
  - `pair_collapses`
  - `pairable_ratio`
  - `pair_nodes_total`

Reporting:

- console summary now shows pair metrics only when they are actually present
- HTML report reorders columns to surface pair metrics near the front
- pair metric columns are dropped from HTML sections when all values are null

### 2) Espresso correctness fix

The old Espresso path in `cm_bench.py` had multiple issues:

- it passed a list of on-set indices to `pyeda.truthtable(...)`, but this PyEDA API expects a full output vector / bitstring
- it then tried to convert the PyEDA result to SymPy using `sympify(str(...))`, which breaks on variable names like `x[0]`
- there was also a variable-order mismatch between our TT convention and PyEDA’s truth-table interpretation

The corrected path now:

1. builds the full CM truth table `tt`
2. bit-reverses the **full vector indexing** before feeding PyEDA
3. creates `truthtable(xs, tt_str)`
4. converts via `truthtable2expr(...)`
5. minimizes with `espresso_exprs(...)`
6. evaluates the resulting PyEDA expression directly with `restrict(...)`

This is the current known-good path.

### 3) `cm_normalize.py` optimizations

Ported from local `Correspondence_Matrices`:

- `lift_cm` now uses `np.broadcast_to(...)` instead of `np.repeat(...)` for ambient expansion
- `lift_cm` returns `.copy()` to ensure the final matrix is writable
- `combine_pointwise` now uses in-place `np.bitwise_*` operations

These were validated by smoke tests after integration.

## Verification Already Performed

### Smoke tests

These were run successfully:

```powershell
python cm_bench.py --sizes 4,8 --trials 2 --max-depth 3 --cm-pair --no-dd --no-espresso --print-summary
python cm_bench.py --sizes 4,8 --trials 2 --max-depth 3 --no-dd --print-summary
```

Observed results:

- `CM_OK = OK`
- `Espresso_OK = OK`
- pair metrics appear only in the `--cm-pair` run

### Pair backend equivalence checks

These were run and passed:

1. pairable-only random expressions with `R=['x0']`, `C=['x1']`
2. mixed random expressions on `n=4,6,8`

In both cases:

- `compile_expr_to_cm_pair(...)` matched `compile_expr_to_cm(...)`

## Current Known State / Risks

### Low remaining risk

The pair/token mapping appears behaviorally correct based on the equivalence checks above.

### Deeper-pass candidates

These are the best targets for another agent or a more capable pass:

1. `cm_build_pair.py`
   - currently falls back to `compile_expr_to_cm(...)`
   - not integrated with IR diagnostics / materialization internals
   - possible future work:
     - improve pairability detection
     - integrate with IR diagnostics
     - measure when pair mode is actually beneficial

2. `cm_render.py` / `cm_lm.py`
   - currently utility-only
   - not integrated into benchmarks
   - could use a quick usability review and maybe a simple documented demo path

3. `README.md`
   - casing cleanup is in progress (`README.md` should replace `Readme.md`)
   - the content still contains some legacy formatting glitches from earlier history, for example:
     - split `requirements.txt` lines
     - odd control characters in some examples
   - this was not fully cleaned up in this thread

4. benchmark/report polish
   - pair metrics are visible now, but output formatting could be improved further if desired
   - summary tables are very wide; a future pass could create a condensed mode

## Suggested Next Checks For Another Agent

### Priority 1

- inspect `README.md` and fully normalize the content, not just the filename
- verify raw/summary CSV columns for pair metrics look good on a larger benchmark run
- run a slightly larger Espresso validation sweep, e.g.:

```powershell
python cm_bench.py --sizes 4,8,12 --trials 5 --max-depth 4 --no-dd --print-summary
```

### Priority 2

- inspect whether `cm_build_pair.py` should support diagnostics / materialization-mode parameters
- inspect whether pair mode should have a dedicated timing column distinct from baseline CM, instead of replacing the baseline path when `--cm-pair` is enabled

### Priority 3

- evaluate whether `cm_render.py` / `cm_lm.py` should be documented in `README.md`
- decide whether `cm_pair.py` should remain as a separate helper or be folded into `cm_build_pair.py`

## Useful Files To Review First

- `cm_bench.py`
- `cm_build_pair.py`
- `cm_token.py`
- `cm_normalize.py`
- `README.md`

## Current Git Notes

At the end of this thread, expected relevant git state is:

- `README.md` should be staged as the canonical readme
- `Readme.md` should be staged for deletion
- implementation files are still uncommitted

If another agent starts from here, the first useful command is:

```powershell
git status -sb
```

