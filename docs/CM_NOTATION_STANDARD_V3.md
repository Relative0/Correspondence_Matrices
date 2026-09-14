# CM notation standard v3

Effective 2026-09-14. Additive successor: all rules in
[v2](CM_NOTATION_STANDARD_V2.md) remain applicable. Preserve v1/v2 standards and
frozen video packages. Brian requested this change for future videos only;
the completed nine foundation videos must not be regenerated for this feedback.

## Implication in every mathematical display

Use the **short double right arrow `⇒` (U+21D2)** for implication, including
between expressions. Brian denotes this in LaTeX as `\Implies`. The correct
bracketed implication CM remains `[⇒]`; the rule also applies outside brackets.
Do not use `→`, `\to`, or `\rightarrow` to express implication or inference.

Render the intended glyph, not raw LaTeX. If a renderer's `\Implies` command is
undefined or produces a long arrow, explicitly map it to the short
`\Rightarrow` glyph. Do not substitute `\Longrightarrow` or a stretched arrow.
For Unicode/HTML rendering, use `⇒` directly. Inspect the rendered result.

Keep the mathematical relation correct: use `=` between equal scalar values,
vectors, matrices, or equivalent expression values in a calculation. Do not
blindly replace every single arrow with implication. A spatial movement arrow
in a diagram may remain a diagram connector when clearly labelled; between
mathematical expressions use the appropriate equality, equivalence, or short
double implication symbol.

Apply this to future scripts, captions, figures, papers, lesson videos, and
derivation annotations. Check all single-arrow occurrences in authored math
and manually inspect representative expression transitions. The earlier XOR
`⇕`/`\Updownarrow`, bracketed operators, defined `[θ]`, and centered Impax rules
remain in force.
