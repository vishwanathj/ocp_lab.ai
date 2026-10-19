# Dev container: every tool for this repository runs here, through `make`.
# The base image is pinned by digest so every build starts from the same bytes.
FROM docker.io/library/python:3.12-slim@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install -r /tmp/requirements-dev.txt

# Run as an unprivileged user; the source tree is mounted read-only at /work.
RUN useradd --create-home --uid 1000 dev
USER dev
WORKDIR /work
