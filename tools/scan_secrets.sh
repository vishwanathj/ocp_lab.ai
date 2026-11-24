#!/bin/sh
# Scans a git repository for secrets with gitleaks and the project's rules (issue #8).
# Runs in the dev container, through `make secrets` (CI) and `make secrets-staged` (the pre-commit hook).
#
#   scan_secrets.sh --staged REPO   what is staged for the next commit
#   scan_secrets.sh REPO            every commit in the history
#
# Exits 0 when nothing is found. Otherwise exits non-zero and prints each finding, with the secret
# redacted: CI logs are public. If git can't read the repository or the index, it says "scan cannot
# run" and exits 2: gitleaks itself would log git's error, report no leaks and exit 0.
set -eu

cannot_run() {
    echo "scan_secrets: scan cannot run: $*" >&2
    exit 2
}

staged=
if [ "${1:-}" = "--staged" ]; then staged="--pre-commit --staged"; shift; fi
repo=${1:?usage: scan_secrets.sh [--staged] REPO}
config="$(dirname "$0")/../.gitleaks.toml"

# The checkout is owned by the host user, not this container's user, and git refuses to read a
# repository someone else owns unless it is marked safe.
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'

git -C "$repo" rev-parse --git-dir >/dev/null 2>&1 ||
    cannot_run "git can't read a repository at $repo (in the container, only the checkout is mounted)"
# The pre-commit hook names the index to scan (git commit -a and git commit <file> use a temporary
# one). git takes a missing index as "everything deleted", so a scan of it would find nothing.
if [ -n "$staged" ] && [ -n "${GIT_INDEX_FILE:-}" ]; then
    case $GIT_INDEX_FILE in /*) index=$GIT_INDEX_FILE ;; *) index=$repo/$GIT_INDEX_FILE ;; esac
    [ -r "$index" ] || cannot_run "can't read the index $GIT_INDEX_FILE"
fi

# shellcheck disable=SC2086 # $staged is two flags, or none
exec gitleaks git $staged --config "$config" --redact --verbose --no-banner "$repo"
