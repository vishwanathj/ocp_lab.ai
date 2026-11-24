# Every target runs its tools inside the dev container (see Containerfile).
# Prerequisites on the host: podman (or docker), make and git.

ENGINE ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)
# Checked only by targets that use the container, so `make setup` and `make help` work without one.
need-engine = $(if $(ENGINE),,$(error Neither podman nor docker was found. Install one of them; see CONTRIBUTING.md))

# The tag is a hash of the files that define the image, so changing either one triggers a rebuild.
IMAGE_TAG  := $(shell cat Containerfile requirements-dev.txt | git hash-object --stdin | cut -c1-12)
IMAGE_NAME := localhost/ocp-lab-ai-dev
IMAGE      := $(IMAGE_NAME):$(IMAGE_TAG)

# Source is mounted read-only: tests must not change the working tree. RUN_OPTS adds options for one target.
RUN = $(ENGINE) run --rm $(RUN_OPTS) -v "$(CURDIR)":/work:ro,Z $(IMAGE)

.PHONY: help setup image test secrets secrets-staged clean merge

# Claude Code session logs, read (read-only) to compute the AI usage block at merge.
CLAUDE_LOGS ?= $(HOME)/.claude/projects

help: ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-15s %s\n", $$1, $$2}'

# Runs on the host and only changes this clone's git config: no container needed (issue #8).
setup: ## Turn on the git hooks in .githooks/ (once, after cloning)
	git config core.hooksPath .githooks

image: ## Build the dev container if it is missing or out of date
	@$(need-engine)$(ENGINE) image inspect $(IMAGE) >/dev/null 2>&1 || $(ENGINE) build -t $(IMAGE) -f Containerfile .

test: image ## Run the unit tests in the dev container
	$(RUN) python -m pytest -p no:cacheprovider tests/unit

secrets: image ## Scan every commit for secrets (CI runs this)
	$(RUN) tools/scan_secrets.sh /work

# GIT_INDEX: the index to scan, as the container sees it; the pre-commit hook passes it (issue #8).
secrets-staged: RUN_OPTS = $(if $(GIT_INDEX),-e GIT_INDEX_FILE=$(GIT_INDEX))
secrets-staged: image ## Scan what is staged for the next commit (the pre-commit hook runs this)
	@$(RUN) tools/scan_secrets.sh --staged /work

# Maintainers only; needs the GitHub CLI on the host. Options: PR=N (must match the branch's PR),
# DRY_RUN=1 (print the message, merge nothing), ALLOW_SKIPPED_REVIEW=1 (merge although CodeRabbit didn't review).
merge: image ## Squash-merge this branch's PR with its AI usage (maintainers; needs gh)
	@ENGINE="$(ENGINE)" IMAGE="$(IMAGE)" CLAUDE_LOGS="$(CLAUDE_LOGS)" PR="$(PR)" DRY_RUN="$(DRY_RUN)" \
	  ALLOW_SKIPPED_REVIEW="$(ALLOW_SKIPPED_REVIEW)" tools/merge.sh

# Fails if an image could not be removed, so a failed clean is never mistaken for a clean one.
clean: ## Remove every dev container image; the next target rebuilds it
	@$(need-engine)ids=$$($(ENGINE) images -q $(IMAGE_NAME)); \
	if [ -n "$$ids" ]; then $(ENGINE) rmi -f $$ids >/dev/null || exit 1; fi; \
	left=$$($(ENGINE) images -q $(IMAGE_NAME) | wc -l | tr -d ' '); \
	echo "dev images left: $$left"; \
	[ "$$left" -eq 0 ]
