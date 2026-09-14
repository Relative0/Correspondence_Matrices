# CM bounded counting, biology, and affine results

Status: retrieved, independently verified, and campaign Pod deleted.

The screen produced 90 successful measurements from 192 planned cells. All 192 cells have terminal records and there were zero paired correctness mismatches. The other 102 frozen `worker_error` records comprise 60 biology admission failures (undeclared regulators), 24 d4 native aborts, and 18 Ganak executions that reached the 60-second deadline.

## Affine solution counts

All 48 cells completed across eight cases and three repetitions per arm. CM packed elimination and the independent sparse-set oracle agreed in every pair. With ratio defined as sparse-set wall time divided by CM-packed wall time, the median ratio was 1.365x and the geometric mean was 1.728x. Thus CM packed elimination was faster on aggregate in this bounded screen. Median arm times across all successful affine cells were 53.604 ms for CM packed and 71.501 ms for sparse-set elimination.

## Biology fixed points

Only two of twelve selected files were closed under their declared targets, yielding 12 valid cells and six matched pairs. The aggregate AEON/CM-scalar median ratio was 0.715x, but the two admissible models point in opposite directions: AEON was much faster on one model while CM scalar was faster on the other. This sample is too small and admission-biased for a general biology performance claim.

## Exact and projected counting

Ganak completed 21 of 24 exact-count cells, covering seven of eight cases; the remaining three executions hit the 60-second bound. d4 aborted with signal 6 on all 24 corpus cells despite passing the pinned Linux smoke fixture, so no paired exact-counter comparison is valid.

The unpaired projected Ganak lane completed nine of 24 cells, covering three of eight cases; the other fifteen reached the 60-second bound. This lane contains no CM arm and supports no CM speedup claim.

## Boundaries

These are screen results, not comprehensive corpus results. The frozen ledger retains the original `worker_error` labels; the categories above are posthoc diagnostics from the captured worker logs. Full per-case counts, timings, memory high-water values, hashes, and error classifications are in `RESULTS.json`.

RunPod's control plane reported the authorized 16 vCPU and 64 GB RAM, while the container runtime reported 64 logical CPUs and no cgroup CPU or memory maximum. The screen ran one fresh worker at a time and Ganak was explicitly limited to one thread, but this discrepancy should remain attached to any hardware-normalized interpretation.
