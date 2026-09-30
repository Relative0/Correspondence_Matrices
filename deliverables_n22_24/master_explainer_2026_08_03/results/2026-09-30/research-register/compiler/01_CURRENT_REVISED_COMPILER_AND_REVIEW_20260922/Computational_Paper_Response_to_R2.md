# Response to review-panel round 2

**Paper:** *Operator-Level Boolean Computation with Correspondence Matrices*  
**Author:** Brian Theory  
**Date:** 2026-09-15

This memo records the disposition of every material R2 panel finding. It does
not claim that the empirical campaign or external novelty review is complete.

## Mathematical-review findings

| Finding | Disposition |
|---|---|
| Mathematical core sound | Retained. No established identity was weakened. |
| Compiler proof only a prose sketch | Addressed. The manuscript now declares an AST grammar, typed pair judgment, provenance classes, inference rules, termination argument, and an appendix induction covering pure and hybrid derivations. |
| Multiple-opportunity success rule | Addressed in protocol v3 and the manuscript. There is one primary cell; root provenance is a correctness check rather than a post-measurement filter; all other cells are multiplicity-controlled secondary analyses. |
| Novelty remains contingent | Retained as a limitation. The manuscript still calls the systems contribution scoped and testable and makes no general priority or performance claim. |
| Uppercase formula variables in numeric fusion | Addressed with `x,y in B`. |
| Abstract called an unfrozen study frozen | Addressed: it is now a protocol that must be frozen before execution. |
| STP truth-row typing implicit | Addressed: `t` is a `1 x 4` Boolean row and its complement is entrywise. |
| Valuation proof equated a bit with a formula | Addressed by writing `b_i = v(...)` and concluding equality under every valuation. |
| ANF coefficient-monomial product implicit | Addressed with explicit conjunction. |
| Operand-swap notation informal | Addressed by defining `Theta^tau(x,y) := Theta(y,x)` and stating `[Theta^tau] = [Theta]^T`. |

## Compiler and experimental-review findings

| Finding | Disposition |
|---|---|
| Hidden hybrid structural-retabulation path | Addressed in code and paper. The API now exposes `pure_structural`, `hybrid`, and `retabulate`; every result reports pure structural, hybrid pair, full retabulation, or ordinary fallback. The old `structural` name is a reported compatibility alias only. |
| Hybrid case absent from proof/tests | Addressed with pair provenance, hybrid soundness induction, and a mixed-child regression test comparing hybrid, pure-only, and whole-retabulated behavior. |
| Empirical campaign unfrozen/unrun | Still open by design. Protocol v3 is now ready for a harness pilot, but no result has been fabricated or carried forward. |
| Primary rule not singular | Addressed with one exact Stratum-B, `N=1023`, `U=N`, token, reuse-one, direct-packed comparison. Threshold rationales and a repeatability gate are declared. |
| Natural corpus and AIG decision ambiguous | Partly completed. Protocol v3 makes the ABC-compatible arm mandatory for a frozen translatable subset and specifies provenance/license/hash requirements. Actual sources, tool environment, and manifest must still be frozen before confirmation. |
| `nodes_total` and `pairable_ratio` incomparable | Addressed. Iterative identity-DAG statistics now separate AST occurrences, unique object nodes, height, compiler calls, and negation scans. Legacy fields remain only for old readers and are forbidden as cross-strategy endpoints. |
| Deep skewed trees may hit recursion limits | Addressed in scope: balanced trees use all sizes; skewed trees stop at 255 occurrences and height 128. The recursion limit is not raised, and any in-scope failure remains an observation. |
| Direct packed arm lacked fixed substitutions | Addressed in `eval_expr_bitset` with all-zero/all-one fixed masks and parity tests, including a fixed-only expression. |
| Cache treatment ambiguous | Addressed: cold one-shot clears and includes environment construction; prepared reuse pays construction once and reports it separately. |
| No shared token-query implementation | Addressed with public `cm_token_value`, now used by alignment tests and required by protocol v3 for all four-bit producers. |
| Sharing not factored explicitly | Addressed in protocol v3 with identity-shared, equal-but-separately-allocated, and no-sharing conditions, recording both `N` and `U`. |
| “External baseline” ambiguous | Addressed. The main paper names direct packed, prepared packed, ROBDD, and external ABC/AIG arms explicitly. |

## Editorial and accessibility-review findings

| Finding | Disposition |
|---|---|
| LM theory appeared after Results | Addressed. Formula-valued LMs now precede Experimental Method and Results. |
| Compiler-LM relationship unstated | Addressed explicitly: the implemented compiler uses numeric tokens, pair metadata, and ordinary IR; formula-valued LMs are an independent symbolic extension and are not timed. |
| Representation figure preceded LM definition and was too dense | Addressed conceptually. The related-work figure is cropped to the numeric CM/truth-vector/ANF/STP path; the existing LM valuation/pairing figure supplies the separate symbolic path after the LM definition. |
| No independently reproducible compiler presentation | Addressed with typed rules, compact algorithm prose, and a worked trace including tokens, transformations, fusion, counts, and root outcome. |
| Availability statement missing | Addressed for the working artifact with exact test/static-check commands and required manifest contents. A public repository or archival DOI remains a submission gate. |
| Six-item contribution list diffuse | Addressed by consolidating it to four contributions. |
| Narrow justified tables | Addressed with ragged-right fixed-width columns. |
| PDF metadata sparse | Improved with keywords. Full tagged-PDF accessibility remains a release-format task. |

## Verification performed after implementation

- Pair/alignment, optimization, output-budget, and packed-backend suites:
  `116 passed`.
- Manuscript static checker: `47 labels`, `15 cited sources`, all resolved.
- The manuscript compiles successfully after the revisions.

## Legitimately remaining gates

1. Build and pilot the protocol-v3 harness without treating pilot measurements
   as evidence.
2. Freeze the generated and natural corpora, ABC/AIG environment, immutable
   source snapshot, schedule, schemas, and manifest.
3. Execute the confirmatory campaign and populate Results and Figure 5 with
   wins, ties, losses, failures, timeouts, and memory results.
4. Finish the primary-source novelty audit and obtain a final adversarial
   logic-synthesis review after results exist.
5. Add a public archival identifier, vector-source publication figures where
   the venue permits them, and tagged-PDF accessibility in the release format.
