# Six-role hostile review ledger

Date: 2026-09-29. This is internal adversarial review by three separately delegated research agents acting in six explicit specialist roles, with primary-agent integration. It is not six external referees or external peer review. Full role reports and their evidence are preserved under `reviews/`.

| Reviewer role | Attack and evidence | Disposition |
|---|---|---|
| SDD / knowledge compilation | A nonsplitting vtree cut is not a semantic prime certificate; trimmed nodes and dynamic minimization can invalidate naive extraction | Corrected reporting and implemented scope-aware extraction. Every nonsingleton receives exact refinement. Real validation passed 903 compilations/113 minimizations; final outcome accepted |
| SAT / Boolean decomposition | Ground-truth stopping, corner-encoding mistakes, unsound witness-to-clique conversion, hidden probe/setup costs, and unjustified learning claims | Four-corner equivalences and global residual-cut proof audited; 1,390 validation cuts and all principal partitions agree. U/W retained; only singleton pairs flagged. Both probe and residual work included; no learned-clause counts inferred |
| Graph / treewidth / vtree | B3 is only min-fill-ordered balancing; candidate prefix is label-biased; carriers might cross; native and recompiled searches are unequal | Accepted limitations stated in protocol and results. No unsupported hard carrier locking. No claim to beat state-of-the-art treewidth construction or isolate objective quality under equal native search budgets |
| Algorithm engineering / statistics | Stale resumed rows could be misattributed; validation selection could move; missing cells, zero denominators, timeout bias and repeated generator structures could favor a result | Immutable source receipts, per-row fingerprints, complete-cell checks, frozen selection hash and explicit zero/PAR2 rules implemented before held-out. Final reviewer independently reproduced baseline selection, ratio, bootstrap and rescue values. Generator dependence remains explicit |
| Hostile novelty / priority | Rotations, graph guidance, bi-decomposition, factorization, and support deletion have established antecedents; nearby 2026 semantic-vtree work narrows claims | No firstness, no novelty-cleared paper, no new LaTeX draft. Current primary references and theorem-by-theorem matrix preserved. Category D means a sound working note survives, not publication readiness |
| Hostile mathematics | Nonfalse assumptions, factor-versus-prime distinction, existential hyperedge semantics, inclusion-minimal versus minimum support, and query-versus-runtime quantifiers | Proofs reconstructed and finite checks added. Greedy/group deletion bounds explicitly MSMP applications. No FPT runtime or universal pairwise theorem. Final mathematical claim boundary accepted |

## Concrete fixes and chronological disposition

- E2: original resume code could overwrite a source receipt. Fixed before any benchmark trial. Resumes now reject mismatched source/protocol/manifest hashes; each row has a fingerprint.
- E3: froze B2/B3 validation selection and the analysis hash before held-out; held-out entry checks the validation hash. Final analysis rechecks that hash and cross-split source equality.
- E4: predefined zero-denominator and censored-pair rescue rules; include defect probes in SAT counts/time. Required every expected cell and every correctness flag before final summaries.
- MAT-CERT: the historical zero-residual prose needs a prime-alignment promise/certificate. New code always certifies nonsingletons. Frozen documents remain unchanged; the correction is recorded in new proof/research ledgers.
- G1/G2/E1/E5/E6: weaker graph baseline, small biased move prefix, repetitive tiny family structures, native-versus-recompilation asymmetry and final-LCC over-solving are interpretation limits. They were not post-hoc redesigned to rescue the result.

## Final independent checks

Engineering/statistics reviewer verified all 2,100 unique cells (600/600/900), all correctness flags, row fingerprints, cross-split source maps, baseline/analysis hashes and chronology. It independently recomputed B3 selection, M5/B3 geometric ratio **2.211513105083704**, bootstrap **[2.008170496336859, 2.4275540473614283]**, 0 wins/30 losses, and all practical-rescue values. Mathematics/priority reviewer independently reaggregated the raw outcome and accepted the scoped conclusion. SDD/SAT reviewer inspected all supplementary move counts and the isolated size/exposure tradeoff.

All six roles accept **D. MATHEMATICAL NOTE SURVIVES; ALGORITHMIC NO-GO** for this tested pilot. No unresolved correctness, leakage or arithmetic blocker remains. The retained limitations prohibit extrapolating the result to every possible factor-aware objective, a native implementation, industrial benchmark populations or publication novelty.

Move diagnostics and the training-only SAT reuse study are supplementary. The latter's positive persistence result is an established shared baseline technique and cannot replace the failed primary vtree-adaptation metric. No reviewer recommended further benchmark searching for a favorable outcome.
