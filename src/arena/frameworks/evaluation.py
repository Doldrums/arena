"""Pinned task-suite evaluation with explicit execution and immutable receipts.

The Docker profile isolates generated candidates. ``local_trusted`` is an
explicit opt-in for reviewed fixtures; it is not a sandbox. Neither importing
this module nor preparing an evaluation executes task or participant code.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time
import uuid

from arena.registry import get_catalog
from arena.task_library import load_task_manifest, read_task_file, resolve_task_root, verify_task_library
from .runtime import _absolute, _digest_file, _write_json, _Capture, _stop

_CGROUP_MOUNT = Path("/sys/fs/cgroup")
_PROCESS_CGROUP = Path("/proc/self/cgroup")
_BROKER_CONTEXT = Path("/run/arena-engine/context.json")


def _broker_context_bytes(path):
    """Read only the root broker's immutable, bounded mount; never worker JSON."""
    if path.resolve() != path or os.geteuid() == 0:
        raise ValueError("Engine context requires a non-root process and an unlinked fixed mount")
    for parent in path.parents:
        info = parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0
                or stat.S_IMODE(info.st_mode) & 0o022):
            raise ValueError("Engine context ancestors must be root-owned and not worker-writable")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != 0 or before.st_gid != 0
                or stat.S_IMODE(before.st_mode) != 0o444 or before.st_nlink != 1 or before.st_size > 4096):
            raise ValueError("Engine context must be a root-owned mode0444 bounded regular file")
        raw = os.read(descriptor, 4097)
        after = os.fstat(descriptor)
        current = path.lstat()
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if (len(raw) > 4096 or any(getattr(before, name) != getattr(after, name)
                                 or getattr(before, name) != getattr(current, name) for name in fields)):
            raise ValueError("Engine context changed while being read")
        return raw
    finally:
        os.close(descriptor)


