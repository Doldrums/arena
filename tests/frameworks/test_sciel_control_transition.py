"""Explicit append transitions retain old admissions and reject unreviewed drift."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("submit_transition_fixture",
    ROOT / "scripts/deployment/submit_sciel_catalog.py")
submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submit)
from sciel_control_transition import load_transition


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(submit.encoded(value) + b"\n")
    path.chmod(0o600)
    return path


def sha(path):
    return submit.hashlib.sha256(path.read_bytes()).hexdigest()


def revision(config):
    return submit.hashlib.sha256(submit.encoded(config)).hexdigest()


def template(index):
    return {"id": f"template-{index}", "name": f"SCiEL · science task {index}",
        "framework": "sciel-release", "profile": "native", "model": "gpt-5.5", "status": "ready",
        "blocked_reason": None, "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
        "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
        "spec": {"schema": "arena.native-run/1", "framework": "sciel-release", "source_dir": "/private/source",
            "output_dir": "{output_dir}", "timeout_seconds": 3600,
            "request": {"task": f"science-{index}", "budget": 16, "protocol": "recreated"}}}


@pytest.fixture
def transition_fixture(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    planned = [template(index) for index in range(3)]
    old = {"schema": "arena.control/1", "state_dir": str(root / "state"), "cgroup_root": "/sys/fs/cgroup/test",
        "limits": {"cpus": 16, "memory_mb": 32768, "evaluation_slots": 4, "max_active": 4,
            "max_queued": 64, "max_runs_per_key": 2000, "max_reserved_seconds_per_key": 10000000},
        "templates": deepcopy(planned)}
    new = {**deepcopy(old), "templates": [*deepcopy(planned), template(99)]}
    previous = write(root / "frozen/previous.json", old)
    following = write(root / "frozen/next.json", new)
    descriptor = {"schema": "arena.control-append-transition/1",
        "previous": {"path": str(previous), "sha256": sha(previous), "revision": revision(old)},
        "next": {"path": str(following), "sha256": sha(following), "revision": revision(new)},
        "added_template_ids": ["template-99"]}
    transition_path = write(root / "transition.json", descriptor)
    config_path = write(root / "control.json", new)
    templates_path = write(root / "templates.json", planned)
    key_path = write(root / "key.json", {"token": "arena_" + "x" * 32})
    status_path = root / "status.json"
    rows, posts, hooks = {}, [], {}
    def record(body, control_revision, ident=None):
        ident = ident or f"{len(rows) + 1:032x}"
        row = {"id": ident, "template": body["template"], "model": body["model"], "label": body["label"],
            "framework": "sciel-release", "batch_id": body["batch_id"], "state": "completed", "revision": control_revision}
        selected = next(item for item in planned if item["id"] == row["template"])
        write(root / "state/runs" / ident / "snapshot.json", {
            "revision": control_revision, "template": selected, "cgroup_root": old["cgroup_root"]})
        write(root / "state/runs" / ident / "artifacts/.arena/native-result.json", {
            "schema": "arena.native-result/1", "framework": "sciel-release", "status": "recorded",
            "native": {"reason": "budget"}})
        rows[ident] = row
        return deepcopy(row)
    old_run = record(submit.submission(planned[0], "original", 1), revision(old))
    write(status_path, {"schema": "arena.sciel-catalog-admission/1", "campaign": "original",
        "templates_sha256": sha(templates_path), "planned": 3, "batch_size": 2, "models": ["gpt-5.5"],
        "control_revision": revision(old), "state": "running", "batches": [{"batch_id": "original-b001",
            "counts": {"completed": 1}, "native_issues": {},
            "runs": [{key: old_run[key] for key in ("id", "template", "model", "state")}]}]})
    class Control:
        def __init__(self, token):
            assert token.startswith("arena_")
        def runs(self):
            return [deepcopy(row) for row in rows.values()]
        def call(self, path, body=None):
            current = json.loads(config_path.read_text())
            if path == "/api/control/templates":
                return {"revision": revision(current), "limits": current["limits"]}
            if body is not None:
                posts.append(deepcopy(body))
                row = record(body, revision(current))
                if hooks.pop("crash_after_post", False):
                    raise RuntimeError("Lost post response")
                return {"run": row}
            row = deepcopy(rows[path.rsplit("/", 1)[1]])
            callback = hooks.pop("after_first_poll", None)
            if callback:
                callback()
            return {"run": row}
    monkeypatch.setattr(submit, "Control", Control)
    monkeypatch.setattr(submit.time, "sleep", lambda _: pytest.fail("Fixture runs are complete"))
    argv = ["--templates", str(templates_path), "--control-config", str(config_path),
        "--key-file", str(key_path), "--campaign", "original", "--status", str(status_path),
        "--batch-size", "2", "--control-transition", str(transition_path), "--admit"]
    return {"root": root, "old": old, "new": new, "descriptor": descriptor, "path": transition_path,
        "config": config_path, "templates": templates_path, "status": status_path, "key": key_path,
        "rows": rows, "posts": posts, "hooks": hooks, "argv": argv}


def load(fixture):
    return load_transition(fixture["path"], control_path=fixture["config"], read=submit.read_bytes, encode=submit.encoded)


def test_old_runs_keep_revision_and_snapshot_new_admissions_use_new_revision(transition_fixture):
    f = transition_fixture
    original_templates = f["templates"].read_bytes()
    original_config = f["config"].read_bytes()
    original_snapshot = (f["root"] / "state/runs" / ("0" * 31 + "1") / "snapshot.json").read_bytes()
    assert submit.main(f["argv"]) == 0
    status = json.loads(f["status"].read_text())
    assert status["state"] == "completed" and status["planned"] == 3
    assert status["control_revision"] == revision(f["old"])
    assert status["active_control_revision"] == revision(f["new"])
    assert [row["revision"] for row in f["rows"].values()] == [revision(f["old"]), revision(f["new"]), revision(f["new"])]
    assert len(status["run_bindings"]) == 3
    assert all(len(binding["snapshot_sha256"]) == 64 for binding in status["run_bindings"].values())
    assert len(f["posts"]) == 2 and all(row["template"] != "template-99" for row in f["posts"])
    assert f["templates"].read_bytes() == original_templates and f["config"].read_bytes() == original_config
    assert (f["root"] / "state/runs" / ("0" * 31 + "1") / "snapshot.json").read_bytes() == original_snapshot
    write(f["key"], {"token": "arena_" + "y" * 32})
    assert submit.main(f["argv"]) == 0 and len(f["posts"]) == 2


def test_explicit_transition_can_activate_between_waves(transition_fixture):
    f = transition_fixture
    write(f["config"], f["old"])
    f["hooks"]["after_first_poll"] = lambda: write(f["config"], f["new"])
    assert submit.main(f["argv"]) == 0
    assert [row["revision"] for row in f["rows"].values()] == [revision(f["old"]), revision(f["old"]), revision(f["new"])]


def test_post_response_loss_recovers_same_run_without_duplicate_or_new_science(transition_fixture):
    f = transition_fixture
    f["hooks"]["crash_after_post"] = True
    assert submit.main(f["argv"]) == 2 and len(f["posts"]) == 1
    assert submit.main(f["argv"]) == 0 and len(f["posts"]) == 2
    assert len(f["rows"]) == 3


@pytest.mark.parametrize("change", ["limits", "existing_spec", "existing_order", "remove", "duplicate", "extra_addition"])
def test_transition_refuses_non_append_changes_even_with_recomputed_file_hashes(transition_fixture, change):
    f = transition_fixture
    candidate = deepcopy(f["new"])
    if change == "limits":
        candidate["limits"]["max_active"] = 3
    elif change == "existing_spec":
        candidate["templates"][0]["spec"]["request"]["budget"] = 17
    elif change == "existing_order":
        candidate["templates"][0], candidate["templates"][1] = candidate["templates"][1], candidate["templates"][0]
    elif change == "remove":
        candidate["templates"].pop(0)
    elif change == "duplicate":
        candidate["templates"].append(deepcopy(candidate["templates"][0]))
    else:
        candidate["templates"].append(template(100))
    path = Path(f["descriptor"]["next"]["path"])
    write(path, candidate)
    f["descriptor"]["next"].update(sha256=sha(path), revision=revision(candidate))
    write(f["path"], f["descriptor"])
    with pytest.raises(ValueError):
        load(f)
    assert not f["posts"]


@pytest.mark.parametrize("change", ["file_bytes", "linked_snapshot", "live_snapshot", "public_descriptor"])
def test_transition_refuses_unfrozen_or_untrusted_inputs(transition_fixture, change):
    f = transition_fixture
    path = Path(f["descriptor"]["next"]["path"])
    if change == "file_bytes":
        path.write_bytes(path.read_bytes() + b" ")
    elif change == "linked_snapshot":
        other = path.with_name("real.json")
        path.rename(other)
        path.symlink_to(other)
    elif change == "live_snapshot":
        f["descriptor"]["next"]["path"] = str(f["config"])
        write(f["path"], f["descriptor"])
    else:
        f["path"].chmod(0o644)
    with pytest.raises((ValueError, OSError)):
        load(f)


def test_snapshot_tamper_stops_before_any_new_admission(transition_fixture):
    f = transition_fixture
    path = f["root"] / "state/runs" / ("0" * 31 + "1") / "snapshot.json"
    snapshot = json.loads(path.read_text())
    snapshot["template"]["spec"]["request"]["protocol"] = "different"
    write(path, snapshot)
    assert submit.main(f["argv"]) == 2
    assert not f["posts"] and json.loads(f["status"].read_text())["state"] == "paused_control_error"


def test_existing_run_cannot_be_relabelled_to_the_new_approved_revision(transition_fixture):
    f = transition_fixture
    ident = next(iter(f["rows"]))
    f["rows"][ident]["revision"] = revision(f["new"])
    path = f["root"] / "state/runs" / ident / "snapshot.json"
    snapshot = json.loads(path.read_text())
    snapshot["revision"] = revision(f["new"])
    write(path, snapshot)
    assert submit.main(f["argv"]) == 2
    assert not f["posts"]


def test_resume_rejects_removed_transition_reversion_and_new_unapproved_revision(transition_fixture):
    f = transition_fixture
    assert submit.main(f["argv"]) == 0
    before = f["status"].read_bytes()
    argv = list(f["argv"])
    index = argv.index("--control-transition")
    del argv[index:index + 2]
    with pytest.raises(ValueError):
        submit.main(argv)
    write(f["config"], f["old"])
    with pytest.raises(ValueError, match="revert"):
        submit.main(f["argv"])
    candidate = deepcopy(f["new"])
    candidate["templates"].append(template(100))
    write(f["config"], candidate)
    with pytest.raises(ValueError, match="outside"):
        submit.main(f["argv"])
    assert f["status"].read_bytes() == before and len(f["posts"]) == 2


def test_mutated_transition_during_run_does_not_admit_next_wave(transition_fixture):
    f = transition_fixture
    f["hooks"]["after_first_poll"] = lambda: f["path"].write_bytes(f["path"].read_bytes() + b" ")
    assert submit.main(f["argv"]) == 2
    assert len(f["posts"]) == 1 and len(f["rows"]) == 2


def test_resume_requires_the_same_frozen_transition_bytes(transition_fixture):
    f = transition_fixture
    assert submit.main(f["argv"]) == 0
    previous = f["status"].read_bytes()
    f["path"].write_bytes(f["path"].read_bytes() + b" ")
    with pytest.raises(ValueError, match="same explicit"):
        submit.main(f["argv"])
    assert f["status"].read_bytes() == previous and len(f["posts"]) == 2
