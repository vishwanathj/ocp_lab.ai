"""Tests for the pre-commit hook in .githooks/ and `make setup` (issue #8).

Each test copies the files the hook needs into a throwaway git repository and commits there with a
fake container engine first in line. Each "blocked" test also checks why it was blocked, so a missing
tool can't pass for a working hook. Tokens are generated at run time.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from fake_secrets import fake_offline_token

ROOT = Path(__file__).resolve().parents[2]
FILES = ["Makefile", "Containerfile", "requirements-dev.txt", ".gitleaks.toml",
         ".githooks/pre-commit", "tools/scan_secrets.sh"]

FAKE_ENGINE = '''#!/usr/bin/env python3
"""Fake podman/docker. With FAKE_ENGINE_BROKEN set, every call fails like an engine that can't start."""
import os, subprocess, sys

if os.environ.get("FAKE_ENGINE_BROKEN"):
    sys.exit("fake engine: cannot connect to the container service")
args = sys.argv[1:]

# `make` checks the image exists, and builds it if not: pretend it's there.
if args[:2] == ["image", "inspect"] or args[0] == "build":
    sys.exit(0)

# `run [options] IMAGE COMMAND...`: run COMMAND here, with each -v mount mapped back to its source.
assert args[0] == "run", args
mounts, env, i = {}, dict(os.environ), 1
while args[i].startswith("-"):
    if args[i] == "--rm":
        i += 1
    elif args[i] == "-v":
        source, target = args[i + 1].split(":")[:2]
        mounts[target] = source
        i += 2
    elif args[i] == "-e":
        key, _, value = args[i + 1].partition("=")
        env[key] = value
        i += 2
    else:
        sys.exit(f"fake engine: unknown option {args[i]} in {args}")
command = args[i + 1:]  # args[i] is the image

def local(arg):
    for target, source in mounts.items():
        if arg == target or arg.startswith(target + "/"):
            return source + arg[len(target):]
    return arg

os.chdir(mounts["/work"])
sys.exit(subprocess.run([local(a) for a in command], env=env).returncode)
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


@pytest.fixture
def no_engine_path(tmp_path):
    """A PATH with the tools the hook needs but no podman or docker, whatever the machine has."""
    bin_dir = tmp_path / "no-engine-bin"
    bin_dir.mkdir()
    for tool in ["git", "make", "sh", "cat", "cut", "grep", "awk"]:
        (bin_dir / tool).symlink_to(shutil.which(tool))
    return str(bin_dir)


def run(repo, env, *args):
    result = subprocess.run(args, cwd=repo, env=env, capture_output=True, text=True)
    result.output = result.stdout + result.stderr
    return result


def setup(repo, env):
    # A fail-closed test must not pass just because the hook was never turned on.
    result = run(repo, env, "make", "setup")
    assert result.returncode == 0, result.output


def commit(repo, env, name, text):
    (repo / name).write_text(text)
    assert run(repo, env, "git", "add", name).returncode == 0
    return run(repo, env, "git", "commit", "-q", "-m", f"add {name}")


def commits(repo, env):
    return run(repo, env, "git", "rev-list", "--all", "--count").stdout.strip()


def test_make_setup_points_git_at_the_hooks(repo):
    repo, env = repo
    setup(repo, env)
    assert run(repo, env, "git", "config", "core.hooksPath").stdout.strip() == ".githooks"


def test_make_setup_works_without_podman_or_docker(repo, no_engine_path):
    # setup only changes git config, so it mustn't need a container engine.
    repo, env = repo
    env = {**env, "PATH": no_engine_path}
    del env["ENGINE"]
    setup(repo, env)
    assert run(repo, env, "git", "config", "core.hooksPath").stdout.strip() == ".githooks"


def test_the_hook_is_executable():
    assert os.access(ROOT / ".githooks" / "pre-commit", os.X_OK)


def test_the_hook_blocks_a_commit_with_a_token(repo):
    repo, env = repo
    setup(repo, env)
    result = commit(repo, env, "vars.yml", f"offline_token: {fake_offline_token()}\n")
    assert result.returncode != 0
    assert "commit blocked" in result.output
    assert "offline-token" in result.output, result.output
    assert commits(repo, env) == "0"


def test_the_hook_lets_a_clean_commit_through(repo):
    repo, env = repo
    setup(repo, env)
    result = commit(repo, env, "playbook.yml", "offline_token: \"{{ lookup('env', 'OFFLINE_TOKEN') }}\"\n")
    assert result.returncode == 0, result.output
    assert commits(repo, env) == "1"


def test_the_hook_fails_closed_when_the_container_cant_run(repo):
    repo, env = repo
    setup(repo, env)
    env = {**env, "FAKE_ENGINE_BROKEN": "1"}
    result = commit(repo, env, "playbook.yml", "name: clean\n")
    assert result.returncode != 0
    assert "commit blocked" in result.output
    assert "cannot connect to the container service" in result.output, result.output
    assert commits(repo, env) == "0"


def test_the_hook_fails_closed_without_podman_or_docker(repo, no_engine_path):
    repo, env = repo
    setup(repo, env)
    env = {**env, "PATH": no_engine_path}
    del env["ENGINE"]
    result = commit(repo, env, "playbook.yml", "name: clean\n")
    assert result.returncode != 0
    assert "commit blocked" in result.output
    assert "Neither podman nor docker was found" in result.output, result.output
    assert commits(repo, env) == "0"
