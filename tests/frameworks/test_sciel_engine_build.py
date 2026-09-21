"""Offline build-input validation; never starts Docker, native code or providers."""
import hashlib
import importlib.util
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
