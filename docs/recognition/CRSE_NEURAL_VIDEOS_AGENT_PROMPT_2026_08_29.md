# Agent prompt: create short visual explainers for the CRSE neural benchmark

Copy everything below the line into a new coding task.

---

Create a small suite of accurate, visually clear videos explaining the CRSE
neural-representation benchmark. This is an implementation task: inspect the
retained evidence, build the video subject/specs, render previews, inspect them,
render the final MP4 files, test the work, and retain provenance manifests.

## Workspaces

Research repository, read-only unless the owner separately asks for research
edits:

`C:\Users\brian\Documents\CM_Computation`

Preferred video implementation:

`C:\Users\brian\Documents\PoP\Tools\POP-Video-Creator`

Also inspect `C:\Users\brian\Documents\PoP\Tools` for another existing video or
motion-graphics tool if it is demonstrably a better fit. Prefer extending the
working POP Video Creator rather than creating a new renderer. Follow its local
`CLAUDE.md`, `README.md`, applicable agent briefs, scene-spec validation,
virtual-clock animation invariant, preview workflow, tests, FFmpeg encoder, and
manifest conventions.

Do not read `.env*`, credentials, voice vaults, or token stores. Do not invoke
ElevenLabs, paid APIs, cloned voices, uploads, or network services. Default to
silent videos with complete on-screen captions. A local stock voice may be
prepared only if already available and free, but do not let narration block the
captioned deliverables. Do not commit, push, publish, or overwrite existing
shipped videos unless explicitly asked.

## Authoritative research evidence

Read these before writing the storyboard:

1. `docs/recognition/LEARNING_MILESTONE_C_2026_08_29.md`
2. `docs/recognition/learning_milestone_c_results.json`
3. `docs/recognition/runs/neural-20260829-001/report.md`
4. `docs/recognition/runs/neural-20260829-001/run_spec.json`
5. `docs/recognition/runs/neural-20260829-001/classification_raw.jsonl`
6. `docs/recognition/runs/neural-20260829-001/retrieval_raw.jsonl`
7. The ten saved model JSON artifacts in that retained run
8. `cmbench/recognition/models/torch_models.py`
9. `cmbench/recognition/graph_inputs.py`
10. `cmbench/recognition/teacher.py`

Treat the retained JSON and code as authoritative. Do not invent activations,
loss curves, weights, predictions, timings, or examples. If you visualize an
actual training curve or prediction, derive it from the retained artifacts and
record its source. Conceptual diagrams must be visibly labelled “conceptual”.

## Scientific facts the videos must preserve

- Every Milestone C formula used an eight-variable ambient universe.
- Eight Boolean variables give 256 truth positions and a balanced 16x16 CM.
- Live positive support differed by split: training 1/2/3/5, validation 4,
  test 6, confirmation 7. Near-match negatives used all eight variables.
- Training comprised 128 generated functions, with 32 validation, 32 test,
  16 confirmation, and 16 evaluation-only EPFL functions.
- The task was affine/XOR classification versus a one-bit non-affine near-match.
- Matrix models received an exact CM; graph models received the source DAG; the
  fused model received both. The graph-only model did not receive the full CM at
  classification inference.
- Two seeds were trained. Classification used 30 epochs; retrieval used 20;
  batch size was 32; optimizer Adam; learning rate 0.003; CPU only.
- A neural prediction was only a proposal. Exact complete-vector verification
  accepted or rejected it, and exact fallback preserved the result.
- There were zero final semantic mismatches. This does not make the classifier
  accurate and does not make neural confidence a proof.

Classification results, shown without rounding away the two seeds:

| Model | Generated test | Confirmation | EPFL specificity |
| --- | --- | --- | --- |
| Matrix MLP | 0.500 / 0.469 | 0.500 / 0.500 | 0.250 / 0.563 |
| Matrix CNN | 0.500 / 0.500 | 0.500 / 0.500 | 0.000 / 0.000 |
| Graph GNN | 1.000 / 1.000 | 0.625 / 0.625 | 0.250 / 0.500 |
| Fused | 1.000 / 1.000 | 1.000 / 1.000 | 0.000 / 0.250 |

Retrieval top-1 exact results:

