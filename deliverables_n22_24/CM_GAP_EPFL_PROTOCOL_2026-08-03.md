# CM Gap Series — EPFL/AIGER External-Corpus Protocol (2026-08-03, pre-registered)

Status: **PRE-REGISTERED, NOT EXECUTED.** `EPFL_DOWNLOAD_APPROVED = NO` at
writing time; nothing has been downloaded, installed, or measured. This
protocol is frozen before any external data is seen. If a defect is found
after execution begins, execution stops, the defect is documented, a
versioned successor protocol is written, and the campaign reruns into new
filenames — this document is never edited after approval.

Purpose: test whether the corrected-E3 synthetic result — CM kernel ≈ parity
with CSE+sharing-aware-flatten (geomean 0.985), 0.888 vs plain structural
CSE, mechanism = n-ary instruction merging — generalizes to real
combinational circuits.

## 1. Source, destination, download

- Repository: `https://github.com/lsils/benchmarks.git` (EPFL combinational
  benchmark suite).
- Proposed clone command (exact):
  `git clone --depth 1 https://github.com/lsils/benchmarks.git C:\Users\brian\Documents\CM_Computation\external\epfl-benchmarks`
- Destination: `C:\Users\brian\Documents\CM_Computation\external\epfl-benchmarks`
  (new directory; never staged or committed; contents never modified).
- Expected download: **~50 MB** (shallow clone).
- Provenance recorded in a machine-readable manifest
  (`cm_gap_epfl_provenance_<date>.json`): remote URL, clone command, clone
  commit SHA (`git -C ... rev-parse HEAD`), clone date, license name +
  SHA-256 of the license file, total on-disk size, and for **every** `.aig`
  file consumed: relative path, category, SHA-256, byte size.
- Categories consumed: `arithmetic/` and `random_control/` only.
  Combinational circuits only (enforced by parser: AIGER latch count L must
  be 0; nonzero-latch files are recorded and skipped).

## 2. Formats, parser, and conversion strategy

- Supported input: **binary AIGER** (`.aig`, header `aig M I L O A`) parsed
  directly by a new, small, in-repo Python parser (delta-encoded AND list
  per the AIGER 1.9 spec); **ASCII AIGER** (`.aag`) parsed for test
  fixtures. No external conversion tool (`aigtoaig`) and **no new
  dependency** — extractor and analysis use the project venv's existing
  stdlib+numpy only. If any additional package ever appears necessary, it
  will be named individually and approved before installation
  (`DEPENDENCY_INSTALL_APPROVED = NO`).
- Conversion: AIG node → expression DAG with **one expression node per AIG
  node** (id-memoized), `And(a,b)` for AND gates, `Not(x)` for inverted
  edges, constants for literals 0/1. **AIG sharing is preserved** in the
  extracted representation; the extractor performs **no synthesis, no
  rewriting, no restructuring** — XOR/MUX recovery, if any, is the measured
  pipelines' own job. (Scope note, stated up front: EPFL AIGs are AND/INV
  structures; this campaign tests generalization to AND/INV-form real
  circuits, a deliberately different operator mix than the synthetic
  families.)
