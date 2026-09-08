# From logical matrices to higher-dimensional CMs — script v3

Status: paper-audited bra-ket revision; narrated review candidate  
Target duration: 4:25  
Target delivery: calm, precise, 132–142 WPM

## 0:00–0:40 — An outer product creates a base LM

**Voiceover**

A correspondence matrix contains binary outputs. A logical matrix keeps one
step more information: its cells contain logical expressions.

Write ket X as the column X, not-X, and bra Y as the row Y, not-Y. Their outer
product—ket X times bra Y—creates a two-by-two logical matrix. The first row is
X and Y, then X and not-Y. The second is not-X and Y, then not-X and not-Y.

So the ket supplies the row states, the bra supplies the column states, and
each cell is their conjunction.

**Visual**

Build, do not merely reveal:

```text
|X⟩ = [X, ¬X]ᵀ       ⟨Y| = [Y, ¬Y]

|X⟩ ⊗ ⟨Y| = |X⟩⟨Y| = M_XY

M_XY = [ X∧Y      X∧¬Y  ]
       [ ¬X∧Y     ¬X∧¬Y ]
```

Animate the column distributing across the row. Badge the result
`LM · expression-valued`.

## 0:40–1:12 — Positive valuation makes the CM

**Voiceover**

The paper applies positive valuation, written V sub T, to every expression.
For equivalence, the two agreement entries are true and the disagreement
entries are false. Positive valuation therefore yields one-zero, zero-one.

That is the central relationship: the L M holds expressions; positive
valuation, entry by entry, produces the binary C M. The shape and cell order
stay fixed while the entry type changes.

**Visual**

Show the paper's equivalence LM, then pass a gold `V_T` scan through it:

```text
[ X↔Y       X XOR Y ]       [1 0]
[ X XOR Y   X↔Y     ]  →    [0 1]
```

Keep `LM expressions → V_T → CM bits` visible.

## 1:12–1:55 — Tensor two smaller LMs

**Voiceover**

For four variables, the paper builds a larger L M from two smaller ones. One
base matrix is ket W bra X. The other is ket Y bra Z. Their tensor, or
Kronecker, product is four by four.

Equivalently, combine the two kets into a four-component column state and the
two bras into a four-component row state; their outer product fills the
four-by-four expression grid. This is a construction from paired states—not a
two-by-two matrix stretched into a larger shape.

**Visual**

Show both equivalent views, with terms moving rather than cross-fading:

```text
(|W⟩⟨X|) ⊗ (|Y⟩⟨Z|)
          =
(|W⟩ ⊗ |Y⟩)(⟨X| ⊗ ⟨Z|)
```

Expand the left compound ket and right compound bra to four components. Show a
single outer-product entry before drawing the full 4×4 frame.

## 1:55–2:35 — Four components on each side

**Voiceover**

The four-by-four matrix has a four-component state on each side. In the
paper's measurement form, the row operand is bra Y followed by bra W, and the
column operand is ket X followed by ket Z.

That gives row labels Y-W and column labels X-Z, each ordered true-true,
true-false, false-true, false-false. The four variables appear across the two
sides: Y and W identify a row; X and Z identify a column. Together they identify
one of sixteen four-variable assignments.

**Visual**

Display the paper's measurement form and expand both compound state vectors:

```text
⟨Y|⟨W|  M  |X⟩|Z⟩

⟨Y,W| = [YW, Y¬W, ¬YW, ¬Y¬W]
|X,Z⟩ = [XZ, X¬Z, ¬XZ, ¬X¬Z]ᵀ
```

Cross one row and one column and show their four-literal cell expression. Add
the small clarification `4 components per side · 4 variables across both sides`.

## 2:35–3:32 — Follow the paper's worked example

**Voiceover**

The paper's example asks whether W exclusive-or X implies not-Y and Z. Compute
the two inner expressions first. The outer implication is false only when its
left side is true and its right side is false.

The tensor construction supplies the sixteen positioned combinations; the
outer operator selects the compound expressions; and positive valuation turns
them into bits. The resulting C M has rows: one-one-zero-zero;
one-one-one-zero; zero-zero-one-one; one-zero-one-one.

The labels must remain attached. Rows are ordered Y-W and columns X-Z. This
four-by-four object represents one compound four-variable rule. It is not one
of the elementary two-input operator C Ms.

**Visual**

Build `W XOR X` and `¬Y AND Z`, then feed both into implication. Track one false
case through a labeled 4×4 LM before revealing the valued result:

```text
[1 1 0 0]
[1 1 1 0]
[0 0 1 1]
[1 0 1 1]
```

Keep row headers `(Y,W)` and column headers `(X,Z)` present throughout.

## 3:32–3:58 — Retrieval

**Voiceover**

Pause on this cell. Before V sub T, it contains a logical expression. Which
object are we looking at?

*[Four-second retrieval pause.]*

An L M. Apply positive valuation and the same position becomes zero or one in
the C M. The frame shape did not decide the name; the entry type did.

**Visual**

Hold one identified cell fixed. On the answer, pass `V_T` through that cell and
change its badge from `LM entry: expression` to `CM entry: bit`.

## 3:58–4:25 — Higher dimensions and boundary

**Voiceover**

The paper extends this construction inductively. For two-n logical
subexpressions, it gives a square two-to-the-n by two-to-the-n L M, followed by
its positive valuation.

The next lesson uses a separate repository operation that arranges truth
outputs into ordered row-column layouts, including rectangles. For this paper
construction, retain the sequence: state-vector outer products, tensor smaller
L Ms, then positive valuation to a binary C M.

**Visual**

Grow `2×2 → 4×4 → 8×8` on a `paper construction` rail. Below a visible
separator, preview `repository row-column layout`. End on:
`outer product → tensor construction → LM → V_T → CM`.
