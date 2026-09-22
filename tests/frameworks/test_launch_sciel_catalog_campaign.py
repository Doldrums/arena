"""Durable launch gates and real SQLite/file transactions without running research."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("launch_sciel_catalog_campaign",
    ROOT / "scripts/deployment/launch_sciel_catalog_campaign.py")
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    return path


def template(ident):
    return {"id": ident, "name": ident, "framework": "sciel-release", "profile": "native",
        "model": "gpt-5.5", "status": "ready", "blocked_reason": None, "containment": "cgroup-v2",
        "evaluation_concurrency_verified": True,
        "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
        "spec": {"schema": "arena.native-run/1", "framework": "sciel-release", "source_dir": "/private/source",
            "output_dir": "{output_dir}", "timeout_seconds": 3600, "request": {}}}


@pytest.fixture
def gate_fixture(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    source = {"id": "arena-tasks", "manifest_sha256": "a" * 64}
    tasks = ["pilot", "physics", "biology", "pending"]
    monkeypatch.setattr(launch, "eligible_task_ids", lambda _, role:
                        {"pilot", "physics"} if role == "base" else {"biology"})
    preflights = []
    for group, eligible in (("base", {"pilot", "physics"}), ("extended", {"biology"})):
        preflights.append(write(root / group / "manifest.json", {
            "schema": "arena.sciel-catalog-preflight/1", "group": group, "task_source": source,
            "finished_at": 123, "tasks": [{"task_id": task,
                "status": "seed_verified" if task in eligible else "seed_check_deferred"} for task in tasks]}))
    pilot_templates = write(root / "pilot/templates.json", [template("pilot-template")])
    inventory = write(root / "pilot/campaign-inventory.json", {
        "schema": "arena.sciel-catalog-campaign/1", "campaign": "pilot", "model": "gpt-5.5",
        "task_source": source, "tasks": [{"task_id": "pilot", "template_id": "pilot-template"}]})
    status = write(root / "pilot-status.json", {"schema": "arena.sciel-catalog-admission/1",
        "campaign": "pilot", "state": "completed", "models": ["gpt-5.5"], "planned": 1,
        "control_revision": "b" * 64, "templates_sha256": launch.digest(pilot_templates.read_bytes()),
        "batches": [{"batch_id": "pilot-b001", "native_issues": {}, "runs": [
            {"id": "1" * 32, "template": "pilot-template", "state": "completed", "model": "gpt-5.5"}]}]})
    return SimpleNamespace(preflight=preflights, pilot_inventory=inventory, pilot_status=status,
        model="gpt-5.5", tasks_root=root / "tasks", config_destination=root / "configs/new",
        native_tasks=root / "native/new", deployment=root / "deployment.json", approval=root / "approved.json",
        campaign="new-campaign", python=Path("/usr/bin/python3"), worker_gid=os.getgid())


def test_group_less_legacy_base_requires_explicit_role_and_exact_eligibility(gate_fixture):
    args = gate_fixture
    base = json.loads(args.preflight[0].read_text())
    del base["group"]
    write(args.preflight[0], base)
    with pytest.raises(ValueError, match="Exactly one base"):
        launch.gate_inputs(args)
    args.base_preflight = args.preflight[0]
    assert launch.gate_inputs(args)["manifests"][0]["group"] == "base"
    assert "group" not in json.loads(args.preflight[0].read_text())
    base["tasks"][2]["status"] = "seed_verified"
    write(args.preflight[0], base)
    with pytest.raises(ValueError, match="eligible task IDs"):
        launch.gate_inputs(args)


def test_explicit_conformance_gate_reserves_active_pilot_without_claiming_completion(gate_fixture, monkeypatch):
    args = gate_fixture
    status = json.loads(args.pilot_status.read_text())
    status["state"] = "running"
    status["batches"][0]["runs"][0]["state"] = "running"
    write(args.pilot_status, status)
    assert launch.gate_inputs(args) is None
    args.pilot_conformance = write(args.pilot_status.parent / "conformance.json", {"test": True})
    proof = {"run_ids": ["1" * 32], "task_ids": ["pilot"], "sha256": "c" * 64}
    monkeypatch.setattr(launch, "load_conformance", lambda *args: proof)
    gates = launch.gate_inputs(args)
    assert gates["excluded"] == ["pilot"] and gates["conformance"] == proof
    assert str(args.pilot_status) not in gates["input_sha256"]
    proof["run_ids"] = ["2" * 32]
    with pytest.raises(ValueError, match="every exact pilot"):
        launch.gate_inputs(args)


def test_launch_waits_for_both_finished_preflights_and_completed_pilot(gate_fixture):
    args = gate_fixture
    assert launch.gate_inputs(args)["excluded"] == ["pilot"]
    base = json.loads(args.preflight[0].read_text())
    del base["finished_at"]
    write(args.preflight[0], base)
    assert launch.gate_inputs(args) is None
    base["finished_at"] = 123
    write(args.preflight[0], base)
    status = json.loads(args.pilot_status.read_text())
    status["state"] = "running"
    write(args.pilot_status, status)
    assert launch.gate_inputs(args) is None
    status["state"] = "paused_native_evidence"
    write(args.pilot_status, status)
    with pytest.raises(ValueError, match="Pilot admission paused"):
        launch.gate_inputs(args)
    assert not args.config_destination.exists() and not args.native_tasks.exists()


def test_ready_preview_does_not_read_keys_prepare_or_call_control(gate_fixture, monkeypatch):
    args = gate_fixture
    root = args.pilot_status.parent
    def forbidden(*_, **__):
        pytest.fail("Preview must not open credentials, prepare or contact control")
    monkeypatch.setattr(launch.submit, "read_key", forbidden)
    monkeypatch.setattr(launch, "launch", forbidden)
    argv = ["--preflight", str(args.preflight[0]), "--preflight", str(args.preflight[1])]
    for name in ("tasks_root", "config_destination", "native_tasks", "deployment", "approval", "python",
                 "pilot_inventory", "pilot_status", "campaign", "model"):
        argv += ["--" + name.replace("_", "-"), str(getattr(args, name))]
    for name in ("control-config", "key-file", "admin-key-file", "status"):
        argv += ["--" + name, str(root / (name + ".json"))]
    assert launch.main(argv) == 0
    assert not args.config_destination.exists() and not args.native_tasks.exists()


@pytest.mark.parametrize("change", ["failed_run", "native_issue", "wrong_model", "edited_templates", "overlap"])
def test_launch_refuses_inconsistent_or_failed_evidence(gate_fixture, change):
    args = gate_fixture
    status = json.loads(args.pilot_status.read_text())
    if change == "failed_run":
        status["batches"][0]["runs"][0]["state"] = "failed"
    elif change == "native_issue":
        status["batches"][0]["native_issues"] = {"1" * 32: "native_research_stopped"}
    elif change == "wrong_model":
        status["models"] = ["other-model"]
    elif change == "edited_templates":
        write(args.pilot_inventory.parent / "templates.json", [template("changed")])
    else:
        extended = json.loads(args.preflight[1].read_text())
        extended["tasks"][0]["status"] = "seed_verified"
        write(args.preflight[1], extended)
    write(args.pilot_status, status)
    with pytest.raises(ValueError):
        launch.gate_inputs(args)


def test_research_order_uses_authoritative_domains_and_preserves_metrics():
    annotations = {key: {"domain_id": domain} for key, domain in
        {"packing": "mathematics-optimization", "heat": "physics", "oscillator": "physics",
         "kinetics": "chemistry-materials", "protein": "biology-health", "control": "robotics-control"}.items()}
    records = [{"task_id": key, "raw_score": -3, "metric": "energy", "protocol": "recreated"}
               for key in reversed(annotations)]
    ordered = launch.research_order(records, annotations)
    assert [row["task_id"] for row in ordered] == ["heat", "kinetics", "protein", "control", "packing", "oscillator"]
    assert all(row["raw_score"] == -3 and row["protocol"] == "recreated" for row in ordered)
    with pytest.raises(ValueError, match="authoritative"):
        launch.research_order([{"task_id": "unknown"}], annotations)


@pytest.fixture
def control_fixture(tmp_path):
    root = tmp_path.resolve()
    state = root / "state"
    state.mkdir(mode=0o700)
    db = sqlite3.connect(state / "queue.sqlite")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE runs(id TEXT,template TEXT,model TEXT,revision TEXT,state TEXT,held INTEGER,snapshot_sha256 TEXT)")
    db.commit()
    db.close()
    before = {"schema": "arena.control/1", "state_dir": str(state), "cgroup_root": "/sys/fs/cgroup/test",
        "limits": {"cpus": 16, "memory_mb": 32768, "evaluation_slots": 4, "max_active": 4,
            "max_queued": 64, "max_runs_per_key": 2000, "max_reserved_seconds_per_key": 10000000},
        "templates": [template("previous")]}
    candidate = {**before, "templates": [*before["templates"], template("new-template")]}
    path = write(root / "control.json", before)
    args = SimpleNamespace(control_config=path, config_destination=root / "prepared")
    write(args.config_destination / "templates.json", [template("new-template")])
    calls = []
    class Control:
        fail_reload = False
        def call(self, route, body=None):
            calls.append((route, body))
            current = json.loads(path.read_text())
            if route == "/api/control/reload" and self.fail_reload:
                self.fail_reload = False
                raise RuntimeError("inert reload failure")
            return {"revision": launch.digest(launch.submit.encoded(current)), "limits": current["limits"]}
    return args, before, candidate, Control(), calls


def test_idle_gate_serializes_all_owners_and_blocks_concurrent_admission(control_fixture):
    _, before, _, _, _ = control_fixture
    state = Path(before["state_dir"])
    with launch.idle_queue(state):
        db = sqlite3.connect(state / "queue.sqlite", timeout=0)
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            db.execute("INSERT INTO runs(state,held) VALUES ('queued',0)")
        db.close()
    db = sqlite3.connect(state / "queue.sqlite")
    db.execute("INSERT INTO runs(state,held) VALUES ('queued',0)")
    db.commit()
    db.close()
    with pytest.raises(ValueError, match="idle"):
        with launch.idle_queue(state):
            pytest.fail("A queued task must prohibit configuration replacement")


def test_sqlite_sidecars_open_as_database_owner_then_restore_operator(control_fixture, monkeypatch):
    _, before, _, _, _ = control_fixture
    state = Path(before["state_dir"])
    owner = (state / "queue.sqlite").stat().st_uid
    if owner == 0:
        pytest.skip("Non-root fixture owner exercises the privilege transition")
    identity = {"effective": 0}
    actual_connect = sqlite3.connect
    observations = []
    def connect(*args, **kwargs):
        observations.append(identity["effective"])
        assert identity["effective"] == owner
        return actual_connect(*args, **kwargs)
    monkeypatch.setattr(launch.os, "geteuid", lambda: identity["effective"])
    monkeypatch.setattr(launch.os, "seteuid", lambda uid: identity.update(effective=uid))
    monkeypatch.setattr(launch.sqlite3, "connect", connect)
    with launch.idle_queue(state):
        assert identity["effective"] == 0
    assert observations == [owner] and identity["effective"] == 0


def test_install_preserves_prior_templates_and_atomic_backup_then_reload(control_fixture):
    args, before, candidate, control, calls = control_fixture
    original = args.control_config.read_bytes()
    revision = launch.install_control(args, before, candidate, control, control)
    assert json.loads(args.control_config.read_text()) == candidate
    assert json.loads((args.config_destination / "control-backup.json").read_text()) == before
    assert (args.config_destination / "control-backup.json").read_bytes() == original
    assert args.control_config.stat().st_mode & 0o777 == 0o600
    assert revision == launch.digest(launch.submit.encoded(candidate))
    assert calls[0] == ("/api/control/reload", {})


def test_reload_failure_restores_previous_config_without_admission(control_fixture):
    args, before, candidate, control, calls = control_fixture
    original = args.control_config.read_bytes()
    control.fail_reload = True
    with pytest.raises(RuntimeError, match="reload failure"):
        launch.install_control(args, before, candidate, control, control)
    assert args.control_config.read_bytes() == original
    assert [route for route, _ in calls] == ["/api/control/reload", "/api/control/reload"]


def test_active_queue_and_invalid_config_never_replace_control(control_fixture):
    args, before, candidate, control, calls = control_fixture
    db = sqlite3.connect(Path(before["state_dir"]) / "queue.sqlite")
    db.execute("INSERT INTO runs(state,held) VALUES ('running',1)")
    db.commit()
    db.close()
    original = args.control_config.read_bytes()
    with pytest.raises(ValueError, match="idle"):
        launch.install_control(args, before, candidate, control, control)
    invalid = deepcopy(candidate)
    invalid["limits"]["max_active"] = 5
    with pytest.raises(ValueError, match="preserve"):
        launch.install_control(args, before, invalid, control, control)
    assert args.control_config.read_bytes() == original and calls == []


def test_only_exact_qualified_pilot_can_remain_active_during_additive_install(control_fixture):
    args, before, candidate, control, _ = control_fixture
    db = sqlite3.connect(Path(before["state_dir"]) / "queue.sqlite")
    db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?)", ("1" * 32, "pilot-template", "gpt-5.5", "a" * 64, "running", 1, "b" * 64))
    db.commit()
    allowed = {"1" * 32: {"template": "pilot-template", "model": "gpt-5.5", "revision": "a" * 64, "snapshot_sha256": "b" * 64}}
    with launch.idle_queue(Path(before["state_dir"]), allowed):
        pass
    launch.install_control(args, before, candidate, control, control, allowed)
    assert json.loads(args.control_config.read_text()) == candidate
    assert db.execute("SELECT state,held FROM runs").fetchone() == ("running", 1)
    write(args.control_config, before)
    db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?)", ("2" * 32, "other-template", "gpt-5.5", "a" * 64, "running", 1, "c" * 64))
    db.commit()
    with pytest.raises(ValueError, match="idle"):
        launch.install_control(args, before, candidate, control, control, allowed)
    db.execute("DELETE FROM runs WHERE id=?", ("2" * 32,))
    db.execute("UPDATE runs SET state='failed',held=0")
    db.commit()
    with pytest.raises(ValueError, match="identity or state"):
        with launch.idle_queue(Path(before["state_dir"]), allowed):
            pytest.fail("Failed pilot cannot authorize installation")
    db.close()


def test_preparation_excludes_pilot_and_combines_both_profiles_without_http(gate_fixture, monkeypatch):
    args = gate_fixture
    gates = launch.gate_inputs(args)
    prepared = []
    def inert_prepare(**kwargs):
        prepared.append(kwargs)
        assert kwargs["exclude_tasks"] == ["pilot"]
        group = kwargs["preflight_manifest"].parent.name
        target = "physics" if group == "base" else "biology"
        planned = template(target)
        write(kwargs["config_destination"] / "templates.json", [planned])
        write(kwargs["config_destination"] / "campaign-inventory.json", {
            "task_source": {"id": "arena-tasks"}, "tasks": [{"task_id": task,
                "status": "prepared" if task == target else "excluded" if task == "pilot" else "pending",
                "template_id": target if task == target else None, "preflight_status": "seed_verified",
                "protocol": "recreated", "metric": "energy"} for task in ("pilot", "physics", "biology", "pending")]})
        kwargs["native_tasks"].mkdir(parents=True)
    monkeypatch.setattr(launch.prepare, "prepare", inert_prepare)
    monkeypatch.setattr(launch, "get_insights", lambda: {"task_annotations": {
        "physics": {"domain_id": "physics"}, "biology": {"domain_id": "biology-health"}}})
    live = {"schema": "arena.control/1", "state_dir": "/private/state", "cgroup_root": "/sys/fs/cgroup/test",
        "limits": {"cpus": 16, "memory_mb": 32768, "evaluation_slots": 4, "max_active": 4,
            "max_queued": 64, "max_runs_per_key": 2000, "max_reserved_seconds_per_key": 10000000}, "templates": []}
    candidate = launch.prepare_all(args, gates, live)
    assert [row["id"] for row in candidate["templates"]] == ["physics", "biology"]
    inventory = json.loads((args.config_destination / "campaign-inventory.json").read_text())
    assert inventory["counts"] == {"pilot_completed": 1, "prepared": 2, "pending": 1}
    assert inventory["model_calls"] == 0 and len(prepared) == 2
    assert all(row["protocol"] == "recreated" and row["metric"] == "energy" for row in inventory["tasks"])
    assert args.config_destination.stat().st_mode & 0o777 == 0o750
    assert (args.config_destination / "templates.json").stat().st_mode & 0o777 == 0o640