- Parser correctness tests (added under `tests\` before any timing):
  hand-built synthetic fixtures — 2-input AND, inverted output, XOR-of-2
  built from 3 ANDs + inverters, 3-input majority, constant-0 and
  constant-1 outputs, a latch-bearing file that must be rejected, and a
  binary/ASCII pair that must parse to identical structures — each verified
  by exhaustive truth-table comparison against the fixture's known truth
  function, plus packed-equality of the converted expression against the
  reference CSE pipeline evaluation.

## 3. Cone selection (deterministic; fixed before any timing)

Processing order: categories alphabetically, circuits alphabetically by
filename within category, candidate roots in deterministic order (primary
outputs by output index first, then internal AND nodes by topological
index). Selection is a pure function of the parsed AIG — reruns of the
extractor must produce a byte-identical corpus (verified under three
PYTHONHASHSEED values, as for corrected E3).

Eligibility of a candidate root's cone:

1. **Syntactic support ≤ 16** primary inputs (cone-of-influence), so the
   complete packed truth-function domain is ≤ 2^16 bits — matching the
   evaluation regime of corrected E3's largest stratum (no new
   memory-bandwidth regime is introduced).
2. **Live semantic support between 8 and 16** inclusive, measured by
   influence on the **complete packed truth function** over the cone's
   syntactic support (same admission machinery class as corrected E3;
   computed with an independent packed evaluator over the cone, not with
   cm_ir). Cones are used **as extracted** — no rewriting to make a cone
   qualify, no dead-variable stripping of the expression.
3. **Structural size cap:** cone ≤ 5,000 AIG AND nodes (parse/compile
   bound). Larger cones recorded as `skipped_structural_cap`.
4. **Raw-ablation cap:** unfolded occurrences ≤ 60,000 for the raw arm.
   Cones over the cap but otherwise eligible are **admitted without the raw
   arm** (`raw_arm_skipped_unfolded_cap` flag); the three primary arms
   always run. This differs from E3 (which capped the corpus) and is
   pre-registered here: external realism outranks raw-ablation coverage.
5. **Constants and degenerate cones** (semantic support < 8, including
   constant truth functions) recorded and skipped.

Deduplication (applied in processing order, first occurrence wins):

- within-circuit and cross-circuit, by the pair
  (structural hash of extracted expression, truth-function SHA-256);
- a cone structurally identical to an already-admitted one is recorded as
  `skipped_duplicate` with a pointer to the kept id.

Per-circuit cap: **max 8 formulas per circuit**, chosen deterministically
before any timing: qualifying primary-output cones first (by output index);
if fewer than 8, fill from qualifying internal-node cones sampled at evenly
spaced ranks of the qualifying-internal list (indices
`floor(j*(Q-1)/(m-1))` for j=0..m-1 over Q qualifying internal cones —
deterministic, no timing knowledge).

Stop rule: a circuit with **no qualifying cone** is recorded with its
rejection histogram and skipped — never synthesized, never rewritten, never
silently dropped. If an entire category yields no qualifying circuit, the
campaign reports that fact rather than widening the rules post hoc.

## 4. Measurement design

Arms (identical harness class to corrected E3; bare `_eval_words` kernels):

- `cm` — repaired CM pipeline, default flags (sharing-aware flattening on);
- `cse` — plain structural CSE (explanatory secondary baseline);
- `cse_flat` — structural CSE + sharing-aware flattening (**primary
  comparator**);
- `raw` — raw ablation, only under the unfolded cap.

**Primary comparison: CM vs CSE+sharing-aware-flatten.**

- **Packed-equality assertion across every applicable arm (and the wrapper)
  before every timing measurement**; truth SHA re-verified against the
  corpus record at measurement time. A formula failing equality aborts the
  campaign (that is a correctness defect, not a data point to drop).
- Schedules: blocked (4 rounds × 200 kernel repeats, warm within formula)
  and round-robin (cycling formulas), **reported separately, never pooled**
  — same parameters as corrected E3.
- Metrics per formula: prep time per arm; kernel time per arm and schedule;
  executed word ops, flat instructions, loads, peak live buffers per arm;
  kernel ratios cm/cse and cm/cse_flat; instruction and executed-op ratios;
  prep multiples; break-even evaluations vs cse and vs cse_flat (rule as
  documented in the spot replication: never iff no kernel gain, else
  `max(0, ceil(Δprep/Δkernel))`).
- Environment metadata recorded in results `_meta`: python, numpy, CPU,
  platform, git revision, extractor/corpus SHA-256s, wall time, schedule
  parameters, PYTHONHASHSEED, cache-state statement.

Runtime stop rules (pre-registered):

- Deterministic pilot first: the alphabetically first circuit per category
  that yields ≥1 qualifying cone, per-circuit cap 4, full measurement
  harness. Pilot must complete and pass all packed-equality assertions.
- Full-campaign wall-time estimate = pilot time × (projected admitted
  formulas / pilot formulas). If the estimate exceeds **60 minutes**, stop,
  report the estimate, and request re-scoping — do not trim rules ad hoc.
- Per-formula guards: any single arm prep > 10 s or single blocked round
  > 5 s ⇒ formula recorded `skipped_runtime_guard` with partial data kept.
  All skips and reasons are listed in the results and the report — nothing
  unfavorable or difficult is silently excluded.

## 5. Analysis (cluster-aware; fixed before data)

- **Inferential unit for primary conclusions: source circuit.** Many cones
  from one circuit must not create false precision.
- Primary statistic: geomean of per-formula cm/cse_flat blocked kernel
  ratios; **circuit-clustered bootstrap** (resample circuits with
  replacement, keep all their formulas; 4,000 draws; fixed literal seed
  recorded in the results; percentile 95% CI, linear interpolation).
  Round-robin analyzed identically and reported separately.
- Secondary (descriptive): per-circuit geomean table; by category; by
  semantic-support bucket (8–10, 11–13, 14–16); cm/cse ratios; instruction
  and executed-op ratio distributions; corr(log instruction ratio, log
  kernel ratio) as the mechanism check; prep multiples and break-even
  distributions; formula-level stratified CIs (labeled descriptive only).
- Summaries are recomputed **independently from the raw measurement rows**
  by a separate reaggregation step before the report cites them (the
  discipline the spot replication just exercised).

## 6. Materiality rule (pre-registered decision rule)

A residual CM kernel advantage is **optimization-worthy** only if all three
hold on the external corpus:

1. CM/CSE-flat blocked geomean ≤ **0.95**;
2. its **circuit-clustered** 95% CI excludes parity (upper endpoint < 1.0);
3. preparation cost amortizes within a realistic reuse count: median
   break-even vs CSE-flat ≤ **1,000 evaluations** over admitted formulas.

Otherwise the two implementations are declared **kernel-equivalent** for
real-circuit workloads, and the ~1.5% synthetic residual (0.985) is not
chased. The plain-CSE comparison is explanatory only and cannot trigger
optimization work by itself. This rule is fixed now, before any external
measurement exists, and the report must apply it as written.

## 7. Outputs (all new files, refuse-overwrite defaults)

Fresh output directory per run (`deliverables_n22_24\epfl_run_<date>\` for
intermediates); final artifacts under `deliverables_n22_24\`:

- `cm_gap_epfl_extract_<date>.py` — extractor/driver (smallest auditable
  implementation; `--out-dir` + refuse-if-exists, no `--overwrite` use in
  the campaign);
- `CM_gap_epfl_corpus_<date>.jsonl` — frozen extracted corpus with
  per-record provenance (circuit, root, category, source-file SHA);
- `cm_gap_epfl_results_<date>.json` — raw rows + `_meta`;
- `CM_gap_epfl_summary_<date>.csv` — summary table;
- `CM_GAP_EPFL_VALIDATION_<date>.md` — report ending with exactly one of:
  `EXTERNAL VALIDATION SUPPORTS GENERALIZATION` /
  `EXTERNAL VALIDATION DOES NOT SUPPORT GENERALIZATION` /
  `EXTERNAL VALIDATION INCONCLUSIVE` / `BLOCKED`;
- parser/extractor tests under `tests\` (fixtures inline, no downloads);
- `cm_gap_epfl_provenance_<date>.json` — the manifest of §1.

`<date>` = actual execution date. The external clone itself is never
staged, committed, or edited.

## 8. Approval gate (open)

Execution requires Brian to approve, explicitly:

1. cloning ~50 MB from `https://github.com/lsils/benchmarks.git`;
2. writing it under
   `C:\Users\brian\Documents\CM_Computation\external\epfl-benchmarks`;
3. any missing parser/conversion dependency, named individually — **none is
   currently anticipated** (direct binary-AIGER parsing in-repo; existing
   venv numpy for packed evaluation).

Until then: `EPFL_DOWNLOAD_APPROVED = NO` and this protocol simply waits.
