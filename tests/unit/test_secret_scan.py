"""Tests for tools/scan_secrets.sh, the gitleaks scan behind the pre-commit hook and CI (issue #8).

Each test builds a throwaway git repository and scans it with the project's real .gitleaks.toml.
A "blocked" test also checks which rule fired: a crash or a bad config fails the scan too, and the
fake token would be caught by gitleaks' built-in rules even if the project's own rule were missing.

The scanner's contract: exit 0 when nothing is found; otherwise exit non-zero and print one finding
record per secret, with a `RuleID:` line (gitleaks' verbose report) and the secret redacted. If git
can't read the repository or the index, exit non-zero with "scan cannot run": gitleaks itself would
report "no leaks found" and exit 0.
"""

import re
import subprocess
from pathlib import Path

import pytest

from fake_secrets import GIT_ENV, fake_offline_token, fake_pull_secret, git

ROOT = Path(__file__).resolve().parents[2]
SCAN = ROOT / "tools" / "scan_secrets.sh"


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    return tmp_path


def stage(repo, name, text):
    (repo / name).write_text(text)
    git(repo, "add", name)


def commit(repo, name, text):
    stage(repo, name, text)
    git(repo, "commit", "-q", "--no-verify", "-m", f"add {name}")


def scan(repo, *flags, env=None):
    env = {**GIT_ENV, **(env or {})}
    result = subprocess.run([str(SCAN), *flags, str(repo)], env=env, capture_output=True, text=True)
    result.output = result.stdout + result.stderr
    return result


def assert_blocked_by(result, rule):
    assert result.returncode != 0, result.output
    # A finding record, not just the rule's name: an error message could mention the rule too.
    assert re.search(rf"^RuleID:\s+{rule}$", result.output, re.M), f"no {rule} finding:\n{result.output}"


def assert_passes(result):
    assert result.returncode == 0, result.output


# The project's own rules

@pytest.mark.parametrize("line", [
    "offline_token: {token}",
    "export OFFLINE_TOKEN={token}",
    'offline_token = "{token}"',
])
def test_a_staged_offline_token_is_blocked_by_the_project_rule(repo, line):
    stage(repo, "vars.yml", line.format(token=fake_offline_token()) + "\n")
    assert_blocked_by(scan(repo, "--staged"), "offline-token")


def test_a_staged_pull_secret_is_blocked_by_the_project_rule(repo):
    stage(repo, "pull-secret.json", fake_pull_secret() + "\n")
    assert_blocked_by(scan(repo, "--staged"), "pull-secret")


def test_changing_only_the_auth_line_of_a_saved_pull_secret_is_blocked(repo):
    # gitleaks runs a rule only if one of its keywords is in the changed lines. Here the change is
    # just the `auth` line; the `auths` line above it is unchanged.
    commit(repo, "pull-secret.json", fake_pull_secret(indent=2) + "\n")
    old_auth = next(l for l in (repo / "pull-secret.json").read_text().splitlines() if '"auth":' in l)
    new_auth = next(l for l in fake_pull_secret(indent=2).splitlines() if '"auth":' in l)
    (repo / "pull-secret.json").write_text((repo / "pull-secret.json").read_text().replace(old_auth, new_auth))
    git(repo, "add", "pull-secret.json")
    assert_blocked_by(scan(repo, "--staged"), "pull-secret")


# What passes

def test_a_change_with_no_secrets_passes(repo):
    # How the collection is meant to be used: the token comes from the environment, never the file.
    stage(repo, "playbook.yml", "offline_token: \"{{ lookup('env', 'OFFLINE_TOKEN') }}\"\n")
    assert_passes(scan(repo, "--staged"))


def test_a_line_marked_gitleaks_allow_passes(repo):
    stage(repo, "vars.yml", f"offline_token: {fake_offline_token()}  # gitleaks:allow\n")
    assert_passes(scan(repo, "--staged"))


def test_this_repositorys_own_history_passes():
    # The test plan's "CI scan passes on the current history"; it also catches rules that flag our
    # own files (these tests, CONTRIBUTING's Secrets section) and git refusing to read /work.
    assert_passes(scan(ROOT))


