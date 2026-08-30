# CM video factory — Level 2 local flagship report

Date: 2026-08-30
Status: **seven-minute local flagship rendered; automated and visual QA passed; editorial listening approval pending**

## Delivered long-form infrastructure

- Strict episode, chapter, narration, caption, and release schemas were added
  without changing the Level 1 proof contracts.
- Every chapter binds its renderer brief, source IDs, claim IDs, narration cue
  set, duration, dependencies, and cache identity.
- The episode binds seven ordered chapter contracts, 42 sentence-level audio
  cues, 42 WebVTT cues, a 16:9 technical format contract, and a content hash.
- Each chapter plans, renders, narrates, muxes, verifies, and caches
  independently. The final concat is allowed only after every chapter has a
  passing result with verified output hashes.
- Offline narration uses Windows SAPI `Microsoft Mark` at rate `+1`; no voice
  credential, network call, or paid provider is involved.

## Flagship master

- Episode: `cm-flagship-representation-to-evidence-v1`
- Title: *Correspondence Matrices: From Representation to Honest Evidence*
- Chapters: **7**
- Duration: **420.021 seconds**
- Script: **800 words** in 42 cues; **298.350 seconds** of nonzero synthesized
  speech, with planned rests and visual reading time.
- Video: **1920×1080, 30 fps, H.264/yuv420p**
- Audio: **AAC, 48 kHz, stereo**
- Captions: **42-cue WebVTT sidecar** plus concise on-frame scene summaries
- MP4 size: **19,565,742 bytes**
- MP4 SHA-256:
  `5765ddc9987360cd03956a83470606a07be67e536da127818623f20862452546`
- Release identity:
  `cd453fe5a308d31e63fcc58b5c3c503aa90f8070a5f53c482641e4cbff9d32bf`

The checked-in `release_manifest.json` binds all chapter contracts, resolved
specs, chapter media, narration WAVs, final MP4, audio master, and caption
hashes. Generated media itself remains local under the ignored `output/`
directory.

## QA and recovery record

- Factory/schema/semantic suite: **10 passed**.
- RunPod packaging/controller/watchdog regression suite: **9 passed**.
- Focused IVC portability/integration suite: **46 passed**.
- Focused POP CM/theme suite: **34 passed, 2 deselected**.
- Automated release QA passed duration range, chapter count, video stream,
  audio stream, caption identity/count, and output-hash gates.
- All 42 narration cue WAVs are nonzero and fit their planned windows; cue
  duration range is **5.215–9.079 seconds**.
- Exact-time contact-sheet review and full-resolution opening/ratio samples
  passed legibility, fit, status labeling, evidence boundary, settling,
  clipping, and overlap checks.
- A four-worker Chromium run timed out on one chapter-5 screenshot. Chapters
  1–4 remained valid cache hits; the run resumed with two workers and chapters
  5–7 completed without another timeout. No completed chapter was rerendered.
- A concurrent legitimate edit changed the retained recognition experiment
  register. The source-hash guard stopped the retry before rendering; the
  factory registry was refreshed to the new stable hash without modifying or
  reverting that source.

## Boundary and next approval

No RunPod resource, network service, paid TTS provider, upload, deployment, or
publication was used. The next meaningful action is an editorial listening
review of the complete local master. Voice replacement or script trims can be
performed chapter-by-chapter without discarding the visual renders.

The scoped version-control checkpoint is prepared, but repository history is
not changed until the user gives the literal commit instruction required by
the repository safety gate. Nothing has been pushed.
