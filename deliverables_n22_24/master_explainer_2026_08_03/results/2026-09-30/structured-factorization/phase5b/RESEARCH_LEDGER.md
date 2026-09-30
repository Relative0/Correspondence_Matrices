# Phase 5B research ledger

Date: 2026-09-29. All new work is under `phase5b_output`. The sibling `continuity_archive` preserves the submitted archive byte for byte. The original ZIP SHA-256 is `21dcbd6747c407bbd7c0ceaf8f9fab87e64e8a8822db95931f46d69f9b85000a`.

## Orientation and reproduction

- Extracted the 117-file archive safely, rejecting traversal/symlink paths and refusing to overwrite an existing extraction target. Read the five requested handoff files in order, then the Phase 5 master/gate/theorem note and Phase 4 master/SDD/SAT/hybrid/operator documents. Treated the invoked Phase 5B prompt as the scoped work specification; unrelated broader-context files remain provenance, not new instructions.
- Copied frozen code before executing. Relocated only hard-coded `/mnt/data` paths in executable copies, recording hashes and every substitution. No archived source or data was overwritten.
- Reproduced all six campaigns and eleven archived output artifacts. Added independent model/projection/cofactor checks rather than relying solely on archived exposure computed from semantic truth. Reproduction gate passed before any new method run.
- Confirmed two interpretation boundaries: sixteen frozen random SAT-validation inputs are false (encoding equivalence still holds), and the fixed-order truth-table helper needs coordinate remapping on permuted trees.
- Corrected the Phase 4/5 prose implication that apparent prime alignment eliminates all residual certification. A true externally certified alignment promise suffices; an ordinary failed vtree cut does not certify unrestricted primeness. New code refines every nonsingleton exposed block.

## Tooling and exact implementation

- Installed actual PySDD 1.0.6 and PySAT 1.9.dev15/Glucose4, plus pinned supporting packages. Initial pip attempts stalled writing the external cache. A traceback identified that path; `--no-cache-dir` resolved it without changing permission settings. Logs preserve the attempts and dependency check.
- Implemented real compressed-SDD extraction, trimmed-node handling, native minimization, persistent four-corner SAT, equality-assumption witness shrinking, and exact final carrier LCC. The pipeline semantically refines direct blocks before final carrier assembly; this is sound but may do avoidable work compared with carrier-compatible residual refinement.
- Real-backend validation passed: 903 compilations, 113 minimizations, 881 direct/semantic/carrier comparisons each, 1,390 cut checks, 46 witness checks and 80 minimality checks. False inputs are separately identified.

## Protocol and review before outcomes

- Froze 70 generated CNFs, ten named families, train/validation/held-out splits, three replicate seeds, ten methods, 12-candidate M search budgets and fixed unit coefficients. No weights were tuned. Primary is total exact runtime, with M5 versus validation-selected B2/B3. Registered a separate practical residual-work threshold before data.
- Internal graph/statistics review found structurally overlapping relabelled families, a modest min-fill-order baseline, label-biased candidate prefixes, and native-minimization versus full-recompilation asymmetry. These restrict interpretation; the manifest and budget were not post-hoc improved.
- Repaired split receipt overwriting before benchmark runs. Resumption now requires identical source/protocol hashes, and rows carry the run fingerprint. Added baseline-selection guard, full-cell/fingerprint checking, and explicit zero/censoring rules before held-out.
- Heuristic workers receive only inputs and seeds. Oracle Pi enters only O; evaluator truth and direct-prime labels are attached after workers finish. Defect unions are soft span features; witnesses retain U/W and only singleton/singleton supports are flagged as sound pairwise links.

## Theorems and priority

- Independently reconstructed the cut/exposure, laminar compatibility, defect-support, equality counterexample, positive irredundant CNF and essential read-once CM proofs with explicit hypotheses.
- Proved equality-assumption greedy inclusion-minimization (at most initial support width extra queries), and a balanced group-deletion output-sensitive bound. These are applications of established monotone-predicate minimization, not novelty claims or FPT runtime theorems. The pilot uses greedy shrinking; the group variant is an independent theorem/check.
- Current primary-source search covered dynamic vtrees, size minimization, graph/hypergraph compilation, SAT/QBF decomposition, alternative objectives and 2025–2026 work. Recent semantic-vtree work and MSMP antecedents narrow any priority claim. No firstness or publication readiness is established.

## Final outcome and subsequent checks

Principal-run receipts, validation selection, statistical summary, move diagnostics, SAT reuse comparison, public smoke controls and final six-role review are the authoritative machine-readable outcome record. The master report and next gate state the single final decision. Source archives are checked again during package assembly; package checksums cover every delivered file.

No source changes, new weights, or new primary benchmark families are allowed in response to held-out outcomes. Any future algorithm change requires a fresh preregistered campaign. This task continues through packaging because the active provenance and review state are needed; a later independently designed scaling campaign should use the concise next-gate handoff.
