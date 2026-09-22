"""No uncertain daemon outcome may release or double-book the GPU."""
from copy import deepcopy
import json
import os
from pathlib import Path
import select
import subprocess
import sys

import pytest

from arena import evaluator_execution as execution, evaluator_gpu as gpu
from arena import evaluator_gpu_leases as leases, evaluator_policy as policy
from evaluator_gpu_helpers import IDENT, NAME, RUN, abandon, lease_root, prepared, setup


def instance(prepared, monkeypatch):
    monkeypatch.setattr(execution.os, "chown", lambda *args: None)
    return execution.Proxy(prepared[0])


def create(proxy, body, *, status=201, failure=False):
    def request(method, path, body=None, **kwargs):
        assert method == "POST"
        payload = json.loads(body)
        metadata = json.loads((leases.STATE_ROOT / leases.RECORD_NAME).read_text())
        assert metadata["id"] is None and metadata["run"] == RUN and metadata["name"] == NAME
        assert metadata["gpu"]["labels"] == payload["Labels"]
        assert len(payload["HostConfig"]["Mounts"]) == 5
        assert {row["Target"] for row in payload["HostConfig"]["Mounts"]} == {
            "/tasks", "/model", "/private-nvidia", "/candidate", "/results"}
        if failure:
            raise OSError("Daemon may have created the container")
        return status, {}, json.dumps({"Id": IDENT}).encode()
    proxy.request = request
    return proxy.create(body, NAME, RUN, "")


def native(record):
    return {"Id": IDENT, "Image": gpu.IMAGE_ID,
            "Config": {"Image": gpu.IMAGE, "Labels": record["gpu"]["labels"]}}


@pytest.mark.parametrize("outcome", ["success", "transport", "500", "409", "malformed"])
def test_ownership_is_durable_before_post_and_unknown_results_stay_reserved(prepared, lease_root, monkeypatch, outcome):
    proxy = instance(prepared, monkeypatch)
    _, body, *_ = prepared
    try:
        if outcome == "transport":
            with pytest.raises(OSError):
                create(proxy, body, failure=True)
        elif outcome == "malformed":
            def broken(*args, **kwargs):
                return 201, {}, b'{"Id":"invalid"}'
            proxy.request = broken
            with pytest.raises(policy.Denied):
                proxy.create(body, NAME, RUN, "")
        else:
            create(proxy, body, status={"success": 201, "500": 500, "409": 409}[outcome])
        owner = json.loads((lease_root / leases.RECORD_NAME).read_text())
        assert owner["id"] == (IDENT if outcome == "success" else None)
        assert Path(owner["stage"]).exists() and proxy.gpu_leases.current is not None
        assert leases.GpuLeases(prepared[0].staging_root).current is None
        other = instance(prepared, monkeypatch)
        other.request = lambda *a, **k: pytest.fail("A second GPU container must not reach Docker")
        with pytest.raises((policy.Denied, BlockingIOError)):
            other.create(body, "arena-eval-" + "c" * 32, RUN, "")
    finally:
        abandon(proxy)


@pytest.mark.parametrize("status", [None, 200, 202, 409, 500])
def test_direct_remove_cannot_clear_ownership_without_confirmed_delete(prepared, lease_root, monkeypatch, status):
    proxy = instance(prepared, monkeypatch)
    try:
        create(proxy, prepared[1])
        record = proxy.records[NAME]
        with pytest.raises(policy.Denied, match="confirmed"):
            proxy.remove(NAME, record, daemon_status=status)
        assert NAME in proxy.records and record["stage"].exists()
        assert (lease_root / leases.RECORD_NAME).exists() and proxy.gpu_leases.current is record["gpu_lease"]
    finally:
        abandon(proxy)


@pytest.mark.parametrize("response", [204, 404, 500, "transport"])
def test_reaper_retains_record_and_lease_until_daemon_confirms_deletion(prepared, lease_root, monkeypatch, response):
    proxy = instance(prepared, monkeypatch)
    try:
        create(proxy, prepared[1])
        record = proxy.records[NAME]
        record["expires"] = 0
        sleeps = 0
        def sleep(_):
            nonlocal sleeps
            sleeps += 1
            if sleeps > 1:
                raise KeyboardInterrupt
        def request(method, path, **kwargs):
            assert method == "DELETE"
            if response == "transport":
                raise OSError("Delete outcome unknown")
            return response, {}, b""
        proxy.request = request
        monkeypatch.setattr(execution.time, "sleep", sleep)
        with pytest.raises(KeyboardInterrupt):
            proxy.reap()
        retained = response not in (204, 404)
        assert (NAME in proxy.records) is retained
        assert record["stage"].exists() is retained
        assert (lease_root / leases.RECORD_NAME).exists() is retained
        assert (proxy.gpu_leases.current is not None) is retained
    finally:
        abandon(proxy)


