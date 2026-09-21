import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import pytest

from arena import control, control_types
from arena.server import DashboardServer
from control_helpers import config_write, http, principal, request, service, submit


def test_keys_hashed_revocable_and_private(service):
    user, key = principal(service)
    with service._db() as db:
        row = dict(db.execute("SELECT * FROM keys").fetchone())
    assert row["token_hash"] == hashlib.sha256(key["token"].encode()).hexdigest()
    assert key["token"] not in json.dumps(row)
    assert service.db_path.stat().st_mode & 0o077 == 0
    assert service.state_dir.stat().st_mode & 0o077 == 0
    service.revoke_key(key["id"])
    with pytest.raises(control.ControlError, match="Invalid bearer"):
        service.authenticate("Bearer " + key["token"])
    with pytest.raises(control.ControlError, match="revoked"):
        submit(service, user)


@pytest.mark.parametrize("header", [None, "", "Basic whatever", "Bearer wrong", "Bearer " + "x" * 300])
def test_authentication_fails_closed(service, header):
    with pytest.raises(control.ControlError) as caught:
        service.authenticate(header)
    assert caught.value.status == 401


def test_scopes_ownership_and_readonly_shared_overview(service):
    alice, _ = principal(service)
    bob, _ = principal(service, "bob")
    reader, _ = principal(service, "reader", ("read",))
    admin, _ = principal(service, "admin", ("admin",))
    run = submit(service, alice)
    assert service.queue(reader)["runs"][0]["id"] == run["id"]
    for operation in (lambda: submit(service, reader), lambda: service.cancel(reader, run["id"])):
        with pytest.raises(control.ControlError) as caught:
            operation()
        assert caught.value.status == 403
    for operation in (lambda: service.detail(bob, run["id"]), lambda: service.logs(bob, run["id"]), lambda: service.cancel(bob, run["id"])):
        with pytest.raises(control.ControlError) as caught:
            operation()
        assert caught.value.status == 404
    assert service.detail(admin, run["id"])["run"]["owner"] == "alice"
    assert service.cancel(admin, run["id"])["run"]["state"] == "cancelled"


def test_results_are_owner_scoped_and_do_not_submit_or_launch(service):
    from arena.results import results
    alice, _ = principal(service)
    bob, _ = principal(service, "bob")
    admin, _ = principal(service, "admin", ("admin",))
    no_read, _ = principal(service, "submitter", ("submit",))
    run = submit(service, alice)
    before = service.queue(admin)
    assert [row['id'] for row in results(service, alice)['runs']] == [run['id']]
    assert results(service, bob)['runs'] == []
    assert results(service, admin)['total'] == 1
    with pytest.raises(control.ControlError) as caught:
        results(service, no_read)
    assert caught.value.status == 403
    assert service.queue(admin) == before


def test_idempotency_is_atomic_and_cannot_rebind(service):
    user, _ = principal(service)
    def enqueue(_):
        return submit(service, user, label="Experiment", batch_id="matrix", idempotency_key="cell-1")["id"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        identifiers = list(pool.map(enqueue, range(12)))
    assert len(set(identifiers)) == 1
    assert service.queue(user)["total"] == 1
    with pytest.raises(control.ControlError) as caught:
        submit(service, user, label="Changed", batch_id="matrix", idempotency_key="cell-1")
    assert caught.value.status == 409


def test_no_caller_native_spec_or_model_override(service):
    user, _ = principal(service)
    with pytest.raises(control.ControlError):
        submit(service, user, request={"arguments": ["--workers", "999"]})
    with pytest.raises(control.ControlError, match="mismatched model"):
        service.submit(user, {"schema": "arena.control-submit/1", "template": "fixture", "model": "expensive-model"})


def test_resources_reserved_atomically_across_workers(service):
    user, _ = principal(service)
    for _ in range(8):
        submit(service, user)
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(lambda n: service.claim("worker-" + str(n)), range(8)))
    claimed = [row for row in rows if row]
    assert len(claimed) == 2  # Eight evaluation slots, four per native run.
    overview = service.queue(user)
    assert overview["resources"]["used"] == {"active": 2, "cpus": 4, "memory_mb": 2048, "evaluation_slots": 8}
    row = claimed[0]
    service.finish(row["id"], row["lease_owner"], "completed")
    assert service.claim("worker-next") is not None


