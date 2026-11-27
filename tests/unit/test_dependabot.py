"""Tests for .github/dependabot.yml, which keeps the pinned tools up to date (issue #10).

The config is parsed as YAML, not matched as text, so a setting in the wrong entry, or in a comment,
can't pass for the right one. Each ecosystem is checked against the folder Dependabot reads: an entry
pointing at the wrong folder is valid YAML and opens no pull requests, ever.
"""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".github" / "dependabot.yml"

# What is pinned, and the file in the entry's folder that pins it. Dependabot's docker ecosystem reads
# files whose name contains "containerfile"; pip reads .txt files whose name contains "requirements".
ECOSYSTEMS = {
    "github-actions": ".github/workflows/ci.yml",
    "docker": "Containerfile",
    "pip": "requirements-dev.txt",
}


def config():
    assert CONFIG.exists(), f"{CONFIG.relative_to(ROOT)} doesn't exist"
    return yaml.safe_load(CONFIG.read_text())


def entry(ecosystem):
    found = [u for u in config().get("updates", []) if u.get("package-ecosystem") == ecosystem]
    assert len(found) == 1, f"expected one {ecosystem} entry, found {len(found)}"
    return found[0]


def test_the_config_is_version_2():
    assert config().get("version") == 2


def test_nothing_else_is_configured():
    # An entry for an ecosystem we don't use is harmless, but a typo ("github-action") is silent.
    assert sorted(u.get("package-ecosystem") for u in config()["updates"]) == sorted(ECOSYSTEMS)


@pytest.mark.parametrize("ecosystem", ECOSYSTEMS)
def test_each_ecosystem_reads_the_folder_that_holds_its_pins(ecosystem):
    directory = entry(ecosystem).get("directory")
    assert directory == "/", f"{ecosystem}: directory is {directory!r}"
    # github-actions reads .github/workflows itself when the directory is "/".
    assert (ROOT / ECOSYSTEMS[ecosystem]).exists()


@pytest.mark.parametrize("ecosystem", ECOSYSTEMS)
def test_each_ecosystem_is_checked_weekly(ecosystem):
    assert entry(ecosystem).get("schedule", {}).get("interval") == "weekly"


@pytest.mark.parametrize("ecosystem", ECOSYSTEMS)
def test_each_ecosystem_waits_seven_days_before_proposing_a_new_release(ecosystem):
    # A brand-new release that turns out broken or malicious is usually pulled within days.
    # Security updates don't wait: the cooldown applies to version updates only.
    assert entry(ecosystem).get("cooldown", {}).get("default-days") == 7


@pytest.mark.parametrize("ecosystem", ECOSYSTEMS)
def test_each_ecosystem_groups_its_updates_into_one_pull_request(ecosystem):
    groups = entry(ecosystem).get("groups", {})
    assert any(g.get("patterns") == ["*"] for g in groups.values()), groups


@pytest.mark.parametrize("ecosystem", ECOSYSTEMS)
def test_each_ecosystems_pull_requests_are_labelled_security_and_ci(ecosystem):
    assert {"type/security", "area/ci"} <= set(entry(ecosystem).get("labels", []))


def test_the_python_base_image_stays_on_its_python_version():
    # The base image tag is `3.12-slim`; Dependabot would propose `3.13-slim` as an update. Moving to a
    # new Python is a decision, not a routine update: only rebuilds of 3.12 (new digests) come through.
    ignored = [i for i in entry("docker").get("ignore", []) if i.get("dependency-name") == "library/python"]
    assert ignored, "no ignore rule for library/python"
    assert {"version-update:semver-major", "version-update:semver-minor"} <= set(ignored[0].get("update-types", []))
