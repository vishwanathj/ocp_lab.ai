# Lessons learned: building with AI

What worked and what went wrong while building this project with an AI coding assistant (Claude Code),
so others can skip the same mistakes. Useful whether or not you use AI tools yourself.

## How to add a lesson

Add a row to the [Log](#log) in the same pull request where the lesson happened, newest first:
the date, what happened and the lesson in one or two sentences, and its theme. When a lesson proves true
more than once, move it into one of the themed sections.

## Verifying AI output

- **Check claims against the installed tool.** Official docs listed a sanity test that ansible-core 2.21 no
  longer runs; `ansible-test sanity --list-tests` settled it in seconds.
- **Treat AI recall as a draft.** A list of documentation macros produced from memory missed five of them;
  reading the official page found the gaps.
- **Read primary sources in full, pinned to a version.** Reading the docs' source files at a fixed commit was
  faster and repeatable when the docs website rate-limited requests.
- **Ask for evidence, not a claim of success.** "Done" comes with test output, a command result or a listing.
- **Measure before writing it down.** A PR description stated a file's line count before it was measured, and
  it was wrong.

## Working style and process

- **Ask for small steps.** A first commit of 35 files works, but nobody can learn from it or review it.
- **Do it by hand, then automate it.** Skills and generators written before the work encode guesses.
- **State methodology and constraints before the first file.** "Use TDD" and "containers only" both arrived
  after work had started, and earlier work had to be redone.
- **Plan before multi-file changes with trade-offs.** Small fixes don't need a plan.
- **Keep work in tracked issues with acceptance criteria.** Follow-ups get recorded, not fixed on the side.

## Guardrails and review

- **Turn important rules into checks.** Rulesets, required forms and secret scanning hold even when someone forgets.
- **Make checks fail loudly.** A check that silently passes when it couldn't run creates false confidence.
- **Review AI work independently.** An automated reviewer caught that the AI author had changed an acceptance
  criterion on its own and duplicated rules it claimed not to duplicate.
- **Keep one source of truth.** Rules live in `CONTRIBUTING.md`; `CLAUDE.md` imports it instead of copying.
- **Put team rules in CI, not in one person's editor**, so they apply with or without AI tools.

## Security and environment

- **Never paste real secrets into an AI chat.** Session logs are stored locally.
- **Deny AI tools access to credential files and to bypasses** such as `git commit --no-verify`.
- **Check your git identity before publishing.** Unconfigured git used a laptop hostname as the author email.
- **Inspect what you publish.** A test build showed a release would ship development-only files.
- **Verify a plugin's publisher.** An IDE marketplace showed a look-alike plugin above the real one.
- **Check version requirements first.** An IDE integration failed silently on a years-old IDE release.

## Log

| Date | What happened → lesson | Theme |
|---|---|---|
| 2026-10-07 | The AI wrote "21 lines" in a PR description before measuring; the file had 18. Measure first, then write. | Verification |
| 2026-10-07 | CodeRabbit flagged that the AI changed an acceptance criterion without approval and repeated rules it said it wouldn't. Independent review catches AI drift. | Review |
| 2026-10-07 | An anonymous check of the "New issue" page was inconclusive; looking as a signed-in user settled it. Verify the way a real user would. | Verification |
| 2026-10-03 | Lessons were scattered across chat; a log was started. Capture lessons the day they happen. | Process |
| 2026-10-03 | Planned skills and hooks to come after the work is done by hand once, not first. | Process |
| 2026-10-02 | IDE integration kept "installing" with no effect: the IDE was from 2018. Check version requirements first. | Environment |
| 2026-10-02 | A test build showed a release would ship `CLAUDE.md`, task lists and git hooks. Inspect what you publish. | Security |
| 2026-10-02 | Docs listed a sanity test the installed ansible-core no longer runs. Verify against the installed tool. | Verification |
| 2026-10-01 | Reading 12 official doc pages in full revealed six rules the generated code broke. Use primary sources, not memory. | Verification |
| 2026-10-01 | A stop-hook passed silently while the container engine was down. Guardrails must fail loudly. | Guardrails |
| 2026-10-01 | Git identity was unset; commits carried the laptop's hostname email. Check before the first push. | Security |
| 2026-10-01 | TDD was requested after code existed, so the first tests came after the code. State methodology up front. | Process |
| 2026-10-01 | A local install was interrupted by "containers only". State constraints before the first command. | Process |
| 2026-10-01 | The first commit was 35 files: fine for a tool, unreadable as a tutorial. Ask for small steps. | Process |