@pytest.mark.parametrize("capacity,value,expected", [("cpus", 2, 1), ("memory_mb", 1024, 1), ("max_active", 1, 1)])
def test_each_resource_cap_is_enforced(service, capacity, value, expected):
    config_write(service, lambda config: config["limits"].update({capacity: value}))
    service.reload()
    user, _ = principal(service)
    for _ in range(3):
        submit(service, user)
    assert sum(service.claim("worker-" + str(n)) is not None for n in range(3)) == expected


def test_queue_and_key_count_and_runtime_budgets(service):
    user, _ = principal(service, max_runs=1)
    submit(service, user)
    with pytest.raises(control.ControlError) as caught:
        submit(service, user)
    assert caught.value.status == 429
    other, _ = principal(service, "budget", max_seconds=59)
    with pytest.raises(control.ControlError, match="budget"):
        submit(service, other)
    config_write(service, lambda config: config["limits"].update(max_queued=1))
    service.reload()
    other, _ = principal(service, "queue")
    with pytest.raises(control.ControlError, match="capacity"):
        submit(service, other)


def test_blocked_admin_records_are_real_nonexecution_states(service):
    def blocked(config):
        config["templates"][0].update(status="blocked", blocked_reason="GPU prerequisite unavailable.", spec=None, evaluation_concurrency_verified=False)
    config_write(service, blocked)
    service.reload()
    user, _ = principal(service)
    with pytest.raises(control.ControlError) as caught:
        submit(service, user)
    assert caught.value.status == 403
    admin, _ = principal(service, "admin", ("admin",))
    run = submit(service, admin)
    assert run["state"] == "blocked"
    assert run["reason"] == "GPU prerequisite unavailable."
    assert run["resources_reserved"] is False
    assert service.claim("worker") is None


def test_reload_changes_future_templates_not_queued_snapshots(service):
    user, _ = principal(service)
    run = submit(service, user)
    revision = service.revision
    config_write(service, lambda config: config["templates"][0]["spec"].update(timeout_seconds=120))
    assert service.reload() != revision
    row = service.claim("worker")
    assert row["id"] == run["id"]
    assert service.snapshot(row)["template"]["spec"]["timeout_seconds"] == 60
    next_run = submit(service, user)
    with service._db() as db:
        assert service._get(db, next_run["id"])["timeout_seconds"] == 120
    config_write(service, lambda config: config.update(state_dir="/other/private"))
    with pytest.raises(control.ControlError, match="cannot change"):
        service.reload()


def test_snapshot_tampering_prevents_execution(service):
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("worker")
    (service.runs_dir / run["id"] / "snapshot.json").write_text("{}")
    with pytest.raises(control.ControlError, match="changed"):
        service.snapshot(row)


def test_public_views_do_not_publish_specs_private_paths_or_key_hashes(service):
    user, key = principal(service)
    run = submit(service, user)
    rendered = json.dumps([service.queue(user), service.detail(user, run["id"]), service.templates(user)])
    for forbidden in (str(service.state_dir), "/fixture/source", sys.executable, key["token"], "OPENAI_API_KEY", "token_hash", "snapshot_sha256"):
        assert forbidden not in rendered
    with service._db() as db:
        raw_row = dict(service._get(db, run["id"]))
    assert "spec" not in raw_row
    assert "request" not in raw_row


@pytest.mark.parametrize("change", [
    lambda c: c["limits"].update(evaluation_slots=33),
    lambda c: c["templates"][0].update(evaluation_concurrency_verified=False),
    lambda c: c["templates"][0]["resources"].update(evaluation_slots=9),
    lambda c: c["templates"][0]["spec"]["request"].update(api_key="value"),
    lambda c: c["templates"][0]["spec"]["request"].update(env={"OPENAI_API_KEY": "value"}),
    lambda c: c["templates"][0]["spec"]["request"].update(code="print(1)"),
    lambda c: c["templates"][0]["spec"]["request"].update(arguments=["--api-key", "value"]),
    lambda c: c["templates"][0]["spec"].update(output_dir="/operator/shared"),
])
def test_config_refuses_unbounded_or_secret_bearing_templates(service, change):
    config = copy.deepcopy(service.config)
    change(config)
    with pytest.raises(control.ControlError):
        control.validate_config(config)


