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
- A test that expects a failure must check why it failed; with built-in rules, check your own rule fired — [L11](#l11).
- A fake must be as limited as what it replaces; run the real thing once. A check that couldn't look must say so — [L12](#l12).
- Before writing tests, list every form the input takes and every way the tool skips; review the tests before approval — [L13](#l13).
- A setting a tool accepts isn't a setting it applies; check where it says so (source, logs, a real run) — [L14](#l14).
- A tool's exit code says what it decided, not whether it saw everything; read its log for errors too — [L15](#l15).

**Process**
- Never assume a pull request's number; look it up, or refer to it by its issue — [L1](#l1).
- Describe what exists; mark anything else as planned, with a link to its issue — [L2](#l2).
- Test an automation once with a real item before relying on it; "on" isn't "working" — [L5](#l5).
- Don't rely on an AI tool's defaults for hard-to-undo actions; write down a rule the tool enforces — [L6](#l6).
- A step that is done every time but written nowhere will be skipped; write it where the doer reads it — [L7](#l7).
- Before making a shared document, find the one that exists and update it; never start a second — [L10](#l10).

**Status of an entry:** `Recorded` means written down; its prevention is planned or accepted as a risk.
`Guarded` means something now enforces it (a check, test, ruleset, template or documented rule), linked in
the entry. A lesson that happens twice must become `Guarded`.

## Entries

Newest first. Use the template in [CONTRIBUTING.md](../CONTRIBUTING.md#lessons-learned).

### <a id="l15"></a>L15 · 2026-11-28: gitleaks said "no leaks found" whenever git complained
**Tags:** Verification · Security · AI — **Status:** Guarded ([test_secret_scan.py](../tests/unit/test_secret_scan.py), [test_pre_commit_hook.py](../tests/unit/test_pre_commit_hook.py): every git problem tested must make the scan exit 2, "scan cannot run")
- **Issue:** Researching [#34](https://github.com/vishwanathj/ocp_lab.ai/issues/34) found that when git writes anything to its error output while gitleaks reads the changes, gitleaks logs an `ERR` line, stops reading, reports "no leaks found" and exits 0. A mistake in `.gitattributes`, a bad config value, an unreadable file, a broken `core.fsmonitor` hook or a missing object was enough: the pre-commit hook, `make secrets` and CI's required check all passed with a fake token in the change ([#42](https://github.com/vishwanathj/ocp_lab.ai/issues/42)). This is [L12](#l12)'s lesson again: a check that couldn't look said "all clear".
- **Why it stayed hidden:** L12's fix checks that git can read the repository *before* the scan. Nobody asked what happens when git works but complains *during* it. gitleaks does print git's message, but above "no leaks found" and a green check, and the tests looked only at exit codes and findings.
- **Resolution:** `tools/scan_secrets.sh` keeps gitleaks' log and exits 2, "scan cannot run", on any `ERR` line, so git's message is shown and the commit or CI check fails. `--platform none` and `core.fsmonitor=false` avoid two `ERR`s that don't mean anything went unread. Found while researching #34 and checked by an independent agent; the tests were reviewed twice by an agent and once by CodeRabbit before approval.
- **Prevention:** the tests above (Guarded), including guards against false failures. Git stopping with no message at all, and shallow clones, are documented limits in [CONTRIBUTING.md](../CONTRIBUTING.md#secrets).
- **Lesson:** a tool's exit code says what it decided, not whether it saw everything. Read its log for errors too, and test what it does when the source it reads from complains.

### <a id="l14"></a>L14 · 2026-11-27: Dependabot features apply to only some of our pins
**Tags:** Verification · Review · AI — **Status:** Guarded ([CONTRIBUTING.md: Roles](../CONTRIBUTING.md#roles): the Reviewer asks for a link to the tool's own docs or source whenever a change says what a tool covers)
- **Issue:** In [#10](https://github.com/vishwanathj/ocp_lab.ai/issues/10), `.github/dependabot.yml` sets a 7-day cooldown for the container images, and a test checks it's there. Dependabot accepts it, but applies it only to Docker Hub images; for gitleaks on `ghcr.io` it logs "skipping cooldown" and proposes new releases at once.
  - **A second case, in the same PR:** Dependabot security updates were switched on, and the docs said every pin would get them. Only pip does. Dependabot has no security updates for container images, and GitHub raises no alerts for Actions pinned by SHA. An independent reviewer found the error for images, fixed in [9e5c112](https://github.com/vishwanathj/ocp_lab.ai/commit/9e5c112). That fix still said Actions get them; CodeRabbit found it, fixed in [655eace](https://github.com/vishwanathj/ocp_lab.ai/commit/655eace).
- **Why it stayed hidden:** the setting is valid, the documentation lists cooldown for the docker ecosystem, and the test of the config passes. Nothing that a test or a reader of the config sees says it's ignored. The second claim was written from the feature's name, "security updates", and no test reads prose.
- **Resolution:** an independent reviewer found it in Dependabot's source before the test review ([`update_checker.rb`](https://github.com/dependabot/dependabot-core/blob/main/docker/lib/dependabot/docker/update_checker.rb)). The product owner accepted the cooldown limit; the acceptance criterion and CONTRIBUTING say so. For the second case, the reviewers checked GitHub's [supported ecosystems table](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories) and its [Dependabot alerts docs](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-alerts).
- **Prevention:** a test of the config can't see what Dependabot skips, and the second case was in prose, so the guard is a review step: the Reviewer role in [CONTRIBUTING.md](../CONTRIBUTING.md#roles) asks for a link to the tool's own docs or source whenever a change says what a tool covers. CONTRIBUTING's [Writing the tests first](../CONTRIBUTING.md#writing-the-tests-first) also asks to read how a tool decides to skip, which is how the first case was found. Both limits are documented in [Dependabot pull requests](../CONTRIBUTING.md#dependabot-pull-requests), and Dependabot PRs are still reviewed before merging.
- **Lesson:** a test of a config proves the setting is written, not that the tool honours it. For a setting that matters, find where the tool applies it: its source, its logs, or a real run. For a claim about what a tool covers, link its docs or source.

### <a id="l13"></a>L13 · 2026-11-27: Reviewers kept finding inputs the tests had never tried
**Tags:** Verification · Review · AI — **Status:** Guarded ([CONTRIBUTING.md: Writing the tests first](../CONTRIBUTING.md#writing-the-tests-first))
- **Issue:** In [#8](https://github.com/vishwanathj/ocp_lab.ai/issues/8), after the tests were approved, reviewers found three inputs the scan missed. A pull secret inside a JSON string, the way the assisted-service API carries it. The same string escaped twice, as a recorded response stores it. And files git treats as binary, whose changes gitleaks skips. Each needed another Red commit and another approval.
- **Why it stayed hidden:** the tests were written for the shapes the author had in mind: a pull secret saved as a file. Nobody listed the shapes the project's own API produces, or read gitleaks' source for when it skips input. The independent reviews came after the tests were approved, and the author's own second look shared the first one's assumptions.
- **Resolution:** a read-only reviewer agent and CodeRabbit found the gaps; new Red tests cover all three, and the fixes land in the same pull request.
- **Prevention:** CONTRIBUTING's [Writing the tests first](../CONTRIBUTING.md#writing-the-tests-first): list the input's forms, read how the tool skips, and review the tests before approving them.
- **Lesson:** test the input as it really arrives, not as you picture it. Ask for an independent review while the tests can still change, not after they're approved.

### <a id="l12"></a>L12 · 2026-11-24: Every test passed, but the real hook let a token through, twice
**Tags:** Verification · Security · AI — **Status:** Guarded (the fake engine refuses what a container can't see; the scan refuses what it can't read: [test_pre_commit_hook.py](../tests/unit/test_pre_commit_hook.py), [test_secret_scan.py](../tests/unit/test_secret_scan.py))
- **Issue:** In [#8](https://github.com/vishwanathj/ocp_lab.ai/issues/8), with all tests green, the real hook let a token through with `git commit -a`: git names that commit's temporary index in `GIT_INDEX_FILE`, which the container never received. CodeRabbit then found that when git can't read the repository or index, gitleaks reports "no leaks" and exits 0, so the hook failed *open*.
- **Why it stayed hidden:** the tests' fake container passed the whole host environment and could open any host path, so it saw what a real container can't. And no test asked what the scan does when it sees nothing.
- **Resolution:** the fake engine now starts from an empty environment and refuses host paths outside the mount; the hook passes the index as a `/work` path; the scanner checks that git can read before scanning and otherwise says "scan cannot run". The real hook was run in a scratch clone before and after.
- **Prevention:** the tests above (Guarded); for anything that runs in a container, run the real thing once before calling it done.
- **Lesson:** a fake must be as limited as what it replaces, where it matters. A safety check must say when it couldn't look, never "all clear".

### <a id="l11"></a>L11 · 2026-11-22: Tests for the project's secret rules would have passed with no rules at all
**Tags:** Verification · Review · AI — **Status:** Guarded (the tests check which rule fired: [test_secret_scan.py](../tests/unit/test_secret_scan.py))
- **Issue:** The first Red tests for [#8](https://github.com/vishwanathj/ocp_lab.ai/issues/8) checked only that a fake offline token and pull secret were "blocked". The fake token is a JWT, which gitleaks' built-in rules already catch, so the tests would pass with an empty `.gitleaks.toml`. A crash or a bad config would have passed as "blocked" too.
- **Why it stayed hidden:** every test failed in the Red run, as it should, and the assertions read as right. Nothing asked *why* a scan would fail once the code existed.
- **Resolution:** a read-only reviewer agent and CodeRabbit found it before the test review. Blocked tests now check the rule ID or the reason in the output, and new tests cover the index vs. the working tree, a clean history and the repository's own history.
- **Prevention:** the tests themselves (Guarded); the review question "could this pass for the wrong reason?" is now part of the test review.
- **Lesson:** a "rejected" test must check why it was rejected. When a tool has built-in behavior, test that *your* part fired.

### <a id="l10"></a>L10 · 2026-11-21: A second progress deck was made because nobody checked for the first
**Tags:** Process · AI — **Status:** Guarded ([CLAUDE.md](../CLAUDE.md) rule: one deck, updated in place)
- **Issue:** Asked for presentation material for [#21](https://github.com/vishwanathj/ocp_lab.ai/issues/21), Claude built a new hosted deck. One already existed from 27 October, with 12 slides. The two had to be merged by hand into the October deck.
- **Why it stayed hidden:** the October deck wasn't linked from anything in the repository, and the issue didn't mention it. Claude's own notes recorded it, but it didn't check them before creating a new one.
- **Resolution:** The new deck's content went into the October deck, which is now the only one. The duplicate was deleted.
- **Prevention:** CLAUDE.md says there is one progress deck, kept by the product owner, to be updated in place and never recreated. The deck's version history keeps every earlier version of its slides.
- **Lesson:** Before making a document others will read, look for the one that already exists and update it. A second copy splits the material and one of them goes stale.

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
