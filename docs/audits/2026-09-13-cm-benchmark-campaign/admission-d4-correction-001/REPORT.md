# CM successor admission and d4 correction

Status: implemented locally and reconciled against the frozen campaign evidence.

## Biology admission

Whole-model fixed-point admission now requires every referenced regulator to have a declared update function. Applied to the frozen ledger, the successor rule admits 33 of 300 candidate rows across 22 of 212 unique models and refuses the other 267 rows across 190 models.

The rule predicts that 2 of 12 selected biology cases are admissible. Those cases produce 12 of 72 cells; the remaining 60 refused cells exactly match all 60 frozen undeclared-regulator errors. The original admission ledger and results remain unchanged.

## d4 abort diagnosis

The pinned d4 source defaults its first cache page to 4 GiB and allocates that page eagerly. The screen worker independently imposed a 4 GiB address-space limit. This collision explains the uniform signal-6 aborts on all 24 d4 corpus cells while the pre-worker smoke could pass.

The successor adapter now passes a 256 MiB first page and 64 MiB additional pages explicitly and rejects unsafe cache sizes. This retains a bounded cache without relying on the upstream 4 GiB default.

## Verification boundary

The admission and command contracts are covered by focused local tests, and this audit reconciles the admission rule with the frozen SHA-256 identities and observed errors. A post-fix native Linux execution was not possible on this host: Docker has no available daemon, and the installed WSL environment lacks Python and the C++ build toolchain. No cloud resources were created and no campaign evidence was rewritten.