def _broker_context():
    """Private cgroup namespace metadata; the proxy authenticates host membership."""
    if os.environ.get("ARENA_EVALUATION_BROKER_CONTEXT") != str(_BROKER_CONTEXT):
        raise ValueError("Engine context must use the fixed broker mount")
    if os.environ.get("DOCKER_HOST") != "unix:///run/arena-evaluator/docker.sock":
        raise ValueError("Engine evaluation requires the restricted canonical proxy")
    memberships = [line[3:] for line in _PROCESS_CGROUP.read_text().splitlines() if line.startswith("0::")]
    if memberships != ["/"]:
        raise ValueError("Engine context requires the broker's private cgroup namespace")
    def unique_keys(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("Duplicate engine context key")
            value[key] = item
        return value
    context = json.loads(_broker_context_bytes(_BROKER_CONTEXT), object_pairs_hook=unique_keys)
    fields = {"schema", "run_id", "container_id", "cgroup_parent", "receipts_dir"}
    if (type(context) is not dict or set(context) != fields
            or any(type(value) is not str for value in context.values())
            or context["schema"] != "arena.engine-context/1"
            or not re.fullmatch(r"[0-9a-f]{32}", context["run_id"])
            or not re.fullmatch(r"[0-9a-f]{64}", context["container_id"])):
        raise ValueError("Invalid engine context identity")
    ident = context["run_id"]
    if (context["cgroup_parent"] != f"/arena-workers/arena-control-{ident}"
            or context["receipts_dir"] != f"/srv/arena/control/runs/{ident}/artifacts/canonical-evaluations"
            or Path(context["receipts_dir"]).resolve() != Path(context["receipts_dir"])):
        raise ValueError("Engine context cgroup and receipts must identify the same admitted run")
    return {name: context[name] for name in fields - {"schema"}} | {"authorization": "engine_broker"}


def _control_context():
    """Bind Docker children to this admitted process's cgroup and artifact root."""
    if "ARENA_EVALUATION_BROKER_CONTEXT" in os.environ:
        return _broker_context()
    raw = os.environ.get("ARENA_EVALUATION_CGROUP_PARENT", "")
    parent = Path(raw)
    if (not raw or not parent.is_absolute() or parent.resolve() != parent
            or not parent.is_relative_to(_CGROUP_MOUNT) or parent == _CGROUP_MOUNT):
        raise ValueError("Controlled evaluation requires an existing real delegated cgroup parent")
    match = re.fullmatch(r"arena-control-([0-9a-f]{32})", parent.name)
    if (match is None or not parent.is_dir()
            or any(not (parent / name).is_file() for name in ("cgroup.controllers", "cgroup.kill"))):
        raise ValueError("Controlled evaluation requires a cgroup v2 admitted run")
    hierarchy = "/" + parent.relative_to(_CGROUP_MOUNT).as_posix()
    memberships = [line[3:] for line in _PROCESS_CGROUP.read_text().splitlines() if line.startswith("0::")]
    if len(memberships) != 1 or not (memberships[0] == hierarchy or memberships[0].startswith(hierarchy + "/")):
        raise ValueError("Evaluator process is outside its declared admitted cgroup")
    raw_receipts = os.environ.get("ARENA_EVALUATION_RECEIPTS_DIR", "")
    receipts = Path(raw_receipts)
    if (not raw_receipts or not receipts.is_absolute() or receipts.resolve() != receipts
            or receipts.name != "canonical-evaluations" or receipts.parent.name != "artifacts"
            or receipts.parent.parent.name != match[1]):
        raise ValueError("Controlled receipts must belong to the same admitted run")
    return {"run_id": match[1], "cgroup_parent": hierarchy, "receipts_dir": str(receipts)}


def receipt_root(config, fallback):
    """Use the worker-owned per-run location only for explicitly controlled tasks."""
    if config.get("execution", {}).get("require_control_cgroup") is True:
        return Path(_control_context()["receipts_dir"])
    return Path(fallback)


def validate_config(config):
    required = {"schema", "task_id", "timeout_seconds", "execution"}
    if type(config) is not dict or not required <= config.keys() or set(config) - required - {"profile", "receipts_dir", "tasks_dir"}:
        raise ValueError("Evaluation config has missing or unknown fields")
    if config["schema"] != "arena.evaluation-config/1":
        raise ValueError("Expected arena.evaluation-config/1")
    timeout = config["timeout_seconds"]
    if type(timeout) is not int or not 1 <= timeout <= 86400:
        raise ValueError("Evaluation timeout must be an integer from 1 to 86400 seconds")
    if "tasks_dir" in config and (type(config["tasks_dir"]) is not str or not config["tasks_dir"]):
        raise ValueError("tasks_dir must be an absolute task library path")
    if "receipts_dir" in config:
        _absolute(config["receipts_dir"], "receipts_dir")
    catalog = get_catalog()
    task = next((t for t in catalog["tasks"] if t["id"] == config["task_id"]), None)
    if task is None or not task["executable"]:
        raise ValueError("Task has no registered executable evaluation definition")
    source = next(s for s in catalog["sources"] if s["id"] == task["source_id"])
    root = resolve_task_root(config.get("tasks_dir"), source=source)
    revision = verify_task_library(root, source)
    config = {**config, "tasks_dir": str(root)}
    read_task_file(root, task["contract_source"]["path"], task["contract_source"]["sha256"])
    evaluator_path = f"suite/{task['id']}/evaluator.py"
    files = load_task_manifest(source)["files"]
    if evaluator_path not in files:
        raise ValueError("Pinned suite evaluator is missing")
    evaluator_raw = read_task_file(root, evaluator_path, files[evaluator_path])
    execution = config["execution"]
    if type(execution) is not dict:
        raise ValueError("execution must specify docker or local_trusted")
    if execution.get("kind") == "local_trusted":
        if set(execution) != {"kind", "python"}:
            raise ValueError("local_trusted requires only kind and python")
        # Preserve the venv path: resolving its Python symlink changes sys.prefix.
        python = Path(execution["python"])
        if not python.is_absolute() or not python.is_file() or not os.access(python, os.X_OK):
            raise ValueError("local_trusted Python must be an absolute executable path")
    elif execution.get("kind") == "docker":
        if (not {"kind", "image", "python"} <= set(execution)
                or set(execution) - {"kind", "image", "python", "require_control_cgroup", "resource_profile"}
                or not isinstance(execution["image"], str)):
            raise ValueError("docker requires kind, image and python")
        if "require_control_cgroup" in execution and type(execution["require_control_cgroup"]) is not bool:
            raise ValueError("require_control_cgroup must be an explicit boolean")
        if not re.fullmatch(r"(?:[A-Za-z0-9][A-Za-z0-9._/:\-]*@)?sha256:[0-9a-f]{64}", execution["image"]):
            raise ValueError("Docker evaluation image must be pinned by sha256 digest")
        if execution["python"] not in {"python", "python3"}:
            raise ValueError("Docker Python must be python or python3 from the pinned image")
        if "resource_profile" in execution:
            from arena.evaluation_resources import budget
            if execution["resource_profile"] is None:
                raise ValueError("resource_profile must name an explicit canonical budget")
            budget(execution["resource_profile"])
    else:
        raise ValueError("Choose docker for generated code or local_trusted for reviewed fixtures")
    return {"config": config, "task": task, "source_dir": str(root), "source": revision,
            "source_registration": source, "problem_sha256": task["contract_source"]["sha256"],
            "evaluator_sha256": hashlib.sha256(evaluator_raw).hexdigest()}


def prepare_evaluation(config, program_path, output_dir):
    prepared = validate_config(config)
    original = Path(program_path)
    if original.is_symlink() or not original.is_absolute() or not original.is_file() or original.suffix != ".py":
        raise ValueError("Candidate must be an absolute regular .py file")
    if original.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Candidate exceeds 16 MiB")
    output = _absolute(str(output_dir), "output_dir")
    source = Path(prepared["source_dir"])
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output) or original.is_relative_to(output):
        raise ValueError("Evaluation output must be new and outside the task checkout")
    prepared.update(candidate_path=str(original), candidate_sha256=_digest_file(original), output_dir=str(output))
    return prepared


