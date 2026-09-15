# Correspondence Matrices paper program

This directory is the reviewable audit package for developing the historical Correspondence Matrices material into a defensible publication program. It preserves supplied sources unchanged and does not modify the original repository or Paper-Workbench checkout.

Prospective author name: **Brian Theory**.

Selected paper title: **Operator-Level Boolean Computation with Correspondence Matrices**.

## Contents

- `00_sources/SOURCE_MANIFEST.md` — provenance, hashes, publication status, and inspection record.
- `01_audit/CLAIM_PROOF_LEDGER.md` — claim status, proof obligations, empirical checks, and exclusions.
- `01_audit/TYPED_SEMANTIC_SPECIFICATION.md` — working definitions for XOR-AND operator evaluation, operand-frame transformations, fusion, LMs, logical measurement pairing, and higher arity.
- `01_audit/FORMAL_PROOF_PACKAGE.md` — appendix-ready proofs for CM selection, coefficient-space linearity, signed operand alignment, fusion, LM valuation/measurement, ANF separation, and higher-arity size.
- `01_audit/IMPLEMENTATION_SEMANTICS_MAP.md` — distinction among 4-bit tokens, pair surrogates, CM IR, and dense CMs, including the true-first/false-first conversion boundary.
- `01_audit/PAIR_COMPILER_CONTRACT.md` — concrete semantics, supported scope, purity, termination, canonicity, complexity, counters, and verification requirements for signed-variable token alignment/fusion.
- `01_audit/EVALUATION_PROTOCOL_V3.md` — current pre-freeze confirmatory plan with explicit pure/hybrid/retabulation outcomes, one primary cell, workload and cache controls, baselines, endpoints, and release manifest. Earlier versions remain preserved as history.
- `01_audit/EXPERIMENT_EVIDENCE_AUDIT.md` — later implementation, correction, benchmark, and artifact-boundary audit.
- `01_audit/check_cm_claims.py` — exhaustive checks for the binary-token identities.
- `01_audit/check_local_implementation.py` — independent truth-table diagnostic for the observed local implementation.
- `02_literature/LITERATURE_MATRIX.md` — focused primary-source novelty audit.
- `02_literature/LM_OPERATOR_ANTECEDENT_SEARCH.md` — targeted search record for Boolean operator, outer-product, and formula-valued LM antecedents.
- `03_program/PROGRAM_DECISION_MEMO.md` — audience, venue class, paper design, figures, readiness gates, and one-versus-two-paper recommendation.
- `03_program/TITLE_AND_TERMINOLOGY_MEMO.md` — ranked title alternatives and the definition of operand-aligned fusion.
- `03_program/DEPENDENCY_OVERLAP_MAP.md` — allocation and prior-version controls.
- `04_figures/figure_01_boolean_operator_contraction.svg` and `FIGURE_01_CAPTION.md` — editable lead figure showing bra/ket operator evaluation, bracketed `[Θ]` notation, the `[⇔]` to `[⇕]` rotation, and tautological Impax superposition.
- `04_figures/figure_02_numeric_representation_map.svg` — current editable numeric map from `[\Theta]` through `\operatorname{vec}([\Theta])` to external ANF and STP representations. The original combined `figure_02_representation_map.svg` remains preserved.
- `04_figures/figure_03_operand_alignment_and_fusion.svg` and `FIGURE_03_CAPTION.md` — editable worked example of signed operand-frame normalization followed by entrywise operator fusion.
- `04_figures/figure_04_lm_valuation_and_pairing.svg` and `FIGURE_04_CAPTION.md` — editable symbolic-to-numeric diagram for formula-valued LM pairing, valuation commutation, and the explicitly nonphysical meaning of logical measurement.
- `04_figures/CM_PAPER_NOTATION_MACROS.tex` — manuscript macros for the centered `\impax` overlay, tight `\inbkthree`/`\otbktwo` bra-ket forms, and compact `2 x 2` displays.
- `05_manuscript/main.tex`, `appendix_proofs.tex`, and `references.bib` — the new Brian Theory manuscript draft, with an accessible main-text operator interpretation, typed CM/LM semantics, representation distinctions, compiler/evaluation methods, scoped contribution claims, and appendix-ready proofs.
- `05_manuscript/DRAFT_STATUS.md` — drafted sections, deliberately withheld empirical material, and the next drafting pass.
- `05_manuscript/PANEL_FINDINGS_RESPONSE_R2.md` — itemized disposition of the second simulated review panel's findings and the gates that legitimately remain open.
- `PAPER_WORKBENCH_STATUS.md` — local Paper-Workbench setup and provider status.

Temporary page renders used for visual inspection are under `tmp/pdfs/` and are not manuscript figures.
