# Gate A: Contract Alignment and Pre-Freeze Qualification

Brian Theory · 23 September 2026 · Independent source reconstruction and prospective qualification.

## A. Gate verdict

**NO-GO — PRE-FREEZE BLOCKERS REMAIN.**

The finite Boolean core and the tested boundary behaviors pass. The live implementation is a **pair-root compiler**, uses **syntactically occurring unfixed variables**, and materializes **all ambient dense axes**. The original manuscript and v3 do not express all of these contracts consistently. Working-copy repairs are supplied; they are not a frozen experiment.

The remaining blockers are a missing named compiler deep-audit artifact, uninstantiated natural/secondary corpus provenance, incomplete source-qualified endpoint/harness/cache/memory adapters, uncompleted pilot/freeze validation, and adoption of the successor protocol and revised manuscript as one immutable package. No confirmatory performance experiment or timing pilot was run. No confirmatory performance results were opened. Previously printed P14 wording was checked solely for the requested contamination boundary.

## B. Source identity

Repository: https://github.com/Relative0/Correspondence_Matrices

Live remote HEAD and audited commit: **`0ab8ffd0c23ffa71ee951d375b1c170ffdcc084b`**. The live sparse checkout was clean at initial and final Git status/diff checks. The tested source is a 187-file isolated dependency closure; **every file was verified against the exact Git blob at that commit**, then SHA-256 hashed. No production source was edited. New tests and analysis are external, independently hashed overlay artifacts. This avoids falsely presenting a dirty local checkout as the live commit.

The existing `C:/Users/brian/Documents/CM_Computation` checkout is based on `9a8ec9172fa1ba841c7960d088b94ef04c67c9b8` and is dirty. Relevant modifications relative to its own HEAD include `cm_build_pair.py`, `cm_token.py`, `bitset_backend.py`, and `tests/test_bitset_backend.py`; the complete tracked status, diff stat, scoped patch, and 192 untracked source/protocol filenames and hashes are retained in evidence. Some dirty changes are already present upstream; dirty-relative-to-local-HEAD is not the same as different-from-live. Live/local byte and normalized comparisons are separate. The old `Documents/Correspondence_Matrices` directory is a different, older implementation and was not used for tests.

Identity artifacts:

- `evidence/source_identity.json`: commit and source-manifest digest.
- `evidence/source_files.json`: every snapshot path, Git blob, SHA-256, byte count.
- `evidence/local_status.txt`, `local_diff_stat.txt`, `local_relevant_vs_HEAD.patch`, `local_relevant_untracked.json`, `local_vs_live.json`: complete scoped local provenance.
- `evidence/input_artifacts.json`: manuscript, companion, review/memo PDF/TEX/Markdown bytes and hashes; the extra standalone Downloads TEX is recorded separately, not silently substituted.
- `audited_source_snapshot.zip`: reproducible exact source closure, with no results corpus.



| Audited file | SHA-256 (exact Git-blob bytes) |
|---|---|
| cm_build_pair.py | `0adba18172baf5b34907d778959d300849b01890960a3843fea6e880ae9048af` |
| cm_token.py | `73101e8090ab9083b22fa97302333246d8830ba63e379d6baa31bf6da9365d39` |
| cm_normalize.py | `11007044c363b2539bd75702fea68b27f500078ac82dd6d09d4b0c6a41416e85` |
| cm_build.py | `4411eb26ffd2834055b5d2b5d06f59ce774abb8f2180d000de8ad19c1c304fe8` |
| cm_ir.py | `928769bb7246717f74f8328fcba8d17f6f0a6508ad7bc27972ca6dec21a3d9b2` |
| bitset_backend.py | `d187c4301231a3a6b2fd1c9bc19fdf5e0bbfadbc486724841a3027b8a0c3f4a5` |
| cm_exprlib.py | `2dae42d07256c8f6b01a4ef054cc35658544607c0338f5a4a8dac76629fbdac1` |
| cmbench/output_budget.py | `d38fafd347d31b56c695e36f89a1f8522322d2a8e5514214d63af6b3644a216b` |

Original Protocol v3 SHA-256: `54039d0c2ce26a8e9f81dbd6eb60cba6fa093335d1d049afbf6f8269182cdc1f`. No v4 successor existed in the inspected live audit directory.

