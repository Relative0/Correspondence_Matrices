# Runpod P7 W3 development-partition continuation V5

The V4 `ir-development-b` controller observed unrelated pod
`cm-c7-linux-eccc3297dfe2` between its successful read-only preflight and its
final zero-inventory gate. It failed closed before a Runpod create request,
uploaded zero files, incurred no charge, and preserved its local evidence.

V5 carries forward the three unexecuted partitions from the validated V4 plan:
`ir-development-b` (17 cases/68 cells), `relation-development-a` (17/85), and
`relation-development-b` (17/85). The uploaded 96-file manifest and bundle,
parent case IDs, on-pod derivation, functional-only contract, focused tests,
offline gate, source-integrity checks, fresh-process isolation, resource shape,
256-KiB chunks, 20-minute lifetime, `$0.10` phase cap, `$0.20` related-campaign
cap, standing `$5` ceiling, owned cleanup, and no-replacement rule are unchanged.

The first V5 preflight requires the unrelated inventory to have cleared. Each
later V5 partition additionally requires every earlier V5 result complete,
verified, deleted, and cost-reconciled. V5 never deletes or otherwise acts on
the unrelated pod.
