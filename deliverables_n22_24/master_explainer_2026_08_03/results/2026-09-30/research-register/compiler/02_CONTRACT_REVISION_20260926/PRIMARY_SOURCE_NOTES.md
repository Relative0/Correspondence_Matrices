# Primary sources checked for this revision

Access date: 26 September 2026. These are specification/literature checks, not runtime benchmarks of these libraries.

- [Cheng, Zhao and Xu, Matrix Approach to Boolean Calculus](https://skoge.folk.ntnu.no/prost/proceedings/cdc-ecc-2011/data/papers/0224.pdf): proceedings p. 6952, Proposition 3.3, gives the entrywise truth-vector outer-operation identity for the same ordered variables. The manuscript identifies that specific antecedent.
- [kitty operations](https://libkitty.readthedocs.io/en/latest/operations.html): Boolean operations, `has_var`, cofactors, swaps, flips, and base expansion are explicitly available. Documentation version labels do not identify an executed benchmark version.
- [Mishchenko, Chatterjee and Brayton, DAG-Aware AIG Rewriting](https://web.cecs.pdx.edu/~mperkows/CLASS_573/febr-2007/p532-mishchenko.pdf): Section 3 and Figure 1 describe four-input cuts, NPN lookup, sharing-aware gain evaluation, candidate rollback and selected replacement. The four-page proceedings paper is pp. 532–535.
- [mockturtle cut rewriting](https://mockturtle.readthedocs.io/en/latest/algorithms/cut_rewriting.html): the rewriting interface supplies a truth table and an iterator range of leaves; rewriting is accepted according to area/gain conditions. This is the direct comparison for explicit operand metadata and commitment.
- [Lee et al., A Simulation-Guided Paradigm for Logic Synthesis and Verification](https://infoscience.epfl.ch/server/api/core/bitstreams/208dfcbe-a87e-43e7-8fbf-29dc68dee3cb/content): primary paper title page confirms Siang-Yun Lee and DOI 10.1109/TCAD.2021.3108704, correcting the previous bibliography's first name.
- [Pinned compiler repository](https://github.com/Relative0/Correspondence_Matrices/tree/0ab8ffd0c23ffa71ee951d375b1c170ffdcc084b): `cm_build_pair.py`, `cm_token.py`, `cm_normalize.py` and their import/test closure are included unchanged with verified Git blob identities in the reproduction directory. The pinned revision specifies the current contract check, not an inferred execution revision for every historical measurement.

Later project-wide benchmark paragraphs were retained as attributed historical context; they were not regenerated as part of this draft revision. No general novelty clearance or complete bibliography audit is claimed.