# The staged scan reads what will be committed

def test_a_staged_token_is_blocked_even_if_the_file_was_cleaned_afterwards(repo):
    stage(repo, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    (repo / "vars.yml").write_text("offline_token: \"{{ lookup('env', 'OFFLINE_TOKEN') }}\"\n")
    assert_blocked_by(scan(repo, "--staged"), "offline-token")


def test_an_unstaged_token_does_not_block_a_clean_commit(repo):
    stage(repo, "playbook.yml", "name: clean\n")
    (repo / "vars.yml").write_text(f"offline_token: {fake_offline_token()}\n")  # never staged
    assert_passes(scan(repo, "--staged"))


def test_a_staged_token_is_blocked_in_a_repository_with_earlier_commits(repo):
    commit(repo, "playbook.yml", "name: clean\n")
    stage(repo, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    assert_blocked_by(scan(repo, "--staged"), "offline-token")


# The scan refuses to say "no leaks" when it couldn't read anything

def assert_cannot_run(result):
    assert result.returncode != 0, result.output
    assert "scan cannot run" in result.output, result.output


@pytest.mark.parametrize("flags", [("--staged",), ()], ids=["staged", "full"])
def test_a_folder_that_is_not_a_git_repository_cannot_be_scanned(tmp_path, flags):
    (tmp_path / "vars.yml").write_text("name: clean\n")
    assert_cannot_run(scan(tmp_path, *flags))


@pytest.mark.parametrize("flags", [("--staged",), ()], ids=["staged", "full"])
def test_a_repository_whose_git_folder_is_out_of_reach_cannot_be_scanned(tmp_path, flags):
    # A git worktree's .git is a file pointing elsewhere; in the container, that place isn't mounted.
    (tmp_path / ".git").write_text("gitdir: /nonexistent/.git/worktrees/wt\n")
    assert_cannot_run(scan(tmp_path, *flags))


def test_a_staged_scan_with_a_missing_index_file_cannot_run(repo):
    # git treats a missing index as "everything deleted" and shows nothing added, so a scan would pass.
    stage(repo, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    assert_cannot_run(scan(repo, "--staged", env={"GIT_INDEX_FILE": "/nonexistent/index"}))


# The full scan reads every commit

def test_a_clean_history_passes_the_full_scan(repo):
    commit(repo, "playbook.yml", "name: clean\n")
    commit(repo, "vars.yml", "offline_token: \"{{ lookup('env', 'OFFLINE_TOKEN') }}\"\n")
    assert_passes(scan(repo))


def test_the_full_scan_finds_a_secret_removed_in_a_later_commit(repo):
    # Deleting a token doesn't unpublish it: CI scans every commit, not just the last one.
    commit(repo, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    git(repo, "rm", "-q", "vars.yml")
    git(repo, "commit", "-q", "--no-verify", "-m", "remove token")
    assert_passes(scan(repo, "--staged"))  # nothing staged
    assert_blocked_by(scan(repo), "offline-token")


def test_the_full_scan_finds_a_secret_added_in_a_merge_commit(repo):
    # A merge commit's own changes (say, while resolving a conflict) aren't shown by a plain `git log -p`.
    commit(repo, "playbook.yml", "name: clean\n")
    git(repo, "switch", "-q", "-c", "topic")
    commit(repo, "topic.yml", "name: topic\n")
    git(repo, "switch", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "--no-commit", "topic")
    stage(repo, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    git(repo, "commit", "-q", "--no-verify", "-m", "merge topic")
    assert_blocked_by(scan(repo), "offline-token")


# The report never shows the secret, in either mode (CI logs are public)

@pytest.mark.parametrize("mode", ["staged", "full"])
def test_the_report_never_prints_any_part_of_the_secret(repo, mode):
    token = fake_offline_token()
    if mode == "staged":
        stage(repo, "vars.yml", f"offline_token: {token}\n")
        result = scan(repo, "--staged")
    else:
        commit(repo, "vars.yml", f"offline_token: {token}\n")
        result = scan(repo)
    assert_blocked_by(result, "offline-token")
    for part in token.split("."):
        assert part not in result.output
