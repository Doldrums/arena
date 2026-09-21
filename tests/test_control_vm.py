"""Explicit inert Linux VM conformance probe; never runs during ordinary pytest.

Run this file with an isolated private directory and the delegated cgroup root.
It uses a temporary source-pinned fixture adapter, never a research framework.
The invoking environment must contain no real provider credentials.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if __name__ != "__main__":
    import pytest
    pytestmark = pytest.mark.skip(reason="Explicit inert VM conformance only; use the script CLI")


NATIVE = '''import json, os, subprocess, sys, time
from pathlib import Path
mode, output = sys.argv[1], Path(sys.argv[2])
if mode == "leaf":
    time.sleep(120)
elif mode == "exit":
    print("fixture completed", flush=True)
else:
    child = subprocess.Popen([sys.executable, __file__, "leaf", str(output)], start_new_session=True)
    (output / "pids.json").write_text(json.dumps([os.getpid(), child.pid]))
    print("fixture secret: " + os.environ.get("OPENAI_API_KEY", ""), flush=True)
    print("inert native diagnostic", file=sys.stderr, flush=True)
    time.sleep(120)
'''

HOOK = '''import os
if os.environ.get("ARENA_CONTROL_INERT_FIXTURE") == "1":
    from pathlib import Path
    import arena.frameworks.runtime as runtime
    original = runtime.get_adapter
    class FixtureAdapter:
        id = "control-fixture"
        commit = Path(os.environ["ARENA_CONTROL_FIXTURE_COMMIT"]).read_text().strip()
        def prepare(self, source_dir, request, output_dir):
            return {"argv": [request["python"], str(source_dir / "program.py"), request["mode"], str(output_dir)],
                    "cwd": str(source_dir), "env": {}, "input_paths": [str(source_dir / "program.py")],
                    "expected_artifacts": ["pids.json"]}
        def read_results(self, output_dir):
            return {"schema": "arena.native-result/1", "framework": "control-fixture", "canonical_evaluation": False,
                    "status": "recorded", "native": {}, "artifacts": [], "warnings": []}
    runtime.get_adapter = lambda name: FixtureAdapter() if name == "control-fixture" else original(name)
'''


def wait_until(callback, timeout=15):
    deadline = time.monotonic() + timeout
    while True:
        result = callback()
        if result:
            return result
        if time.monotonic() >= deadline:
            raise AssertionError("Inert VM condition timed out")
        time.sleep(0.05)


def request(base, path, key=None, body=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = Request(base + path, data=None if body is None else json.dumps(body).encode(), headers=headers)
    try:
        with urlopen(req, timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def probe(directory, cgroup_root):
    from arena import control
    assert sys.platform == "linux" and os.getuid() != 0
    assert os.environ.get("ARENA_CONTROL_INERT_FIXTURE") == "1"
    directory = Path(directory)
    directory.mkdir(mode=0o700, exist_ok=True)
    assert not any(directory.iterdir()), "Use a fresh isolated session directory"
    source = directory / "fixture-source"
    source.mkdir(mode=0o700)
    (source / "program.py").write_text(NATIVE)
    for args in (["init", "-q"], ["add", "program.py"], ["-c", "user.name=Inert Fixture", "-c", "user.email=fixture@localhost", "commit", "-qm", "Inert control conformance fixture"]):
        subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True)
    commit = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    commit_file = directory / "fixture-commit"
    commit_file.write_text(commit)
    os.environ["ARENA_CONTROL_FIXTURE_COMMIT"] = str(commit_file)
    hooks = directory / "hooks"
    hooks.mkdir()
    (hooks / "sitecustomize.py").write_text(HOOK)
    os.environ["PYTHONPATH"] = str(hooks) + os.pathsep + os.environ["PYTHONPATH"]
    fixture_key = "inert-control-validation-secret-do-not-use"
    os.environ["OPENAI_API_KEY"] = fixture_key
    config = {"schema": "arena.control/1", "state_dir": str(directory / "state"), "cgroup_root": str(cgroup_root),
              "limits": {"cpus": 2, "memory_mb": 512, "evaluation_slots": 2, "max_active": 2,
                         "max_queued": 20, "max_runs_per_key": 100, "max_reserved_seconds_per_key": 10000},
              "templates": []}
    for mode in ("sleep", "exit"):
        config["templates"].append({"id": mode, "name": "Explicit inert fixture", "framework": "control-fixture", "profile": mode,
            "model": "no-model", "status": "ready", "blocked_reason": None,
            "resources": {"cpus": 1, "memory_mb": 256, "evaluation_slots": 1, "pids": 32},
            "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
            "spec": {"schema": "arena.native-run/1", "framework": "control-fixture", "source_dir": str(source),
                     "output_dir": "{output_dir}", "timeout_seconds": 30,
                     "request": {"python": sys.executable, "mode": mode}, "environment_names": ["OPENAI_API_KEY"]}})
    config_path = directory / "config.json"
    config_path.write_text(json.dumps(config))
    config_path.chmod(0o600)
    service = control.ControlService(config_path)
    owner = service.create_key("fixture-owner", ["read", "submit", "cancel", "logs:native"])
    other = service.create_key("fixture-other", ["read", "submit", "cancel", "logs:native"])
    readonly = service.create_key("fixture-readonly", ["read"])
    principal = service.authenticate("Bearer " + owner["token"])
    results = {"schema": "arena.control-conformance/1", "inert_only": True,
               "module_sha256": hashlib.sha256(Path(control.__file__).read_bytes()).hexdigest(),
               "control_modules_sha256": {
                   path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in sorted(Path(control.__file__).parent.glob("control*.py"))},
               "source_fixture_commit": commit, "checks": {}}
    processes = []
    own_run_ids = []

    def submit(mode="sleep"):
        run = service.submit(principal, {"schema": "arena.control-submit/1", "template": mode, "model": "no-model"})["run"]
        own_run_ids.append(run["id"])
        return run

    def worker():
        process = subprocess.Popen([sys.executable, "-m", "arena.control", "worker", "--config", str(config_path), "--once"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        processes.append(process)
        return process

    def run_detail(run):
        return service.detail(principal, run["id"])["run"]

    def started(run):
        path = service.runs_dir / run["id"] / "artifacts" / "pids.json"
        return path if path.exists() else None

    try:
        # Exercise the actual CLI module identity and same-port control routing.
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        http = subprocess.Popen([sys.executable, "-m", "arena.control", "serve", "--config", str(config_path), "--port", str(port)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        processes.append(http)
        base = "http://127.0.0.1:" + str(port)
        def available():
            try:
                return request(base, "/api/queue")[0] == 401
            except (URLError, OSError):
                return False
        wait_until(available)
        assert request(base, "/api/control/templates")[0] == 401
        assert request(base, "/api/queue", readonly["token"], {"schema": "arena.control-submit/1", "template": "exit", "model": "no-model"})[0] == 403
        results["checks"]["actual_cli_auth_scopes"] = True

        # Run the actual native runtime against the pinned inert script.
        done = submit("exit")
        first = worker()
        assert first.wait(timeout=20) == 0
        assert run_detail(done)["state"] == "completed"
        receipt = json.loads((service.runs_dir / done["id"] / "artifacts" / ".arena" / "receipt.json").read_text())
        assert receipt["status"] == "process_completed" and receipt["canonical_evaluation"] is False
        results["checks"]["source_pinned_runtime_completion"] = True

        # Native setsid descendants stay contained; scoped diagnostics redact
        # the in-memory dummy key before the HTTP process reads them.
        run = submit()
        active = worker()
        pids_path = wait_until(lambda: started(run))
        native_pids = json.loads(pids_path.read_text())
        group = control.RunCgroup.existing(cgroup_root, run["id"])
        assert group is not None and group.populated()
        membership = [Path(f"/proc/{pid}/cgroup").read_text() for pid in native_pids]
        assert all("arena-control-" + run["id"] in entry for entry in membership)
        native_log = wait_until(lambda: service.logs(principal, run["id"], stream="native_stdout") if (service.runs_dir / run["id"] / "native_stdout.log").exists() else None)
        wait_until(lambda: "REDACTED" in service.logs(principal, run["id"], stream="native_stdout")["text"])
        text = request(base, "/api/queue/" + run["id"] + "/logs?stream=native_stdout", owner["token"])[1]["text"]
        assert fixture_key not in text and "REDACTED" in text
        assert request(base, "/api/queue/" + run["id"] + "/logs?stream=native_stdout", other["token"])[0] == 404
        assert request(base, "/api/queue/" + run["id"] + "/logs?stream=native_stdout", readonly["token"])[0] in {403, 404}
        code, payload = request(base, "/api/queue/" + run["id"] + "/cancel", owner["token"], {})
        assert code == 200 and payload["run"]["cancel_requested"]
        assert active.wait(timeout=15) == 0
        assert run_detail(run)["state"] == "cancelled"
        assert not run_detail(run)["resources_reserved"]
        assert all(not control._pid_alive(pid, None) for pid in native_pids)
        assert control.RunCgroup.existing(cgroup_root, run["id"]) is None
        results["checks"]["setsid_descendant_cancel_cleanup"] = True
        results["checks"]["native_log_scope_and_exact_secret_redaction"] = True

        # Kill only the queue worker supervisor. Surviving helper/native
        # descendants must not be re-launched from a stale lease.
        orphan = submit()
        supervisor = worker()
        orphan_pids = json.loads(wait_until(lambda: started(orphan)).read_text())
        supervisor.kill()
        supervisor.wait(timeout=5)
        with service._db(write=True) as db:
            db.execute("UPDATE runs SET lease_until=0 WHERE id=?", (orphan["id"],))
        restarted = control.ControlService(config_path)
        restarted.reconcile()
        observed = restarted.detail(principal, orphan["id"])["run"]
        assert observed["state"] == "blocked" and observed["resources_reserved"]
        assert restarted.claim("fixture-restarted-worker") is None
        restarted.cancel(principal, orphan["id"])
        def cancelled():
            restarted.reconcile()
            return not restarted.detail(principal, orphan["id"])["run"]["resources_reserved"]
        wait_until(cancelled)
        assert restarted.detail(principal, orphan["id"])["run"]["state"] == "cancelled"
        assert all(not control._pid_alive(pid, None) for pid in orphan_pids)
        results["checks"]["worker_crash_restart_no_duplicate"] = True
        results["checks"]["orphan_cancel_releases_only_after_exit"] = True

        # Real kernel CPU throttling and OOM accounting, with tiny inert jobs.
        probe_group = control.RunCgroup(cgroup_root, uuid.uuid4().hex, {"cpus": 1, "memory_mb": 128, "pids": 32})
        try:
            cpu_code = "import pathlib,os,subprocess,sys,time;pathlib.Path(sys.argv[1]).write_text(str(os.getpid()));p=[subprocess.Popen([sys.executable,'-c','while True: pass']) for _ in range(3)];time.sleep(2);[x.kill() for x in p];[x.wait() for x in p]"
            cpu = subprocess.Popen([sys.executable, "-c", cpu_code, str(probe_group.main / "cgroup.procs")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append(cpu)
            assert cpu.wait(timeout=10) == 0
            counters = dict(line.split() for line in (probe_group.path / "cpu.stat").read_text().splitlines())
            assert int(counters["nr_throttled"]) > 0
            results["checks"]["kernel_cpu_throttling"] = {"nr_throttled": int(counters["nr_throttled"]), "cpu_max": (probe_group.path / "cpu.max").read_text().strip()}
            oom_code = "import pathlib,os,sys;pathlib.Path(sys.argv[1]).write_text(str(os.getpid()));x=bytearray(384*1024*1024)"
            memory = subprocess.Popen([sys.executable, "-c", oom_code, str(probe_group.main / "cgroup.procs")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append(memory)
            assert memory.wait(timeout=10) != 0
            counters = dict(line.split() for line in (probe_group.path / "memory.events").read_text().splitlines())
            assert int(counters["oom_kill"]) > 0
            results["checks"]["kernel_memory_limit"] = {"oom_kill": int(counters["oom_kill"]), "memory_max": (probe_group.path / "memory.max").read_text().strip()}
        finally:
            probe_group.close()
        results["resources_after"] = service.queue(principal)["resources"]["used"]
        assert results["resources_after"]["active"] == 0
        results["state_counts"] = service.queue(principal)["counts"]
        results["checks"]["no_control_key_in_database"] = owner["token"].encode() not in service.db_path.read_bytes()
        assert results["checks"]["no_control_key_in_database"]
        return results
    finally:
        for run_id in own_run_ids:
            try:
                group = control.RunCgroup.existing(cgroup_root, run_id)
                if group:
                    group.close()
            except (OSError, control.ControlError):
                pass
        for process in processes:
            if process.poll() is None:
                process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass


if __name__ == "__main__":
    result = probe(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(result, indent=2, sort_keys=True))
