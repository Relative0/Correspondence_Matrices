# C41 ablation results and external-producer disposition

Status: complete local Windows run; 2026-09-16.

## Integrity and validity

- Declared freeze hash: `8d31d08ae4b8c9cc095d88b20fe3e5a53d4896362df95310ba8b66453df72f59`
- Freeze-file SHA-256: `ce1dc6b72e0a8cf854ddd2e950ca1ac391045183984b1cdaa3c661fb3fecff8c`
- Frozen schedule: 500 distinct rows = 20 cases × 5 methods × 5 rounds
- Retained measurements: 500 rows with the same 500 schedule hashes
- Pre-timing validity: 160 rows = 32 public/control inputs × 5 methods
- Invalid rows: 0
- Every method selected the byte-identical C16-reference artifact document and
  that artifact reconstructed the frozen truth vector on every public case and
  control.

The C41 source closure still verified after the run. C39 and C40 evidence was
read only; C41 copied C40's packed vectors into its own freeze.

## Frozen aggregate result

The statistic was fixed before measurement: median `analysis_ns` for each
case/method across five rounds, summed over 20 cases.

| Method | Sum of case medians | Ablation / C16 | C16 / ablation | Scoped reading |
| --- | ---: | ---: | ---: | --- |
| `c16_reference` | 589,799,300 ns | 1.0000× | 1.0000× | Production C16, budget one |
| `no_shared_layout` | 1,022,052,400 ns | 1.7329× | 0.5771× | Repeating layout was 73.29% slower |
| `eager_all_descriptors` | 2,093,239,700 ns | 3.5491× | 0.2818× | Eager strict admission/reconstruction was 254.91% slower |
| `linear_min_no_dedup_sort` | 549,940,200 ns | 0.9324× | 1.0725× | Linear minimum was 6.76% lower time |
| `unchecked_partition_admission` | 574,756,600 ns | 0.9745× | 1.0262× | Omitting in-lane strict checks was 2.55% lower time |

These results support two positive implementation conclusions on this frozen
host/workload: shared layout and deferred strict admission/reconstruction of
nonleading descriptors account for material costs. They do not support adding
bulk sorting/deduplication as a speed optimization at budget one; the tested
linear-minimum alternative was faster while preserving the selected artifact.
Strict admission/reconstruction had a smaller observed cost, but remains a
correctness boundary, not expendable production overhead.

The lanes are individually scoped implementation substitutions, but the ratios
are not additive causal shares of the historical C15-to-C16 speedup. The run is
warm-process Windows Python timing, reuses the 20 C40 vectors, and does not
establish cross-platform or broad-corpus effects. The unchecked lane omits
strict `from_dict` admission for the leading partition descriptor and skips the
outer in-lane reconstruction pass; post-timing validation supplies the retained
evidence check, not a production-safe replacement.

## External result

The scoped primary-source and implementation search is recorded in
`EXTERNAL_PRODUCER_SEARCH.md`. No public producer was identified that
independently emits the complete `crse-exact-cm-gf2-artifact/v1` document. C41
therefore makes no external speed or quality claim and does not use C16 to fill
foreign payload gaps. A future shared-objective experiment is eligible only
after the complete objective, validation, corpus, lifecycle, and statistic are
frozen before measurement.

## Commands

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_gf2_c41_ablation_benchmark.py `
  tests/test_external_gf2_artifact_adapter.py tests/test_gf2_decomposition.py -q

.\.venv\Scripts\python.exe -m cmbench.recognition.gf2_c41_ablation_benchmark freeze `
  --c40-freeze docs/recognition/c40_gf2_development_blind_freeze_20260916/FREEZE.json `
  --created-utc 2026-09-16T11:37:55Z `
  --output docs/recognition/c41_gf2_ablation_freeze_20260916/FREEZE.json

.\.venv\Scripts\python.exe -m cmbench.recognition.gf2_c41_ablation_benchmark run `
  --freeze docs/recognition/c41_gf2_ablation_freeze_20260916/FREEZE.json `
  --output docs/recognition/runs/c41_gf2_ablation_windows_20260916_001
```

## Remaining submission gaps

- Report serialized artifact sizes and factor-size distributions explicitly.
- Repeat C41 on a second operating system before making portable ablation claims.
- Resolve redistribution/licensing for the C40-derived public slice.
- Obtain a genuinely task-aligned independent producer, or prospectively freeze
  and run a defensible shared-objective comparison.
- Add an independently implemented small-domain oracle if claiming independent
  algorithmic verification.
