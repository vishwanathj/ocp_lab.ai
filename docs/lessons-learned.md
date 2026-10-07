# Lessons learned

Surprises, mistakes and their fixes while building this collection, so others can skip them.
Covers code, process and working with AI tools; AI-related entries are tagged `AI`.
The log exists because early lessons were scattered across chat history and nearly lost — so lessons are
recorded the day they happen, in the same pull request.

**Decisions vs. lessons:** a choice between options is recorded as an ADR in `docs/adr/`.
A surprise — something that went wrong or turned out differently than expected — goes here.

## Principles

The short version. Each links to the entries it came from.

**Verification**
- Check claims against the installed tool, not memory or docs — [L6](#l6), [L7](#l7).
- Measure before writing it down; ask for evidence, not a claim of success — [L11](#l11).
- When an automated check is inconclusive, verify the way a real user would — [L10](#l10).

**Process**
- Small steps, one idea per commit — [L1](#l1).
- State methodology and constraints before the first file — [L3](#l3), [L2](#l2).
- Do it by hand once, then automate it — [L9](#l9).

**Guardrails and review**
- Checks must fail loudly when they can't run — [L5](#l5).
- Review AI-written work independently — [L12](#l12).

**Security and environment**
- Check git identity before publishing — [L4](#l4).
- Inspect what you publish — [L8](#l8).

**Status of an entry:** `Recorded` means written down only. `Guarded` means something now enforces it
(a check, test, ruleset, template or documented rule), linked in the entry.
A lesson that happens twice must become `Guarded`.

## Entries

Newest first. Use the template in [CONTRIBUTING.md](../CONTRIBUTING.md#lessons-learned).

### <a id="l12"></a>L12 · 2026-10-07: The AI changed an acceptance criterion on its own
**Tags:** Review · AI — **Status:** Guarded (independent review on every PR; resolved threads required by the `Protect main` ruleset)
- **Issue:** Issue #5 asked to *record* lessons in the log; the AI changed it to "point lessons out" and also repeated rules it said it wouldn't ([#22](https://github.com/vishwanathj/ocp_lab.ai/pull/22)).
- **Why it stayed hidden:** the author's own checks verified what it built, not whether that matched the issue.
- **Resolution:** CodeRabbit flagged both; the product owner chose a public log and the duplicate rules were removed.
- **Lesson:** An author — human or AI — shouldn't be the only check on its own work. Deviations from acceptance criteria need the product owner's approval.

### <a id="l11"></a>L11 · 2026-10-07: A PR description stated a number before it was measured
**Tags:** Verification · AI — **Status:** Recorded
- **Issue:** The PR description said `CLAUDE.md` had 21 lines; it had 18 ([#22](https://github.com/vishwanathj/ocp_lab.ai/pull/22)).
- **Why it stayed hidden:** the description was written before the checks ran, and nothing compares a PR's claims with the files.
- **Resolution:** Corrected after measuring; evidence sections are now written from command output.
- **Lesson:** Write evidence after running the command, and paste its output instead of paraphrasing.

### <a id="l10"></a>L10 · 2026-10-07: An anonymous check of the issue forms was inconclusive
**Tags:** Verification — **Status:** Recorded
- **Issue:** Fetching the "New issue" page without signing in showed GitHub's sign-in page, and the API reported blank issues as enabled ([#2](https://github.com/vishwanathj/ocp_lab.ai/pull/2)).
- **Why it stayed hidden:** an automated check can be technically right but incomplete — blank issues are only enabled for maintainers.
- **Resolution:** The maintainer checked the page while signed in: both forms render, blank issues are "Maintainers only".
- **Lesson:** When an automated check is inconclusive, verify the way a real user would.

### <a id="l9"></a>L9 · 2026-10-03: Skills written before the work encode guesses
**Tags:** Process · AI — **Status:** Guarded (CLAUDE.md: skills and hooks come after the work is done by hand)
- **Issue:** In an earlier prototype, AI skills and hooks were written first and later needed corrections.
- **Why it stayed hidden:** instructions look authoritative even when nobody has followed them yet.
- **Resolution:** Skills and hooks are added only after a procedure has been done by hand at least once.
- **Lesson:** Do it by hand, then automate it.

### <a id="l8"></a>L8 · 2026-10-02: A test build would have shipped development files
**Tags:** Security — **Status:** Recorded
- **Issue:** In the prototype, the release tarball contained `CLAUDE.md`, task lists and git hooks.
- **Why it stayed hidden:** `ansible-galaxy collection build` includes every file not explicitly excluded.
- **Resolution:** Found by building and listing the tarball; to be guarded when release tooling is added.
- **Lesson:** Inspect what you publish before you publish it.

### <a id="l7"></a>L7 · 2026-10-01: Recalled details were incomplete; official docs were partly outdated
**Tags:** Verification · AI — **Status:** Recorded
- **Issue:** A list of Ansible documentation macros produced from memory missed five; official docs also listed a sanity test that ansible-core 2.21 no longer runs.
- **Why it stayed hidden:** both sources sound confident; only the installed tool is current.
- **Resolution:** Read the docs' source at a pinned commit and checked against `ansible-test sanity --list-tests`.
- **Lesson:** Treat recall and docs as drafts; the installed tool decides.

### <a id="l6"></a>L6 · 2026-10-01: Primary sources revealed rules the code broke
**Tags:** Verification · AI — **Status:** Recorded
- **Issue:** In the prototype, reading 12 official Ansible doc pages in full showed six conventions the generated code violated.
- **Why it stayed hidden:** the sanity tests don't check those conventions.
- **Resolution:** Distilled the docs into project guidance and tracked each gap as a task.
- **Lesson:** Distill primary sources before building; tools only enforce part of the rules.

### <a id="l5"></a>L5 · 2026-10-01: A check passed silently when it couldn't run
**Tags:** Guardrails · AI — **Status:** Recorded (to be guarded when CI hooks are added)
- **Issue:** In the prototype, a hook that ran tests before the AI finished passed silently while the container engine was down.
- **Why it stayed hidden:** "could not run" and "passed" looked the same.
- **Resolution:** The hook now reports that checks did not run.
- **Lesson:** Guardrails must fail loudly; an unverified result must never look like success.

### <a id="l4"></a>L4 · 2026-10-01: Commits carried a laptop hostname as the author email
**Tags:** Security — **Status:** Recorded
- **Issue:** Git had no identity configured, so it built an email from the machine's hostname.
- **Why it stayed hidden:** it is harmless locally and only visible after pushing.
- **Resolution:** Set `user.name` and `user.email` globally before the first push.
- **Lesson:** Check your git identity before publishing anything.

### <a id="l3"></a>L3 · 2026-10-01: TDD was requested after code existed
**Tags:** Process · AI — **Status:** Recorded (to be guarded by the CI test-first check, #20)
- **Issue:** In the prototype, the first tests were written after the code they tested.
- **Why it stayed hidden:** passing tests look the same whether they came first or last.
- **Resolution:** Test-first was enforced from then on.
- **Lesson:** State the methodology before the first file.

### <a id="l2"></a>L2 · 2026-10-01: A constraint arrived after work had started
**Tags:** Process · AI — **Status:** Guarded (CLAUDE.md: containers only)
- **Issue:** "Containers only, nothing installed locally" was stated while a local install was already running.
- **Why it stayed hidden:** the AI assumed a typical local setup.
- **Resolution:** The install was stopped and all tooling moved into a container.
- **Lesson:** State environment constraints before the first command.

### <a id="l1"></a>L1 · 2026-10-01: The first commit was 35 files
**Tags:** Process · AI — **Status:** Guarded (milestones sized as small sprints; one issue per PR)
- **Issue:** The prototype's first commit added about 2,800 lines at once.
- **Why it stayed hidden:** it worked, so nothing flagged its size.
- **Resolution:** This repository grows in small milestones, one issue per pull request.
- **Lesson:** Ask for small steps; a change nobody can review or learn from is a cost even when it works.
