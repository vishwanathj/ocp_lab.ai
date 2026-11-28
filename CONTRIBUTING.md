# Contributing to ocp_lab.ai

Thanks for helping! This page explains how work flows through this repository.
You don't need any particular editor or AI tool. Everything here works with plain `git` and a browser.

## How work flows

Every change follows the same path:

1. **Issue** — open one with the **Task** or **Bug report** form. Planned work is grouped into
   milestones (`M01`, `M02`, …) and tracked on the [project board](https://github.com/users/vishwanathj/projects/2).
   Every new open issue is added to the board automatically, however it was created; check that it
   shows up there.
2. **Kickoff comment** — when you start work, comment on the issue with four lines (see [Starting work](#starting-work)).
3. **Feature branch** — create a branch from `main` named after the issue.
4. **Pull request** — open a PR against `main`. The PR template asks for a summary, test evidence and a checklist.
5. **Merge** — once reviewed, the PR is squashed into one commit on `main`, and the issue closes.

Nothing is pushed straight to `main`; the repository's ruleset blocks it.

### Starting work

Issues are often written weeks before someone picks them up, and things change in between. Before the
first commit, comment on the issue:

```markdown
**Kickoff**
- **Assumptions:** what you're taking as given
- **Dependencies:** issues or PRs this needs, and whether they're merged
- **Open decisions:** anything the product owner still has to decide
- **Changes to acceptance criteria:** what you propose to add, drop or change
```

"None" is a fine answer. If every line is "none", start. Otherwise the product owner answers in the
issue before work starts, and any agreed change to the acceptance criteria is edited into the issue.

### Writing the tests first

Tests are written from the acceptance criteria before the code, and fail until the code exists. Gaps
found after that cost another round of review, so before writing them:

- **List every form the input really takes,** not just the obvious one. A pull secret can be a file, a
  string inside JSON, that string escaped again, YAML or base64. Write a test for each.
- **Read how the tool you rely on decides to skip.** Check its documentation or source for input it
  ignores, and for cases where it finds nothing and still reports success. Test each one.
- **Get the tests reviewed before they're approved:** CodeRabbit, plus a second person or an independent
  agent. Ask them whether any test could pass for the wrong reason, and what input it doesn't cover.

## Setting up

You need three things on your machine: **podman** (or docker), **make** and **git**.
Nothing else is installed on your machine; every tool runs inside the project's dev container.

**After cloning, run `make setup` once.** It turns on the project's git hooks, including the one that
scans every commit for secrets (see [Secrets](#secrets)). Git never runs a repository's hooks on its
own, so a cloned project can't run code on your machine without your say-so; this is that say-so.

| Command | What it does |
|---|---|
| `make setup` | Turns on the git hooks in `.githooks/`; run once after cloning (no container needed) |
| `make test` | Runs the unit tests in the dev container, building the container first if needed |
| `make secrets` | Scans every commit for secrets, as CI does |
| `make clean` | Removes the dev container images; the next `make test` rebuilds them |
| `make merge` | Maintainers only: squash-merges the current branch's PR (see [Merging](#merging)) |
| `make help` | Lists every target |

- The first `make test` downloads the base image and builds the container, which takes a minute.
  Later runs reuse it. Editing `Containerfile` or `requirements-dev.txt` rebuilds it automatically.
- `make` uses podman if it is installed, otherwise docker. To choose one: `make test ENGINE=docker`.
- Your checkout is mounted **read-only** inside the container, so tests can't change your files.

## Branches and commits

- **Branch name:** `<issue-number>-<short-slug>`, for example `3-contributing-guide`.
- **Small commits:** one logical change per commit, with a message that says what and why.
- **Sign off every commit:** `git commit -s`. This adds a `Signed-off-by:` line, which certifies that
  you wrote the change or have the right to submit it under the project's license — the
  [Developer Certificate of Origin](https://developercertificate.org/) used by Ansible's own projects.
- **Link the issue:** put `Closes #<number>` in the PR description.
- **Pull request numbers:** issues and pull requests share one number sequence, so don't predict a PR's
  number. Until it exists, refer to it as "the PR for issue #N".

## Roles

Roles are hats, not people. One person may wear several; as more contributors join, they can take some over.
The rule that matters: **work is checked by a different hat from the one that produced it.**

| Role | Responsible for |
|---|---|
| Product owner | Why and what: milestone goals, priorities, acceptance criteria, accepting finished work |
| Developer | Building the change on a feature branch |
| Tester | Turning acceptance criteria into tests before the work starts, and verifying the result |
| Reviewer | Reviewing pull requests independently of the author, and asking for a link to the tool's own docs or source whenever a change says what a tool covers |
| Security | Secrets handling, token flows, `no_log`, dependency updates |
| Docs | README, primers, tutorial notes |
| Release | Versions, tags and release notes |

Each role is described in more detail when it is first needed in the project.

## Merging

- `main` requires a pull request with **1 approval**, resolved review comments, linear history
  (squash merges only, so the failing Red commits of a PR never reach `main`) and two green checks,
  **`make test`** and **`make secrets`**.
- **CI:** [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs `make test` in the same dev container
  on every pull request and every push to `main`, and `make secrets` in a job of its own. If they pass on
  your machine, they should pass in CI.
- **Solo-maintainer rule:** GitHub doesn't allow approving your own pull request. While the project has
  one maintainer, that maintainer may merge their own PRs with an admin override — only after
  self-reviewing against the PR template's checklist, and **only when CI is green**. The override
  replaces the missing approval, never a failing check. When a second maintainer joins, every PR gets
  a real approval; [#31](https://github.com/vishwanathj/ocp_lab.ai/issues/31) lists what else changes.
- **Read a check, not just its color.** A green check can mean "skipped": CodeRabbit marks a review it
  didn't run as a success, with the description "Review skipped…". A skipped review isn't a review; ask
  for one by commenting `@coderabbitai review`.
- **`make merge`** does the merge, run on the PR's branch. It needs the GitHub CLI (`gh`) on your machine,
  which is the only tool that runs outside the container, so no GitHub token ever enters one. It:
  - finds the PR from the branch (`PR=N` is only a cross-check) and refuses if your branch isn't its
    head commit, or if someone else opened the PR (the usage block comes from your own logs);
  - refuses while a required check hasn't passed (there is no override for that), and while CodeRabbit
    didn't review the last commit, unless you give `ALLOW_SKIPPED_REVIEW=1`, which the message records;
  - writes the squash message from the PR's **Summary**, its **Test evidence** (as "Tested:"), its `Closes #`
    line, the AI usage block and your sign-off, merges with the admin override, and posts the usage block
    as a PR comment. If the comment fails, it exits with an error and prints the block for you to post.

  Try `make merge DRY_RUN=1` first: it prints the message and merges nothing.

### Dependabot pull requests

[Dependabot](.github/dependabot.yml) keeps every pin up to date: the GitHub Actions, the dev container's
images (the Python base and gitleaks) and the packages in `requirements-dev.txt`. Each week it opens at most
one pull request per kind, labelled `type/security` and `area/ci`. For the Python packages, a fix for a
known vulnerability also comes as soon as it's published, in a pull request of its own, without waiting for
the week.

To review and merge one:
- **CI must pass:** both required checks run the new pin, so a broken update can't merge.
- **Read the changelog** Dependabot links in the PR, for anything that changes behavior or needs a change here.
- **Approve it and merge it on GitHub** with the squash button. Dependabot opened the PR, so a maintainer's
  approval is a real one, with no admin override. `make merge` refuses PRs someone else opened, and there's
  no AI usage to record.

Known limits:
- New releases wait 7 days before Dependabot proposes them (the **cooldown**), so a broken one has time to be
  pulled. Dependabot only does this for Docker Hub images, so gitleaks updates (from `ghcr.io`) don't wait.
- The base image stays on **Python 3.12**: Dependabot brings rebuilds of `3.12-slim`, not `3.13-slim`. Moving
  to a new Python is an issue of its own.
- Only the Python packages get those immediate security updates. Dependabot has none for **container
  images**, and none for **GitHub Actions pinned by commit SHA**, as ours are (it only alerts on Actions
  referenced by version). Their fixes arrive with the weekly update, after the cooldown where it applies.
- If the weekly image PRs stop bringing rebuilds of `3.12-slim`, check that Dependabot still proposes
  digest-only updates; a change on its side could stop them without any error.
- CodeRabbit may skip bot PRs. Green CI plus reading the changelog is the review for these.

## Definition of done

A change is done when:

- the issue's acceptance criteria are all met
- tests were written or updated first and pass (or the PR explains why none are needed)
- CI is green
- docs are updated where behavior changed
- the PR checklist is complete and the change is merged

A milestone is done when all its issues are done and the **progress deck** has its slide: the
milestone's goal, a demo and its main lesson. The product owner keeps the deck and shares it by link;
it is rebuilt from GitHub (milestones, issues, the lessons log and each merge's AI usage block), so
it holds nothing that isn't already here. A PDF export of the deck is attached to the milestone's release
(`m02` onward), so each milestone's slides are kept with the repository.

This list grows as the project gains tests, CI and release tooling.

## AI tools

AI tools are optional. A PR merged with `make merge` records an **AI usage** block in its squash
commit: token counts and an estimated cost at API list prices, or "AI usage: none reported". The counts
come from every Claude Code session on the merger's machine while the branch existed, not only this
branch's. The same rules apply to every change, however it was written.

If you use Claude Code, [CLAUDE.md](CLAUDE.md) imports this page and adds a few Claude-specific notes.
Lessons about working with AI tools go in the project's [lessons log](#lessons-learned), tagged `AI`.

## Lessons learned

When something surprising happens — a bug that slipped through, a check that misled you, a step that had
to be redone — add an entry to [docs/lessons-learned.md](docs/lessons-learned.md) **in the same pull request**,
newest first. Decisions between options belong in an ADR instead.

Add an entry only if it would **change how someone works on this repository**. Personal or one-machine
issues (an old editor, a local setup quirk) belong in your own notes. Most pull requests won't need one.

```markdown
### <a id="lN"></a>LN · YYYY-MM-DD: <what happened, in a few words>
**Tags:** <Verification | Process | Guardrails | Review | Security | Environment | Code> [· AI] — **Status:** Recorded
- **Issue:** what went wrong, with links to the issue or PR
- **Why it stayed hidden:** why nothing caught it earlier
- **Resolution:** what fixed this occurrence
- **Prevention:** what stops it from happening again — a guard (link it), an issue that will add one (link it),
  or "accepted risk" with a one-line reason
- **Lesson:** the rule to follow next time, in one or two sentences
```

- **IDs are permanent:** a new entry takes the highest existing number + 1. Never renumber; removed entries leave a gap.
- **Every entry needs a prevention action.** When the guard exists, set the status to `Guarded` and link it.
  **A lesson that happens twice must become `Guarded`.** Each milestone's retrospective reviews the `Recorded`
  entries and checks their prevention issues are scheduled.

## Secrets

This project talks to an API that needs Red Hat credentials. **Never** put tokens, pull secrets,
passwords or internal hostnames in code, tests, examples, issues, PRs or commit messages.
Read them from the environment instead, e.g. `offline_token: "{{ lookup('env', 'OFFLINE_TOKEN') }}"`.

Three checks back this up:

1. **The pre-commit hook** (after `make setup`) scans what you're about to commit with
   [gitleaks](https://github.com/gitleaks/gitleaks), in the dev container, using its built-in rules and
   ours in [`.gitleaks.toml`](.gitleaks.toml) (offline tokens and pull secrets). A secret blocks the commit.
2. **CI's `make secrets`** scans every commit of the pull request's history, merge commits included,
   because deleting a secret in a later commit doesn't unpublish it.
3. **GitHub push protection** rejects pushes containing well-known token formats.

**"commit blocked"** means one of two things, and the lines above it say which:
- **A secret was found.** gitleaks prints the file, line and rule, with the secret itself hidden. Remove it
  and commit again. If it's a false positive, end that line with `# gitleaks:allow` and say why in the PR.
- **The scan couldn't run.** podman isn't working; git couldn't read the repository; git reported a
  problem while the changes were read, such as a mistake in `.gitattributes` (git's message is shown
  after `[git]`); or gitleaks itself failed, or didn't report that it finished. The hook *fails closed*:
  it blocks rather than guess. Fix the cause and commit again. CI's `make secrets` fails the same way.

`git commit --no-verify` skips the hook. Use it only when you must (for example, podman is broken and
the change is urgent); CI scans the commit anyway, but by then it has been pushed. If a secret was
ever pushed, treat it as leaked: revoke it, then remove it.

**Without podman or docker**, the hook blocks every commit, because it can't scan; install one (see
[Setting up](#setting-up)). CI still scans your pull request.

**If a secret reaches GitHub**, on any branch, every pull request's scan fails until it's dealt with:
revoke the secret first, then ask a maintainer to remove it from the history or list it in a
`.gitleaksignore` file.

Known limits:
- The hook refuses in a **git worktree**, whose git data is outside what the container can see; use a
  normal clone.
- Only `git commit` runs the hook. `--amend` scans only the new changes, and merges, `cherry-pick`,
  `rebase`, `revert` and `git am` aren't scanned locally; CI scans all of them.
- A branch created before the hook existed has no `.githooks/`, so git runs no hook there, silently.
  Rebase it on `main`.
- The hook doesn't see inside files git treats as binary (marked in `.gitattributes`, or containing a
  NUL byte); CI does. Neither reads UTF-16 files, which some Windows tools write.
- If git stops without a message (killed for lack of memory, say), the scan can't tell that it read
  only part of the changes. And a shallow clone (`git clone --depth`) has no older commits for
  `make secrets` to scan; CI fetches the whole history.
- gitleaks' built-in rules skip some paths without saying so: images, PDFs and other binary formats,
  `.gitleaks.toml` itself, and Python virtual environments such as `venv/`. Don't keep
  credentials in such files either.
- The first commit after `Containerfile` or `requirements-dev.txt` changes rebuilds the dev container
  inside the hook, which takes a few minutes.

Found a security problem? Report it [privately](https://github.com/vishwanathj/ocp_lab.ai/security/advisories/new),
not as a public issue.
