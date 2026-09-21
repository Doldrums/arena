"""Bridge environment credentials to ProTeGi's unmodified native search loop."""
import os
from pathlib import Path
import runpy
import sys
from types import ModuleType


def main(argv=None):
    config = ModuleType("config")
    config.OPENAI_KEY = os.environ["OPENAI_API_KEY"]
    sys.modules["config"] = config
    entrypoint = Path.cwd() / "main.py"
    sys.path.insert(0, str(Path.cwd()))
    sys.argv = [str(entrypoint), *(sys.argv[1:] if argv is None else argv)]
    runpy.run_path(str(entrypoint), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
