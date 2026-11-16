"""Tests for tools/merge.sh, the host side of `make merge` (issue #9).

Each test builds a throwaway git repository with a local "origin", and puts fake `gh` and container
engine scripts first on PATH. Nothing talks to GitHub and no token is used: the fake `gh` answers
from a JSON file and logs every call, and the fake engine runs tools/merge_message.py directly.
"""

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
SIGNOFF = "Signed-off-by: A Maintainer <maintainer@example.com>"
BODY = "Closes #9\n\n## Summary\nAdds make merge.\n\n## Test evidence\nAll green.\n"

FAKE_GH = '''#!/usr/bin/env python3
"""Fake gh: answers from $FAKE_GH_STATE and appends each call to $FAKE_GH_LOG."""
import json, os, sys
from pathlib import Path

state = json.loads(Path(os.environ["FAKE_GH_STATE"]).read_text())
args = sys.argv[1:]
call = {"args": args}
if "--body-file" in args:
    call["body"] = Path(args[args.index("--body-file") + 1]).read_text()
with open(os.environ["FAKE_GH_LOG"], "a") as log:
    log.write(json.dumps(call) + "\\n")

def show(value):
    print(value if isinstance(value, str) else json.dumps(value))

if args[:2] == ["pr", "view"]:
    pr = state["pr"]
    show(str(pr[args[args.index("--jq") + 1].lstrip(".")]) if "--jq" in args else pr)
elif args[:2] == ["pr", "checks"] and "--jq" in args:
    # The re-check right before merging; gh evaluates the --jq expression itself.
    assert args[args.index("--jq") + 1] == 'length > 0 and all(.bucket == "pass")', args
    recheck = state.get("recheck", state["checks"])
    show("true" if recheck and all(c["bucket"] == "pass" for c in recheck) else "false")
    sys.exit(state.get("recheck_exit", 0))
elif args[:2] == ["pr", "checks"] and "--json" in args:
    show(state["checks"])
    sys.exit(0 if all(c["bucket"] == "pass" for c in state["checks"]) else 8)
elif args[:2] == ["pr", "checks"]:
    sys.exit(state.get("recheck_exit", 0))
elif args[0] == "api" and args[1].endswith("/check-runs"):
    show(state["check_runs"])
elif args[0] == "api" and args[1].endswith("/statuses"):
    show(state["statuses"])
elif args[:2] == ["pr", "merge"]:
    sys.exit(0)
elif args[:2] == ["pr", "comment"]:
    sys.exit(state.get("comment_exit", 0))
else:
    sys.exit(f"fake gh: unexpected call {args}")
'''

FAKE_ENGINE = '''#!/usr/bin/env python3
"""Fake podman/docker: runs the command on this machine, with each -v mount mapped back to its source."""
import os, sys

args = sys.argv[1:]
assert args[0] == "run", args
mounts, i = {}, 1
while args[i].startswith("-"):
    if args[i] == "-v":
        source, target = args[i + 1].split(":")[:2]
        mounts[target] = source
    i += 2 if args[i] in ("-v", "--security-opt") else 1
command = args[i + 1:]  # args[i] is the image

def local(arg):
    for target, source in mounts.items():
        if arg == target or arg.startswith(target + "/"):
            return source + arg[len(target):]
    return arg

command = [sys.executable if command[0] == "python" else command[0]] + [local(a) for a in command[1:]]
os.chdir(mounts["/work"])
os.execv(command[0], command)
'''


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def executable(path, text):
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


@pytest.fixture
def repo(tmp_path):
    """A clone on branch 9-make-merge, pushed to a local origin, with the merge tools committed."""
    git(tmp_path, "init", "-q", "--bare", "-b", "main", "origin.git")
    work = tmp_path / "work"
    git(tmp_path, "clone", "-q", str(tmp_path / "origin.git"), str(work))
    git(work, "symbolic-ref", "HEAD", "refs/heads/main")
    git(work, "config", "user.name", "A Maintainer")
    git(work, "config", "user.email", "maintainer@example.com")
    shutil.copytree(TOOLS, work / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    git(work, "add", ".")
    git(work, "commit", "-q", "-m", "Start")
    git(work, "push", "-q", "origin", "HEAD:main")
    git(work, "switch", "-q", "-c", "9-make-merge")
    (work / "change.txt").write_text("change\n")
    git(work, "add", ".")
    git(work, "commit", "-q", "-m", "Change")
    git(work, "push", "-q", "-u", "origin", "9-make-merge")
    return work


@pytest.fixture
def gh_state(tmp_path, repo):
    """What the fake gh reports: a PR for the branch, a passing required check and a finished review."""
    return {
        "pr": {"number": 30, "title": "Add make merge", "body": BODY, "headRefOid": git(repo, "rev-parse", "HEAD")},
        "checks": [{"name": "make test", "bucket": "pass"}],
        "check_runs": [{"name": "CodeRabbit", "conclusion": "success", "output": {"title": "Review completed"}}],
        "statuses": [],
    }


def run_merge(tmp_path, repo, state, with_gh=True, **env):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    executable(bin_dir / "engine", FAKE_ENGINE)
    if with_gh:
        executable(bin_dir / "gh", FAKE_GH)
    (tmp_path / "gh-state.json").write_text(json.dumps(state))
    base = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "HOME": str(tmp_path),
            "ENGINE": str(bin_dir / "engine"), "IMAGE": "fake-image", "CLAUDE_LOGS": str(tmp_path / "no-logs"),
            "FAKE_GH_STATE": str(tmp_path / "gh-state.json"), "FAKE_GH_LOG": str(tmp_path / "gh-calls.jsonl")}
    result = subprocess.run(["bash", "tools/merge.sh"], cwd=repo, env={**base, **env}, capture_output=True, text=True)
    log = tmp_path / "gh-calls.jsonl"
    result.calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    return result