def test_private_configuration_required_and_duplicate_fields_rejected(service):
    service.config_path.chmod(0o644)
    with pytest.raises(control.ControlError, match="0600"):
        service.reload()
    with pytest.raises(control.ControlError, match="Duplicate"):
        control_types._decode('{"a":1,"a":2}')


def test_reserved_control_environment_names_are_not_credential_values(service):
    config = copy.deepcopy(service.config)
    config["templates"][0]["spec"]["environment_names"] = ["OPENAI_API_KEY", "ARENA_EVALUATION_CGROUP_PARENT", "ARENA_EVALUATION_RECEIPTS_DIR", "ARENA_CONTROL_RUN_ID"]
    assert control.validate_config(config) is config
    config["templates"][0]["spec"]["environment_names"].append("arena_this-is-a-bearer-value-123456789")
    with pytest.raises(control.ControlError, match="variable names"):
        control.validate_config(config)


def test_http_same_port_authentication_submission_read_and_cancel(service, http):
    user, key = principal(service)
    assert request(http + "/api/queue")[0] == 401
    assert request(http + "/api/control/templates")[0] == 401
    assert request(http + "/api/health")[1]["mode"] == "private_control"
    assert request(http + "/api/control/templates", token=key["token"])[1]["templates"][0]["id"] == "fixture"
    code, value = request(http + "/api/queue", token=key["token"], body={"schema": "arena.control-submit/1", "template": "fixture", "model": "fixture-model"})
    assert code == 200
    run_id = value["run"]["id"]
    assert request(http + "/api/queue/" + run_id, token=key["token"])[1]["run"]["state"] == "queued"
    assert request(http + "/api/queue/" + run_id + "/logs", token=key["token"])[1]["policy"] == "safe_control_events"
    assert request(http + "/api/queue/" + run_id + "/cancel", token=key["token"], body={})[1]["run"]["state"] == "cancelled"
    assert request(http + "/api/runs", token=key["token"], body={})[0] == 404


def test_results_http_requires_auth_and_preserves_owner_boundaries(service, http):
    alice, alice_key = principal(service)
    _, bob_key = principal(service, 'bob')
    run = submit(service, alice)
    assert request(http + '/api/control/results')[0] == 401
    code, value = request(http + '/api/control/results', token=alice_key['token'])
    assert code == 200 and value['schema'] == 'arena.results/1'
    assert [row['id'] for row in value['runs']] == [run['id']]
    assert request(http + '/api/control/results', token=bob_key['token'])[1]['runs'] == []
    assert request(http + '/api/control/results', token=alice_key['token'], body={})[0] == 404


def test_control_server_refuses_nonloopback_binding(service):
    with pytest.raises(ValueError, match="loopback"):
        DashboardServer(("0.0.0.0", 0), [], control=service)


def test_sample_configuration_is_blocked_and_valid():
    path = Path(__file__).resolve().parents[1] / "examples/control.json"
    config = control.validate_config(json.loads(path.read_text()))
    assert config["limits"]["evaluation_slots"] == 32
    assert all(item["status"] == "blocked" for item in config["templates"])


def test_python_module_serve_preserves_http_error_classes(service):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(Path(control.__file__).resolve().parents[1])
    process = subprocess.Popen([sys.executable, "-m", "arena.control", "serve", "--config", str(service.config_path), "--port", str(port)],
                               env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 5
        while True:
            try:
                code, body = request(f"http://127.0.0.1:{port}/api/queue")
                break
            except OSError:
                if time.monotonic() > deadline or process.poll() is not None:
                    raise
                time.sleep(0.025)
        assert code == 401 and body["error"] == "A bearer key is required"
        reader, key = principal(service, "reader", ("read",))
        code, _ = request(f"http://127.0.0.1:{port}/api/queue", token=key["token"], body={"schema": "arena.control-submit/1", "template": "fixture", "model": "fixture-model"})
        assert code == 403
    finally:
        process.terminate()
        process.wait(timeout=5)
