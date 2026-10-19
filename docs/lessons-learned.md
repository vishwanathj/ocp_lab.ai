# Lessons learned

Surprises, mistakes and their fixes while building this collection, so others can skip them.
Covers code, process and working with AI tools; AI-related entries are tagged `AI`.
Lessons are recorded the day they happen, in the same pull request.

**Decisions vs. lessons:** a choice between options is recorded as an ADR in `docs/adr/`.
A surprise — something that went wrong or turned out differently than expected — goes here.

## Principles

The short version. Each links to the entries it came from.

**Verification**
- Confirm a test's setup worked before trusting its result; script the setup — [L3](#l3).
- Read what a check did, not just its color; "skipped" can show as green — [L4](#l4).

**Process**
- Never assume a pull request's number; look it up, or refer to it by its issue — [L1](#l1).
- Describe what exists; mark anything else as planned, with a link to its issue — [L2](#l2).

**Status of an entry:** `Recorded` means written down; its prevention is planned or accepted as a risk.
`Guarded` means something now enforces it (a check, test, ruleset, template or documented rule), linked in
the entry. A lesson that happens twice must become `Guarded`.

## Entries

Newest first. Use the template in [CONTRIBUTING.md](../CONTRIBUTING.md#lessons-learned).

### <a id="l4"></a>L4 · 2026-10-19: A green check meant "skipped", not "passed"
**Tags:** Verification · Review · AI — **Status:** Guarded ([CONTRIBUTING](../CONTRIBUTING.md#merging) rule; automated check planned in [#9](https://github.com/vishwanathj/ocp_lab.ai/issues/9))
- **Issue:** Before merging [#24](https://github.com/vishwanathj/ocp_lab.ai/pull/24), the CodeRabbit check on the last commit was green, which looked like a clean review. Its description said "Review skipped: manual review required for this OSS repository": CodeRabbit had confirmed one fix in a comment thread, but hadn't reviewed the commit as a whole.
- **Why it stayed hidden:** GitHub shows the check's color first; the description is only visible when you open it. A skipped review and a clean review look the same in the list of checks.
- **Resolution:** Noticed while reading the check's details before merging. The maintainer accepted the in-thread confirmation, and the squash commit says the review was skipped.
- **Prevention:** now — CONTRIBUTING says to read a check's description, not just its color, and to ask for a skipped review with `@coderabbitai review`. Planned — `make merge` ([#9](https://github.com/vishwanathj/ocp_lab.ai/issues/9)) will refuse to merge while the CodeRabbit status description says "skipped", unless told otherwise.
- **Lesson:** A green check only means the check didn't fail. Before trusting it, read what it actually did.

### <a id="l3"></a>L3 · 2026-10-14: A check passed although its setup step had failed
**Tags:** Verification · AI — **Status:** Guarded ([`make clean`](../Makefile))
- **Issue:** While testing [#6](https://github.com/vishwanathj/ocp_lab.ai/issues/6), the step "remove the image, then rerun `make test`" was run with a mistyped removal command (`podman rmi -q`, a flag that doesn't exist). The removal failed, the old image stayed, and `make test` passed, so it looked as if the rebuild had been tested.
- **Why it stayed hidden:** the removal error scrolled past, and the result that mattered (`1 passed`) looked right. Nothing checked that the image was gone before the rerun.
- **Resolution:** Noticed the error and the remaining image count, removed the images properly, and confirmed the rebuild.
- **Prevention:** `make clean` removes the images, prints how many are left and fails unless none are, so the setup step is one tested command that reports its own result instead of a hand-typed one.
- **Lesson:** When a test step has a setup ("remove X, then check Y"), confirm the setup worked before trusting the check, and prefer a `make` target over a hand-typed command.

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
