# P14 historical runtime identity: evidence needed

The numerical part is reproducible from archived data: [the independent replay](P14_BOOTSTRAP_REPLAY.json) reconstructs all 17 reported interval sets from the 51,102 timing rows. The [recovered candidate runtime](P14_RUNTIME_RECOVERY.json) contains 2,035 hash-checked files and passes the historical import smoke. The original P14 freeze bound six top-level scripts and two holdouts, **not** the full module/dependency tree imported by the timing workers. Thus numerical replay and candidate compatibility do not prove which compiler bytes ran on 18 September 2026.

To close this specific gap, locate a **contemporaneous** record from the original worker execution: a full source/import-closure manifest with per-file hashes, an immutable container/environment digest that contains that closure, or a run log that binds a revision plus a clean-tree status and dependency hashes to the raw worker output. Match that record to the preserved P14 freeze, worker timestamps/IDs and the 51,102-row archive. Hash every named module/dependency in the recovered candidate and compare it to the contemporaneous record. Record any missing, modified or unbound member rather than assuming equivalence from successful imports. Also preserve Python/package versions, environment and the exact analysis script amendment used for the archived intervals.

Read-only checks already available in this package are:

```powershell
cd 'CM Computation\03_STUDY_DESIGN_20260926'
python verify_p14_runtime.py
python replay_p14_intervals.py
cd '..\02_CONTRACT_REVISION_20260926\reproducibility'
python check_historical.py
```

If no contemporaneous import-closure or equivalent binding record exists, report historical *execution identity* as unresolved. A fresh timing run on the candidate would be a new replication under its own environment, not proof of the original worker bytes; it is unnecessary to verify the archived point estimates and intervals. The attempted original-analyzer replay timed out after 600 seconds, while the independent numerical replay completed. Do not replace the archived negative primary outcome with a new run or a favorable subset.
