"""A common, evidence-aware interface to autoresearch evaluation tasks."""
__version__ = "0.6.0"

from pathlib import Path
import sys

_library_helpers = str(Path(__file__).resolve().parents[2] / "suite" / "_lib")
if _library_helpers not in sys.path:
    sys.path.insert(0, _library_helpers)
