"""Read-only journal compatibility extracted from sciel.engine.runtime.

SCiEL source commit: 0d67f813dd4ac21dee304f2b0de0b0ce59bf4157.
Only dependency-reachable validators/readers/constants are retained.
"""
from __future__ import annotations

import os


from pathlib import Path


import socket


import subprocess


def process_identity(pid):
    """Return an OS process-start token, or None if it cannot be established."""
    if type(pid) is not int or pid <= 0:
        return None
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        fields = stat.rsplit(")", 1)[1].split()
        if fields[0] in {"Z", "X"}:
            return None
        return {"kind": "proc_start_ticks", "value": fields[19]}
    except (OSError, IndexError):
        pass
    try:
        result = subprocess.run(["ps", "-o", "lstart=", "-o", "stat=", "-p", str(pid)],
                                capture_output=True, text=True, timeout=1, check=False)
        fields = result.stdout.split()
        if result.returncode == 0 and len(fields) >= 6 and not fields[-1].startswith(("Z", "X")):
            return {"kind": "ps_lstart", "value": " ".join(fields[:-1])}
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def process_matches(record):
    """True=the same live local process; False=dead/different; None=unverified."""
    if not isinstance(record, dict) or record.get("hostname") != socket.gethostname():
        return None
    pid, expected = record.get("pid"), record.get("process_identity")
    if type(pid) is not int or pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return None
    except OSError:
        return None
    if not isinstance(expected, dict) or not expected.get("value"):
        return None
    actual = process_identity(pid)
    return actual == expected if actual is not None else None
