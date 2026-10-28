"""Checks the Claude Code permission rules in .claude/settings.json.

Hard-to-undo GitHub actions must match an `ask` rule, so Claude Code asks first; `ask` wins over
`allow`. Kickoff comments must not. Rules are matched here with fnmatch, a close approximation of
Claude Code's `*` wildcard; the live check is trying a command in a new session (issue #28).
"""

import json
from fnmatch import fnmatchcase
from pathlib import Path

import pytest

SETTINGS = Path(__file__).resolve().parents[2] / ".claude" / "settings.json"

ASK_FIRST = [
    "gh pr merge 30 --squash --admin",
    "git tag -a m02 -m M02",
    "git push origin m02",
    "git push origin v0.1.0",
    "git push origin --tags",
    "git push origin main",
    "gh issue close 9",
    "gh issue delete 27 --yes",
    "gh release create v0.1.0",
    "gh repo edit --enable-wiki=false",
    "gh api -X PUT repos/vishwanathj/ocp_lab.ai/rulesets/24629416",
    "gh api repos/vishwanathj/ocp_lab.ai/rulesets/24629416 --method DELETE",
    "gh api graphql -f query=mutation",
]

NO_CONFIRMATION = [
    "gh issue comment 28 --body-file kickoff.md",
    "gh pr create --fill",
    "git push -u origin 28-kickoff-and-posting-rules",
]


def _rules(kind):
    rules = json.loads(SETTINGS.read_text())["permissions"].get(kind, [])
    return [r[len("Bash("):-1] for r in rules if r.startswith("Bash(") and r.endswith(")")]


def _matches(command, patterns):
    return any(fnmatchcase(command, p) for p in patterns)


@pytest.mark.parametrize("command", ASK_FIRST)
def test_hard_to_undo_commands_ask_first(command):
    assert _matches(command, _rules("ask")), f"no ask rule matches: {command}"


@pytest.mark.parametrize("command", NO_CONFIRMATION)
def test_routine_commands_need_no_confirmation(command):
    assert _matches(command, _rules("allow")), f"no allow rule matches: {command}"
    assert not _matches(command, _rules("ask")), f"an ask rule matches: {command}"
