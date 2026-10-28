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
5. **Merge** — once reviewed, the PR is squashed (or rebased) into `main`, and the issue closes.

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

## Setting up

You need three things on your machine: **podman** (or docker), **make** and **git**.
Nothing else is installed on your machine; every tool runs inside the project's dev container.

| Command | What it does |
|---|---|
| `make test` | Runs the unit tests in the dev container, building the container first if needed |
| `make clean` | Removes the dev container images; the next `make test` rebuilds them |
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
| Reviewer | Reviewing pull requests independently of the author |
| Security | Secrets handling, token flows, `no_log`, dependency updates |
| Docs | README, primers, tutorial notes |
| Release | Versions, tags and release notes |

Each role is described in more detail when it is first needed in the project.

## Merging

- `main` requires a pull request with **1 approval**, resolved review comments, linear history
  (squash or rebase merges only; merge commits are disabled) and a green **`make test`** check.
- **CI:** [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs `make test` in the same dev container
  on every pull request and every push to `main`. If it passes on your machine, it should pass in CI.
- **Solo-maintainer rule:** GitHub doesn't allow approving your own pull request. While the project has
  one maintainer, that maintainer may merge their own PRs with an admin override — only after
  self-reviewing against the PR template's checklist, and **only when CI is green**. The override
  replaces the missing approval, never a failing check. When a second maintainer joins, every PR gets
  a real approval.
- **Read a check, not just its color.** A green check can mean "skipped": CodeRabbit marks a review it
  didn't run as a success, with the description "Review skipped…". A skipped review isn't a review; ask
  for one by commenting `@coderabbitai review`.
- Squash commit messages keep the PR's summary, the `Closes #` line and the sign-off.

## Definition of done

A change is done when:

- the issue's acceptance criteria are all met
- tests were written or updated first and pass (or the PR explains why none are needed)
- CI is green
- docs are updated where behavior changed
- the PR checklist is complete and the change is merged

This list grows as the project gains tests, CI and release tooling.

## AI tools

AI tools are optional. If a pull request was built with an AI assistant, its squash commit records an
**AI usage** block: token counts and an estimated cost at API list prices. PRs built without AI simply
have no such block. The same rules apply to every change, however it was written.

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
GitHub push protection is enabled and will reject pushes containing known token formats.

Found a security problem? Report it [privately](https://github.com/vishwanathj/ocp_lab.ai/security/advisories/new),
not as a public issue.
