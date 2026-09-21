"""Run the released LMX symbolic-regression loop with its required output dir."""
from pathlib import Path
import runpy
import sys


def main(argv=None):
    Path("results").mkdir(exist_ok=True)
    entrypoint = Path.cwd() / "scripts/symbolic_regression.py"
    sys.argv = [str(entrypoint), *(sys.argv[1:] if argv is None else argv)]
    runpy.run_path(str(entrypoint), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
