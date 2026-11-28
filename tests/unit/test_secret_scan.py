"""Tests for tools/scan_secrets.sh, the gitleaks scan behind the pre-commit hook and CI (issue #8).

Each test builds a throwaway git repository and scans it with the project's real .gitleaks.toml.
A "blocked" test also checks which rule fired: a crash or a bad config fails the scan too, and the
fake token would be caught by gitleaks' built-in rules even if the project's own rule were missing.

The scanner's contract: exit 0 when nothing is found; exit 1 and print one finding record per secret,
with a `RuleID:` line (gitleaks' verbose report) and the secret redacted. If the scan can't read the
changes (git can't read the repository or the index, or reports a problem while gitleaks reads them),
exit 2 with "scan cannot run": gitleaks itself would report "no leaks found" and exit 0.
"""

import json
import os
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
    assert result.returncode == 1, result.output
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


@pytest.mark.parametrize("depth", [1, 2], ids=["escaped once", "escaped twice"])
def test_a_pull_secret_inside_a_json_string_is_blocked(repo, depth):
    # The assisted-service API carries the pull secret as a JSON *string*, so request bodies and
    # examples hold it escaped: "pull_secret": "{\"auths\": {... \"auth\": \"...\"}}". A recorded
    # response that stores such a body as a string again escapes it twice: \\\"auth\\\".
    text = fake_pull_secret()
    for _ in range(depth):
        text = json.dumps({"pull_secret": text})
    stage(repo, "request.json", text + "\n")
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
    # Exactly 2: a scan that found a token and then hit a problem would exit 1 even without the check.
    assert result.returncode == 2, result.output
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


# gitleaks reads the changes from a git command it runs itself. If git writes anything to its error
# output, apart from a few notices gitleaks knows are harmless, gitleaks stops reading, logs an error,
# says "no leaks found" and exits 0 (issue #42). Each problem below makes git complain on every command;
# the scan must say it cannot run, and pass on git's message so the user knows what to fix.

def unreadable_gitattributes(repo):
    # root can read any file, so this only works as another user; the dev container runs as `dev`.
    if os.geteuid() == 0:
        pytest.skip("root ignores file permissions")
    (repo / ".gitattributes").write_text("*.yml text\n")
    (repo / ".gitattributes").chmod(0)


GIT_PROBLEMS = {
    "invalid attribute name": (lambda repo: (repo / ".gitattributes").write_text("*.yml -!x\n"),
                               "is not a valid attribute name"),
    "negative attribute pattern": (lambda repo: (repo / ".gitattributes").write_text("!*.yml text\n"),
                                   "Negative patterns are ignored"),
    "bad info/attributes": (lambda repo: (repo / ".git" / "info" / "attributes").write_text("*.yml -!x\n"),
                            "is not a valid attribute name"),
    "unreadable .gitattributes": (unreadable_gitattributes, "unable to access"),
    "bad config value": (lambda repo: git(repo, "config", "diff.renames", "maybe"), "bad boolean config value"),
    "broken alternates": (lambda repo: (repo / ".git" / "objects" / "info" / "alternates").write_text("/nonexistent/objects\n"),
                          "alternate object path"),
}


def scan_in(repo, mode):
    return scan(repo, *(["--staged"] if mode == "staged" else []))


@pytest.mark.parametrize("problem", GIT_PROBLEMS)
@pytest.mark.parametrize("mode", ["staged", "full"])
def test_a_scan_during_which_git_reports_a_problem_cannot_run(repo, mode, problem):
    token_line = f"offline_token: {fake_offline_token()}\n"
    if mode == "staged":
        stage(repo, "vars.yml", token_line)
    else:
        commit(repo, "vars.yml", token_line)
    make_problem, message = GIT_PROBLEMS[problem]
    make_problem(repo)
    result = scan_in(repo, mode)
    assert_cannot_run(result)
    assert message in result.output, result.output


