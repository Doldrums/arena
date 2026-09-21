#!/usr/bin/python3 -I
"""Enter the dedicated cgroup before permanently dropping worker privileges."""
import os
from pathlib import Path
import pwd

if os.geteuid() != 0:
    raise SystemExit("The system service must enter its cgroup before dropping privileges")
account = pwd.getpwnam("arena")
root = Path("/sys/fs/cgroup/arena-workers")
supervisor = root / "supervisor"
supervisor.mkdir(exist_ok=True)
(supervisor / "cgroup.procs").write_text(str(os.getpid()))
os.initgroups("arena", account.pw_gid)
os.setgid(account.pw_gid)
os.setuid(account.pw_uid)
if os.geteuid() != account.pw_uid or os.getegid() != account.pw_gid:
    raise SystemExit("Worker privilege drop failed")
os.environ["HOME"] = account.pw_dir
os.execv("/opt/arena/venv/bin/python", ["/opt/arena/venv/bin/python", "-m", "arena.control", "worker",
        "--config", "/srv/arena/configs/control.json", "--concurrency", "32"])
