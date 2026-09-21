"""Bounded foreground Station session; native imports occur only in its worker.

Linux cgroup v2 contains native workers that intentionally create new sessions.
This is lifecycle/resource containment, not a sandbox for generated code.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid


TASK = "example/research_alpha_evolve/circle_n32"
TEMPLATE = "example/station/default"
MODULE = "arena.frameworks.drivers.station"
CGROUP_ROOT = Path("/sys/fs/cgroup")


def _integer(upper):
    def convert(value):
        result = int(value)
        if not 1 <= result <= upper:
            raise argparse.ArgumentTypeError(f"Expected an integer from 1 to {upper}")
        return result
    return convert


def _parse(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["run", "_worker"])
    parser.add_argument("--task", choices=[TASK], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--coder-model", required=True)
    parser.add_argument("--agents", type=_integer(32), required=True)
    parser.add_argument("--ticks", type=_integer(10000), required=True)
    parser.add_argument("--context-tokens", type=_integer(2000000), required=True)
    parser.add_argument("--response-tokens", type=_integer(100000), required=True)
    parser.add_argument("--wall-seconds", type=_integer(604800), required=True)
    parser.add_argument("--eval-seconds", type=_integer(86400), required=True)
    parser.add_argument("--eval-workers", type=_integer(32), required=True)
    parser.add_argument("--cpus", type=_integer(1024), required=True)
    parser.add_argument("--memory-gib", type=_integer(1024), required=True)
    parser.add_argument("--max-processes", type=_integer(4096), required=True)
    parser.add_argument("--conda-env", required=True)
    parser.add_argument("--codex-binary", type=Path, required=True)
    parser.add_argument("--cgroup-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", value)
           for value in (args.model, args.coder_model)):
        parser.error("Models must be explicit provider model identifiers")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", args.conda_env):
        parser.error("A prepared named conda environment is required")
    if args.response_tokens > args.context_tokens or args.eval_seconds > args.wall_seconds:
        parser.error("Response/evaluation limits must fit within their enclosing limits")
    if not args.codex_binary.is_absolute() or not args.codex_binary.is_file() or not os.access(args.codex_binary, os.X_OK):
        parser.error("Codex must be an explicit existing absolute executable")
    if not args.output.is_absolute() or args.output.is_symlink():
        parser.error("Output must be an absolute non-symlink path")
    return args


class SessionCgroup:
    """Own only a fresh child of an operator-delegated Linux cgroup v2 root."""

    def __init__(self, root, args):
        if sys.platform != "linux" or not root.is_absolute() or root.is_symlink():
            raise ValueError("Station requires a delegated Linux cgroup v2 directory")
        root = root.resolve()
        kernel_root = CGROUP_ROOT
        if root == kernel_root or not root.is_relative_to(kernel_root) or not (root / "cgroup.controllers").is_file():
            raise ValueError("Use a dedicated delegated child under /sys/fs/cgroup")
        self.path = root / ("arena-station-" + uuid.uuid4().hex)
        self.path.mkdir(mode=0o700)
        try:
            settings = {"memory.max": str(args.memory_gib * 1024 ** 3),
                        "cpu.max": f"{args.cpus * 100000} 100000", "pids.max": str(args.max_processes)}
            for name in (*settings, "cgroup.kill", "cgroup.procs"):
                if not (self.path / name).is_file():
                    raise ValueError("Delegate memory, cpu and pids controllers and cgroup.kill before launching")
            for name, value in settings.items():
                (self.path / name).write_text(value)
            # Prove termination permission while the owned group is still empty.
            self.kill()
        except BaseException:
            self.path.rmdir()
            raise

    def join_before_exec(self):
        # Runs in the forked child before any participant code or descendants.
        (self.path / "cgroup.procs").write_text(str(os.getpid()))

    def kill(self):
        (self.path / "cgroup.kill").write_text("1")

    def close(self):
        self.kill()
        deadline = time.monotonic() + 1
        while True:
            try:
                self.path.rmdir()
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Station cgroup cleanup is incomplete") from None
                time.sleep(0.02)


def _supervise(args, argv):
    if args.output.exists():
        raise ValueError("Station output must be new")
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY must be explicitly provided in the execution environment")
    group = SessionCgroup(args.cgroup_root, args)
    process, interrupted = None, []
    prior = {}
    started = time.monotonic()

    def cancel(number, _frame):
        interrupted.append(number)
        # The outer native runtime allows only a short termination grace.
        # Immediately kill all cgroup members, including detached native jobs.
        group.kill()

    try:
        for number in (signal.SIGTERM, signal.SIGINT):
            prior[number] = signal.signal(number, cancel)
        if interrupted:
            return 128 + interrupted[-1]
        args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
        process = subprocess.Popen([sys.executable, "-m", MODULE, "_worker", *argv[1:]],
                                   preexec_fn=group.join_before_exec)
        status, code = "native_exit", None
        while process.poll() is None:
            if interrupted:
                status, code = "interrupted", 128 + interrupted[-1]
                break
            if time.monotonic() - started >= args.wall_seconds:
                status, code = "timeout", 124
                break
            time.sleep(0.1)
        if code is None:
            code = 128 - process.returncode if process.returncode < 0 else process.returncode
            if interrupted:
                status, code = "interrupted", 128 + interrupted[-1]
        group.kill()
        process.wait(timeout=1)
        (args.output / "session.json").write_text(json.dumps({
            "schema": "arena.station-session/1", "canonical_evaluation": False,
            "status": status, "returncode": code,
            "limits": {"ticks": args.ticks, "wall_seconds": args.wall_seconds,
                       "cpus": args.cpus, "memory_gib": args.memory_gib, "max_processes": args.max_processes},
            "native_evaluation": "Station circle_n32 evaluator; results retain native validity and score",
        }, indent=2) + "\n")
        return code
    finally:
        try:
            group.close()
            if process is not None:
                process.wait(timeout=1)
        finally:
            for number, handler in prior.items():
                signal.signal(number, handler)


def _worker(args):
    """Call the pinned native initializer, research loop and evaluators unchanged."""
    workspace = Path.cwd().resolve()
    data = args.output / "station_data"
    if data.exists() or data.is_symlink():
        raise ValueError("Station state must be fresh")
    if any((parent / ".env").exists() or (parent / ".env").is_symlink()
           for parent in (workspace, *workspace.parents)):
        raise ValueError("Implicit dotenv configuration is not allowed")
    os.environ["STATION_BASE_DATA_PATH"] = str(data)
    os.environ["CODEX_BIN_PATH"] = str(args.codex_binary)
    # Source stays ahead of separately installed Station packages.
    sys.path.insert(0, str(workspace))
    from station_tools.commands.init import (copy_station_template_and_task,
                                            write_initial_station_config, disable_initial_agent_spawn,
                                            configure_multistart_for_init)
    from station import constants, startup_overrides
    copy_station_template_and_task(data, workspace / TEMPLATE, workspace / args.task)
    write_initial_station_config(data, "Arena native Station session", workspace, TEMPLATE)
    disable_initial_agent_spawn(data)
    configure_multistart_for_init(data, enabled=False)
    # Native configuration knobs: explicit models and budgets, no secret values.
    config = {
        "AUTO_START": False, "AUTO_EVAL_RESEARCH": True, "RESEARCH_CENTER_ENABLED": True,
        "RESEARCH_EVAL_MAX_PARALLEL_WORKERS": args.eval_workers,
        "RESEARCH_EVAL_TIMEOUT": args.eval_seconds, "RESEARCH_EVAL_MEMORY_LIMIT": f"{args.memory_gib}g",
        "RESEARCH_EVAL_CPU_NUM": None, "RESEARCH_EVAL_CPU_LIMIT": str(args.cpus),
        "RESEARCH_EVAL_GPU_NUM": None, "RESEARCH_EVAL_AVAILABLE_GPUS": [],
        "RESEARCH_EVAL_GPU_COORD_FILE": str(args.output / "gpu-coordination.json"),
        "RESEARCH_EVAL_CPU_COORD_FILE": str(args.output / "cpu-coordination.json"),
        "RESEARCH_EVAL_PYTHON_CONDA_ENV": args.conda_env,
        "RESEARCH_EVAL_USE_PYTHON_SANDBOX": True,
        "RESEARCH_EVAL_SANDBOX_BASE_DIR": str(args.output / "scratch"),
        "RESEARCH_CODER_BACKEND": "codex", "RESEARCH_CODER_MODEL_NAME": args.coder_model,
        "RESEARCH_CODER_TIMEOUT_SECONDS": args.eval_seconds,
        "ARCHIVE_SURVEY_BACKEND": "codex", "ARCHIVE_SURVEY_MODEL_NAME": args.coder_model,
        "AUTO_EVAL_ARCHIVE_MODEL_CLASS": "OpenAI", "AUTO_EVAL_ARCHIVE_MODEL_NAME": args.model,
        "REFLECTION_META_MODEL_PROVIDER_CLASS": "OpenAI", "REFLECTION_META_MODEL_NAME": args.model,
    }
    startup_overrides._update_constant_config(data, config)
    constants._load_config_overrides()
    from station.station import Station
    from station.station_runner import Orchestrator
    station, orchestrator = None, None
    reason, code = "native_error", 1
    try:
        station = Station()
        start_tick = station._get_current_tick()
        target_tick = start_tick + args.ticks
        startup_overrides._update_constant_config(data, {"PAUSE_AFTER_TICK_END": target_tick - 1})
        constants._load_config_overrides()
        orchestrator = Orchestrator(station, auto_prepare_on_init=False)
        for _ in range(args.agents):
            success, _message = orchestrator.dynamic_add_agent_to_station(
                agent_type=constants.AGENT_STATUS_GUEST, model_provider_class="OpenAI", model_name=args.model,
                initial_tokens_max=args.context_tokens, llm_max_tokens=args.response_tokens)
            if success is not True:
                raise RuntimeError("Native Station agent preparation failed")
        if not orchestrator.prepare_for_run() or not orchestrator.agent_turn_order or not orchestrator.start_orchestration():
            raise RuntimeError("Native Station research loop did not start")
        while orchestrator.is_running:
            if orchestrator.is_paused and station._get_current_tick() >= target_tick:
                pending = any((station.has_pending_research_evaluations(), station.has_pending_coder_sessions(),
                               station.has_pending_archive_evaluations(), station.has_pending_archive_surveys(),
                               station.has_pending_external_reports()))
                if not pending:
                    reason, code = "tick_limit_drained", 0
                    break
            time.sleep(0.1)
        return code
    finally:
        # stop_orchestration may return early when its thread has already died,
        # so always invoke each Station service's own shutdown path as well.
        try:
            if orchestrator is not None:
                orchestrator.stop_orchestration()
        finally:
            if station is not None:
                for stop in (station.stop_auto_research_evaluator, station.stop_auto_archive_evaluator,
                             station.stop_auto_archive_surveyor, station.stop_auto_external_reporter):
                    stop()
            (args.output / "native-session.json").write_text(json.dumps({
                "canonical_evaluation": False, "status": reason,
                "current_tick": station._get_current_tick() if station is not None else None,
                "requested_ticks": args.ticks, "task": args.task,
            }, indent=2) + "\n")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = _parse(argv)
    return _worker(args) if args.mode == "_worker" else _supervise(args, argv)


if __name__ == "__main__":
    raise SystemExit(main())
