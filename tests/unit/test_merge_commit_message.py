"""Tests for the squash commit message and the command line of tools/merge_message.py (issue #9)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import merge_message as mm

BODY = """Closes #9

## Summary
<!-- What changed and why, in two or three sentences. -->
`make merge` merges a PR with its AI usage.

- one command instead of five steps

## Developer notes
Not part of the commit.
"""
PR = {"number": 30, "title": "Add make merge", "body": BODY, "headRefOid": "abc123"}
BLOCK = "AI usage (Claude Code) — estimate\n- Model: claude-opus-5-5 · 3 responses"
SIGNOFF = "Signed-off-by: A Maintainer <maintainer@example.com>"
TOOLS = Path(mm.__file__).parent


def test_the_message_keeps_the_summary_closes_usage_and_trailers():
    subject, message = mm.commit_message(PR, BLOCK, ["claude-opus-5-5"], None, SIGNOFF)
    assert subject == "Add make merge (#30)"
    assert message == (
        "`make merge` merges a PR with its AI usage.\n\n- one command instead of five steps\n\n"
        "Closes #9\n\n"
        f"{BLOCK}\n\n"
        f"{SIGNOFF}\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
    )


def test_an_accepted_skipped_review_is_recorded_before_closes():
    _, message = mm.commit_message(PR, BLOCK, ["claude-opus-5-5"], "Review: skipped.", SIGNOFF)
    assert "five steps\n\nReview: skipped.\n\nCloses #9" in message


def test_without_ai_usage_there_is_no_co_author():
    _, message = mm.commit_message(PR, "AI usage: none reported", [], None, SIGNOFF)
    assert message.endswith(f"AI usage: none reported\n\n{SIGNOFF}")


def test_an_unknown_model_is_credited_by_its_id():
    _, message = mm.commit_message(PR, BLOCK, ["claude-new-9"], None, SIGNOFF)
    assert message.endswith("Co-Authored-By: claude-new-9 <noreply@anthropic.com>")


@pytest.mark.parametrize("body, missing", [
    ("## Summary\nText\n", "Closes #"),
    ("Closes #9\n\n## Developer notes\nText\n", "## Summary"),
    ("Closes #9\n\n## Summary\n<!-- only the template comment -->\n\n## Checklist\n", "## Summary"),
])
def test_a_pr_without_closes_or_a_summary_is_refused(body, missing):
    with pytest.raises(ValueError, match=missing):
        mm.commit_message({**PR, "body": body}, BLOCK, [], None, SIGNOFF)


def run_cli(tmp_path, *extra, checks=None, head=None):
    files = {
        "pr.json": PR,
        "checks.json": checks if checks is not None else [{"name": "make test", "bucket": "pass"}],
        "head.json": head or {"check_runs": [{"name": "CodeRabbit", "conclusion": "success",
                                              "output": {"title": "Review completed"}}], "statuses": []},
    }
    for name, data in files.items():
        (tmp_path / name).write_text(json.dumps(data))
    return subprocess.run(
        [sys.executable, str(TOOLS / "merge_message.py"),
         "--pr", str(tmp_path / "pr.json"), "--checks", str(tmp_path / "checks.json"),
         "--head", str(tmp_path / "head.json"), "--logs", str(tmp_path / "no-logs"),
         "--start", "2026-10-27T10:00:00+00:00", "--now", "2026-10-27T12:00:00+00:00",
         "--signoff", SIGNOFF, *extra],
        capture_output=True, text=True,
    )


def test_the_command_line_prints_subject_message_and_comment(tmp_path):
    result = run_cli(tmp_path)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out["subject"] == "Add make merge (#30)"
    assert out["comment"] == "AI usage: none reported"
    assert out["message"].endswith(f"AI usage: none reported\n\n{SIGNOFF}")


def test_the_command_line_refuses_with_the_reason_and_exit_1(tmp_path):
    result = run_cli(tmp_path, checks=[{"name": "make test", "bucket": "fail"}])
    assert result.returncode == 1
    assert result.stdout == ""
    assert "make test (fail)" in result.stderr


def test_the_command_line_passes_the_skipped_review_flag(tmp_path):
    head = {"check_runs": [{"name": "CodeRabbit", "conclusion": "neutral",
                            "output": {"title": "Review rate limited"}}], "statuses": []}
    assert run_cli(tmp_path, head=head).returncode == 1
    result = run_cli(tmp_path, "--allow-skipped-review", "1", head=head)
    assert result.returncode == 0, result.stderr
    assert "merged with ALLOW_SKIPPED_REVIEW=1." in json.loads(result.stdout)["message"]


@pytest.mark.parametrize("value", ["0", "yes", "true"])
def test_the_skipped_review_flag_accepts_only_1(tmp_path, value):
    head = {"check_runs": [{"name": "CodeRabbit", "conclusion": "neutral",
                            "output": {"title": "Review rate limited"}}], "statuses": []}
    result = run_cli(tmp_path, "--allow-skipped-review", value, head=head)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "invalid choice" in result.stderr


def test_the_shell_format_separates_the_three_parts_with_nul(tmp_path):
    # tools/merge.sh reads these with `read -d ''`; the host has no jq or Python to parse JSON.
    result = run_cli(tmp_path, "--format", "nul")
    assert result.returncode == 0, result.stderr
    subject, message, comment, rest = result.stdout.split("\0")
    assert (subject, comment, rest) == ("Add make merge (#30)", "AI usage: none reported", "")
    assert message.startswith("`make merge` merges a PR")
