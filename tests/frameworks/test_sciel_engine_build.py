"""Offline build-input validation; never starts Docker, native code or providers."""
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("sciel_engine_build", ROOT / "scripts/deployment/build_sciel_engine.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_inventory_excludes_only_the_two_separately_snapshotted_local_sources():
    rows = builder.pinned_requirements("torch==2.14.0+cpu\nPyYAML==6.0.3\nsciel @ file:///build/sciel\nresearch-arena @ file:///app\n")
    assert rows == {"torch": "2.14.0+cpu", "pyyaml": "6.0.3"}
    for bad in ("other @ file:///private", "pkg>=1.0", "pkg @ https://token@example.com/pkg.whl", "torch==2.14.0+cpu\nTorch==2.14.0+cpu"):
        with pytest.raises(ValueError):
            builder.pinned_requirements(bad)


def wheel(path, name, version):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{name}-{version}.dist-info/METADATA", f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")


def test_locked_wheels_match_metadata_inventory_and_exact_bytes(tmp_path):
    path = tmp_path / "pinned.whl"
    wheel(path, "Some_Package", "1.2.3")
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("vendor/other-9.0.dist-info/METADATA", "Name: other\nVersion: 9.0\n")
    lock, rows = builder.wheel_lock(tmp_path, {"some-package": "1.2.3"})
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert lock == f"some-package==1.2.3 --hash=sha256:{digest}\n"
    assert rows["some-package"]["sha256"] == digest
    with pytest.raises(ValueError, match="identity"):
        builder.wheel_lock(tmp_path, {"some-package": "1.2.4"})
    with pytest.raises(ValueError, match="missing"):
        builder.wheel_lock(tmp_path, {"some-package": "1.2.3", "missing": "0.1"})
    wheel(tmp_path / "duplicate.whl", "some-package", "1.2.3")
    with pytest.raises(ValueError, match="identity"):
        builder.wheel_lock(tmp_path, {"some-package": "1.2.3"})


def test_arena_snapshot_hash_tracks_changes_and_refuses_linked_host_files(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "module.py").write_text("VERSION = 1\n")
    before, records = builder.snapshot_files(source)
    assert records == {"module.py": hashlib.sha256(b"VERSION = 1\n").hexdigest()}
    (source / "module.py").write_text("VERSION = 2\n")
    assert builder.snapshot_files(source)[0] != before
    (source / "external").symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError, match="symlinks"):
        builder.snapshot_files(source)


def test_image_contract_is_validated_before_push_and_matches_release_validator():
    from copy import deepcopy
    from arena.release_deployment import CONTRACT, ENTRYPOINT
    identity = {"Architecture": "amd64", "Config": {"User": "998:998", "Entrypoint": ENTRYPOINT,
        "Labels": {"org.opencontainers.image.revision": builder.PIN,
                   "org.opencontainers.image.source": "https://github.com/Doldrums/sciel",
                   "org.opencontainers.image.version": builder.VERSION,
                   "io.arena.sciel.contract": CONTRACT}}}
    assert builder.validate_image_config(identity, builder.VERSION)["io.arena.sciel.contract"] == CONTRACT
    for key in identity["Config"]["Labels"]:
        changed = deepcopy(identity)
        del changed["Config"]["Labels"][key]
        with pytest.raises(ValueError, match="release contract"):
            builder.validate_image_config(changed, builder.VERSION)
    for key, value in (("Entrypoint", ["python", "other.py"]), ("User", "0:0")):
        changed = deepcopy(identity)
        changed["Config"][key] = value
        with pytest.raises(ValueError, match="entrypoint or user"):
            builder.validate_image_config(changed, builder.VERSION)
    dockerfile = (ROOT / "scripts/deployment/sciel-engine/Dockerfile").read_text()
    assert f'io.arena.sciel.contract="{CONTRACT}"' in dockerfile


def test_explicit_release_pins_reject_mutable_refs_and_mismatched_image_revision():
    from arena.release_deployment import CONTRACT, ENTRYPOINT
    commit, version = "e" * 40, "0.3.0+arena.reviewed.worker1"
    assert builder.release_identity(commit, version)["version"] == version
    for value in ("main", "v0.3.0", "e" * 12, "E" * 40):
        with pytest.raises(ValueError, match="immutable Git commit"):
            builder.release_identity(value, version)
    for value in ("latest", "0.3", "0.3.0\n"):
        with pytest.raises(ValueError):
            builder.release_identity(commit, value)
    identity = {"Architecture": "amd64", "Config": {"User": "998:998", "Entrypoint": ENTRYPOINT,
        "Labels": {"org.opencontainers.image.revision": commit,
                   "org.opencontainers.image.source": "https://github.com/Doldrums/sciel",
                   "org.opencontainers.image.version": version,
                   "io.arena.sciel.contract": CONTRACT}}}
    assert builder.validate_image_config(identity, version, commit)["org.opencontainers.image.revision"] == commit
    with pytest.raises(ValueError, match="release contract"):
        builder.validate_image_config(identity, version, "f" * 40)


