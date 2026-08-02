# CM Gap Series — Consolidated File Index and Supersession Map (2026-08-02)

Authoritative revision at writing: `main` = `4c51429` = `origin/main`
(production repair at `12defc4`). The consolidated corrective pass added the
files marked **NEW** below as uncommitted working-tree changes; nothing
historical was edited, overwritten, or rewritten.

Status legend — **authoritative**: current best evidence, cite this;
**superseded**: kept for provenance, do not cite without the correction;
**historical**: intermediate step, superseded by the chain that followed it.

## 1. Production code (tracked; modified by this pass where noted)

| path | purpose | commit | status |
|---|---|---|---|
| `C:\Users\brian\Documents\CM_Computation\cm_ir.py` | CM IR builder, canonicalization, persistent compile path | `12defc4`, **modified (uncommitted)**: F4 foreign-node structural adoption + keepalive; F7a digest-language correction | authoritative |
| `C:\Users\brian\Documents\CM_Computation\bitset_backend.py` | packed evaluation, flat programs, metrics, structural-CSE baseline | `12defc4` (unmodified by this pass) | authoritative |
| `C:\Users\brian\Documents\CM_Computation\cm_expr_serde.py` | v1 tree + v2 defs/ref serialization | `12defc4`, **modified (uncommitted)**: F7b unreachable-definition rejection + accepted-input contract docs | authoritative |

## 2. Tests (tracked at `12defc4` unless marked NEW)

| path | purpose | status |
|---|---|---|
| `C:\Users\brian\Documents\CM_Computation\tests\test_share_aware_flatten.py` | sharing-aware flattening | authoritative |
| `C:\Users\brian\Documents\CM_Computation\tests\test_build_memo.py` | per-compilation memo lifetime | authoritative |
| `C:\Users\brian\Documents\CM_Computation\tests\test_persistent_path_consistency.py` | persistent ≡ normal compile | authoritative |
| `C:\Users\brian\Documents\CM_Computation\tests\test_program_metrics.py` | executed-op accounting | authoritative |
| `C:\Users\brian\Documents\CM_Computation\tests\test_bitset_cse.py` | structural-CSE baseline | authoritative |
| `C:\Users\brian\Documents\CM_Computation\tests\test_expr_serde_v2.py` | v2 serde; **modified (uncommitted)**: F7 unreachable/non-last-root/alt-ordering tests | authoritative |
| `C:\Users\brian\Documents\CM_Computation\tests\test_foreign_node_interning.py` | **NEW** — F4 regression suite (idempotence, interning, GC/id-reuse pinning) | authoritative |
| `C:\Users\brian\Documents\CM_Computation\tests\test_e3_output_safety.py` | **NEW** — F5: corrected driver cannot overwrite by default | authoritative |
| `C:\Users\brian\Documents\CM_Computation\tests\test_e3_corpus_determinism.py` | **NEW** — F1: byte-identical corpus across PYTHONHASHSEED subprocesses | authoritative |

## 3. Consolidated corrective pass (NEW, uncommitted)

| path | purpose | status |
|---|---|---|
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_GAP_CONSOLIDATED_AUDIT_AND_ERRATUM_2026-08-02.md` | audit verdicts F1–F7, area-by-area production audit, erratum, claim disposition | **authoritative** |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_e3_corrected_2026_08_02.py` | corrected E3 driver (stable seeds, exact semantic support, admission rules, overwrite-safe) | **authoritative** |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_gap_e3_corrected_corpus_2026_08_02.jsonl` | corrected corpus: 192 formulas, 24 cells × 8, exact support, sha `8a6da87cc8b13f6123cb11adfa77b5d69bcd0a086666abea7df633ef92f6e68a` | **authoritative** |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_e3_corrected_results_2026_08_02.json` | corrected E3 machine-readable results (blocked + round-robin, stratified bootstrap, break-even) | **authoritative** |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_gap_e3_corrected_summary_2026_08_02.csv` | corrected E3 summary table | **authoritative** |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\e3_corrected_pilot_2026_08_02\` (corpus/results/summary) | deterministic 4-per-cell pilot that passed the 60-minute widening gate (13.6 s wall) | historical (superseded by the 8-per-cell run above) |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_consolidated_validation_probe_2026_08_02.py` | machine validation of F1–F7 + gate evidence | authoritative |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_consolidated_validation_2026_08_02.json` | validation results (all findings, probe rerun, corrected-E3 headline) | **authoritative** |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_repair_merge_review_results_consolidated_rerun_2026_08_02.json` | adversarial probe re-run **after** the F4/F7 fixes (new path; archived result untouched) | **authoritative** for post-fix state |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_GAP_MASTER_HANDOFF_2026-08-02.md` | self-contained prompt + state for the next independent review | **authoritative** |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_GAP_FILE_INDEX_AND_SUPERSESSION_2026-08-02.md` | this file | authoritative |

