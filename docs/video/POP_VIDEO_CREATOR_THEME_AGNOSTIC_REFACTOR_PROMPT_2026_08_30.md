# POP-Video-Creator theme-agnostic refactor — audit and agent prompt

Date: 2026-08-30  
Status: ready to copy into a new Codex task  
Target: `C:\Users\brian\Documents\PoP\Tools\POP-Video-Creator`

## Audit conclusion

The POP orientation is real. It is not caused by one hidden template; it comes
from several layers being coupled:

| Layer | Current coupling |
| --- | --- |
| Product and CLI | The README, module description, and CLI say the tool generates videos from POP project content. The only registered subjects are glyph/card/language subjects plus the recently added CRSE subject. There is no generic brief/spec planning command for arbitrary subject matter. |
| Directors/templates | “Templates” are mostly Python directors with fixed POP scripts and scene data. The foundational design proposed a `templates/` directory, but the current implementation does not have an independent generic template layer. |
| Default theme | `Theme()` is explicitly documented as the locked CCSGL card ground and supplies POP-adjacent dark colors and Windows-oriented fonts. All original directors instantiate that default. |
| Renderer | `render/html.py` mixes the generic virtual-clock runtime with glyph geometry, card art, language rails, POP-specific copy, fixed card/plate colors, and hard-coded layouts. |
| Scientific renderer | `render/crse.py` is editorially non-POP, but its dark technical palette, typography, gradients, spacing, and status chrome are hard-coded. It accepts a `Theme` argument but does not use it. Changing the spec theme therefore does not actually retheme CRSE scenes. |
| Scene contract | The closed scene-kind list is mostly domain-specific. Useful generic kinds exist (`title`, `section`, `stat`, `outro`), but they share a stylesheet and module with POP-specific scenes. |
| Assets | Asset loading safely restricts paths, but it restricts them to the built-in `pop_video/content` tree rather than an explicit, hash-bound content pack. |
| Integration | Master-Video-Creator exposes a `popvc` adapter and POP-specific subjects. That compatibility path can remain, but a neutral generator interface is needed for new work. |

The deterministic virtual clock, validated `VideoSpec`, frame driver, FFmpeg
encoder, provenance, narration opt-in, and encoded-output checks are reusable
and should be preserved. The correct change is to separate a neutral engine
from explicit theme, brand, content, and subject packs—not to discard the
working renderer.

“Theme agnostic” cannot mean that pixels have no typography, spacing, colors,
or motion rules. It should mean that the engine contains no hidden brand,
subject, editorial voice, or house-look choice. Every such choice must come
from an explicit, inspectable, hash-bound input. New specs should name a theme;
legacy POP subjects should explicitly select a legacy POP theme/content pack.

## Copy-paste prompt

