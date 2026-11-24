#!/bin/sh
# Scans a git repository for secrets with gitleaks and the project's rules (issue #8).
# Runs in the dev container, through `make secrets` (CI) and `make secrets-staged` (the pre-commit hook).
#
#   scan_secrets.sh --staged REPO   what is staged for the next commit
#   scan_secrets.sh REPO            every commit in the history
#
# Exits 0 when nothing is found. Otherwise exits non-zero and prints each finding, with the secret
# redacted: CI logs are public.
set -eu

staged=
if [ "${1:-}" = "--staged" ]; then staged="--pre-commit --staged"; shift; fi
repo=${1:?usage: scan_secrets.sh [--staged] REPO}
config="$(dirname "$0")/../.gitleaks.toml"

# The checkout is owned by the host user, not this container's user, and git refuses to read a
# repository someone else owns unless it is marked safe.
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'

# shellcheck disable=SC2086 # $staged is two flags, or none
exec gitleaks git $staged --config "$config" --redact --verbose --no-banner "$repo"
