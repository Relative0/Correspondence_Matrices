# External Runs Results

Run date: **2026-08-26**  
Local repository revision: `0f833bc389778f7f915deb7acd4499d207e0ec21`

## Executive result

Both explicitly approved follow-ups completed.

1. The retained one-memo preparation change reproduced on all three Runpod
   CPU flavors. BX1+B2 candidate/baseline ratios were `0.972147--0.978781`;
   EPFL ratios were `0.969411--0.976902`. Every per-pod exactness, archive,
   source-snapshot, row-count, and termination gate passed.
2. The genuinely held-out Berkeley ABC i10 selector study accepted 144 exact
   cones across every `k=8..16` stratum. The existing `k=16` rule transferred
   well, at about `1.012x` oracle regret with zero catastrophic routes. The
   preregistered BX1-trained feature selector failed transfer, at `1.121x` raw
   and `1.136x` CM regret with 7 and 11 catastrophic routes. It is rejected;
   no production selector changed.

## Runpod one-memo confirmation

The campaign uploaded the frozen 12-file archive plus worker, used
`python:3.13.5-slim`, two vCPUs, sequential `cpu3c`, `cpu3m`, and `cpu5c`
pods, and deleted each pod in `finally`.

| Pod / flavor | BX1+B2, 272 rows | Cluster interval | EPFL, 129 rows | Circuit-cluster interval | Cost |
|---|---:|---:|---:|---:|---:|
| pod1 / cpu3c | 0.973374 | [0.970685, 0.977404] | 0.974072 | [0.970962, 0.977040] | $0.000699 |
| pod2 / cpu3m | 0.972147 | [0.968410, 0.976329] | 0.969411 | [0.964334, 0.973442] | $0.001249 |
| pod3 / cpu5c | 0.978781 | [0.976288, 0.981908] | 0.976902 | [0.972727, 0.980961] | $0.000867 |

Each interval is computed within its own machine. Hosts are not pooled. All
three pods had 272 unique BX1+B2 rows, 129 unique EPFL roots, zero canonical or
packed mismatches, eight source manifests covering 72 frozen source files, and
successful archive SHA-256 verification. Total actual cost was `$0.002815`.
All campaign termination flags were true; the postflight inventory found zero
pods.

Verdict: this is strong cross-host confirmation of the already-retained local
preparation optimization. It does not change CM/CSE-flat kernel claims.

Primary machine-readable evidence:

- `deliverables_n22_24/memo_runpod_2026_08_26/memo_runpod_audit_2026_08_26.json`
- `deliverables_n22_24/memo_runpod_2026_08_26/postflight_runpod_inventory.json`
- each pod's `memo_bx1_b2_raw.csv`, seven EPFL chunk CSVs, source snapshots,
  and `memo_epfl_combined_summary.json`

## Berkeley ABC i10 held-out selector

Source was frozen before parsing or outcome inspection:

- upstream: `https://github.com/berkeley-abc/abc`
- commit: `c6e8823c0b9f0c7c469a7538dc2a75b39da17cc4`
- `i10.aig` SHA-256:
  `b551b0932703d7d3c5e3b3cd0fc742b484d0f5d8332b1bf3dd7567679d1559d7`
- notice SHA-256:
  `819151b8f059a48f806c75732ef62b1f873b49b6a04fb128aed28bf87d3dcd6c`

The binary AIGER contained 257 inputs, 224 outputs, no latches, and 2,675 AND
nodes. The preregistered screen selected 144 unique cones: exactly 16 at every
semantic support from 8 through 16. The immutable corpus SHA-256 is
`dbefb5dd790eb394a74a99f9dd710fdd344c5a2d90a7379d12038dde9e5da16b`.

The feature models were frozen before held-out timing and trained only on the
80 BX1 tuning rows. Their frozen model SHA-256 is
`d577d5d795f0297e9931d2cd4116df6dc24495ae4e3ce093d5c65ec0112f1bdc`.

| Arm / policy | Eligible | Regret geomean | Conditional row-bootstrap interval | Max regret | Catastrophic routes | Word routes |
|---|---:|---:|---:|---:|---:|---:|
| raw / current k16 | 140 | 1.012285 | [1.005847, 1.020103] | 1.289918 | 0 | 15 |
| raw / feature ridge | 140 | 1.121191 | [1.063731, 1.189841] | 5.024960 | 7 | 8 |
| CM / current k16 | 144 | 1.012460 | [1.005133, 1.021391] | 1.405483 | 0 | 16 |
| CM / feature ridge | 144 | 1.136482 | [1.078097, 1.205356] | 3.816209 | 11 | 30 |

All 144 CM outputs were exact. Four raw rows were ineligible under the frozen
source protocol; they are retained rather than silently dropped. The feature
decision arithmetic itself cost a median 7.56 us for raw and 9.15 us for CM in
this Python prototype.

The failure mechanism is visible rather than inferred only from an aggregate:
the model routed words on low-support i10 cases where words cost multiples
(including seven CM catastrophes at k=8), while it also missed many k=16 word
wins. This is out-of-corpus model extrapolation, exactly the failure the
held-out gate was designed to catch. Retuning it on i10 would destroy the
held-out status and was not done.

Verdict: reject the feature selector, retain the current `k=16` policy, and do
not integrate a production selector. The current rule now has useful transfer
evidence on i10, but this one circuit is not a universal crossover theorem.

Primary machine-readable evidence is under
`deliverables_n22_24/heldout_abc_i10_2026_08_26/`, including the
preregistration, source manifest, frozen corpus, screen, frozen model, raw
paired rows, decisions, summary, audit, environment, and immutable source
snapshot.

## Exact commands

```powershell
& .\.venv\Scripts\python.exe `
  deliverables_n22_24\cm_memo_runpod_campaign_2026_08_26.py

& .\.venv\Scripts\python.exe `
  deliverables_n22_24\cm_memo_runpod_campaign_2026_08_26.py --inventory

& .\.venv\Scripts\python.exe scripts\cm_heldout_abc_i10_selector.py `
  --stage extract
& .\.venv\Scripts\python.exe scripts\cm_heldout_abc_i10_selector.py `
  --stage freeze-model
& .\.venv\Scripts\python.exe scripts\cm_heldout_abc_i10_selector.py `
  --stage measure --prep-repetitions 5 --kernel-rounds 9 `
  --max-kernel-temporary-bytes 16777216
& .\.venv\Scripts\python.exe scripts\cm_heldout_abc_i10_selector.py `
  --stage analyze
```

No dependency was installed. No cloud resource remains active.

