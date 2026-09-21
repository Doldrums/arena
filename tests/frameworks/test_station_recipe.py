"""Station lifecycle tests use inert stand-ins; no native code or cgroup runs."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
from types import ModuleType, SimpleNamespace

import pytest

from arena.frameworks.drivers import station as driver
from arena.frameworks.recipes import RecipeAdapter, load_recipes


def arguments(tmp_path, mode="run"):
    return [mode, "--task", driver.TASK, "--model", "explicit-model", "--coder-model", "explicit-coder",
            "--agents", "2", "--ticks", "3", "--context-tokens", "1000", "--response-tokens", "100",
            "--wall-seconds", "20", "--eval-seconds", "10", "--eval-workers", "2", "--cpus", "2",
            "--memory-gib", "4", "--max-processes", "128", "--conda-env", "station-native",
            "--codex-binary", sys.executable, "--cgroup-root", "/sys/fs/cgroup/arena-worker",
            "--output", str(tmp_path / "native")]


@pytest.mark.parametrize("field,value", [("--agents", "0"), ("--ticks", "-1"), ("--wall-seconds", "0"),
                                         ("--eval-seconds", "21"), ("--response-tokens", "1001"),
                                         ("--model", "https://user:secret@host"), ("--conda-env", "../elsewhere")])
def test_limits_fail_before_native_import_or_launch(tmp_path, monkeypatch, field, value):
    args = arguments(tmp_path)
    args[args.index(field) + 1] = value
    monkeypatch.setattr(driver, "SessionCgroup", lambda *_: pytest.fail("Must validate before launch"))
    with pytest.raises(SystemExit) as error:
        driver.main(args)
    assert error.value.code == 2 and not (tmp_path / "native").exists()


def test_cgroup_requires_real_delegated_linux_location_before_native_launch(tmp_path, monkeypatch):
    args = driver._parse(arguments(tmp_path))
    monkeypatch.setattr(driver.sys, "platform", "linux")
    with pytest.raises(ValueError, match="dedicated delegated child"):
        driver.SessionCgroup(tmp_path, args)
    with pytest.raises(ValueError, match="dedicated delegated child"):
        driver.SessionCgroup(Path("/sys/fs/cgroup"), args)
    monkeypatch.setattr(driver.sys, "platform", "darwin")
    with pytest.raises(ValueError, match="Linux"):
        driver.SessionCgroup(args.cgroup_root, args)


def test_owned_cgroup_installs_total_limits_and_membership_before_participant_exec(tmp_path, monkeypatch):
    kernel = tmp_path / "kernel-fixture"
    delegated = kernel / "delegated"
    delegated.mkdir(parents=True)
    (delegated / "cgroup.controllers").write_text("cpu memory pids")
    original_mkdir = Path.mkdir
    def mkdir(path, *args, **kwargs):
        original_mkdir(path, *args, **kwargs)
        if path.parent == delegated:
            for name in ("memory.max", "cpu.max", "pids.max", "cgroup.kill", "cgroup.procs"):
                (path / name).touch()
    monkeypatch.setattr(Path, "mkdir", mkdir)
    monkeypatch.setattr(driver.sys, "platform", "linux")
    monkeypatch.setattr(driver, "CGROUP_ROOT", kernel)
    args = driver._parse(arguments(tmp_path))
    group = driver.SessionCgroup(delegated, args)
    assert group.path.parent == delegated and group.path.name.startswith("arena-station-")
    assert (group.path / "memory.max").read_text() == str(4 * 1024 ** 3)
    assert (group.path / "cpu.max").read_text() == "200000 100000"
    assert (group.path / "pids.max").read_text() == "128"
    assert (group.path / "cgroup.kill").read_text() == "1"  # empty-group permission probe
    assert (group.path / "cgroup.procs").read_text() == ""
    group.join_before_exec()
    assert (group.path / "cgroup.procs").read_text() == str(os.getpid())
    assert (delegated / "cgroup.controllers").read_text() == "cpu memory pids"


@pytest.fixture
def supervisor(monkeypatch):
    calls = []
    clock = [0.0]
    mode = {"value": "success"}
    monkeypatch.setenv("OPENAI_API_KEY", "inert-provider-secret")
    monkeypatch.setattr(driver.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(driver.time, "sleep", lambda _: clock.__setitem__(0, clock[0] + 21))

    class Group:
        def __init__(self, root, args):
            calls.append(("cgroup", str(root), args.memory_gib, args.cpus, args.max_processes))
        def join_before_exec(self):
            calls.append(("join",))
        def kill(self):
            calls.append(("kill-all-members",))
        def close(self):
            calls.append(("close-cgroup",))

    class Process:
        returncode = 0
        def __init__(self, command, **kwargs):
            calls.append(("spawn", command, set(kwargs)))
            assert set(kwargs) == {"preexec_fn"}  # retains outer process-group cleanup too
            kwargs["preexec_fn"]()
            if mode["value"] == "spawn-error":
                raise OSError("inert failure")
        def poll(self):
            if mode["value"] == "signal":
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                return None
            return 0 if mode["value"] == "success" else None
        def wait(self, timeout):
            calls.append(("wait", timeout))
            return 0

    monkeypatch.setattr(driver, "SessionCgroup", Group)
    monkeypatch.setattr(driver.subprocess, "Popen", Process)
    return calls, mode


@pytest.mark.parametrize("mode,code,status", [("success", 0, "native_exit"), ("timeout", 124, "timeout"),
                                             ("signal", 143, "interrupted")])
def test_supervisor_contains_before_exec_and_kills_detached_workers_on_every_exit(tmp_path, supervisor, mode, code, status):
    calls, settings = supervisor
    settings["value"] = mode
    prior = signal.getsignal(signal.SIGTERM)
    assert driver.main(arguments(tmp_path)) == code
    spawn = next(call for call in calls if call[0] == "spawn")
    assert spawn[1][:4] == [sys.executable, "-m", driver.MODULE, "_worker"]
    assert calls.index(("join",)) > calls.index(spawn)
    assert ("kill-all-members",) in calls and ("close-cgroup",) in calls
    assert signal.getsignal(signal.SIGTERM) == prior
    result = json.loads((tmp_path / "native/session.json").read_text())
    assert result["status"] == status and result["returncode"] == code
    assert result["canonical_evaluation"] is False
    assert "inert-provider-secret" not in json.dumps(result)


def test_supervisor_cleans_its_cgroup_when_process_creation_fails(tmp_path, supervisor):
    calls, settings = supervisor
    settings["value"] = "spawn-error"
    prior = signal.getsignal(signal.SIGTERM)
    with pytest.raises(OSError):
        driver.main(arguments(tmp_path))
    assert ("close-cgroup",) in calls and signal.getsignal(signal.SIGTERM) == prior


def _module(monkeypatch, name, **values):
    module = ModuleType(name)
    module.__dict__.update(values)
    monkeypatch.setitem(sys.modules, name, module)
    return module


@pytest.fixture
def native(monkeypatch, tmp_path):
    calls, config, mode = [], {}, {"value": "success"}
    native = SimpleNamespace(tick=1)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(driver.time, "sleep", lambda _: None)
    old_path = sys.path[:]
    data = tmp_path / "native"
    data.mkdir()
    def copy(station_data, template, task):
        calls.append(("copy", template, task))
        station_data.mkdir()
    def stopped(name):
        return lambda: calls.append(("stop", name))
    station = SimpleNamespace(_get_current_tick=lambda: native.tick,
        has_pending_research_evaluations=lambda: False, has_pending_coder_sessions=lambda: False,
        has_pending_archive_evaluations=lambda: False, has_pending_archive_surveys=lambda: False,
        has_pending_external_reports=lambda: False,
        stop_auto_research_evaluator=stopped("research"), stop_auto_archive_evaluator=stopped("archive"),
        stop_auto_archive_surveyor=stopped("surveyor"), stop_auto_external_reporter=stopped("external"))
    class Orchestrator:
        def __init__(self, instance, auto_prepare_on_init):
            assert instance is station and auto_prepare_on_init is False
            calls.append(("orchestrator",))
            self.is_running = False
            self.is_paused = False
            self.agent_turn_order = []
        def dynamic_add_agent_to_station(self, **kwargs):
            calls.append(("agent", kwargs))
            self.agent_turn_order.append("native-agent")
            return mode["value"] != "agent-error", "native message"
        def prepare_for_run(self):
            calls.append(("prepare",))
            return True
        def start_orchestration(self):
            calls.append(("start-native-loop",))
            native.tick = config["PAUSE_AFTER_TICK_END"] + 1
            self.is_running = mode["value"] != "early-exit"
            self.is_paused = True
            return True
        def stop_orchestration(self):
            calls.append(("stop", "orchestrator"))
    _module(monkeypatch, "station_tools")
    _module(monkeypatch, "station_tools.commands")
    _module(monkeypatch, "station_tools.commands.init", copy_station_template_and_task=copy,
            write_initial_station_config=lambda *args: calls.append(("initial-config",)),
            disable_initial_agent_spawn=lambda path: calls.append(("disable-roster",)),
            configure_multistart_for_init=lambda path, **kwargs: calls.append(("multistart", kwargs)))
    constants = SimpleNamespace(_load_config_overrides=lambda: calls.append(("reload",)), AGENT_STATUS_GUEST="guest")
    overrides = SimpleNamespace(_update_constant_config=lambda path, values: config.update(values))
    _module(monkeypatch, "station", constants=constants, startup_overrides=overrides)
    _module(monkeypatch, "station.station", Station=lambda: station)
    _module(monkeypatch, "station.station_runner", Orchestrator=Orchestrator)
    yield calls, config, mode
    sys.path[:] = old_path
    for key in ("STATION_BASE_DATA_PATH", "CODEX_BIN_PATH"):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize("mode,code", [("success", 0), ("early-exit", 1), ("agent-error", None)])
def test_worker_delegates_native_research_loop_and_all_evaluator_shutdowns(tmp_path, native, mode, code):
    calls, config, settings = native
    settings["value"] = mode
    if code is None:
        with pytest.raises(RuntimeError, match="agent preparation"):
            driver.main(arguments(tmp_path, "_worker"))
    else:
        assert driver.main(arguments(tmp_path, "_worker")) == code
    assert ("disable-roster",) in calls and ("multistart", {"enabled": False}) in calls
    assert config["PAUSE_AFTER_TICK_END"] == 3
    assert config["AUTO_EVAL_RESEARCH"] is True and config["RESEARCH_CENTER_ENABLED"] is True
    assert config["RESEARCH_CODER_MODEL_NAME"] == "explicit-coder"
    assert config["AUTO_EVAL_ARCHIVE_MODEL_NAME"] == "explicit-model"
    agents = [c[1] for c in calls if c[0] == "agent"]
    assert len(agents) == (1 if mode == "agent-error" else 2)
    assert agents[0] == {"agent_type": "guest", "model_provider_class": "OpenAI", "model_name": "explicit-model",
                         "initial_tokens_max": 1000, "llm_max_tokens": 100}
    assert {c[1] for c in calls if c[0] == "stop"} == {"orchestrator", "research", "archive", "surveyor", "external"}
    result = json.loads((tmp_path / "native/native-session.json").read_text())
    assert result["canonical_evaluation"] is False
    assert result["status"] == ("tick_limit_drained" if mode == "success" else "native_error")


def test_station_recipe_has_real_native_source_evidence_and_immutable_inert_plan(tmp_path):
    recipe = load_recipes()["the-station"]
    assert recipe["status"] == "source_verified" and recipe["blocked_reason"] is None
    assert recipe["repository"]["commit"] == "782088e561998bf357d95a838a0566a8229425d9"
    source = Path("/tmp/arena-framework-sources/the-station")
    if source.exists():
        for path, digest in recipe["evidence"].items():
            assert hashlib.sha256((source / path).read_bytes()).hexdigest() == digest
    source = tmp_path / "source"
    source.mkdir()
    recipe = deepcopy(recipe)
    for name in recipe["evidence"]:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("raise AssertionError('must not import')\n")
        recipe["evidence"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    request = {"python": sys.executable, "executables": {"codex": sys.executable}}
    command = RecipeAdapter(recipe).prepare(source, request, tmp_path / "result")
    assert command["argv"][1:5] == ["-m", driver.MODULE, "run", "--task"]
    assert command["executables"][0]["name"] == "codex"
    assert command["evaluation"]["mode"] == "native" and not (tmp_path / "result").exists()
    with pytest.raises(ValueError, match="fixes this option"):
        RecipeAdapter(recipe).prepare(source, {**request, "arguments": ["--task", "other"]}, tmp_path / "result")
