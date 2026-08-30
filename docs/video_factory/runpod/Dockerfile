# syntax=docker/dockerfile:1.7
FROM python:3.10.15-slim-bookworm@sha256:97ff6fda70178dee6c144d41030fb88b6ec86d75e1c517fe96b8f62094ea7ac2

ARG BUNDLE_SHA256
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    CM_VIDEO_BUNDLE_ROOT=/opt/cm-video/bundle \
    IVC_DATA=/workspace/cache \
    POP_VIDEO_FFMPEG=/usr/bin/ffmpeg

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates ffmpeg fontconfig fonts-dejavu-core fonts-liberation \
       nodejs npm tini unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/cm-video
COPY requirements.lock /opt/cm-video/requirements.lock
RUN python -m pip install --no-cache-dir --requirement requirements.lock

# package_bundle.py writes this stable copy and a content-addressed sibling.
COPY dist/bundle.zip /tmp/bundle.zip
RUN test -n "$BUNDLE_SHA256" \
    && echo "$BUNDLE_SHA256  /tmp/bundle.zip" | sha256sum --check - \
    && mkdir -p "$CM_VIDEO_BUNDLE_ROOT" \
    && unzip -q /tmp/bundle.zip -d "$CM_VIDEO_BUNDLE_ROOT" \
    && rm /tmp/bundle.zip \
    && npm ci --prefix "$CM_VIDEO_BUNDLE_ROOT/pop" \
    && cd "$CM_VIDEO_BUNDLE_ROOT/pop" \
    && npx playwright install --with-deps chromium

WORKDIR /workspace
ENTRYPOINT ["/usr/bin/tini", "--", "python", "/opt/cm-video/bundle/runpod/worker.py"]
CMD ["--help"]
