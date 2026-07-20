# CM Experiment C: Operator Difference / Quotient Report

## Executive Summary

Experiment C implements CM quotienting as directional feature subtraction on aligned Boolean CM arrays:

```text
A \ B = A & ~B
```

This is not division and not semantic XOR. It keeps positive CM features present in `A` and absent from `B`. The implementation now includes quotienting, containment, symmetric CM feature delta, dense aligned expression-pair quotient, bitset semantic truth delta, ROBDD symbolic XOR delta, and a native 2x2 CM transformation benchmark.

Current verdict: CM quotienting is implemented and validated as a directional feature artifact. It remains distinct from bitset/ROBDD semantic delta, and the follow-up does not change the conservative conclusion: CM quotienting is not shown as a semantic-delta speed win in these runs.

## Mathematical Definition

For aligned CM arrays with the same shape and ordered basis:

```text
A \ B = A & ~B
B \ A = B & ~A
sym(A,B) = (A \ B) | (B \ A) = A ^ B
```

Containment is directional:

```text
A contains B iff B \ A is empty
```

Paper example, validated by tests and the generated 2x2 table:

```text
OR \ AND = XOR
AND \ OR = FALSE
OR contains AND = true
```

## XOR Baseline Clarification

Bitset XOR delta means semantic output difference:

```text
truth_delta = truth_A XOR truth_B
```

ROBDD XOR delta means symbolic semantic difference:

```text
delta = A XOR B
```

CM quotient is not XOR:

```text
A \ B = A & ~B
```

CM symmetric feature delta is XOR over CM features:

```text
A ^ B
```

That is a feature-delta artifact. It is not the same as semantic truth-output XOR unless the CM artifact is explicitly a truth-output basis.

| Operation | Meaning | Artifact |
| --- | --- | --- |
| Bitset XOR delta | assignments where outputs differ | semantic truth-output vector |
| ROBDD XOR delta | canonical symbolic difference | BDD semantic delta |
| CM quotient `A \ B` | features in A not in B | directional CM feature artifact |
| CM symmetric delta `A ^ B` | features differing either way | CM feature artifact |
| CM containment | whether one feature set includes another | operator/basis feature relation |

## Operator-Family Stratification

The CLI now supports the expression styles needed for broader Experiment C stratification:

```text
ordinary, broad, low-reuse, anti-reduction,
balanced_all_vars, xor_heavy, and_or_not,
implication_heavy, mixed_no_constants, transform_pairs
```

Experiment C summaries now group by `expr_style` as well as `n_vars`, `operator_pair_style`, and `operator_diff_mode`. The follow-up runs below use `mixed_no_constants`; broader family sweeps should include `and_or_not`, `xor_heavy`, `implication_heavy`, `mixed_no_constants`, and `balanced_all_vars`.

## n=16 Follow-up

Commands run:

```bash
python cm_bench.py --bench-operator-difference --operator-diff-mode all --operator-pair-style related_variant --sizes 16 --trials 3 --max-depth 5 --expr-style mixed_no_constants --require-nontrivial-expr --min-used-var-fraction 0.75 --min-tt-density 0.05 --max-tt-density 0.95 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --robdd-dd-backend autoref --robdd-order-policy fixed --robdd-order-sweeps 1 --operator-quotient-direction both --operator-quotient-max-dense-n 16 --print-summary --out-prefix bench_operator_difference_related_n16_autoref
python cm_bench.py --bench-operator-difference --operator-diff-mode all --operator-pair-style equivalent_rewrite --sizes 16 --trials 3 --max-depth 5 --expr-style mixed_no_constants --require-nontrivial-expr --min-used-var-fraction 0.75 --min-tt-density 0.05 --max-tt-density 0.95 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --robdd-dd-backend autoref --robdd-order-policy fixed --robdd-order-sweeps 1 --operator-quotient-direction both --operator-quotient-max-dense-n 16 --print-summary --out-prefix bench_operator_difference_equiv_rewrite_n16_autoref
```