def test_a_full_scan_of_a_history_with_a_missing_object_cannot_run(repo):
    # git stops partway through the history: every commit after the missing object goes unread.
    commit(repo, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    blob = subprocess.run(["git", "rev-parse", "HEAD:vars.yml"], cwd=repo, capture_output=True,
                          text=True, check=True).stdout.strip()
    (repo / ".git" / "objects" / blob[:2] / blob[2:]).unlink()
    result = scan(repo)
    assert_cannot_run(result)
    assert "unable to read" in result.output, result.output


def test_a_scan_that_may_have_found_a_token_before_a_problem_cannot_run(repo):
    # git log shows the newest commit, with the token, then dies on an older one. gitleaks reads git's
    # output and its errors side by side, so whether it found the token first is down to timing. Either
    # way the scan must say it cannot run: "leaks found" would hide that the rest went unread.
    commit(repo, "notes.txt", "older notes\n")
    blob = subprocess.run(["git", "rev-parse", "HEAD:notes.txt"], cwd=repo, capture_output=True,
                          text=True, check=True).stdout.strip()
    commit(repo, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    (repo / ".git" / "objects" / blob[:2] / blob[2:]).unlink()
    assert_cannot_run(scan(repo))


# The scan also needs proof that gitleaks finished: its closing "no leaks found" or "leaks found" line.
# Without it, exit 0 proves nothing. With a full /tmp, for example, gitleaks' log can't be written, so
# no ERR line can be seen either, and the scan used to pass in silence. Each fake below stands in for
# gitleaks, first on the PATH.
FAKE_GITLEAKS = {
    "ends without a word": "exit 0",
    "is killed": "kill -9 $$",
    "fails with a fatal error": 'echo "4:00AM FTL unable to load gitleaks config" >&2; exit 1',
    # What gitleaks says when it stopped early: "no leaks found" is in it, but isn't the closing line.
    "reports a partial scan": 'echo "4:00AM WRN no leaks found in partial scan" >&2; exit 0',
    # The closing line is there, but no exit status gitleaks gives for a finished scan.
    "exits with an unknown status": 'echo "4:00AM INF no leaks found" >&2; exit 3',
}


@pytest.mark.parametrize("fake", FAKE_GITLEAKS)
def test_a_scan_with_no_proof_that_gitleaks_finished_cannot_run(repo, tmp_path, fake):
    stage(repo, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    (bin_dir / "gitleaks").write_text(f"#!/bin/sh\n{FAKE_GITLEAKS[fake]}\n")
    (bin_dir / "gitleaks").chmod(0o755)
    assert_cannot_run(scan(repo, "--staged", env={"PATH": f"{bin_dir}:{GIT_ENV['PATH']}"}))


def test_a_scan_without_gitleaks_cannot_run(repo):
    # gitleaks is in /usr/local/bin in the dev container; git, sh and the rest are in /usr/bin and /bin.
    stage(repo, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    assert_cannot_run(scan(repo, "--staged", env={"PATH": "/usr/bin:/bin"}))


@pytest.mark.parametrize("mode", ["staged", "full"])
def test_a_notice_gitleaks_knows_is_harmless_does_not_stop_the_scan(repo, mode):
    # With more renames than diff.renameLimit, git says rename detection was skipped and shows each
    # rename as a deletion and an addition, so nothing goes unread. gitleaks logs it as a warning.
    for i in range(3):
        commit(repo, f"notes{i}.txt", f"notes number {i}, long enough to be matched as a rename\n")
    for i in range(3):
        git(repo, "mv", f"notes{i}.txt", f"moved{i}.txt")
        (repo / f"moved{i}.txt").write_text(f"notes number {i}, long enough to be matched as a rename\nmore\n")
    stage(repo, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    git(repo, "add", "-A")
    if mode == "full":
        git(repo, "commit", "-q", "--no-verify", "-m", "move notes")
    git(repo, "config", "diff.renameLimit", "1")
    result = scan_in(repo, mode)
    assert "rename detection was skipped" in result.output, result.output  # the notice did happen
    assert_blocked_by(result, "offline-token")


def test_a_broken_fsmonitor_setting_does_not_stop_the_staged_scan(repo):
    # core.fsmonitor speeds up reading the work tree, which a staged scan doesn't need. A hook the
    # container can't run (a host path, say) makes git complain, so the scan must not use it.
    stage(repo, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    git(repo, "config", "core.fsmonitor", "/nonexistent/fsmonitor-hook")
    assert_blocked_by(scan(repo, "--staged"), "offline-token")


@pytest.mark.parametrize("url", ["my_alias:owner/repo", "someone@github.com:owner/repo"])
def test_a_remote_gitleaks_cant_parse_does_not_stop_the_full_scan(repo, url):
    # gitleaks reads the remote's URL to link findings to the code host, and logs an error when it
    # can't parse it, as for an ssh alias. That isn't a problem with reading the changes.
    commit(repo, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    git(repo, "remote", "add", "origin", url)
    assert_blocked_by(scan(repo), "offline-token")


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


@pytest.mark.parametrize("how", ["marked binary", "nul byte"])
def test_the_full_scan_reads_files_git_treats_as_binary(repo, how):
    # git shows no contents for a file it treats as binary, so a scan of its diff would find nothing.
    # Either .gitattributes says so, or git guesses it from a NUL byte.
    token_line = f"offline_token: {fake_offline_token()}\n"
    if how == "marked binary":
        commit(repo, ".gitattributes", "*.env binary\n")
        commit(repo, "creds.env", token_line)
    else:
        commit(repo, "notes.txt", "\x00" + token_line)
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
