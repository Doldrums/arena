"""Verify image evidence and network boundaries without running Docker."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "catalog_cpu_image", ROOT / "scripts/deployment/build_catalog_cpu_image.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
BASE = "127.0.0.1:5000/empira/canonical-base@sha256:" + "a" * 64
TAG = "127.0.0.1:5000/empira/canonical-small-cpu:test"
DIGEST = TAG.rsplit(":", 1)[0] + "@sha256:" + "b" * 64


def wheel(directory, name, version="1.0", suffix=""):
    path = directory / f"{name.replace('-', '_')}-{version}{suffix}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{name}.dist-info/METADATA", f"Name: {name}\nVersion: {version}\n")
    return path


def test_lock_uses_embedded_identities_exact_versions_and_actual_wheel_bytes(tmp_path):
    a = wheel(tmp_path, "scikit-learn", "1.8.0")
    b = wheel(tmp_path, "joblib", "1.5.2")
    lock, records = builder.wheel_lock(tmp_path, required=["scikit_learn"])
    assert [r["name"] for r in records] == ["joblib", "scikit-learn"]
    for path, name, version in [(a, "scikit-learn", "1.8.0"), (b, "joblib", "1.5.2")]:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert f"{name}=={version} --hash=sha256:{digest}\n" in lock
    assert all("sha256" in row and row["file"].endswith(".whl") for row in records)


def test_vendored_metadata_does_not_override_wheel_distribution_identity(tmp_path):
    path = wheel(tmp_path, "setuptools", "84.0.0")
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("setuptools/_vendor/wheel.dist-info/METADATA", "Name: wheel\nVersion: 0.46.3\n")
    lock, records = builder.wheel_lock(tmp_path, required=["setuptools"])
    assert len(records) == 1
    assert lock.startswith("setuptools==84.0.0 --hash=sha256:")


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "sdist", "symlink"])
def test_lock_rejects_unpinned_or_ambiguous_install_inputs(tmp_path, mutation):
    first = wheel(tmp_path, "numpy")
    if mutation == "duplicate":
        wheel(tmp_path, "NumPy", "2.0")
    elif mutation == "sdist":
        (tmp_path / "source.tar.gz").write_bytes(b"unreviewed build source")
    elif mutation == "symlink":
        (tmp_path / "linked.whl").symlink_to(first)
    required = ["numpy", "scipy"] if mutation == "missing" else ["numpy"]
    with pytest.raises(ValueError):
        builder.wheel_lock(tmp_path, required)


def test_shared_profile_imports_and_distributions_are_all_included():
    from arena.frameworks.sciel_catalog_profile import CPU_DEPENDENCIES
    assert {requirement.removeprefix("py:") for requirement in CPU_DEPENDENCIES} == set(builder.IMPORTS)
    assert {builder.normalize(name) for name in CPU_DEPENDENCIES.values()} == {
        builder.normalize(name) for name in builder.PACKAGES}


def test_build_locks_transitive_inputs_and_installs_without_network_or_engine_code(tmp_path, monkeypatch):
    output = tmp_path.resolve() / "build"
    commands = []
    def inspect(reference):
        return {"Id": "sha256:" + "c" * 64,
                "RepoDigests": [BASE if reference == BASE else DIGEST],
                "Config": {"Entrypoint": None, "Cmd": ["python3"]}}
    def run(command, log):
        commands.append(command)
        if log.name == "download.log":
            for name in builder.PACKAGES:
                wheel(output / "wheels", name)
            wheel(output / "wheels", "transitive-dependency")
        elif log.name == "install.log":
            packages = {name: "1.0" for name in (*builder.PACKAGES, "transitive-dependency")}
            log.write_text("ARENA_PACKAGE_PROBE=" + json.dumps({
                "packages": packages, "solvers": ["CLARABEL"], "python": "3.11 fixture"}) + "\n")
    monkeypatch.setattr(builder, "inspect", inspect)
    monkeypatch.setattr(builder, "run", run)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    result = builder.build(BASE, TAG, output)
    assert result["image"] == DIGEST
    assert result["model_calls"] == 0 and result["research_executed"] is False
    assert result["pip_check"] == "passed"
    assert len(result["wheels"]) == len(builder.PACKAGES) + 1
    assert result["requirements_sha256"] == hashlib.sha256((output / "requirements.lock").read_bytes()).hexdigest()
    assert (output / "receipt.json").stat().st_mode & 0o077 == 0
    resolver, installer = commands[:2]
    for command in (resolver, installer):
        assert command[command.index("--cpus") + 1] == "2"
        assert command[command.index("--memory") + 1] == "8g"
        assert not any("token" in item.lower() or "key=" in item.lower() for item in command)
        assert not any("/tasks" in item or "sciel" in item for item in command)
    assert "--only-binary=:all:" in resolver[-1]
    assert installer[installer.index("--network") + 1] == "none"
    assert "--require-hashes" in installer[-1] and "--no-index" in installer[-1]
    assert "'pip', 'check'" in installer[-1]
    assert "--entrypoint" not in installer
    smoke = next(command for command in commands if "--read-only" in command)
    assert "--entrypoint" not in smoke
    assert smoke[smoke.index(TAG) + 1:][:2] == ["python", "-c"]
    assert result["canonical_command_probe"] == "passed"


@pytest.mark.parametrize("entrypoint", [["python"], ["/bin/sh", "-c"], "python"])
def test_image_entrypoint_cannot_silently_prepend_python_to_the_canonical_command(entrypoint):
    with pytest.raises(ValueError, match="no entrypoint"):
        builder.verify_image_command({"Config": {"Entrypoint": entrypoint, "Cmd": ["python3"]}})


@pytest.mark.parametrize("base,tag", [
    ("python:latest", TAG), (BASE, "public.example/evaluator:latest"),
    (BASE.replace("127.0.0.1:5000", "user:secret@example.org"), TAG),
])
def test_rejects_unpinned_or_credential_bearing_image_references(tmp_path, monkeypatch, base, tag):
    def unexpected(*args):
        raise AssertionError("Invalid references must not reach Docker")
    monkeypatch.setattr(builder, "inspect", unexpected)
    with pytest.raises(ValueError):
        builder.build(base, tag, tmp_path.resolve() / "build")
