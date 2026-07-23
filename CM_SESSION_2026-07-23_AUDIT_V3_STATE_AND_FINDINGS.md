# CM session state — Audit V3 findings and corrected handoff

Date: 2026-07-23
Project contact: **Brian Theory (Droncheff)**
Predecessor: `CM_SESSION_2026-07-22_STATE_AND_FINDINGS.md`
Full verdict: `CM_AUDIT_V3_2026-07-23.md`

## Corrected state in one page

1. **Words backend retained.** Both interpreters passed the original 1,827 checks and
   79 new adversarial cache/alias/boundary checks. Fresh n=24 speedups are
   6.28×/7.47× (CM/raw) on Python 3.13.5 and 7.13×/8.21× on Python 3.10.11.
   Symmetric availability is the fairness guarantee; the CM/raw ratio is not literally
   invariant.
2. **Harness threshold is now 16.** A 1,500-formula paired three-way run confirms the
   live_k≥8 cliff and no systematic regression below it. Only the benchmark harness
   default changed; `cm_ir` library defaults remain threshold 7, flat off, words off.
3. **n=24 wrapper correction remains, with a range.** The old 0.84 result was sampling
   luck. Repeated 300-formula medians are 1.02–1.09 CM/Bitset.
4. **Ambient-n drift is control bookkeeping.** Same-formula n=24→32 isolation gives
   +1.83 µs full raw, +1.50 µs binder, -0.08 µs prebound evaluation, and -0.13 µs CM
   wrapper. Do not describe the drift as an inherently growing Bitset kernel cost.
5. **The Fable “all-live through n=32” claim is retracted.** Its EQV mixer can cancel
   an entire subtree. Exact BDD support: 4/29 rows truly all-live; median support 16;
   n=32 support 16. The row remains a bit-exact full-ambient-output timing, not an
   all-live result.
6. **The sharing bracket survives.** Old-family raw-op/CM-op compression correlates
   r=0.945 with speed advantage. A corrected exactly all-live family gives CM a
   1.75–2.52× advantage through n=26; it remains a favorable upper bracket.
7. **Beyond guard survives.** Six fresh local rows through retained_k=26 are complete
   packed matches plus sampled scalar matches; local median ratio 0.95.
8. **Public pages are corrected.** The invalid n=32 all-live series was removed,
   wrapper/F4/F3 language was narrowed, all plotted data maps through
   `CM_V3AUDIT_F6_chart_trace.csv`, and both themes render.

## Code/config state

- `--cm-words-eval` selects the numpy-words engine symmetrically for CM and the raw-AST
  Bitset control.
- Rows and summaries record `cm_words_eval`; baseline provenance is
  `raw_ast_words` or `raw_ast_words_matched_scope`.
- `--cm-hybrid-threshold` defaults to 16 in the harness.
- A natural n=18, ≥64-slot last-use release case is now part of the existing pytest
  function without increasing the 159-test collection.
- Tiled evaluator design: `CM_TILED_WORDS_EVALUATOR_DESIGN_2026-07-23.md`.
- CUDD remains untouched pending Brian's environment placeholders.

## Do not repeat these claims

- Do not call `CMNode.vars` exact or minimal semantic support. It is a sound
  post-rewrite support over-approximation.
- Do not cite the old n=32 row as all-variable-live.
- Do not say words leaves the CM/Bitset ratio unchanged; say both sides receive it.
- Do not present 1.02 as a universal n=24 wrapper constant.
- Do not treat the current matched-scope control's O(n) fixed-key cost as an inherent
  Bitset kernel property.

## Key Audit V3 artifacts

- F1: `CM_V3AUDIT_F1_words_timing.csv`,
  `CM_V3AUDIT_F1_words_adversarial_py{310,313}.csv`
- F2: `CM_V3AUDIT_F2_threshold_paired_{raw,summary}.csv`
- F3: `CM_V3AUDIT_F3_n24_seeds_{raw,summary}.csv`
- F4: `CM_V3AUDIT_F4_binding_profile_{raw,summary}.csv`
- F5: `CM_V3AUDIT_F5_family_structure_{raw,summary}.csv`,
  `CM_V3AUDIT_F5_corrected_all_live_{raw,summary}.csv`,
  `CM_V3AUDIT_F5_beyondguard_local.csv`
- F6: `CM_V3AUDIT_F6_chart_trace.csv` and theme/full-page screenshots
- CLI: `CM_v3audit_words_cli_{raw,summary}.csv`
- tests: `v3audit_pytest.log`

Historical reports and CSVs remain in place. Corrections are additive in the Audit V3
report, the state chain, and explicit correction blocks on the Fable benchmark report.
