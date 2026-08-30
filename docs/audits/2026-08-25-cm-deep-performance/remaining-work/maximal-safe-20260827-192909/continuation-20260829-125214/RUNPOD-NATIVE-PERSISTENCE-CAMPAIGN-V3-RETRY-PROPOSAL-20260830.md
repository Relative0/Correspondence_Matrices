# RunPod native persistence campaign V3 retry proposal

This retry preserves the V1 workload, exact 136-file/5,494,221-byte upload manifest, native identities, resource and cost limits, exactness gates, and cleanup controls. No additional project file is uploaded.

V2 pod `odcer7ilz59smo` reached the d4 build and established that the reviewed minimal build closure omitted upstream `patoh/patoh.h` and the container lacked Boost development headers. It preserved partial evidence, left all uploaded source files unchanged, deleted the pod with HTTP 204, and reconciled both inventories as empty. Estimated compute cost was $0.0009319689631462096.

V3 adds two setup dependencies only:

- Debian package `libboost-dev`, with its resolved package version recorded alongside the existing build packages.
- The public upstream `patoh/patoh.h` fetched directly from `raw.githubusercontent.com/crillab/d4` at exact commit `333370cc1e843dd0749c1efe88516e72b5239174`, requiring exactly 12,250 bytes and SHA-256 `60e00eabe484f67f6efefa6747e4d4e218322e5a454ab3b6eac70a041afbd3bc`, with redirects refused by final-URL equality.

The public dependency is downloaded into the ephemeral pod; it is not an additional export from the user's repository. This separately frozen controller may create exactly one replacement under the user's approved external upload, automatic-retry instruction, and aggregate $10 cap. All acceptance and mandatory-cleanup requirements remain unchanged.

