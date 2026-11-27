# Dev container: every tool for this repository runs here, through `make`.
# The base image is pinned by digest so every build starts from the same bytes.
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

# gitleaks scans for secrets (issue #8). A pinned release, checked against the SHA-256 published
# with it, so every build installs the same bytes.
ARG GITLEAKS_VERSION=8.30.1
RUN set -eu; \
    case "$(dpkg --print-architecture)" in \
      amd64) arch=x64;   sum=551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb ;; \
      arm64) arch=arm64; sum=e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080 ;; \
      *) echo "no pinned gitleaks for $(dpkg --print-architecture)" >&2; exit 1 ;; \
    esac; \
    file="gitleaks_${GITLEAKS_VERSION}_linux_${arch}.tar.gz"; \
    python -c 'import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], sys.argv[2])' \
      "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/${file}" "/tmp/${file}"; \
    echo "${sum}  /tmp/${file}" | sha256sum -c -; \
    tar -xzf "/tmp/${file}" -C /usr/local/bin gitleaks; \
    rm "/tmp/${file}"

# Run as an unprivileged user; the source tree is mounted read-only at /work.
RUN useradd --create-home --uid 1000 dev
USER dev
WORKDIR /work
