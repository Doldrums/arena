"""Source-recipe and inert native-driver tests; no upstream code is imported."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
from types import SimpleNamespace

import pytest

from arena.frameworks.recipes import RecipeAdapter, validate_recipe
from arena.frameworks.drivers import agentic_optimization, godel_agent, meta_harness


ROOT = Path(__file__).resolve().parents[2]
DOCUMENT = json.loads((ROOT / "registry/framework-recipes/agent-systems.json").read_text())
RECIPES = {r["id"]: r for r in DOCUMENT["recipes"]}
PAIRS = [(r["id"], p["id"]) for r in DOCUMENT["recipes"] for p in r["profiles"]]


def test_complete_requested_coverage_and_honest_artifact_status():
    expected = set("adas aflow agentsquare ael-harness ahe darwinian-evolver evoskill evoflow g-del-agent gea hsi hyperagents limen mce meta-harness meta-ttl omni-epic sica agentic-optimization aevo".split())
    assert {p for r in RECIPES.values() for p in r["participant_ids"]} == expected
    assert DOCUMENT["schema"] == "arena.framework-recipes/1"
    assert len(RECIPES) == 21 and len(PAIRS) == 28
    for recipe in RECIPES.values():
        validate_recipe(recipe)
    assert RECIPES["meta-harness"]["status"] == "artifact_only"
    assert RECIPES["evoflow"]["status"] == "blocked"
    assert RECIPES["evoflow"]["profiles"] == []
    assert RECIPES["evoflow"]["repository"] is None
    assert RECIPES["aevo"]["status"] == "blocked" and RECIPES["aevo"]["profiles"] == []
    assert set(RECIPES["aevo"]["evidence"]) == {"LICENSE", "README.md"}
    assert RECIPES["mce"]["repository"]["commit"] != RECIPES["mce-artifact"]["repository"]["commit"]
    assert RECIPES["hsi"]["profiles"][0]["remove_files"] == [".env"]
    assert all(not any(Path(path).name in {".env", "key.env"} for path in r["evidence"]) for r in RECIPES.values())


def _fixture_source(tmp_path, recipe):
    recipe = deepcopy(recipe)
    source = tmp_path / "source"
    source.mkdir()
    names = set(recipe["evidence"])
    for profile in recipe["profiles"]:
        names.update(profile["required_files"])
        (source / profile["cwd"]).mkdir(parents=True, exist_ok=True)
    for name in names:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("raise AssertionError('Planning must not execute source')\n" if path.suffix == ".py" else "inert fixture\n")
    recipe["evidence"] = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in recipe["evidence"]}
    return recipe, source


@pytest.mark.parametrize(("recipe_id", "profile_id"), PAIRS)
def test_every_native_profile_plans_without_loading_source(tmp_path, recipe_id, profile_id):
    recipe, source = _fixture_source(tmp_path, RECIPES[recipe_id])
    profile = next(p for p in recipe["profiles"] if p["id"] == profile_id)
    output = tmp_path / "output"
    command = RecipeAdapter(recipe).prepare(source, {"python": sys.executable, "profile": profile_id, "arguments": []}, output)
    workspace = output / "workspace" / recipe_id
    assert command["cwd"] == str(workspace / profile["cwd"])
    assert command["argv"][0] == sys.executable
    assert command["env"]["PYTHONPATH"].split(os.pathsep)[:2] == [str(workspace), str(workspace / "src")]
    assert command["evaluation"]["mode"] == "native"
    assert not output.exists()
    if profile["output"]:
        assert command["argv"][-2:] == [profile["output"]["flag"], str(output / profile["output"]["path"])]
        with pytest.raises(ValueError, match="fixes this option"):
            RecipeAdapter(recipe).prepare(source, {"python": sys.executable, "profile": profile_id,
                                                   "arguments": [profile["output"]["flag"], "/escape"]}, output)


@pytest.mark.parametrize("recipe_id", [r["id"] for r in DOCUMENT["recipes"] if r["repository"]])
def test_source_evidence_matches_available_exact_pinned_checkout(recipe_id):
    """Offline source conformance when the reviewed checkouts are present."""
    source = Path("/tmp/arena-framework-sources") / recipe_id
    if not source.is_dir():
        pytest.skip("Reviewed external checkout is not installed in this test environment")
    for name, digest in RECIPES[recipe_id]["evidence"].items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == digest, name


@pytest.fixture
def godel_workspace(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("# inert source\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "inert-test-value")
    return tmp_path


@pytest.mark.parametrize("outcome", ["success", "error", "signal"])
def test_godel_secret_file_is_private_and_removed_on_all_handled_exits(godel_workspace, monkeypatch, outcome):
    key = godel_workspace / "src/key.env"
    original_signal = signal.getsignal(signal.SIGTERM)

    def run(path, *, run_name):
        assert path == str(godel_workspace / "src/main.py") and run_name == "__main__"
        assert key.read_text() == "inert-test-value"
        assert key.stat().st_mode & 0o777 == 0o600
        if outcome == "error":
            raise RuntimeError("inert native failure")
        if outcome == "signal":
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)

    monkeypatch.setattr(godel_agent.runpy, "run_path", run)
    if outcome == "success":
        assert godel_agent.main([]) == 0
    else:
        with pytest.raises(RuntimeError if outcome == "error" else SystemExit):
            godel_agent.main([])
    assert not key.exists()
    assert signal.getsignal(signal.SIGTERM) == original_signal


def test_godel_never_replaces_existing_credential_file(godel_workspace, monkeypatch):
    key = godel_workspace / "src/key.env"
    key.write_text("existing fixture")
    with pytest.raises(FileExistsError):
        godel_agent.main([])
    assert key.read_text() == "existing fixture"
    key.unlink()
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(ValueError, match="explicitly provided"):
        godel_agent.main([])
    assert not key.exists()


def test_harbor_driver_uses_installed_console_contract(monkeypatch):
    calls = []
    entry = SimpleNamespace(load=lambda: lambda: calls.append("native-harbor-cli"))
    monkeypatch.setattr(meta_harness, "entry_points", lambda **kwargs: [entry] if kwargs == {"group": "console_scripts", "name": "harbor"} else [])
    meta_harness.main()
    assert calls == ["native-harbor-cli"]
    monkeypatch.setattr(meta_harness, "entry_points", lambda **kwargs: [])
    with pytest.raises(RuntimeError, match="Exactly one"):
        meta_harness.main()


@pytest.fixture
def agentic_native(monkeypatch):
    calls = []
    statuses = [{"status": "running"}, {"status": "finished", "returncode": 0}]
    control = SimpleNamespace(update_experiment_status=lambda *args: calls.append(("stop", args)),
                              list_sessions=lambda **kwargs: [])
    workers = SimpleNamespace(worker_status=lambda ident: statuses.pop(0) if statuses else None,
                              close=lambda: calls.append(("close",)))

    def post(path, *, json):
        calls.append(("post", path, json))
        value = {"experiment": {"experiment_id": "exp-fixture"}, "assignments": [{"assignment_id": "assignment-fixture"}]} if path == "/api/v1/experiments" else {"session_id": "session-fixture"}
        return SimpleNamespace(status_code=201, get_json=lambda: value)

    app = SimpleNamespace(config={"AO_CONTEXT": SimpleNamespace(control=control, workers=workers)},
                          test_client=lambda: SimpleNamespace(post=post))
    server = SimpleNamespace(server_port=12345, serve_forever=lambda: None,
                             shutdown=lambda: calls.append(("shutdown",)), server_close=lambda: calls.append(("server-close",)))
    def make_server(host, port, native_app, *, threaded):
        assert (host, port, native_app, threaded) == ("127.0.0.1", 0, app, True)
        return server
    monkeypatch.setattr(agentic_optimization, "_native_components", lambda: (lambda **kwargs: app, make_server))
    monkeypatch.setattr(agentic_optimization.time, "sleep", lambda _: None)
    return SimpleNamespace(calls=calls, statuses=statuses, control=control)


def _agentic_args(tmp_path):
    return ["--task-id", "circle_packing_26", "--max-evaluator-runs", "3", "--worker-seconds", "5",
            "--wall-seconds", "10", "--state-root", str(tmp_path / "native")]


def test_agentic_driver_launches_real_native_assignment_contract_and_cleans_up(agentic_native, tmp_path):
    assert agentic_optimization.main(_agentic_args(tmp_path)) == 0
    posts = [c for c in agentic_native.calls if c[0] == "post"]
    assert posts[0][1:] == ("/api/v1/experiments", {"task_id": "circle_packing_26", "mode": "local",
                                               "assignment_count": 1, "worker_backend": "codex-local",
                                               "budget": {"total_evaluator_runs": 3}})
    assert posts[1][1] == "/api/v1/assignments/assignment-fixture/start-local"
    assert posts[1][2] == {"api_url": "http://127.0.0.1:12345", "max_turn_wall_time_s": 5}
    assert ("stop", ("exp-fixture", "stopped")) in agentic_native.calls
    assert agentic_native.calls[-3:] == [("close",), ("shutdown",), ("server-close",)]
    result = json.loads((tmp_path / "native/arena-native.json").read_text())
    assert result["canonical_evaluation"] is False and result["termination"] == "native_worker_terminal"


def test_agentic_missing_terminal_evidence_never_becomes_success(agentic_native, tmp_path):
    agentic_native.statuses.clear()
    assert agentic_optimization.main(_agentic_args(tmp_path)) == 1


def test_agentic_wall_timeout_stops_native_children(agentic_native, tmp_path, monkeypatch):
    ticks = iter([0, 11])
    monkeypatch.setattr(agentic_optimization.time, "monotonic", lambda: next(ticks))
    assert agentic_optimization.main(_agentic_args(tmp_path)) == 124
    assert ("stop", ("exp-fixture", "stopped")) in agentic_native.calls
    assert json.loads((tmp_path / "native/arena-native.json").read_text())["termination"] == "wall_timeout"
