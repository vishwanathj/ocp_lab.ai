"""Tests for when `make merge` refuses to merge (issue #9, lessons L4).

Inputs have the shapes GitHub returns: `gh pr checks --required --json name,bucket`, and the head
commit's check runs and statuses from the REST API.
"""

import pytest

import merge_message as mm

GREEN = [{"name": "make test", "bucket": "pass"}]
REVIEWED = {"check_runs": [{"name": "CodeRabbit", "conclusion": "success",
                            "output": {"title": "Review completed"}}], "statuses": []}
RATE_LIMITED = {"check_runs": [{"name": "CodeRabbit", "conclusion": "neutral",
                                "output": {"title": "Review rate limited"}}], "statuses": []}
SKIPPED = {"check_runs": [], "statuses": [{"context": "CodeRabbit", "state": "success",
           "description": "Review skipped: manual review required for this OSS repository"}]}
NO_REVIEW = {"check_runs": [{"name": "make test", "conclusion": "success", "output": {"title": None}}],
             "statuses": []}


def test_green_checks_and_a_review_allow_the_merge():
    decision = mm.merge_decision(GREEN, REVIEWED, allow_skipped_review=False)
    assert decision.ok and decision.review_note is None


@pytest.mark.parametrize("bucket", ["fail", "pending", "cancel", "skipping"])
@pytest.mark.parametrize("allow", [False, True])
def test_a_required_check_that_did_not_pass_always_blocks(bucket, allow):
    checks = [{"name": "make test", "bucket": bucket}]
    decision = mm.merge_decision(checks, REVIEWED, allow_skipped_review=allow)
    assert not decision.ok
    assert "make test" in decision.reason and bucket in decision.reason


def test_no_required_checks_blocks():
    decision = mm.merge_decision([], REVIEWED, allow_skipped_review=True)
    assert not decision.ok and "no required checks" in decision.reason


@pytest.mark.parametrize("review", [RATE_LIMITED, SKIPPED, NO_REVIEW], ids=["rate-limited", "skipped", "missing"])
def test_a_review_that_did_not_run_blocks_without_the_flag(review):
    decision = mm.merge_decision(GREEN, review, allow_skipped_review=False)
    assert not decision.ok
    assert "ALLOW_SKIPPED_REVIEW=1" in decision.reason
    assert "@coderabbitai review" in decision.reason


@pytest.mark.parametrize("review, said", [
    (RATE_LIMITED, "Review rate limited"),
    (SKIPPED, "Review skipped: manual review required for this OSS repository"),
    (NO_REVIEW, "no CodeRabbit check"),
])
def test_the_flag_allows_a_skipped_review_and_the_message_says_so(review, said):
    decision = mm.merge_decision(GREEN, review, allow_skipped_review=True)
    assert decision.ok
    assert decision.review_note == (
        f"Review: CodeRabbit didn't review the last commit ({said}); merged with ALLOW_SKIPPED_REVIEW=1.")


def test_a_review_counts_when_any_coderabbit_result_completed():
    review = {"check_runs": RATE_LIMITED["check_runs"] + REVIEWED["check_runs"], "statuses": []}
    assert mm.merge_decision(GREEN, review, allow_skipped_review=False).ok
