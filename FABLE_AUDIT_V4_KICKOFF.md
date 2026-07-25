# Kickoff — Audit V4: Adversarial Verification of the Latent Fixes and Honest CM/Bitset/CUDD Comparison

You are joining the **Correspondence Matrices (CM)** project at:

`C:\Users\brian\Documents\CM_Computation`

Project contact: **Brian Theory (Droncheff)**.

This is an independent audit, not an implementation campaign. Treat every prior report,
commit message, CSV, chart, and handoff as a claim to reproduce. Do not infer correctness
from the existing 159-test suite or from agreement between two paths that share code.

## 0. Repository state expected at handoff

At preparation time (2026-07-24):

- `main` is at `6419b21`.
- `origin/main` is at `5dd6ec7`; local `main` is five commits ahead.
- The primary worktree and the CUDD branch worktree are clean.
- System `python -m pytest -q` reports exactly **159 passed**.
- No Audit V4 report or `v4audit` artifact exists yet.

Verify all of this yourself before accepting it:

```powershell
git status --short --branch
git log --oneline --decorate -n 30
git branch -a -vv
git reflog --all --date=iso -n 80
python --version
python -m pytest -q
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import numpy; print(numpy.__version__)"
```

Expected interpreter split:

- tests: system Python 3.10.11;
- benchmarks: `.\.venv\Scripts\python.exe`, Python 3.13.5 with numpy 2.3.2.

If the commit IDs or collection count differ, record the difference before proceeding.
Never read or print `.env.runpod`, `.env.runpod.local`, token caches, or credentials.

## 1. Chain under review

The relevant history is:

1. Fable campaign through `7bb0566`;
2. Audit V3: `ad04dcc`, `5aeea36`, `1a3adda`;
3. independent review: `39f3313`;
4. CUDD branch work: `085c0ab`, `64358f7`;
5. corrected CUDD merge: `5dd6ec7`;
6. latent fixes:
   - `cc52f43` — symmetric engines in partial/family Bitset controls;
   - `f80a1cd` — remote words provenance;
   - `96294ac` — reject unknown opcodes;
   - `1cf4bcf` — skip unused bigint environment construction;
   - `6419b21` — latent-fix report and session-chain record.

Review the actual patches, including the merge resolution:

```powershell
git log --graph --oneline --decorate 7bb0566..HEAD
git log --stat 7bb0566..HEAD
git show 085c0ab
git show 64358f7
git show 5dd6ec7
git show cc52f43
git show f80a1cd
git show 96294ac
git show 1cf4bcf
git show 6419b21
git diff --stat origin/main..HEAD
```

Do not assume the five local commits need merging: they are already direct commits on
`main`. At preparation time they need only a user-authorized push. Do not push, commit,
deploy, start/stop a pod, or make another external write without Brian's explicit approval.

## 2. Read first, in this order

### Audit and state documents

1. `CM_AUDIT_V3_INDEPENDENT_REVIEW_2026-07-23.md`
2. `CM_AUDIT_V3_2026-07-23.md`
3. `CM_LATENT_FIXES_2026-07-23.md`
4. `CM_SESSION_2026-07-23_AUDIT_V3_STATE_AND_FINDINGS.md`
5. `CM_SESSION_2026-07-22_STATE_AND_FINDINGS.md`
6. `FABLE_AUDIT_V3_KICKOFF.md`
7. `FABLE_CUDD_COMPARISON_KICKOFF.md`
8. `CUDD_WSL_install_and_benchmark_report.md`
9. `deliverables_n22_24\CM_FABLE_BENCHMARKS_2026-07-21.md`, especially §7e
10. `deliverables_n22_24\CM_ARCHITECTURE_AND_AUDIT.md`

Prior audit reports are historical records. **Do not edit them.** Corrections belong in the
new V4 report.

### Public pages

- `deliverables_n22_24\cm_head_to_head_explained.html`
- `deliverables_n22_24\cm_benchmark_charts.html`

### Core implementation