Inputs inspected: both requested manuscript PDF/TEX pairs, panel audit, rules-update notes, revision memo, R1, R2, response to R2, actual v3 and `PAIR_COMPILER_CONTRACT.md`, source and focused tests. The named `CM_Compiler_Deep_Audit_2026-09-22.md`/PDF was not found in the package, live audit directory, or scoped local artifact search. `CM_LM_Audit_Astra.md` is a foundations audit and is not a substitute. Its presence does not satisfy the missing-input requirement. Companion scope and numeric contract agree; no companion edit was made. Its draft-status paragraph refers to the earlier combined computational manuscript; a future explicit historical qualifier is editorial, not a compiler algorithm repair.

Source references below use audited snapshot paths and line numbers. Manuscript references use original TEX section/line locations, so they remain interpretable after working-copy changes. Protocol references are v3 headings/lines. Exact replacement text is in the patch.

## C. Manuscript–source–protocol contract matrix

| Concept | Manuscript says | Source actually does | Protocol assumes | Agreement? | Required action |
|---|---|---|---|---|---|
| Canonical frame | §§2–4: distinct canonical R,C | `cm_build_pair.py:230,269`: one distinct unfixed variable from each disjoint layout; names checked at fusion | Arms/order, v3:30 | Yes for valid inputs | Preserve explicit order and axis names |
| Signed primitive | §4.2: supported connective over signed literals | :230 strips finite NOT chains; rejects fixed primitive variables; swaps/flips token | Pure arm | Yes | Keep five operations and all eight signed frames |
| S | §4.1: structural ancestry only | :304 primitive, NOT, fusion, zero retained tabulations | Pure outcome | Yes | Native root mapping tested |
| T | §4.1: directly tabulated root | :391 / :444 returns structural_steps=False, one tabulated subtree | Whole-root outcome | Yes, needs discarded-work qualification | T describes returned derivation, not absence of prior failed work |
| H | §4.1: structural step above tabulation | :334,361 set structural_steps=True and carry/sum tabulations | Hybrid arm language overconstrains requested hybrid | Partial | Separate request from outcome; all 9 fusion combinations tested |
| Provenance combination | §4.2: p sqcup q | S,S→S; every other pair→H | Implicit | Semantics agree; notation misleading | Use mu; T,T→H is non-idempotent |
| Pure strategy | §4.2: no tabulation | :506 passes allow_local_retabulation=False; no scalar tabulator called | Pure arm | Yes | Monkeypatch prohibition regression retained |
| Hybrid strategy | §4.2 structural plus local tabulation | :515 allows S/T/H/NoPair | v3 arm row says root must hybrid_pair | No for general calls | v4 makes hybrid request distinct from H outcome |
| Whole-root retabulation | §5.2 admitted root tabulated | :444; public :489 statistics plus second discovery, four scalar traversals | V3 prose suggests discovery and four evaluations | Partial | Charge both passes; distinguish explicit ablation from hybrid T |
| Ordinary fallback | §5.2 token top level “or ordinary IR” | :473 signals; :550 executes original-root fallback via :283 | v3 ordinary row conflates signal and execution | No | Separate disposition and fallback_executed |
| NoPair | §5 pseudocode no-pair | None plus metrics; no dense allocation or ordinary compiler | Not fully separated from fallback | Partial | Valid NoPair is not exception or delivered truth output |
| Invalid layout | §4.3 grouped outside pure rule | :52 duplicates/overlap raise ValueError before token compilation | Out-of-domain stratum ambiguous | No | Invalid request disposition; boundary tests both APIs |
| Fixed variables | §4 invariant after F | Pair excludes fixed canonical names; scalar env precedence harmless on admitted pair | Equal fixed mappings all arms | Partial | Explicit apply-F-then-live-axes; packed ambient adapter required |
| Live-support definition | §4.2, lemma says support | :269 computes sorted syntactic FV minus fixed keys; no dependence minimization | “live support” | No | Define FV_F; retain canceled syntactic names |
| Child-fold retention | Intro/§5 pipeline can imply local rewrite into general IR | :304 returns only Pair/None; :283 receives original expression | Ordinary original-root row mostly correct | No/ambiguous | Identify pair-root; discard speculative tokens; no persistent rewrite claim |
| Token ordering | §§2,5 true-first | `cm_token.py:45` bit shift 2r+c; token MSB (11,10,01,00) | V3 masks x0=12,x1=10 | Yes | Exhaustive check all 16 |
| Dense ordering | §5.3 false-first | :174 conversion, `cm_normalize.py:124` axis lift, IR materialize | V3 output equality implicit | Partial | Explicit list-order/MSB layout and digest |
| Output axes | Table1, §5.4 requested unfixed axes | All declared axes, including fixed/absent, preserved; shape 2^len(rows) by 2^len(cols) | v3 dense wording lacks axis contract | No, blocker | Contract A; n_out=ambient count; adapters match |
| Output ownership | §5.3 owned output | `lift_cm` and `materialize_cm` end in copy; writable owned bool | Allocation/copy charged | Yes | Public ownership and nonaliasing tests pass |
| Diagnostics | §5/general proof suggests typed provenance | Native dictionary root_outcome/counters; requested strategy not returned; dense diagnostics only passed to fallback | v3 requests more counters/phase timings than API supplies | Partial | Harness records request; untimed wrappers for missing counters; do not invent zero phase costs |
| Compiler-call counts | §5 N/U/H distinguished | Recursive calls, not all AST nodes; recognized primitive stops at its literal children | v3 explicit compiler_calls | Yes with clarification | Shared primitive compiled twice when referenced twice |
| Unique nodes | §5 sharing-aware caveat | :67 iterative identity DAG stats, U distinct object identities | v3 U=N primary | Yes | Preserve identity serialization, not structural hash alone |
| Shared DAG handling | General IR DAG can imply compiler reuse | Stats share identities; recursive pair compiler does not memoize; direct packed does | Sharing cells required | Partial | Distinguish N work from U stats; equal-distinct tests |
| Token query | §7 shared lookup but later reuse language loose | `cm_token_value` same routine for both producers | Common query explicitly required | Partial | Same q means no ordering reversal by K |
| Cache state | §7 preparation separated | Import LUTs, composition LRU, index/lift LRUs, env and IR/program caches | v3 clears packed env but warm-up may repopulate; other resets absent | No | Complete v4 cold/prepared policy; source-qualified runner required |
| Explicit output | Table1 says 2^n bits | Bool dense uses 2^n_out payload bytes; token/packed/object sizes distinct | Output bytes required | No units/axes | Report bits versus payload/allocation bytes separately |
| Output budget | §5 exponential boundary | :566 checks len(R)+len(C) before pair attempt; fallback disables redundant inner budget | v3 budget permitted unspecified | Partial | Common 64 KiB/16-axis secondary dense policy; reject before any arm; heuristic temp bound disclosed |
| Fixed/env overlap | Same substitutions assumed | `bitset_backend.py:65` env wins, ordinary IR fixed wins | Equal arms | No if called naïvely | Ambient adapter overwrites fixed masks; retained raw counterexample |
| Primary statistic | §7 “median ratio” | No source-qualified confirmatory analyzer bound to manuscript | v3:177 hierarchical interval without levels/counts | No | V4 defines 100 cases, 30 repetitions, median of ratios of medians and paired bootstrap |
| Secondary inference | No exact family | No bound analysis implementation | v3:207 “intervals or tests” BH | No | Withdraw undefined inference; descriptive pointwise intervals only in v4 |
| Natural provenance | Open empirical gap | No selected source-qualified corpus attached to gate | v3:84 requires provenance before pairability | Not qualified | Populate manifest before pair runs; retain full intake denominator |

