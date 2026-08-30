# RunPod native persistence campaign V5 retry proposal

This retry preserves the exact 136-file/5,494,221-byte external upload, public dependency identities, resource and cost limits, workload, exactness gates, and cleanup controls.

V4 pod `vlfvhjewad21xf` compiled d4 successfully in 11.69 seconds, producing a 5,905,384-byte ELF with SHA-256 `ea86d879062828983695762650fbc20cd9b0b8b682757861779ccd3c79ec3aea`. Focused tests then reported 22 passes and two failures. Both failed tests deliberately assert that CUDD ZDD is unavailable in a normal local environment; this premise is false on the native-equipped RunPod and is already covered positively by the native adapter tests and the gated workload. The returned archive was intact, but Windows extraction encountered the case-insensitive name collision between command record `d4-build.json` and compiler identity `D4-BUILD.json`. V4 deleted the pod with HTTP 204 and reconciled both inventories as empty. Estimated compute cost was $0.001210822586218516.

V5 makes two remote-only corrections:

- Deselect exactly the two environment-negative tests while retaining 22 focused tests, including all native structural adapter and Linux supervisor tests. The workload itself still requires native CUDD ZDD and d4 availability and refuses substitution.
- Rename compiler identity evidence to `D4-COMPILER-IDENTITY.json`, eliminating the Windows case-fold collision without changing its content.

No project source/data identity changes. This separately frozen controller may create exactly one replacement under the user's explicit external-upload approval, automatic-retry instruction, and aggregate $10 cap. All semantic and mandatory-cleanup requirements remain unchanged.