def normalize_result(native, prepared):
    """Map metric direction once. Unknown validity never becomes true."""
    task = prepared["task"]
    if task["direction"] not in {"maximize", "minimize"}:
        raise ValueError("Evaluation direction must be maximize or minimize")
    if type(native) is not dict or native.get("task_id") != task["id"]:
        raise ValueError("Evaluation returned the wrong task identity")
    expected = {"candidate_sha256": prepared["candidate_sha256"],
                "evaluator_sha256": prepared["evaluator_sha256"],
                "protocol": task["protocol"], "direction": task["direction"], "mode": "suite"}
    if any(native.get(key) != value for key, value in expected.items()):
        raise ValueError("Evaluation provenance does not match its request")
    valid = native.get("valid")
    if valid is not None and type(valid) is not bool:
        raise ValueError("Evaluation validity must be true, false or null")
    # The pinned suite runner rejects a null score before copying the native
    # evaluator's validity. Preserve only an explicit repository-level failure;
    # nested successes and generic exceptions cannot establish validity.
    upstream = native.get("upstream_result")
    if (valid is None and native.get("status") == "failed"
            and native.get("evaluator_scope") == "repository"
            and type(upstream) is dict and upstream.get("valid") is False):
        valid = False
    score = native.get("score")
    if score is not None:
        try:
            finite = type(score) in (int, float) and math.isfinite(score)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("Evaluation score must be finite or null")
    native_status = native.get("status")
    if native_status == "timeout":
        status = "timeout"
    elif valid is False:
        status = "invalid"
    elif native_status == "completed" and score is not None:
        status = "completed"
    else:
        status = "error"
    # Preserve any raw metric even for invalid candidates, but give it no fitness.
    fitness = (score if task["direction"] == "maximize" else -score) if status == "completed" and valid is True else None
    return {"raw_score": score, "direction": task["direction"], "fitness": fitness,
            "validity": valid, "status": status, "metric": task["metric"]}