## D. Blocking discrepancy ledger

Severity P0 = blocks freeze; P1 = required documentary repair supplied in working copy but not adopted. “Repaired” below means revised artifact provided, not authorization to freeze.

| ID/severity | Source location | Manuscript location | V3 location | Observation and correct interpretation | Required fix/status |
|---|---|---|---|---|---|
| D01 P0 | pair :283,304,550 | Intro:98; figure:210; pseudocode:471; discussion:634 | Arms:30 | No general-IR persistence; root failure discards child pairs | Retain pair-root architecture; narrow wording/diagram. Working-copy patch supplied; no new optimizer implemented |
| D02 P0 | normalize :124; IR :1970; pair :566 | Table1:434; cost:488,496; limitation:662 | Output:101 | Fixed/unused axes remain; eight-byte example contradicts reduced-axis wording | Contract A supplied throughout working copy and v4; freeze adapter needed |
| D03 P0 | bitset :65; pair :269; IR materialization | Invariant:264; layout §5.3 | Correctness:137 | Raw env overlap ignores fixed; compare with explicit fixed-first ambient adapter | Reference adapter passes regression; integrate and hash in actual harness |
| D04 P1 | pair :269 | Tabulation:316,324; lemma:399 | Workloads:55 | FV_F is syntactic, not essential support | Exact FV_F definition and cancellation examples supplied; no semantic minimization added |
| D05 P1 | pair :52,473,550 | §4.3; top-level pseudocode | Arms:30 | Invalid, NoPair, and executed fallback differ | Separate raw dispositions and API descriptions supplied |
| D06 P1 | pair :409,489–547 | Provenance §4 | Hybrid arm:37 | Requested hybrid may return pure/T/H/NoPair; metrics omit request | V4 schema logs both; no relabeling/filtering |
| D07 P1 | pair :334,361 | Rule:310,313 | Hybrid outcome | T,T combines to H; “join” violates idempotence | mu notation and total table supplied |
| D08 P0 | pair :67,304,391; token LRUs; bitset/IR caches | Cost:488–496; implementation contract cost table | Caches:101; sampling:156 | O(H) auxiliary claim omits O(U) structures; v3 warm-up/cold contradiction; support and fallback work not fully instrumented | Correct complexity and full cache policy supplied; untimed diagnostic wrappers and reset-asserting runner still required |
| D09 P0 | No completed frozen harness/analysis identity | Primary paragraph:560 | Primary:177–209 | Formula count, bootstrap units, memory aggregation and failure denominator underspecified | V4 and primary_analysis.py supplied; full runner/schema validation and manifest integration outstanding |
| D10 P0 | No identified fixed natural corpus/tool closure | Natural-workload gap | Natural:84; freeze:211 | Cannot determine immutable natural population or AIG subset; pairability not measured | Populate provenance/extraction/license/source hashes before selection-dependent compilation; no convenient substitute corpus used |
| D11 P0 | Missing supplied artifact | Revision history | Input gate | Named compiler deep audit absent | Obtain exact report or explicitly resolve its absence before declaring all required inputs reviewed |
| D12 P1 | N/A; printed P14 only | P14:600 | Evidence boundary | Synthetic interval includes 1; “5.1% slower” overstates establishment | Changed to slower by point estimate; numbers/aggregation untouched |
| D13 P1 | Common token query | Reuse:558,644–650 | Query:110 | Equal q cannot reverse setup ordering | Exact T(K) difference and ratio-to-parity statement supplied |
| D14 P0 | Analysis not previously bound | Primary/evidence descriptions | BH:207; threshold:201 | BH does not automatically adjust CIs; ratio1.20 is 16.7% lower time | V4 descriptive secondary policy and exact threshold interpretation; adoption required |
| D15 P0 | Live/local identity divergence | Historical test counts:567 | Freeze source requirements:211 | Old local SHA + dirty changes differ from live; historical counts do not qualify current code | Exact clean live blob snapshot + overlay hashes supplied; final combined source/harness/corpus freeze still absent |

