# C38 C37-native second-machine replication protocol

Upload only the frozen **44-file, 1,797,840-byte package** described by
`c38_linux_upload_manifest.json`. It contains the exact C37 source map, fresh sealed
18-case/six-workload dataset, independent verifiers, and the minimal transitive runtime
needed to rebuild the C11 native library. It excludes the Windows DLL, credentials,
local timing artifacts, unrelated dirty work, persistent storage, and website files.

On one new Secure CPU Pod, use the pinned amd64 Python 3.13.15 Bookworm image. Resolve
the image's `cc`, record its executable path, full version text, and SHA-256, then build
`fused_slot_executor.c` with exactly `-std=c11 -O3 -Wall -Wextra -Wpedantic -shared -fPIC`. Record the resulting
shared-library hash and ABI. Rebind only the environment-specific freeze and dataset
hash references; independently prove that the cases, expressions, traces, expected
outputs, schedules, gates, and original C37 source map are otherwise byte-equivalent.

Run the unchanged 12-block single-root and 20-block multi-root C37 schedule: 954 raw
sessions, 44,928 single-root exact query checks, and 48,384 multi-root output-query
checks. Run both the packaged C37 verifier and the C38 rebinding/compiler verifier.
A failed performance gate is a valid cross-machine outcome and must be retained; it
does not permit rerunning with changed methods, schedules, flags, cases, or thresholds.

No upload or paid action is authorized by this freeze. A later exact authorization is
limited to one Secure CPU Pod, one creation attempt and no replacement, 2 vCPU, at least
4 GB RAM, 12 GB ephemeral disk, no persistent/network volume, one HTTPS port, a
$0.25/hour rate ceiling, a $0.05 controller cost ceiling, deletion within ten minutes,
and twelve-minute inventory reconciliation. Setup may download only the pinned image
and hash-locked NumPy wheel. Workload execution uses no network. No training, website
write, deployment, shadow promotion, production change, commit, or push is authorized.
