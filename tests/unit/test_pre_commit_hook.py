"""Tests for the pre-commit hook in .githooks/ and `make setup` (issue #8).

Each test copies the files the hook needs into a throwaway git repository and commits there with a
fake container engine first in line: it answers `image inspect` and runs `run`'s command on this
machine, with the /work mount mapped back to the repository. Tokens are generated at run time.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from test_secret_scan import fake_offline_token

ROOT = Path(__file__).resolve().parents[2]
FILES = ["Makefile", "Containerfile", "requirements-dev.txt", ".gitleaks.toml",
         ".githooks/pre-commit", "tools/scan_secrets.sh"]

FAKE_ENGINE = '''#!/usr/bin/env python3
"""Fake podman/docker. With FAKE_ENGINE_BROKEN set, every call fails like an engine that can't start."""
import os, subprocess, sys

if os.environ.get("FAKE_ENGINE_BROKEN"):
    sys.exit("fake engine: cannot connect to the container service")
args = sys.argv[1:]
if args[:2] == ["image", "inspect"] or args[0] == "build":
    sys.exit(0)
assert args[0] == "run", args
mounts, i = {}, 1
while args[i].startswith("-"):
    if args[i] == "-v":
        source, target = args[i + 1].split(":")[:2]
        mounts[target] = source
    i += 2 if args[i] in ("-v", "-e", "--security-opt") else 1
command = args[i + 1:]  # args[i] is the image

def local(arg):
    for target, source in mounts.items():
        if arg == target or arg.startswith(target + "/"):
            return source + arg[len(target):]
    return arg

os.chdir(mounts["/work"])
sys.exit(subprocess.run([local(a) for a in command]).returncode)
'''


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "repo"
    for name in FILES:
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, repo / name)
    engine = tmp_path / "bin" / "podman"
    engine.parent.mkdir()
    engine.write_text(FAKE_ENGINE)
    engine.chmod(engine.stat().st_mode | stat.S_IXUSR)
    env = {
        "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
        "HOME": str(tmp_path), "PATH": "/usr/local/bin:/usr/bin:/bin", "ENGINE": str(engine),
    }
    run(repo, env, "git", "init", "-q", "-b", "main")
    return repo, env


def run(repo, env, *args):
    return subprocess.run(args, cwd=repo, env=env, capture_output=True, text=True)


def setup(repo, env):
    # A fail-closed test must not pass just because the hook was never turned on.
    result = run(repo, env, "make", "setup")
    assert result.returncode == 0, result.stdout + result.stderr


def commit(repo, env, name, text):
    (repo / name).write_text(text)
    run(repo, env, "git", "add", name)
    return run(repo, env, "git", "commit", "-q", "-m", f"add {name}")


def commits(repo, env):
    return run(repo, env, "git", "rev-list", "--all", "--count").stdout.strip()


def test_make_setup_points_git_at_the_hooks(repo):
    repo, env = repo
    result = run(repo, env, "make", "setup")
    assert result.returncode == 0, result.stdout + result.stderr
    assert run(repo, env, "git", "config", "core.hooksPath").stdout.strip() == ".githooks"


def test_the_hook_is_executable():
    assert os.access(ROOT / ".githooks" / "pre-commit", os.X_OK)


def test_the_hook_blocks_a_commit_with_a_token(repo):
    repo, env = repo
    setup(repo, env)
    result = commit(repo, env, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    assert result.returncode != 0
    assert commits(repo, env) == "0"


def test_the_hook_lets_a_clean_commit_through(repo):
    repo, env = repo
    setup(repo, env)
    result = commit(repo, env, "playbook.yml", "offline_token: \"{{ lookup('env', 'OFFLINE_TOKEN') }}\"\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert commits(repo, env) == "1"


def test_the_hook_fails_closed_when_the_container_cant_run(repo):
    repo, env = repo
    setup(repo, env)
    env = {**env, "FAKE_ENGINE_BROKEN": "1"}
    result = commit(repo, env, "playbook.yml", "name: clean\n")
    assert result.returncode != 0
    assert "commit blocked" in result.stderr
    assert commits(repo, env) == "0"


def test_the_hook_fails_closed_without_podman_or_docker(repo):
    repo, env = repo
    setup(repo, env)
    env = {k: v for k, v in env.items() if k != "ENGINE"}  # and neither is on PATH in the dev container
    result = commit(repo, env, "playbook.yml", "name: clean\n")
    assert result.returncode != 0
    assert "commit blocked" in result.stderr
    assert commits(repo, env) == "0"
