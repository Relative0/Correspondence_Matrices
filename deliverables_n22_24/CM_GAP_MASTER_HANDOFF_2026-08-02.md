# CM Gap Series — Master Handoff (2026-08-02, post-consolidated-corrective-pass)

Self-contained state + prompt for the next independent (GPT/Codex) review.
Read this file first; everything else is referenced by absolute path.

## 1. Repository state

- Project root: `C:\Users\brian\Documents\CM_Computation`
- Branch `main`; HEAD = `origin/main` = `4c51429` ("docs(audit): preserve CM
  gap repair deliverables"); production repair commit `12defc4` ("feat(cm):
  add structural CSE flat baseline").
- The consolidated corrective pass (this handoff's author) left **uncommitted
  working-tree changes** — do not "restore" or discard them:
  - modified: `cm_ir.py`, `cm_expr_serde.py`, `tests/test_expr_serde_v2.py`
  - new tests: `tests/test_foreign_node_interning.py`,
    `tests/test_e3_output_safety.py`, `tests/test_e3_corpus_determinism.py`
  - new deliverables under `deliverables_n22_24\` (full list:
    `CM_GAP_FILE_INDEX_AND_SUPERSESSION_2026-08-02.md`)
- Pre-existing untracked files to preserve:
  `deliverables_n22_24\CM_FINAL_REVIEW_PROMPT_2026-08-02.md`, `.claude\`.
- Benchmarks: `C:\Users\brian\Documents\CM_Computation\.venv\Scripts\python.exe`
  (3.13.5, numpy 2.3.2). Tests: system Python 3.10.11 with
  `--basetemp C:\Users\brian\Documents\CM_Computation\tmp\pytest_cm_<name>`
  (create the `tmp` parent first; a missing parent produces collection
  ERRORs that look like test failures but are environmental).

## 2. What this pass established (details + machine evidence in the audit report)

Authoritative report:
`C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_GAP_CONSOLIDATED_AUDIT_AND_ERRATUM_2026-08-02.md`
Machine evidence:
`...\cm_gap_consolidated_validation_2026_08_02.json`,
`...\cm_gap_repair_merge_review_results_consolidated_rerun_2026_08_02.json`.

- Findings F1 (hash-seeded corpus), F2 (syntactic-only support: 53/96 exact,
  5 constants), F4 (foreign-node interning regression), F5 (overwriting
  drivers), F6 (stale repo-state text), F7 (digest/canonicality overreach):
  **CONFIRMED**; F4/F5/F7 fixed in the working tree, F1/F2 fixed by the
  corrected driver, F6 handled by erratum. F3 (`tree_occurrences` mislabeled):
  **REFUTED** — the archived function returns exact unfolded counts.
- Production audit (8 areas): sharing-aware flattening, memo_by_uid, build
  memo, executed-op accounting, CSE baseline — CONFIRMED; persistent path,
  compact interning, serde — CONFIRMED-WITH-CORRECTION (fixes landed).
- **Corrected E3** (192 formulas, exact semantic support, stable seeds,
  overwrite-safe; corpus SHA-256
  `8a6da87cc8b13f6123cb11adfa77b5d69bcd0a086666abea7df633ef92f6e68a`):
  kernel-boundary cm/cse geomean **0.888 [0.876, 0.899]** (strata 0.871 /
  0.869 / 0.925; medians 0.90–0.93; round-robin agrees within ~2%).
  Mechanism corrected: executed-op ratio median **1.000** (semantic rewrites
  rarely compress real work); the edge is n-ary instruction merging
  (instruction-ratio geomean 0.693, r=0.824 with kernel ratio); vs
  CSE+sharing-aware-flatten the gap closes to **0.985**. Prep 4.30× CSE;
  break-even median 78.5 evals; 30/192 never break even (impeqv/tree-heavy).
  Scope: one local box, this synthetic generator only.
- Claim disposition: V4 C1 superseded again (cite only the corrected
  statement); 128×/240× retraction stands; compile-scaling and schedule
  claims retained; BDD boundary out of scope.

## 3. Commands (verification set)

```powershell
# full suite (system Python 3.10)
New-Item -ItemType Directory -Force C:\Users\brian\Documents\CM_Computation\tmp\pytest_cm_review | Out-Null
python -m pytest C:\Users\brian\Documents\CM_Computation\tests -q --basetemp C:\Users\brian\Documents\CM_Computation\tmp\pytest_cm_review

# adversarial probe, output redirected (do NOT run the probe directly; it
# writes the archived filename)
# see scratch wrapper pattern in the audit report §1/F5; or:
#   import the probe module, set OUT to a new path, call main()

# corrected E3 — regenerate/verify (writes refuse to overwrite by default)
C:\Users\brian\Documents\CM_Computation\.venv\Scripts\python.exe C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_e3_corrected_2026_08_02.py --per-cell 8 --out-dir <FRESH_DIR>

# corrected E3 — measure from the frozen corpus without regenerating
C:\Users\brian\Documents\CM_Computation\.venv\Scripts\python.exe C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_e3_corrected_2026_08_02.py --corpus C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\CM_gap_e3_corrected_corpus_2026_08_02.jsonl --out-dir <FRESH_DIR>

# consolidated validation probe (F1–F7 + gate evidence) — REDIRECTED RUN ONLY
# (2026-08-03 amendment: never pass --overwrite against the archived JSON.
#  Import the module, point OUT at a fresh path, then call main([]):)
#   import importlib.util, pathlib
#   p = r"C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\cm_gap_consolidated_validation_probe_2026_08_02.py"
#   spec = importlib.util.spec_from_file_location("vprobe", p)
#   m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
#   m.OUT = pathlib.Path(r"<FRESH_DIR>\cm_gap_consolidated_validation_rerun.json")
#   m.main([])
```

## 4. Unresolved risks

- blake2b-128 digest collision assumption in the persistent IR cache
  (documented, no equality fallback — a collision would serve a wrong
  compile; accepted and stated).
- Re-associated (as opposed to commuted) associative chain variants remain
  separate splice-guard classes (pre-existing, measured limitation).
- E3 evidence is single-machine and generator-scoped; nothing external.
- The working tree is uncommitted; nothing here is on `origin/main` yet.

## 5. External work requiring authorization (prepared, NOT executed)

- **EPFL benchmark download** (`git clone --depth 1
  https://github.com/lsils/benchmarks.git external/epfl-benchmarks`, ~50 MB)
  → cone extraction plan + stop rules in
  `CM_GAP_FINAL_REPAIR_AND_E3_2026-08-02.md` §External work.
- **Pod replication (E8 gate)**: 5 × cpu3c pods, frozen corrected corpus +
  driver, ~5 pod-min each, <$1; worker-redeploy note in
  `CM_LATENT_FIXES_2026-07-23.md` applies.
- **Commit/push** of the working tree (Brian's call). Suggested decomposition:
  1. `fix(cm): structural adoption for foreign nodes in compact interning` —
     `cm_ir.py` (F4 hunks) + `tests/test_foreign_node_interning.py`
  2. `fix(serde): reject unreachable v2 definitions; document accepted input`
     — `cm_expr_serde.py` + `tests/test_expr_serde_v2.py`
  3. `docs(cm): state persistent-digest collision assumption` — `cm_ir.py`
     docstring hunk (or fold into 1)
  4. `bench(e3): corrected corpus generator with semantic-support admission`
     — driver + safety/determinism tests
  5. `bench(data): consolidated audit, erratum, corrected E3 artifacts` —
     `deliverables_n22_24\*` new files

## 6. Prompt for the next session (copy from here)

> Independently review the consolidated corrective pass in
> `C:\Users\brian\Documents\CM_Computation` (branch `main`, HEAD `4c51429`,
> uncommitted working-tree changes are part of the review surface — do not
> discard them). Read
> `deliverables_n22_24\CM_GAP_MASTER_HANDOFF_2026-08-02.md` and
> `deliverables_n22_24\CM_GAP_CONSOLIDATED_AUDIT_AND_ERRATUM_2026-08-02.md`
> first, then the file index. Prefer refutation: (1) re-verify the F4 fix in
> `cm_ir.py` (`_adopt_foreign`) — hunt for remaining foreign-node or id-reuse
> holes, including under the persistent subtree regime and LRU eviction;
> (2) attack the corrected E3 corpus generator
> (`deliverables_n22_24\cm_gap_e3_corrected_2026_08_02.py`): check semantic
> support exactness, seed stability under PYTHONHASHSEED, admission-rule
> correctness, and whether any statistic in
> `cm_gap_e3_corrected_results_2026_08_02.json` is irreproducible from the
> frozen corpus (use `--corpus … --out-dir <fresh>`; never write over the
> archived artifacts); (3) audit the claim disposition in the consolidated
> report against the raw numbers; (4) check the erratum for completeness
> against the historical reports it corrects. Rules: benchmarks with
> `.venv\Scripts\python.exe`, tests with system Python 3.10 and a
> workspace-local `--basetemp` whose parent exists; no commit/push/amend/
> reset; do not edit historical reports or result artifacts; do not download
> EPFL data or start pods; preserve untracked files. Deliver a findings
> report (CONFIRMED/REFUTED per item) as a NEW file
> `deliverables_n22_24\CM_GAP_CONSOLIDATED_REVIEW_<date>.md` and end with
> READY / REVISE / BLOCKED.

## 7. Status

**READY FOR INDEPENDENT REVIEW**