## E. Implementation-boundary report

### Public call reconstruction

`compile_expr_to_cm_pair_token(e,R,C,fixed,strategy='hybrid')` validates duplicate/overlapping axes, then traverses the identity DAG for variables, unfolded occurrence count N, unique count U, and height H. It discards the variable list but keeps metrics. Unknown strategy raises ValueError after this pass; unknown nodes raise TypeError. Malformed input outside the declared finite DAG grammar has no totality guarantee. No runtime Boolean-value type validation is promised; fixed values are coerced by bool in evaluators. Use the stricter v4 input schema.

`pure_structural` attempts a signed primitive first. Recognition peels NOT chains and excludes literals in fixed. It normalizes tokens by operand swap and row/column flips. If not primitive, NOT recursively compiles its child; binary nodes recursively compile both children (including the second when the first fails), then fuse only matching canonical frames. Variables alone return None. Pure never invokes the scalar tabulator.

`hybrid` uses the same path; after unsuccessful structural assembly of a non-variable node it discovers syntactic variables again. If exactly one unfixed row variable and one unfixed column variable remain and no other live names occur, it evaluates the entire subtree four times, creating T. Successful descendants from a failed attempt may already have incurred cost and counters; a later root tabulation does not retain those descendants. A subsequent structural NOT/fusion above T yields H. Root T is not synonymous with “the only work was four passes.”

