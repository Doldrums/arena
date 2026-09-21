"""Shared inert fixtures; no provider calls, container builds or research runs."""
import subprocess

import pytest

from arena import release_deployment as deployment
from arena.releases import public_release, register_release


@pytest.fixture
def release_fixture(tmp_path):
    source = tmp_path / "private-source"
    source.mkdir()
    # Planning must never import or execute source code.
    (source / "research.py").write_text("raise RuntimeError('must not execute private source during preparation')\n")
    for args in (["init", "-q"], ["add", "research.py"], ["-c", "user.name=Fixture", "-c", "user.email=fixture@localhost", "commit", "-qm", "inert source"]):
        subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True)
    commit = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    binding = {"schema": "arena.private-release/1", "system": "sciel", "version": "0.0.0-inert-test",
               "repository": {"url": "https://code.example.invalid/private/sciel", "commit": commit},
               "image": "registry.example.invalid/private/sciel@sha256:" + "a" * 64}
    reference = public_release(binding)
    store = tmp_path / "store"
    register_release(store, binding)
    inspection = [{"Id": "sha256:" + "b" * 64, "RepoDigests": [binding["image"]],
                   "Config": {"Entrypoint": deployment.ENTRYPOINT,
                              "Labels": {"org.opencontainers.image.revision": commit,
                                         "org.opencontainers.image.source": binding["repository"]["url"],
                                         "io.arena.sciel.contract": deployment.CONTRACT,
                                         "private-unrelated-label": "not-for-manifest"},
                              "Env": ["FIXTURE_SECRET=must-not-be-projected"]}}]
    output = tmp_path / "manifests"
    output.mkdir(mode=0o700)
    manifest = deployment.prepare_deployment(reference, store, source, inspection,
                                              broker_socket=tmp_path / "private-image.sock",
                                              operator="fixture-operator", review_reference="review-123")
    path = output / "deployment.json"
    digest = deployment.write_manifest(path, manifest)
    return {"source": source, "binding": binding, "reference": reference, "store": store,
            "inspection": inspection, "manifest": manifest, "path": path, "digest": digest}

