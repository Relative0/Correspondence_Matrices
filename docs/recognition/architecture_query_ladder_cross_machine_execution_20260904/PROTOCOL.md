# Architecture query-ladder cross-machine/compiler replication protocol

This package repeats the verified 27,648-cell Lane-B query ladder without changing its
54 cases, eight arms, four query counts, 16 counterbalanced blocks, output contract,
source freeze, or oracle data. It is a non-neural portability check, not a new search,
selector fit, or architecture modification.

The prior decision-bearing run used RunPod flavor `cpu3c`, an AMD EPYC 9655 host, and
GCC 12. The replication requests `cpu5c` and installs Debian Bookworm's exact
`clang-14=1:14.0.6-12` package. Before dependency setup or timing, the remote worker must
confirm a new Pod identity and a CPU model different from the prior EPYC 9655 model. The
control plane must also return a nonempty RunPod machine-placement identifier. Failure of
any placement or compiler check closes the single attempt without running the workload;
no replacement is permitted.

APT network access is limited to setup inside the disposable Pod. The Clang package
version, resolved compiler path, compiler executable SHA-256, and version output are
recorded before the frozen source is compiled. The existing four Python dependencies
retain their hash-locked wheel contract. The workload itself has no network access.

Every cell retains the corrected isolated-child timing, RSS, cleanup, exact-artifact,
and independent-verification contracts. All favorable and unfavorable cells must be
retained. A completed replication permits a paired cross-host analysis only after local
evidence verification; it does not itself authorize a website change, publication,
selector fitting, neural training, routing changes, a commit, or a push.

A later exact approval is limited to one Secure CPU Pod, one create and no replacement,
2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, no persistent/network volume, RunPod
flavor `cpu5c`, a $0.10/hour rate ceiling, a $0.02 total ceiling, cleanup within 600
seconds, and inventory reconciliation within 720 seconds. Earlier authorizations may
not be reused.
