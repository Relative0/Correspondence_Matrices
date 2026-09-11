# Collecting a genuine consumer session

No natural-use session has been admitted by this continuation. Rebuilding the
saved video contracts for a benchmark would be a controlled replay. The new
recorder is ready for the next independently motivated compiler build.

From the repository, use the same Python environment and POP repository you
normally use for the video compiler. Choose a new local output filename:

```powershell
python -B scripts/capture_cm_consumer.py --output build/consumer-session-001.jsonl --purpose production -- build --pop-root C:/path/to/your/POP-repository
```

The forwarded `build` command performs the compiler's normal local writes. Run
it when the video work itself calls for a build. Use `--purpose controlled_replay`
for tests or research replays. The recorder does not launch a build on its own,
schedule anything, upload the capture, render media, or enable a CM backend.

The wrapper records each actual `truth_layout_payload` call in sequence: request
digest, return digest or exception type, elapsed call time, source-file digest,
start/end boundaries, completion status, and the resulting compiler-manifest
digest. It preserves successful outputs and raised exceptions. It never stores
arguments, returned text, exception messages, or the POP path. Hashes of known,
low-entropy values can still be recognized; keep receipts local until reviewed.

The file is created exclusively and its records form a SHA-256 chain. The
20,000-call limit keeps recording bounded. Further calls continue normally but
mark the session truncated, and verification rejects it as a complete trace.
The adapter covers sequential calls only. Hashing and disk I/O add observer
overhead; its timing fields are not performance-comparison measurements.

Validate a receipt locally:

```powershell
python -B -c "from pathlib import Path; from cmbench.comparative.consumer_capture import verify_capture; print(verify_capture(Path('build/consumer-session-001.jsonl')))"
```

Custody validation deliberately returns `natural_use_admitted: false` even when
the operator chose `production`. Admission additionally needs the owner to
document the real purpose, capture interval, selection rule, source revision,
and resulting video-work artifact that consumed the returned data. Call return
alone does not prove downstream use or a useful plan lifetime. The current
caller returns complete small matrices; its trace must not be relabeled as a
projected-CNF count workload or evidence for a general-purpose router.

# Historical fixture restoration

Two archives retain 115 previously missing scientific files, including original
manifests, raw records, the source scout, and its licensed BLIF inputs. Every
member keeps its retained byte identity, including historical CRLF line endings.
Some retained EPFL best-results files differ from the currently pinned upstream
tree; substituting those upstream files was refused.

```powershell
python -B scripts/restore_cm_historical_fixtures.py --restore
python -B scripts/restore_cm_historical_fixtures.py
```

The second command only checks. Restoration validates all archives, members,
paths, byte counts, and hashes before writing missing files. It refuses an
existing file with different bytes. No network or credentials are required.
An interrupted write is detectable; it is never silently overwritten.

The fixture manifest is `tests/fixtures/cm_historical_restoration.json`. This
restores data identity, not compatibility between old frozen source closures
and today's implementation. Linux also needs a locally built native library
for native activation API tests:

```powershell
python -B scripts/build_cm_fused_slots.py
```

Exact historical Windows-DLL experiments remain a separate platform-bound
contract. Their binary hashes must not be replaced with a newly compiled binary
to make an old scientific freeze pass.
