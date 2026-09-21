"""Canonical evaluation orchestration with local Git and inert evaluator fixtures."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from arena.frameworks import evaluation, runtime


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def evaluation_inputs(tmp_path, monkeypatch):
    source = tmp_path / "tasks"
    task_dir = source / "suite/fixture-task"
    task_dir.mkdir(parents=True)
    problem = task_dir / "problem.json"
    problem.write_text('{"fixture":true}')
    evaluator = task_dir / "evaluator.py"
    evaluator.write_text("# Never imported; this file is a provenance fixture.\n")
    # This explicit local child does not execute the submitted program.
    (source / "run.py").write_text('''import hashlib,json,os,sys
from pathlib import Path
args=sys.argv
root=Path(args[args.index('--root')+1]);candidate=Path(args[args.index('--candidate')+1])
native={'task_id':'fixture-task','candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),
 'evaluator_sha256':hashlib.sha256((root/'suite/fixture-task/evaluator.py').read_bytes()).hexdigest(),
 'protocol':'original','direction':'minimize','mode':'suite','valid':True,'score':4.25,'status':'completed',
 'secret_present':'APP_SECRET' in os.environ}
Path(args[args.index('--output')+1]).write_text(json.dumps(native))
sys.stdout.write('x'*8192);sys.stderr.write('fixture stderr')
''')
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()
    git("init", "-q")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    git("add", ".")
    git("commit", "-qm", "fixture")
    task = {"id": "fixture-task", "source_id": "fixture", "executable": True, "direction": "minimize",
            "protocol": "original", "metric": "fixture_error", "contract_source": {
                "path": "suite/fixture-task/problem.json", "sha256": digest(problem)}}
    catalog = {"tasks": [task], "sources": [{"id": "fixture", "repository": {"commit": git("rev-parse", "HEAD")}}]}
    monkeypatch.setattr(evaluation, "get_catalog", lambda: catalog)
    candidate = tmp_path / "candidate.py"
    candidate.write_text("raise RuntimeError('Candidate must not execute in these fixtures')\n")
    config = {"schema": "arena.evaluation-config/1", "tasks_dir": str(source), "task_id": "fixture-task",
              "timeout_seconds": 1, "execution": {"kind": "local_trusted", "python": sys.executable}}
    return config, candidate, tmp_path / "evaluation", catalog


def native_result(prepared, **overrides):
    task = prepared["task"]
    return {"task_id": task["id"], "candidate_sha256": prepared["candidate_sha256"],
            "evaluator_sha256": prepared["evaluator_sha256"], "protocol": task["protocol"],
            "direction": task["direction"], "mode": "suite", "valid": True,
            "score": 4.25, "status": "completed"} | overrides


def test_prepare_does_not_execute_or_create_outputs(evaluation_inputs):
    config, candidate, output, catalog = evaluation_inputs
    plan = evaluation.prepare_evaluation(config, candidate, output)
    assert not output.exists()
    assert plan["candidate_sha256"] == digest(candidate)
    assert plan["source"]["commit"] == catalog["sources"][0]["repository"]["commit"]
    assert plan["problem_sha256"] == catalog["tasks"][0]["contract_source"]["sha256"]


@pytest.mark.parametrize("direction,fitness", [("maximize", 4.25), ("minimize", -4.25)])
def test_metric_direction_is_applied_once(evaluation_inputs, direction, fitness):
    config, candidate, output, catalog = evaluation_inputs
    catalog["tasks"][0]["direction"] = direction
    plan = evaluation.prepare_evaluation(config, candidate, output)
    result = evaluation.normalize_result(native_result(plan), plan)
    assert result["raw_score"] == 4.25 and result["fitness"] == fitness
    assert result["status"] == "completed" and result["validity"] is True


@pytest.mark.parametrize("valid,status,expected", [(False, "completed", "invalid"),
    (None, "completed", "completed"), (True, "timeout", "timeout"), (True, "error", "error")])
def test_invalid_unknown_or_failed_results_never_receive_fitness(evaluation_inputs, valid, status, expected):
    config, candidate, output, _ = evaluation_inputs
    plan = evaluation.prepare_evaluation(config, candidate, output)
    result = evaluation.normalize_result(native_result(plan, valid=valid, status=status), plan)
    assert result["fitness"] is None and result["raw_score"] == 4.25
    assert result["validity"] is valid and result["status"] == expected


@pytest.mark.parametrize("field,value", [
    ("task_id", "another"), ("candidate_sha256", "0" * 64), ("evaluator_sha256", "1" * 64),
    ("protocol", "recreated"), ("direction", "maximize"), ("mode", "other"),
    ("valid", 1), ("score", float("inf")), ("score", float("nan")), ("score", True),
    ("score", 10 ** 400),
])
def test_identity_and_nonfinite_values_are_rejected(evaluation_inputs, field, value):
    config, candidate, output, _ = evaluation_inputs
    plan = evaluation.prepare_evaluation(config, candidate, output)
    with pytest.raises(ValueError):
        evaluation.normalize_result(native_result(plan, **{field: value}), plan)


def test_unknown_direction_is_not_silently_minimized(evaluation_inputs):
    config, candidate, output, catalog = evaluation_inputs
    catalog["tasks"][0]["direction"] = "unknown"
    plan = evaluation.prepare_evaluation(config, candidate, output)
    with pytest.raises(ValueError, match="direction"):
        evaluation.normalize_result(native_result(plan), plan)


def test_suite_failure_preserves_explicit_repository_invalidity(evaluation_inputs):
    config, candidate, output, _ = evaluation_inputs
    plan = evaluation.prepare_evaluation(config, candidate, output)
    native = native_result(plan, status="failed", score=None, valid=None,
                           evaluator_scope="repository", error="Evaluator returned no numeric score",
                           upstream_result={"valid": False, "score": None, "error": "construct returned an empty packing"})
    result = evaluation.normalize_result(native, plan)
    assert result["status"] == "invalid" and result["validity"] is False
    assert result["fitness"] is None and result["raw_score"] is None
    for changed in ({"upstream_result": {"valid": True}}, {"upstream_result": {"error": "failed"}},
                    {"evaluator_scope": "unknown"}, {"status": "error"}):
        result = evaluation.normalize_result(native | changed, plan)
        assert result["validity"] is None and result["fitness"] is None


def test_existing_output_and_candidate_links_are_rejected(evaluation_inputs):
    config, candidate, output, _ = evaluation_inputs
    output.mkdir()
    (output / "keep").write_text("existing")
    with pytest.raises(ValueError, match="new"):
        evaluation.evaluate(config, candidate, output)
    assert (output / "keep").read_text() == "existing"
    link = candidate.parent / "link.py"
    link.symlink_to(candidate)
    with pytest.raises(ValueError, match="regular"):
        evaluation.prepare_evaluation(config, link, output.parent / "unused")


def test_local_fixture_receipt_has_hashes_bounded_logs_and_no_secret_env(evaluation_inputs, monkeypatch):
    config, candidate, output, _ = evaluation_inputs
    monkeypatch.setenv("APP_SECRET", "must-not-reach-evaluator")
    monkeypatch.setattr(runtime, "MAX_LOG_BYTES", 64)
    receipt = evaluation.evaluate(config, candidate, output)
    assert receipt["status"] == "completed" and receipt["fitness"] == -4.25
    assert receipt["raw_score"] == 4.25 and receipt["evaluation_attempts"] == 1 and receipt["retries"] == 0
    assert receipt["candidate_sha256"] == digest(candidate) == digest(output / "input/program.py")
    assert receipt["native_result_sha256"] == digest(output / "native-output/native.json")
    assert json.loads((output / "native-output/native.json").read_text())["secret_present"] is False
    assert "must-not-reach-evaluator" not in (output / "request.json").read_text()
    assert (output / "stdout.log").stat().st_size == 64
    assert any("truncated" in warning for warning in receipt["warnings"])
    assert receipt["environment_locked"] is False
    assert json.loads((output / "receipt.json").read_text()) == receipt


@pytest.mark.parametrize("mutation", ["candidate_copy", "source"])
def test_mutation_before_launch_is_recorded_without_evaluation(evaluation_inputs, monkeypatch, mutation):
    config, candidate, output, _ = evaluation_inputs
    copyfile = evaluation.shutil.copyfile
    def mutate(source, destination):
        copied = copyfile(source, destination)
        if mutation == "candidate_copy":
            Path(destination).write_text("changed snapshot")
        else:
            (Path(config["tasks_dir"]) / "run.py").write_text("changed evaluator entrypoint")
        return copied
    monkeypatch.setattr(evaluation.shutil, "copyfile", mutate)
    receipt = evaluation.evaluate(config, candidate, output)
    assert receipt["status"] == "error" and receipt["evaluation_attempts"] == 0
    assert receipt["fitness"] is None
    assert json.loads((output / "receipt.json").read_text()) == receipt


@pytest.mark.parametrize("execution", [
    {"kind": "docker", "image": "python:latest", "python": "python"},
    {"kind": "docker", "image": "sha256:" + "a" * 64, "python": "/bin/sh"},
    {"kind": "docker", "image": "sha256:" + "a" * 64, "python": "python", "network": "host"},
    {"kind": "local_trusted", "python": "python"},
])
def test_unsafe_or_unpinned_execution_profiles_rejected(evaluation_inputs, execution):
    config, candidate, output, _ = evaluation_inputs
    with pytest.raises(ValueError):
        evaluation.prepare_evaluation(config | {"execution": execution}, candidate, output)


def fake_docker(monkeypatch, config, candidate, output, *, timeout=False, cleanup_failure=False, driver=b"cgroupfs 2\n"):
    """Emulate the Docker client only; no daemon or candidate is invoked."""
    calls = []
    stops = []
    prepared = evaluation.prepare_evaluation(config, candidate, output)
    class Process:
        pid = 99999999
        returncode = None
        def __init__(self, argv, **kwargs):
            calls.append((argv, kwargs))
            self.stdout, self.stderr = io.BytesIO(b"fixture stdout"), io.BytesIO()
            (output / "native-output/native.json").write_text(json.dumps(native_result(prepared)))
        def wait(self, timeout=None):
            if fail_timeout:
                raise subprocess.TimeoutExpired("controlled docker client", timeout)
            self.returncode = 0
            return 0
    fail_timeout = timeout
    def cleanup(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[:2] == ["docker", "info"]:
            return subprocess.CompletedProcess(argv, 0, driver, b"")
        return subprocess.CompletedProcess(argv, 1 if cleanup_failure else 0, b"", b"daemon denied cleanup" if cleanup_failure else b"")
    monkeypatch.setattr(evaluation, "subprocess", SimpleNamespace(Popen=Process, run=cleanup,
                        TimeoutExpired=subprocess.TimeoutExpired, SubprocessError=subprocess.SubprocessError,
                        DEVNULL=subprocess.DEVNULL, PIPE=subprocess.PIPE))
    monkeypatch.setattr(evaluation, "_stop", lambda process: stops.append(process.pid))
    return calls, stops


def test_docker_command_is_pinned_offline_resource_limited_and_cleaned(evaluation_inputs, monkeypatch):
    config, candidate, output, _ = evaluation_inputs
    image = "sha256:" + "a" * 64
    config["execution"] = {"kind": "docker", "image": image, "python": "python3"}
    calls, stops = fake_docker(monkeypatch, config, candidate, output)
    receipt = evaluation.evaluate(config, candidate, output)
    argv, options = calls[0]
    assert argv[:4] == ["docker", "run", "--rm", "--pull=never"]
    for flag, value in [("--network", "none"), ("--cpus", "1"), ("--memory", "2g"),
                        ("--pids-limit", "128"), ("--cap-drop", "ALL"), ("--security-opt", "no-new-privileges")]:
        assert argv[argv.index(flag) + 1] == value
    assert "--read-only" in argv and image in argv and "--privileged" not in argv
    mounts = [argv[i+1] for i, value in enumerate(argv) if value == "--mount"]
    assert len(mounts) == 3
    assert any("dst=/tasks,readonly" in value for value in mounts)
    assert any("dst=/candidate,readonly" in value for value in mounts)
    assert f"type=bind,src={output / 'native-output'},dst=/results" in mounts
    assert f"type=bind,src={output},dst=/results" not in mounts
    assert not any("docker.sock" in value for value in mounts)
    assert options["start_new_session"] is True and options["stdin"] == subprocess.DEVNULL
    assert calls[-1][0][:3] == ["docker", "rm", "--force"] and len(stops) == 1
    assert receipt["status"] == "completed" and receipt["environment_locked"] is True


def controlled_context(tmp_path, monkeypatch):
    ident = "c" * 32
    mount = tmp_path / "cgroup"
    parent = mount / "arena-workers" / ("arena-control-" + ident)
    parent.mkdir(parents=True)
    for name in ("cgroup.controllers", "cgroup.kill"):
        (parent / name).write_text("")
    membership = tmp_path / "self-cgroup"
    hierarchy = "/arena-workers/arena-control-" + ident
    membership.write_text("0::" + hierarchy + "/main\n")
    receipts = tmp_path / "runs" / ident / "artifacts/canonical-evaluations"
    monkeypatch.setattr(evaluation, "_CGROUP_MOUNT", mount)
    monkeypatch.setattr(evaluation, "_PROCESS_CGROUP", membership)
    monkeypatch.setenv("ARENA_EVALUATION_CGROUP_PARENT", str(parent))
    monkeypatch.setenv("ARENA_EVALUATION_RECEIPTS_DIR", str(receipts))
    monkeypatch.setenv("DOCKER_HOST", "unix:///run/arena-evaluator/docker.sock")
    return parent, membership, receipts, hierarchy, ident


def test_controlled_evaluation_joins_own_cgroup_and_keeps_proxy_on_cleanup(evaluation_inputs, monkeypatch, tmp_path):
    config, candidate, _, _ = evaluation_inputs
    _, _, receipts, hierarchy, ident = controlled_context(tmp_path, monkeypatch)
    config["execution"] = {"kind": "docker", "image": "sha256:" + "a" * 64,
                           "python": "python", "require_control_cgroup": True}
    output = receipts / ("e" * 32)
    calls, _ = fake_docker(monkeypatch, config, candidate, output)
    monkeypatch.setenv("OPENAI_API_KEY", "never-pass-to-docker")
    result = evaluation.evaluate(config, candidate, output)
    assert result["status"] == "completed"
    argv = next(command for command, _ in calls if command[:2] == ["docker", "run"])
    assert argv[argv.index("--cgroup-parent") + 1] == hierarchy
    assert "arena.evaluator=canonical-v1" in argv and "arena.control-run=" + ident in argv
    assert result["control"]["run_id"] == ident
    assert evaluation.receipt_root(config, tmp_path / "ignored") == receipts
    for _, options in calls:
        assert options["env"]["DOCKER_HOST"] == "unix:///run/arena-evaluator/docker.sock"
        assert "OPENAI_API_KEY" not in options["env"]
    assert calls[-1][0][:3] == ["docker", "rm", "--force"]


@pytest.mark.parametrize("damage", ["missing-parent", "foreign-membership", "prefix-lookalike", "foreign-receipts", "symlink", "systemd"])
def test_controlled_evaluation_fails_before_container_launch_if_admission_is_not_bound(evaluation_inputs, monkeypatch, tmp_path, damage):
    config, candidate, _, _ = evaluation_inputs
    parent, membership, receipts, hierarchy, ident = controlled_context(tmp_path, monkeypatch)
    config["execution"] = {"kind": "docker", "image": "sha256:" + "a" * 64,
                           "python": "python", "require_control_cgroup": True}
    output = receipts / ("e" * 32)
    calls, _ = fake_docker(monkeypatch, config, candidate, output, driver=b"systemd 2\n" if damage == "systemd" else b"cgroupfs 2\n")
    if damage == "missing-parent":
        monkeypatch.delenv("ARENA_EVALUATION_CGROUP_PARENT")
    elif damage == "foreign-membership":
        membership.write_text("0::/another-run/main\n")
    elif damage == "prefix-lookalike":
        membership.write_text("0::" + hierarchy + "-other/main\n")
    elif damage == "foreign-receipts":
        monkeypatch.setenv("ARENA_EVALUATION_RECEIPTS_DIR", str(tmp_path / "runs" / ("d" * 32) / "artifacts/canonical-evaluations"))
    elif damage == "symlink":
        link = parent.parent / ("arena-control-" + "d" * 32)
        link.symlink_to(parent, target_is_directory=True)
        monkeypatch.setenv("ARENA_EVALUATION_CGROUP_PARENT", str(link))
    result = evaluation.evaluate(config, candidate, output)
    assert result["status"] == "error" and result["evaluation_attempts"] == 0
    assert result["fitness"] is None
    assert not any(argv[:2] == ["docker", "run"] for argv, _ in calls)


def test_docker_timeout_and_failed_cleanup_still_write_receipt(evaluation_inputs, monkeypatch):
    config, candidate, output, _ = evaluation_inputs
    config["execution"] = {"kind": "docker", "image": "sha256:" + "b" * 64, "python": "python"}
    calls, stops = fake_docker(monkeypatch, config, candidate, output, timeout=True, cleanup_failure=True)
    receipt = evaluation.evaluate(config, candidate, output)
    assert receipt["status"] == "timeout" and receipt["fitness"] is None
    assert len(stops) == 1 and calls[-1][0][:3] == ["docker", "rm", "--force"]
    assert any("cleanup" in warning for warning in receipt["warnings"])
    assert json.loads((output / "receipt.json").read_text()) == receipt


def test_native_result_hash_identifies_exact_parsed_bytes(tmp_path, monkeypatch):
    path = tmp_path / "native.json"
    raw = b'{ "valid": true, "score": 4.25 }\n'
    path.write_bytes(raw)
    loads = evaluation.json.loads
    def replace_after_read(data, **kwargs):
        path.write_text('{"valid":false,"score":0}')
        return loads(data, **kwargs)
    monkeypatch.setattr(evaluation.json, "loads", replace_after_read)
    native, sha = evaluation._read_native_result(path)
    assert native == {"valid": True, "score": 4.25}
    assert sha == hashlib.sha256(raw).hexdigest() and sha != digest(path)


@pytest.mark.parametrize("content", [b'{"valid":false,"valid":true}', b'{"score":NaN}',
                                     b'{"nested":{"score":1,"score":2}}', b'x' * (4 * 1024 * 1024 + 1)])
def test_native_result_rejects_ambiguous_or_unbounded_json(tmp_path, content):
    path = tmp_path / "native.json"
    path.write_bytes(content)
    with pytest.raises(ValueError):
        evaluation._read_native_result(path)


def test_native_result_rejects_symlinks_and_fifo_without_blocking(tmp_path):
    target = tmp_path / "target.json"
    target.write_text("{}")
    link = tmp_path / "native.json"
    link.symlink_to(target)
    with pytest.raises(OSError):
        evaluation._read_native_result(link)
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="regular"):
        evaluation._read_native_result(fifo)


def test_native_result_rejects_mutation_during_read(tmp_path, monkeypatch):
    path = tmp_path / "native.json"
    path.write_text('{"valid":true}')
    read = evaluation.os.read
    mutated = False
    def mutate(descriptor, count):
        nonlocal mutated
        data = read(descriptor, count)
        if not mutated:
            mutated = True
            path.write_text('{"valid":false}')
        return data
    monkeypatch.setattr(evaluation.os, "read", mutate)
    with pytest.raises(ValueError, match="changed"):
        evaluation._read_native_result(path)
