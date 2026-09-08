# Narration and mux plan — foundational CM production v1

Status: prepared; final voice not selected; no narration service authorized

## Voice policy

The final narration must sound conversational, varied, and teacherly. Windows
SAPI is permitted only for cue timing and must not be released as final audio.
Before final mux, audition at least three 20–30 second readings drawn from:

1. the four-case definition in the operator-CM lesson;
2. the positive-valuation explanation;
3. the `1011 → (2,3)` coordinate explanation.

Choose one voice across all three episodes. Judge warmth, phrasing, symbol
pronunciation, and whether the reader distinguishes definition from emphasis.
Any cloud or paid voice service requires a separate exact authorization.

## Spoken/display separation

The screen may display mathematical notation while the narration uses natural
speech:

| Display | Speak |
|---|---|
| `CM` | “C M” |
| `LM` | “L M” |
| `X ⊕ Y` | “X exclusive-or Y” |
| `V<sub>T</sub>` | “V sub T” |
| `2⁴` | “two to the fourth power” |
| `M[2,3]` | “M of two comma three” |
| `1011 ↦ (2,3)` | “one-zero-one-one maps to row two, column three” |

Do not ask a speech engine to infer pronunciation from the Unicode display
string. Narration contracts contain normalized spoken text.

## Final mux and QA

- 48 kHz mono narration, AAC in the episode master.
- Preserve the 1920×1080, 30 fps silent visual master without retiming frames.
- Fit narration by performance and pauses, not speech time-compression.
- Add sidecar WebVTT and an embedded subtitle track.
- Verify stream codecs, duration, cue bounds, decoded opening/middle/final
  frames, captions, peak level, and absence of clipping.
- Publication remains a separate authorization.