def test_source_package_version_must_match_the_release_not_just_the_image_label(tmp_path):
    project = tmp_path / "pyproject.toml"
    project.write_text('[project]\nname="sciel"\nversion="0.2.0"\n')
    assert builder.source_package_version(tmp_path, "0.2.0+arena.worker1") == "0.2.0"
    with pytest.raises(ValueError, match="differs"):
        builder.source_package_version(tmp_path, "0.3.0+arena.worker1")
    project.write_text('[project]\nname="other-package"\nversion="0.2.0"\n')
    with pytest.raises(ValueError, match="differs"):
        builder.source_package_version(tmp_path, "0.2.0+arena.worker1")
    project.unlink()
    project.symlink_to(tmp_path / "external.toml")
    with pytest.raises(ValueError, match="regular pyproject"):
        builder.source_package_version(tmp_path, "0.2.0+arena.worker1")


@pytest.fixture
def bundled_app(tmp_path, monkeypatch):
    from arena import registry
    app = tmp_path / "app"
    for name in ("src/arena", "registry", "schemas", "tasks/suite/task"):
        (app / name).mkdir(parents=True)
    (app / "src/arena/__init__.py").write_text("# fixture runtime\n")
    files = {"suite/task/evaluator.py": b"raise AssertionError('Never import')\n",
             "suite/task/initial_program.py": b"raise AssertionError('Never execute')\n",
             "run.py": b"# fixture runner\n"}
    for name, payload in files.items():
        (app / "tasks" / name).write_bytes(payload)
    manifest = app / "registry/task-library-manifest.json"
    manifest.write_text(json.dumps({"schema": "arena.task-library/1", "files": {
        key: hashlib.sha256(value).hexdigest() for key, value in files.items()}}))
    source = {"id": "arena-tasks", "kind": "bundled", "root_path": "tasks",
              "manifest_path": "registry/task-library-manifest.json",
              "manifest_sha256": builder.digest(manifest)}
    monkeypatch.setattr(registry, "get_catalog", lambda _: {"sources": [source]})
    return app, source


def test_image_snapshot_contains_verified_tasks_without_importing_them(bundled_app, tmp_path):
    app, source = bundled_app
    # Normal pip bytecode exists but never belongs in the immutable image snapshot.
    cache = app / "tasks/__pycache__"
    cache.mkdir()
    (cache / "run.cpython-311.pyc").write_bytes(b"ignored installed cache")
    target = tmp_path / "context/arena"
    identity = builder.snapshot_arena(app, target)
    assert identity["manifest_sha256"] == source["manifest_sha256"]
    assert (target / "tasks/run.py").read_bytes() == (app / "tasks/run.py").read_bytes()
    assert not (target / "tasks/__pycache__").exists()
    assert set(builder.snapshot_files(target)[1]) >= {
        "tasks/run.py", "tasks/suite/task/initial_program.py", "registry/task-library-manifest.json"}


def test_tampered_task_fails_before_image_snapshot(bundled_app, tmp_path):
    app, _ = bundled_app
    (app / "tasks/run.py").write_text("modified runner")
    target = tmp_path / "context/arena"
    with pytest.raises(ValueError, match="digest mismatch"):
        builder.snapshot_arena(app, target)
    assert not target.exists()


def test_changed_task_during_copy_cannot_pass_image_snapshot(bundled_app, tmp_path, monkeypatch):
    app, _ = bundled_app
    original = builder.shutil.copytree

    def copy(source, destination, *args, **kwargs):
        result = original(source, destination, *args, **kwargs)
        if Path(source) == app / "tasks":
            (Path(destination) / "run.py").write_text("mutated after copy")
        return result

    monkeypatch.setattr(builder.shutil, "copytree", copy)
    with pytest.raises(ValueError, match="digest mismatch"):
        builder.snapshot_arena(app, tmp_path / "context/arena")


def test_docker_build_checks_dependency_closure_and_bundled_task_integrity():
    text = (ROOT / "scripts/deployment/sciel-engine/Dockerfile").read_text()
    assert "python -m pip check" in text
    assert "verify_task_library(resolve_task_root(source=s), s)" in text