- `cm_bench.py`
- `bitset_backend.py`
- `cm_ir.py`
- `cmbench\config.py`
- `cmbench\backends\robdd_dd.py`
- `cmbench\results\`
- `cmbench\reporting\`
- `cm_runpod_protocol.py`
- `cm_remote_executor.py`
- `cm_remote_worker.py`
- `cm_runpod_client.py`
- `cm_runpod_config.py`
- `scripts\cudd_env_check.py`

Trace the full path from CLI configuration through local and remote execution. In
particular, verify engine selection (`words > flat > recursive`), output scope, timing
boundaries, CUDD backend identity, variable-order policy, correctness mode, and summary
aggregation.

## 3. Existing evidence to reproduce

### Independent-review scripts and outputs

Under `deliverables_n22_24\`:

- `independent_review_f1_words_extra_2026_07_23.py`
- `independent_review_f2_depth6_2026_07_23.py`
- `independent_review_f3_f5gen_2026_07_23.py`
- `independent_review_f4_profile_2026_07_23.py`
- `independent_review_f5_support_2026_07_23.py`
- `independent_review_f6_chart_check_2026_07_23.py`
- corresponding `CM_independent_review_*.csv` files.

### Audit-V3 scripts and outputs

Under `deliverables_n22_24\`:

- `v3audit_f1_words_adversarial_2026_07_23.py`
- `v3audit_f2_threshold_paired_2026_07_23.py`
- `v3audit_f3_n24_seeds_2026_07_23.py`
- `v3audit_f4_binding_profile_2026_07_23.py`
- `v3audit_f5_beyondguard_local_2026_07_23.py`
- `v3audit_f5_corrected_all_live_2026_07_23.py`
- `v3audit_f5_family_structure_2026_07_23.py`
- `v3audit_f6_build_chart_trace_2026_07_23.py`
- corresponding `CM_V3AUDIT_*.csv` and `CM_v3audit_*.csv` files.

### Latent-fix evidence

Under `deliverables_n22_24\`:

- `latentfix1_partial_family_engine_parity_2026_07_23.py`
- `latentfix2_remote_words_provenance_2026_07_23.py`
- `latentfix3_opcode_guard_2026_07_23.py`
- corresponding `CM_latentfix*.csv` files.

### CUDD evidence

Under `deliverables_n22_24\`:

- `fable_cudd_wrapper32_campaign_2026_07_23.py`
- `CM_FABLE_cudd_wrapper32_raw.csv`
- `CM_FABLE_cudd_wrapper32_summary.csv`
- `CM_FABLE_cudd_matched_headline_runpod_{raw,summary}.csv`
- `CM_FABLE_autoref_matched_headline_runpod_{raw,summary}.csv`
- `CM_FABLE_wrapper_stats300_t16_{raw,summary}.csv`
- `CM_FABLE_extended_n32_{raw,summary}.csv`

The 2,700-row wrapper campaign claims 300 expressions at each even `n=16..32`, seed
`9_100_000 + 10_000*n + trial`, depth 4, threshold 16, complete packed equality for
CM versus Bitset, and sampled correctness for CUDD. It times CM/Bitset reduced flat output
but CUDD symbolic construction. It grants CUDD best-of-10 variable orders. Those are
different operations and different optimization policies; do not call the existing gray
CUDD chart series a direct speed contest.

## 4. Audit task A — independently review the four completed latent fixes

The old V4 prompt asked whether findings 1, 2, 3, and 5 should be fixed. They have now been
fixed. Review the fixes rather than proposing them again.

### A1. Partial/family comparator symmetry (`cc52f43`)

Verify:

- partial and family CM and Bitset controls select the same engine;
- precedence is words, then flat, then recursive;
- full-recompute remains full-scope and restricted remains restricted-scope;
- row fields truthfully identify `raw_ast_words`, `raw_ast_flat`, or
  `raw_ast_recursive`;
- flat/words complete packed outputs equal the previous recursive controls on an
  independently generated fuzz corpus spanning at least `n=8..18`;
- no published result used the formerly asymmetric paths.

Reproduce both ordinary CLI and partial/family end-to-end equality flags with and without
`--cm-words-eval`.

### A2. Remote words provenance (`f80a1cd`)

Trace:

`cm_bench.py` → `build_remote_request` → `CMRemoteRequest` serialization →
`cm_remote_worker.execute_cm_request` → response diagnostics →
`_check_remote_words_provenance`.

Using `--cm-runpod-local-mock`, prove words on/off survives the round trip, packed output is
equal to an independent local reference, and a words response without affirmative
`remote_words_eval` is rejected. Check backward compatibility of non-words requests.

Do not use a live pod merely to repeat what the local mock can establish. If a live deployed
worker is old, the client must fail honestly rather than record a false words claim.

### A3. Unknown opcode rejection (`96294ac`)

Independently hand-build `FlatProgram` values:

- prove all six known binary opcodes are bit-identical to a separate semantic oracle;
- prove unknown opcodes raise in `eval_cm_node_flat`, `eval_expr_flat_bitset`, and
  `_eval_words`;
- inspect `_compute_word_plan`, bound/prebound copies, and other live library loops for
  another catch-all-as-EQV path;
- leave historical copies under `deliverables_n22_24\` unchanged.

Repeat the paired/interleaved hot-loop check for at least five rounds and report the raw
timings without claiming precision beyond the data.

### A4. Unused environment construction (`1cf4bcf`)

Prove:

- the recursive path still constructs and uses its bigint environment;
- flat and words paths do not construct an unused bigint environment;
- construction remains outside every reported timing window;
- packed output and schema remain unchanged.

### A5. Finding 4 remains historical prose

Confirm the n=28 trial-1 constant in
`CM_V3AUDIT_F5_family_structure_raw.csv`. Do not edit Audit V3 to add it. Record whether the
existing later reports describe the omission accurately.

## 5. Audit task B — review the Independent Review and CUDD merge

### B1. Independent Review

- Re-run its F5 packed-cofactor and own-BDD support checks.
- Spot-check with a third independently implemented method.
- Inspect the BDD recursion and cofactor indexing rather than accepting agreement alone.
- Check the corrected-generator liveness proof for negation placement, odd-node
  carry-through, constants, and non-constant premises.
- Recalculate the F3 bootstrap, F4 profile split, and depth-6 threshold comparison from raw
  data.
- Replace the F6 script's hand-transcribed arrays with parsing or direct extraction from the
  current HTML for the audit check; confirm the current post-merge pages.

### B2. CUDD backend and data integrity

- Verify `--robdd-dd-backend cudd` cannot silently fall back to `dd.autoref`.
- Verify every existing CUDD raw row's backend identity, status, and correctness fields.
- Reconstruct summary medians and ratios directly from raw CSVs.
- Reproduce seed/expression parity against the threshold-16 wrapper corpus.
- Confirm the matched-headline run used threshold 7 and explain why it is not the primary
  current comparison.
- Confirm the wrapper campaign used `flat_eval=True`, not the newer words engine.
- Audit best-of-k implementation: what is timed, how orders are generated, and whether
  order-search cost is excluded.
- Verify the CUDD correctness sample count and what each sample proves.

### B3. Merge fidelity and public pages

For merge `5dd6ec7`:

- ensure the retracted all-live frontier did not return;
- ensure Audit V3's corrected CM/Bitset arrays and correction notes survived;
- match every CUDD chart value to its source CSV and stated rounding;
- ensure every occurrence says CUDD is symbolic-build time, not packed-output time;
- check legends, tooltips, table headings, prose, and both themes;
- render both pages and inspect them visually.

Use a browser or screenshot tooling if available. Store any new images with `v4audit` in
their names; never overwrite the existing V3 images.

## 6. Audit task C — produce honest n=20..32 comparisons

The main objective is not one blended leaderboard. Produce three separately labeled
comparisons because the methods return different artifacts.

### C1. One environment and one immutable corpus

Use the same Linux/RunPod environment for primary CM, Bitset, and CUDD timings. Run all
three methods in the same process/container where possible. Record:

- CPU model and allocated CPU count;
- RAM;
- OS/container image;
- Python, numpy, `dd`, and CUDD versions;
- Git commit;
- exact command;
- warmup policy;
- process/thread-affinity policy if controlled.

Create and commit a serialized expression corpus before interpreting timings. It must
include even `n=20,22,24,26,28,30,32`, stable IDs/hashes, seeds, expression structure,
actual support/live variables, node/leaf/operator counts, and generator parameters.
CUDD, CM, and Bitset must consume the exact same serialized formulas.

Stratify, do not pool away structure:

1. the existing sparse depth-4 distribution;
2. controlled actual-support bands where practical, such as `live_k` 6–8, 9–12, 13–16,
   and >16;
3. variable-forcing/all-live or adversarial formulas where memory permits.

Nominal `n=32` with `live_k=6` must never be described as a 32-live-variable truth table.
Record refusals, timeouts, and OOM-risk skips explicitly. Do not calculate a CM median over
survivors while silently excluding the same formulas from competitor results.

### C2. Comparison 1 — equivalent packed truth-function evaluation

This is the primary **CM versus Bitset** speed comparison.

- CM gets its fastest verified engine: words where applicable, otherwise flat, otherwise
  recursive.
- Bitset gets the same engine technology and exact same output scope.
- Separate compile/setup time from cached execution.
- Compare full recompute to full recompute and restricted scope to restricted scope.
- Verify complete packed-bit equality, not samples, whenever an explicit result is
  materialized.
- Use paired, interleaved order with at least five timing rounds; report median plus a
  dispersion measure and raw paired observations.

CUDD may enter this table only when it extracts/materializes the exact same truth result
over the exact same variables. Report CUDD build and extraction separately and combined.
If extraction is infeasible at large `live_k`, state `infeasible/not run`; do not substitute
symbolic build time.

### C3. Comparison 2 — symbolic representation construction

Compare tasks with truthful outputs:

- CM expression compilation/interned DAG/flat-program construction;
- CUDD expression-to-BDD construction;
- Bitset/FlatProgram preparation where a meaningful preparation phase exists.

Report representation sizes with clearly defined, method-specific units. For CUDD report:

- fixed/natural expression order as the neutral primary result;
- best-of-k as a separate optimized result;
- dynamic reordering separately;
- order-search/reordering time, including both excluded and all-in totals.

Do not compare CUDD best-of-10 build against a single fixed CM/Bitset run without displaying
the asymmetry.

### C4. Comparison 3 — equivalent downstream workloads

Use already-built representations and compare:

- single assignment queries;
- batches of assignment queries;
- restriction/cofactoring with identical fixed variables;
- repeated evaluation;
- equivalence or XOR-to-false queries where supported;
- full extraction only where feasible.

Measure build, query, extraction, and total end-to-end time separately. Give CUDD workloads
where BDDs are expected to excel equal prominence. Verify every answer independently.

### C5. Correctness bar

- Explicit packed outputs: complete equality against an independently written semantic
  oracle where feasible.
- At sizes where full enumeration is infeasible: deterministic sampled assignments plus
  algebraic/metamorphic checks, with sample count, seed, projection method, and mismatch
  count recorded.
- CUDD backend identity must be affirmative on every CUDD row.
- A shared implementation is not an independent oracle.
- Any mismatch stops headline timing interpretation until explained.

### C6. Interpretation required

Answer separately:

1. Which CM engine is fastest in each actual-`live_k` regime?
2. When does CM cached execution beat, match, or trail the symmetric Bitset control?
3. When does CUDD build the best symbolic representation fastest?
4. When CUDD must return the same packed output, what does extraction cost?
5. How much of apparent `n=20..32` scaling is nominal `n`, actual `live_k`, expression
   structure, or variable ordering?
6. Which negative results or infeasible regimes bound each method?

The current provisional headline to challenge is:

> On shallow, sparse formulas through nominal n=32, optimized CM is approximately at
> Bitset parity and sometimes modestly faster. CUDD builds compact symbolic
> representations quickly, but its existing build timing is a different operation and
> does not establish a direct three-way winner.

Replace it only if the audited evidence warrants doing so.

## 7. Audit task D — hunt for additional issues

At minimum inspect:

- words environment/cache behavior under `--cm-parallel`;
- `free_dead_slots` interactions with word plans;
- threshold 16 in partial-context and family workloads;
- global state from `set_words_eval_default` and `set_flat_eval_default`;
- exact boundaries at six live variables and guard 16/17;
- remote protocol fields for CUDD and words provenance;
- summary NaN handling, declined counts, survivor bias, and ratio-of-medians versus
  median-of-paired-ratios;
- timing windows for compilation, environment construction, order search, extraction,
  correctness checks, and serialization;
- whether any historical CSV/report changed since `00c8ac3` and `7bb0566`;
- whether chart arrays can drift from their source CSVs.

Classify each new finding as confirmed, refuted, or partial, with severity and blast radius.
Do not opportunistically fix code during the audit unless Brian explicitly approves the
specific change.

## 8. Ground rules

- Begin and end with `git status --short --branch`.
- Preserve unrelated user changes.
- Do not edit historical reports or CSVs.
- All new artifacts go under `deliverables_n22_24\` and contain `v4audit` in the filename.
- Tests must remain exactly **159 passed, collection unchanged**, unless Brian explicitly
  approves a new test function.
- Use system Python for tests and the project virtualenv for local benchmarks.
- Use paired/interleaved timing with at least five rounds; retain raw observations.
- Never silently fall back from CUDD to autoref or from remote words to non-words.
- Never print secrets.
- Do not start/stop paid pods, deploy workers, push, publish, or commit without explicit
  authorization for the exact action.
- Do not perform full `2^32` materialization. Estimate memory first for every large explicit
  output.
- Do not reopen the dead ends catalogued in `FABLE_CM_HANDOFF.md` §6 without new evidence.

If a live CUDD environment is unavailable, complete every local/source/data audit first,
write an exact command/corpus plan, and report the live rerun as blocked. Do not replace a
same-box experiment with cross-machine raw timing and call it equivalent.

## 9. Required deliverables

Create:

1. `CM_AUDIT_V4_<date>.md` at repository root, containing:
   - executive verdict;
   - repository/environment provenance;
   - verdict on each latent fix;
   - verdict on every Independent-Review claim checked;
   - CUDD campaign and merge audit;
   - three separate comparison sections from task C;
   - correctness evidence;
   - new findings with severity and blast radius;
   - current honest headline and publication guidance;
   - explicit unresolved work.
2. `CM_SESSION_<date>_AUDIT_V4_STATE_AND_FINDINGS.md`, chaining from
   `CM_SESSION_2026-07-23_AUDIT_V3_STATE_AND_FINDINGS.md`.
3. New scripts, immutable corpus, raw timing data, reconstructed summaries, and rendered
   page checks under `deliverables_n22_24\`, all with `v4audit` in their names.

Recommended artifact split:

- `v4audit_corpus_<date>.jsonl`
- `v4audit_latentfix_verification_<date>.py`
- `v4audit_cudd_integrity_<date>.py`
- `v4audit_packed_eval_<date>.py`
- `v4audit_symbolic_build_<date>.py`
- `v4audit_query_workloads_<date>.py`
- `CM_v4audit_*_raw.csv`
- `CM_v4audit_*_summary.csv`

Every summary must be reproducible from its committed raw data by a committed script.
Reports must distinguish newly measured evidence from reconstruction of historical CSVs.

## 10. Definition of done

Audit V4 is complete only when:

- all four latent fixes have independent verdicts;
- existing CUDD raw/summary/chart claims have been reconstructed;
- merge fidelity has been checked;
- n=20..32 results are stratified by actual support and separated into packed evaluation,
  symbolic build, and downstream query workloads;
- correctness and backend identity are explicit;
- failures/refusals are reported symmetrically;
- `python -m pytest -q` still reports exactly 159 passed;
- `git status --short` and `git diff --stat` have been reviewed;
- the report states exactly what was run, skipped, blocked, changed, and left uncommitted.

Begin with repository provenance and commit diffs. Audit the CUDD commits and the four latent
fixes before running a new headline campaign.
