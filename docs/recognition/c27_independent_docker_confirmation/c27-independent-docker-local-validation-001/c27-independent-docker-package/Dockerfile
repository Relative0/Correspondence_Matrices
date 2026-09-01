FROM python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129
RUN printf '%s\n' 'numpy==2.3.2 --hash=sha256:938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f' > /tmp/requirements.txt \
 && python -m pip install --disable-pip-version-check --no-cache-dir --require-hashes -r /tmp/requirements.txt \
 && rm /tmp/requirements.txt