Dense quotient ran successfully at n=16 with `cm_quotient_status=ok`.

| n | pair style | bitset delta | ROBDD/autoref delta | CM quotient | A\B | B\A | Jaccard | status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 16 | related_variant | 0.000547 | 0.009119 | 0.002734 | 2912 | 3068 | 0.884849 | ok |
| 16 | equivalent_rewrite | 0.000655 | 0.011074 | 0.002224 | 0 | 0 | 1.000000 | ok |

For related variants, bitset remained fastest for semantic truth delta. CM quotient was faster than autoref symbolic XOR delta in this native-Windows run, but it computes a different artifact. For equivalent rewrites, semantic delta was zero and dense CM quotient also collapsed to zero for these generated rewrites.

## CUDD Follow-up

Native Windows check failed:

```text
importlib.util.find_spec("dd.cudd") -> None
from dd import cudd -> ImportError
```

Docker/Linux check succeeded in `python:3.10-slim` after installing `dd`, `numpy`, `pandas`, `sympy`, and `requests`:

```text
dd.cudd import OK
```

Commands run in Docker/Linux:

```bash
python cm_bench.py --bench-operator-difference --operator-diff-mode all --operator-pair-style related_variant --sizes 8,12,16 --trials 3 --max-depth 5 --expr-style mixed_no_constants --require-nontrivial-expr --min-used-var-fraction 0.75 --min-tt-density 0.05 --max-tt-density 0.95 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --robdd-dd-backend cudd --robdd-order-policy fixed --robdd-order-sweeps 1 --operator-quotient-direction both --operator-quotient-max-dense-n 16 --print-summary --out-prefix bench_operator_difference_related_cudd
python cm_bench.py --bench-operator-difference --operator-diff-mode all --operator-pair-style equivalent_rewrite --sizes 8,12,16 --trials 3 --max-depth 5 --expr-style mixed_no_constants --require-nontrivial-expr --min-used-var-fraction 0.75 --min-tt-density 0.05 --max-tt-density 0.95 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --robdd-dd-backend cudd --robdd-order-policy fixed --robdd-order-sweeps 1 --operator-quotient-direction both --operator-quotient-max-dense-n 16 --print-summary --out-prefix bench_operator_difference_equiv_rewrite_cudd
```

| n | pair style | bitset semantic delta | ROBDD/CUDD XOR delta | ROBDD/autoref XOR delta if available | CM quotient | semantic equivalent | notes |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 8 | related_variant | 0.000054 | 0.000174 | 0.003949 | 0.001095 | false | CUDD Docker/Linux; autoref previous native run |
| 12 | related_variant | 0.000075 | 0.000408 | 0.010305 | 0.001451 | false | CUDD Docker/Linux; autoref previous native run |
| 16 | related_variant | 0.000393 | 0.000414 | 0.009119 | 0.002561 | false | CUDD Docker/Linux; autoref native n=16 run |
| 8 | equivalent_rewrite | 0.000106 | 0.000265 | 0.003645 | 0.001412 | true | CUDD Docker/Linux; autoref previous native run |
| 12 | equivalent_rewrite | 0.000100 | 0.000271 | 0.011135 | 0.002163 | true | CUDD Docker/Linux; autoref previous native run |
| 16 | equivalent_rewrite | 0.000521 | 0.000336 | 0.011074 | 0.003262 | true | CUDD Docker/Linux; autoref native n=16 run |

CUDD materially changes the ROBDD symbolic-delta baseline versus autoref in these runs, especially at n=16. It does not change quotient correctness, because quotienting is a CM feature operation rather than a BDD semantic-delta operation. CUDD and autoref are reported separately; autoref is not labeled as CUDD.

## Native CM Transformation Benchmark

New mode:

