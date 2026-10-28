#!/usr/bin/env bash
# Squash-merges the current branch's pull request with its AI usage (issue #9). Run it with `make merge`.
#
# Only the GitHub calls run here, on the host, so no token ever enters a container. Everything else
# (checks, usage, message) is decided by tools/merge_message.py in the dev container.
# Variables (set by make): ENGINE, IMAGE, CLAUDE_LOGS, PR, DRY_RUN, ALLOW_SKIPPED_REVIEW.
set -euo pipefail

die() { echo "make merge: $*" >&2; exit 1; }

case "${DRY_RUN:-}" in ''|1) ;; *) die "DRY_RUN must be 1 or empty, not '$DRY_RUN'" ;; esac

command -v gh >/dev/null || die "needs the GitHub CLI (gh) on the host; maintainers only, see CONTRIBUTING.md"
branch=$(git symbolic-ref --short HEAD)
[ "$branch" != main ] || die "run it on the PR's branch, not main"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# The PR is looked up from the branch, never assumed (lessons L1).
gh pr view --json number,title,body,headRefOid > "$tmp/pr.json" || die "no pull request found for $branch"
number=$(gh pr view --json number --jq .number)
sha=$(gh pr view --json headRefOid --jq .headRefOid)
[ -z "${PR:-}" ] || [ "$PR" = "$number" ] || die "PR=$PR, but $branch belongs to PR #$number"
[ "$(git rev-parse HEAD)" = "$sha" ] || die "local $branch isn't the PR's head commit ($sha); push or pull first"

# gh exits non-zero while checks fail or are pending; merge_message.py decides, and [] means "none found".
gh pr checks "$number" --required --json name,bucket > "$tmp/checks.json" 2>/dev/null || true
[ -s "$tmp/checks.json" ] || echo '[]' > "$tmp/checks.json"
runs=$(gh api "repos/{owner}/{repo}/commits/$sha/check-runs" --jq .check_runs)
statuses=$(gh api "repos/{owner}/{repo}/commits/$sha/statuses")
printf '{"check_runs": %s, "statuses": %s}\n' "$runs" "$statuses" > "$tmp/head.json"

# The usage window starts when the branch was created here, else at its first commit.
start=$(git reflog show --date=iso-strict --format='%gd %gs' "$branch" \
  | sed -n 's/^.*@{\(.*\)} branch: Created from.*/\1/p' | tail -1)
[ -n "$start" ] || start=$(git log --reverse --format=%aI "origin/main..$sha" | head -1)
now=$(date -u +%Y-%m-%dT%H:%M:%S+00:00)
signoff="Signed-off-by: $(git config user.name) <$(git config user.email)>"

logs=${CLAUDE_LOGS:-}
[ -d "$logs" ] || { logs="$tmp/no-logs"; mkdir "$logs"; }
args=(--pr /in/pr.json --checks /in/checks.json --head /in/head.json --logs /logs
      --start "$start" --now "$now" --signoff "$signoff" --format nul
      --allow-skipped-review "${ALLOW_SKIPPED_REVIEW:-}")  # merge_message.py accepts only 1 or empty

# label=disable: read the logs without relabeling the maintainer's own directory on SELinux hosts.
"$ENGINE" run --rm --security-opt label=disable \
  -v "$PWD":/work:ro -v "$tmp":/in:ro -v "$logs":/logs:ro \
  "$IMAGE" python tools/merge_message.py "${args[@]}" > "$tmp/out"
{ IFS= read -r -d '' subject; IFS= read -r -d '' message; IFS= read -r -d '' comment; } < "$tmp/out"
printf '%s' "$message" > "$tmp/message"
printf '%s' "$comment" > "$tmp/comment"

if [ "${DRY_RUN:-}" = 1 ]; then
  printf 'Dry run; nothing merged.\n\n--- subject\n%s\n\n--- message\n%s\n\n--- comment\n%s\n' \
    "$subject" "$message" "$comment"
  exit 0
fi

# --admin: the solo-maintainer override (CONTRIBUTING); it never overrides a failing check.
gh pr merge "$number" --squash --admin --subject "$subject" --body-file "$tmp/message" --match-head-commit "$sha"
if ! gh pr comment "$number" --body-file "$tmp/comment"; then
  printf 'make merge: merged, but posting the usage comment failed. Post this on PR #%s:\n\n%s\n' \
    "$number" "$comment" >&2
  exit 1
fi
git switch main && git pull --ff-only
