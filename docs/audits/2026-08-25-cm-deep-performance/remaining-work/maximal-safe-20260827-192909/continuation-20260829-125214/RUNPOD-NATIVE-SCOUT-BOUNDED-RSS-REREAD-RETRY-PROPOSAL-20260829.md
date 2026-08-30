# RunPod native-scout bounded RSS-reread retry

Date: 2026-08-29  
Status: authorized by the user's aggregate `$10` testing instruction

## Saved V9 result

V9 passed transport, all 63 frozen focused tests, all 144 P5 cells, dependency
identity, Linux controls, and native CaDiCaL. The short-lived native CUDD
worker then crossed a procfs transition where `status` lacked `VmRSS` while an
immediate `stat` reread still appeared live. The supervisor failed closed with
`process_tree_measurement_incomplete`. d4 was not reached. Pod
`jwyi342sjmjkcj` was deleted and both inventories were empty. Estimated V9
compute cost was `$0.0016668784`.

## Exact V10 change

The Linux supervisor performs at most two additional `stat`/`status` rereads,
one millisecond apart, when an owned live entry temporarily lacks `VmRSS`.
Disappearance, group change or a terminal state is classified as a procfs
race. A still-live entry without RSS after the bounded rereads remains a hard
measurement failure. One focused recovery test is added, making 64 focused
testcase elements.

Only `cmbench/comparative/linux_supervisor.py` and
`tests/test_cm_comparative_linux_supervisor.py` differ from V6. The exact
37-file V7 manifest is 5,506,504 bytes. The V8 read-only upload-status 404 retry
is retained. All resource, dependency, P5, deadline, cleanup and zero-volume
constraints are unchanged. The phase cap is `$0.10`; the aggregate campaign
ceiling is `$10.00`. This controller performs exactly one create request.
