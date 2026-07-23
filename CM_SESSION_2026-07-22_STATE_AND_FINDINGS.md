# CM Session 2026-07-21/23 — Consolidated State & Findings (Fable session)

> The successor to `CM_SESSION_2026-07-21_STATE_AND_FINDINGS.md` (which described the
> Opus baseline through `fe73f82`). This document maps everything the Fable session did:
> the audit of the third-party agent's changes, the new numpy-words backend, five
> benchmark campaigns (two on RunPod), the bugs found, and every artifact's location.
>
> Project contact: **Brian Theory (Droncheff)**. Prepared with Claude Fable 5, 2026-07-23.

---

## 0. TL;DR for a new session

1. The unreviewed third-party changes were audited adversarially and **all KEPT**
   (claims C1–C7 all confirmed) — commit `f4cac02`; verdicts in
   `CM_FABLE_AUDIT_V2_2026-07-21.md`.
2. Its **C3 finding was real**: pre-`f4cac02`, the `--large-n-safe` "bitset" comparator
   timed the canonicalized CM DAG itself (1.2–2.2× slower than a fair flattened raw-AST
   Bitset). All published n≥18 ratios from the Opus session are superseded. It was a
   fairness bug only — the two comparators agree bit-for-bit.
3. A **numpy-uint64 "words" backend** landed (`4f99fbf`): FlatProgram over uint64
   vectors, scratch buffers colored by the liveness schedule. Opt-in, bit-identical,
   loses below ~2^14 bits, crossover n≈16, **~7× at n=24** for CM *and* Bitset alike.
4. **Two configuration-level bugs found by scaling up sample sizes** (`2dc99fa`):
   an 8-formula sample had shown CM winning at n=24 (0.84) — 300 formulas/n showed
   1.02 (sampling luck); and `hybrid_threshold=7` routed live_k≥8 formulas (~20% of
   depth-4 draws) to a numpy fallback running **~40× slower** — threshold 16 eliminates
   the cliff (→1.12–1.38×). Recommendation on record: benchmark default threshold 16.
   (No library default was changed — configuration/recommendation only.)
5. **Extended campaigns on RunPod** (`e3e2f3b`, `5787629`): n=24–32 × depths 4–8 (6,000
   formulas); full-output all-variables-live to **n=32** (4.3 G rows, CM 3.86 s vs
   Bitset 7.78 s, bit-verified); beyond-guard formulas (live_k 17–26) computed exactly
   over their true support (ratio ≈0.96 — the guard is a policy cap, not a capability
   wall). Every accepted result in every campaign was bit-exact.
6. **Current honest headline** (all claims must stay inside this envelope):
   kernel parity-to-modest-CM-advantage on sparse formulas; 1.4–3.3× CM advantage on
   sharing-rich all-live formulas (upper bracket — family caveat mandatory); end-to-end
   wrapper 1.02–1.25× behind at n≤24 drifting to 0.84 (CM ahead) by n=32; exactness and
   the reduced representation are the product, not raw speed dominance.
7. `pytest` = **159 passed** on system Python 3.10.11 throughout (words assertions were
   folded into existing tests). Benchmarks run on `.venv` Python 3.13.5.

## 1. Commit ledger (fe73f82 → HEAD, all on main)

