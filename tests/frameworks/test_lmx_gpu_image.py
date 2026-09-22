"""Check dependency identity and private image boundaries without Docker/network."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "lmx_gpu_image", ROOT / "scripts/deployment/build_lmx_gpu_image.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
ASSETS = ROOT / "tasks/adapters/lmx_sd_assets.json"
TAG = "127.0.0.1:5000/empira/canonical-lmx-gpu:test"
CHILD_ID = "sha256:" + "c" * 64
REF = TAG.rsplit(":", 1)[0] + "@sha256:" + "b" * 64


def wheel(directory, name, version="1.0", suffix=""):
    path = directory / f"{name}-{version}{suffix}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{name}.dist-info/METADATA", f"Name: {name}\nVersion: {version}\n")
    return path


def image(identity=CHILD_ID):
    return {"Id": identity, "Architecture": "amd64", "Os": "linux",
            "RepoDigests": [builder.BASE if identity == builder.BASE_ID else REF],
            "Config": {"Entrypoint": None, "Cmd": ["python3"], "OnBuild": None}}


def test_large_file_digest_works_on_worker_python_without_file_digest(tmp_path, monkeypatch):
    path = tmp_path / "wheel-bytes"
    raw = b"wheel" * 500000
    path.write_bytes(raw)
    monkeypatch.delattr(hashlib, "file_digest", raising=False)
    assert builder.digest(path) == hashlib.sha256(raw).hexdigest()


def test_model_lock_is_the_reviewed_offline_fp16_snapshot():
    value = builder.model_lock(ASSETS)
    assert value["revision"] == "2880f2ca379f41b0226444936bb7a6766a227587"
    assert value["source_ref"] == "fp16"
    assert sum(row["size"] for row in value["files"].values()) == 2742615730
    assert "safety_checker/pytorch_model.bin" in value["files"]


@pytest.mark.parametrize("mutation", ["changed", "symlink", "traversal", "revision", "missing"])
def test_asset_lock_rejects_changes_and_unsafe_future_records(tmp_path, monkeypatch, mutation):
    path = tmp_path / "assets.json"
    value = json.loads(ASSETS.read_bytes())
    if mutation == "symlink":
        path.symlink_to(ASSETS)
    else:
        if mutation == "traversal":
            value["files"]["../model"] = value["files"].pop("model_index.json")
        elif mutation == "revision":
            value["revision"] = "main"
        elif mutation == "missing":
            del value["files"]["safety_checker/pytorch_model.bin"]
        path.write_text(json.dumps(value))
        if mutation != "changed":
            monkeypatch.setattr(builder, "ASSET_SHA", builder.digest(path))
    with pytest.raises(ValueError):
        builder.model_lock(path)


def test_wheel_lock_covers_transitive_bytes_without_reading_whole_large_files(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, "PINS", {"numpy": "2.2.6"})
    sources = []
    monkeypatch.setattr(builder, "official_source", lambda row: sources.append(row.copy()) or "https://files.pythonhosted.org/wheel")
    first = wheel(tmp_path, "numpy", "2.2.6")
    second = wheel(tmp_path, "transitive", "3.0")
    with zipfile.ZipFile(second, "a") as archive:
        archive.writestr("transitive/_vendor/other.dist-info/METADATA", "Name: other\nVersion: 1\n")
    monkeypatch.setattr(Path, "read_bytes", lambda _: pytest.fail("Stream large wheels"))
    lock, records = builder.wheel_lock(tmp_path)
    assert [row["name"] for row in records] == ["numpy", "transitive"]
    assert len(sources) == 2
    for path in (first, second):
        assert "--hash=sha256:" + builder.digest(path) in lock
    assert records[1]["version"] == "3.0"


@pytest.mark.parametrize("mutation", ["duplicate", "sdist", "symlink", "wrong_version", "missing"])
def test_wheel_lock_rejects_ambiguous_or_incomplete_install_input(tmp_path, monkeypatch, mutation):
    monkeypatch.setattr(builder, "PINS", {"numpy": "2.2.6"})
    monkeypatch.setattr(builder, "official_source", lambda _: "https://files.pythonhosted.org/wheel")
    first = wheel(tmp_path, "numpy", "2.2.5" if mutation == "wrong_version" else "2.2.6")
    if mutation == "duplicate":
        wheel(tmp_path, "NumPy", "2.2.6", suffix="-copy")
    elif mutation == "sdist":
        (tmp_path / "source.tar.gz").write_bytes(b"build source")
    elif mutation == "symlink":
        (tmp_path / "linked.whl").symlink_to(first)
    elif mutation == "missing":
        first.unlink()
    with pytest.raises(ValueError):
        builder.wheel_lock(tmp_path)


def test_official_pytorch_hash_and_exact_version_are_required(monkeypatch):
    monkeypatch.setattr(builder, "urlopen", lambda *a, **k: pytest.fail("Pinned torch needs no PyPI fallback"))
    filename, sha = builder.TORCH["torch"]
    record = {"name": "torch", "version": "2.9.1+cu128", "file": filename.replace("%2B", "+"), "sha256": sha}
    assert builder.official_source(record) == "https://download.pytorch.org/whl/cu128/" + filename
    for key, value in (("sha256", "a" * 64), ("version", "2.9.1+cpu"), ("file", "other.whl")):
        with pytest.raises(ValueError):
            builder.official_source({**record, key: value})


@pytest.mark.parametrize("mutation", [None, "hash", "size", "host", "source"])
def test_pypi_provenance_must_match_the_downloaded_wheel(monkeypatch, mutation):
    record = {"name": "diffusers", "version": "0.35.2", "file": "diffusers.whl", "sha256": "a" * 64, "size": 12}
    source = {"filename": record["file"], "digests": {"sha256": record["sha256"]}, "size": 12,
              "packagetype": "bdist_wheel", "url": "https://files.pythonhosted.org/packages/diffusers.whl"}
    if mutation == "hash":
        source["digests"]["sha256"] = "b" * 64
    elif mutation == "size":
        source["size"] = 13
    elif mutation == "host":
        source["url"] = "https://untrusted.example/wheel"
    elif mutation == "source":
        source["packagetype"] = "sdist"
    calls = []
    def response(url, **kwargs):
        calls.append(url)
        return io.BytesIO(json.dumps({"urls": [source]}).encode())
    monkeypatch.setattr(builder, "urlopen", response)
    if mutation:
        with pytest.raises(ValueError, match="official PyPI"):
            builder.official_source(record)
    else:
        assert builder.official_source(record) == source["url"]
    assert calls == ["https://pypi.org/pypi/diffusers/0.35.2/json"]


@pytest.mark.parametrize("key,value", [("Entrypoint", ["python"]), ("Cmd", ["sh"]), ("OnBuild", ["RUN fetch-secret"])])
def test_image_command_rejects_silent_entrypoint_or_build_hooks(key, value):
    record = image()
    record["Config"][key] = value
    with pytest.raises(ValueError):
        builder.check_image(record)


def test_full_build_keeps_models_drivers_and_credentials_outside_image(tmp_path, monkeypatch):
    output = tmp_path / "new-build"
    calls = []
    inventory = {"packages": {**builder.PINS, "transitive": "1.0"}, "python": "3.11 fixture",
                 "torch_cuda": "12.8", "model_loaded": False}
    def run(command, log):
        calls.append(command)
        if log.name == "download.log":
            for name, version in inventory["packages"].items():
                wheel(output / "wheels", name, version)
        elif log.name in ("install.log", "uid998-offline-import.log"):
            log.write_text("ARENA_LMX_PROBE=" + json.dumps(inventory) + "\n")
    registry_states = iter([None, None, {"reference": REF, "image_id": CHILD_ID}])
    monkeypatch.setattr(builder, "registry_tag", lambda _: next(registry_states))
    monkeypatch.setattr(builder, "inspect", lambda ref: image(builder.BASE_ID if ref == builder.BASE else CHILD_ID))
    monkeypatch.setattr(builder, "run", run)
    monkeypatch.setattr(builder, "official_source", lambda row: "https://files.pythonhosted.org/" + row["file"])
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: b"")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)
    receipt = builder.build(TAG, output, ASSETS)
    assert receipt["image"] == REF and receipt["image_id"] == CHILD_ID
    assert receipt["model_calls"] == 0 and receipt["admitted"] is False
    assert receipt["model_loaded"] is False and receipt["gpu_probe_executed"] is False
    assert receipt["model"]["assets_external"] and receipt["driver_libraries_external"]
    assert receipt["requirements_sha256"] == builder.digest(output / "requirements.lock")
    assert (output / "receipt.json").stat().st_mode & 0o077 == 0
    containers = [command for command in calls if command[:2] == ["docker", "run"]]
    assert len(containers) == 3
    for command in containers:
        assert command[command.index("--cpus") + 1] == "2"
        assert command[command.index("--memory") + 1] == "8g"
        assert "--gpus" not in command and "--device" not in command and "--entrypoint" not in command
        mounts = [command[i + 1] for i, word in enumerate(command) if word == "--mount"]
        assert all("/assets," not in value and ".ssh" not in value and "userland" not in value for value in mounts)
    resolver, installer, smoke = containers
    assert "--only-binary=:all:" in resolver
    assert installer[installer.index("--network") + 1] == "none"
    assert "--require-hashes" in installer[-1] and "--no-index" in installer[-1]
    assert "os.umask(0o022)" in installer[-1] and ".chmod(0o644)" in installer[-1]
    assert "from_pretrained" not in installer[-1]
    assert smoke[smoke.index("--user") + 1] == "998:998"
    assert smoke[smoke.index("--network") + 1] == "none" and "--read-only" in smoke
    assert smoke[smoke.index(CHILD_ID) + 1:][:2] == ["python", "-c"]
    assert calls[-1] == ["docker", "push", TAG]


@pytest.mark.parametrize("mutation", ["local-tag", "remote-tag", "wrong-base", "unsafe-output"])
def test_rejects_identity_or_overwrite_conflicts_before_download(tmp_path, monkeypatch, mutation):
    parent = image(builder.BASE_ID)
    if mutation == "wrong-base":
        parent["Id"] = CHILD_ID
    monkeypatch.setattr(builder, "inspect", lambda _: parent)
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: b"existing" if mutation == "local-tag" else b"")
    monkeypatch.setattr(builder, "registry_tag", lambda _: {} if mutation == "remote-tag" else None)
    monkeypatch.setattr(builder, "run", lambda *a: pytest.fail("Do not start build"))
    output = tmp_path / ("with,comma" if mutation == "unsafe-output" else "new")
    with pytest.raises(ValueError):
        builder.build(TAG, output, ASSETS)
    assert not output.exists()


@pytest.mark.parametrize("mutation", ["retagged", "claimed", "published-other", "missing-repodigest"])
def test_push_never_attests_changed_image_or_overwrites_release(tmp_path, monkeypatch, mutation):
    states = iter([{} if mutation == "claimed" else None,
                   {"reference": REF, "image_id": "other" if mutation == "published-other" else CHILD_ID}])
    monkeypatch.setattr(builder, "registry_tag", lambda _: next(states))
    def inspected(ref):
        value = image()
        if mutation == "retagged" and ref == TAG:
            value["Id"] = "other"
        if mutation == "missing-repodigest" and ref == CHILD_ID:
            value["RepoDigests"] = []
        return value
    calls = []
    monkeypatch.setattr(builder, "inspect", inspected)
    monkeypatch.setattr(builder, "run", lambda command, log: calls.append(command))
    with pytest.raises(ValueError):
        builder.push_verified(TAG, CHILD_ID, tmp_path / "log")
    assert bool(calls) is (mutation in ("published-other", "missing-repodigest"))


@pytest.mark.parametrize("status", [401, 403, 500, 503])
def test_registry_errors_are_not_an_absent_tag(monkeypatch, status):
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        def request(self, *args, **kwargs):
            pass
        def getresponse(self):
            return type("Response", (), {"status": status})()
        def close(self):
            pass
    monkeypatch.setattr(builder.http.client, "HTTPConnection", Client)
    with pytest.raises(ValueError, match="could not be verified"):
        builder.registry_tag(TAG)
