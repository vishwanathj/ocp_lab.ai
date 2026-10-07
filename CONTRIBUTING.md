# Contributing to ocp_lab.ai

Thanks for helping! This page explains how work flows through this repository.
You don't need any particular editor or AI tool. Everything here works with plain `git` and a browser.

## How work flows

Every change follows the same path:

1. **Issue** — open one with the **Task** or **Bug report** form. Planned work is grouped into
   milestones (`M01`, `M02`, …) and tracked on the [project board](https://github.com/users/vishwanathj/projects/2).
2. **Feature branch** — create a branch from `main` named after the issue.
3. **Pull request** — open a PR against `main`. The PR template asks for a summary, test evidence and a checklist.
4. **Merge** — once reviewed, the PR is squashed (or rebased) into `main`, and the issue closes.

Nothing is pushed straight to `main`; the repository's ruleset blocks it.

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

- `main` requires a pull request with **1 approval**, resolved review comments and linear history
  (squash or rebase merges only; merge commits are disabled).
- **Solo-maintainer rule:** GitHub doesn't allow approving your own pull request. While the project has
  one maintainer, that maintainer may merge their own PRs with an admin override — only after
  self-reviewing against the PR template's checklist, and only when all checks pass. When a second
  maintainer joins, every PR gets a real approval.
- Squash commit messages keep the PR's summary, the `Closes #` line and the sign-off.

## Definition of done

A change is done when:

- the issue's acceptance criteria are all met
- tests were written or updated first and pass (or the PR explains why none are needed)
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
