"""Tests that every tool in the dev container comes from a pin Dependabot can update (issue #10).

Dependabot updates `FROM image:tag@sha256:digest` lines, but not a version and checksum in a download
URL. So gitleaks comes from its official image, in a stage of its own, rather than a release download.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTAINERFILE = (ROOT / "Containerfile").read_text()
FROM = re.compile(r"^FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?\s*$", re.M | re.I)
PINNED = re.compile(r"^(?P<image>[^:@\s]+):(?P<tag>[^@\s]+)@sha256:[0-9a-f]{64}$")


def stages():
    """Each FROM line's image and stage name, in order."""
    return [m.groups() for m in FROM.finditer(CONTAINERFILE)]


def test_every_image_is_pinned_by_tag_and_digest():
    # The digest fixes the bytes; the tag tells Dependabot (and readers) which version it is. A digest
    # alone gets no version updates, and a tag alone can change under us.
    # Only a stage declared *earlier* can be referred to; `FROM alpine AS alpine` still pulls an image.
    earlier = set()
    for image, name in stages():
        if image not in earlier:
            assert PINNED.match(image), f"not pinned by tag and digest: {image}"
        if name:
            earlier.add(name)


def gitleaks_stage():
    found = [(image, name) for image, name in stages() if image.startswith("ghcr.io/gitleaks/gitleaks:")]
    assert len(found) == 1, f"expected one ghcr.io/gitleaks/gitleaks stage, found {stages()}"
    return found[0]


def test_gitleaks_comes_from_its_official_image():
    _, name = gitleaks_stage()
    assert name, "the gitleaks stage needs a name to copy from"
    assert re.search(rf"^COPY\s+--from={re.escape(name)}\s+/usr/bin/gitleaks\s+/usr/local/bin/gitleaks\s*$",
                     CONTAINERFILE, re.M), "gitleaks isn't copied from its stage"


def test_nothing_is_downloaded_by_version_in_the_containerfile():
    # A version in a download URL (and its checksum) is a pin nothing updates.
    assert "releases/download" not in CONTAINERFILE
    assert not re.search(r"^(ARG|ENV)\s+\w*_VERSION", CONTAINERFILE, re.M)
    assert not re.search(r"\b(curl|wget|urlretrieve)\b", CONTAINERFILE), "the Containerfile downloads something"


def test_the_installed_gitleaks_is_the_version_the_image_tag_names():
    # The tests run in the dev container, so this is the gitleaks the hook and CI use.
    image, _ = gitleaks_stage()
    assert PINNED.match(image), f"not pinned by tag and digest: {image}"
    tag = PINNED.match(image)["tag"]
    result = subprocess.run(["gitleaks", "version"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == tag, f"gitleaks {result.stdout.strip()}, image tag {tag}"
