# Application evidence and the actual video consumer

The September 12 application audit verifies all nine concrete-feature contracts,
independently checks the completed projected counts, tests bounded hidden-variable
simplification, and restores more historical dependencies. See
`docs/audits/2026-09-12-cm-application-evidence/REPORT.md` and its immutable manifest.

## What the video evidence means

The owner identified the active video project and its current-state handoff. The
three completed foundational narrated masters and their retained manifests match
the recorded hashes. Their archived producer differs from today's local source.
It formats supplied bit strings and fixed operator tables into HTML. This is an
actual presentation consumer, but it is not observed demand for a CM counter or
materialization backend. No historical runtime trace was reconstructed.

The old `capture_cm_consumer.py` adapter targets the separate maintained chapter
compiler. The new `capture_foundational_consumer.py` targets the actual
foundational producer's `matrix` and `mini_matrix` functions. It preserves the
original argument objects, including highlighting sets, while hashing a normalized
request. The underlying hash-chain recorder remains unchanged.

Use the adapter only inside the next independently needed and authorized video
render. Package it with that production job on RunPod. Select the exact producer
source and a fresh render directory; do not run a new render merely to manufacture
natural-use evidence. This command renders silent video and does not replace the
existing narration, review or publication steps:

```text
python -B scripts/capture_foundational_consumer.py \
  --producer docs/video_factory/foundational_cm_production.py \
  --producer-sha256 <SHA256-of-the-selected-producer> \
  --receipt /workspace/presentation-session.jsonl \
  --output-root /workspace/new-foundational-render \
  --purpose production
```

The receipt binds the producer source, sequential formatter calls, returned HTML
identities and final render-summary identity. It stores no arguments, HTML or
exception messages. Preserve the full production package and output manifests
locally for independent downstream-use review. Hashing and receipt I/O add
observer overhead; these timings are not performance comparisons. A production
purpose declaration alone never admits natural use. Formatter calls never become
evidence for a counting backend just because their outputs depict matrices.

## Recovering the historical dependency closure

The original fixture restorer still recovers 115 retained files. The new restorer
recovers 156 public LogikBench files directly from the already retained historical
ZIP and its unchanged manifest, plus the exact d4 executable from immutable
upstream. No historical expected hash is rewritten, no binary is executed by the
restorer, and differing existing files are refused before any fixture write.

```text
python -B scripts/restore_cm_historical_fixtures.py --restore
python -B scripts/restore_cm_application_fixtures.py --restore --download-d4
python -B scripts/restore_cm_application_fixtures.py
```

The d4 download is bound to upstream commit
`15eff31962466804a48374826b9e5a746fc2766e` and SHA-256
`29cb30f351ed92b02343e5e7a98b082e949d9838245f37c0bcdecf68a57ffd39`.
It is fetched directly from the upstream project, whose source and license remain
available there. The downloaded executable is not added to this repository.
The broad historical suite still contains source-closure and platform-specific
failures; restoring byte identity does not make every old source version compatible
with today's implementation.
