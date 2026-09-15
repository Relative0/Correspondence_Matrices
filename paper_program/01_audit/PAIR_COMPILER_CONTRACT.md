# Signed-pair compiler contract

Date: 2026-09-14  
Applies to: `cm_token.py` and `cm_build_pair.py` in the current worktree

## Semantic contract

The compact path uses true-first 4-bit tokens in assignment order
`(1,1),(1,0),(0,1),(0,0)`. A pair surrogate

```text
Pair(row_variable, column_variable, token)
```

asserts that XOR-AND evaluation of `token` on those two positive variables
equals the represented source subtree after declared fixed substitutions.

The compiler may construct such a pair by:

1. recognizing a supported binary connective over signed row/column literals;
2. applying transpose and row/column swaps to align it with the positive
   `(row_variable,column_variable)` frame;
3. complementing a child token for formula negation;
4. fusing child tokens only when both canonical variable names match; or
5. directly evaluating four assignments for a remaining subtree with exactly
   one live row variable and one live column variable.

If none applies, evaluation falls back to the ordinary CM IR. Before a compact
token becomes an explicit dense CM, both axes are reversed from true-first to
false-first order and absent axes are broadcast into the declared layout.

## Supported structural scope

- Primitive connectives: AND, OR, XOR, implication, and equivalence.
- Primitive operands: variables with any finite stack of logical negations.
- Operand order: row/column or column/row.
- Recursive combination: negation and the five binary connectives when child
  pairs carry identical canonical row/column variable names.
- Fallback: any other subtree whose live support is exactly one declared row
  variable and one declared column variable.

The structural claim does not cover two arbitrary compound formulas treated as
opaque logical operands, algebraic equivalence checking between compound
operands, or pair fusion across different row/column partitions.

## Purity and mutation contract

- Expression nodes are frozen dataclasses and are not modified.
- `R`, `C`, and `fixed` are read-only inputs from the pair compiler's point of
  view.
- Tokens are immutable Python integers.
- Pair surrogates are frozen dataclasses.
- Token transformations and lookup-table fusion return new integer values and
  do not alter their inputs.
- Dense lifting returns an owned copy. It does not expose a writable broadcast
  view or mutate the 2-by-2 token matrix supplied to it.

The property suite includes an explicit input-mutation check. Broader mutation
testing of every fallback backend remains part of the release gate.

## Termination and canonicity

Every recursive call receives a strict source-AST child, so structural
compilation terminates for every finite expression tree. Direct retabulation
performs four terminating Boolean evaluations of one finite subtree.

For fixed row/column names and the true-first convention, the 4-bit token is a
canonical representation of the resulting binary truth function. The source
formula, CM IR, and variable partition are not claimed to be globally
canonical.

## Cost model

Let `N` be the number of AST nodes, `H` its height, and `n=|R|+|C|` the number
of explicit dense axes.

| Operation | Time | Additional working memory | Qualification |
|---|---:|---:|---|
| One signed-literal alignment | `O(1)` after reading its negation chain | `O(1)` | At most transpose plus two axis swaps on four bits |
| One token fusion | `O(1)` | `O(1)` | Lookup in a fixed 16-by-16 table |
| One direct pair retabulation | `O(4S)` | `O(D)` | `S` is fallback-subtree size; `D` is its evaluation depth |
| Successful structural pair tree | `O(N)` typical | `O(H)` | No dense intermediate is materialized |
| Current support discovery worst case | `O(N^2)` | `O(H)` | `_pairable_vars` may rescan nested non-pairable subtrees |
| Token-to-dense lift | `Theta(2^n)` | `Theta(2^n)` | Current public function returns the complete explicit CM |
| Ordinary CM IR fallback | backend-dependent plus explicit output cost | backend-dependent plus output | Must be reported separately |

Consequently, constant-time token fusion is a **kernel** property, not an
end-to-end complexity result. Returning an explicit CM still incurs its full
exponential output cost. Any speed claim must report compilation, support
discovery, fallback, conversion, allocation, and materialization separately.

## Required benchmark counters

The compiler returns these counters so the evaluation can stratify workloads:

- `primitive_pair_tokens`;
- `signed_operand_alignments`;
- `token_negations`;
- `token_fusions`;
- `direct_pair_retabulations`;
- `nodes_total`, `pair_attempts`, and `pair_collapses`.

`pairable_ratio` is the fraction of visited nodes that produced a compact pair,
so it is bounded between zero and one. It is not itself a performance result.

`compile_expr_to_cm_pair_token` is the public token-only measurement boundary.
It exposes the compact compilation result and counters without charging the
experiment for dense output materialization. End-to-end experiments must use
the dense public path as a separate endpoint rather than treating this boundary
as the complete user-visible cost.

The non-default `strategy="retabulate"` option is the registered ablation. It
performs one support-discovery traversal and four evaluations of the full AST,
without invoking signed-literal assembly or token fusion. The dense public path
exposes the same arm as `pair_strategy="retabulate"`.

## Verification record

The focused tests cover:

- all 16 tokens in all eight signed operand frames;
- all five primitive connectives in all eight signed frames;
- recursive fusion after signed alignment;
- the direct-retabulation fallback;
- preservation of the true-first token constants;
- 250 seeded random two-variable formulas against the ordinary CM evaluator;
- nonmutation of caller-owned layout and fixed-assignment inputs; and
- the token-only public result and unsupported-scope behavior; and
- the existing optimization and output-budget behavior.

The focused pair, optimization, and output-budget suites pass 102 tests,
including caller-input nonmutation through both compact and ordinary fallback
paths.

Passing these finite tests supports implementation assurance but does not
replace the soundness proof or establish a performance advantage.
