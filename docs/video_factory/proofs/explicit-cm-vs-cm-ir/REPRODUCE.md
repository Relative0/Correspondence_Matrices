# Reproduce explicit-cm-vs-cm-ir

From `CM_Computation`, with IVC's Python and the two sibling tools in their documented locations:

```powershell
$tools = Join-Path (Split-Path -Parent (Resolve-Path .)) 'PoP\Tools'
$ivc = Join-Path $tools 'Master-Video-Creator'
$pop = Join-Path $tools 'POP-Video-Creator'
$env:IVC_VIDEO_SPEC_ROOTS = (Resolve-Path 'docs\video_factory').Path
$env:IVC_DATA = (Resolve-Path 'docs\video_factory\tmp').Path + '\ivc-data'
$env:POP_VIDEO_CREATOR_DIR = $pop
$env:POP_VIDEO_CREATOR_PYTHON = "$ivc\venv\Scripts\python.exe"
& "$ivc\venv\Scripts\ivc.exe" render `
  'docs\video_factory\proofs\explicit-cm-vs-cm-ir\assembly.spec.json' `
  --out 'docs\video_factory\proofs\explicit-cm-vs-cm-ir\ivc-output' --json
```

The assembly request is hash-bound to `resolved.spec.json`; a changed spec, theme, or content-pack contract fails validation.