def called(result, *prefix):
    return [c for c in result.calls if c["args"][:len(prefix)] == list(prefix)]


def test_merges_with_the_built_message_then_posts_the_usage_comment(tmp_path, repo, gh_state):
    result = run_merge(tmp_path, repo, gh_state)
    assert result.returncode == 0, result.stderr
    [merge] = called(result, "pr", "merge")
    assert merge["args"][:5] == ["pr", "merge", "30", "--squash", "--admin"]
    assert merge["args"][merge["args"].index("--subject") + 1] == "Add make merge (#30)"
    assert merge["args"][merge["args"].index("--match-head-commit") + 1] == gh_state["pr"]["headRefOid"]
    assert merge["body"].startswith("Adds make merge.\n\nTested:\nAll green.\n\nCloses #9")
    assert merge["body"].endswith(SIGNOFF)
    [comment] = called(result, "pr", "comment")
    assert comment["args"][2] == "30" and comment["body"] == "AI usage: none reported"
    assert result.calls.index(merge) < result.calls.index(comment)
    assert git(repo, "branch", "--show-current") == "main"


def test_a_dry_run_prints_the_message_and_merges_nothing(tmp_path, repo, gh_state):
    result = run_merge(tmp_path, repo, gh_state, DRY_RUN="1")
    assert result.returncode == 0, result.stderr
    assert "Dry run; nothing merged." in result.stdout and "Closes #9" in result.stdout
    assert not called(result, "pr", "merge") and not called(result, "pr", "comment")


def test_without_gh_it_stops_with_a_clear_message(tmp_path, repo, gh_state):
    if shutil.which("gh"):
        pytest.skip("a real gh is on PATH; run this in the dev container with `make test`")
    result = run_merge(tmp_path, repo, gh_state, with_gh=False)
    assert result.returncode == 1
    assert "needs the GitHub CLI (gh)" in result.stderr


def test_refuses_on_main(tmp_path, repo, gh_state):
    git(repo, "switch", "-q", "main")
    result = run_merge(tmp_path, repo, gh_state)
    assert result.returncode == 1
    assert "not main" in result.stderr
    assert not called(result, "pr", "merge")


def test_refuses_when_PR_does_not_match_the_branch(tmp_path, repo, gh_state):
    # Lessons L1: the PR number is looked up from the branch, never assumed.
    result = run_merge(tmp_path, repo, gh_state, PR="29")
    assert result.returncode == 1
    assert "PR=29, but 9-make-merge belongs to PR #30" in result.stderr
    assert not called(result, "pr", "merge")


def test_refuses_when_the_local_branch_is_not_the_PR_head(tmp_path, repo, gh_state):
    (repo / "unpushed.txt").write_text("not pushed\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "Not pushed")
    result = run_merge(tmp_path, repo, gh_state)
    assert result.returncode == 1
    assert "isn't the PR's head commit" in result.stderr
    assert not called(result, "pr", "merge")


def test_a_failing_required_check_merges_nothing(tmp_path, repo, gh_state):
    result = run_merge(tmp_path, repo, {**gh_state, "checks": [{"name": "make test", "bucket": "fail"}]})
    assert result.returncode == 1
    assert "make test (fail)" in result.stderr
    assert not called(result, "pr", "merge")


def test_refuses_when_a_check_stops_passing_before_the_merge(tmp_path, repo, gh_state):
    # The checks are read again right before merging, because a rerun can change them meanwhile.
    result = run_merge(tmp_path, repo, {**gh_state, "recheck_exit": 8})
    assert result.returncode == 1
    assert "no longer passing; nothing was merged" in result.stderr
    assert not called(result, "pr", "merge")


@pytest.mark.parametrize("recheck", [[{"name": "make test", "bucket": "cancel"}], []], ids=["cancelled", "none"])
def test_the_recheck_accepts_only_passing_checks(tmp_path, repo, gh_state, recheck):
    # gh pr checks exits 0 when a required check was cancelled (CodeRabbit on #30), so its exit code isn't enough.
    result = run_merge(tmp_path, repo, {**gh_state, "recheck": recheck})
    assert result.returncode == 1
    assert "no longer passing; nothing was merged" in result.stderr
    assert not called(result, "pr", "merge")

def test_a_failed_comment_exits_non_zero_and_prints_the_block(tmp_path, repo, gh_state):
    result = run_merge(tmp_path, repo, {**gh_state, "comment_exit": 1})
    assert result.returncode == 1
    assert called(result, "pr", "merge")
    assert "posting the usage comment failed" in result.stderr
    assert "AI usage: none reported" in result.stderr


@pytest.mark.parametrize("value", ["0", "yes"])
def test_dry_run_accepts_only_1(tmp_path, repo, gh_state, value):
    result = run_merge(tmp_path, repo, gh_state, DRY_RUN=value)
    assert result.returncode == 1
    assert f"DRY_RUN must be 1 or empty, not '{value}'" in result.stderr
    assert not called(result, "pr", "merge")