@pytest.mark.parametrize("response", [204, 404, 500, "transport"])
def test_shutdown_keeps_uncertain_ownership_for_restart(prepared, lease_root, monkeypatch, response):
    proxy = instance(prepared, monkeypatch)
    try:
        create(proxy, prepared[1])
        def request(*args, **kwargs):
            if response == "transport": raise OSError("Unknown")
            return response, {}, b""
        proxy.request = request
        proxy.close()
        assert (lease_root / leases.RECORD_NAME).exists() is (response not in (204, 404))
    finally:
        abandon(proxy)


@pytest.mark.parametrize("known_id", [False, True])
@pytest.mark.parametrize("get_status", [200, 404])
def test_restart_recovers_persisted_owner_before_any_new_gpu_claim(prepared, lease_root, monkeypatch, known_id, get_status):
    proxy = instance(prepared, monkeypatch)
    if known_id:
        create(proxy, prepared[1])
    else:
        with pytest.raises(OSError): create(proxy, prepared[1], failure=True)
    saved = json.loads((lease_root / leases.RECORD_NAME).read_text())
    abandon(proxy)
    restarted = instance(prepared, monkeypatch)
    calls = []
    def request(method, path, **kwargs):
        calls.append((method, path))
        assert (lease_root / leases.RECORD_NAME).exists()
        if method == "GET": return get_status, {}, json.dumps(native(saved)).encode()
        return 204, {}, b""
    restarted.request = request
    restarted.recover()
    assert calls[0] == ("GET", "/containers/" + (IDENT if known_id else NAME) + "/json")
    assert [call[0] for call in calls] == (["GET", "DELETE"] if get_status == 200 else ["GET"])
    assert not Path(saved["stage"]).exists() and not (lease_root / leases.RECORD_NAME).exists()
    assert restarted.gpu_leases.current is None
    try:
        create(restarted, prepared[1])
    finally:
        abandon(restarted)


@pytest.mark.parametrize("mutation", ["run", "device", "extra-label", "missing-label", "image", "image-id",
                                    "container-id", "delete500", "get503", "transport"])
def test_restart_never_kills_unmatched_container_or_releases_uncertain_gpu(prepared, lease_root, monkeypatch, mutation):
    proxy = instance(prepared, monkeypatch)
    create(proxy, prepared[1])
    saved = json.loads((lease_root / leases.RECORD_NAME).read_text())
    abandon(proxy)
    restarted = instance(prepared, monkeypatch)
    value = deepcopy(native(saved))
    if mutation == "run": value["Config"]["Labels"]["arena.control-run"] = "f" * 32
    elif mutation == "device": value["Config"]["Labels"]["arena.gpu-device"] = "GPU-other"
    elif mutation == "extra-label": value["Config"]["Labels"]["untrusted"] = "label"
    elif mutation == "missing-label": value["Config"]["Labels"].pop("io.arena.profile")
    elif mutation == "image": value["Config"]["Image"] = "wrong:image"
    elif mutation == "image-id": value["Image"] = "sha256:" + "a" * 64
    elif mutation == "container-id": value["Id"] = "c" * 64
    calls = []
    def request(method, path, **kwargs):
        calls.append(method)
        if mutation == "transport": raise OSError("Unknown")
        if method == "GET": return (503 if mutation == "get503" else 200), {}, json.dumps(value).encode()
        return 500, {}, b""
    restarted.request = request
    try:
        with pytest.raises((policy.Denied, OSError)):
            restarted.recover()
        assert calls == (["GET", "DELETE"] if mutation == "delete500" else ["GET"])
        assert (lease_root / leases.RECORD_NAME).exists() and Path(saved["stage"]).exists()
        assert restarted.gpu_leases.current is not None
    finally:
        abandon(restarted)


