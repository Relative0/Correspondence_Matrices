# Pod issue diagnosis — 2026-08-28 Asia/Bangkok

## What is established

This is not established to be only exhausted capacity. Small CPU stock fluctuated, but the previous creation request returned a generic HTTP 500 even after the exact CPU catalog reported stock. Its underlying cause remains unknown. One earlier HTTP 400 was conclusively caused by the explicit `globalNetworking: false` field being invalid for CPU pods; that field was removed.

The account has enough existing credit for both the original configuration and an eight-vCPU configuration at the revised rate ceiling. No payment method or account spending limit was changed. The pod-billing query returned zero records and zero reported pod charges as of 16:45:31 UTC; the API rounded the requested interval to the current UTC day. This is a billing snapshot, not a finalized invoice. The account separately reported $0.008/hour of current spending, which was not attributed to this campaign or changed.

At 16:37–16:39 UTC, selected two- and four-vCPU offers reported NONE. At 16:39:58 UTC, eight-vCPU CPU3C reported HIGH at $0.24/hour and 16 GB RAM; eight-vCPU CPU3G reported HIGH at $0.32/hour. By 17:02 UTC, CPU3C with eight vCPUs reported NONE again. Availability is neither stable nor reserved.

Brian's higher-spend authorization is recorded in `CPU8-AUTHORIZATION-AMENDMENT.md`. A separate eight-vCPU CPU3C controller is prepared with a $0.25/hour ceiling, retaining $0.10 total, 20 minutes, 10 GB ephemeral disk, the same image, the exact 65-file bundle, and the same smoke. It has not launched or sent a creation request.

## Host-sleep finding

Windows Kernel-Power event 506 recorded entry into connected standby at 23:45:27 Bangkok time with reason `Lid`. Event 507 recorded exiting standby around 23:59, including reason `Lid` at 23:59:42. These timestamps correspond to the pause in the local reconciliation process.

The old watchdog was due at 16:46:29 UTC but activated at 16:59:37 UTC, 787.6 seconds late. It retained a connection error during recovery and then confirmed that its owned pod was absent and account pod count was zero. The separate inventory monitor failed with a connection-reset error; its incomplete run must not be reported as successful. Fresh independent v1/v2 inventories after the original 20-minute horizon were empty.

This demonstrates that the old local watchdog did not enforce its deadline through laptop sleep. No pod was observed during this failed attempt, but the same condition during a successful creation could violate the lifetime and spending caps.

## Corrections prepared and checked

The eight-vCPU controller now requires AC power and requests temporary `ES_CONTINUOUS | ES_SYSTEM_REQUIRED` protection separately in the controller and detached watchdog. Each process clears its request in `finally`; no persistent power settings or lid behavior is changed. An actual Windows acquire/release probe passed. This prevents automatic idle sleep; it cannot prevent lid closure, explicit sleep, power loss, or loss of network access.

The controller also omits `startSsh` and `startJupyter` entirely on CPU creation, retaining their disabled defaults, and records bounded request-size/hash diagnostics and safe response headers. Runpod's official CLI CPU creation path omits these startup fields. This is a compatibility correction; it has not yet been tested in a live creation and does not establish the prior HTTP 500's cause.

Host/remote syntax, six CPU8 quote/refusal cases, unchanged remote bootstrap, original source hashes, and the cost-reserve arithmetic passed. The latest controller hash is `a7728ee101a3c04cda50d5a8b52e9b1628dc31d2098def0a0ab348587aa0edb2`; `CPU8-HOST-AWAKE-CHECKS.json` supersedes earlier prepared-controller hashes. All 65 approved source entries remain unchanged. No remote test, study, package install, source build, or nontrivial local computation occurred in this diagnosis turn.

## Next launch condition

Before a billable launch, confirm that Brian can leave the laptop plugged in, awake, connected, and with its lid open until teardown is confirmed. This is an operational safety condition, not another request for the already authorized upload or budget. Refresh the exact eight-vCPU quote and both pod inventories, then run the prepared CPU8 controller only if the existing checks pass. Do not leave a billable pod relying on a sleeping laptop for teardown.

Runpod's documented `--terminate-after` CLI option is wired to the GPU GraphQL creation path in the inspected official source, not its CPU REST creation path. No verified provider-managed CPU expiry was established, and no such field should be invented in a request.

Primary references: [Runpod account query fields](https://docs.runpod.io/runpodctl/reference/runpodctl-user), [Runpod CLI creation implementation](https://github.com/runpod/runpodctl/blob/main/cmd/pod/create.go), [Windows execution-state API and limitations](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate).

Evidence: `ACCOUNT-CAPACITY-DIAGNOSIS-20260827-163734.json`, `LARGER-CPU-CAPACITY-20260827.json`, `CPU8-AND-REQUEST-SCHEMA-20260827.json`, `CPU8-CREDIT-SUFFICIENCY.json`, `POD-BILLING-SMOKE-WINDOW.json`, `RETRY007-AFTER-HORIZON-RECONCILIATION.json`, `v2-execute-007/WATCHDOG-RESULT.json`, and `DIAGNOSIS-FINAL-INVENTORY-20260828.json`.
