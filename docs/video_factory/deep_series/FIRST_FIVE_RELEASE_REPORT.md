# CM deep series — first-five production report

Date: 2026-09-01  
Status: **five local production candidates rendered; automated and contact-sheet QA passed; editorial watch/listen approval pending**

## Delivered masters

| Episode | Duration | MP4 SHA-256 |
|---|---:|---|
| Conceptual animation versus measured result | 360.021 s | `a01734fc5773772d9d1453fdbe645a58bae99020fd3a87a88faca725b947c76e` |
| Why Boolean computation is the substrate | 360.021 s | `f584c8ff362cf871f8a7cfb1fb9d294c79064defaf94104f7affc68c6091edb2` |
| Expression, truth table, and Boolean function | 600.021 s | `07f1af1af67146a11f832694a0746e7cfefbe07abe43cd8633220def5ef2c6b7` |
| Live support versus ambient universe | 360.021 s | `13ca2501bd73984522625a4df05e5f5109a4cfa14008401df1e3125f7f2471ed` |
| What an explicit correspondence matrix is | 599.988 s | `ff374112470965a07537a9eafefa759d30a91f5e40072b943fe17aa37979e02e` |

Total duration: **2,280.072 seconds (38:00.072)**.

Every episode has a 1920×1080, 30 fps H.264/yuv420p master; 48 kHz stereo AAC narration; embedded `mov_text` English captions; a WebVTT sidecar; an AAC audio master; a 12-frame decoded contact sheet; and a hash/provenance release manifest.

## Remote production

- Proposal: `cm-video-deep-series-first5-production-remote-v1`
- Proposal identity: `e16034b3aa55996c353ea1a1cc3e3af972bf347c14fc79dbff7309e62c29edf3`
- Run: `runpod-first5-production-v1-20260831-160714`
- Jobs: **17/17 passed**
- Pod creates: **1/1**
- Controller-estimated compute: **$1.266824**
- Provider billing visible at latest postflight: **$1.037668**; the final partial-hour record may lag
- Exact owned pod: **confirmed absent** by controller cleanup and independent postflight inventory
- Credential value recorded: **false**

## Narration and assembly

All 268 spoken cues were synthesized locally with offline Windows SAPI `Microsoft Mark`; no network or paid voice provider was used. Every cue fits its approved timing window. Nine longer cues required a faster native SAPI speaking rate; no words were changed and no recorded waveform was time-compressed. The maximum native rate used was `+6`.

Automated QA passed all final video, audio, caption, duration, decoded-frame, artifact-hash, source-run, authorization, cleanup, and release-identity checks. Visual review of the five contact sheets found no clipping, internal compiler labels, truncated copy, or broken layouts. Some early animation states are intentionally sparse before their diagrams settle.

Focused regression: **18 passed**. Full video-factory regression: **58 passed, 1 unrelated concurrent source-hash failure** (`src-recognition-roadmap`). The six scoped sources governing these episodes remain verified.

## Editorial gate

These files are production candidates, not published releases. A human should watch and listen to all five masters, paying particular attention to the nine faster narration cues and the pacing of sparse transition states. Publication remains unauthorized. No commit or push was performed.
