# CM Gap Series — Final Acceptance Handoff (2026-08-03)

Self-contained state for a new GPT/Codex session after the accepted
consolidated corrective pass. Decision of record:
**READY FOR INDEPENDENT REVIEW ACCEPTED**
(`CM_GAP_CONSOLIDATED_REVIEW_2026-08-03.md`; caveat: the acceptance review
was executed by the pass's author at the operator's direction — a third-party
replication of any one review section, cheapest being the §4A reaggregation,
closes that caveat).

## 1. Repository state

- Root: `C:\Users\brian\Documents\CM_Computation`
- Branch `main`; HEAD = `origin/main` = `4c51429`; production repair `12defc4`.
- **Accepted working-tree changes (uncommitted; do not discard):**
  - `cm_ir.py` — F4 fix: `_adopt_foreign` structural adoption of foreign
    CMNodes + `_foreign_keepalive` pinning; F7a: `_persistent_digest`
    docstring states the blake2b-128 collision assumption (+81/−8).
  - `cm_expr_serde.py` — F7b: v2 reader rejects unreachable definitions
    (forces root-last); accepted-input contract documented (+33).
  - `tests/test_expr_serde_v2.py` — +3 tests (+39).
  - New tests: `tests/test_foreign_node_interning.py` (11),
    `tests/test_e3_output_safety.py` (5), `tests/test_e3_corpus_determinism.py` (1).
  - New deliverables under `deliverables_n22_24\` (see §2/§3).
- Pre-existing untracked, preserve: `deliverables_n22_24\CM_FINAL_REVIEW_PROMPT_2026-08-02.md`,
  `.claude\`, `tmp\pytest_cm_consolidated\`.
- Interpreters: benchmarks `C:\Users\brian\Documents\CM_Computation\.venv\Scripts\python.exe`
  (3.13.5, numpy 2.3.2); tests system Python 3.10.11 with a workspace-local
  `--basetemp` whose parent exists.

## 2. Authoritative files (absolute paths)

| file | role |
|---|---|
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_GAP_CONSOLIDATED_AUDIT_AND_ERRATUM_2026-08-02.md` | audit verdicts F1–F7, 8-area production audit, erratum E1–E6, claim disposition |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_GAP_CONSOLIDATED_REVIEW_2026-08-03.md` | acceptance review (this pass's verification of record; findings R1/R2) |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_consolidated_review_results_2026_08_03.json` | machine-readable acceptance evidence (embeds all probe outputs) |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_e3_corrected_2026_08_02.py` | corrected E3 driver (stable seeds, exact semantic support, overwrite-safe) |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_gap_e3_corrected_corpus_2026_08_02.jsonl` | frozen corpus, 192 formulas, SHA-256 `8a6da87cc8b13f6123cb11adfa77b5d69bcd0a086666abea7df633ef92f6e68a` |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_e3_corrected_results_2026_08_02.json` | authoritative E3 results (blocked + round-robin, stratified bootstrap, break-even) |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_gap_e3_corrected_summary_2026_08_02.csv` | authoritative E3 summary table |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_consolidated_validation_2026_08_02.json` | F1–F7 validation evidence (frozen; rerun only redirected) |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_repair_merge_review_results_consolidated_rerun_2026_08_02.json` | post-fix adversarial probe result |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_GAP_FILE_INDEX_AND_SUPERSESSION_2026-08-02.md` | complete artifact index + status map |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_GAP_MASTER_HANDOFF_2026-08-02.md` | pass-level handoff (its §3 was amended 2026-08-03: validation probe reruns must be redirected, never `--overwrite`) |

Superseded (kept for provenance; never cite without the erratum):
`cm_gap_final_repair_e3_2026_08_02.py`, `CM_gap_e3_corpus_2026_08_02.jsonl`,
`cm_gap_final_repair_e3_results_2026_08_02.json`,
`CM_gap_final_repair_e3_summary_2026_08_02.csv`, the archived report's
§Phase C (0.843 headline), `CM_GAP_FINAL_REPAIR_HANDOFF_2026-08-02.md`.
Full map: file index §4/§5.

## 3. Accepted results of record

- Kernel boundary, repaired CM vs structural CSE, 192 exact-support
  formulas: geomean **0.888 [0.876, 0.899]** (strata 0.871 / 0.869 / 0.925;
  round-robin within ~2%; impeqv_dom ≈ parity). Scope: one local Windows
  box, this synthetic generator.
- Mechanism: executed-op ratio median 1.000; edge = n-ary instruction
  merging (instr ratio 0.693, r 0.824); vs CSE+flatten **0.985** (≈parity).
- Costs: prep 4.30× CSE geomean; break-even median 78.5 evals; 30/192 never
  break even. Wrapper overhead median 23 µs, reported separately.
- Dispositions: V4 C1 superseded (cite only the corrected statement);
  128×/240× retraction stands; compile-scaling and schedule claims retained;
  BDD boundary out of scope.
- Verification: full suite 326/326; corpus regenerates byte-identically
  under PYTHONHASHSEED 0/1/31337; archived stats reaggregate exactly from
  raw rows; fresh replay Δgeomean 0.0001 with CI overlap.
- Known nuances (non-blocking, documented in the review): R1 identity-basis
  corpus fields are generation-time values (recompute via recorded seed);
  R2 foreign/twin identity divergence can duplicate lowered slots exactly as
  the pre-compact-key builder did.

## 4. Proposed commit decomposition (do not execute without Brian)

1. `fix(cm): structural adoption for foreign nodes in compact interning` —
   `cm_ir.py` + `tests/test_foreign_node_interning.py`
2. `fix(serde): reject unreachable v2 definitions; document accepted input` —
   `cm_expr_serde.py` + `tests/test_expr_serde_v2.py`
3. `bench(e3): corrected corpus generator with semantic-support admission` —
   `deliverables_n22_24/cm_gap_e3_corrected_2026_08_02.py`,
   `tests/test_e3_output_safety.py`, `tests/test_e3_corpus_determinism.py`
4. `bench(data): consolidated audit, erratum, corrected E3, acceptance review` —
   remaining new `deliverables_n22_24\*` files
   (fold the `cm_ir.py` docstring hunk into commit 1).
   Each message ends with the repo's `Co-Authored-By: Claude Fable 5
   <noreply@anthropic.com>` convention.

## 5. Open follow-ups (all require Brian's authorization)

- Commit/push the accepted tree (above).
- EPFL external corpus (download ~50 MB; plan + stop rules in
  `CM_GAP_FINAL_REPAIR_AND_E3_2026-08-02.md` §External work).
- Pod replication, 5 × cpu3c, frozen corrected corpus + driver, <$1
  (worker-redeploy note in `CM_LATENT_FIXES_2026-07-23.md` applies).
- Optional third-party spot-replication of one review section (§4A
  reaggregation) to close the self-review caveat.
- Two one-line docs clarifications (R1 field basis; R2 nuance) in a future
  pass — do not amend historical artifacts for them.
- Public-facing claim text may now be updated to the §3 statements above.

## 6. Rules for the next session

No commit/push/amend/reset/stash/clean without explicit instruction; never
run archived fixed-output drivers directly (redirect probes via module `OUT`
override); write all new evidence to new paths; benchmarks on the venv
interpreter, tests on system 3.10 with an existing basetemp parent; preserve
every pre-existing untracked file; do not edit historical reports or result
artifacts.
