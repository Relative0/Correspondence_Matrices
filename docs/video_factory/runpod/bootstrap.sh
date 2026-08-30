#!/bin/sh
set -eu

if [ "$#" -ne 3 ]; then
  echo "usage: bootstrap.sh BUNDLE_ZIP BUNDLE_SHA256 INSTALL_ROOT" >&2
  exit 2
fi

BUNDLE_ZIP=$1
BUNDLE_SHA256=$2
INSTALL_ROOT=$3

printf '%s  %s\n' "$BUNDLE_SHA256" "$BUNDLE_ZIP" | sha256sum --check -
apt-get update
apt-get install -y --no-install-recommends \
  ffmpeg fontconfig fonts-dejavu-core fonts-liberation nodejs npm unzip
rm -rf /var/lib/apt/lists/*
mkdir -p "$INSTALL_ROOT"
unzip -q "$BUNDLE_ZIP" -d "$INSTALL_ROOT"
python -m pip install --no-cache-dir --requirement "$INSTALL_ROOT/runpod/requirements.lock"
npm ci --prefix "$INSTALL_ROOT/pop"
cd "$INSTALL_ROOT/pop"
npx playwright install --with-deps chromium
python "$INSTALL_ROOT/runpod/worker.py" --help >/dev/null
