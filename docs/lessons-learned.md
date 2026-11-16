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
- When a convention depends on a setting, check the setting allows nothing else — [L9](#l9).
- Map every acceptance criterion to a test before any code; "no test needed" is the reviewer's call — [L8](#l8).

**Process**
- Never assume a pull request's number; look it up, or refer to it by its issue — [L1](#l1).
- Describe what exists; mark anything else as planned, with a link to its issue — [L2](#l2).
- Test an automation once with a real item before relying on it; "on" isn't "working" — [L5](#l5).
- Don't rely on an AI tool's defaults for hard-to-undo actions; write down a rule the tool enforces — [L6](#l6).
- A step that is done every time but written nowhere will be skipped; write it where the doer reads it — [L7](#l7).

**Status of an entry:** `Recorded` means written down; its prevention is planned or accepted as a risk.
`Guarded` means something now enforces it (a check, test, ruleset, template or documented rule), linked in
the entry. A lesson that happens twice must become `Guarded`.

## Entries

Newest first. Use the template in [CONTRIBUTING.md](../CONTRIBUTING.md#lessons-learned).

### <a id="l9"></a>L9 · 2026-11-16: Rebase merges were allowed, so a PR's failing commits could land on `main`
**Tags:** Process · Guardrails — **Status:** Guarded (repository setting and the `main` ruleset allow squash only)
- **Issue:** Asked whether a maintainer could merge from GitHub's PR page instead of `make merge`, the maintainer and Claude read the `main` ruleset: it allowed squash **and rebase** merges, and so did the repository setting. A tests-first PR has `Red:` commits that fail on purpose; [#30](https://github.com/vishwanathj/ocp_lab.ai/pull/30) has eight. A rebase merge from the button would have put all 17 commits on `main`.
- **Why it stayed hidden:** every merge so far was a squash (`gh pr merge --squash`), so the other allowed method was never used. Rebase was allowed when linear history was set up, before PRs had failing commits by design.
- **Resolution:** The repository setting and the ruleset now allow squash merges only; CONTRIBUTING says so.
- **Prevention:** The setting itself: GitHub refuses any other merge method, from the button, `gh` or the API. A check that each commit on `main` came from `make merge` is proposed separately.
- **Lesson:** A convention ("we always squash") is only as safe as the settings behind it. When a new practice relies on one, check the settings allow nothing else.

### <a id="l8"></a>L8 · 2026-11-16: The test review found untested safety checks, and approved tests that disagreed
**Tags:** Testing · Process · AI — **Status:** Recorded (prevention planned in [#20](https://github.com/vishwanathj/ocp_lab.ai/issues/20))
- **Issue:** When [#30](https://github.com/vishwanathj/ocp_lab.ai/pull/30) was rebuilt tests-first, laying [#9](https://github.com/vishwanathj/ocp_lab.ai/issues/9)'s acceptance criteria next to the tests showed four criteria covered only by `tools/merge.sh`, which had no tests. One of them was the PR lookup that is [L1](#l1)'s prevention. Claude's review guide had also said a test covered the PR-number check when none did. Later, a new `merge.sh` test expected a "Tested:" section that the approved message test didn't, so two approved tests contradicted each other.
- **Why it stayed hidden:** the earlier version of the PR had a Red/Green pair per behavior, so each pair looked complete, and nobody compared the criteria with the tests. A "Why no Red" note made the gap look like a decision. The contradiction spanned two test files reviewed separately.
- **Resolution:** Added 11 tests for `merge.sh`, with fake `gh` and engine scripts and git in the dev image. The Red that changed approved tests went through a second review: the `tests-approved` label was removed and added back.
- **Prevention:** The stage-1 test review starts from a table with one row per acceptance criterion and the test that covers it. The tests-first rule and its CI check are planned in [#20](https://github.com/vishwanathj/ocp_lab.ai/issues/20).
- **Lesson:** Review tests against the acceptance criteria, one row per criterion, before any code is written. Whether something needs no test is for the reviewer to accept, not for the author to decide.

### <a id="l7"></a>L7 · 2026-10-27: The AI usage comment was skipped at a merge
**Tags:** Process · AI — **Status:** Guarded ([`make merge`](../tools/merge.sh) posts the comment)
- **Issue:** Every merge from [#2](https://github.com/vishwanathj/ocp_lab.ai/pull/2) to [#25](https://github.com/vishwanathj/ocp_lab.ai/pull/25#issuecomment-6282640477) posted the AI usage block as a PR comment. At the merge of [#29](https://github.com/vishwanathj/ocp_lab.ai/pull/29), Claude put the block in the squash commit but didn't post the comment; the maintainer noticed and it was posted afterward.
- **Why it stayed hidden:** the comment was a habit, not a rule. CLAUDE.md and CONTRIBUTING only required the block in the squash commit, and the comment was mentioned only in #9's acceptance criteria, for a target that doesn't exist yet. The conversation's earlier context had been summarized, and the habit didn't survive it.
- **Resolution:** Posted the block on #29.
- **Prevention:** `make merge` ([#9](https://github.com/vishwanathj/ocp_lab.ai/issues/9)) posts the block as a PR comment and fails loudly if it can't; CLAUDE.md says to merge with `make merge`.
- **Lesson:** A step that is done every time but written nowhere will eventually be skipped. Write it where the person or tool doing the step will read it, then automate it.

### <a id="l6"></a>L6 · 2026-10-27: What the AI could post to GitHub was decided only by the AI
**Tags:** Process · Guardrails · AI — **Status:** Guarded ([`.claude/settings.json`](../.claude/settings.json), checked by [a test](../tests/unit/test_claude_settings.py))
- **Issue:** Asked whether Claude had to confirm before commenting on an issue, nobody could point to a rule. Claude had been asking before outward-facing actions out of its own default; nothing in the repository said which actions need the maintainer's yes ([#28](https://github.com/vishwanathj/ocp_lab.ai/issues/28)).
- **Why it stayed hidden:** the default was cautious, so nothing went wrong. A different session, model or tool could have behaved differently.
- **Resolution:** Decided which actions need confirmation and wrote it down.
- **Prevention:** `.claude/settings.json` makes Claude Code ask before merges, tags, closing or deleting issues, releases, repository edits and writing `gh api` calls; a unit test checks the rules; CLAUDE.md explains them.
- **Lesson:** Don't rely on an AI tool's own defaults for actions that are hard to undo. Write the rule down where the tool enforces it.

### <a id="l5"></a>L5 · 2026-10-19: The board's auto-add filter had never matched anything
**Tags:** Process · Guardrails · AI — **Status:** Guarded (board filter fixed; [CONTRIBUTING](../CONTRIBUTING.md#how-work-flows) rule)
- **Issue:** [#26](https://github.com/vishwanathj/ocp_lab.ai/issues/26) was created with `gh issue create` without `--project` and never reached the board, although the board's "Auto-add to project" workflow was on. Its filter was `is:issue,pr is:open label:bug`, GitHub's suggested starting filter, and this repository has no `bug` label (it uses `type/bug`). So auto-add had never added a single item.
- **Why it stayed hidden:** every earlier issue reached the board another way: the issue forms (their `projects:` setting) or `--project`. The workflow showed as "on", and its filter can't be read through the API, only in the board's settings.
- **Resolution:** Added #26 to the board by hand. The maintainer changed the filter to `is:issue is:open`; a throwaway issue created without `--project` then appeared on the board within seconds, and was deleted (number #27 is a gap).
- **Prevention:** the filter is fixed and was tested as above. CONTRIBUTING says to check that a new issue shows up on the board.
- **Lesson:** "Turned on" doesn't mean "working". Test an automation once with a real item before relying on it.

### <a id="l4"></a>L4 · 2026-10-19: A green check meant "skipped", not "passed"
**Tags:** Verification · Review · AI — **Status:** Guarded ([CONTRIBUTING](../CONTRIBUTING.md#merging) rule; checked by [`make merge`](../tools/merge_message.py))
- **Issue:** Before merging [#24](https://github.com/vishwanathj/ocp_lab.ai/pull/24), the CodeRabbit check on the last commit was green, which looked like a clean review. Its description said "Review skipped: manual review required for this OSS repository": CodeRabbit had confirmed one fix in a comment thread, but hadn't reviewed the commit as a whole.
- **Why it stayed hidden:** GitHub shows the check's color first; the description is only visible when you open it. A skipped review and a clean review look the same in the list of checks.
- **Resolution:** Noticed while reading the check's details before merging. The maintainer accepted the in-thread confirmation, and the squash commit says the review was skipped.
- **Prevention:** CONTRIBUTING says to read a check's description, not just its color, and to ask for a skipped review with `@coderabbitai review`. `make merge` ([#9](https://github.com/vishwanathj/ocp_lab.ai/issues/9)) refuses while CodeRabbit didn't review the last commit (skipped or rate limited), unless `ALLOW_SKIPPED_REVIEW=1` is given.
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
**Tags:** Process · AI — **Status:** Guarded ([CONTRIBUTING](../CONTRIBUTING.md#branches-and-commits) rule; [`make merge`](../tools/merge.sh) looks the PR up)
- **Issue:** The plan called the first pull request "PR #1", but GitHub numbered it [#2](https://github.com/vishwanathj/ocp_lab.ai/pull/2) because issue #1 already had that number.
- **Why it stayed hidden:** issue and pull request numbers look like separate counters, and nothing checked the number before it was used.
- **Resolution:** Referred to the pull request by its real number, #2.
- **Prevention:** CONTRIBUTING says to refer to "the PR for issue #N" until the PR exists, and `make merge` ([#9](https://github.com/vishwanathj/ocp_lab.ai/issues/9)) looks up the pull request from the branch instead of taking an assumed number.
- **Lesson:** Never assume a pull request's number. Look it up, or refer to it by its issue.
