"""Optional benchmark source installation is explicit and hash-bound."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("source_assets", ROOT / "tasks/scripts/prepare_source_assets.py")
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


def fixture(root, raw=b"// exact fixture source\n"):
    item = dict(path="suite/example/seed.cpp", sha256=hashlib.sha256(raw).hexdigest(),
        url="https://raw.githubusercontent.com/example/project/" + "a" * 40 + "/seed.cpp",
        task_ids=["example"], role="native_seed")
    (root / "catalog").mkdir()
    (root / "catalog/source-assets.json").write_text(json.dumps(
        {"schema": "arena.source-assets/1", "files": [item]}))
    return item


def response(data, url):
    value = io.BytesIO(data)
    value.geturl = lambda: url
    return value


def test_prepare_checks_hash_without_executing_and_is_idempotent(tmp_path):
    item = fixture(tmp_path)
    assert assets.status(tmp_path, item) == "missing"
    assert assets.load_assets(tmp_path) == [item]
    assert assets.prepare(tmp_path, item, lambda url, **kw: response(b"// exact fixture source\n", url)) == "ready"
    assert assets.prepare(tmp_path, item, lambda *a, **kw: pytest.fail("Repeated network request")) == "ready"


def test_hash_mismatch_leaves_no_downloaded_file(tmp_path):
    item = fixture(tmp_path)
    with pytest.raises(ValueError, match="hash"):
        assets.prepare(tmp_path, item, lambda url, **kw: response(b"different", url))
    assert not (tmp_path / item["path"]).exists()


def test_existing_modified_source_is_never_overwritten(tmp_path):
    item = fixture(tmp_path)
    path = tmp_path / item["path"]
    path.parent.mkdir(parents=True)
    path.write_text("local modification")
    with pytest.raises(ValueError, match="differs"):
        assets.prepare(tmp_path, item, lambda *a, **kw: pytest.fail("Must not download"))
    assert path.read_text() == "local modification"


@pytest.mark.parametrize("change", [
    {"path": "../outside.cpp"}, {"path": "/tmp/outside.cpp"},
    {"sha256": "bad"}, {"url": "https://example.com/seed.cpp"},
    {"url": "https://raw.githubusercontent.com/example/project/main/seed.cpp"},
])
def test_lock_rejects_unsafe_or_mutable_records(tmp_path, change):
    item = fixture(tmp_path)
    item.update(change)
    (tmp_path / "catalog/source-assets.json").write_text(json.dumps(
        {"schema": "arena.source-assets/1", "files": [item]}))
    with pytest.raises(ValueError):
        assets.load_assets(tmp_path)


def test_prepare_rejects_symlinked_destination(tmp_path):
    item = fixture(tmp_path)
    (tmp_path / "suite").symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        assets.status(tmp_path, item)


def test_committed_asset_lock_has_no_collection_checkout_dependency():
    locked = assets.load_assets(ROOT / "tasks")
    assert locked and all("IMRUNya" not in item["url"] for item in locked)
