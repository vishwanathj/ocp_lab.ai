# Lessons learned

Surprises, mistakes and their fixes while building this collection, so others can skip them.
Covers code, process and working with AI tools; AI-related entries are tagged `AI`.
Lessons are recorded the day they happen, in the same pull request.

**Decisions vs. lessons:** a choice between options is recorded as an ADR in `docs/adr/`.
A surprise — something that went wrong or turned out differently than expected — goes here.

## Principles

The short version. Each links to the entries it came from.

**Process**
- Never assume a pull request's number; look it up, or refer to it by its issue — [L1](#l1).
- Describe what exists; mark anything else as planned, with a link to its issue — [L2](#l2).

**Status of an entry:** `Recorded` means written down; its prevention is planned or accepted as a risk.
`Guarded` means something now enforces it (a check, test, ruleset, template or documented rule), linked in
the entry. A lesson that happens twice must become `Guarded`.

## Entries

Newest first. Use the template in [CONTRIBUTING.md](../CONTRIBUTING.md#lessons-learned).

### <a id="l2"></a>L2 · 2026-10-07: Documentation described a planned feature as if it existed
**Tags:** Process · AI — **Status:** Recorded (accepted risk for now)
- **Issue:** L1's prevention said `make merge` "looks up" the pull request, but `make merge` doesn't exist yet ([#9](https://github.com/vishwanathj/ocp_lab.ai/issues/9)); the line was written by the AI in [#22](https://github.com/vishwanathj/ocp_lab.ai/pull/22).
- **Why it stayed hidden:** the plan was clear in the writer's head, and nothing compares documentation claims with the code.
- **Resolution:** CodeRabbit flagged it; the entry now separates what is in place from what is planned.
- **Prevention:** accepted risk for now — automated review checks claims against the code. If it happens again, add a PR-template checklist item: "Docs describe only what exists; planned work is marked as planned."
- **Lesson:** Write documentation in the tense of reality: describe what exists, and label anything else as planned, with a link to its issue.

### <a id="l1"></a>L1 · 2026-10-07: Issues and pull requests share one number sequence
**Tags:** Process · AI — **Status:** Guarded ([CONTRIBUTING](../CONTRIBUTING.md#branches-and-commits) rule; automated lookup planned in [#9](https://github.com/vishwanathj/ocp_lab.ai/issues/9))
- **Issue:** The plan called the first pull request "PR #1", but GitHub numbered it [#2](https://github.com/vishwanathj/ocp_lab.ai/pull/2) because issue #1 already had that number.
- **Why it stayed hidden:** issue and pull request numbers look like separate counters, and nothing checked the number before it was used.
- **Resolution:** Referred to the pull request by its real number, #2.
- **Prevention:** now — CONTRIBUTING says to refer to "the PR for issue #N" until the PR exists. Planned — `make merge` ([#9](https://github.com/vishwanathj/ocp_lab.ai/issues/9)) will look up the pull request from the branch instead of taking an assumed number.
- **Lesson:** Never assume a pull request's number. Look it up, or refer to it by its issue.