def _read_native_result(path):
    """Parse and hash the same bounded, stable regular-file snapshot."""
    limit = 4 * 1024 * 1024
    def signature(info):
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate native JSON key")
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError("Nonfinite native JSON")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("Native evaluator result must be a regular file of at most 4 MiB")
        chunks, size = [], 0
        while size <= limit:
            chunk = os.read(descriptor, min(65536, limit + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if (size > limit or signature(before) != signature(os.fstat(descriptor))
                or signature(before) != signature(path.lstat())):
            raise ValueError("Native evaluator result changed while being read")
    finally:
        os.close(descriptor)
    raw = b"".join(chunks)
    native = json.loads(raw, object_pairs_hook=unique_keys, parse_constant=reject_constant)
    return native, hashlib.sha256(raw).hexdigest()


def evaluate(config, program_path, output_dir):
    prepared = prepare_evaluation(config, Path(program_path), Path(output_dir))
    output = Path(prepared["output_dir"])
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    candidate_dir = output / "input"
    candidate = candidate_dir / "program.py"
    execution = config["execution"]
    ident = uuid.uuid4().hex
    native_dir = output / "native-output"
    native_file = native_dir / "native.json"
    receipt = {"schema": "arena.evaluation/1", "evaluation_id": ident,
               "task_id": config["task_id"], "task_source": prepared["source"],
               "protocol": prepared["task"]["protocol"], "problem_sha256": prepared["problem_sha256"],
               "evaluator_sha256": prepared["evaluator_sha256"],
               "candidate_sha256": prepared["candidate_sha256"], "execution": execution,
               "raw_score": None, "fitness": None, "validity": None,
               "direction": prepared["task"]["direction"], "metric": prepared["task"]["metric"],
               "status": "error", "evaluation_attempts": 0, "retries": 0,
               "receipt_path": str(output / "receipt.json"), "warnings": [],
               "native_result_path": str(native_file),
               "started_at": time.time(), "environment_locked": execution["kind"] == "docker"}
    root = Path(prepared["source_dir"])
    container = f"arena-eval-{ident}"
    if execution["kind"] == "docker":
        # A trusted evaluator and candidate share this container. This constrains
        # resource/host access; it is not an adversarial verifier guarantee.
        from arena.evaluation_resources import budget
        resources = budget(execution.get("resource_profile"))
        memory = f"{resources['memory_mb']}m" if "resource_profile" in execution else "2g"
        argv = ["docker", "run", "--rm", "--pull=never", "--name", container,
                "--network", "none", "--read-only", "--cpus", "1", "--memory", memory,
                "--pids-limit", str(resources["pids"]), "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--user", f"{os.getuid()}:{os.getgid()}", "--tmpfs", "/tmp:rw,nosuid,nodev,size=268435456",
                "--mount", f"type=bind,src={root},dst=/tasks,readonly",
                "--mount", f"type=bind,src={candidate_dir},dst=/candidate,readonly",
                "--mount", f"type=bind,src={native_dir},dst=/results",
                "--env", "PYTHONDONTWRITEBYTECODE=1",
                "--env", "PYTHONPYCACHEPREFIX=/tmp/arena-pycache", "--workdir", "/tmp", execution["image"],
                execution["python"], "/tasks/run.py", "--root", "/tasks", "evaluate", config["task_id"],
                "--candidate", "/candidate/program.py", "--python", execution["python"],
                "--timeout", str(config["timeout_seconds"]), "--output", "/results/native.json"]
        if "resource_profile" in execution:
            position = argv.index(execution["image"])
            argv[position:position] = ["--memory-swap", memory]
    else:
        argv = [execution["python"], str(root / "run.py"), "--root", str(root), "evaluate", config["task_id"],
                "--candidate", str(candidate), "--python", execution["python"],
                "--timeout", str(config["timeout_seconds"]), "--output", str(native_file)]
        receipt["warnings"].append("local_trusted executes reviewed code on this host without sandbox isolation")
    captures, process = [], None
    started = time.monotonic()
    # Only the operator-selected Unix Docker endpoint crosses this boundary;
    # no model credentials are inherited by the CLI, cleanup, or container.
    environment = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1",
                   "HOME": str(output), "TMPDIR": "/tmp", "MPLBACKEND": "Agg",
                   "PYTHONPYCACHEPREFIX": str(output / "bytecode-cache")}
    try:
        docker_host = os.environ.get("DOCKER_HOST")
        if execution["kind"] == "docker" and docker_host:
            if not re.fullmatch(r"unix:///[^\x00\r\n]+", docker_host):
                raise ValueError("Docker evaluation endpoint must be a local Unix socket")
            environment["DOCKER_HOST"] = docker_host
        if execution.get("require_control_cgroup") is True:
            context = _control_context()
            if output.parent != Path(context["receipts_dir"]) or re.fullmatch(r"[0-9a-f]{32}", output.name) is None:
                raise ValueError("Evaluation output must be a fresh evaluation ID under its admitted run")
            driver = subprocess.run(["docker", "info", "--format", "{{.CgroupDriver}} {{.CgroupVersion}}"],
                                    env=environment, capture_output=True, timeout=10, check=True)
            if driver.stdout.strip() != b"cgroupfs 2":
                raise ValueError("Controlled evaluation requires Docker cgroupfs with cgroup v2")
            position = argv.index(execution["image"])
            argv[position:position] = ["--label", "arena.evaluator=canonical-v1", "--label",
                                      "arena.control-run=" + context["run_id"],
                                      "--cgroup-parent", context["cgroup_parent"]]
            if "resource_profile" in execution:
                argv[position:position] = ["--label", "arena.evaluation-profile=" + execution["resource_profile"]]
            receipt["control"] = context
        native_dir.mkdir(mode=0o700)
        candidate_dir.mkdir()
        shutil.copyfile(prepared["candidate_path"], candidate)
        if _digest_file(candidate) != prepared["candidate_sha256"]:
            raise ValueError("Candidate changed while being snapshotted")
        candidate.chmod(0o444)
        if verify_task_library(root, prepared["source_registration"]) != prepared["source"]:
            raise ValueError("Task library identity changed before execution")
        if execution["kind"] == "local_trusted":
            receipt["python_sha256"] = _digest_file(Path(execution["python"]))
        _write_json(output / "request.json", {"schema": "arena.evaluation-request/1", "config": config,
                                             "candidate_sha256": prepared["candidate_sha256"], "argv": argv})
        # No model credentials or participant environment is passed to evaluators.
        process = subprocess.Popen(argv, cwd=output, env=environment, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        receipt["evaluation_attempts"] = 1
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            capture = _Capture(stream, output / f"{name}.log")
            captures.append(capture)
            capture.start()
        process.wait(timeout=config["timeout_seconds"] + 15)
        receipt["returncode"] = process.returncode
        native, native_digest = _read_native_result(native_file)
        receipt.update(normalize_result(native, prepared))
        if process.returncode not in (0, 1) or (process.returncode != 0 and receipt["status"] == "completed"):
            receipt.update(status="error", fitness=None)
        receipt["native_result_sha256"] = native_digest
    except subprocess.TimeoutExpired:
        receipt["status"] = "timeout"
    except KeyboardInterrupt:
        receipt["status"] = "interrupted"
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        receipt["warnings"].append(f"Evaluation did not produce a verified result ({type(error).__name__})")
    finally:
        if process is not None:
            _stop(process)
        if execution["kind"] == "docker" and process is not None:
            try:
                cleanup = subprocess.run(["docker", "rm", "--force", container], env=environment,
                                         capture_output=True, timeout=15)
                if cleanup.returncode and b"No such container" not in (cleanup.stderr or b""):
                    receipt["warnings"].append("Could not confirm Docker container cleanup")
            except (OSError, subprocess.SubprocessError):
                receipt["warnings"].append("Could not confirm Docker container cleanup")
        for capture in captures:
            capture.join(timeout=5)
            if capture.truncated:
                receipt["warnings"].append(f"{capture.path.name} truncated")
        receipt.update(ended_at=time.time(), wall_seconds=round(time.monotonic() - started, 6))
        _write_json(output / "receipt.json", receipt)
    return receipt
