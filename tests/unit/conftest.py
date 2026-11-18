import sys
from pathlib import Path

# The merge tools live in tools/, not in a package; make them importable from the tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
