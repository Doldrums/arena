"""Offline context preparation; fixtures never claim a built or evaluated image."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import urllib.request

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "science5_recipe", ROOT / "scripts/deployment/prepare_science5_cpu_image.py")
recipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recipe)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def context(tmp_path, monkeypatch):
    base = tmp_path.resolve()
    cache, wheels = base / "cache", base / "wheels"
    cache.mkdir()
    wheels.mkdir()
    packages = {**recipe.PRESERVED_RUNTIME, **{f"fixture-package-{i}": "1.0" for i in range(42)}}
    base_receipt = {"image": recipe.BASE, "image_id": recipe.BASE_ID,
                    "validation": {"packages": packages}}
    files = []
    names = {req.removeprefix("file:").removeprefix("../../.cache/")
             for task in recipe.TASKS.values() for req in task["requirements"] if req.startswith("file:")}
    assert len(names) == 9
    for name in sorted(names):
        path = cache / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = ("inert data fixture " + name).encode()
        path.write_bytes(raw)
        files.append({"path": name, "sha256": sha(raw), "bytes": len(raw), "role": "runtime_data"})
    data_lock = {"files": files, "task_details": {name: {} for name in recipe.TASKS}}
    additions = []
    for name, version in recipe.RUNTIME_ADDITIONS.items():
        raw = ("inert wheel fixture " + name).encode()
        filename = f"{name}-{version}-cp311-none-linux_x86_64.whl"
        (wheels / filename).write_bytes(raw)
        additions.append({"package": name, "version": version, "filename": filename,
                          "sha256": sha(raw), "bytes": len(raw),
                          "url": "https://files.pythonhosted.org/packages/fixture/" + filename})
    monkeypatch.setattr(recipe, "WHEEL_PINS", {row["package"]: row["sha256"] for row in additions})
    args = {"cache_root": cache, "wheels": wheels, "output": base / "output"}
    records = {"data_lock": data_lock, "base_receipt": base_receipt, "wheel_lock": {"files": additions}}
    for name, value in records.items():
        args[name] = base / (name + ".json")
        raw = recipe.encode(value)
        args[name].write_bytes(raw)
        monkeypatch.setattr(recipe, name.upper() + "_SHA256", sha(raw))
    return args, records


def test_recipe_is_exact_offline_data_and_dependency_closure(context, monkeypatch):
    args, _ = context
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("No process execution"))
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: pytest.fail("No network"))
    (args["cache_root"] / "unrelated-source-archive.zip").write_bytes(b"must not be included")
    (args["wheels"] / "preparation-only-package.whl").write_bytes(b"must not be included")
    plan = recipe.prepare(**args)
    assert plan["image_built"] is False and plan["canonical_readiness"] == "pending"
    assert plan["model_calls"] == plan["candidate_evaluations"] == 0
    assert plan["data_files"] == 9 and plan["base_package_count"] == 45
    assert plan["added_packages"] == {"viennarna": "2.6.4", "rdkit": "2026.3.6"}
    out = args["output"]
    installed = json.loads((out / "expected-packages.json").read_bytes())
    assert len(installed) == 47 and installed["pillow"] == "12.3.0"
    assert len(list((out / "wheels").iterdir())) == 2
    assert not (out / "data/unrelated-source-archive.zip").exists()
    assert (out.stat().st_mode & 0o777) == 0o700
    for name, record in plan["files"].items():
        raw = (out / name).read_bytes()
        assert sha(raw) == record["sha256"] and len(raw) == record["bytes"]
        assert (out / name).stat().st_mode & 0o777 == 0o600
    for name in ("install.py", "smoke.py"):
        compile((out / name).read_text(), name, "exec")
    assert "--no-deps" in (out / "install.py").read_text()
    assert "actual == expected" in (out / "smoke.py").read_text()


@pytest.mark.parametrize("input_name", ["data_lock", "wheel_lock", "base_receipt", "data_file", "wheel_file"])
def test_tampered_input_never_creates_partial_recipe(context, input_name):
    args, records = context
    if input_name == "data_file": path = args["cache_root"] / records["data_lock"]["files"][0]["path"]
    elif input_name == "wheel_file": path = args["wheels"] / records["wheel_lock"]["files"][0]["filename"]
    else: path = args[input_name]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="SHA256|size"):
        recipe.prepare(**args)
    assert not args["output"].exists()


@pytest.mark.parametrize("kind", ["data", "wheel", "parent", "lock"])
def test_symlinked_files_and_parents_are_rejected(context, kind):
    args, records = context
    if kind == "data": path = args["cache_root"] / records["data_lock"]["files"][0]["path"]
    elif kind == "wheel": path = args["wheels"] / records["wheel_lock"]["files"][0]["filename"]
    elif kind == "parent": path = args["cache_root"] / "science-biology"
    else: path = args["data_lock"]
    renamed = path.with_name(path.name + "-real")
    path.rename(renamed)
    path.symlink_to(renamed, target_is_directory=renamed.is_dir())
    with pytest.raises(ValueError, match="symlink"):
        recipe.prepare(**args)
    assert not args["output"].exists()


@pytest.mark.parametrize("input_name", ["cache_root", "wheels"])
def test_output_cannot_modify_any_input_tree(context, input_name):
    args, _ = context
    args["output"] = args[input_name] / "new-output"
    with pytest.raises(ValueError, match="separate"):
        recipe.prepare(**args)


@pytest.mark.parametrize("bad_path", ["../secret", "/root/secret", "data/../secret", "a//b", "a\\b", ".", ""])
def test_noncanonical_data_paths_rejected(bad_path):
    with pytest.raises(ValueError, match="relative path"):
        recipe.relative(bad_path)


@pytest.mark.parametrize("change", ["pillow", "numpy", "extra", "replaced", "base", "source", "duplicate"])
def test_recipe_contract_rejects_changed_proofs_even_if_rehashed(context, monkeypatch, change):
    args, records = context
    if change in ("pillow", "numpy", "extra", "replaced", "base"):
        name = "base_receipt"
        packages = records[name]["validation"]["packages"]
        if change == "base": records[name]["image_id"] = "sha256:" + "0" * 64
        elif change == "replaced": packages["rdkit"] = "2026.3.6"
        else: packages[change] = "unexpected"
    else:
        name = "wheel_lock"
        if change == "source": records[name]["files"][0]["url"] = "https://example.invalid/evil.whl"
        else: records[name]["files"].append(records[name]["files"][0])
    raw = recipe.encode(records[name])
    args[name].write_bytes(raw)
    monkeypatch.setattr(recipe, name.upper() + "_SHA256", sha(raw))
    with pytest.raises(ValueError):
        recipe.prepare(**args)
    assert not args["output"].exists()
