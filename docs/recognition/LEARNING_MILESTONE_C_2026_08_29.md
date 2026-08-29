# CRSE learning: Milestone C, 2026-08-29

## Result

Implemented and measured the first CM-supervised graph-learning slice. Four
matched classifiers now compare matrix MLP, matrix CNN, source-DAG GNN, and
fused graph+matrix inputs. A separate GNN is trained for contrastive functional
retrieval. All ten trained artifacts were saved as inert, bounded, hashed float32
JSON tensors, reloaded, and checked for identical outputs.

The retained run is
[neural-20260829-001](runs/neural-20260829-001/report.md); its manifest SHA-256 is
`7dcabbfa873839011ff9658b7a3bfc7e04eeec4f030882fa88a189b7706f473b`.
The compact [machine summary](learning_milestone_c_results.json) and
[independent verification](verification/neural-20260829-001.json) retain the
tracked evidence. Raw rows and trained models remain in the ignored local run.

This is a mixed result. Graph and fused models learned the generated mechanism
better than the matrix MLP under the matched training contract, so the
predeclared representation signal passed. Contrastive retrieval missed its
predeclared test threshold. All models transferred poorly to the real EPFL
negative-only slice. No model is promoted.

## Approved environment and finite run

The approved pins were downloaded from PyPI and the official PyTorch CPU index,
verified before installation, and installed offline into `.venv-crse-neural`.
The existing project `.venv` was unchanged. The
[dependency manifest](pytorch_cpu_2_10_0_manifest.json) records all eleven wheel
filenames, metadata, bundled license paths, byte sizes, and SHA-256 hashes.

- PyTorch `2.10.0+cpu`; CUDA unavailable; two CPU threads.
- 130.59 MiB of wheels; 0.722 GiB combined environment and wheelhouse, below the
  approved 250 MiB and 1.5 GiB caps.
- One manually invoked retained experiment, 35.39 seconds, below the 120-second
  cooperative limit. No JIT, native compilation, model download, upload, paid
  call, background service, or system install occurred.
- Two shared training seeds, 30 classification epochs, 20 retrieval epochs,
  batch size 32, Adam at 0.003. Every model is between 72,337 and 83,841
  parameters, inside the approved 50,000–250,000 comparison band.

## Data and representation contract

Training used the existing 208 exact-labeled generated functions: 128 train, 32
validation, 32 held-out test, and 16 sealed confirmation cases. Exact CM
semantics label affine functions versus one-bit near-matches. Held-out splits
change source template and live support. The comparison shares training IDs,
minibatch order, optimizer, epochs, batch size, threshold, and seeds.

The graph schema keeps one node per serialized v2 DAG node, explicit root,
operator type, variable identity, negation nodes, child-to-parent edges, left,
right and unary edge roles, and repeated references to shared nodes. The GNN does
not receive a full CM at classification inference. Matrix and fused timing charge
CM construction from the expression; graph timing charges DAG encoding.

The real-source check uses 16 eligible eight-variable cones from 15 EPFL
arithmetic/control circuits. They are evaluation-only and come from the frozen
local corpus at upstream commit
`0060e156826e733d69bf5b3322d1bdd0d03a1f9a`, MIT license, corpus SHA-256
`bb98f14a5525a2d869a7ad80e25e879fd176e78ad6d01c51385edc947f2806ac`.
All 16 selected functions are non-affine, so the EPFL number below is specificity,
not a balanced two-class domain estimate.

## Classification evidence

Balanced accuracy for generated test/confirmation and specificity for EPFL:

| Representation | Parameters | Test seeds | Confirmation seeds | EPFL specificity seeds |
| --- | ---: | ---: | ---: | ---: |
| Matrix MLP | 73,985 | 0.500 / 0.469 | 0.500 / 0.500 | 0.250 / 0.562 |
| Matrix CNN | 83,841 | 0.500 / 0.500 | 0.500 / 0.500 | 0.000 / 0.000 |
| Graph GNN | 79,233 | **1.000 / 1.000** | 0.625 / 0.625 | 0.250 / 0.500 |
| Fused | 72,337 | **1.000 / 1.000** | **1.000 / 1.000** | 0.000 / 0.250 |

The CNN collapsed to positive predictions on these held-out cells. The fused
model separated every generated held-out case but predicted most or all EPFL
negatives as affine. The graph-only model was perfect on the test template but
recalled only two of eight positives in each confirmation seed. These conflicts
are useful evidence that success on the generator is not natural-source
generalization.

A positive classification only proposes invoking affine extraction. Independent
complete truth-vector equivalence and strict node reduction decide acceptance.
Across repeated cells there were 630 accepted proposals, 552 semantic rejections,
and 1,122 abstentions. Rejection and fallback costs are included in total time.
There were zero final semantic mismatches. Disabling learned advice invoked no
model and returned all 224 exact original results with zero mismatches.

## Contrastive retrieval

The retrieval GNN learns from paired graphs related by an absorption transform,
with every positive pair proved functionally equal before training. One-bit
near-matches remain hard negatives. A retrieved function is accepted only after
an independent complete truth-vector equality check; otherwise exact fallback
retains the query function.

| Split | Seed 173 top-1 exact | Seed 271 top-1 exact |
| --- | ---: | ---: |
| Test | 0.469 | 0.469 |
| Confirmation | 0.875 | 0.812 |
| EPFL | 0.438 | 0.750 |

The predeclared retrieval criterion required at least 0.80 on both test and
confirmation for both seeds, so it failed. Exact verification accepted 111 of
192 top candidates and used fallback for 81; no incorrect retrieved function
became an output.

## Verification and remaining work

The independent verifier checked every artifact hash, loaded all ten models,
recomputed 224 exact functions, checked 2,304 classification rows and 192
retrieval rows, and confirmed zero result or bypass mismatches. Optional neural
unit tests cover graph semantics, all forward paths, actual updates, contrastive
updates, safe serialization/tamper rejection, exact augmentation, and frozen
EPFL admission.

- Existing NumPy-only focused suite: **65 tests passed** in the project Python
  3.13 environment; importing the default research package still needs no torch.
- Optional PyTorch suite: **6 tests passed** in `.venv-crse-neural`.
- Selected existing regression suites: **225 tests and 146 subtests passed** in
  the available Python 3.10 pytest environment.
- `pip check`: no broken requirements. The independent neural verifier also
  passed again after tightening model-provenance validation.

Milestone C is measured as a bounded plumbing/mechanism slice, not completed as
a broad research claim. Recursive/shared-block and hierarchical/transformer
models, richer CM/cofactor targets, independent natural positive examples,
unseen ambient sizes/padding evaluation, calibration, second-source and
second-machine replication remain pending. All neural cases in this run declare
an eight-variable universe even when live support is smaller. The
experiment register still preserves all 18 tracks and all eight application
families. Milestones D/E remain pending.