## 4. Final-round E3 artifacts (tracked, `4c51429`) — SUPERSEDED

| path | purpose | status / replacement |
|---|---|---|
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_final_repair_e3_2026_08_02.py` | superseded E3 driver | **superseded** (F1 seeds, F2 syntactic-only support, F5 fixed outputs) → `cm_gap_e3_corrected_2026_08_02.py` |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_gap_e3_corpus_2026_08_02.jsonl` | superseded corpus (96 formulas; 53 exact-support, 43 reduced, 5 constants) | **superseded** → `CM_gap_e3_corrected_corpus_2026_08_02.jsonl` |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_final_repair_e3_results_2026_08_02.json` | superseded E3 results | **superseded** → `cm_gap_e3_corrected_results_2026_08_02.json` |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_gap_final_repair_e3_summary_2026_08_02.csv` | superseded E3 summary | **superseded** → `CM_gap_e3_corrected_summary_2026_08_02.csv` |
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_GAP_FINAL_REPAIR_AND_E3_2026-08-02.md` | final repair report + superseded E3 analysis | Phases A/B **authoritative with erratum items E2–E5**; §Phase C and §Revised disposition **superseded** by the consolidated audit |

## 5. Repair and review chain (tracked, `4c51429`) — historical with erratum

All of these describe the repair as an *uncommitted diff on `b6ce6b2`*; that
became stale when `12defc4`/`4c51429` were committed and pushed (erratum E1).
Technical content stands except where the erratum says otherwise.

| path | purpose | status |
|---|---|---|
| `...\CM_GAP_AUDIT_2026-08-01.md` | first gap audit (found the benchmark gaps) | historical |
| `...\cm_gap_audit_probe_2026_08_01.py` / `..._results_2026_08_01.json` | audit probe + results | historical |
| `...\CM_GAP_DEEP_FOLLOWUP_2026-08-02.md` (+ `_HANDOFF`) | deep follow-up (len(ops)≠executed ops, sharing analysis) | historical |
| `...\cm_gap_deep_followup_2026_08_02.py` / `..._results_2026_08_02.json` | follow-up probe + results | historical |
| `...\CM_GAP_REPAIR_IMPLEMENTATION_2026-08-02.md` (+ `CM_GAP_REPAIR_HANDOFF`) | repair implementation report | historical |
| `...\cm_gap_repair_benchmark_2026_08_02.py` / `cm_gap_repair_results_2026_08_02.json` / `CM_gap_repair_before_after_2026_08_02.csv` | repair benchmark + results | historical |
| `...\CM_GAP_REPAIR_MERGE_REVIEW_2026-08-02.md` (+ `_HANDOFF`) | adversarial merge review (6 concerns) | historical |
| `...\cm_gap_repair_merge_review_probe_2026_08_02.py` | adversarial probe (still the live probe; run redirected from now on) | authoritative script |
| `...\cm_gap_repair_merge_review_results_2026_08_02.json` | archived pre-consolidation probe result (was updated in place during the final round) | frozen archived; post-fix state → `..._consolidated_rerun_2026_08_02.json` |
| `...\CM_GAP_FINAL_REPAIR_HANDOFF_2026-08-02.md` | final-round handoff | **superseded** → `CM_GAP_MASTER_HANDOFF_2026-08-02.md` |
| `C:\Users\brian\Documents\CM_Computation\CM_BENCHMARK_GAP_ANALYSIS_2026-08-01.md` | root-level gap analysis | historical |

## 6. Pre-existing untracked files (preserved, not part of this pass)

| path | purpose | status |
|---|---|---|
| `C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_FINAL_REVIEW_PROMPT_2026-08-02.md` | external final-review prompt (source of the Codex findings) | historical input; its "uncommitted diff" framing and its instruction to re-run the fixed-path drivers are corrected by erratum E1/E6 |
| `C:\Users\brian\Documents\CM_Computation\.claude\` | local tool state | not an artifact |

## 7. Earlier campaign artifacts (V2–V4, CUDD, etc.)

Unchanged by this pass; see `CM_AUDIT_V4_2026-07-24.md` and the audit-V2/V3
chain. The V4 C1 and multiplier claims they contain are governed by the claim
disposition in `CM_GAP_CONSOLIDATED_AUDIT_AND_ERRATUM_2026-08-02.md`.