`retabulate` bypasses recursive pair construction, but does not bypass the initial statistics pass: it performs another discovery pass, one admitted pair attempt, then four scalar evaluations. compiler_calls=0 does not mean no work. If ineligible it returns NoPair with pair_attempts=1, unlike recursive metrics. In the audited live commit, legacy nodes_total=compiler_calls; the dirty local copy instead sets nodes_total=ast_occurrences. Both expose a separate ast_occurrences field. The boundary regression locks the live meaning. pairable_ratio=collapses/compiler_calls when calls>0, otherwise0. Neither legacy field is a cross-strategy success probability.

Return is `(CompiledPairToken(row_variable,column_variable,token), metrics)` or `(None,metrics)`. The public token artifact has no provenance field; provenance is in metrics. The token API never calls ordinary compilation or allocates dense output. Statistics arrays/maps and transient pair objects are real allocations. The native dictionary does not report requested_strategy, support-discovery pass count, scalar visit count, discarded-pair count, or all phase times.

`compile_expr_to_cm_pair(...)` first enforces the ambient dense output budget, then calls the token API with pair_strategy. If pair succeeds, it creates a false-first 2x2 uint8 matrix, casts/lifts to ambient Boolean axes, broadcasts and copies to an owned writable matrix. If pair fails, `_fallback_compile` calls ordinary `compile_expr_to_cm` on **the original expression object**, not rewritten children. Ordinary compilation builds an interned/simplified IR and materializes it, applying fixed substitutions and reinserting ambient axes. The wrapper has already checked output budget; the nested ordinary call receives output_budget=None. Caller diagnostics are passed to fallback, not filled symmetrically by the successful pair lift; raw schema must not treat missing values as zero cost.

Dense materialize_mode/hybrid_threshold govern ordinary fallback only. An invalid strategy/layout may be preceded by output-budget refusal in the dense wrapper because budget validation occurs first. Tests use admitted small layouts to isolate invalid-input behavior.

### Concrete boundary observations

- `(R XOR R) XOR C`: hybrid T, token10 (function C), despite essential support only C. FV_F contains R,C.
- `(R AND C) XOR (Z XOR Z)`: FV_F includes Z; root NoPair despite function R AND C. A child pair is constructed then discarded.
- `R AND C`, rows `[R,Z]`, cols `[C]`, Z=1: shape(4,2), dtype bool, eight bytes, `[[0,0],[0,0],[0,1],[0,1]]`. The budget estimator correctly counts all three axes.
- Fixed-only expression: no pair; dense fallback can return shape(1,1), or repeat the constant across declared axes.
- Fixing canonical R or C prevents that pair; it does not accidentally overwrite the fixed value with four-assignment tabulation.
- `Or(And(R,C),Z)`: one primitive child pair, three compiler calls, NoPair; token API executes no fallback; dense executes original-root ordinary compiler exactly once. Child-pair counters survive; child tokens do not.
- Identity-shared `Or(s,s)` and equal-distinct `Or(S(),S())`: N=7 both, U=4 versus7, compiler_calls=3 and primitive_pair_tokens=2 both. Pair construction has no identity memoization; direct packed evaluation has it.
- `Or(And(R,C),Z)` with fixed Z=1 still has syntactic FV_F={R,C}, returns T token15. Constant functions need not be rejected if the syntax retains two live names.

**Recommendation:** retain architecture A and narrow the paper. Persistent local rewriting or essential-support minimization would be material new optimizations with new source identity, tests and a successor protocol. Neither was introduced.

### Complexity and caches

Let C_p be recursive calls, L signed-literal negation scans, D the discovery passes, and T the retabulations. With fixed-size layouts/names, a faithful bound is

`O(U + V log V + C_p + L + sum_D(U_v + V_v log V_v) + 4 sum_T N_v)`.

