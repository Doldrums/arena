"""Local, explicit native launches. No HTTP handler imports this module.

This is a process driver, not a sandbox, dependency installer or canonical
evaluator. Use a dedicated machine/container for native generated-code runs.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
import time

from . import get_adapter

MAX_INPUT_BYTES = 512 * 1024 * 1024
MAX_INPUT_FILES = 10000
MAX_LOG_BYTES = 8 * 1024 * 1024
_BASE_ENV = ("PATH", "HOME", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL", "SYSTEMROOT")


def _git_environment():
    return {**{key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
            "GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}


def _git(source, *args):
    # Git configuration must not arrange external pagers or mutation hooks for
    # these read-only probes. No participant Python is loaded here.
    result = subprocess.run(
        ["git", "--no-replace-objects", "-c", f"safe.directory={source}", "-c", "core.fsmonitor=false",
         "-c", "core.hooksPath=/dev/null", "-C", str(source), *args],
        check=True, capture_output=True, text=True, timeout=30,
        env=_git_environment(),
    )
    return result.stdout.strip()


def verify_source(source, commit):
    if not source.is_dir() or Path(_git(source, "rev-parse", "--show-toplevel")).resolve() != source:
        raise ValueError("source_dir must be the root of a separate Git checkout")
    if _git(source, "rev-parse", "HEAD") != commit:
        raise ValueError(f"Source must be checked out at the registered commit {commit}")
    flags = _git(source, "ls-files", "-v", "-z").split("\x00")
    if any(entry and (entry[0].islower() or entry[0] == "S") for entry in flags):
        raise ValueError("Source index must not hide files with assume-unchanged or skip-worktree flags")
    if _git(source, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Source checkout contains modifications or untracked files")
    return {"commit": commit, "tree": _git(source, "rev-parse", "HEAD^{tree}")}


def _absolute(value, name):
    if not isinstance(value, str) or not value or "\x00" in value or not Path(value).is_absolute():
        raise ValueError(f"{name} must be an absolute path")
    return Path(value).resolve()


def _digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_adapter(framework, request):
    if framework == "sciel-release":
        return get_adapter(framework, request=request)
    return get_adapter(framework)


def fingerprint_inputs(paths):
    """Record explicit inputs without copying config/credential contents."""
    files, size = {}, 0
    for value in paths:
        path = Path(value)
        if not path.is_absolute() or not path.exists() or path.is_symlink():
            raise ValueError("Adapter inputs must be existing absolute, non-symlink paths")
        candidates = [path] if path.is_file() else sorted(path.rglob("*"))
        for candidate in candidates:
            if candidate.is_symlink():
                raise ValueError(f"Input symlinks are not snapshot-safe: {candidate}")
            if candidate.is_dir():
                continue
            if not candidate.is_file():
                raise ValueError(f"Input is not a regular file: {candidate}")
            key = str(candidate.resolve())
            if key in files:
                continue
            length = candidate.stat().st_size
            size += length
            if size > MAX_INPUT_BYTES or len(files) >= MAX_INPUT_FILES:
                raise ValueError("Explicit inputs exceed the local provenance scan limit")
            files[key] = {"path": key, "bytes": length, "sha256": _digest_file(candidate)}
    return [files[key] for key in sorted(files)]


def prepare_plan(spec):
    required = {"schema", "framework", "source_dir", "output_dir", "timeout_seconds", "request"}
    if type(spec) is not dict or not required <= spec.keys() or set(spec) - required - {"environment_names"}:
        raise ValueError("Native run spec has missing or unknown fields")
    if spec["schema"] != "arena.native-run/1" or type(spec["request"]) is not dict:
        raise ValueError("Expected arena.native-run/1 and an object request")
    timeout = spec["timeout_seconds"]
    if type(timeout) is not int or not 1 <= timeout <= 604800:
        raise ValueError("timeout_seconds must be an integer between 1 and 604800")
    names = spec.get("environment_names", [])
    if type(names) is not list or any(not isinstance(n, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", n) for n in names):
        raise ValueError("environment_names must list explicit environment variable names")
    if len(names) != len(set(names)) or set(names) & {"PYTHONPATH", "PYTHONHOME", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES"}:
        raise ValueError("Duplicate or interpreter-injection environment names are not allowed")
    source = _absolute(spec["source_dir"], "source_dir")
    if isinstance(spec["output_dir"], str) and Path(spec["output_dir"]).is_symlink():
        raise ValueError("output_dir must be new, not a symlink")
    output = _absolute(spec["output_dir"], "output_dir")
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("output_dir must be new and outside the source checkout")
    adapter = _run_adapter(spec["framework"], spec["request"])
    revision = verify_source(source, adapter.commit)
    command = adapter.prepare(source, spec["request"], output)
    argv = command.get("argv")
    if type(argv) is not list or not argv or any(not isinstance(a, str) or "\x00" in a for a in argv):
        raise ValueError("Adapter returned an invalid argument vector")
    python = Path(argv[0])
    if not python.is_absolute() or not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError("request.python must name an absolute executable Python interpreter")
    command_env = command.get("env", {})
    if type(command_env) is not dict or any(not isinstance(k, str) or not isinstance(v, str) for k, v in command_env.items()):
        raise ValueError("Adapter returned invalid environment overrides")
    inputs = fingerprint_inputs(command.get("input_paths", []))
    # Never store values of credentials passed through the environment.
    plan = {"schema": "arena.native-plan/1", "framework": spec["framework"],
            "source_dir": str(source), "source": revision, "output_dir": str(output),
            "timeout_seconds": timeout, "environment_names": names, "command": command,
            "inputs": inputs, "python_sha256": _digest_file(python),
            "canonical_evaluation": False, "environment_locked": False}
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    plan["sha256"] = hashlib.sha256(canonical).hexdigest()
    return plan


def _write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


def _stage_workspace(plan):
    if not plan["command"].get("workspace_copy"):
        return
    destination = Path(plan["command"].get("workspace_root", plan["command"]["cwd"]))
    output = Path(plan["output_dir"]).resolve()
    if not destination.resolve().is_relative_to(output) or destination.resolve() == output:
        raise ValueError("Workspace must remain inside the new output directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-c", f"safe.directory={plan['source_dir']}", "-c", "core.hooksPath=/dev/null", "-c", "core.autocrlf=false", "clone", "--no-hardlinks",
                    "--no-checkout", plan["source_dir"], str(destination)],
                   check=True, capture_output=True, timeout=120, env=_git_environment())
    subprocess.run(["git", "-C", str(destination), "-c", "core.hooksPath=/dev/null",
                    "-c", "core.autocrlf=false", "-c", "core.eol=lf",
                    "checkout", "--detach", plan["source"]["commit"]],
                   check=True, capture_output=True, timeout=120, env=_git_environment())
    verify_source(destination, plan["source"]["commit"])
    for name, digest in plan["command"].get("source_evidence", {}).items():
        path = destination / name
        if (path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(destination.resolve())
                or _digest_file(path) != digest):
            raise ValueError("Copied native source differs from its reviewed evidence")
    def contained(value):
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts or ".git" in relative.parts:
            raise ValueError("Workspace input destination must be a contained non-Git path")
        target = destination / relative
        for parent in (target, *target.parents):
            if parent == destination:
                break
            if parent.is_symlink():
                raise ValueError("Workspace input destination traverses a symlink")
        if not target.resolve().is_relative_to(destination.resolve()):
            raise ValueError("Workspace input destination escapes the workspace")
        return target
    cwd = Path(plan["command"]["cwd"])
    if not cwd.is_relative_to(destination) or not contained(str(cwd.relative_to(destination))).is_dir():
        raise ValueError("Native working directory must exist inside the workspace")
    for value in plan["command"].get("workspace_remove_files", []):
        target = contained(value)
        if target.exists():
            if not target.is_file():
                raise ValueError("Native credential template must be a regular file")
            target.unlink()
    additions = [(item, False) for item in plan["command"].get("workspace_inputs", [])]
    additions += [(item, True) for item in plan["command"].get("workspace_overlays", [])]
    for item, overlay in additions:
        target = contained(item["destination"])
        if overlay and not target.is_file():
            raise ValueError("Configuration overlay must replace an existing regular config file")
        if not overlay and (target.exists() or target.is_symlink()):
            raise ValueError("Workspace input would overwrite native source")
        source = Path(item["source"])
        if str(source) not in plan["command"].get("input_paths", []):
            raise ValueError("Workspace input must be declared in input_paths")
        expected = [entry for entry in plan["inputs"] if Path(entry["path"]).is_relative_to(source.resolve())]
        before = fingerprint_inputs([str(source)])
        if before != expected:
            raise ValueError("Workspace input differs from its planned provenance")
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copyfile(source, target)
        copied = fingerprint_inputs([str(target)])
        def relative_manifest(entries, base):
            return sorted((str(Path(entry["path"]).relative_to(base.resolve())), entry["bytes"], entry["sha256"])
                          for entry in entries)
        if relative_manifest(before, source) != relative_manifest(copied, target):
            raise ValueError("Workspace input changed while being copied")
    if plan["command"].get("engine"):
        from .recipes import snapshot_artifacts
        baseline = snapshot_artifacts(output, destination, plan["command"]["expected_artifacts"])
        _write_json(output / ".arena" / "artifact-baseline.json", baseline)


class _Capture(threading.Thread):
    def __init__(self, stream, path):
        super().__init__(daemon=True)
        self.stream, self.path, self.truncated = stream, path, False

    def run(self):
        written = 0
        with self.path.open("xb") as log:
            self.path.chmod(0o600)
            while chunk := self.stream.read1(8192):
                keep = chunk[:max(0, MAX_LOG_BYTES - written)]
                log.write(keep)
                log.flush()
                written += len(keep)
                self.truncated |= len(keep) != len(chunk)
        self.stream.close()


def _stop(process):
    # Stop the native process group, including its ordinary child processes.
    # Independently scheduled Docker/remote jobs need framework-specific cleanup.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def run(spec):
    """Explicitly start one native process; return a process receipt, not a score."""
    if os.name != "posix":
        raise ValueError("The local native driver requires POSIX process groups")
    plan = prepare_plan(spec)
    output = Path(plan["output_dir"])
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    metadata = output / ".arena"
    metadata.mkdir(mode=0o700)
    _write_json(metadata / "plan.json", plan)
    receipt = {"schema": "arena.native-process/1", "framework": plan["framework"],
               "plan_sha256": plan["sha256"], "status": "preparing", "returncode": None,
               "canonical_evaluation": False, "started_at": None, "ended_at": None,
               "warnings": []}
    process, captures = None, []
    started = time.monotonic()
    try:
        _stage_workspace(plan)
        # Refuse changed explicit inputs between planning and launch.
        if fingerprint_inputs(plan["command"].get("input_paths", [])) != plan["inputs"]:
            raise ValueError("Explicit inputs changed during launch preparation")
        verify_source(Path(plan["source_dir"]), plan["source"]["commit"])
        if _digest_file(Path(plan["command"]["argv"][0])) != plan["python_sha256"]:
            raise ValueError("Python executable changed during launch preparation")
        for executable in plan["command"].get("executables", []):
            if _digest_file(Path(executable["path"])) != executable["sha256"]:
                raise ValueError("External runtime changed during launch preparation")
        environment = {name: os.environ[name] for name in (*_BASE_ENV, *plan["environment_names"]) if name in os.environ}
        environment.update(plan["command"].get("env", {}))
        process = subprocess.Popen(plan["command"]["argv"], cwd=plan["command"]["cwd"],
                                   env=environment, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            capture = _Capture(stream, metadata / f"{name}.log")
            captures.append(capture)
            capture.start()
        receipt.update(status="running", pid=process.pid, started_at=time.time())
        _write_json(metadata / "receipt.json", receipt)
        try:
            process.wait(timeout=plan["timeout_seconds"])
            receipt["status"] = "process_completed" if process.returncode == 0 else "process_failed"
        except subprocess.TimeoutExpired:
            receipt["status"] = "timed_out"
        except KeyboardInterrupt:
            receipt["status"] = "interrupted"
        finally:
            _stop(process)
            receipt["returncode"] = process.returncode
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        receipt["status"] = "launch_failed"
        # Exception arguments may contain native output or configuration values.
        receipt["warnings"].append(f"Launch preparation failed ({type(error).__name__})")
    finally:
        for capture in captures:
            capture.join(timeout=5)
            if capture.truncated:
                receipt["warnings"].append(f"{capture.path.name} truncated at {MAX_LOG_BYTES} bytes")
        receipt.update(ended_at=time.time(), wall_seconds=round(time.monotonic() - started, 6))
        _write_json(metadata / "receipt.json", receipt)
    try:
        native = _run_adapter(plan["framework"], spec["request"]).read_results(output)
        _write_json(metadata / "native-result.json", native)
    except (OSError, ValueError, KeyError, TypeError) as error:
        receipt["warnings"].append(f"Native result is not yet readable ({type(error).__name__})")
        _write_json(metadata / "receipt.json", receipt)
    return receipt
