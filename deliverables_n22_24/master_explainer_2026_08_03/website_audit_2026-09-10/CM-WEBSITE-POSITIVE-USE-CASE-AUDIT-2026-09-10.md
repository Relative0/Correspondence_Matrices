# CM website positive-use-case audit — 2026-09-10

## Rule

A “positive” result must use a current, task-matched comparator; preserve timing/materialization boundaries; have the favorable ratio direction; retain interval/tail/case heterogeneity; and survive the stated correctness/verification gate. A speedup against an obsolete or weaker arm is not promoted when a stronger current baseline wins.

## Positive or promising cases that should be visible

| Case | Result | Why it qualifies | Boundary that must remain |
| --- | --- | --- | --- |
| Plain CSE kernel | CM/CSE 0.887646 local; 0.926772 EPFL; five Linux synthetic replications 0.877–0.888 | same kernel task, ratios below 1 | kernel only; excludes preparation/wrapper |
| Current flattened-CSE bare kernel | B2/B4 V3 0.890570 [0.874065, 0.907272] | exactly counterbalanced and interval wholly below parity | bare CM, not public wrapper; 216 formulas/264 rows |
| C6 cached packed source-ANF | 1.313448× test; 1.637157× confirmation; p95 2.175615× / 1.835850× | same-split total-time comparison; exact accuracy/partition; zero mismatches | packed exact core advances; learned hybrid and production promotion do not |
| C16 exact-screened GF(2) | 3.545324× local; Linux 3.177887× whole path and 3.117978× p95 | same exact artifact, cross-machine confirmation, zero semantic/artifact mismatch | minimum local case 0.892796×; not every case wins; production disabled |
| Feature-model k=16 versus direct CNF | CM/direct-CNF 0.276951 [0.200748, 0.371722] | favorable bounded warm-output result across seven equal-weight histories | performance-provisional; incomplete cold pipeline; conditioned slices |
| Complete relation versus dense CM | packed/recursive CM 1.053300× [1.045764, 1.060967] | task-matched complete-relation comparison on one verified host | direct BitSet is stronger and beats CM; not a best-current-backend win |
| Related multi-root union reuse | Python union 1.146961× [1.126666, 1.167327] and native union 1.237987× [1.209490, 1.263523] versus separate arenas | same ordered related-root outputs; structural sharing saves repeated work | single architecture-comparison host; native-vs-Python union interval crosses parity |
| CSE-flat q64 engine over Python R2 | 1.100368× GCC (minimum 1.030643) and 1.090161× Clang (minimum 1.013096), 54 cases per host | within-host q64 repeated-query contract and all cases favorable | positive engine result, not evidence that CM universally wins |

## Looks favorable but is not a current positive-use-case claim

| Finding | Reason not positive |
| --- | --- |
| Historical flattened-CSE 1.0038 | CM/baseline time ratio is slightly above 1, so CM is slightly slower; a later B2/B4 V3 contract is the current headline. |
| Public-wrapper 3.094136 | CM wrapper/baseline time ratio is above 1; the wrapper is about 3.09× the comparator time. |
| Feature-model CM/CUDD 0.624 [0.216, 1.535] | The clustered interval crosses parity and the extraction contracts are sensitive/asymmetric. |
| Native union/Python union 1.002884 [0.953251, 1.046587] | The interval crosses parity; retain shared-union benefit, not unconditional native superiority. |
| Complete-relation CM/direct BitSet 0.929550 [0.921916, 0.937246] | This speedup-oriented field is direct-BitSet over CM expressed inversely in site naming; the underlying verdict is that BitSet wins all 78 cases. |
| CUDD full enumeration gains | They compare against enumeration/extraction contracts, not the strongest current direct BitSet or task-specific solver. |
| All thirteen small-query controls | CNF or SAT beats the CM arm by about 2.20×–16.23× on the matched small tasks. |
| Sep-10 q64 native stable subset | The fixed subset is selective; fully charged two-host values 0.949341× and 0.977972× fail the 1.10 gate. It is post-cutoff and a no-go. |

## Publication recommendation

The current site should foreground four CM-positive surfaces: the current B2/B4 V3 bare kernel, C6 packed exact source-ANF, C16 exact screening with both machines, and the bounded feature-model k=16 direct-CNF result with its provisional label. Keep plain-CSE and multi-root sharing as scoped supporting positives. Keep losses, parity crossings, and stronger-baseline outcomes immediately adjacent so readers can distinguish “where CM helps” from “where a current competitor remains better.”
