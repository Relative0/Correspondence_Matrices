# CM website visual and editorial expansion — 2026-08-24

## Status

The recommended publication visuals are implemented across the master explainer
and all three audience cuts. The pass does not change a benchmark result or
rerun the campaign: every numeric visual is generated from the same evidence
payload as the existing charts, and qualitative roadmap categories are labelled
as authored categories rather than measured timings.

A later UX pass added progressive disclosure, graph-analysis dialogs and a
restructured investor narrative without changing those visuals or their
evidence. See `CM_WEBSITE_UX_PROGRESSIVE_DISCLOSURE_2026-08-24.md` for the
current generated hashes and browser checks.

Scientific source:

- evidence revision: `6e8a283d22fb7cf643753fb6ad2d7fc3f3f2c96f`;
- campaign revision: `eab8879edcb7fb13582ad9bdff7ea7c00238774d`;
- evidence date: 3 August 2026.

## Recommendations implemented

1. **Master §4, “Which is better when”.** Added a five-card decision atlas
   covering one-shot evaluation, reuse, internal-engine selection, canonical
   symbolic work, and real AND/INV circuits. Each recommendation names the
   matched evidence signal; the original detailed charts remain immediately
   below it.
2. **Master §6 corrections and discrepancies.** Retained the full corrections
   ledger, replaced the audit-chain table with a visual 14-pass evidence
   ladder, and added a two-part discrepancy visual. It shows where the old
   “about 1–2%” schedule wording fails and compares archived with fresh
   preparation and break-even values.
3. **Baseline-matched break-even view.** Split the economics figure into a
   conclusion-first finite-versus-never summary and the full finite-case
   distribution. Synthetic and EPFL rows against plain CSE are explicitly
   matched; the stricter EPFL-versus-CSE-flat row is labelled as a different
   question.
4. **Master §5 open frontier.** Added evidence-state lanes for all ten open
   questions and a priority/effort roadmap. Downside cases remain available in
   the expandable table and in the audience-specific cards.
5. **Layperson page, end to end.** Added explicit-output growth, the decision
   atlas, the baseline-matched break-even outcome view, the frontier map, and
   the audit ladder. The page now carries the full argument visually from scale
   through tool choice, economics, uncertainty, and trust.
6. **Investor roadmap and downside cases.** Replaced the prose roadmap table
   with the sourced priority/effort chart, added the frontier evidence-state
   map ahead of the downside cards, and surfaced the discrepancy visual beside
   the corrections ledger.

All visual cards begin with the conclusion in the title or caption and expose
both a complete table view and provenance. SVG plots carry accessible labels;
DOM-based infographics preserve the same text in the document rather than
embedding it in an image.

## Generated visual inventory

| page | sourced visual cards | SVG plots | visual cards with captions | visual cards with provenance |
|---|---:|---:|---:|---:|
| Master knowledge base | 23 | 22 | 23 | 23 |
| Plain-language version | 5 | 2 | 5 | 5 |
| Investor brief | 9 | 7 | 9 | 9 |
| Expert summary | 21 | 21 | 21 | 21 |

Some cards use a responsive HTML infographic rather than SVG, and some contain
two SVG panels, so card and SVG counts are intentionally not identical.

## Verification

The build was run twice without intervening edits. The five generated outputs
were byte-for-byte stable:

| output | SHA-256 |
|---|---|
| `cm_master_data_2026_08_03.json` | `646439FF223A419681D05CF44DA290561C5EAF37AA20255EF57C488B1C4AEB73` |
| `index.html` | `3B09BFABDBAD4CA02F609F2DA684A4F338AF7CD45D25E40492B309AB0420F642` |
| `layperson.html` | `3002C200CB6476ECEF893759DD4636807B0058D5BBC46E32AED40011FF533FC0` |
| `investor.html` | `D181F432643ECDD8DF3D9308D1EE928B4E393C9EFCAC1A8CDB7353494E5E8275` |
| `expert.html` | `4B24B432A4EE0E9D9BAFC36C5D2EE3ACE9C4F4B522C1B44F9E84E4056719475E` |

Browser QA covered all four pages at 1280 px and 375 × 812 px:

- no body-width overflow;
- no unresolved `{{...}}` evidence tokens;
- no missing same-page section anchors;
- every visual card has an interpretation caption and provenance;
- every SVG has an accessible label;
- the mobile menu opens from zero visible links to all eight master sections
  and reports `aria-expanded="true"`;
- no console warnings or errors.

Source checks also passed:

- Python byte-compilation of `cm_master_build_2026_08_03.py`;
- JavaScript syntax checking of `cm_master_shared.js`;
- `git diff --check`.

## Remaining publication gates

1. Final human visual/editorial review in a normal browser, with particular
   attention to preferred chart density and caption tone.
2. Choose the exact public origin and hosting route, then add absolute canonical
   and social-preview URLs and run the final share-preview check.
3. Publish and add the public URL to the root README; archive or clearly label
   older V4-era public pages.
4. After the website is frozen, rebuild the PDF from the same current
   data/content source.
