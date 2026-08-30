# Flagship pilot — human review

Date: 2026-08-30
Release: `cm-flagship-representation-to-evidence-v1-local-20260830`

## Visual review — passed

The exact-time contact sheet was sampled at twelve settled scene midpoints.
Full-resolution frames were also inspected for the opening separation map and
the corrected-evidence ratio panel.

- 16:9 safe zones, chapter labels, status badges, source footers, and claim
  footers remain inside frame.
- Titles, scene summaries, matrix labels, graph nodes, boundary cards, and
  ratio annotations are legible at 1920×1080.
- Conceptual scenes carry a visible conceptual label; measured scenes retain
  workload, numerator/denominator, uncertainty, and timing-boundary context.
- No clipping, unintended overlap, missing settled panel, or misleading pooled
  comparison was observed.
- The contact-sheet decoder was corrected to decode forward from the prior
  keyframe to the requested timestamp; timestamps now occupy external gutters
  and do not obscure the frame.

## Technical audio/caption review — passed

- All 42 offline SAPI cue files contain nonzero PCM audio and fit their planned
  windows.
- The final stream is AAC, 48 kHz, stereo; the sidecar is valid WebVTT with 42
  cue identities bound to the narration contract.
- The seven chapter audio timelines and the final audio master are hash-bound
  by `release_manifest.json`.

## Editorial listening review — still requested

Automated and structural audio QA cannot judge whether the local synthetic
voice is the desired public-facing performance. Listen through the full master
before approving publication. The voice layer is replaceable without changing
the chapter visuals, evidence contracts, or render cache identities.

No upload, publication, paid provider, or RunPod resource was used.
