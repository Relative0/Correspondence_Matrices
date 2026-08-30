# CM video render worker — local package only

This directory defines a disposable, CPU-first Linux render worker. Nothing in
it authenticates to RunPod. `package_bundle.py` creates a deterministic
allowlisted ZIP and audits exclusions; `worker.py` renders one immutable job;
`batch_runner.py` bounds concurrency and resumes only verified results;
`controller.py` is a provider-neutral fail-closed lifecycle model exercised
only with local fakes in this level.

The container is intentionally not built here because the local Docker daemon
is unavailable. The unexecuted build is exact once `dist/bundle_record.json`
exists:

```powershell
$record = Get-Content .\dist\bundle_record.json -Raw | ConvertFrom-Json
docker build --build-arg "BUNDLE_SHA256=$($record.bundle_sha256)" `
  --tag "cm-video-worker:$($record.bundle_sha256.Substring(0,16))" .
```

No `.env`, credential, cache, output video, historical run, or arbitrary CM
research corpus is allowlisted. The container has no exposed port and needs no
persistent volume; upload/download transport is controller-owned and remains
unimplemented until exact remote authorization.
