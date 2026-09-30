# Revision notes after Rules-section update

Date: 22 September 2026

The post-split computational manuscript was revised after the simulated four-role panel audit.

## Changes incorporated

- Renamed the retabulated provenance letter from `R` to `T`, so `R` is reserved unambiguously for the canonical row variable. Pair provenance is now `{S,T,H}`: structural, tabulated root, hybrid.
- Expanded the explanation of the pair-compilation judgment and semantic invariant before presenting inference rules.
- Added an explicit **primitive normalization** rule showing how a supported connective over signed literals becomes a canonical-frame token.
- Preserved the existing numbering of the two rules the author specifically wanted clarified:
  - Equation (17): token negation;
  - Equation (18): same-frame fusion.
- Defined the provenance behavior of negation and fusion more explicitly.
- Added an explicit **exact local tabulation** rule and true-first tabulated token definition.
- Added a complete worked derivation for
  `(X => NOT Y) XOR (NOT Y => X)`,
  producing normalized tokens `0111_2` and `1110_2`, then `1001_2 = [XNOR]`.
- Added a declared pure-structural syntactic fragment and a scoped completeness theorem for that fragment.
- Added an explicit warning that this is syntactic completeness for the declared fragment, not semantic completeness for all two-variable formulas.
- Updated soundness statements and the appendix wording to use tabulation/provenance `T` consistently.
- Updated manuscript header/draft-status wording to identify this as the revised post-split compiler draft.

## Deliberately not added

The revision does not restore formula-valued LM theory, higher-dimensional tensors, spectral material, phase/quantum analogies, or other foundations material now owned by the companion paper.

The main remaining scientific gap is still empirical: the pair-compiler protocol-v3 campaign has not been executed in the manuscript evidence set. Later project-wide CM/BitSet/CSE/native studies use different task contracts and are not silently substituted for that missing pair-compiler experiment.