```text
--bench-cm-transformations
--cm-transform-kind {complement,transpose,rotate90,rotate180,rotate270,negate_left_operand,negate_right_operand,negate_both_operands,all}
```

It generates:

```text
cm_transform_2x2_table.csv
bench_cm_transform_2x2_raw.csv
bench_cm_transform_2x2_summary.csv
```

The benchmark validates all 16 two-variable operators against truth-table semantics for:

```text
transpose / operand swap
complement / expression negation
negated left operand
negated right operand
both operands negated
```

Summary:

| operators | valid lookup names | transpose | complement | negate left | negate right | negate both |
| ---: | --- | --- | --- | --- | --- | --- |
| 16 | true | true | true | true | true | true |

Selected 2x2 transformation examples:

| operator | transpose | complement | negate left | negate right | negate both |
| --- | --- | --- | --- | --- | --- |
| IMP | RIMP | X_AND_NOT_Y | OR | NAND | RIMP |
| OR | OR | NOR | IMP | RIMP | NAND |
| AND | AND | NAND | NOT_X_AND_Y | X_AND_NOT_Y | NOR |
| XOR | XOR | EQV | EQV | EQV | XOR |
| EQV | EQV | XOR | XOR | XOR | EQV |

This validates native CM transformation functionality beyond quotienting. No speed win is claimed; this is a correctness and artifact-coverage benchmark.

## Expression-Family and Ordering Caveats

ROBDD/CUDD performance depends strongly on variable ordering. CM dense/basis computations also depend on variable and basis ordering. Bitset output order exists too, but usually affects layout more than asymptotic complexity.

XOR-heavy expressions may stress ROBDDs differently than AND/OR/IMP rule-like expressions. Therefore, no universal benchmark claim should be made from one expression class.

Future Experiment C sweeps should run:

```text
and_or_not
xor_heavy
implication_heavy
mixed_no_constants
balanced_all_vars
```

For each family, compare:

```text
bitset semantic delta
ROBDD/CUDD symbolic delta
CM quotient
CM transformation correctness/time where applicable
```

## Implementation Updates

Files changed in this follow-up:

- `cm_operator_difference.py`: CM transpose, complement, rotations, paper transformation rules, 2x2 evaluator, and truth-table transform validator.
- `cm_bench.py`: `--bench-cm-transformations`, `--cm-transform-kind`, `cm_transform` operator-diff mode, `implication_heavy`, `transform_pairs`, grouped Experiment C summaries by `expr_style`, and explicit `dense_quotient_status=skipped_limit` for bounded dense quotient skips.
- `tests/test_operator_quotient.py`: all-operator transform lookup/correctness tests and n=16 dense quotient run-or-skip test.
- `tests/test_bench_integration.py`: CUDD detection assertion that autoref is not mislabeled as CUDD.

## Interpretation

1. n=16 ran successfully for related and equivalent-rewrite autoref follow-ups; dense quotient status was `ok`.
2. CUDD changed the ROBDD semantic-delta baseline by making symbolic XOR delta much faster than autoref in Docker/Linux.
3. This does not affect quotient correctness; CM quotient remains `A & ~B` over aligned CM features.
4. XOR baselines are useful semantic comparisons, but they should not be treated as the assumption behind CM quotient or CM feature-delta comparisons.
5. Native CM functionality now validated beyond quotienting: transpose, complement, rotations, operand swap, expression negation, left/right/both operand negation over all 16 two-variable operators.
6. Transformation benchmarks should become a dedicated Experiment D if the next step is timing and extending them to dense expression-level transformations.

## Final Verdict

Experiment C is stronger after the follow-up: it now separates semantic XOR baselines, directional CM quotienting, and CM transformation artifacts explicitly. CUDD improves the ROBDD symbolic semantic-delta baseline where it actually imports and runs, but the quotient conclusion does not change: CM quotienting is a distinct operator/basis feature artifact, not a semantic XOR speed win.
