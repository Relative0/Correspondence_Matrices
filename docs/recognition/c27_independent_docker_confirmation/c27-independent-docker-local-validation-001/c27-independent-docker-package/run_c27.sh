#!/usr/bin/env bash
set -euo pipefail

scope="${1:-}"
if [[ "$scope" != "same-host" && "$scope" != "independent-machine" ]]; then
  echo "usage: ./run_c27.sh same-host|independent-machine" >&2
  exit 2
fi
case "$(uname -s)" in
  MINGW*|MSYS*) export MSYS_NO_PATHCONV=1; root="$(pwd -W)" ;;
  *) root="$(pwd -P)" ;;
esac
if [[ -e results || -e c27-results.tar.gz ]]; then
  echo "refusing to overwrite existing results" >&2
  exit 3
fi
sha256sum -c frozen.sha256
mkdir results

image='crse-c27-independent:python3.13.15-numpy2.3.2'
docker build --pull=false --tag "$image" .
docker image inspect "$image" --format '{{printf "{\"id\":%q,\"os\":%q,\"architecture\":%q}" .Id .Os .Architecture}}' > results/docker-image.txt
docker version --format 'Client={{.Client.Version}} Server={{.Server.Version}} OS={{.Server.Os}} Arch={{.Server.Arch}}' > results/docker-version.txt
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  "$image" python -B -c 'import json,numpy,platform; print(json.dumps({"python":platform.python_version(),"numpy":numpy.__version__,"system":platform.system(),"machine":platform.machine()}))' \
  > results/runtime.json

common=(docker run --rm --network none --cpus 2 --memory 4g --pids-limit 256
  --read-only --cap-drop ALL --security-opt no-new-privileges
  --env PYTHONDONTWRITEBYTECODE=1 --env OPENBLAS_NUM_THREADS=1
  --env OMP_NUM_THREADS=1 --env MKL_NUM_THREADS=1 --env NUMEXPR_NUM_THREADS=1
  --mount "type=bind,source=$root/frozen,target=/frozen,readonly"
  --mount "type=bind,source=$root/results,target=/output"
  --mount "type=bind,source=$root,target=/package,readonly"
  --tmpfs /work:rw,exec,nosuid,size=268435456
  --tmpfs /tmp:rw,noexec,nosuid,size=67108864)

"${common[@]}" "$image" sh -ec   "cp -a /frozen/. /work/; ln -s /output /work/run-output; cd /work; exec python -B scripts/cm_comparative_c27_support_aware.py --output run-output/c27-support-aware-fresh-linux-20260831-001 --rounds 5 --max-seconds 1200"
"${common[@]}" "$image" sh -ec   "cp -a /frozen/. /work/; ln -s /output /work/run-output; cd /work; exec python -B scripts/crse_gf2_support_aware_verify.py run-output/c27-support-aware-fresh-linux-20260831-001"
"${common[@]}" --env "CRSE_EVIDENCE_SCOPE=$scope" "$image"   python -B /package/verify_c27_outputs.py   /output/c27-support-aware-fresh-linux-20260831-001 /output/PORTABILITY-SUMMARY.json

tar -czf c27-results.tar.gz -C results .
bytes="$(wc -c < c27-results.tar.gz)"
if (( bytes > 16777216 )); then
  echo "result archive exceeds 16 MiB" >&2
  exit 4
fi
printf '{"status":"complete","scope":"%s","archive_bytes":%s}\n' "$scope" "$bytes"
