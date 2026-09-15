# Implementation-to-paper semantic map

Date: 2026-09-14  
Scope: updated after the signed operand-alignment implementation

## Finding

The repository contains three related but nonidentical computational objects.
The paper must name them separately.

| Object | Current implementation | Meaning | Ordering |
|---|---|---|---|
| 4-bit CM operator token | `cm_token.py`, `cm_lm.py` | One binary truth function packed as `(11,10,01,00)`; supports entrywise operator composition and geometric transformations | True-first `(1,0)` |
| Pair surrogate | `cm_build_pair.py` | A 4-bit token plus one row variable and one column variable; signed primitive tokens are aligned and recursively fused, with four-assignment retabulation as a fallback | Token is true-first; conversion reverses both axes for dense output |
| CM IR | `cm_ir.py` | Interned/canonicalized Boolean expression DAG evaluated as arrays, packed bits, or flat instructions | Hypercube axes are false-first `(0,1)` |
| Explicit dense CM | `cm_build.py`, `cm_normalize.py` | A truth-relation array split across declared row and column variables | Natural binary index order, false-first `(0,1)` |

The 4-bit token is the paper's compact binary operator. The explicit dense CM
is a reshaped truth table for the full expression. The CM IR is a symbolic
compiler artifact. Calling all three simply “the CM” would obscure their type,
size, semantics, and performance costs.

## Confirmed code relationships

- `cm_token.cm_compose` applies AND, OR, XOR, implication, or equivalence
  entrywise to two 4-bit tokens through 16-by-16 lookup tables.
- `cm_build_pair._signed_operator_pair` recognizes a Boolean connective over
  two signed literals, identifies whether the operands are row/column ordered
  or swapped, and uses `cm_align_signed_operands` to emit a positive-frame token.
- `cm_build_pair._compile_pair` recursively fuses child tokens with `cm_compose`
  when their `(row_variable, column_variable)` metadata matches. It evaluates
  four assignments only when a remaining two-variable subtree cannot be built
  by those structural rules.
- `cm_build_pair._token_to_matrix` reverses both token axes so the result can be
  lifted into the dense false-first array layout.
- `cm_lm` provides true-first bra/ket states, token conversion, transpose and
  rotations, and Boolean, XOR, or arithmetic contractions.
- `cm_ir.align_to_vars` permutes and broadcasts array axes by variable name.
  This is full truth-array alignment, not the signed two-operand token
  normalization proved in the formal package.
- `cm_normalize.combine_pointwise` performs entrywise Boolean combination after
  dense shapes match.

## Claim boundary

The current codebase now supports this integrated statement:

> Binary connectives over signed row/column variables are normalized into a
> positive operand frame by token transformations. Tokens with matching frame
> metadata are recursively fused by a constant-size entrywise lookup table and
> converted explicitly into the dense false-first layout.

The implementation retains a transparent four-assignment fallback for a
two-variable subtree that cannot be assembled structurally. Diagnostics report
primitive tokens, signed alignments, token negations, token fusions, and direct
retabulations separately.

The stronger statement that remains unsupported is:

> Arbitrary multi-variable formulas can be treated as two opaque operands,
> recognized up to swap/negation, and fused in the same 4-bit path.

The current frame metadata names one row variable and one column variable; it
does not identify equivalence classes of compound operand formulas.

## Required reconciliation before performance drafting

1. Add an explicit artifact/type table to the paper and use distinct names:
   `CM token`, `pair surrogate`, `CM IR`, `flat program`, and `explicit CM`.
2. Specify every boundary conversion, especially true-first token to
   false-first dense array.
3. State the implemented scope precisely: signed variable operands and
   recursively matching pair tokens, with direct retabulation reported as a
   separate fallback rather than hidden inside “fusion.”
4. Tie every benchmark endpoint to one named artifact and report conversion,
   compilation, materialization, and output costs separately.
5. Benchmark the structural path against direct four-assignment retabulation
   and the ordinary CM IR, including compilation and conversion costs.

## Recommended decision

The signed-variable alignment gate is now implemented and locally verified.
The next gate is to freeze and run an evaluation that separates structural
alignment/fusion, direct retabulation, ordinary CM IR, and appropriate external
baselines. General compound-operand alignment should remain future work unless
it receives its own representation, algorithm, and tests.
