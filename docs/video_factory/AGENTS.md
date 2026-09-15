# CM video authoring conventions

Follow `../CM_NOTATION_STANDARD_V2.md` in new and successor video work.
Keep all frozen production/review packages immutable.

- Introduce `[θ]` before using it as a placeholder for an operator CM.
- Display each named CM with its bracketed operator symbol and complete numeric
  array under declared axes. Do not invent an undefined `M_⇕` alias.
- Render Impax by centering the actual `⇔` and `⇕` glyphs on both axes.
- Teach measurements as row–CM–column calculations: AND the paired entries and
  XOR the resulting products. Show intermediate vectors before the scalar answer.
- Teach numeric measurements before symbolic derivations and LM measurement.
- Keep a separate playable MP4 for each lesson, with a clear local review index.
- Verify manuscript examples independently before teaching them. A source image
  is evidence of what was printed, not a substitute for checking its algebra.

## General presentation refinements (Brian, 2026-09-16)

- In row–CM–column displays, vertically center both vector arrays on the CM's
  numeric/symbolic cell block. Position names and axis labels separately so they
  cannot shift the visual center of an operand.
- When demonstrating a calculation, highlight every participating operand.
  Match each AND pair to its product with consistent colors plus outlines or
  labels; identify the products combined by XOR. Distinguish entrywise AND/XOR,
  tensor products and row-by-column contraction. Keep practice answers hidden.
- When introducing numbers of assignments or possibilities, show a compact
  derivation in available space: k independent Boolean inputs give 2^k
  assignments; r row bits and c column bits give 2^r × 2^c = 2^(r+c) cells.
  Distinguish this from the 2^(2^k) possible Boolean functions. Do not write
  “number of variables × states per variable” as the general counting rule.
- Apply these conventions to successor artifacts and future authoring; preserve
  frozen historical videos, narration and packages.
