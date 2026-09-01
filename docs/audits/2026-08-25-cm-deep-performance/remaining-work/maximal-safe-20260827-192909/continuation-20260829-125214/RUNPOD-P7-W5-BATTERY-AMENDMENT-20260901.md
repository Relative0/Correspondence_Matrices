# P7 W5 battery-launch amendment

Date: 2026-09-01
Status: authorized by Brian's instruction to bypass the plugged-in requirement
because the host has a high battery charge

This amendment carries forward the exact frozen W5 campaign in
`RUNPOD-P7-W5-DEVELOPMENT-PROPOSAL-20260901.md`: the same four sequential
shards, exact 96-file bundle, remote programs, cases, typed `sqrt` exclusion,
7,524 primary cells, 328 diagnostic cells, resources, storage, deadlines,
budgets, evidence gates, cleanup ownership, and W8 separation.

Only the local host-power gate changes:

- AC power is not required for a shard launch.
- Windows must report a known battery charge of at least 50%, unless AC power
  has been restored.
- The power gate is checked again before every shard and by its independent
  watchdog process.
- The temporary idle-sleep guard remains active, without changing persistent
  power settings and without overriding lid-close, explicit sleep, battery
  depletion, power loss, or network loss.
- The measured power state and this override are retained in the run evidence.

Each controller still creates at most one pod and cleans only its identity-bound
resource. Failed runs require a fresh run identity under the existing standing
rerun authorization. The 20-minute hard horizon and 18-minute cleanup point are
unchanged.
