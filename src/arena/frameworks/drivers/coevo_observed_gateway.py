"""Versioned CoEvo provider driver with observational native-save sidecars."""
from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

from . import cpu_program_gateway
from .coevo_history import observe_native_saves


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if any(arg == "--engine" or arg.startswith("--engine=") for arg in args):
        raise ValueError("This versioned driver selects only CoEvo")
    native_runpy = cpu_program_gateway.runpy

    def observed_run_path(path, **kwargs):
        # The unchanged provider driver reaches this point only after verifying
        # TLS/cache and establishing its offline environment.
        with observe_native_saves(Path.cwd()):
            return native_runpy.run_path(path, **kwargs)

    cpu_program_gateway.runpy = SimpleNamespace(run_path=observed_run_path,
                                               run_module=native_runpy.run_module)
    try: return cpu_program_gateway.main(["--engine", "coevo", *args])
    finally: cpu_program_gateway.runpy = native_runpy


if __name__ == "__main__": main()
