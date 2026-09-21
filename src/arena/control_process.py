"""Linux process identity and delegated cgroup containment for queued runs."""
from __future__ import annotations

import hmac
import os
from pathlib import Path
import signal
import sys
import time

from .control_io import _read_regular
from .control_types import ControlError, _decode, _id


def _pid_identity(pid):
    if sys.platform != "linux" or not pid:
        return None
    try:
        start = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        return f"{boot}:{start}"
    except (OSError, IndexError):
        return None


def _pid_alive(pid, identity):
    if not pid:
        return False
    actual = _pid_identity(pid)
    if actual is not None:
        try:
            if Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] == "Z":
                return False  # A zombie cannot run; cgroup descendants are checked separately.
        except (OSError, IndexError):
            pass
        return identity is None or hmac.compare_digest(actual, identity)
    try:
        os.kill(pid, 0)
        return True  # Cannot disprove identity; retain the reservation.
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _kill_recorded_process(pid, identity):
    """Stop a gated helper outside its leaf only with its exact recorded identity."""
    if not pid or not identity or _pid_identity(pid) != identity:
        return
    try:
        if os.getpgid(pid) == pid:
            os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


class RunCgroup:
    """Whole-run CPU/RAM/pid enforcement, including new sessions and descendants."""

    kernel_root = Path("/sys/fs/cgroup")

    @classmethod
    def _root(cls, root):
        root = Path(root)
        if sys.platform != "linux" or not root.is_absolute() or root.is_symlink() or any(p.is_symlink() for p in root.parents):
            raise ControlError("A delegated Linux cgroup v2 root is required")
        if root == cls.kernel_root or not root.is_relative_to(cls.kernel_root) or not (root / "cgroup.controllers").is_file():
            raise ControlError("A dedicated delegated child cgroup is required")
        return root

    @classmethod
    def existing(cls, root, run_id):
        root = cls._root(root)
        _id(run_id, "run id")
        path = root / ("arena-control-" + run_id)
        if path.is_symlink():
            raise ControlError("Run cgroup must not be a symlink")
        if not path.exists():
            return None
        obj = cls.__new__(cls)
        obj.path, obj.main = path, path / "main"
        return obj

    def __init__(self, root, run_id, resources):
        root = self._root(root)
        _id(run_id, "run id")
        self.path = root / ("arena-control-" + run_id)
        self.main = self.path / "main"
        self.path.mkdir(mode=0o700)
        try:
            settings = {"memory.max": str(resources["memory_mb"] * 1024**2),
                        "memory.swap.max": "0", "cpu.max": f"{resources['cpus'] * 100000} 100000",
                        "pids.max": str(resources["pids"])}
            for name in (*settings, "cgroup.kill", "cgroup.events", "cgroup.subtree_control"):
                if not (self.path / name).is_file():
                    raise ControlError("Delegate cpu, memory, pids and cgroup.kill before running")
            for name, value in settings.items():
                (self.path / name).write_text(value)
            # Empty parent with a main leaf supports native drivers that create
            # bounded child cgroups (e.g. Station) beneath the same run caps.
            (self.path / "cgroup.subtree_control").write_text("+cpu +memory +pids")
            self.main.mkdir(mode=0o700)
            self.kill()  # Prove kill permission before executing anything.
        except BaseException:
            try:
                self.close()
            except (OSError, ControlError):
                pass
            raise

    def kill(self):
        (self.path / "cgroup.kill").write_text("1")

    def populated(self):
        data = dict(line.split() for line in (self.path / "cgroup.events").read_text().splitlines())
        if data.get("populated") not in {"0", "1"}:
            raise ControlError("Cannot establish cgroup liveness")
        return data["populated"] == "1"

    def wait_empty(self, timeout=3):
        until = time.monotonic() + timeout
        while self.populated():
            if time.monotonic() >= until:
                return False
            time.sleep(0.05)
        return True

    def close(self):
        self.kill()
        if not self.wait_empty():
            raise ControlError("Run processes have not exited")
        for base, directories, _ in os.walk(self.path, topdown=False, followlinks=False):
            for directory in directories:
                (Path(base) / directory).rmdir()
        self.path.rmdir()


def _completed_result(directory):
    try:
        result = _decode(_read_regular(directory / "result.json", maximum=4096, private=True))
        if result.get("state") in {"completed", "failed"} and type(result.get("returncode")) is int:
            return result["state"], None if result["state"] == "completed" else "Native process failed; inspect private worker artifacts.", result["returncode"]
    except (OSError, ControlError, AttributeError):
        pass
    return "blocked", "Worker interrupted without a confirmed terminal result; no automatic relaunch.", None
