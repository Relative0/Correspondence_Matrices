#!/usr/bin/env bash
# Local Ubuntu/WSL build. Downloads dependencies; does not install system packages.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build/downloads build/deps results
if [[ ! -x build/venv/bin/python ]]; then
    python3 -m venv build/venv
fi
build/venv/bin/pip install Cython==3.0.12 setuptools==80.9.0 wheel==0.48.0 \
    pytest==9.1.1 astutils==0.0.6 ply==3.10 networkx==3.4.2
build/venv/bin/pip download --no-deps --no-binary=:all: --no-build-isolation \
    dd==0.6.0 -d build/downloads
if [[ ! -d build/dd-0.6.0 ]]; then
    tar -xzf build/downloads/dd-0.6.0.tar.gz -C build
fi
(
    cd build/downloads
    # Match libc debug symbols to the running loader. Availability depends on
    # the configured Ubuntu package repository still retaining that release.
    apt-get download libpython3.12-dev valgrind "libc6-dbg=$(dpkg-query -W -f='${Version}' libc6)"
)
python3 build_native.py unpack-debs
python3 fetch_cudd.py
python3 build_native.py cudd
build/venv/bin/python build_native.py extension
build/venv/bin/pip freeze > results/python-dependencies.txt
