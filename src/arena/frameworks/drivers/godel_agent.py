"""Supply the native credential-file interface for an explicit Gödel Agent run.

No source import, environment read or file write occurs on importing this module.
The ephemeral file is private and excluded from every recipe result pattern.
"""
import os
from pathlib import Path
import runpy
import signal
import sys


def main(argv=None):
    if (sys.argv[1:] if argv is None else argv):
        raise ValueError("This pinned Gödel Agent entrypoint accepts no CLI arguments")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY must be explicitly provided in the native environment")
    root = Path.cwd()
    path = root / "src/key.env"
    if not (root / "src/main.py").is_file():
        raise ValueError("The native Gödel Agent entrypoint is missing")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    previous = {}
    original_path = list(sys.path)

    def interrupted(signum, _frame):
        raise SystemExit(128 + signum)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(key)
            stream.flush()
            os.fsync(stream.fileno())
        del key
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous[signum] = signal.signal(signum, interrupted)
        sys.path.insert(0, str(root / "src"))
        runpy.run_path(str(root / "src/main.py"), run_name="__main__")
    finally:
        sys.path[:] = original_path
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
