# Dev container: every tool for this repository runs here, through `make`.
# Every image is pinned by tag and digest, so every build starts from the same bytes, and Dependabot
# proposes updates to both (issue #10).

# gitleaks scans for secrets (issue #8). It comes from its official image, so Dependabot can update it.
FROM ghcr.io/gitleaks/gitleaks:v8.30.1@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f AS gitleaks

FROM docker.io/library/python:3.12-slim@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install -r /tmp/requirements-dev.txt

# git: the tools/merge.sh and secret-scan tests build throwaway repositories (issues #9, #8).
# make: the pre-commit hook tests run `make setup` and the hook, which calls make (issue #8).
RUN apt-get update && apt-get install -y --no-install-recommends git make && rm -rf /var/lib/apt/lists/*

# A static binary, so it runs on this base too.
COPY --from=gitleaks /usr/bin/gitleaks /usr/local/bin/gitleaks

# Run as an unprivileged user; the source tree is mounted read-only at /work.
RUN useradd --create-home --uid 1000 dev
USER dev
WORKDIR /work
