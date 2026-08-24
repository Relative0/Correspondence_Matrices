# CM website publication stabilization — 2026-08-24

## Status

The first publication-preparation pass is complete. The website is preserved in
baseline commit `17ad2c7`, rebuilt from the latest local evidence, and ready for
editorial sign-off. It has not been publicly hosted or pushed by this pass.

The targeted graph and editorial recommendations from that sign-off list were
subsequently implemented and verified. See
`CM_WEBSITE_VISUAL_EDITORIAL_EXPANSION_2026-08-24.md` for the current visual
inventory, deterministic hashes, and remaining gates.

The scientific source is unchanged:

- evidence revision: `6e8a283d22fb7cf643753fb6ad2d7fc3f3f2c96f`;
- campaign revision recorded by the evidence manifest:
  `eab8879edcb7fb13582ad9bdff7ea7c00238774d`;
- evidence date: 3 August 2026.

## Changes in this pass

1. **Stable provenance.** The builder now records `evidence_revision` and
   `campaign_revision`. It no longer inserts the checkout's current Git HEAD
   into generated data, which previously made the build change merely because
   the generated site had been committed.
2. **Mobile navigation.** All four pages now expose their navigation through a
   responsive menu below 640 px. The button reports expanded state, links close
   the menu after use, and Escape closes it and restores focus.
3. **Publication metadata.** All pages now carry page-specific Open Graph title,
   description, type, and large-card metadata. `og.png` is the shared 1200 × 630
   publication artwork and favicon source.
4. **Generated outputs refreshed.** `index.html`, `layperson.html`,
   `investor.html`, `expert.html`, and `cm_master_data_2026_08_03.json` were
   regenerated from the same evidence and shared source files.
5. **Repository discovery.** The root README now links to the master site, the
   three audience cuts, the authoritative claim map, and the build reports.

An absolute `og:image` URL and canonical page URLs are deliberately deferred
until the public origin is chosen. Adding a guessed origin now would create
incorrect share previews later.

## Verification

The builder was run twice without intervening edits. All generated outputs were
byte-for-byte stable on the second run:

| output | SHA-256 |
|---|---|
| `cm_master_data_2026_08_03.json` | `1EC1A6255F72B0D2C9F2797F0917608C1C88F65B94B0B637A6FA6FDE0053297D` |
| `index.html` | `729FE25973836024B4B5B50D6BA5F6D4DD63D9FDE481293F03E879130DDBF843` |
| `layperson.html` | `0492ACA68D7353E17CA56C2E3CE6096316ACE6EE224C5093CEF20DE00AA42B1A` |
| `investor.html` | `13F748CB18527715FB5C9ECC65AC6AB6709D1BC6078B8409BACAF2E6900FB430` |
| `expert.html` | `B8FAA0A439D0A1CC5970695F16C73E134A11EA300A50A14D18EC53A82A09FDEA` |

Browser QA:

- desktop, 1280 × 720: 18 SVG charts, 21 tables, no horizontal body
  overflow, no unresolved tokens, and no console warnings or errors;
- mobile, 375 × 812: all four pages have no horizontal body overflow, expose
  the menu, contain no unresolved tokens, and produce no console warnings or
  errors;
- the master mobile menu opens to all eight sections, reports its expanded
  state correctly, and closes with Escape;
- `og.png` loads successfully and removes the former missing-favicon request.

No benchmark or production-code test was rerun because this pass changes only
the static publication build and its generated pages. The website build and
browser checks are the tests for the touched surface.

## Remaining publication gates

1. Brian's final visual/editorial sign-off on the expanded master and audience
   cuts. The previously listed §4, §5, §6, break-even and audience-cut work is
   implemented in the follow-on visual/editorial pass.
2. Choose the exact public origin and hosting route. Then add absolute canonical
   and `og:image` URLs, run one final link/share-preview check, and publish.
3. Add the final public URL to the README and archive or clearly label the older
   V4-era public pages so searchers cannot mistake them for the current result.
4. Rebuild the PDF from this same data/content source after the website is
   editorially frozen.
