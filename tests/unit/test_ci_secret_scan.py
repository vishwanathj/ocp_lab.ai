"""Tests that CI scans the full history for secrets (issue #8).

The workflow is read as text: the dev container has no YAML library, and these checks only need
to find two settings.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text()


def test_ci_checks_out_the_full_history():
    # The default checkout is one commit deep; a scan of it would miss a token removed later.
    checkout = re.search(r"uses: actions/checkout@.*?(?=\n      - |\Z)", WORKFLOW, re.S).group()
    assert re.search(r"^\s+fetch-depth: 0$", checkout, re.M), checkout


def test_ci_runs_the_secret_scan():
    assert re.search(r"^\s+run: make secrets$", WORKFLOW, re.M)


def test_make_secrets_scans_every_commit_not_just_the_staged_changes():
    result = subprocess.run(["make", "-n", "secrets", "ENGINE=podman"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    scan = [line for line in result.stdout.splitlines() if "scan_secrets.sh" in line]
    assert scan and "--staged" not in scan[-1], result.stdout
