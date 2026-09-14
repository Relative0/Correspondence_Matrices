FROM python:3.13.15-bookworm@sha256:a53008522631dbcb063c4d5982aa91a00e86e51d90bbcf3513313f1a5c163af8 AS d4-builder

COPY vendor/d4v2-15eff31962466804a48374826b9e5a746fc2766e.tar.gz /tmp/d4.tar.gz
COPY vendor/libpatoh-linux-x86_64-pr8.a /tmp/libpatoh.a
RUN echo "f3263aa02cb4229f81df79cdaa624e508cec7a7fba754f9efa9bcd64ce11478d  /tmp/d4.tar.gz" | sha256sum -c - \
 && echo "f813a4a8e30e3515f4e0a6d5379723d58eb3cc099fbfd116b6d686c81f4c559d  /tmp/libpatoh.a" | sha256sum -c - \
 && apt-get update \
 && apt-get install -y --no-install-recommends build-essential cmake ninja-build libboost-program-options-dev libgmp-dev zlib1g-dev \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /src/d4 \
 && tar -xzf /tmp/d4.tar.gz --strip-components=1 -C /src/d4 \
 && install -m 0644 /tmp/libpatoh.a /src/d4/3rdParty/patoh/libpatoh.a \
 && cd /src/d4/demo/counter \
 && ./build.sh -s

FROM python:3.13.15-bookworm@sha256:a53008522631dbcb063c4d5982aa91a00e86e51d90bbcf3513313f1a5c163af8

COPY vendor/ganak-v2.6.4-linux-amd64.tar.gz /tmp/ganak.tar.gz
COPY vendor/kissat-4.0.4-linux-amd64.zip /tmp/kissat.zip
COPY vendor/cryptominisat5-v5.15.0-linux-amd64.tar.gz /tmp/cryptominisat.tar.gz
COPY vendor/biodivine_aeon-1.4.2-cp37-abi3-manylinux_2_28_x86_64.whl /tmp/biodivine_aeon-1.4.2-cp37-abi3-manylinux_2_28_x86_64.whl
COPY --from=d4-builder /src/d4/demo/counter/build/counter_static /usr/local/bin/d4-counter
RUN echo "2d5f731e7529e55c021b4966068bd3f0c22ed337949a2c7b496c45ec44ae6137  /tmp/ganak.tar.gz" | sha256sum -c - \
 && echo "63282e5168ca040a2018edfba0726bf893a7a6bcdb1db87feb67857e2da697a7  /tmp/kissat.zip" | sha256sum -c - \
 && echo "4c3f5775cf960f6904c6468caabe3a21e82e03a28303b8626b70568ce3a0c56a  /tmp/cryptominisat.tar.gz" | sha256sum -c - \
 && echo "7084f222407d31220569fe9f1c1ed31c5ce6a04d2497e9e28811aa1ea97d70f3  /tmp/biodivine_aeon-1.4.2-cp37-abi3-manylinux_2_28_x86_64.whl" | sha256sum -c - \
 && tar -xzf /tmp/ganak.tar.gz -C /usr/local/bin ganak \
 && python -c "import pathlib,zipfile; p=pathlib.Path('/usr/local/bin/kissat'); p.write_bytes(zipfile.ZipFile('/tmp/kissat.zip').read('kissat-4.0.4-linux-amd64'))" \
 && tar -xzf /tmp/cryptominisat.tar.gz -C /usr/local/bin cryptominisat5 \
 && python -m pip install --no-cache-dir --no-deps /tmp/biodivine_aeon-1.4.2-cp37-abi3-manylinux_2_28_x86_64.whl \
 && chmod 0755 /usr/local/bin/ganak /usr/local/bin/kissat /usr/local/bin/cryptominisat5 /usr/local/bin/d4-counter \
 && rm /tmp/ganak.tar.gz /tmp/kissat.zip /tmp/cryptominisat.tar.gz /tmp/biodivine_aeon-1.4.2-cp37-abi3-manylinux_2_28_x86_64.whl

COPY fixtures /opt/cm-smoke/fixtures
COPY smoke.py /opt/cm-smoke/smoke.py
COPY NATIVE_LOCK.json /opt/cm-smoke/NATIVE_LOCK.json
ENTRYPOINT ["python", "/opt/cm-smoke/smoke.py"]
