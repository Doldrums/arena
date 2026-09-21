import importlib.util
import json
import os
from pathlib import Path

import pytest

from arena.releases import ReleaseError

spec = importlib.util.spec_from_file_location("release_pr", Path(__file__).resolve().parents[1] / "scripts/check_releases.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_public_pr_accepts_identity_without_resolving_or_running(tmp_path):
    path = tmp_path / "sciel/1.0.4.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"schema": "arena.release/1", "system": "sciel", "version": "1.0.4"}))
    assert module.check(tmp_path) == {"valid": True, "public_references": 1, "private_bindings_checked": False, "execution": False}


@pytest.mark.parametrize("field", ["repository", "image", "api_key"])
def test_private_data_cannot_enter_release_pr(tmp_path, field):
    path = tmp_path / "sciel/1.0.4.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"schema": "arena.release/1", "system": "sciel", "version": "1.0.4", field: "private"}))
    with pytest.raises(ReleaseError):
        module.check(tmp_path)


def test_release_pr_rejects_identity_path_mismatch_and_duplicate_fields(tmp_path):
    path = tmp_path / "sciel/1.0.5.json"
    path.parent.mkdir()
    path.write_text('{"schema":"arena.release/1","system":"sciel","version":"1.0.4"}')
    with pytest.raises(ReleaseError):
        module.check(tmp_path)
    path.write_text('{"schema":"arena.release/1","system":"sciel","version":"1.0.5","version":"1.0.5"}')
    with pytest.raises(ReleaseError):
        module.check(tmp_path)


@pytest.mark.parametrize("entry", ["root-yaml", "nested-yaml", "linked-system", "linked-record",
                                   "dangling-link", "nested-directory", "fifo"])
def test_public_release_check_enumerates_and_rejects_every_forbidden_entry(tmp_path, entry):
    root = tmp_path / "releases"
    root.mkdir()
    system = root / "sciel"
    system.mkdir()
    if entry == "root-yaml":
        (root / "private-binding.yaml").write_text("image: private.example.invalid/repo\n")
    elif entry == "nested-yaml":
        (system / "private-binding.yaml").write_text("repository: private.example.invalid/repo\n")
    elif entry == "linked-system":
        (root / "linked").symlink_to(tmp_path, target_is_directory=True)
    elif entry == "linked-record":
        external = tmp_path / "record.json"
        external.write_text('{"schema":"arena.release/1","system":"sciel","version":"1.0.4"}')
        (system / "1.0.4.json").symlink_to(external)
    elif entry == "dangling-link":
        (root / "missing").symlink_to(tmp_path / "absent", target_is_directory=True)
    elif entry == "nested-directory":
        (system / "hidden").mkdir()
    else:
        os.mkfifo(system / "1.0.4.json")
    with pytest.raises(ReleaseError):
        module.check(root)


def test_release_check_allows_only_the_root_readme_alongside_references(tmp_path):
    (tmp_path / "README.md").write_text("Public release instructions\n")
    assert module.check(tmp_path)["public_references"] == 0
    (tmp_path / "sciel").mkdir()
    (tmp_path / "sciel/README.md").write_text("Not a release reference\n")
    with pytest.raises(ReleaseError):
        module.check(tmp_path)
