"""Bounded campaign admission against inert local control and native receipts."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import threading

import pytest

from arena.control_types import _json

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("submit_sciel_catalog",
    ROOT / "scripts/deployment/submit_sciel_catalog.py")
submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submit)


def key_file(root, value="arena_" + "x" * 32):
    path = root / "key.json"
    path.write_text(json.dumps({"token": value}))
    path.chmod(0o600)
    return path


def test_key_reader_rejects_shared_files_links_and_foreign_ownership(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    path = key_file(root)
    assert submit.read_key(path).startswith("arena_")
    path.chmod(0o640)
    with pytest.raises(ValueError, match="private credential"):
        submit.read_key(path)
    path.chmod(0o600)
    link = root / "link.json"
    link.symlink_to(path)
    with pytest.raises(ValueError):
        submit.read_key(link)
    parent = root / "linked-parent"
    parent.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError):
        submit.read_key(parent / path.name)
    if os.geteuid() != 0:
        monkeypatch.setattr(submit.os, "geteuid", lambda: 123456)
        with pytest.raises(ValueError):
            submit.read_key(path)


def test_http_redirect_never_forwards_control_credential(monkeypatch):
    redirected = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def do_GET(self):
            if self.path == "/capture":
                redirected.append(self.headers.get("Authorization"))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")
            else:
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/capture")
                self.end_headers()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(submit, "CONTROL_ORIGIN", f"http://127.0.0.1:{server.server_port}")
    try:
        with pytest.raises(RuntimeError, match="HTTP 302"):
            submit.Control("arena_" + "x" * 32).call("/api/control/templates")
        assert redirected == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.mark.parametrize("size,failures,paused", [(1, 1, True), (4, 1, True), (16, 3, False), (16, 4, True)])
def test_failure_threshold_is_exactly_one_quarter_even_in_small_final_batches(size, failures, paused):
    templates = [{"id": f"template-{index}"} for index in range(size)]
    rows = [{"id": f"{index:032x}", "template": template["id"], "batch_id": "batch",
        "state": "failed" if index < failures else "completed"} for index, template in enumerate(templates)]
    assert submit.batch_state(rows, templates, "batch")[2:] == (True, paused)
    rows[0]["state"] = "running"
    assert submit.batch_state(rows, templates, "batch")[2:] == (False, False)
    rows[0]["state"] = "unknown"
    with pytest.raises(ValueError, match="Unknown queue state"):
        submit.batch_state(rows, templates, "batch")


@pytest.fixture
def control_fixture(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    planned = [{"id": f"template-{i}", "name": f"SCiEL · task {i}", "framework": "sciel-release",
                "model": "gpt-5.5", "status": "ready"} for i in range(3)]
    live = {"templates": planned, "limits": {"max_active": 4}, "state_dir": str(root / "state")}
    templates = root / "templates.json"
    templates.write_text(json.dumps(planned))
    config = root / "control.json"
    config.write_text(json.dumps(live))
    credential = key_file(root)
    status = root / "status.json"
    revision = submit.hashlib.sha256(_json(live).encode()).hexdigest()
    rows, posts, outcome = {}, [], {"state": "completed", "reason": "budget"}
    class FakeControl:
        def __init__(self, token):
            assert token.startswith("arena_")
        def runs(self):
            return list(rows.values())
        def call(self, path, body=None):
            if path == "/api/control/templates":
                return {"revision": revision, "limits": live["limits"]}
            if body is not None:
                if posts and posts[-1]["batch_id"] != body["batch_id"]:
                    assert all(row["state"] in submit.TERMINAL for row in rows.values())
                posts.append(deepcopy(body))
                ident = f"{len(posts):032x}"
                rows[ident] = {"id": ident, "template": body["template"], "model": body["model"],
                    "label": body["label"], "batch_id": body["batch_id"], "framework": "sciel-release",
                    "revision": revision, "state": "queued"}
                artifact = Path(live["state_dir"]) / "runs" / ident / "artifacts/.arena/native-result.json"
                artifact.parent.mkdir(parents=True)
                artifact.write_text(json.dumps({"schema": "arena.native-result/1", "framework": "sciel-release",
                    "status": "recorded", "native": {"reason": outcome["reason"]}}))
                return {"run": deepcopy(rows[ident])}
            ident = path.rsplit("/", 1)[1]
            rows[ident]["state"] = outcome["state"]
            return {"run": deepcopy(rows[ident])}
    monkeypatch.setattr(submit, "Control", FakeControl)
    monkeypatch.setattr(submit.time, "sleep", lambda _: pytest.fail("All fixture runs are immediately terminal"))
    argv = ["--templates", str(templates), "--control-config", str(config), "--key-file", str(credential),
            "--campaign", "fixture", "--status", str(status), "--batch-size", "2", "--admit"]
    return argv, status, credential, posts, outcome, live, config


def test_waves_wait_for_completion_and_resume_reuses_runs_even_after_key_rotation(control_fixture):
    argv, status, credential, posts, _, _, _ = control_fixture
    assert submit.main(argv) == 0
    assert len(posts) == 3
    assert [row["batch_id"] for row in posts] == ["fixture-b001", "fixture-b001", "fixture-b002"]
    assert len({row["idempotency_key"] for row in posts}) == 3
    assert json.loads(status.read_text())["state"] == "completed"
    credential.write_text(json.dumps({"token": "arena_" + "y" * 32}))
    assert submit.main(argv) == 0
    assert len(posts) == 3
    assert stat_mode(status) == 0o600


def stat_mode(path):
    return path.stat().st_mode & 0o777


def test_resume_rejects_changed_batch_size_without_overwriting_saved_identity(control_fixture):
    argv, status, _, posts, _, _, _ = control_fixture
    assert submit.main(argv) == 0
    original = status.read_bytes()
    argv[argv.index("--batch-size") + 1] = "1"
    with pytest.raises(ValueError, match="Resume requires"):
        submit.main(argv)
    assert status.read_bytes() == original and len(posts) == 3


@pytest.mark.parametrize("failure", ["queue", "native"])
def test_provider_or_wave_failures_pause_before_any_following_wave(control_fixture, failure):
    argv, status, _, posts, outcome, _, _ = control_fixture
    if failure == "queue":
        outcome["state"] = "failed"
    else:
        outcome["reason"] = "post_evaluation_research_stopped:ProviderRecoveryError"
    assert submit.main(argv) == 2
    assert len(posts) == 2
    expected = "paused_after_failures" if failure == "queue" else "paused_native_evidence"
    assert json.loads(status.read_text())["state"] == expected


def test_more_than_four_live_workers_are_rejected_before_submission(control_fixture):
    argv, _, _, posts, _, live, config = control_fixture
    live["limits"]["max_active"] = 5
    config.write_text(json.dumps(live))
    with pytest.raises(ValueError, match="at most four"):
        submit.main(argv)
    assert not posts


def test_campaign_lock_refuses_parallel_submitters(tmp_path):
    path = tmp_path.resolve() / "status.json"
    with submit.campaign_lock(path):
        with pytest.raises(ValueError, match="Another process"):
            with submit.campaign_lock(path):
                pytest.fail("Concurrent admission must not acquire the campaign lock")


def test_long_task_titles_fit_the_control_label_limit_without_changing_idempotency():
    template = {"id": "stable-task", "model": "gpt-5.5", "name": "Research task " * 16}
    body = submit.submission(template, "fixture", 1)
    assert len(body["label"]) == 128
    renamed = {**template, "name": "Short name"}
    assert submit.submission(renamed, "fixture", 1)["idempotency_key"] == body["idempotency_key"]
