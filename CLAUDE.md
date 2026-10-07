# Claude Code notes for ocp_lab.ai

@CONTRIBUTING.md

The contribution rules above apply to everyone. These notes only add what is specific to Claude Code:

- **Containers only:** run every tool through podman (docker as fallback). Never install packages on the host.
- **Merging:** the squash commit carries an "AI usage (Claude Code) — estimate" block: token counts and
  estimated cost at API list prices for the branch's window, plus what was not measured.
- **Evidence:** show command or test output before calling something done. If a check could not run,
  say so plainly instead of claiming success.
- **Secrets:** never ask for, print or store real tokens or pull secrets. Use fake values in tests.
- **Lessons:** when something surprising happens, add an entry to
  [docs/lessons-learned.md](docs/lessons-learned.md) in the same pull request (tag `AI` when relevant).

Skills and hooks are added later, once the procedures they describe have been done by hand.
