"""Run the independent Arena board with python -m arena."""

from __future__ import annotations

import argparse
from pathlib import Path

from .server import serve


def main(argv=None):
    parser = argparse.ArgumentParser(description="Arena catalog and live experiment board (read-only)")
    parser.add_argument("--root", action="append", type=Path,
                        help="Watch a run directory or directory of runs; repeat for multiple roots")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args(argv)
    roots = args.root or [Path("outputs"), Path("autoresearch")]
    serve(roots, port=args.port)


if __name__ == "__main__":
    main()
