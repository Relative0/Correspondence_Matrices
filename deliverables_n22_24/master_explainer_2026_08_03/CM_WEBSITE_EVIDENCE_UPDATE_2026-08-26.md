# CM website evidence update — 2026-08-26

## Outcome

The most recently regenerated tracked CM website is the master explainer under
this directory. Its source and all four generated audience pages now include
the accepted 2026-08-25 symmetric V3 evidence.

The update does not replace the B1/E3 or EPFL result. It corrects the former
universal wording:

- B1/E3 and EPFL remain parity evidence for those workloads;
- current B2/B4 V3 measured formula-balanced bare CM/CSE-flat at `0.890570`
  overall, formula-cluster interval `[0.874065, 0.907272]`;
- current B2/B4 V3 measured `0.961234` at `k=16`, interval
  `[0.928974, 0.994177]`;
- the public CM wrapper is a separate timing boundary and measured `3.094136`
  overall against CSE-flat, interval `[2.883083, 3.310818]`.

The site also no longer says preparation is unprofiled. It records the completed
deep profile, accepted one-memo reduction, its three-host confirmation, and the
exact-but-slower compact canonical-order experiment that was rejected and
reverted.

The post-consolidation follow-up is reported without replacing the accepted V3
headline:

- three fresh same-host V3 repetitions ranged from `0.904905` to `0.908991`
  (run geomean `0.907590`); this confirms the direction while showing run-level
  variation that a within-run formula-cluster interval does not measure;
- bounded direct-kernel cases at `live_k=17..20` completed `16/16` with zero
  mismatches and zero timeouts under the documented memory/time limits;
- the public wrapper refused all `16/16` above-guard cases, so the supported
  guard remains `live_k=16` and no above-guard speed claim is made.
- three Runpod CPU flavors reproduced the one-memo preparation improvement:
  BX1+B2 `0.972147–0.978781`, EPFL `0.969411–0.976902`, zero mismatches,
  total cost `$0.002815`, and zero postflight pods;
- 144 untouched Berkeley ABC i10 cones gave the current k16 policy
  `1.012285` raw and `1.012460` CM regret with zero catastrophes; the frozen
  BX1-trained feature selector failed at `1.121191`/`1.136482` with 7/11
  catastrophes and was rejected without retuning.

## Evidence source

- `../corrections_2026_08_25/symmetric/audited_v3_inference.csv`
- `../corrections_2026_08_25/symmetric/audited_v3_audit.json`
- `../../docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/symmetric_v3_audit.json`
- `../../docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/symmetric_v3_r2_audit.json`
- `../../docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/symmetric_v3_r3_audit.json`
- `../../docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/above_guard_audit.json`
- `../../docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/above_guard_raw.csv`
- `../memo_runpod_2026_08_26/memo_runpod_audit_2026_08_26.json`
- `../memo_runpod_2026_08_26/postflight_runpod_inventory.json`
- `../heldout_abc_i10_2026_08_26/abc_i10_screening.json`
- `../heldout_abc_i10_2026_08_26/abc_i10_selector_audit.json`
- `../../docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/dpr1_smoke_summary.json`
- evidence revision pinned by the builder:
  `1fd3907dbc1986cb2d8a9f0f8cab2b5920a415ce`

The builder selects the exact V3 rows by scope, corpus, live support, and metric,
fails if selection is not unique, and carries field-level provenance into
`cm_master_data_2026_08_03.json`.

## Rebuild

```powershell
& .\.venv\Scripts\python.exe `
  deliverables_n22_24\master_explainer_2026_08_03\cm_master_build_2026_08_03.py
```

Generated outputs:

| File | SHA-256 |
|---|---|
| `cm_master_data_2026_08_03.json` | `574ABD9737669A695FD7F72F702FDED140F4824A7D3DBC50776C514752AFEA73` |
| `index.html` | `7B081BBDC515CE5E0E078C40D83146B0E74B0159D84EC12F9A1579D2BD629A22` |
| `layperson.html` | `0B611C28EE4F773741C8C31CE5FC8EEEFA8826DD6F3B91903A1E680B3EB1D33F` |
| `investor.html` | `69324A4ABA5F5108E5CA87F4E0D7A71E9B0BE15C4888F57091B2674588C04A67` |
| `expert.html` | `A59706A930C6EB3D5F3007BD1F54D98440CBCA7B3704C29868831982FD9E2BD9` |

Two consecutive builds produced identical hashes.

## Validation

- content JSON and generated data JSON parsed successfully;
- builder byte-compilation passed;
- shared JavaScript syntax check passed;
- all four generated HTML files parsed with Python's HTML parser;
- exact V3 values and the current chart row matched the authoritative CSV;
- all four pages contain the updated chart title and injected V3 data;
- focused correctness/integrity suite: `86 passed, 4 subtests passed`;
- final full suite: `368 passed, 4 subtests passed` in 95.82 seconds;
- `git diff --check` passed (line-ending conversion warnings only).

A rendered in-app-browser check was attempted, but local `file:` navigation was
blocked by the browser security policy. No alternate browser workaround was
used. No site was deployed or published.
