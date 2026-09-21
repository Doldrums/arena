from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import stat

import pytest

from arena.releases import (MAX_RECORD_BYTES, ReleaseError, ReleaseNotFound, main, public_release,
                            register_release, resolve_release,
                            validate_private_release, validate_public_release)


@pytest.fixture
def binding():
    return {"schema": "arena.private-release/1", "system": "example-system", "version": "1.0.4",
            "repository": {"url": "https://code.example.invalid/private/system", "commit": "a" * 40},
            "image": "registry.example.invalid/private/system@sha256:" + "b" * 64}


def test_public_projection_is_exact_identity_without_private_pointers(binding):
    original = deepcopy(binding)
    projected = public_release(binding)
    assert projected == {"schema": "arena.release/1", "system": "example-system", "version": "1.0.4"}
    assert binding == original
    assert "private" not in json.dumps(projected)
    assert validate_public_release(projected) == projected


@pytest.mark.parametrize("extra", ["repository", "image", "commit", "api_key", "token", "url", "credentials", "private_release"])
def test_public_record_rejects_every_pointer_or_secret_field(binding, extra):
    value = public_release(binding)
    value[extra] = "must-not-be-disclosed"
    with pytest.raises(ReleaseError) as error:
        validate_public_release(value)
    assert "must-not-be-disclosed" not in str(error.value)


@pytest.mark.parametrize("change", [
    lambda r: r.update(api_key="must-not-be-disclosed"),
    lambda r: r["repository"].update(token="must-not-be-disclosed"),
    lambda r: r["repository"].update(commit="main"),
    lambda r: r["repository"].update(commit="a" * 39),
    lambda r: r["repository"].update(url="https://must-not-be-disclosed@code.example.invalid/repo"),
    lambda r: r["repository"].update(url="https://@code.example.invalid/repo"),
    lambda r: r["repository"].update(url="https://code.example.invalid/repo?token=must-not-be-disclosed"),
    lambda r: r["repository"].update(url="https://code.example.invalid:invalid/repo"),
    lambda r: r.update(image="registry.example.invalid/private/system:latest"),
    lambda r: r.update(image="registry.example.invalid/private/system:tag@sha256:" + "b" * 64),
    lambda r: r.update(system="../../escape"),
    lambda r: r.update(version="latest"),
    lambda r: r.update(version="1.0.4-01"),
])
def test_private_record_rejects_mutable_or_credential_bearing_bindings(binding, change):
    change(binding)
    with pytest.raises(ReleaseError) as error:
        validate_private_release(binding)
    assert "must-not-be-disclosed" not in str(error.value)


def test_registration_resolves_privately_and_is_idempotent_without_rebinding(binding, tmp_path):
    root = tmp_path / "worker-store"
    reference = register_release(root, binding)
    path = root / binding["system"] / "1.0.4.json"
    before = path.stat()
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(before.st_mode) == 0o600
    assert resolve_release(root, reference) == binding
    assert register_release(root, deepcopy(binding)) == reference
    assert path.stat().st_ino == before.st_ino and path.stat().st_mtime_ns == before.st_mtime_ns
    for field in ("commit", "image"):
        changed = deepcopy(binding)
        if field == "commit":
            changed["repository"]["commit"] = "c" * 40
        else:
            changed["image"] = "registry.example.invalid/private/system@sha256:" + "d" * 64
        with pytest.raises(ReleaseError, match="immutable"):
            register_release(root, changed)
        assert resolve_release(root, reference) == binding
    assert not list(path.parent.glob(".pending-*"))


def test_python_registration_bounds_serialized_record_before_any_publication(binding, tmp_path):
    root = tmp_path / "worker-store"
    oversized = deepcopy(binding)
    # The image string itself fits the limit; the full encoded record does not.
    oversized["image"] = "a" * (MAX_RECORD_BYTES - 150) + "@sha256:" + "b" * 64
    assert len(oversized["image"]) < MAX_RECORD_BYTES
    with pytest.raises(ReleaseError, match="size limit"):
        register_release(root, oversized)
    assert not root.exists()
    # A failed oversized attempt has not consumed the immutable version.
    reference = register_release(root, binding)
    assert resolve_release(root, reference) == binding


def test_largest_accepted_encoded_binding_remains_resolvable(binding, tmp_path):
    overhead = len((json.dumps(binding, sort_keys=True, indent=2) + "\n").encode()) - len(binding["image"])
    suffix = "@sha256:" + "b" * 64
    binding["image"] = "a" * (MAX_RECORD_BYTES - overhead - len(suffix)) + suffix
    root = tmp_path / "worker-store"
    reference = register_release(root, binding)
    record = root / binding["system"] / (binding["version"] + ".json")
    assert record.stat().st_size == MAX_RECORD_BYTES
    assert resolve_release(root, reference) == binding


