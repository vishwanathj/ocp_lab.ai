#!/bin/sh
# Scans a git repository for secrets with gitleaks and the project's rules (issue #8).
# Runs in the dev container, through `make secrets` (CI) and `make secrets-staged` (the pre-commit hook).
#
#   scan_secrets.sh --staged REPO   what is staged for the next commit
#   scan_secrets.sh REPO            every commit in the history
#
# Exits 0 when gitleaks finished and found nothing, and 1 when it finished and found something,
# printing each finding with the secret redacted: CI logs are public. In every other case it says "scan
# cannot run" and exits 2, because gitleaks itself would often report no leaks and exit 0: git can't
# read the repository or the index; gitleaks logs an error or a fatal error; it exits with any other
# status; or its log doesn't end with its closing line (issue #42).
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
# repository someone else owns unless it is marked safe. core.fsmonitor only speeds up reading the work
# tree, and a hook set on the host can't run here: git would complain, and the scan stop (issue #42).
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*' \
    GIT_CONFIG_KEY_1=core.fsmonitor GIT_CONFIG_VALUE_1=false

git -C "$repo" rev-parse --git-dir >/dev/null 2>&1 ||
    cannot_run "git can't read a repository at $repo (in the container, only the checkout is mounted)"
# The pre-commit hook names the index to scan (git commit -a and git commit <file> use a temporary
# one). git takes a missing index as "everything deleted", so a scan of it would find nothing.
if [ -n "$staged" ] && [ -n "${GIT_INDEX_FILE:-}" ]; then
    case $GIT_INDEX_FILE in /*) index=$GIT_INDEX_FILE ;; *) index=$repo/$GIT_INDEX_FILE ;; esac
    [ -r "$index" ] || cannot_run "can't read the index $GIT_INDEX_FILE"
fi

# The full scan also reads merge commits' own changes, which a plain `git log -p` leaves out, and
# (--text) the contents of files git treats as binary, which gitleaks would otherwise skip.
history="--log-opts=--all --full-history --diff-merges=first-parent --text"
[ -z "$staged" ] || history=

# gitleaks reads the changes from git itself. If git complains, gitleaks logs an ERR line, stops
# reading and still exits 0 (or 1, if it found something first), so its log decides: any ERR line means
# part of the changes went unread. Its log goes to stderr, the findings to stdout.
# --platform none: gitleaks would otherwise read the remote's URL to link findings, and log an ERR for
# one it can't parse (an ssh alias, say), though the scan itself is complete. So findings have no
# `Link:` line; their commit, file and line are still printed.
log=$(mktemp) || cannot_run "can't create a temporary file for gitleaks' log"
trap 'rm -f "$log"' EXIT
status=0
# shellcheck disable=SC2086 # $staged is two flags, or none
gitleaks git $staged ${history:+"$history"} --config "$config" --redact --verbose --no-banner \
    --no-color --platform none "$repo" 2>"$log" || status=$?
cat "$log" >&2
# --no-color applies once gitleaks has read its settings; strip colors from anything logged before.
esc=$(printf '\033')
plain=$(sed "s/$esc\[[0-9;]*m//g" "$log")
if printf '%s\n' "$plain" | grep -qE '^[^ ]* (ERR|FTL) '; then
    cannot_run "gitleaks reported an error (see above), so part of the changes may have gone unread"
fi
case $status in
    0|1) ;;
    *) cannot_run "gitleaks stopped with exit status $status (see above)" ;;
esac
# Proof that gitleaks finished: its closing line, always the last in its log. Without it, exit 0 proves
# nothing; with /tmp full, for example, the log can't be written, so no error could be seen either.
# "no leaks found in partial scan" is what gitleaks says when it stopped early, so it doesn't count.
printf '%s\n' "$plain" | tail -n 1 | grep -qE '^[^ ]* (INF no leaks found|WRN leaks found: [0-9]+)$' ||
    cannot_run "gitleaks didn't report that it finished the scan (see above); is /tmp full?"
exit "$status"