def test_real_process_lock_then_persisted_record_prevents_double_booking(prepared, lease_root, monkeypatch):
    config, body, *_ = prepared
    rebuilt, *_ = policy.canonical_config(body, NAME, RUN, config)
    stage = config.staging_root / ("e" * 32); stage.mkdir()
    recovery = {"run": RUN, "name": NAME, "gpu": {
        "device_uuid": gpu.DEVICE_UUID, "image": gpu.IMAGE, "labels": rebuilt["Labels"]}}
    source = """
import json,os,sys
from pathlib import Path
from arena import evaluator_gpu_leases as leases
leases.STATE_ROOT=Path(sys.argv[1]);leases.OWNER_UID=os.getuid()
manager=leases.GpuLeases(Path(sys.argv[2]))
manager.reserve(json.loads(sys.argv[3]),Path(sys.argv[4]))
print('reserved',flush=True)
sys.stdin.readline()
os._exit(0)
"""
    child = subprocess.Popen([sys.executable, "-c", source, str(lease_root), str(config.staging_root),
        json.dumps(recovery), str(stage)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")})
    try:
        assert select.select([child.stdout], [], [], 5)[0]
        assert child.stdout.readline().strip() == "reserved"
        other = leases.GpuLeases(config.staging_root)
        with pytest.raises(BlockingIOError): other.reserve(recovery, stage)
        child.stdin.write("exit\n"); child.stdin.flush()
        assert child.wait(timeout=5) == 0
        with pytest.raises(policy.Denied, match="recovered"):
            other.reserve(recovery, stage)
        other.recover(lambda *a, **k: (404, {}, b""))
        assert not (lease_root / leases.RECORD_NAME).exists()
    finally:
        if child.poll() is None: child.kill()
        child.communicate(timeout=5)


@pytest.mark.parametrize("mutation", ["linked-lock", "hardlinked-lock", "writable-lock", "writable-storage",
                                    "linked-record", "wrong-record-mode"])
def test_unsafe_persistent_storage_never_reaches_docker(prepared, lease_root, monkeypatch, mutation):
    lock = lease_root / leases.LOCK_NAME
    lock.touch(mode=0o600)
    if mutation == "linked-lock":
        lock.unlink(); lock.symlink_to(lease_root / "missing")
    elif mutation == "hardlinked-lock": os.link(lock, lease_root / "other-lock")
    elif mutation == "writable-lock": lock.chmod(0o666)
    elif mutation == "writable-storage": lease_root.chmod(0o777)
    elif mutation == "linked-record": (lease_root / leases.RECORD_NAME).symlink_to(lock)
    else:
        (lease_root / leases.RECORD_NAME).write_text("{}")
        (lease_root / leases.RECORD_NAME).chmod(0o644)
    proxy = instance(prepared, monkeypatch)
    proxy.request = lambda *a, **k: pytest.fail("Unsafe ownership reached Docker")
    try:
        with pytest.raises((policy.Denied, OSError)):
            proxy.create(prepared[1], NAME, RUN, "")
        assert not proxy.records and proxy.gpu_leases.current is None
    finally:
        abandon(proxy)


def test_startup_cannot_recover_an_owner_still_locked_by_live_proxy(prepared, lease_root, monkeypatch):
    proxy = instance(prepared, monkeypatch)
    try:
        create(proxy, prepared[1])
        second = instance(prepared, monkeypatch)
        second.request = lambda *a, **k: pytest.fail("Cannot kill a live proxy's GPU owner")
        with pytest.raises(BlockingIOError): second.recover()
        assert NAME in proxy.records and (lease_root / leases.RECORD_NAME).exists()
    finally:
        abandon(proxy)


def test_failed_durable_reservation_cannot_send_post_or_unlock_current_owner(prepared, lease_root, monkeypatch):
    proxy = instance(prepared, monkeypatch)
    def failed(*args): raise OSError("Persistence failed")
    monkeypatch.setattr(leases, "write_ownership", failed)
    proxy.request = lambda *a, **k: pytest.fail("POST must follow durable reservation")
    try:
        with pytest.raises(OSError, match="Persistence"):
            proxy.create(prepared[1], NAME, RUN, "")
        assert proxy.gpu_leases.current is not None and not proxy.records
        assert Path(proxy.gpu_leases.current.record["stage"]).exists()
        with pytest.raises(BlockingIOError):
            other = leases.state_directory()
            try: leases.device_lock(other)
            finally: os.close(other)
    finally:
        abandon(proxy)
