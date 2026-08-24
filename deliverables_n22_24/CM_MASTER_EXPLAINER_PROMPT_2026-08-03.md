# CM Master Explainer & Display Build — Prompt for a new agent session (2026-08-03)

Copy-paste everything below into a new session.

---

## PROMPT

Act as a science-communication + data-visualization agent for the CM
(Correspondence Matrices) project. Your deliverable is a **master
knowledge-base webpage** — one comprehensive, self-contained HTML site (a
"master file") that presents the entire CM story at every level of depth:
what Boolean computation is and where it shows up, what each tool/method
solves, which is better when (with charts supporting each scenario), what
CM is and what it is not, the full refreshed evidence, honest limits, and
the open problems. It must be written in layered depth so that shorter
audience-specific versions (layperson one-pager, investor brief, expert
technical summary) can later be cut from it without re-research — build
those three derived versions too, as separate shorter pages, pulling only
from the master.

Do not re-run benchmarks. Never modify committed evidence or archived
reports. Write everything to `deliverables_n22_24\master_explainer_2026_08_03\`
(new directory). `COMMIT_PUSH_APPROVED = NO` unless Brian states otherwise.

**Repository:** `C:\Users\brian\Documents\CM_Computation`, branch `main`
(evidence through commit `6e8a283`). Data prep with
`.venv\Scripts\python.exe`. Record `git rev-parse HEAD` first. If
`deliverables_n22_24\displays_2026_08_03\` contains prior display-agent
output, review it and reuse/extend rather than duplicating.

### Source hierarchy (read in this order)

**1. Narrative source — the slide deck PDF (structure and prose, NOT numbers):**
`C:\Users\brian\Downloads\Correspondence-Matrices-A-Structural-Layer-for-Boolean-Computation (14).pdf`
(57 pages; read in ≤20-page chunks). This deck is excellent for: the
three-act narrative arc (the fragmented Boolean ecosystem → what a CM is →
what experiments show), the application-domain map (AI reasoning, formal
verification/EDA, SAT, rule engines, security policy, feature flags,
computational biology, knowledge graphs, compilers, hardware synthesis),
the "CM represents / BitSet executes / CUDD canonicalizes" framing, the
nominal-n vs live_k explainer, the structural-compilation pipeline, the
implemented-vs-formal-vs-future capability separation, the glossaries, the
claim-boundary and statistical-interpretation appendices, and the
priority-experiments list. **REUSE its structure and honesty conventions;
DO NOT reuse its numbers** — it is frozen at Audit V4 (2026-07-24) and
many of its results are superseded (notably: "CM 0.944/0.925 at controlled
live_k=16", the 8–12 "near crossover", 49-formula corpus stats, 194 tests,
and all V4 C1-derived wrapper claims).

**2. The authoritative number map — which deck claims survived:**
- `deliverables_n22_24\CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md`
  (16 claims: CONFIRMED / REVISED / SUPERSEDED, with slide guidance)
- `deliverables_n22_24\CM_BENCHMARK_REFRESH_CLAIM_MAP_ADDENDUM_2026-08-03.md`
  (engine-crossover REVISED to workload-dependent; CUDD best-of-10 and
  reordering rows closed with data)
- `deliverables_n22_24\CM_BENCHMARK_REFRESH_HANDOFF_2026-08-03.md`
  (campaign overview + the four-point "headline story for the rebuilt deck")
- `deliverables_n22_24\CM_GAP_CONSOLIDATED_AUDIT_AND_ERRATUM_2026-08-02.md`
  (corrected-E3 definitions, erratum, supersession discipline)
- `deliverables_n22_24\CM_GAP_POST_ACCEPTANCE_OPTIMIZATION_DECISION_2026-08-03.md`
  (Outcome A — kernel-equivalence — now FINAL; ranked next tests)

**3. Refreshed evidence (every chart's numbers come from these files, re-read
programmatically, never retyped from prose):**
- Kernel headline: `b1_e3_replay_2026_08_03\cm_gap_e3_corrected_results_2026_08_02.json`
  (0.8876 [0.873, 0.902] vs plain CSE; ≈parity vs CSE-flat)
- External validation: `cm_gap_epfl_results_2026_08_03.json`,
  `epfl_run_2026_08_03\cm_gap_epfl_analysis_2026_08_03.json`
  (EPFL real circuits: 0.9998 vs CSE-flat; 0.927 vs plain CSE;
  per-circuit table; verdict SUPPORTS GENERALIZATION),
  report `CM_GAP_EPFL_VALIDATION_2026-08-03.md`
- Cross-platform: `b6_pod_replication_2026_08_03\b6_analysis_2026_08_03.json`
  (5 pods, 0.877–0.888, REPLICATION PASSED)
- Wrapper boundary (REVISED story): `b2_wrapper_2026_08_03\…results…json`,
  `b4_sweep_2026_08_03\…results…json` (BitSet leads at all live_k ≤ 16)
- Guard/decline: `b4_sweep_2026_08_03\CM_b4_guard_summary_2026_08_03.csv`
- Compile scaling: `b3_scaling_2026_08_03\cm_b3_scaling_results_2026_08_03.json`
- Engine crossover: `bx1_crossover_2026_08_03\cm_bx1_crossover_results_2026_08_03.json`
  (flat fastest through k=12; words wins at k=16 — workload-dependent)
- CUDD matched + orders: `b5_cudd_2026_08_03_run5\cm_b5_cudd_matched_results_2026_08_03.json`,
  `bx2_cudd_orders_2026_08_03\cm_bx2_cudd_orders_results_2026_08_03.json`
  (construction vs evaluation kept separate; extraction 74×–12,800× slower
  than words kernels; best-of-10 −21–30% nodes at ~8–10× search cost;
  reordering never triggers ≤78 nodes; NOTE the build-window convention
  differs between B5 and BX2 — never mix in one chart)
- Costs/provenance: `cm_benchmark_refresh_manifest_2026_08_03.json`
- Per-leg reports (captions/prose): the `CM_B*_…REPORT…md` files in each
  evidence directory listed above.

### Required master-page content (layered: every section has a
plain-language paragraph FIRST, then the technical layer, then the chart)

1. **Why Boolean computation matters** — rebuild the deck's domain map as
   an interactive/annotated figure; for each domain, one lay sentence on
   what the computation solves (e.g., "does this configuration ever allow
   X?", "are these two circuits the same?", "which rule fired and why").
2. **The toolbox and what each tool solves** — BitSet, ROBDD/CUDD, SAT,
   Espresso, SymPy, structural CSE, CM — one card each: what question it
   answers, its superpower, its cost, a lay analogy. Keep the deck's "no
   single blended speed ranking is meaningful" discipline.
3. **What a CM is** — the truth-table vs CM view, nominal-n vs live_k
   explainer (the x2 AND x17 example), the operator-calculus framing, and
   the implemented / formal-but-unvalidated / future separation exactly as
   the deck draws it.
4. **Which is better when** — the heart of the page. One subsection per
   scenario, each with its supporting chart from the refreshed data:
   - evaluate one formula once → BitSet (wrapper charts, B2/B4);
   - evaluate the same formula thousands of times → kernel-level story +
     break-even distributions (B1/EPFL: median 78.5 synthetic / 174.5
     external, 55/129 never — reuse count is the decision variable);
   - tiny vs medium vs large support → engine crossover chart (BX1) and
     the guard boundary at live_k=16;
   - need canonical form / equivalence / compact symbolic object → CUDD
     (B5/BX2 two-panel: construction vs evaluation; extraction economics);
   - real circuits → EPFL results and what "kernel-equivalent to CSE-flat"
     means in practice;
   - a plain-language decision flowchart summarizing the above.
5. **The current computational problem / open frontier** — what remains
   genuinely unsolved: prep cost (4.1–4.3×) as the top optimization
   surface; validated backend selection (BX1 shows a k-only rule leaves
   2–5× on the table); canonical CM equivalence (formal, not demonstrated
   — carry the deck's caveat verbatim in spirit); cross-expression reuse;
   the deck's three CM-value experiments (related-expression families,
   repeated partial contexts, operator difference/quotient) with their
   success/failure interpretations; real-workload validation. Frame
   honestly: what would change the picture if it succeeded or failed.
6. **How we know — evidence quality** — the audit chain (V3→V4→gap
   repair→corrected E3→independent replication→external validation→
   cross-platform), packed-equality discipline, pre-registration, the
   statistical-interpretation rules (clustering, schedules never pooled),
   and the corrections ledger (0.843, 128×/240×, "ahead at 12/16" —
   presented as corrections of record, a strength of the project).
7. **Glossaries** — extend the deck's two glossaries; add lay definitions.
8. **Audience versions** (separate pages derived from the master):
   layperson (no numbers beyond a couple of vivid ones, analogies, the
   decision flowchart); investor (the problem's breadth, the honest
   evidence chain as credibility, what's proven vs open, the roadmap);
   expert (dense: all charts, CIs, protocols, file provenance).

### Build rules

- Self-contained HTML (inline CSS/JS, embedded data arrays generated by a
  Python build script that reads the source files — commit-grade
  regenerability; include the script). Light/dark friendly. Every chart
  carries: scope label (synthetic generator / EPFL AND/INV cones / pod
  platform / local box), clustering basis of any CI, and a source-file
  footnote. live_k on the x-axis, never nominal n.
- Superseded numbers appear ONLY inside the corrections ledger, marked as
  such. Blocked vs round-robin labeled, never pooled. Construction vs
  evaluation never merged into one ranking. "Kernel-equivalent" language
  for CM vs CSE-flat everywhere (the ≈1.5% residual is not a win).
- Lay layer quality bar: a smart non-programmer should finish section 4
  able to answer "when would I want each tool?" without jargon.
- End with a build report: page inventory, every chart → source file map,
  any claim-map row not visualized and why, and a suggested review order
  for Brian.
