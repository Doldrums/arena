"""A separate, bounded prompt-only candidate process; never a grader import."""
from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import resource
import sys

MAX_PROMPT_BYTES = 4096


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 ** 2, 512 * 1024 ** 2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    if hasattr(resource, "RLIMIT_NPROC"):
        resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
    try:
        with open(os.devnull, "w") as sink:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                spec = importlib.util.spec_from_file_location("lmx_prompt_candidate", sys.argv[1])
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                value = module.candidate()
        if type(value) is not str or len(value.encode("utf-8")) > MAX_PROMPT_BYTES:
            raise ValueError("candidate() must return a string of at most 4096 UTF-8 bytes")
        message = {"prompt": value}
    except BaseException as exc:
        message = {"error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    os.write(1, json.dumps(message, ensure_ascii=True).encode())
    return 0 if "prompt" in message else 1


if __name__ == "__main__":
    raise SystemExit(main())