```text
Act as the lead architect and implementation engineer for a compatibility-safe,
theme-agnostic refactor of POP-Video-Creator.

PROJECT

C:\Users\brian\Documents\PoP\Tools\POP-Video-Creator

RELATED INTEGRATION TO INSPECT AFTER THE CORE WORKS

C:\Users\brian\Documents\PoP\Tools\Master-Video-Creator

PRIMARY OBJECTIVE

Turn POP-Video-Creator into a genuinely subject-, theme-, and brand-agnostic
deterministic video engine while preserving all current POP/card/glyph/language
outputs as an explicit legacy content/theme pack. New videos must not inherit
POP wording, glyph/card imagery, graphite styling, colors, fonts, mastheads,
status straps, animation vocabulary, or editorial tone unless their brief
explicitly selects those assets or that pack.

Build the refactor and prove it with working renders. Do not stop at renaming
classes, moving constants, or adding a `--theme` flag that most renderers
ignore.

DEFINITION OF DONE

The engine is theme agnostic when all of the following are true:

1. Core planning/rendering/encoding modules do not import POP cards, glyphs,
   CCSGL roots, CRSE evidence, or any branded asset/content director.
2. Every aesthetic or brand-bearing choice is supplied by an explicit resolved
   theme, optional brand pack, scene data, or content pack and is recorded in
   the spec and manifest.
3. The same generic video brief/spec renders under at least three materially
   distinct themes without changing Python or scene data.
4. A neutral render contains no POP/CCSGL/card/glyph text, image, logo, palette,
   disclaimer, or provenance unless the input explicitly requests it.
5. Existing saved version-1 POP specs and current POP CLI commands continue to
   render with their intended legacy appearance and semantics.
6. CRSE/scientific scenes use theme tokens rather than their current hard-coded
   dark technical CSS, so the same CRSE scene can render in a neutral light or
   other explicitly selected theme.
7. Theme selection changes pixels and is covered by encoded-frame tests; it is
   not merely metadata.

Theme agnostic does not mean “un-designed.” A rendered spec must resolve to a
complete visual system. The requirement is that the engine does not silently
choose a POP or other house identity. New versioned specs should explicitly pin
their resolved theme. A neutral reference theme is allowed as an explicit
fixture and CLI choice, not as an undocumented internal bias.

OPERATING AND SAFETY RULES

1. Read the full project `CLAUDE.md`, README, and all relevant design contracts
   before editing. `docs/10-reading-templates.md` is mandatory before touching
   a reading or its compatibility path.
2. Begin read-only. Record root, repository root, branch/HEAD if available,
   interpreter/tool versions, and `git status --short`. The shared Tools
   repository already contains unrelated and possibly uncommitted work,
   including the CRSE additions. Preserve it. Never reset, restore, clean,
   reformat, stage, commit, or push unless Brian explicitly asks.
3. Inspect the exact current diff for `pop_video/cli.py`, `pop_video/spec.py`,
   `pop_video/render/html.py`, and all untracked CRSE files before designing
   edits. Treat those changes as user work; integrate rather than overwrite.
4. Do not read or expose `.env*`, voice credentials, token caches, private keys,
   or local databases. Do not make a paid voice/model call. Narration stays off
   for proof renders.
5. Use the project's established deterministic rules: frames are pure functions
   of progress, no wall clock, no CSS transitions/keyframes, no
   `requestAnimationFrame`, fixed seeds, and encoded-frame inspection.
6. Use the project interpreter/dependencies. If no project virtualenv exists,
   report the actual interpreter used rather than inventing one or modifying
   global packages without approval.
7. Prefer small migration steps and compatibility adapters. Do not perform a
   repository-wide package rename merely to make the name sound neutral.
8. No external publication, upload, cloud resource, or RunPod work is part of
   this task.

CURRENT COUPLING TO VERIFY

Confirm these findings against the current files before implementation:

- `pop_video/spec.py`: `Theme` defaults are explicitly the locked CCSGL card
  ground and a fixed dark palette/font stack.
- `pop_video/cli.py`: help text and subject registry are POP/content-specific;
  there is no generic `plan <brief>` or plugin discovery surface.
- `pop_video/render/html.py`: the generic virtual-clock runtime and base CSS
  share a module with direct glyph imports, locked plate/card constants,
  domain-specific scene builders, and some hard-coded POP/language copy.
- `pop_video/render/crse.py`: `build_crse(data, theme)` accepts `theme`, but
  colors, typography, surfaces, gradients, spacing, and chrome are all fixed in
  module constants/CSS.
- the original directors instantiate `Theme()`; `root_language` changes only
  the accent; `crse_neural` defines its own fixed theme.
- the scene-kind literal and `_BUILDERS` registry are closed and centrally
  edited for every new content family.
- `asset_data_uri()` provides useful path safety but only resolves built-in
  content rather than a declared pack root with asset hashes.
- the docs call Python directors “templates”; a separate generic, data-driven
  template system does not currently exist.

If a finding has already changed, document the current state and adapt the
implementation. Do not preserve an obsolete diagnosis just because it appears
in this prompt.

PHASE 0 — BASELINE AND ARCHITECTURE DECISION RECORD

Before editing:

- capture concise current state and relevant diffs;
- run the focused fast suite and, if practical, the documented full baseline;
- plan/render tiny existing fixtures without narration to establish behavior;
- record hashes or perceptual baselines for representative legacy scenes:
  generic title/stat, glyph, card/reading, language, and CRSE;
- inspect existing spec and manifest compatibility expectations.

Write an ADR describing:

- the boundary between neutral engine, theme pack, optional brand pack, content
  pack, subject director, scene primitive, frame driver, encoder, and voice;
- migration strategy for version-1 specs and current CLI commands;
- theme resolution and hashing;
- asset roots and trust boundary;
- scene/plugin registry strategy;
- why a package-wide rename is accepted or rejected;
- dependency direction rules and how tests enforce them;
- rejected shortcut: merely adding more fields to the current `Theme` while
  hard-coded CSS and content imports remain.

Preferred architecture unless inspection identifies a stronger compatible
fit:

  neutral engine
    ├── spec + validation + registries
    ├── deterministic runtime + frame driver + encoder
    ├── generic scene primitives
    └── explicit theme/brand/content resolution

  packs
    ├── themes/neutral_light
    ├── themes/neutral_dark
    ├── themes/technical_reference
    ├── themes/pop_legacy
    ├── content/pop_cards_glyphs_language
    └── content/crse (evidence/director only; visuals use generic primitives)

Keep `python -m pop_video ...` as a compatibility entry point. Internal neutral
modules may remain under the `pop_video` package; neutrality is a dependency
and input property, not a cosmetic directory name.

PHASE 1 — EXPLICIT THEME, BRAND, AND CONTENT CONTRACTS

Introduce strict, versioned contracts. Match surrounding Pydantic/schema style.
Use names that fit the codebase, but cover these concepts:

1. `ThemeManifest`

- stable ID, display name, schema version, theme version, provenance/license;
- colors by semantic role rather than component-specific guesses:
  canvas, surface levels, primary/secondary text, muted text, rule, focus,
  accent series, information, success/verified, warning/conceptual,
  error/failed, neutral/fallback, data-series colors;
- typography: bundled/fingerprinted families or explicit portable stacks,
  weight/size/line-height/letter-spacing scales, numeric/monospace role;
- geometry: safe zones, spacing scale, max content widths, border widths,
  radii, shadows, grid/gutter rules;
- motion: named reveal families, offsets, easing constants, default durations,
  stagger/cadence limits, reduced-motion policy;
- chrome: title, caption, source footnote, status label, counter, and outro
  component tokens;
- accessibility metadata and contrast assertions;
- optional component overrides where semantic tokens are insufficient.

2. `BrandManifest` (optional and absent by default)

- display name, logo/mark asset, legal/footer copy, placement and safe zone;
- theme compatibility and provenance;
- no automatic logo or brand name when no brand manifest is selected;
- theme packs must not smuggle branding into default strings or assets.

3. `ContentPackManifest`

- stable ID/version, source/provenance, subject/director registrations, custom
  scene registrations, validators, declared asset roots and file hashes;
- no ability to resolve outside its declared roots;
- status/disclaimer copy belongs to the content/brief, not the neutral engine;
- POP and CRSE packs are explicit and independently selectable.

4. `SceneRegistry` / plugin contract

- generic builders registered by the core;
- content-specific builders registered by packs without editing one global
  `_BUILDERS` dictionary or `SceneKind` literal for every extension;
- strict scene-data validation owned beside the builder;
- collision refusal for duplicate kind IDs;
- deterministic ordered registration and manifest reporting;
- no dynamic arbitrary-code loading from untrusted spec paths.

5. Resolved render context

- every scene builder receives one immutable `RenderContext` containing the
  resolved theme, optional brand, dimensions, fps, safe zones, and asset
  resolver;
- builders do not reach into global palettes, fonts, paths, or environment
  variables for visual decisions;
- the manifest records theme/content/brand IDs, versions, hashes, source files,
  asset hashes, and the fully resolved pixel-affecting token snapshot.

Make the models strict enough to reject misspelled/unknown token fields. Add
semantic validators: colors, contrast, nonnegative spacing, safe-zone bounds,
font declarations, motion limits, unique IDs, and referenced asset hashes.

PHASE 2 — SPEC VERSIONING AND COMPATIBILITY

Do not silently reinterpret existing specs.

- Preserve the version-1 loader and its exact legacy meaning. A v1 spec with
  the historical inline `Theme` must render through a `pop_legacy_v1`
  compatibility resolver or equivalent so old files retain their appearance.
- Add a new spec version only if necessary. New specs must explicitly carry a
  resolved theme identity/hash or an embedded immutable resolved snapshot.
- A new spec must not depend on “whatever the theme named X contains today.”
  Resolution happens at plan time and is pinned for deterministic re-rendering.
- Existing checked-in specs are build artifacts: do not bulk rewrite them.
- Existing manifest omission/shape behavior for legacy silent videos must
  remain compatible where tests require it; put new identity fields in the new
  version/manifest path rather than retroactively changing old hashes.
- Add an explicit migration/inspection command that can show how a v1 spec
  would map to the new model without overwriting it. Migration writes only to a
  new path and records the source hash.

For new planning commands, require a visible theme choice. Acceptable UX:

  python -m pop_video themes list
  python -m pop_video packs list
  python -m pop_video scenes list
  python -m pop_video plan-brief brief.json --theme neutral_light
  python -m pop_video render-spec spec.json

Exact command names may follow current Typer conventions. The essential point
is that a new arbitrary-subject brief does not pass through a POP director.
Legacy commands such as `make reading` should explicitly select the POP legacy
pack/theme internally and state that choice in the plan summary/manifest.

PHASE 3 — EXTRACT THE NEUTRAL CORE

Separate modules by dependency direction. Do the work incrementally so tests
stay reviewable.

Core may contain:

- base spec models and registries;
- generic scene validation and HTML/SVG helpers;
- the virtual-progress JavaScript runtime;
- safe text/asset handling;
- frame scheduling/Playwright driver;
- FFmpeg encoder and technical provenance;
- narration interface/opt-in boundary, without a POP editorial voice.

Core must not import:

- `content.cards`, `content.glyphs`, `content.roots`;
- POP card art, palettes, geometry, or fixed root inventories;
- CRSE evidence paths/directors;
- a POP/CCSGL disclaimer or brand string;
- a theme-specific stylesheet with hidden fixed colors/fonts/layout chrome.

Extract a small generic scene library from the useful existing work:

- title, section, text/caption, stat/metric cards, table, matrix/grid, graph,
  pipeline/process, split comparison, image, source/status footnote, outro;
- generic animation hooks continue to use virtual progress;
- every builder reads all theme-bearing values through `RenderContext`;
- copy such as `CONCEPTUAL`, `EXPERIMENTAL`, “Current glyph inventory,” or
  “Building a six-glyph reading” is scene data owned by a brief/content pack,
  not core renderer text;
- fixed functional values such as `transparent` may remain only when they are
  not aesthetic choices and are documented. Black/white/dark blue are still
  aesthetic choices and belong to a theme.

Split the current monolithic `render/html.py` by concern without gratuitously
rewriting its validated geometry. The POP glyph/card builders can initially
remain largely intact inside the POP pack. The objective is a clean dependency
boundary, not forcing highly specialized card geometry into generic tokens.

PHASE 4 — MAKE CRSE/SCIENTIFIC PRIMITIVES ACTUALLY THEMEABLE

Refactor `render/crse.py` carefully; it is current uncommitted work.

- Replace module constants such as cyan/violet/amber/verify/slate/fallback with
  semantic theme roles supplied by `RenderContext`.
- Replace the fixed background gradient, surfaces, borders, text colors,
  fonts, spacing, radii, and caption/footer chrome with theme/layout tokens.
- Remove the unused-theme behavior. Add a test that changes sentinel theme
  values and proves every appropriate CRSE component consumes them.
- Separate scientific meaning from decoration. For example, truth=1,
  operator, learned proposal, exact verification, failure, and fallback are
  semantic data roles; their actual colors come from the theme.
- Preserve redundant labels/shapes so color is not the only carrier of
  meaning.
- Move CRSE visuals toward generic matrix/graph/pipeline/table/metric scene
  primitives. Retain a CRSE content director for evidence selection and exact
  copy, not a hard-coded CRSE house renderer, when that can be done without
  destabilizing the proof set.
- Remove the hard-coded evidence-root default from portable runtime behavior;
  require an explicit/configured evidence root with a clear error. Do not read
  or bundle unrelated CM files.

Prove the same CRSE scene under at least `technical_reference` and
`neutral_light`, with unchanged scientific scene data and claim provenance.

PHASE 5 — MOVE POP IDENTITY INTO AN EXPLICIT LEGACY PACK

Keep all real POP-specific requirements, but make their ownership honest:

- glyph geometry/taper, CCSGL plate, card ground, art, root palettes,
  card/reading layouts, language rail, scripts, and provenance disclaimers
  belong to the POP content/theme pack;
- `pop_legacy` captures the exact historical colors, fonts, layout constants,
  animation treatments, plate/ground choices, and chrome needed by old specs;
- POP subjects explicitly select the POP pack and legacy theme unless the
  subject contract deliberately supports safe retheming;
- do not pretend physical card/glyph identity tokens are generic theme knobs.
  The graphite plate may correctly remain locked inside the POP glyph
  component because it is content/identity, as long as neutral scenes never
  import or receive it;
- preserve the two reading templates, narration timing, glyph-reveal behavior,
  status semantics, and existing tests;
- preserve claim/provenance warnings even when an operator deliberately hides
  the on-picture strap; theme refactoring must not weaken research status.

Compatibility is measured from existing specs and encoded frames. If exact
pixels cannot be preserved because of a justified dependency split, document
the minimal delta, render representative before/after encoded frames, measure
it, and ask Brian before accepting a legacy visual change.

PHASE 6 — GENERIC BRIEF/DIRECTOR PATH

Add a data-driven input path for arbitrary subject matter. The renderer should
not invent a POP-oriented script because the only available directors are POP
directors.

Define a strict generic `VideoBrief`, for example:

- title, subject ID, audience, purpose, dimensions/fps;
- explicit theme ID/version and optional brand ID/version;
- ordered scenes using generic scene types;
- all visible copy and optional narration supplied in the brief;
- assets through declared pack/file references and hashes;
- source/status/citation data;
- no automatic POP footer, kicker, disclaimer, CTA, wording, or content;
- deterministic content hash.

Planning a brief should validate and resolve it into a complete immutable spec.
It does not need an LLM. Do not solve theme bias by adding a new LLM whose
system prompt may introduce a different hidden style. If an LLM director is
added later, it must output this same validated brief/spec contract and theme
selection must still be explicit.

Provide helpful discovery commands and plan output showing:

- chosen theme/brand/content pack and their hashes;
- scene kinds and their owners (core or named pack);
- assets and roots;
- duration/frame count;
- visible status/source labels;
- whether narration is off/on and whether any paid provider would be used.

PHASE 7 — MASTER-VIDEO-CREATOR ADAPTER

After the neutral engine and compatibility suite pass, inspect IVC's current
`popvc` generator. Make only the minimal compatible integration change:

- retain `popvc` for explicit POP legacy subjects;
- add a neutral/spec-driven generator name or request mode for generic briefs;
- remove misleading generic descriptions such as “dark POP style” from neutral
  generators;
- make theme/content pack selection and hashes part of request validation and
  cache identity;
- keep current POP requests working;
- do not hard-code the Windows project path; use explicit configuration or a
  portable resolved project/interpreter contract;
- add focused adapter tests, but do not refactor unrelated IVC production code.

If IVC has overlapping generic theme/scene capabilities, record the boundary in
the ADR rather than duplicating them. IVC should orchestrate/assemble; this
project should deterministically render its declared scenes.

PHASE 8 — PROOF RENDERS

Produce a small proof matrix using silent, deterministic, low-cost local
renders. Inspect frames from encoded MP4s, not only HTML.

Proof A — generic, unrelated subject

- Use a neutral subject unrelated to POP, CM, CRSE, cards, or glyphs, such as
  “How a task queue processes three jobs.”
- Use only generic title, pipeline, metric/table, comparison, caption/source,
  and outro primitives.
- Render identical scene data under:
  1. `neutral_light` — restrained editorial/documentary look;
  2. `neutral_dark` — distinct but non-POP neutral look;
  3. `technical_reference` — denser technical look.
- The outputs must be materially different in theme but identical in factual
  copy, timing, scene order, and data.
- No rendered frame/spec/manifest may contain POP, PoP, CCSGL, glyph, card,
  graphite, or a POP asset/provenance value.

Proof B — legacy POP compatibility

- Render representative existing title/glyph/card/reading/language scenes from
  saved version-1 specs through `pop_legacy` compatibility.
- Compare against baseline encoded frames with the project's established
  visual tolerance.
- Confirm narration remains off and manifests retain legacy-compatible shape.

Proof C — scientific retheming

- Render one unchanged CRSE/scientific scene under `technical_reference` and
  `neutral_light`.
- Scientific semantic roles and labels remain correct while colors,
  typography, surfaces, spacing/chrome, and other declared theme aspects change.
- Confirm no POP content appears unless explicitly present in the brief.

For each proof retain spec/brief, theme/pack manifests, output MP4, provenance,
ffprobe report, opening/middle/final encoded frames, contact sheet, exact
command, and a short visual review record.

TEST STRATEGY

Add tests at these layers:

1. Contract tests

- strict valid/invalid theme, brand, content-pack, scene, brief, and spec
  fixtures;
- stable normalization/hash behavior;
- unknown tokens, path escape, missing assets, hash mismatch, duplicate scene
  registration, and conflicting pack IDs rejected;
- accessibility/contrast and safe-zone validation.

2. Dependency-boundary tests

- neutral core import graph contains no POP/CCSGL/CRSE content modules;
- generic render works when POP packs are unavailable;
- POP pack removal causes a clear “pack missing” error only for POP specs;
- no core source contains subject-specific default copy or branded asset paths.

3. Theme-consumption tests

- a sentinel theme with conspicuous unique values proves generic builders and
  CRSE/scientific builders consume declared tokens;
- scan generated neutral HTML/CSS for known legacy hard-coded palette/font and
  POP strings, allowing only explicitly documented non-aesthetic values;
- changing a pixel-affecting token changes the spec/cache identity;
- changing metadata that cannot affect pixels follows the documented identity
  rule.

4. Visual tests

- same generic spec under three themes is materially different;
- each theme is deterministic within the existing Chromium tolerance;
- legacy scenes remain within baseline tolerance;
- encoded frames have no clipping, overlap, unsafe text, missing fonts, or
  accidental logo/status strap;
- theme contrast and color-role redundancy survive rasterization.

5. Regression tests

- current POP subject/CLI/reading/layout/glyph/voice tests;
- current CRSE tests;
- render/encoder/provenance and silent-output compatibility;
- IVC adapter tests if that project is touched.

Run focused tests during development and the documented complete suite before
completion. Report pre-existing failures separately. Do not update snapshots
merely to make failures disappear; inspect every intentional visual delta.

ACCEPTANCE GATES

Do not call the refactor complete unless:

- the ADR and dependency boundaries exist and match the code;
- new arbitrary-subject videos have an explicit theme and no implicit POP
  content path;
- no neutral core module imports a branded/domain content module;
- base and scientific scene builders are driven by resolved theme tokens;
- no theme argument is accepted and ignored;
- themes, brands, content packs, scene registrations, assets, and briefs are
  hash-bound and visible in provenance;
- the generic unrelated proof renders successfully in three themes;
- the CRSE proof visibly rethemes without data changes;
- legacy POP proofs remain compatible;
- existing and new tests pass or failures are plainly reported;
- encoded representative frames were inspected;
- no secrets, paid calls, external writes, commits, or pushes occurred;
- final `git status --short` and `git diff --stat` distinguish pre-existing
  shared-repository changes from this task's changes.

DELIVERABLES

1. architecture/coupling audit and ADR;
2. versioned theme, brand, content-pack, scene-registry, brief, and resolved
   render-context contracts;
3. neutral core dependency split;
4. generic scene library and explicit brief planning path;
5. `neutral_light`, `neutral_dark`, `technical_reference`, and `pop_legacy`
   themes with provenance and tests;
6. explicit POP legacy content pack;
7. themeable CRSE/scientific primitives;
8. version-1 compatibility and non-destructive migration/inspection support;
9. three proof groups with encoded-frame review artifacts;
10. focused IVC adapter compatibility update if needed;
11. test report, visual-delta report, and precise final change inventory;
12. concise user documentation showing how to create a new non-POP video
    without touching Python.

HANDOFF STYLE

Lead with the outcome. State what coupling was removed, how legacy POP behavior
is preserved, exact commands for a generic video and for a legacy POP video,
proof locations, tests and results, any intentional visual differences, and
remaining limitations. Do not say “theme agnostic” merely because several
palettes exist; demonstrate that content, brand, layout, typography, chrome,
and motion choices are explicit and replaceable.
```

## Expected architectural result

The desirable end state is not “POP styling turned off.” It is:

```text
generic brief + explicit theme + optional brand/content packs
        ↓
validated, fully resolved, hash-bound video spec
        ↓
neutral deterministic renderer/runtime
        ↓
frames + MP4 + provenance

POP legacy brief + pop_legacy theme + POP content pack
        ↓
the same core runtime, preserving existing POP behavior
```

This makes POP one supported identity rather than the renderer's implicit
identity. It also prevents the opposite failure: replacing a POP bias with one
new mandatory “technical dark” bias.
