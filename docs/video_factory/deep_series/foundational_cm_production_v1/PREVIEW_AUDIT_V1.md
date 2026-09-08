# Foundational CM production preview audit — v1

Date: 2026-09-01  
Status: passed for silent-master rendering; final narration and mux remain pending

## Scope reviewed

- 3 revised scripts;
- 19 production scenes;
- 19 settled 960×540 frames;
- 3 short silent animatics;
- 1 mathematical symbol stress frame rendered twice;
- 10 required mathematical Unicode characters;
- exact operator, paper 4×4, and repository-coordinate values.

## Typography result

The renderer embeds DejaVu Sans and DejaVu Sans Mono in each HTML scene. The
actual font cmap was checked for `×`, `¬`, `∧`, `∨`, `⊕`, `→`, `↔`, `↦`, `₂`,
and `⁴`. All were present in both font files. Subscripts such as
`V<sub>T</sub>` and `M<sub>XY</sub>` use HTML positioning, while matrix brackets
are drawn borders rather than font glyphs.

The same symbol specimen was rendered twice with identical PNG hashes. The
RunPod job repeats both the cmap audit and the rendered specimen check inside
the target Linux environment before rendering any episode frames.

## Visual result

### Operator CMs

- Starts with one two-input grid rather than an unexplained gallery.
- AND is built from four identified cases.
- The sixteen-pattern gallery follows the visible `2×2×2×2=16` derivation.
- Named patterns and the implication swap remain readable at half-resolution.
- Retrieval leaves the XOR name hidden until the answer reveal.

### Logical matrices

- Expression-valued cells and binary cells use visibly distinct treatments.
- `V<sub>T</sub>` is a causal bridge rather than a detached label.
- The larger construction is shown as a functional sequence before technical
  notation.
- The paper example uses rows `YW: 11,10,01,00` and columns
  `XZ: 11,10,01,00`; valued rows are exactly `1100/1110/0011/1011`.

### Repository layout

- One tracked `1011 ↦ 1` card establishes the task before the full matrix.
- Ordered `R`, `C`, and MSB-first metadata visibly generate `(2,3)`.
- The 4×4 rows are exactly `0111/0111/0111/1000`.
- Repartitioning preserves the assignment-output pair while coordinates change
  through `(2,3)`, `(1,3)`, and `(5,1)`.

## Production boundary

The previews are sparse visual animatics, not finished videos. The exact remote
proposal covers only three 1920×1080 silent masters. Final narration must pass
a human voice audition; Windows SAPI is scratch timing only. Narration services,
mux, publication, commit, and push are not authorized by the render proposal.
