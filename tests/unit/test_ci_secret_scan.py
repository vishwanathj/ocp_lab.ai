"""Tests that CI scans the full history for secrets on every pull request (issue #8).

The workflow is read as text: the dev container has no YAML library. Each job is cut out by its
header, so the checks look at the job that runs the scan, not at another job's settings.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text()


def jobs():
    """Each job's text, by name: the lines from its two-space-indented header to the next one."""
    body = WORKFLOW.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([\w-]+):\s*$", body, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def scan_job():
    found = {name: text for name, text in jobs().items() if re.search(r"^\s+run: make secrets$", text, re.M)}
    assert len(found) == 1, f"expected one job running `make secrets`, found {list(found)}"
    return next(iter(found.values()))


def test_ci_runs_on_every_pull_request():
    trigger = re.search(r"^on:\n((?:  .*\n|\s*\n)*)", WORKFLOW, re.M)
    assert trigger and re.search(r"^  pull_request:", trigger.group(1), re.M), WORKFLOW
    # A path filter (e.g. only *.py) would skip the scan for a PR that adds a token to a YAML file.
    assert not re.search(r"^\s+(paths|paths-ignore):", trigger.group(1), re.M), trigger.group(1)


def test_the_secret_scan_is_its_own_job():
    # Its own job gives it its own check, which can be made required on main.
    assert "make test" not in scan_job()


def test_nothing_can_skip_the_scan_job():
    # `if:` (e.g. push only) would skip the scan on pull requests, and `needs:` would skip it
    # whenever the job it waits for fails; the tests above would still pass.
    job = scan_job()
    assert not re.search(r"^\s+(- )?(if|needs):", job, re.M), job


def test_the_scan_job_checks_out_the_full_history():
    # The default checkout is one commit deep; a scan of it would miss a token removed later.
    checkout = re.search(r"uses: actions/checkout@.*?(?=\n      - |\Z)", scan_job(), re.S)
    assert checkout, "the scan job has no checkout"
    assert re.search(r"^\s+fetch-depth: 0$", checkout.group(), re.M), checkout.group()


def test_make_secrets_scans_every_commit_of_the_mounted_repository():
    result = subprocess.run(["make", "-n", "secrets", "ENGINE=podman"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    scan = [line for line in result.stdout.splitlines() if "scan_secrets.sh" in line]
    assert scan, result.stdout
    assert scan[-1].rstrip().endswith("tools/scan_secrets.sh /work"), scan[-1]
