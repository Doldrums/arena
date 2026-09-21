"""Stable control-service API and ``python -m arena.control`` entry point.

HTTP serving and imports do not launch participant code. Workers execute only
explicitly admitted run templates inside their delegated containment boundary.
"""
from .control_cli import main
from .control_config import validate_config
from .control_http import dispatch_http
from .control_io import _read_regular
from .control_process import RunCgroup, _pid_alive
from .control_service import ControlService
from .control_types import ControlError, SECRET_VALUE, _decode
from .control_worker import Worker

__all__ = ["ControlError", "ControlService", "RunCgroup", "Worker",
           "dispatch_http", "main", "validate_config"]


if __name__ == "__main__":
    raise SystemExit(main())
