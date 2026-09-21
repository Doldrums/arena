#!/usr/bin/env python3
"""Run Arena's bundled task library without consuming installed bytecode caches."""
import os
from pathlib import Path
import sys
import tempfile


def main():
    # pip compiles bundled Python files at installation. Always import the
    # reviewed source, including in evaluator subprocesses, from a fresh prefix.
    with tempfile.TemporaryDirectory(prefix="arena-task-bytecode-") as cache:
        sys.dont_write_bytecode = True
        sys.pycache_prefix = cache
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        os.environ["PYTHONPYCACHEPREFIX"] = cache
        sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
        from autoresearch_tasks.cli import main as run
        return run()


if __name__ == "__main__":
    raise SystemExit(main())