| Split | Seed 173 | Seed 271 |
| --- | --- | --- |
| Test | 0.469 | 0.469 |
| Confirmation | 0.875 | 0.812 |
| EPFL | 0.438 | 0.750 |

The interpretation must be explicit: graph and fused inputs learned the narrow
generated mechanism, the CNN collapsed, retrieval missed its predeclared test
threshold, and every model transferred poorly to the all-negative EPFL slice.
No model was promoted.

## Deliverables

Create five caption-complete videos, approximately 45–75 seconds each, plus an
optional combined reel if it costs little after the individual cuts exist:

1. **From Boolean function to CM and graph**
   - Animate 4 variables into 16 assignments and a 4x4 CM as a legible teaching
     example, then scale the diagram to the actual benchmark: 8 variables,
     256 assignments, 16x16 CM.
   - Show the same expression as a sharing-preserving operator DAG.
   - Distinguish ambient variables from live support.

2. **Matrix MLP and Matrix CNN**
   - Show the 16x16 truth-value channel and validity-mask channel.
   - MLP: flatten -> dense layers -> affine proposal score.
   - CNN: local filters/pooling -> embedding -> score; explain that image-like
     locality was a hypothesis, not a fact about Boolean semantics.
   - End with the actual near-chance/collapse results.

3. **Graph GNN**
   - Show operator/variable node features, child-to-parent edges, left/right/
     unary roles, explicit root, negation, and retained DAG sharing.
   - Animate several conceptual message-passing rounds and root/mean/max pooling.
   - End with perfect generated test accuracy, weaker 0.625 confirmation, and
     poor EPFL specificity. Explain template learning versus transfer.

4. **Fused graph plus CM**
   - Run matrix and graph streams side by side, combine their embeddings, and
     show the proposal/exact-check/fallback boundary.
   - End with 1.000/1.000 generated test and confirmation but 0.000/0.250 EPFL
     specificity. Make the negative transfer visually unmistakable.

5. **Functional retrieval and the overall verdict**
   - Show two syntactically different but exactly equivalent DAGs approaching in
     embedding space, with a one-bit near-match as a hard negative.
   - Show the actual top-1 results and the failed >=0.80 criterion.
   - Finish with the architecture: learned proposal -> exact verifier -> accept
     or fallback, zero final semantic errors, no production promotion.

## Visual direction

Use a restrained technical-explainer style rather than the existing card/glyph
visual language unless that language genuinely improves comprehension. A dark
or light neutral field, high-contrast type, one consistent color per data path,
and large readable labels are preferable to decorative motion.

Keep one persistent visual vocabulary:

- CM/truth values: square grid, two clearly distinguishable binary states
- Validity mask: a second, visually quieter channel
- Graph nodes: operator-specific shapes or colors, variables separately encoded
- Learned proposal: amber
- Exact verification: blue or green
- Rejection/fallback: neutral gray, never red as though it were an error
- Failed generalization: clearly labelled result panel, not melodramatic motion

Animations must be driven only by the POP virtual progress clock. No CSS
transitions, keyframes, `requestAnimationFrame`, or wall-clock reads. Videos
must remain understandable when paused and without audio.

## Required workflow and verification

1. Inspect the video tool and choose whether to add a `crse_neural` subject,
   reusable scientific scene types, or validated hand-authored specs. Document
   the choice.
2. Write a shot list and exact on-screen copy before full rendering.
3. Generate and validate the scene specs. Preserve source paths and SHA-256
   hashes in provenance.
4. Render representative preview frames for every video: early animation,
   mid-transition, settled diagram, and result panel.
5. Open and visually inspect those frames. Iterate on clipping, contrast,
   typography, pacing, matrix legibility, and graph density.
6. Run the existing POP Video Creator tests plus focused new tests for the
   subject/spec/rendering logic.
7. Render and encode the final MP4 files. Do not overwrite unrelated outputs.
8. Extract frames from each encoded MP4 and inspect them; verify duration,
   resolution, FPS, stream presence, and manifest hashes.
9. Write a concise production report listing every output, duration, sources,
   checks, limitations, and any skipped narration.

Do not claim the videos are finished based only on generated HTML or submitted
render commands. Completion requires encoded MP4s, visual inspection, passing
focused tests, and retained manifests.
