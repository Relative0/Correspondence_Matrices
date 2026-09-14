# CM notation standard v2

Effective 2026-09-14. Additive successor to v1; preserve frozen versions.

- Logical exclusive-or: rendered `⇕` (U+21D5), LaTeX `\Updownarrow`.
  Never substitute `⊕` or `\oplus`. `\Updownoperator` in the feedback is
  interpreted as the established `\Updownarrow` symbol, not a new command.
- Name a numeric CM by its bracketed operator: `[⇕]`, `[∧]`, `[⇒]`, `[⇔]`.
  Pair the bracketed name with its complete numeric matrix and declared axes.
- `[θ]` is a placeholder for a chosen operator's CM. Define it before use, then
  show an explicit assignment such as `[θ] = [⇕] = [[0,1],[1,0]]`.
  The manuscript often writes uppercase Θ; the tutorial uses the user's θ.
- Do not introduce the undefined `M_⇕` alias. Measurement examples use
  `⟨0|[⇕]|1⟩`. Reserve M-based names for explicitly defined logical matrices
  or a clearly defined general matrix, such as `M_XY` or the paper's `[M]`.
- Impax is the centered overlay of `\Leftrightarrow` and `\Updownarrow`,
  enclosed in brackets when naming its CM. Its true-first numeric matrix is
  `[[1,1],[1,1]]`. The two glyphs must share both horizontal and vertical ink
  centers. An adjacent pair of arrows or a diagonal-cross substitute is wrong.
- Implication CM `[⇒]`: `[[1,0],[1,1]]`; reverse `[⇐]`: `[[1,1],[0,1]]`.
- The four basis CMs are `[∧]`, `[⇑]`, `[⇓]`, `[¬∨]`, in 11,10,01,00 order.
  Define the less familiar up/down operators by their complete numeric matrices.
- Projections use the paper's `[L]`, `[¬L]`, `[R]`, `[¬R]`. For X rows and Y
  columns, they represent X, ¬X, Y and ¬Y, respectively.
- In the displayed matrix products, pair entries with AND and combine products
  with XOR. This is not ordinary arithmetic addition or generic OR summation.
  Keep the intermediate row/column and the unprocessed operand visible.
- Distinguish a one-cell numeric result from an intermediate two-entry vector,
  a whole numeric CM, and an expression-valued LM. State vectors are rows for
  bras and columns for kets. Do not rename a complete LM as an unexplained ket.

Tutorial implementation: `docs/video_factory/cm_tutorial_visuals_v2.py` uses
the actual two arrow glyphs in an SVG and aligns their rendered ink boxes.
`cm_tutorial_layout_qa_v2.cjs` checks their center coordinates within 0.5 pixels.

An equivalent LaTeX overlay can be implemented with measured math boxes and
zero-width centered placement. Center both glyphs in the same math box; simply
placing one after the other, or aligning only their baselines, is insufficient.
