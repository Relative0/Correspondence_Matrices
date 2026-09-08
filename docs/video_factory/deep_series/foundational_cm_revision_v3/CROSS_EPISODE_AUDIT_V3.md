# Foundational CM v3 — cross-episode audit

Date: 2026-09-01  
Status: PASS for editorial review; production not authorized

## Scope

Audited:

- two new foundational episode scripts and visual contracts;
- `what-is-explicit-cm` script/spec revision v3;
- source, claim, glossary, content-Bible, and series-order deltas;
- local prerequisite scripts for episodes 2–4;
- neighboring ownership for `what-cm-does-not-claim` and
  `explicit-cm-vs-cm-ir`;
- the originating paper's Figure 1, Section 4.1, and Sections 5.1–5.2;
- repository `eval_cm_boolean` and `materialize_cm` semantics.

## Unique-information test

| Episode | Sole teaching responsibility | Permitted recap | Explicitly moved elsewhere |
|---|---|---|---|
| Why there are sixteen 2×2 operator CMs | Four two-input states, sixteen functions, one whole 2×2 operator matrix, paper ordering | Expression versus function in one sentence | LM, repository layout, IR, packed output, benchmarks |
| From logical matrices to higher-dimensional CMs | Expression-valued LM, positive valuation, paper 4×4 construction, square higher rule | One operator CM anchor | Arbitrary rectangles, repository API, IR, benchmarks |
| Repository explicit row-column CM layout | Ordered R/C lists, coordinates, 4×4/2×8/8×2 materialization, coordinate context | Ten-second paper/operator distinction | Solver/performance, detailed IR/packed comparison |
| What CM does not claim | Compactness, solver/output-contract, scoped speed boundaries | Fixed dense-layout icon | Rebuilding matrices or teaching indexing |
| Explicit dense CM versus CM-IR | Artifact and measurement-boundary comparison | Fixed dense-layout icon | Operator gallery and LM valuation |

No fourth foundational video is recommended. Addressing is part of the
repository-layout lesson, and bra-ket notation remains secondary notation in
the LM lesson.

## Automated audit result

Command:

```powershell
C:\Users\brian\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe `
  docs\video_factory\deep_series\foundational_cm_revision_v3\audit_foundational_cm_revision_v3.py
```

Result: **46/46 checks passed**.

### Script metrics

| Script | Spoken words | Planned runtime | Voiceover/visual pairs |
|---|---:|---:|---:|
| Operator CMs | 577 | 4:15–4:35 | 7 |
| LM to higher CMs | 682 | 5:00–5:20 | 8 |
| Repository layout | 644 | 4:40–5:05 | 9 |

The revised runtimes follow the material rather than the old 8–12 minute tier.

### Repetition checks

- Exact repeated spoken sentences of eight or more words across the three
  scripts: **0**.
- Shared spoken sequences of twelve or more consecutive words: **0**.
- Prohibited mechanical narration phrases: **0**.
- Passive generic three-box teaching directions: **0**.
- Each episode has a different persistent visual object and causal action.

Short conceptual handoffs remain, but no lesson reconstructs a neighboring
lesson's worked mechanism.

## Mathematical audit

### Operator lesson

Verified in the paper's state order `11, 10, 01, 00`:

```text
AND          1000
OR           1110
XOR          0110
equivalence  1001
implication  1011
```

Enumerating four independent Boolean output positions yields exactly sixteen
complete patterns.

### Paper LM lesson

Verified against the downloaded primary PDF and rendered pages:

- Figure 1 contains sixteen distinct 2×2 CMs.
- Section 4.1 states that a CM is the positive valuation of an LM.
- The worked expression is `(W XOR X) implies (not Y AND Z)`.
- The paper's valued 4×4 rows are exactly:

```text
1100
1110
0011
1011
```

- The paper measurement order is left `(Y,W)` and right `(X,Z)`.
- Formal Section 5.2 supplies the square `2^n × 2^n` construction.

### Repository layout lesson

Independently recomputed for
`F=(A AND B) XOR (C OR D)` in `ABCD` MSB-first order:

```text
truth vector: 0111011101111000
matrix rows:  0111 / 0111 / 0111 / 1000
```

Verified coordinates and outputs:

```text
1011 in AB/CD   → (2,3) → 1
1011 in A/BCD   → (1,3) → 1
1011 in ABC/D   → (5,1) → 1
1110 in AB/CD   → (3,2) → 0
1101 in AB/CD   → (3,1) → 0
```

The invalid legacy sequence `0001111011100001` is absent.

## Visual sufficiency audit

### Operator lesson

Persistent object: four state-pair cards. The learner sees ordering, population,
binary choice, gallery formation, operand swap, and retrieval. The sixteen
matrices never become anonymous boxes.

### LM lesson

Persistent object: one expression-valued cell carried through positive
valuation. Tensor/projection and modifier actions construct the larger object;
the 4×4 result does not appear as an unexplained reshape.

### Repository lesson

Persistent objects: an invariant assignment-output rail and a changing layout
rail. Re-partitioning changes only the explicitly named layout fields while the
tracked card remains intact.

## Prerequisite audit resolution

The attached research report could not inspect local episodes 2–4. Local review
confirmed:

- episodes 2 and 3 already teach assignment/function and expression/function
  distinctions;
- none of episodes 2–4 teaches the sixteen paper operator CMs, LM/CM valuation,
  or the paper's 4×4 construction;
- all three currently repeat later CM layout, indexing, packed-output, or dense
  boundary language.

`PREREQUISITE_CLEANUP_DELTA_V3.md` removes that premature material without
creating more videos or altering each episode's owned concept.

## Registry and approval audit

- The approved 51-episode Bible and shared registries were not mutated.
- The proposed candidate contains two new stable examples, two new episodes,
  one rewritten episode, six claim changes/additions, six glossary terms, and a
  53-episode series insertion.
- Applying the delta requires schema/count updates from 51 to 53 and a new Bible
  hash and review manifest.
- Previous content approvals cannot authorize this revision.
- No rendering, narration synthesis, RunPod call, publication, commit, or push
  occurred.

## Verdict

The three-video partition is accurate, succinct, visually differentiated, and
ready for human content review. The next safe step is to create the immutable
review manifest for these exact artifacts. Applying the deltas to the shared
factory should occur only after that content review is accepted.

