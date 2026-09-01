# CM video factory

This directory is the Level 1 evidence/editorial authority for three local CM
proofs and the proposed later catalog. JSON is authoritative; Markdown is
generated for review. No command here authorizes a paid service or cloud write.

Use Master-Video-Creator's checked-in Python because it already supplies the
same pinned `jsonschema`/Pydantic/Pillow/FFmpeg environment used by the local
video integration:

```powershell
$tools = Join-Path (Split-Path -Parent (Resolve-Path .)) 'PoP\Tools'
$ivcPython = Join-Path $tools 'Master-Video-Creator\venv\Scripts\python.exe'
& $ivcPython docs\video_factory\factory.py build
& $ivcPython -m pytest docs\video_factory\tests -q
```

The build reads retained machine evidence, hashes every selected source,
extracts the accepted chart rows, writes three CM briefs plus POP renderer
briefs, validates strict schemas and semantic guards, and refuses to replace an
artifact marked approved/production/published.

## Deep-series v2 editorial layer

`deep_series/episode_content_bible.json` is the authoritative proposed
51-episode curriculum. Its generated Markdown twin is the review surface. The
bible fixes lesson ownership, exclusions, prerequisites, stable examples,
claims, chapter partitions, teaching beats, episode-specific visual spines,
duration-scaled visual contracts, dialogue anchors, misconceptions, and
caveats. The catalog and learning paths are generated from the bible and
validation rejects drift between them.

`deep_series/content_readiness_audit.json` records the audited partition,
chapter coverage, claim/source coverage, and duration-scaled visual budgets. A
`pass` means ready for script/storyboard authoring, not render-ready: complete
scripts, shot-level storyboards, assets/previews, and human content approval
remain separate gates.

`RUNPOD_DEEP_SERIES_MASTER_PROMPT_V2.md` is the audited one-shot authoring and
production prompt. It preserves v1 as history, adds the current CRSE C9-C23,
D10, and E1-E2 lessons, includes the initial learned baseline through the
task-matched and source-packed C22 result, and requires a hash-bound content-review approval before any
separate RunPod execution proposal. Neither the proposed bible nor approval of
its content authorizes a paid or remote action.

Renderer planning and IVC integration are separate deterministic steps:

```powershell
$pop = Join-Path $tools 'POP-Video-Creator'
$env:PYTHONPATH = $pop

foreach ($id in 'cm-foundation','explicit-cm-vs-cm-ir','cm-ir-vs-cse-flat') {
  $brief = "docs\video_factory\renderer_briefs\$id.renderer_brief.json"
  $spec = "docs\video_factory\proofs\$id\resolved.spec.json"
  & $ivcPython -m pop_video plan-brief $brief --out $spec
}

Remove-Item Env:PYTHONPATH
& $ivcPython docs\video_factory\factory.py integrate
```

The exact proof render, observation, and preview commands are written beside
each proof. `LEVEL1_REPORT.md` records the final local evidence, test outcomes,
proof hashes, proposed first wave, and the content-addressed RunPod package.
`runpod/preflight.json` is the machine-readable remote proposal; its presence
does not authorize a quote lookup, upload, pod creation, or any paid action.

## Long-form flagship

`episodes/cm-flagship-representation-to-evidence-v1` is the rendered seven-
chapter, seven-minute local master. Five additive schemas bind the episode,
chapters, narration cues, captions, and release. Chapters render and cache
independently, so a later failure resumes from the first unfinished chapter.

```powershell
$tools = Join-Path (Split-Path -Parent (Resolve-Path .)) 'PoP\Tools'
$ivcPython = Join-Path $tools 'Master-Video-Creator\venv\Scripts\python.exe'
$env:PYTHONPATH = Join-Path $tools 'POP-Video-Creator'

& $ivcPython docs\video_factory\longform.py build-contracts
& $ivcPython docs\video_factory\longform.py render --workers 2
```

The narration provider is offline Windows SAPI (`Microsoft Mark`); the helper
does not use a network or paid voice service. Generated media remains local in
the ignored episode `output/` directory. `release_manifest.json` retains every
input and output hash, and `LEVEL2_REPORT.md` records the render and QA result.