def test_concurrent_different_bindings_publish_exactly_one_complete_record(binding, tmp_path):
    root = tmp_path / "worker-store"
    other = deepcopy(binding)
    other["repository"]["commit"] = "c" * 40
    def attempt(value):
        try:
            return register_release(root, value)
        except ReleaseError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, (binding, other)))
    assert sum(r is not None for r in results) == 1
    assert resolve_release(root, public_release(binding)) in (binding, other)
    assert not list(root.rglob(".pending-*"))


def test_missing_release_fails_closed_without_creating_a_store(binding, tmp_path):
    root = tmp_path / "missing"
    with pytest.raises(ReleaseNotFound):
        resolve_release(root, public_release(binding))
    assert not root.exists()
    register_release(root, binding)
    missing = {**public_release(binding), "version": "1.0.5"}
    with pytest.raises(ReleaseNotFound):
        resolve_release(root, missing)
    assert not (root / binding["system"] / "1.0.5.json").exists()


@pytest.mark.parametrize("damage", ["truncated", "wrong-identity", "symlink", "permissions", "extra-field", "duplicate-field", "fifo"])
def test_corrupt_or_unprivate_records_are_never_resolved(binding, tmp_path, damage):
    root = tmp_path / "worker-store"
    reference = register_release(root, binding)
    path = root / binding["system"] / "1.0.4.json"
    if damage == "truncated":
        path.write_text('{"schema":')
    elif damage == "wrong-identity":
        path.write_text(json.dumps({**binding, "version": "1.0.5"}))
    elif damage == "symlink":
        external = tmp_path / "external.json"
        external.write_text(path.read_text())
        path.unlink()
        path.symlink_to(external)
    elif damage == "permissions":
        path.chmod(0o644)
    elif damage == "duplicate-field":
        path.write_text(json.dumps(binding)[:-1] + ',"version":"1.0.4"}')
    elif damage == "fifo":
        path.unlink()
        os.mkfifo(path, 0o600)
    else:
        path.write_text(json.dumps({**binding, "credential": "unrecorded-secret"}))
    with pytest.raises(ReleaseError):
        resolve_release(root, reference)


def test_private_store_cannot_be_public_or_a_symlink(binding, tmp_path):
    public = tmp_path / "web"
    for root in (public, public / "nested", tmp_path):
        with pytest.raises(ReleaseError, match="outside public/source"):
            register_release(root, binding, public_roots=[public])
    actual = tmp_path / "actual"
    actual.mkdir(mode=0o700)
    link = tmp_path / "link"
    link.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ReleaseError, match="non-symlink"):
        register_release(link, binding)
    assert not list(actual.iterdir())
    open_store = tmp_path / "open-store"
    open_store.mkdir(mode=0o755)
    with pytest.raises(ReleaseError, match="accessible only"):
        register_release(open_store, binding)
    assert stat.S_IMODE(open_store.stat().st_mode) == 0o755


def test_cli_register_emits_public_only_and_missing_resolution_never_echoes_input(binding, tmp_path, capsys):
    record = tmp_path / "registration.json"
    record.write_text(json.dumps(binding))
    root = tmp_path / "worker-store"
    assert main(["register", str(record), "--store", str(root)]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == public_release(binding)
    assert binding["repository"]["url"] not in output.out
    record.write_text(json.dumps({**public_release(binding), "image": "must-not-be-disclosed"}))
    with pytest.raises(SystemExit) as error:
        main(["resolve", str(record), "--store", str(root)])
    assert error.value.code == 2
    output = capsys.readouterr()
    assert output.out == "" and "must-not-be-disclosed" not in output.err


def test_example_files_are_explicit_placeholders_not_registered_releases():
    root = Path(__file__).resolve().parents[1] / "examples/releases"
    private = json.loads((root / "private-binding.example.json").read_text())
    public = json.loads((root / "public-reference.example.json").read_text())
    assert public_release(private) == public
    assert public["system"] == "example-system" and public["version"] == "0.0.0-example"
    assert ".invalid/" in private["repository"]["url"]


def test_cli_rejects_duplicate_fields_before_registration(binding, tmp_path, capsys):
    record = tmp_path / "registration.json"
    record.write_text(json.dumps(binding)[:-1] + ',"version":"1.0.4"}')
    store = tmp_path / "never-created"
    with pytest.raises(SystemExit) as error:
        main(["register", str(record), "--store", str(store)])
    assert error.value.code == 2
    assert not store.exists()
    output = capsys.readouterr()
    assert output.out == "" and binding["repository"]["url"] not in output.err
