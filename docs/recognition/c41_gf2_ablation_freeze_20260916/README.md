# C41 exact-decomposition ablation freeze

Status: protocol prepared; freeze and measurement results are recorded by
additive manifests in this directory. Prepared 2026-09-16.

C41 is a successor experiment. It does not alter the C39 or C40 freezes, source
closures, raw runs, or result manifests. It copies the 20 packed C40 truth
vectors into a new self-hashed freeze and generates its own deterministic
five-round schedule. It also freezes 12 newly generated structured/dense
controls, all code that affects the experiment, and the two protocol documents
in this directory.

The reference is production C16 with `materialize_budget=1`. The four ablations
each remove one scoped mechanism:

1. `no_shared_layout` repeats layout independently for the rank, cofactor, and
   Kronecker screens while retaining the other C16 mechanisms.
2. `eager_all_descriptors` retains shared layout and canonical descriptor
   ordering/deduplication but strictly admits and reconstructs every unique
   partition descriptor.
3. `linear_min_no_dedup_sort` retains shared layout and strict budget-one
   admission but uses a deterministic linear minimum over raw descriptors,
   without bulk sorting or digest deduplication.
4. `unchecked_partition_admission` retains shared layout and canonical
   ordering/deduplication but omits strict `from_dict` admission and internal
   reconstruction for the leading partition descriptor.

The fourth lane is intentionally unsafe as a production procedure; it estimates
the cost of the checks. Before timing, and again in the retained evidence, C41
requires each method and case to select a byte-identical artifact document and
requires that selected artifact to reconstruct the frozen truth vector. Any
failure marks that lane invalid and prevents its timings from supporting a
claim.

The aggregate statistic is fixed before measurement: median `analysis_ns` for
each case/method across five rounds, summed over the 20 cases. Ratios divide the
C16-reference sum by the ablation sum; below one means the ablation is slower.
The measurements are warm-process Python timings with packed truth vectors
already loaded. They are implementation- and host-specific and are not additive
causal shares of the historical C15-to-C16 speedup.

Commands:

```powershell
.\.venv\Scripts\python.exe -m cmbench.recognition.gf2_c41_ablation_benchmark freeze `
  --c40-freeze docs/recognition/c40_gf2_development_blind_freeze_20260916/FREEZE.json `
  --created-utc 2026-09-16T12:00:00Z `
  --output docs/recognition/c41_gf2_ablation_freeze_20260916/FREEZE.json

.\.venv\Scripts\python.exe -m cmbench.recognition.gf2_c41_ablation_benchmark run `
  --freeze docs/recognition/c41_gf2_ablation_freeze_20260916/FREEZE.json `
  --output docs/recognition/runs/c41_gf2_ablation_windows_20260916_001
```

The exact creation timestamp in the actual command is recorded in `FREEZE.json`.
