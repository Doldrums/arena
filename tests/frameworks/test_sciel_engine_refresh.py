"""A runtime-only refresh must retain the pinned engine and dependency identity."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("engine_refresh",
    ROOT / "scripts/deployment/refresh_sciel_engine.py")
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)

PARENT = "127.0.0.1:5000/empira/sciel@sha256:" + "a" * 64
OLD = "0.2.0+arena.a6c0d215.worker2"
NEW = "0.2.0+arena.a6c0d215.worker3"
SNAPSHOT = "b" * 64


def images():
    parent = {"Id": "sha256:" + "c" * 64, "RepoDigests": [PARENT], "Architecture": "amd64",
        "RootFS": {"Layers": ["sha256:" + "d" * 64]}, "Config": {
            "User": "998:998", "WorkingDir": "/opt/sciel", "Cmd": None,
            "Entrypoint": ["/opt/venv/bin/python", "-m", "sciel.cli.main"],
            "Env": ["PYTHONPATH=/opt/sciel/src:/opt/arena/src"],
            "Labels": {"org.opencontainers.image.revision": refresh.PIN,
                "org.opencontainers.image.source": "https://github.com/Doldrums/sciel",
                "org.opencontainers.image.version": OLD, "io.arena.sciel.contract": "sciel-cli-v1"}}}
    child = deepcopy(parent)
    child["RootFS"]["Layers"].append("sha256:" + "e" * 64)
    child["Config"]["Labels"].update({"org.opencontainers.image.version": NEW,
                                   "org.empira.arena.snapshot-sha256": SNAPSHOT})
    before = {"source_commit": refresh.PIN, "sciel_version": "0.2.0",
              "dependency_sha256": "f" * 64, "dependency_count": 120, "task_source": {"manifest": "old"}}
    after = {**before, "task_source": {"manifest": "new"}, "arena_snapshot_sha256": SNAPSHOT}
    return parent, child, before, after


def test_refresh_retains_engine_with_a_new_task_library():
    parent, child, before, after = images()
    refresh.validate_parent(parent, PARENT, OLD)
    labels = refresh.verify_child(parent, child, NEW, SNAPSHOT, before, after, after["task_source"])
    assert labels["org.opencontainers.image.revision"] == refresh.PIN
    definition = refresh.dockerfile(PARENT, NEW, SNAPSHOT)
    assert definition.startswith("FROM " + PARENT + "\n")
    assert "RUN rm -rf /opt/arena\nCOPY arena/ /opt/arena/" in definition
    assert "pip" not in definition and "curl" not in definition
    assert definition.endswith("USER 998:998\n")


@pytest.mark.parametrize("change", ["tag", "wrong_digest", "source", "release", "directory", "onbuild", "layers"])
def test_parent_identity_is_explicit_and_immutable(change):
    parent, *_ = images()
    reference = PARENT
    if change == "tag": reference = "127.0.0.1:5000/empira/sciel:latest"
    elif change == "wrong_digest": parent["RepoDigests"] = []
    elif change == "source": parent["Config"]["Labels"]["org.opencontainers.image.revision"] = "0" * 40
    elif change == "release": parent["Config"]["Labels"]["org.opencontainers.image.version"] = NEW
    elif change == "directory": parent["Config"]["WorkingDir"] = "/tmp"
    elif change == "onbuild": parent["Config"]["OnBuild"] = ["RUN touch /opt/sciel/changed.py"]
    else: parent["RootFS"]["Layers"] = []
    with pytest.raises(ValueError): refresh.validate_parent(parent, reference, OLD)


@pytest.mark.parametrize("field", refresh.PRESERVED)
def test_child_cannot_change_engine_execution_configuration(field):
    parent, child, before, after = images()
    child["Config"][field] = "changed"
    with pytest.raises(ValueError):
        refresh.verify_child(parent, child, NEW, SNAPSHOT, before, after, after["task_source"])


@pytest.mark.parametrize("change", ["layer", "snapshot", "source", "version", "packages", "package_count", "task_library", "arena_code"])
def test_child_proof_must_bind_the_actual_new_runtime(change):
    parent, child, before, after = images()
    expected_task = deepcopy(after["task_source"])
    if change == "layer": child["RootFS"]["Layers"][0] = "sha256:" + "1" * 64
    elif change == "snapshot": child["Config"]["Labels"]["org.empira.arena.snapshot-sha256"] = "2" * 64
    elif change == "source": after["source_commit"] = "3" * 40
    elif change == "version": after["sciel_version"] = "0.3.0"
    elif change == "packages": after["dependency_sha256"] = "4" * 64
    elif change == "package_count": after["dependency_count"] += 1
    elif change == "task_library": after["task_source"] = {"manifest": "old"}
    else: after["arena_snapshot_sha256"] = "9" * 64
    with pytest.raises(ValueError):
        refresh.verify_child(parent, child, NEW, SNAPSHOT, before, after, expected_task)


@pytest.mark.parametrize("reference,version,snapshot", [
    (PARENT + "\nRUN touch /tmp/injected", NEW, SNAPSHOT),
    (PARENT, NEW + '\"\nUSER root', SNAPSHOT),
    (PARENT, NEW, SNAPSHOT + "\nRUN true")])
def test_dockerfile_inputs_cannot_add_commands(reference, version, snapshot):
    with pytest.raises(ValueError): refresh.dockerfile(reference, version, snapshot)


@pytest.mark.parametrize("status", [401, 403, 429, 500, 503])
def test_registry_failure_is_not_mistaken_for_an_unused_tag(monkeypatch, status):
    class Response:
        pass
    Response.status = status
    class Connection:
        def __init__(self, host, port, timeout):
            assert (host, port) == ("127.0.0.1", 5000)
        def request(self, method, path, headers): pass
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(refresh.http.client, "HTTPConnection", Connection)
    with pytest.raises(ValueError, match="verified tag state"):
        refresh.registry_tag("127.0.0.1:5000/empira/sciel:worker3")
    Response.status = 404
    assert refresh.registry_tag("127.0.0.1:5000/empira/sciel:worker3") is None


@pytest.mark.parametrize("corrupt", [False, True])
def test_registry_manifest_digest_binds_the_image_config(monkeypatch, corrupt):
    raw = json.dumps({"schemaVersion": 2, "config": {"digest": "sha256:" + "e" * 64}}).encode()
    digest = "sha256:" + refresh.sha(raw)
    class Response:
        status = 200
        def read(self, limit): return raw
        def getheader(self, key): return "sha256:" + "0" * 64 if corrupt else digest
    class Connection:
        def __init__(self, *args, **kwargs): pass
        def request(self, *args, **kwargs): pass
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(refresh.http.client, "HTTPConnection", Connection)
    if corrupt:
        with pytest.raises(ValueError, match="digest"):
            refresh.registry_tag("127.0.0.1:5000/empira/sciel:worker3")
    else:
        assert refresh.registry_tag("127.0.0.1:5000/empira/sciel:worker3") == {
            "reference": "127.0.0.1:5000/empira/sciel@" + digest, "image_id": "sha256:" + "e" * 64}


@pytest.mark.parametrize("change", [None, "remote_exists", "local_retag", "published_wrong_id", "missing_digest"])
def test_push_never_issues_a_receipt_for_unverified_image_bytes(monkeypatch, change):
    tag, ident = "127.0.0.1:5000/empira/sciel:worker3", "sha256:" + "e" * 64
    published = {"reference": PARENT, "image_id": ident}
    if change == "published_wrong_id": published["image_id"] = "sha256:" + "f" * 64
    responses = iter([published if change == "remote_exists" else None, published])
    monkeypatch.setattr(refresh, "registry_tag", lambda _: next(responses))
    inspected, pushed = [], []
    def inspect(reference):
        inspected.append(reference)
        return {"Id": "sha256:" + "f" * 64 if change == "local_retag" else ident,
                "RepoDigests": [] if change == "missing_digest" else [PARENT]}
    monkeypatch.setattr(refresh, "inspect", inspect)
    monkeypatch.setattr(refresh.subprocess, "run", lambda *args, **kwargs: pushed.append(args))
    if change is None:
        assert refresh.push_verified(tag, ident, None)["Id"] == ident
        assert inspected == [tag, ident] and len(pushed) == 1
    else:
        with pytest.raises(ValueError): refresh.push_verified(tag, ident, None)
        if change in {"remote_exists", "local_retag"}: assert not pushed
