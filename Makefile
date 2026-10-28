# Every target runs its tools inside the dev container (see Containerfile).
# Prerequisites on the host: podman (or docker), make and git.

ENGINE ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)
ifeq ($(ENGINE),)
$(error Neither podman nor docker was found. Install one of them; see CONTRIBUTING.md)
endif

# The tag is a hash of the files that define the image, so changing either one triggers a rebuild.
IMAGE_TAG  := $(shell cat Containerfile requirements-dev.txt | git hash-object --stdin | cut -c1-12)
IMAGE_NAME := localhost/ocp-lab-ai-dev
IMAGE      := $(IMAGE_NAME):$(IMAGE_TAG)

# Source is mounted read-only: tests must not change the working tree.
RUN := $(ENGINE) run --rm -v "$(CURDIR)":/work:ro,Z $(IMAGE)

.PHONY: help image test clean merge

# Claude Code session logs, read (read-only) to compute the AI usage block at merge.
CLAUDE_LOGS ?= $(HOME)/.claude/projects

help: ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

image: ## Build the dev container if it is missing or out of date
	@$(ENGINE) image inspect $(IMAGE) >/dev/null 2>&1 || $(ENGINE) build -t $(IMAGE) -f Containerfile .

test: image ## Run the unit tests in the dev container
	$(RUN) python -m pytest -p no:cacheprovider tests/unit

# Maintainers only; needs the GitHub CLI on the host. Options: PR=N (must match the branch's PR),
# DRY_RUN=1 (print the message, merge nothing), ALLOW_SKIPPED_REVIEW=1 (merge although CodeRabbit didn't review).
merge: image ## Squash-merge this branch's PR with its AI usage (maintainers; needs gh)
	@ENGINE="$(ENGINE)" IMAGE="$(IMAGE)" CLAUDE_LOGS="$(CLAUDE_LOGS)" PR="$(PR)" DRY_RUN="$(DRY_RUN)" \
	  ALLOW_SKIPPED_REVIEW="$(ALLOW_SKIPPED_REVIEW)" tools/merge.sh

# Fails if an image could not be removed, so a failed clean is never mistaken for a clean one.
clean: ## Remove every dev container image; the next target rebuilds it
	@ids=$$($(ENGINE) images -q $(IMAGE_NAME)); \
	if [ -n "$$ids" ]; then $(ENGINE) rmi -f $$ids >/dev/null || exit 1; fi; \
	left=$$($(ENGINE) images -q $(IMAGE_NAME) | wc -l | tr -d ' '); \
	echo "dev images left: $$left"; \
	[ "$$left" -eq 0 ]
