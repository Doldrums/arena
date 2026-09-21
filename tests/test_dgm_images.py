"""Inert checks for image-context integrity and the real bootstrap shell."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts/deployment"


def module(name):
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
        value = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(value)
        return value
    finally:
        sys.path.remove(str(SCRIPTS))


prepare = module("prepare_dgm_images")
build = module("build_dgm_images")


def bootstrap(tmp_path):
    for name in ("dgm", "testbed", "root", "tmp"):
        (tmp_path / name).mkdir()
    for name in ("dgm", "testbed", "home"):
        source = tmp_path / "opt" / ("arena-" + name + "-template")
        source.mkdir(parents=True)
        (source / ".hidden-native-data").write_text(name)
    text = prepare.BOOTSTRAP.replace("/opt/", "__SEED_OPT__/").replace("/tmp/", "__SEED_TMP__/")
    text = text.replace("__SEED_OPT__", str(tmp_path / "opt")).replace("__SEED_TMP__", str(tmp_path / "tmp"))
    text = text.replace("destination=/$2", "destination=" + str(tmp_path) + "/$2")
    text = text.replace("exec tail -f /dev/null", "exit 0")
    return text


@pytest.mark.skipif(sys.platform != "linux", reason="Image bootstrap uses GNU cp on native Linux")
def test_bootstrap_copies_hidden_native_data_before_readiness(tmp_path):
    text = bootstrap(tmp_path)
    process = subprocess.run(["/bin/sh"], input=text, text=True, capture_output=True)
    assert process.returncode == 0, process.stderr
    assert (tmp_path / "tmp/.arena-dgm-ready").is_file()
    for target, original in (("dgm", "dgm"), ("testbed", "testbed"), ("root", "home")):
        assert (tmp_path / target / ".hidden-native-data").read_text() == original
        assert (tmp_path / "opt" / ("arena-" + original + "-template") / ".hidden-native-data").read_text() == original


@pytest.mark.skipif(sys.platform != "linux", reason="Image bootstrap uses GNU cp on native Linux")
def test_bootstrap_refuses_existing_work_and_never_marks_it_ready(tmp_path):
    text = bootstrap(tmp_path)
    (tmp_path / "dgm/existing").write_text("preserve")
    process = subprocess.run(["/bin/sh"], input=text, text=True, capture_output=True)
    assert process.returncode != 0
    assert (tmp_path / "dgm/existing").read_text() == "preserve"
    assert not (tmp_path / "tmp/.arena-dgm-ready").exists()


@pytest.mark.skipif(sys.platform != "linux", reason="Image bootstrap uses GNU cp on native Linux")
def test_bootstrap_refuses_symlink_destination(tmp_path):
    text = bootstrap(tmp_path)
    (tmp_path / "testbed").rmdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (tmp_path / "testbed").symlink_to(elsewhere, target_is_directory=True)
    process = subprocess.run(["/bin/sh"], input=text, text=True, capture_output=True)
    assert process.returncode != 0
    assert not list(elsewhere.iterdir())
    assert not (tmp_path / "tmp/.arena-dgm-ready").exists()


def test_context_verification_detects_changed_or_extra_inputs(tmp_path):
    file = tmp_path / "Dockerfile"
    file.write_text("FROM inert@sha256:" + "a" * 64)
    job = {"files": {"Dockerfile": hashlib.sha256(file.read_bytes()).hexdigest()}}
    build.verify_context(tmp_path, job)
    file.write_text("FROM mutable:latest")
    with pytest.raises(ValueError, match="context changed"):
        build.verify_context(tmp_path, job)


def test_context_verification_rejects_symlink_even_when_hash_matches(tmp_path):
    file = tmp_path / "Dockerfile"
    file.symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError, match="symlink"):
        build.verify_context(tmp_path, {"files": {}})


def test_base_resolution_rejects_unreviewed_repositories_without_network():
    with pytest.raises(ValueError, match="reviewed Docker Hub"):
        prepare.resolve_base("unreviewed/private-image", "latest")
