"""Offline Rank contexts: inert fixtures are never claims of benchmark readiness."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "rank_recipe", ROOT / "scripts/deployment/prepare_rankevolve_cpu_image.py")
recipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recipe)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def context(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    source, data, runtime = (root / name for name in ("source", "data", "runtime"))
    data.mkdir()
    runtime.mkdir()
    paths = ["suite/_lib/" + n for n in recipe.HELPERS]
    paths += ["suite/rankevolve-scidocs/" + n for n in ("evaluator.py", "initial_program.py", "problem.json")]
    for name in paths:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "tasks" / name, target)
    monkeypatch.setitem(recipe.DATASETS, "scidocs", (3, 2, 900))
    rows = {
        "public/corpus.jsonl": [{"id": str(i), "text": "inert full text " + str(i)} for i in range(3)],
        "public/queries.jsonl": [{"id": str(i), "text": "inert query"} for i in range(2)],
        "private/qrels.jsonl": [{"id": str(i), "relevance": {str(i): 1}} for i in range(2)],
    }
    files = {}
    for name, entries in rows.items():
        path = data / name
        path.parent.mkdir(exist_ok=True)
        raw = b"".join(json.dumps(row).encode() + b"\n" for row in entries)
        path.write_bytes(raw)
        files[name] = {"bytes": len(raw), "sha256": sha(raw)}
    manifest = {"schema": "arena.rankevolve-data/1", "dataset": "scidocs",
                "source_commit": recipe.SOURCE_COMMIT, "documents": 3, "queries": 2,
                "sample_queries": 0, "warmup_queries": 0, "tokenizer": "candidate.LuceneTokenizer",
                "search_protocol": "exploratory_search_on_test",
                "qrels_semantics": "positive relevance is binary; no graded gain",
                "source": {"kind": "inert_test_fixture"}, "files": files}
    lock = {"schema": "arena.rankevolve-task-data/1", "dataset": "scidocs",
            "candidate_timeout_seconds": 900, "state": "inert_test_fixture"}
    args = {"dataset": "scidocs", "source_root": source, "data_root": data,
            "data_lock": root / "task-lock.json", "runtime_config": root / "config.json",
            "runtime_root": runtime, "output": root / "output"}
    image_config = {"os": "linux", "architecture": "amd64", "rootfs": {"type": "layers", "diff_ids": []},
                    "config": {"User": "", "WorkingDir": "", "Entrypoint": None, "Cmd": ["python3"],
                               "Labels": {"io.arena.fixture": "preserve"},
                               "Env": [name + "=1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                       "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "BM25_QUERY_WORKERS")]}}
    raw = recipe.encoded(image_config)
    args["runtime_config"].write_bytes(raw)
    monkeypatch.setattr(recipe, "RUNTIME_IMAGE", "sha256:" + sha(raw))
    args["runtime_image"] = recipe.RUNTIME_IMAGE
    for name, attr in (("requirements.lock", "REQUIREMENTS_SHA256"), ("wheels.json", "WHEELS_SHA256")):
        raw = ("inert " + name).encode()
        (runtime / name).write_bytes(raw)
        monkeypatch.setattr(recipe, attr, sha(raw))
    value = (args, manifest, lock, image_config)
    repin(value, monkeypatch)
    return value


def repin(context, monkeypatch):
    args, manifest, lock, _ = context
    raw = recipe.encoded(manifest)
    (args["data_root"] / "manifest.json").write_bytes(raw)
    monkeypatch.setitem(recipe.DATA_PINS, "scidocs", sha(raw))
    lock["manifest_sha256"] = sha(raw)
    raw = recipe.encoded(lock)
    args["data_lock"].write_bytes(raw)
    monkeypatch.setitem(recipe.LOCK_PINS, "scidocs", sha(raw))


def test_streams_only_full_reviewed_payload_and_preserves_provenance(context, monkeypatch):
    args, _, _, _ = context
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("No process execution"))
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: pytest.fail("No network"))
    (args["data_root"] / "unrelated.zip").write_bytes(b"not copied")
    plan = recipe.prepare(**args)
    assert plan["image_built"] is False and plan["image_id"] is None
    assert plan["candidate_evaluations"] == plan["model_calls"] == 0
    assert plan["canonical_readiness"] == "pending"
    assert len(plan["roster"]) == 13 and all(row["image_id"] is None for row in plan["roster"])
    assert plan["runtime"]["labels"] == {"io.arena.fixture": "preserve"}
    output = args["output"]
    assert output.stat().st_mode & 0o777 == 0o700
    assert not (output / "data/scidocs/unrelated.zip").exists()
    assert not (output / "source").exists()
    assert plan["files"]["data/scidocs/public/corpus.jsonl"]["records"] == 3
    for name, record in plan["files"].items():
        raw = (output / name).read_bytes()
        assert sha(raw) == record["sha256"] and len(raw) == record["bytes"]
    dockerfile = (output / "Dockerfile").read_text()
    assert dockerfile.count("COPY data/") == 1
    assert not any(token in dockerfile for token in ("pip install", "ENTRYPOINT", "ENV ", "LABEL ", "ADD "))
    assert dockerfile.startswith("FROM " + args["runtime_image"] + "\n")
    compile((output / "support/smoke.py").read_text(), "smoke.py", "exec")
    assert (output / "data/scidocs/public").stat().st_mode & 0o777 == 0o555
    assert (output / "data/scidocs/public/corpus.jsonl").stat().st_mode & 0o777 == 0o444
    ignore = (output / ".dockerignore").read_text()
    assert ignore.startswith("*\n") and "!data/scidocs/public/corpus.jsonl\n" in ignore


@pytest.mark.parametrize("target", ["data", "manifest", "lock", "runtime", "wheels", "requirements", "helper", "seed", "problem"])
def test_changed_bytes_fail_before_publication(context, target):
    args, _, _, _ = context
    paths = {"data": args["data_root"] / "public/corpus.jsonl",
             "manifest": args["data_root"] / "manifest.json", "lock": args["data_lock"],
             "runtime": args["runtime_config"], "wheels": args["runtime_root"] / "wheels.json",
             "requirements": args["runtime_root"] / "requirements.lock",
             "helper": args["source_root"] / "suite/_lib/rankevolve/seed_library.py",
             "seed": args["source_root"] / "suite/rankevolve-scidocs/initial_program.py",
             "problem": args["source_root"] / "suite/rankevolve-scidocs/problem.json"}
    path = paths[target]
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="SHA256|size|hash"):
        recipe.prepare(**args)
    assert not args["output"].exists()
    assert not list(args["output"].parent.glob(".rankevolve-image-*"))


@pytest.mark.parametrize("field,value", [("documents", 2), ("queries", 1), ("sample_queries", 1),
    ("warmup_queries", 1), ("tokenizer", "different"), ("source_commit", "0" * 40),
    ("documents", True), ("search_protocol", "held_out"), ("qrels_semantics", "graded")])
def test_even_rehashed_manifest_cannot_change_full_protocol(context, monkeypatch, field, value):
    context[1][field] = value
    repin(context, monkeypatch)
    with pytest.raises(ValueError, match="counts or protocol"):
        recipe.prepare(**context[0])
    assert not context[0]["output"].exists()


@pytest.mark.parametrize("name", recipe.FILES)
def test_rehashed_truncated_file_fails_physical_record_count(context, monkeypatch, name):
    args, manifest, _, _ = context
    path = args["data_root"] / name
    raw = b"".join(path.read_bytes().splitlines(keepends=True)[:-1])
    path.write_bytes(raw)
    manifest["files"][name] = {"bytes": len(raw), "sha256": sha(raw)}
    repin(context, monkeypatch)
    with pytest.raises(ValueError, match="record count"):
        recipe.prepare(**args)
    assert not args["output"].exists()


@pytest.mark.parametrize("kind", ["data", "parent", "source", "lock", "runtime", "output-parent"])
def test_symlink_components_rejected(context, kind):
    args, _, _, _ = context
    paths = {"data": args["data_root"] / "public/corpus.jsonl", "parent": args["data_root"] / "public",
             "source": args["source_root"] / "suite/_lib/rankevolve/seed_library.py",
             "lock": args["data_lock"], "runtime": args["runtime_config"]}
    if kind == "output-parent":
        link = args["output"].parent / "output-link"
        link.symlink_to(args["data_root"], target_is_directory=True)
        args["output"] = link / "new"
    else:
        path = paths[kind]
        real = path.with_name(path.name + ".real")
        path.rename(real)
        path.symlink_to(real, target_is_directory=real.is_dir())
    with pytest.raises(ValueError, match="symlink"):
        recipe.prepare(**args)


@pytest.mark.parametrize("change", ["image", "cmd", "entrypoint", "platform", "threads", "timeout", "lock-dataset"])
def test_wrong_runtime_or_lock_contract_even_with_fixture_repin(context, monkeypatch, change):
    args, _, lock, config = context
    if change == "image": args["runtime_image"] = recipe.PRIVATE_IMAGE
    elif change in ("timeout", "lock-dataset"):
        lock["candidate_timeout_seconds" if change == "timeout" else "dataset"] = 1 if change == "timeout" else "nq"
        repin(context, monkeypatch)
    else:
        if change == "cmd": config["config"]["Cmd"] = ["sh"]
        elif change == "entrypoint": config["config"]["Entrypoint"] = ["sh"]
        elif change == "platform": config["architecture"] = "arm64"
        else: config["config"]["Env"].append("BM25_QUERY_WORKERS=8")
        raw = recipe.encoded(config)
        args["runtime_config"].write_bytes(raw)
        monkeypatch.setattr(recipe, "RUNTIME_IMAGE", "sha256:" + sha(raw))
        args["runtime_image"] = recipe.RUNTIME_IMAGE
    with pytest.raises(ValueError):
        recipe.prepare(**args)
    assert not args["output"].exists()


def test_inventory_keeps_missing_four_and_all_missing_images_explicit():
    rows = recipe.roster()
    assert len(rows) == 13 and len({r["task_id"] for r in rows}) == 13
    assert {r["dataset"] for r in rows if r["data_status"] == "preparation_pending"} == {"hotpotqa", "fever", "dl19", "dl20"}
    assert all(r["image_id"] is None and r["canonical_readiness"] == "pending" for r in rows)


def test_missing_full_data_and_overlapping_output_refused(context):
    args, _, _, _ = context
    with pytest.raises(ValueError, match="pending"):
        recipe.dataset_inputs("hotpotqa", args["data_root"], args["data_lock"])
    args["output"] = args["source_root"] / "new-image"
    with pytest.raises(ValueError, match="separate"):
        recipe.prepare(**args)
