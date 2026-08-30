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
