# CM website UX and progressive-disclosure pass — 2026-08-24

## Status

The publication site has been restructured following independent UX/UI,
venture-capital and engineering reviews. The changes reduce the initial text
load, make graphs the primary evidence surface, and keep the scientific limits
visible without requiring a reader to open anything.

This pass changes presentation and authored framing only. It does not change a
benchmark result or rerun the campaign.

Scientific source:

- evidence revision: `6e8a283d22fb7cf643753fb6ad2d7fc3f3f2c96f`;
- campaign revision: `eab8879edcb7fb13582ad9bdff7ea7c00238774d`;
- evidence date: 3 August 2026.

## Specialist review synthesis

The three reviews agreed on six priorities:

1. Align section introductions with the full-width card grid instead of forcing
   premature line breaks.
2. Keep one decision-useful paragraph visible in repeated boxes and move
   secondary explanation behind a predictable `More` control.
3. Put CM first in the toolbox while keeping BitSet and CSE results adjacent and
   explicit.
4. Lead graph cards with scope, baseline, conclusion and the visual; move the
   extended interpretation, table and provenance into an accessible dialog.
5. Frame CM's opportunity around expression identity, persistence, structural
   change and partial evaluation—not an unproved raw-speed advantage.
6. Make the investor sequence opportunity → evidence → economics → thesis risks
   → decision roadmap → audit credibility.

## Changes implemented

### Width and hierarchy

- Page and section introductions now use the full content width and align with
  the card-grid margins.
- Long technical material remains progressively disclosed rather than becoming
  a full-width wall of text.
- A three-part state panel now distinguishes validated evidence, implemented
  structural capabilities and the decisive next proof.
- An always-visible evidence-boundary strip preserves five non-negotiable
  caveats: strong-baseline parity, BitSet's whole-call lead, unmeasured
  production reuse, external-corpus scope, and the explicit-output guard.

### Cards and `More`

- Domain cards show title, question and one plain-language answer; the technical
  continuation is collapsed under `More`.
- Tool cards show name, role and `Question it answers`; superpower, cost,
  analogy and measured status are collapsed.
- CM is first/top-left, BitSet is second/top-right, and the remaining tools
  retain their previous order.
- Multi-paragraph plain-language blocks show their first paragraph initially.
- Technical layers, frontier consequences, investor downside cases, thesis-risk
  tests and corrections ledgers are collapsed by default.
- Controls change from `More` to `Less` when expanded and retain a minimum
  44-pixel touch target.

### Opportunity framing

- The master and investor pages now lead with three capability wedges:
  hardware verification/EDA, rules/policies/configuration, and
  compilers/symbolic reasoning.
- Each wedge pairs the problem, CM capability, evidence state and missing proof.
- Hardware is labelled `Measured expressions`, not a deployed-workflow
  validation. The other wedges are labelled `High-value hypothesis`.
- The full ten-domain catalogue remains available behind a single expandable
  control rather than appearing as an initial wall of cards.

### Graph interactions

- Every graph or DOM-based visual retains its scope, baseline and a concise
  takeaway in the card.
- Every visual opens the same native analysis dialog from either a graph click
  or an explicit `Explain this graph` button.
- Dialogs contain the complete caption, interpretation/decision boundary,
  plotted-value table and provenance.
- Close buttons restore focus to the opener; native dialogs support Escape;
  clicking the backdrop closes the dialog.
- Hover/focus value tooltips and the original expandable table/provenance views
  remain available.
- Print styling exposes the collapsed source content and removes interactive
  controls.

### Investor structure

- The opening statement now describes a tested structural layer and names the
  missing workflow-value proof.
- Three state cards and the evidence-boundary strip appear before detailed
  metrics.
- Five thesis risks are paired with the experiment that resolves each one.
- Section order is now opportunity, evidence, economics, thesis risks, roadmap,
  then audit credibility.

## Verification

The build was run twice without intervening edits and produced identical
SHA-256 hashes:

| output | SHA-256 |
|---|---|
| `cm_master_data_2026_08_03.json` | `3D828F0A690B2C1482FD3A837393F3BD15068A2EC4468828266AE04F293131B7` |
| `index.html` | `AD2623A8CF1319F412EAE34A0496801BB217685A7E458AB987BBBA718CB23FC4` |
| `layperson.html` | `527FBAC268E4D1133CC388F116AA98D17C3E2A95378F86B4C972743F9A0F9A21` |
| `investor.html` | `C71B4F383BE515881C07A30D558F398093F965A8E8CB336114B8F7414D495A71` |
| `expert.html` | `2893B6F351AD6124ABC5FABECDDA1650E3CA065AB99CA7B9AAA55B7DD00ECE12` |

Browser QA covered all four pages at 1280 × 900 and 375 × 812, plus master
and investor pages at 320 × 720:

- no horizontal body overflow;
- no unresolved `{{...}}` evidence tokens;
- no duplicate element IDs, broken same-page anchors or missing
  `aria-controls` targets;
- no browser warnings or errors;
- all graph cards have a concise caption, dialog and explicit analysis button;
- all `More` and graph-analysis controls meet the 44-pixel touch target;
- CM renders first in both the master and layperson toolboxes;
- individual card disclosure changes `More` to `Less` and does not open sibling
  cards;
- graph click and button activation open the full analysis; Close restores
  focus;
- analysis dialogs remain inside a 320-pixel viewport with their close control
  visible;
- section introduction and opportunity-grid right edges align exactly at the
  desktop test width.

Source checks passed:

- Python byte-compilation of `cm_master_build_2026_08_03.py`;
- JavaScript syntax checking of `cm_master_shared.js`;
- `git diff --check`.

## Remaining publication gates

1. Brian's visual/editorial review of the new default density and opportunity
   framing in a normal browser.
2. Choose the public origin and hosting route, add absolute canonical and
   social-preview URLs, and perform the final share-preview check.
3. Publish, update the public README URL and clearly label or archive older
   V4-era public pages.
4. Freeze this website source and then rebuild the PDF from the same current
   data/content source.
