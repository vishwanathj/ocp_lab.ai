"""Builds the squash commit message and AI usage comment for `make merge` (issue #9).

Runs in the dev container and never talks to GitHub: tools/merge.sh fetches the pull request and its
checks on the host and passes them in as files.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

FIELDS = ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h")


@dataclass
class Usage:
    models: dict = field(default_factory=dict)  # model -> {field: tokens}
    responses: int = 0
    latest: datetime | None = None  # newest entry in any log, inside the window or not


def load_pricing(path):
    return json.loads(Path(path).read_text())


def _time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def sum_usage(log_dir, start, end):
    """Sum Claude Code usage from session logs between start and end, counting each response once."""
    usage, seen = Usage(), set()
    for path in sorted(Path(log_dir).glob("**/*.jsonl")):
        for line in path.open(errors="ignore"):
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            message = entry.get("message") or {}
            tokens, model = message.get("usage"), message.get("model")
            if entry.get("type") != "assistant" or not tokens or not model or not entry.get("timestamp"):
                continue
            when = _time(entry["timestamp"])
            usage.latest = max(usage.latest or when, when)
            key = (message.get("id"), entry.get("requestId"))
            if not start <= when <= end or key in seen:
                continue
            seen.add(key)
            usage.responses += 1
            split = tokens.get("cache_creation") or {}
            if split:
                write_5m = split.get("ephemeral_5m_input_tokens") or 0
                write_1h = split.get("ephemeral_1h_input_tokens") or 0
            else:  # older logs don't split cache writes; count them at the 5-minute rate
                write_5m, write_1h = tokens.get("cache_creation_input_tokens") or 0, 0
            totals = usage.models.setdefault(model, dict.fromkeys(FIELDS, 0))
            totals["input"] += tokens.get("input_tokens") or 0
            totals["output"] += tokens.get("output_tokens") or 0
            totals["cache_read"] += tokens.get("cache_read_input_tokens") or 0
            totals["cache_write_5m"] += write_5m
            totals["cache_write_1h"] += write_1h
    return usage


def rate(value):
    """A per-MTok rate as a price list writes it: $4, $0.20, $3.75."""
    return f"${value:g}" if value == int(value) else f"${value:.2f}"


def usage_block(usage, pricing, start, end):
    if not usage.responses:
        return "AI usage: none reported"
    total = dict.fromkeys(FIELDS, 0)
    for tokens in usage.models.values():
        for name in FIELDS:
            total[name] += tokens[name]
    priced = sorted(m for m in usage.models if m in pricing["models"])
    unpriced = sorted(m for m in usage.models if m not in pricing["models"])
    cost = sum(usage.models[m][f] * pricing["models"][m][f] / 1e6 for m in priced for f in FIELDS)
    rates = "; ".join(
        f"{m}: {rate(r['input'])} in / {rate(r['output'])} out / {rate(r['cache_read'])} cache read"
        f" / {rate(r['cache_write_5m'])} & {rate(r['cache_write_1h'])} cache write per MTok"
        for m in priced for r in [pricing["models"][m]]
    )
    lines = [
        "AI usage (Claude Code) — estimate",
        f"- Window: {start:%Y-%m-%d %H:%M} → {end:%Y-%m-%d %H:%M} UTC (branch created → merge)",
        f"- Model: {', '.join(sorted(usage.models))} · {usage.responses} responses",
        f"- Tokens: input {total['input']:,} · output {total['output']:,} · cache read {total['cache_read']:,}"
        f" · cache write 1h {total['cache_write_1h']:,} · cache write 5m {total['cache_write_5m']:,}",
        f"- Estimated cost: ${cost:.2f} at API list prices ({rates}, checked {pricing['checked']});"
        " billed via subscription, not per token",
    ]
    if unpriced:
        lines.append(f"- Unpriced models: {', '.join(unpriced)} (not included in the cost)")
    if usage.latest:
        lines.append(f"- Log lag at merge: {(end - usage.latest).total_seconds():.0f} s,"
                     " so the last response or two may be missing")
    lines.append("- Not measured: CodeRabbit review; work before the branch existed")
    return "\n".join(lines)


@dataclass
class Decision:
    ok: bool
    reason: str = ""
    review_note: str | None = None  # goes into the squash message when a skipped review was accepted


# CodeRabbit reports a review it didn't run as success or neutral, with one of these in its text (L4).
NOT_REVIEWED = ("skip", "rate limit", "paused")


def _coderabbit(head):
    """(conclusion, text) for each CodeRabbit result on the head commit, from check runs and statuses."""
    results = [(r.get("conclusion"), (r.get("output") or {}).get("title") or "")
               for r in head.get("check_runs", []) if r.get("name") == "CodeRabbit"]
    results += [(s.get("state"), s.get("description") or "")
                for s in head.get("statuses", []) if s.get("context") == "CodeRabbit"]
    return results


def merge_decision(required_checks, head, allow_skipped_review):
    """Refuse on any required check that didn't pass (no override), or on a review that didn't run."""
    if not required_checks:
        return Decision(False, "no required checks found on the pull request; refusing to merge")
    failing = [f"{c['name']} ({c['bucket']})" for c in required_checks if c.get("bucket") != "pass"]
    if failing:
        return Decision(False, "required checks did not pass: " + ", ".join(failing)
                        + ". There is no override for a failing check.")
    results = _coderabbit(head)
    if any(state == "success" and not any(w in text.lower() for w in NOT_REVIEWED) for state, text in results):
        return Decision(True)
    said = "; ".join(text or state for state, text in results) or "no CodeRabbit check"
    if allow_skipped_review:
        return Decision(True, review_note=f"Review: CodeRabbit didn't review the last commit ({said});"
                                          " merged with ALLOW_SKIPPED_REVIEW=1.")
    return Decision(False, f"CodeRabbit didn't review the last commit ({said}). Comment"
                           " `@coderabbitai review` and wait, or rerun with ALLOW_SKIPPED_REVIEW=1.")


CO_AUTHORS = {"claude-opus-5-5": "Claude Opus 5.5"}


def _section(body, heading):
    """The text under `## heading` in a PR description, without the template's <!-- --> hints."""
    match = re.search(rf"^## {heading}[ \t]*\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    text = re.sub(r"<!--.*?-->", "", match.group(1), flags=re.S).strip() if match else ""
    if not text:
        raise ValueError(f"the PR description has no ## {heading} section, or it is empty")
    return text


def commit_message(pr, block, models, review_note, signoff):
    """(subject, body) for the squash commit: summary, test evidence, review note, Closes, usage block, trailers."""
    body = pr.get("body") or ""
    closes = re.findall(r"^\s*((?:closes|fixes|resolves) #\d+)", body, re.I | re.M)
    if not closes:
        raise ValueError("the PR description has no 'Closes #N' line")
    parts = [_section(body, "Summary"), "Tested:\n" + _section(body, "Test evidence")] + ([review_note] if review_note else []) + ["\n".join(closes), block]
    trailers = [signoff] + [f"Co-Authored-By: {CO_AUTHORS.get(m, m)} <noreply@anthropic.com>"
                            for m in sorted(models)]
    return f"{pr['title']} (#{pr['number']})", "\n\n".join(parts + ["\n".join(trailers)])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pr", "checks", "head", "logs", "start", "now", "signoff"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--pricing", default=str(Path(__file__).with_name("pricing.json")))
    parser.add_argument("--allow-skipped-review", choices=("", "1"), default="",
                        help="1 merges although CodeRabbit didn't review the last commit")
    parser.add_argument("--format", choices=("json", "nul"), default="json",
                        help="nul: subject, message and comment, each ending in a NUL byte, for tools/merge.sh")
    args = parser.parse_args(argv)
    read = lambda path: json.loads(Path(path).read_text())
    pr = read(args.pr)
    decision = merge_decision(read(args.checks), read(args.head), args.allow_skipped_review == "1")
    if not decision.ok:
        print(f"make merge: refusing to merge PR #{pr['number']}: {decision.reason}", file=sys.stderr)
        return 1
    start, now = _time(args.start), _time(args.now)
    usage = sum_usage(args.logs, start, now)
    block = usage_block(usage, load_pricing(args.pricing), start, now)
    try:
        subject, message = commit_message(pr, block, list(usage.models), decision.review_note, args.signoff)
    except ValueError as error:
        print(f"make merge: refusing to merge PR #{pr['number']}: {error}", file=sys.stderr)
        return 1
    if args.format == "nul":
        sys.stdout.write(f"{subject}\0{message}\0{block}\0")
    else:
        print(json.dumps({"subject": subject, "message": message, "comment": block}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