Membership uses layout lists, so varying layout sizes add membership factors. Scalar four-pass evaluation unfolds shared occurrences; direct packed memoization uses U. For the pure two-variable fragment, token time O(N), auxiliary O(U+H), including initial DAG statistics. Hybrid rejected-support rescans can be quadratic for bounded variable vocabulary; conservative tree bound with name sorting is O(N² log N). Counts on a highly shared DAG use O(log N)-bit integers, so unit-cost count arithmetic is a stated convention. Peak auxiliary storage is O(U+H+V), plus caches, not O(H) alone. Dense output adds Theta(2^n_out) time and bytes; ordinary fallback adds its own backend work to all failed pair-attempt work.

Relevant caches: five import-time 16x16 LUTs; `cm_compose` unbounded decorator cache (at most1280 normal compiler token/op keys); four normalize permutation/lift LRUs; packed environment LRU256; words environment LRU4 and constants LRU8; IR compiled-root4096, persistent16384 and alignment LRU; per-builder interning; per-call evaluator memos; AST/IR-attached programs and node statistics; FlatProgram bound FIFO64, word plan and thread-local scratch widths; benchmark-context masks/layouts/truth tables; native BDD/AIG managers. V4 enumerates exact cold/prepared treatment. A verified runner implementing it is still required. Import-resident LUT cost is disclosed rather than secretly assigned to another arm.

## F. Mathematical re-verification

The independent finite oracle uses direct bit extraction and elementary Boolean scalar operations, not the CM query routine to generate expected values. Script: `finite_core_check.py`. Current counts, not historical counts:

| Check | Equality assertions | Failures |
|---|---:|---:|
| One-hot XOR–AND selection over16 tokens×4 assignments |64|0|
| Shared query bit convention |64|0|
| Transpose, row flip, column flip |192|0|
| Output complement |64|0|
| All16 tokens×8 signed frames×4 assignments |512|0|
| All16² token pairs×5 outer fusions×4 assignments |5,120|0|
| Independently signed token pairs×5 fusions×4 assignments |327,680|0|
| All16 tokens constructed by pure/hybrid/retabulate |48|0|
| Corresponding expected provenance |48|0|
| Worked implication expression and complement |2|0|
| **Total** |**333,794**|**0**|

Boundary suite additionally covers all9 provenance pairs under5 binary operations, all3 NOT provenance cases, fixed values/axes/constant roots, and discarded children. Historical manuscript counts116 and1,048,576 remain clearly historical and were not rebranded as this run. Existing project tests separately include signed primitive frames and250 random formulas.

Proof review: one-hot selection leaves exactly one term; signed transforms permute assignments; complement and same-frame pointwise fusion preserve denotation. Structural soundness follows induction over admitted primitives/NOT/fusion. Fragment completeness follows construction induction for finite acyclic expressions and fixed maps disjoint from the canonical pair, subject to runtime resource limits. Exact tabulation proves four assignments of e[F], not essential-support discovery. Hybrid soundness adds exact tabulation as an induction base. NoPair correctness is not a pair theorem: ordinary fallback depends on the separate IR evaluator. No finite test count proves unbounded completeness or a complexity theorem.

One retained interface counterexample: raw packed `And(x0,x1)` with env masks(x0=12,x1=10) and fixed{x0:1} returns8, whereas fixed-first dense semantics corresponds to10. This is the raw API's documented absent-from-env substitution boundary, not evidence against the token algebra. The adapter fixes the task mapping without changing production code. Tests assert both the counterexample and corrected equality.

## G. Regression-suite report

Interpreter: project `.venv/Scripts/python.exe`, Python3.13.5, NumPy2.3.2, pytest9.1.1, Windows. CWD is the isolated audited source closure. Exact absolute commands, PYTHONPATH, outputs and return codes are in `evidence/check_commands.json`, `project_tests.txt`, `gate_a_tests.txt`, `finite_core.txt`.

Commands (relative arguments interpreted from the recorded source CWD):

```text
python -m pytest tests/test_cm_pair_alignment.py tests/test_cm_optimizations.py tests/test_output_budget.py tests/test_bitset_backend.py tests/test_bitset_cse.py -q -p no:cacheprovider
python -m pytest <outputs>/gate_a_regressions.py -q -p no:cacheprovider
python <outputs>/finite_core_check.py
```

