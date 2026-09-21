"""The native driver runs only controlled local children in these tests."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from arena.frameworks import runtime


def git(directory, *args):
    return subprocess.check_output(["git", "-C", str(directory), *args], text=True).strip()


@pytest.fixture
def native_spec(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init", "-q")
    git(source, "config", "user.name", "Fixture")
    git(source, "config", "user.email", "fixture@example.invalid")
    (source / "tracked.py").write_text("fixture = True\n")
    git(source, "add", ".")
    git(source, "commit", "-qm", "fixture")
    pin = git(source, "rev-parse", "HEAD")

    class FixtureAdapter:
        commit = pin

        def prepare(self, source_dir, request, output_dir):
            command = {"argv": [sys.executable, "-c", request.get("code", "print('controlled child')")],
                       "cwd": str(source_dir), "env": {}, "input_paths": request.get("input_paths", []),
                       "expected_artifacts": []}
            if request.get("workspace"):
                command.update(cwd=str(output_dir / "workspace/dgm"), workspace_copy=True,
                               workspace_inputs=request.get("workspace_inputs", []))
            return command

        def read_results(self, output):
            return {"schema": "arena.native-result/1", "framework": "fixture", "status": "missing",
                    "canonical_evaluation": False, "native": {}, "artifacts": [], "warnings": []}

    monkeypatch.setattr(runtime, "get_adapter", lambda name: FixtureAdapter())
    return {"schema": "arena.native-run/1", "framework": "fixture", "source_dir": str(source),
            "output_dir": str(tmp_path / "output"), "timeout_seconds": 10, "request": {}}


def test_plan_is_inert_pinned_and_does_not_serialize_environment_values(native_spec, tmp_path, monkeypatch):
    marker = tmp_path / "executed"
    native_spec["request"]["code"] = f"open({str(marker)!r}, 'w').write('bad')"
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-secret-never-in-plan")
    native_spec["environment_names"] = ["OPENAI_API_KEY"]
    plan = runtime.prepare_plan(native_spec)
    assert not marker.exists() and not Path(native_spec["output_dir"]).exists()
    assert plan["source"]["commit"] == git(native_spec["source_dir"], "rev-parse", "HEAD")
    assert plan["source"]["tree"] == git(native_spec["source_dir"], "rev-parse", "HEAD^{tree}")
    assert plan["environment_names"] == ["OPENAI_API_KEY"]
    assert "fixture-secret-never-in-plan" not in json.dumps(plan)
    unsigned = {key: value for key, value in plan.items() if key != "sha256"}
    assert plan["sha256"] == hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@pytest.mark.parametrize("mutation", ["tracked", "untracked", "assume_unchanged", "skip_worktree", "new_commit"])
def test_source_verification_rejects_real_checkout_changes(native_spec, mutation):
    source = Path(native_spec["source_dir"])
    if mutation == "untracked":
        (source / "extra.py").write_text("untracked")
    else:
        if mutation in ("assume_unchanged", "skip_worktree"):
            git(source, "update-index", "--" + mutation.replace("_", "-"), "tracked.py")
        (source / "tracked.py").write_text("changed = True\n")
        if mutation == "new_commit":
            git(source, "add", ".")
            git(source, "commit", "-qm", "different source")
    with pytest.raises(ValueError):
        runtime.prepare_plan(native_spec)
    assert not Path(native_spec["output_dir"]).exists()


def test_git_probes_ignore_redirecting_environment(native_spec, monkeypatch, tmp_path):
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "not-this-checkout"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "false-command")
    assert runtime.prepare_plan(native_spec)["source"]["commit"]


def test_readonly_operator_owned_source_uses_an_exact_git_trust_boundary(native_spec, monkeypatch):
    # Git's own test switch exercises cross-owner checks without requiring root
    # or changing file ownership in the test environment.
    environment = runtime._git_environment() | {"GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"}
    source = native_spec["source_dir"]
    baseline = subprocess.run(["git", "-C", source, "rev-parse", "--show-toplevel"],
                              env=environment, capture_output=True)
    if baseline.returncode == 0:
        pytest.skip("Installed Git does not expose its different-owner test hook")
    monkeypatch.setattr(runtime, "_git_environment", lambda: environment)
    assert runtime.prepare_plan(native_spec)["source"]["commit"]
    # Trusting ownership never exempts the pin or clean-tree requirements.
    (Path(source) / "tracked.py").write_text("changed = True\n")
    with pytest.raises(ValueError, match="modifications"):
        runtime.prepare_plan(native_spec)


def test_outputs_are_never_overwritten_or_nested_in_source(native_spec, tmp_path):
    output = Path(native_spec["output_dir"])
    output.mkdir()
    sentinel = output / "keep"
    sentinel.write_text("preserved")
    with pytest.raises(ValueError, match="new"):
        runtime.run(native_spec)
    assert sentinel.read_text() == "preserved"
    for forbidden in (Path(native_spec["source_dir"]) / "results", tmp_path):
        with pytest.raises(ValueError):
            runtime.prepare_plan(native_spec | {"output_dir": str(forbidden)})
    link = tmp_path / "dangling-output"
    link.symlink_to(tmp_path / "not-created")
    with pytest.raises(ValueError, match="symlink"):
        runtime.prepare_plan(native_spec | {"output_dir": str(link)})


def test_only_requested_secrets_reach_child_and_logs_are_bounded(native_spec, monkeypatch):
    monkeypatch.setenv("APP_SECRET", "present-only-at-runtime")
    monkeypatch.setenv("OTHER_SECRET", "must-not-pass")
    monkeypatch.setattr(runtime, "MAX_LOG_BYTES", 128)
    native_spec["environment_names"] = ["APP_SECRET"]
    native_spec["request"]["code"] = (
        "import os,sys; print(os.getenv('APP_SECRET') is not None, os.getenv('OTHER_SECRET') is None, flush=True);"
        "sys.stdout.write('x'*100000);sys.stderr.write('y'*100000)"
    )
    receipt = runtime.run(native_spec)
    metadata = Path(native_spec["output_dir"]) / ".arena"
    assert receipt["status"] == "process_completed" and receipt["canonical_evaluation"] is False
    assert (metadata / "stdout.log").read_text().startswith("True True")
    assert (metadata / "stdout.log").stat().st_size == (metadata / "stderr.log").stat().st_size == 128
    assert len([warning for warning in receipt["warnings"] if "truncated" in warning]) == 2
    assert "present-only-at-runtime" not in (metadata / "plan.json").read_text()
    assert (metadata / "plan.json").stat().st_mode & 0o777 == 0o600


def test_short_native_log_lines_are_visible_while_process_pipe_remains_open(tmp_path):
    reader, writer = os.pipe()
    log = tmp_path / "live.log"
    capture = runtime._Capture(os.fdopen(reader, "rb"), log)
    capture.start()
    try:
        os.write(writer, b"a live diagnostic\n")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if log.exists() and log.read_bytes() == b"a live diagnostic\n":
                break
            time.sleep(0.01)
        assert capture.is_alive(), "The producer pipe should still be open"
        assert log.read_bytes() == b"a live diagnostic\n"
    finally:
        os.close(writer)
        capture.join(timeout=5)
    assert not capture.is_alive()


def test_changed_explicit_input_before_launch_produces_failure_receipt(native_spec, tmp_path, monkeypatch):
    data = tmp_path / "config.txt"
    data.write_text("planned")
    native_spec["request"]["input_paths"] = [str(data)]
    monkeypatch.setattr(runtime, "_stage_workspace", lambda plan: data.write_text("changed"))
    receipt = runtime.run(native_spec)
    assert receipt["status"] == "launch_failed" and receipt["started_at"] is None
    assert (Path(native_spec["output_dir"]) / ".arena/receipt.json").is_file()


def test_workspace_stages_only_declared_inputs_without_mutating_original(native_spec, tmp_path):
    data = tmp_path / "dataset"
    data.mkdir()
    (data / "example.json").write_text('{"fixture":true}')
    native_spec["request"].update(workspace=True, input_paths=[str(data)],
                                  workspace_inputs=[{"source": str(data), "destination": "prepared/data"}],
                                  code="from pathlib import Path; assert Path('prepared/data/example.json').is_file()")
    receipt = runtime.run(native_spec)
    workspace = Path(native_spec["output_dir"]) / "workspace/dgm"
    assert receipt["status"] == "process_completed"
    assert (workspace / "prepared/data/example.json").read_bytes() == (data / "example.json").read_bytes()
    assert not (Path(native_spec["source_dir"]) / "prepared").exists()
    assert git(native_spec["source_dir"], "status", "--porcelain") == ""


@pytest.mark.parametrize("destination", ["tracked.py", "../outside", ".git/config", "/absolute"])
def test_workspace_inputs_cannot_overwrite_or_escape(native_spec, tmp_path, destination):
    data = tmp_path / "data.txt"
    data.write_text("fixture")
    native_spec["request"].update(workspace=True, input_paths=[str(data)],
                                  workspace_inputs=[{"source": str(data), "destination": destination}])
    receipt = runtime.run(native_spec)
    assert receipt["status"] == "launch_failed" and receipt["started_at"] is None


def test_fingerprints_reject_links_and_enforce_limits(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    (data / "a").write_bytes(b"a" * 10)
    (data / "link").symlink_to(data / "a")
    with pytest.raises(ValueError, match="symlinks"):
        runtime.fingerprint_inputs([str(data)])
    (data / "link").unlink()
    monkeypatch.setattr(runtime, "MAX_INPUT_BYTES", 9)
    with pytest.raises(ValueError, match="scan limit"):
        runtime.fingerprint_inputs([str(data)])


@pytest.mark.skipif(os.name != "posix", reason="driver requires POSIX groups")
def test_timeout_terminates_native_child_process_group(native_spec, tmp_path):
    heartbeat = tmp_path / "heartbeat"
    child = f"import time;from pathlib import Path;p=Path({str(heartbeat)!r});\nwhile True:\n p.write_text(str(time.time_ns()));time.sleep(.03)"
    native_spec["timeout_seconds"] = 1
    native_spec["request"]["code"] = f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',{child!r}]);time.sleep(30)"
    receipt = runtime.run(native_spec)
    assert receipt["status"] == "timed_out" and heartbeat.is_file()
    before = heartbeat.read_text()
    time.sleep(0.15)
    assert heartbeat.read_text() == before
