# Bra-ket and narration implementation audit — foundational CM v2

Date: 2026-09-01  
Status: local preparation passed; full narrated RunPod render awaits exact authorization

## Paper-grounded notation

- The four single-entry 2×2 CM basis matrices are displayed as
  `|1⟩⟨1|`, `|1⟩⟨0|`, `|0⟩⟨1|`, and `|0⟩⟨0|`.
- The script calls these ket-bra objects **basis dyads** and shows the paper's
  notation `|i⟩ ⊗ ⟨j| = |i⟩⟨j|` only while deriving the basis.
- The full operator table is a 4×4 reconstruction of the paper's Figure 1.
  Each tile contains a name, exact 2×2 matrix, and XOR sum of basis dyads.
- A base logical matrix is visibly constructed as
  `|X⟩ ⊗ ⟨Y| = |X⟩⟨Y| = M_XY`.
- The 4×4 LM construction displays
  `(|W⟩⟨X|) ⊗ (|Y⟩⟨Z|)` and the equivalent compound ket-bra view.
- The paper's measurement ordering is retained: rows `(Y,W)`, columns `(X,Z)`.
  The video says **four components per side** and **four variables across both
  sides**, avoiding the inaccurate claim that all four variables occur in both
  the row and column state vector.

## Visual QA

- Replaced the prior eight-across matrix gallery with a legible 4×4 table.
- Added teaching actions for the basis outer products, base-LM outer product,
  tensor construction, compound state vectors, and one worked 4×4 cell.
- Embedded DejaVu glyph audit passes for `⟨ ⟩ ⊗ ⊕ ᵀ` and the earlier Boolean
  symbols. Repeated symbol frames are byte-deterministic.
- All three 960×540 settled-frame contact sheets rendered and were visually
  inspected. No clipping, missing glyph, or overlapping table content was
  observed. Master rendering remains 1920×1080.

## Narration implementation

- Added an offline Kokoro ONNX pipeline; no cloud or paid voice service is
  used.
- Generated three identical 20–22 second auditions: `af_heart`, `af_bella`,
  and `bf_emma`. `af_heart` is the proposal's provisional voice.
- Retrieval pauses are now machine-readable four-second silent segments.
- Episode synthesis enforces cue-window fit and a maximum 1.12× voice speed.
- Output contract: normalized 48 kHz mono narration, AAC in the master,
  sidecar WebVTT, embedded English captions, copied H.264 visual stream, and a
  full decode check after mux.
- Final human voice and listening review remain release gates.

## Verification

- Foundational production validation: 15/15 checks passed.
- Focused bra-ket/narration tests: 3/3 passed.
- Total revised scope: 21 scenes, 21,120 frames, 704 seconds.
- RunPod proposal: `cm-video-foundational-three-production-remote-v3`.
- Proposal identity:
  `e15b8b08b7ad0921803176ff48b8024c7105e9b42e17182d409cc0c0c6d2bde1`.
- Estimated compute: $0.54; hard ceiling: $1.25; one pod create; publication,
  commit, and push excluded.