Final results: **147 existing tests passed; 95 new parameterized boundary cases passed; zero failed/skipped; 333,794 independent finite checks passed**. No production patch, commit or push. Tests are runnable overlay deliverables, not secretly installed in the user's dirty repository.

Initial snapshot attempt had one collection error (missing `cmbench.tracing`); adding source dependencies resolved it. A subsequent run had3 missing-helper import failures and144 passes; after adding the verified `scripts/cm_memory_estimator_study.py` dependency, all147 passed. These were snapshot packaging failures, not claimed pre-existing code defects. The latter initial output is retained. No test was dropped to obtain the final count. No performance campaign was invoked by the gate; pytest wall time is test-run metadata, not a benchmark observation.

Coverage of required17 boundaries:

| Required boundary | Added regression |
|---|---|
|1 overlap;2 duplicates | test_invalid_layouts_raise (both APIs) |
|3 syntactic versus cancellation | test_syntactic_cancellation_is_not_essential_support |
|4 fixed axes | test_fixed_and_ambient_axes, test_budget_uses_ambient_axes_before_pair_attempt |
|5 fixed-only;6 canonical variable fixed | test_fixed_only_and_canonical_fixed_no_pair |
|7 successful child, root fallback | test_token_signals_fallback_and_discards_successful_child |
|8 hybrid→S;9 hybrid→H;10 hybrid→T | test_requested_hybrid_separate_from_observed |
|11 token signal;12 dense execution | token_signals… and test_dense_executes_original_root_once |
|13 T then NOT→H | test_negation_provenance |
|14 T+T→H | test_all_nine_provenance_fusions |
|15 token/dense order | test_all_tokens_true_first_to_dense_owned |
|16 ownership/writeability | test_public_dense_ownership_independent_calls and fixed/ambient tests |
|17 shared/equal-distinct | test_identity_dag_versus_equal_distinct_instrumentation |

Additional tests prohibit scalar tabulation in pure mode, demonstrate packed overlap mismatch, verify semantic constant tabulation, common token queries, ambient budget admission, nonaliasing and fixed false/true across all strategies.

## H. Manuscript patch list

Deliverables: `Operator_Level_CM_Compiler_Gate_A_Working_Copy.tex`, compiled PDF, and `Manuscript_Gate_A.patch`. The 15-page PDF was compiled with references resolved; all pages rendered and visually inspected, including full-size rules/diagram/cost/evidence pages. No overfull-box, undefined-reference, or duplicate-destination warnings remain in the final compile. Companion source/PDF bytes are unchanged.

Exact principal replacement wording:

1. “The implementation is a pair-root compiler: child tokens are retained only when construction of the requested root succeeds. On root failure, the dense wrapper recompiles the unchanged source expression through ordinary IR.”
2. “Define FV_F(e)=FV(e)\dom(F): the syntactically occurring unfixed variables, without Boolean dependence minimization.”
3. “This is a provenance-combination function, not a lattice join: mu(T,T)=H≠T, so it is not idempotent.”
4. “A valid token request returns NoPair (Python None) and records ordinary_fallback … This signals fallback; only the dense wrapper executes ordinary compilation.”
5. “The public dense contract retains all declared ambient axes … including fixed axes … shape(4,2), eight Boolean entries occupying eight payload bytes.”
6. Cost section replaced with the source-aware N/U/H/pass-sum bound and ambient n_out. “Recursive pair construction does not memoize shared nodes.”
7. “Their total-cost difference remains C1−C2 for every K; reuse cannot reverse the preparation ordering and the time ratio approaches one.”
8. “About5.1% slower by point estimate … its reported interval includes parity and does not establish a slowdown.” P14 numbers, aggregation and intervals unchanged.
9. Primary ratio1.20 explicitly means16.7% less time. New test counts separated from historical counts. Draft status explicitly NO-GO and v4 working copy.

Statement classification: introduction's before-expansion language is narrowed to successful roots; figure previously routed generic fallback to pair output and now labels only successful tabulation; top-level pseudocode previously executed IR implicitly and now separates APIs; discussion's general local-cut optimization claim is explicitly a different architecture. Historical S1/S2 mechanism claims remain attributed to that experiment, not to retention in this pair-root source. Generic-optimizer related-work statements are comparisons, not assertions of implemented persistent rewriting. Conclusion now names discarded children on root failure. No broad LM/foundations material was added.

