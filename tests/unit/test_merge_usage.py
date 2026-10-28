"""Tests for the AI usage block that `make merge` puts in the squash commit (issue #9).

Session logs are fake, written by the tests; no real logs are read.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import merge_message as mm

START = datetime(2026, 10, 27, 10, 0, tzinfo=timezone.utc)
END = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
PRICING = {
    "checked": "2026-10-07",
    "models": {
        "claude-opus-5-5": {
            "input": 4.0, "output": 20.0, "cache_read": 0.2,
            "cache_write_5m": 5.0, "cache_write_1h": 8.0,
        }
    },
}


def response(ts, msg_id="m1", req="r1", model="claude-opus-5-5", **usage):
    return {
        "type": "assistant", "timestamp": ts, "requestId": req,
        "message": {"id": msg_id, "model": model, "usage": usage},
    }


def write_log(tmp_path, *entries, name="session.jsonl"):
    path = tmp_path / "project" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        for e in entries:
            f.write((e if isinstance(e, str) else json.dumps(e)) + "\n")
    return tmp_path


def test_counts_only_responses_inside_the_window(tmp_path):
    logs = write_log(
        tmp_path,
        response("2026-10-27T09:59:59Z", "before", input_tokens=100),
        response("2026-10-27T11:00:00Z", "inside", input_tokens=7, output_tokens=3),
        response("2026-10-27T12:00:01Z", "after", input_tokens=100),
    )
    usage = mm.sum_usage(logs, START, END)
    assert usage.responses == 1
    assert usage.models["claude-opus-5-5"]["input"] == 7
    assert usage.models["claude-opus-5-5"]["output"] == 3


def test_counts_a_response_logged_twice_once(tmp_path):
    entry = response("2026-10-27T11:00:00Z", input_tokens=5)
    logs = write_log(tmp_path, entry, entry)
    write_log(tmp_path, entry, name="resumed.jsonl")
    usage = mm.sum_usage(logs, START, END)
    assert usage.responses == 1
    assert usage.models["claude-opus-5-5"]["input"] == 5


def test_splits_5_minute_and_1_hour_cache_writes(tmp_path):
    logs = write_log(tmp_path, response(
        "2026-10-27T11:00:00Z", cache_read_input_tokens=50, cache_creation_input_tokens=30,
        cache_creation={"ephemeral_5m_input_tokens": 10, "ephemeral_1h_input_tokens": 20},
    ))
    totals = mm.sum_usage(logs, START, END).models["claude-opus-5-5"]
    assert (totals["cache_read"], totals["cache_write_5m"], totals["cache_write_1h"]) == (50, 10, 20)


def test_older_logs_without_the_split_count_as_5_minute_writes(tmp_path):
    logs = write_log(tmp_path, response("2026-10-27T11:00:00Z", cache_creation_input_tokens=30))
    totals = mm.sum_usage(logs, START, END).models["claude-opus-5-5"]
    assert (totals["cache_write_5m"], totals["cache_write_1h"]) == (30, 0)


def test_skips_other_entries_and_broken_lines(tmp_path):
    logs = write_log(
        tmp_path,
        "not json",
        {"type": "user", "timestamp": "2026-10-27T11:00:00Z"},
        {"type": "assistant", "timestamp": "2026-10-27T11:00:00Z", "message": {"id": "x"}},
        response("2026-10-27T11:00:00Z", input_tokens=1),
    )
    assert mm.sum_usage(logs, START, END).responses == 1


def test_an_entry_without_a_model_is_not_counted(tmp_path):
    logs = write_log(
        tmp_path,
        response("2026-10-27T11:00:00Z", "no-model", model=None, input_tokens=100),
        response("2026-10-27T11:00:01Z", "named", input_tokens=1),
    )
    usage = mm.sum_usage(logs, START, END)
    assert usage.responses == 1
    assert list(usage.models) == ["claude-opus-5-5"]

def test_latest_entry_is_kept_for_the_log_lag(tmp_path):
    logs = write_log(tmp_path, response("2026-10-27T12:30:00Z", input_tokens=1))
    assert mm.sum_usage(logs, START, END).latest == datetime(2026, 10, 27, 12, 30, tzinfo=timezone.utc)


def test_block_shows_tokens_cost_and_what_was_not_measured(tmp_path):
    logs = write_log(tmp_path, response(
        "2026-10-27T11:00:00Z", input_tokens=1_000_000, output_tokens=100_000,
        cache_read_input_tokens=2_000_000,
        cache_creation={"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 500_000},
    ))
    usage = mm.sum_usage(logs, START, END)
    block = mm.usage_block(usage, PRICING, START, END)
    # $4 + $2 + $0.40 + $4 = $10.40
    assert block.splitlines() == [
        "AI usage (Claude Code) — estimate",
        "- Window: 2026-10-27 10:00 → 2026-10-27 12:00 UTC (branch created → merge)",
        "- Model: claude-opus-5-5 · 1 responses",
        "- Tokens: input 1,000,000 · output 100,000 · cache read 2,000,000 · cache write 1h 500,000 · cache write 5m 0",
        "- Estimated cost: $10.40 at API list prices (claude-opus-5-5: $4 in / $20 out / $0.20 cache read "
        "/ $5 & $8 cache write per MTok, checked 2026-10-07); billed via subscription, not per token",
        "- Log lag at merge: 3600 s, so the last response or two may be missing",
        "- Not measured: CodeRabbit review; work before the branch existed",
    ]


def test_no_responses_in_the_window_reports_none(tmp_path):
    logs = write_log(tmp_path, response("2026-10-27T09:00:00Z", input_tokens=1))
    assert mm.usage_block(mm.sum_usage(logs, START, END), PRICING, START, END) == "AI usage: none reported"


def test_a_missing_log_directory_reports_none(tmp_path):
    usage = mm.sum_usage(tmp_path / "absent", START, END)
    assert mm.usage_block(usage, PRICING, START, END) == "AI usage: none reported"


def test_an_unknown_model_is_flagged_not_priced(tmp_path):
    logs = write_log(
        tmp_path,
        response("2026-10-27T11:00:00Z", "a", input_tokens=1_000_000),
        response("2026-10-27T11:00:01Z", "b", model="claude-new-9", input_tokens=1_000_000),
    )
    block = mm.usage_block(mm.sum_usage(logs, START, END), PRICING, START, END)
    assert "- Estimated cost: $4.00 at API list prices" in block
    assert "- Unpriced models: claude-new-9 (not included in the cost)" in block


def test_the_pricing_table_is_dated_and_prices_the_current_model():
    table = mm.load_pricing(Path(mm.__file__).with_name("pricing.json"))
    datetime.strptime(table["checked"], "%Y-%m-%d")
    assert set(table["models"]["claude-opus-5-5"]) == {
        "input", "output", "cache_read", "cache_write_5m", "cache_write_1h"}


@pytest.mark.parametrize("rate, text", [(4.0, "$4"), (0.2, "$0.20"), (3.75, "$3.75")])
def test_rates_are_written_like_a_price_list(rate, text):
    assert mm.rate(rate) == text


def test_the_window_is_shown_in_utc_whatever_zone_it_was_given_in(tmp_path):
    # merge.sh passes the branch's reflog time, which is in the maintainer's local zone.
    local = timezone(timedelta(hours=-5))
    logs = write_log(tmp_path, response("2026-10-27T11:00:00Z", input_tokens=1))
    block = mm.usage_block(mm.sum_usage(logs, START, END), PRICING,
                           START.astimezone(local), END.astimezone(local))
    assert "- Window: 2026-10-27 10:00 → 2026-10-27 12:00 UTC" in block
