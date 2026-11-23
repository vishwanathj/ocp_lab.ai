"""Tests for tools/scan_secrets.sh, the gitleaks scan behind the pre-commit hook and CI (issue #8).

Each test builds a throwaway git repository and scans it with the project's real .gitleaks.toml.
No real credential is ever used: every token and pull secret is generated at run time from random
bytes, so nothing in this file is a secret and the history scan never flags it.
"""

import base64
import json
import secrets
import subprocess
import uuid
from pathlib import Path

import pytest

SCAN = Path(__file__).resolve().parents[2] / "tools" / "scan_secrets.sh"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin",
}


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def fake_offline_token():
    """A random JWT shaped like a Red Hat offline token; it signs nothing and opens nothing."""
    header = {"alg": "HS512", "typ": "JWT", "kid": str(uuid.uuid4())}
    payload = {"typ": "Offline", "jti": str(uuid.uuid4()), "sub": secrets.token_hex(16)}
    return ".".join([b64url(json.dumps(header).encode()), b64url(json.dumps(payload).encode()),
                     b64url(secrets.token_bytes(64))])


def fake_pull_secret():
    """A random pull secret: registry logins whose `auth` is base64 of user:password."""
    auth = base64.b64encode(f"user:{secrets.token_urlsafe(48)}".encode()).decode()
    return json.dumps({"auths": {"cloud.openshift.com": {"auth": auth, "email": "user@example.com"}}})


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, env=GIT_ENV, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    return tmp_path


def stage(repo, name, text):
    (repo / name).write_text(text)
    git(repo, "add", name)


def scan(repo, *flags):
    return subprocess.run([str(SCAN), *flags, str(repo)], env=GIT_ENV, capture_output=True, text=True)


@pytest.mark.parametrize("line", [
    "offline_token: {token}",
    "export OFFLINE_TOKEN={token}",
    'offline_token = "{token}"',
])
def test_a_staged_offline_token_is_blocked(repo, line):
    stage(repo, "vars.yml", line.format(token=fake_offline_token()) + "\n")
    assert scan(repo, "--staged").returncode != 0


def test_a_staged_pull_secret_is_blocked(repo):
    stage(repo, "pull-secret.json", fake_pull_secret() + "\n")
    assert scan(repo, "--staged").returncode != 0


def test_a_change_with_no_secrets_passes(repo):
    # How the collection is meant to be used: the token comes from the environment, never the file.
    stage(repo, "playbook.yml", "offline_token: \"{{ lookup('env', 'OFFLINE_TOKEN') }}\"\n")
    result = scan(repo, "--staged")
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_line_marked_gitleaks_allow_passes(repo):
    stage(repo, "vars.yml", f"offline_token: {fake_offline_token()}  # gitleaks:allow\n")
    result = scan(repo, "--staged")
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_report_never_prints_the_secret(repo):
    token = fake_offline_token()
    stage(repo, "vars.yml", f"offline_token: {token}\n")
    result = scan(repo, "--staged")
    assert result.returncode != 0
    assert token not in result.stdout + result.stderr


def test_the_full_scan_finds_a_secret_removed_in_a_later_commit(repo):
    # Deleting a token doesn't unpublish it: CI scans every commit, not just the last one.
    stage(repo, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    git(repo, "commit", "-q", "--no-verify", "-m", "add token")
    git(repo, "rm", "-q", "vars.yml")
    git(repo, "commit", "-q", "--no-verify", "-m", "remove token")
    assert scan(repo, "--staged").returncode == 0  # nothing staged
    assert scan(repo).returncode != 0
