# Runpod continuation handoff

The smoke is blocked by provider creation/capacity failures, not by missing authentication. Read RESULTS.md and SUMMARY.json first. Exactly one API creation request was sent; HTTP 500 returned no pod ID. Three current-API retry preflights were read-only and stopped on no CPU capacity. The independent final inventory, more than 22 minutes later, verified zero account pods.

The detached watchdog's deadline lookup failed with a DNS error; its startup ready marker did not prove network access. A subsequent read-only inventory outside the sandbox at 15:12:18 UTC verified zero pods. Before any future launch, require a successful network probe in the actual watchdog context, keep bounded retry/error reporting, and use sandbox escalation when required. Do not claim the old watchdog successfully verified teardown.

The user authorized the exact original smoke, then use of the specific supplied credential file. It is now `../.env.runpod.local`, renamed from `.env.txt` under the existing Git ignore rule. Read only this file for authentication. Do not display its content, copy it into an archive, or upload the account key into a worker.

The 65 approved source hashes are unchanged. The earlier root implementation changes and 70 local tests remain as documented by the parent campaign. No remote test pass or memory measurement was obtained. Website work and unrelated CRSE proposals remain outside this campaign.

`runpod_smoke_controller.py` preserves the first executed controller. `CONTROLLER-V2-PREFLIGHT-SOURCE.py` preserves the initial v2 retry source; `CONTROLLER-V2-EXECUTED-SOURCE.py` preserves the later executed preflight source. The current `runpod_retry_v2_controller.py` adds unique run labels, retained live-offer responses, a required watchdog network probe before readiness, and bounded/reported recovery failures. Four fake-client watchdog checks pass, but the hardened detached execution context is not yet verified live. Its default output folder already exists and will refuse reuse. For an authorized continuation, select a fresh lowercase alphanumeric/hyphen `CM_SMOKE_RUN_LABEL`; the watchdog inherits it.

Before any new creation request, independently recheck zero pods, the exact manifest, image digest, current CPU price and stable capacity. Do not increase any approved cap. Do not turn a transient LOW/NONE catalog response into an excuse to raise resources or launch a matrix. All remote commands, binary-only dependency pins, expected 70 tests, and expected 312 memory rows remain as in the approved package. Preserve failed/refused rows.

The controller invokes the standard-library bootstrap through a container command and sends exactly the allow-listed source bundle as command environment data. It opens no public service. Runpod's authenticated v2 SSE log API returns bounded evidence. The account key stays out of worker inputs. Inspect returned limits before accepting any computation, and terminate only the identified campaign pod in finally, followed by an independent inventory.

A successful smoke would still require review and a separate exact approval for calibration, accepted-corpus replay, and the full suite. No estimator promotion, production-balanced-v1 activation, commit, push, deployment, or publication is authorized.