## I. Protocol disposition

**Protocol v4 required.** Full successor: `EVALUATION_PROTOCOL_V4_WORKING_COPY.md`. V3 preserved. Material changes: explicit ambient output/fixed mapping; request/outcome/disposition; pair-root scope; comprehensive cache/reset and warm-up policy; exact case/repetition/aggregation/bootstrap/memory rules; failure/attrition; secondary multiplicity policy. Thresholds1.20 and1.10 and the primary signed-frame N=U=1023 token K=1 comparison are preserved. V4 supplies an exact construction meeting N=1023 despite signed-literal NOT nodes:240 primitives plus239 joins plus64 NOTs.

This is a complete prospective policy document with named required freeze inputs, not a claim that those inputs have been supplied. Natural corpus, secondary-cell list, native tool closure and runner remain explicit STOP conditions. Selecting100 formulas and descriptive-only secondary inference are disclosed prospective choices made before seeing any performance data; they require adoption and a new immutable freeze identity.

## J. Frozen measurement schema

`MEASUREMENT_SCHEMA_V4.md` specifies every raw-row field, units, types, enumerations, null handling, hashes, input identity, fixed/layout contracts, strategy/provenance, dispositions, attempted/discarded/retained work, cache states, timing/memory boundaries and correctness digest. It is **prospective**, not falsely labelled an actual frozen dataset. Empty example JSONL files are supplied; actual freeze files require manifest registration and a validated append-only writer. No confirmatory row exists in this package.

## K. Primary analysis specification

For100 cases and30 timing repetitions: `r_i=median_j(D_ij)/median_j(C_ij)`; `R=median_i(r_i)`. Paired hierarchical bootstrap resamples cases and, independently for each selected case occurrence, paired repetition indices;20,000 draws, PCG64 seed2026092304, linear percentile95% CI. Memory:15 independent fresh-process peaks per arm/case; `m_i=median(MC_i)/median(MD_i)`; `M=median_i(m_i)`.

Success requires all correctness/completion gates, R>=1.20, CI lower>1.00, M<=1.10. Missing/failed rows→not_evaluable, not a filtered success; valid threshold failure→utility_not_established. `primary_analysis.py` implements aggregation/bootstrap and rejects missing/duplicate/wrong-contract primary rows. Five synthetic constant-data fixtures check time threshold, parity, below-threshold time, memory failure, and memory-boundary behavior using200 bootstrap draws each; an invalid-array-shape fixture checks rejection. No measured data were used. The production function defaults to20,000; its full runner/schema/manifest integration remains a repair item. No statistical output from experimental data was computed.

## L. Confirmatory freeze manifest template

`CONFIRMATORY_FREEZE_MANIFEST_TEMPLATE.json` contains required source/corpus/environment/command/seed/schedule/schema/analysis/protocol and empty-result registrations. Null/TODO fields are deliberately invalid for an actual freeze. The source snapshot is audit evidence, not a Gate B manifest. SHA-256 of an empty JSONL file is `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; this does not establish append-only enforcement.

## M. Remaining non-blocking issues

Once all P0 items are resolved, submission-level polish may wait: public archival DOI, external human compiler/logic-synthesis review, tagged PDF/venue formatting, and optional prior-art comparison table. Broader foundations theory, persistent rewriting, essential-support optimization and additional favorable workload searching are not needed for this gate and should not be mixed into repair. Companion historical cross-reference wording can be clarified editorially in a separate authorized copy if desired.

## N. Next-agent repair prompt

See `NEXT_AGENT_REPAIR_PROMPT.md`, titled **CM Pair Compiler — Gate A Repair and Requalification**. No frozen-execution prompt is provided.

**Final question:** If the confirmatory benchmark were run tomorrow from the audited source and protocol, could a skeptical reviewer determine exactly the algorithm, every returned artifact, charged work, primary statistic, and manuscript agreement? **No.** This audit makes the pair-root algorithm and tested contracts explicit, but the real runner/adapters, selected corpora/tool provenance, complete cache/memory implementation and adopted immutable freeze package are not yet qualified. Gate B remains unauthorized.
