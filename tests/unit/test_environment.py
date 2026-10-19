"""Walking-skeleton test: proves `make test` runs pytest in the pinned container."""

import sys


def test_runs_on_pinned_python():
    # The Containerfile pins Python 3.12; any other version means the tests ran outside it.
    assert sys.version_info[:2] == (3, 12)