| Commit | What / why |
|---|---|
| `4a94fc0` | (pre-session) Audit-V2 kickoff brief. |
| `f4cac02` | **Adopt third-party changes after review — all KEPT.** Last-use slot freeing (+peak alloc ↓12–27×, n=22 ~2×, n=24 neutral); first-class flattened raw-AST Bitset evaluator; C3 comparator fix + per-row `bitset_baseline_kind`; declined tracking (`cm_hybrid_no_reinflate_declined`, `_declined_count`); diagnostics-off wrapper fast path (`flat_fast_path`); caveat banners on older reports. |
| `4f99fbf` | **numpy-words backend** (`eval_cm_node_words`, `eval_expr_words_bitset`): buffer coloring via `release_after` (13–21 buffers, ~40 MB not ~500 MB at n=24); words-env cache; <6-var bigint fallback keeps it a bit-compatible drop-in. 1,827 verification checks × two interpreters. |
| `a8f17bb` | **Audit V2 deliverables**: per-claim verdicts, C3 blast radius (paired old/new comparator), 2,909-check forced-gate liveness fuzz (closed a real verification gap: the third party's own audit never executed the freeing branch), C4 reconciliation, end-to-end CLI verification. |
| `3d13c3d` | Visualization pages (dashboard + single-chart explainer), attribution (Brian Theory (Droncheff)), CUDD-comparison kickoff (`FABLE_CUDD_COMPARISON_KICKOFF.md`, has `<<TO FILL>>` blanks). |
| `7cdcd51` | Chart clarification (regimes are separate contests). |
| `2dc99fa` | **300-formula wrapper campaign** (×2 configs): n=24 0.84→1.02 correction; threshold-7 cliff discovery and threshold-16 fix; live_k n-independence confirmed. |
| `e3e2f3b` | **Extended RunPod campaign** n=24–32 × depths 4–8, 6,000 formulas, ~3 min on the $0.06/hr pod. New finding: wrapper ratio drifts toward CM with ambient n (1.01@24 → 0.84@32 at depth 4; CM ahead at every depth by n≥30). Disclosed mechanism: CM's reduced program is ambient-size-independent; the matched-scope Bitset control pays O(n) fixed-binding bookkeeping. |
| `5787629` | **Comprehensive campaign**: Regime A all-variables-live at full 2^n output, n=16–32 (words: CM 1.4–3.3× faster; family caveat: sharing-rich); Regime B beyond-guard live_k 17–26 computed over true support (≈0.96). Small pod OOM at n=28 → recovery worker pattern; n≥28 tail on a temporary 128 GB pod (~$0.35, terminated, verified 404). |
| `388011f` | Fold n=26–32 + comprehensive results into both chart pages. |
| `7bb0566` | Split the explainer's single 5-series chart into three focused charts (kernel / end-to-end / frontier). |

## 2. Bugs and traps discovered this session (audit targets)

| # | Bug/trap | Status |
|---|---|---|
| 1 | **C3 comparator** (inherited from Opus session): large-n "bitset" column timed the CM DAG. | Fixed by third party at `f4cac02`; verified; blast radius quantified; published tables superseded. |
| 2 | **`hybrid_threshold=7` mis-tuning**: live_k≥8 → numpy TT-vector fallback, ~40× slower than fair Bitset (~20% of depth-4 draws). | Config recommendation: threshold 16 (kernel handles 2^16-bit outputs cheaply). No code change; all post-`2dc99fa` campaigns use 16. Verify the recommendation independently. |
| 3 | **Small-sample luck**: 8 formulas/n produced a false n=24 CM win (0.84 vs robust 1.02). | Corrected everywhere; pages narrate the correction transparently. |
| 4 | **Third party's verification gap**: its exhaustive suite never executed the slot-freeing branch (gate ≥18 vars AND ≥64 slots unmet by its cases; committed unit tests also run below the gate). | Closed by forced-gate fuzz (`fable_adversarial_liveness_2026_07_21.py`). Follow-up suggestion (not done): promote a forced-gate case into the pytest suite. |
| 5 | Infra: RunPod container RAM ≪ host `/proc/meminfo` (guard must read cgroup limits); stale worker holds port 8081 across deploys (bootstrap can't kill; requires pod restart). | Both handled in the archived worker scripts; documented here for the next remote campaign. |

## 3. Where everything lives

**Core library (endorsed state):**
- `bitset_backend.py` — recursive kernel; C1a `FlatProgram`/`compile_flat`/`eval_cm_node_flat`
  (+ last-use freeing, gate `_FLAT_FREE_MIN_VARS=18`/`_FLAT_FREE_MIN_SLOTS=64`);
  raw-AST flat evaluator (`compile_expr_flat`/`eval_expr_flat_bitset`) = the fair Bitset;
  **words backend** (`_compute_word_plan`, `_eval_words`, `eval_cm_node_words`,
  `eval_expr_words_bitset`, words-env cache). Vectorized env build (R3) at top.
- `cm_ir.py` — canonicalizing constructors (§ "The canonicalization rule set" in the
  explainer page); `materialize_hybrid_no_reinflate` + guard + diagnostics-off fast path.
- `cm_bench.py` — harness; corrected comparator + `bitset_baseline_kind`; declined
  tracking; `--cm-flat-eval`; `--cm-hybrid-threshold` (use 16); `--large-n-safe`.
- `cmbench/results/schema.py`+`flatten.py` — `declined` field / `_declined` column.
- Words backend is NOT yet wired into the CLI (no `--cm-words-eval` flag) — open item.

**Documents (read in this order):**
1. This file.
2. `CM_FABLE_AUDIT_V2_2026-07-21.md` (repo root) — audit verdicts, C3 blast radius.
3. `deliverables_n22_24/CM_FABLE_BENCHMARKS_2026-07-21.md` — ALL benchmark results:
   §1 correctness, §2 env cliff, §3 corrected headline, §4 liveness, §5 words backend,
   §6 declines, §7 CLI runs, **§7b** 300-formula campaign + threshold fix, **§7c**
   extended n=24–32, **§7d** comprehensive full-variable + beyond-guard, §8 variance.
4. `deliverables_n22_24/cm_head_to_head_explained.html` — the public-facing explainer
   (three charts + lay/expert writeups incl. losslessness and canonicalization rules).
5. `deliverables_n22_24/cm_benchmark_charts.html` — seven-chart dashboard.
6. Historical: `CM_AUDIT_REVIEW_2026-07-21.md` (third party's report),
   `CM_SESSION_2026-07-21_STATE_AND_FINDINGS.md` (Opus baseline, §2.1 ratios superseded),
   `FABLE_CM_HANDOFF.md` §6 (dead ends — still closed), `FABLE_CUDD_COMPARISON_KICKOFF.md`
   (next planned comparison; placeholders unfilled).

**Data + reproducers (all in `deliverables_n22_24/`):**
| Artifact | Contents |
|---|---|
| `CM_FABLE_c3_blast_radius_{raw,summary}.csv` + `fable_c3_blast_radius_2026_07_21.py` | Paired old-vs-new comparator measurement. |
| `fable_adversarial_liveness_2026_07_21.py` | 2,909-check forced-gate liveness fuzz (run on both interpreters). |
| `fable_words_verify_2026_07_21.py` | Words backend: 1,827 checks + crossover timing. |
| `CM_FABLE_wrapper_stats300{,_t16}_{raw,summary}.csv` + `fable_wrapper_stats300{,_t16}_2026_07_22.py` | 300/n campaigns, thresholds 7 and 16. |
| `CM_FABLE_extended_n32_{raw,summary}.csv` + `fable_extended_campaign_worker_2026_07_22.py` + push/poll scripts | RunPod n=24–32 × depth 4–8. |
| `CM_FABLE_comprehensive_{fullvars,beyondguard}.csv` (+ `RECOVERED_*`, `*_tail_*` provenance) + `fable_comprehensive{,_tail}_worker_2026_07_22.py`, `fable_bigpod_provision_2026_07_22.py` | Full-output to n=32 + beyond-guard; two-pod story. |
| `fable_headline_endorsed_{raw,summary}.csv`, `fable_decline_d6_{raw,summary}.csv` | End-to-end CLI verification (baseline-kind column, declined_count surfacing). |
| `CM_audit_2026-07-21_*_fable_*.csv`, `CM_env_build_*_fable.csv`, `CM_flat_liveness_*_fable_*.csv` | Fable re-runs of the third party's audit scripts. |

**RunPod:** standing pod `x82z2pbpofhcgz` ($0.06/hr, kept warm at Brian's request);
config in `.env.runpod{,.local}` (never print the API key). The bootstrap `/put` can
overwrite `cm_remote_worker.py` to run arbitrary campaign workers; a pod restart is
needed to replace a running worker. Temporary big pod pattern:
`fable_bigpod_provision_2026_07_22.py` (created 128 GB pod, terminated after use).

## 4. Protocols that must not regress

- Oracle (`eval_expr_tt` or the independent scalar evaluator) outside timed windows;
  bit-exactness proven for every kernel (packed-output equality IS exhaustive).
- CM claims measured against the **flattened raw-AST Bitset**, matched scope, matched
  engine; `bitset_baseline_kind` recorded per row.
- Medians over ≥5 trials, paired/interleaved ordering, spreads + live_k/repr mix
  disclosed; declines counted, never silently dropped.
- Family caveats attached to sharing-rich results (upper bracket) vs sparse (~parity).
- `python -m pytest -q` (system 3.10.11) stays green; new evaluators behind opt-in
  entry points; schema changes via `cmbench/results/schema.py` + stability tests.
- `FABLE_CM_HANDOFF.md` §6 dead ends stay closed.

## 5. Open items (ranked)

1. **`--cm-words-eval` CLI flag** + schema column, mirroring `--cm-flat-eval`.
2. **Adopt threshold 16** as the harness default (currently recommendation-only).
3. Promote a forced-gate liveness case into the pytest suite.
4. **Tiled/blocked evaluator** for full-output beyond the RAM wall (n≥30 needs
   ~4–16 GB env; a 2^24-row block evaluator would make n arbitrary at O(block) memory).
5. Profile the wrapper-drift mechanism claim (§7c) — the O(n) fixed-binding bookkeeping
   explanation is plausible and stated honestly, but was not isolated by profiling.
6. CUDD comparison (`FABLE_CUDD_COMPARISON_KICKOFF.md`) once Brian fills the
   environment placeholders.
