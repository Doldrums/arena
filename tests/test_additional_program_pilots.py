import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from arena.frameworks.drivers import cpu_program_gateway as driver


def generator():
    path = Path(__file__).resolve().parents[1] / "scripts/deployment/prepare_additional_program_pilots.py"
    spec = importlib.util.spec_from_file_location("additional_program_pilots", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("engine", ["codeevolve", "loongflow", "coevo"])
def test_templates_keep_model_identity_and_evaluation_admission_explicit(tmp_path, engine):
    gen = generator()
    items = [gen.template(tmp_path, engine, model, tmp_path / "configs", {"name": engine}) for model in gen.MODELS]
    assert len(items) == 7 and len({item["id"] for item in items}) == 7
    for item in items:
        assert item["resources"] == {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512}
        assert item["evaluation_concurrency_verified"] is True
        spec = item["spec"]
        assert spec["timeout_seconds"] == 2400 and spec["environment_names"] == ["OPENAI_API_KEY"]
        request = spec["request"]
        assert request["profile"] == "gateway-cpu-pilot"
        if engine == "coevo":
            options = dict(zip(request["arguments"][::2], request["arguments"][1::2]))
            assert options["--model"] == item["model"]
            assert options["--max_gen"] == "1" and options["--pop_size"] == "2"
            assert options["--tls-ca"] in request["inputs"]
            assert options["--hf-manifest"] in request["inputs"]
        else:
            assert list(request["config_overlays"].values())[0].endswith(item["model"] + ".yaml")


def embedding_cache(tmp_path):
    cache = tmp_path / "cache"
    repo = cache / "hub/models--openai-community--gpt2"
    snapshot = repo / "snapshots" / driver.GPT2_REVISION
    snapshot.mkdir(parents=True)
    (repo / "refs").mkdir()
    (repo / "refs/main").write_text(driver.GPT2_REVISION)
    files = {}
    for name in ("config.json", "generation_config.json", "tokenizer_config.json", "tokenizer.json",
                 "vocab.json", "merges.txt", "model.safetensors"):
        data = ("inert cache fixture " + name).encode()
        (snapshot / name).write_bytes(data)
        files[name] = hashlib.sha256(data).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema": "arena.model-cache/1", "model": "openai-community/gpt2",
                                    "revision": driver.GPT2_REVISION, "files": files}))
    return cache, snapshot, manifest


def test_embedding_cache_rejects_rebound_reference_and_tampered_weights(tmp_path):
    cache, snapshot, manifest = embedding_cache(tmp_path)
    assert driver.verify_embedding_cache(cache, manifest)["revision"] == driver.GPT2_REVISION
    (snapshot / "model.safetensors").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        driver.verify_embedding_cache(cache, manifest)
    (cache / "hub/models--openai-community--gpt2/refs/main").write_text("new revision")
    with pytest.raises(ValueError, match="reference"):
        driver.verify_embedding_cache(cache, manifest)


def test_embedding_cache_rejects_symlink_escape(tmp_path):
    cache, snapshot, manifest = embedding_cache(tmp_path)
    target = snapshot / "config.json"
    outside = tmp_path / "external.json"
    outside.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(outside)
    with pytest.raises(ValueError, match="outside"):
        driver.verify_embedding_cache(cache, manifest)


def test_codeevolve_only_discards_tracking_metadata():
    body = {"model": "gpt-6-astra", "user": "user_fixture", "messages": [{"role": "user", "content": "hello"}],
            "temperature": .7, "top_p": .9, "max_completion_tokens": 8192, "seed": None}
    result = json.loads(driver.discard_tracking_metadata(json.dumps(body).encode()))
    assert result == {key: value for key, value in body.items() if key != "user"}
    assert "user_fixture" not in str(result)
    for invalid in (None, 1, {}, "x" * 257):
        with pytest.raises(ValueError, match="user metadata"):
            driver.discard_tracking_metadata(json.dumps({**body, "user": invalid}).encode())


def test_codeevolve_driver_delegates_original_cli_and_never_serializes_key(tmp_path, monkeypatch):
    monkeypatch.setattr(driver.os, "environ", dict(driver.os.environ))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-secret-only")
    monkeypatch.setattr(driver, "configure_codeevolve_transport", lambda: None)
    calls = []
    monkeypatch.setattr(driver.runpy, "run_module", lambda name, **kwargs: calls.append((name, list(driver.sys.argv))))
    driver.main(["--engine", "codeevolve", "--cfg_path", "config.yaml", "--out_dir", "results", "--y"])
    assert calls == [("codeevolve.cli", ["codeevolve", "--cfg_path", "config.yaml", "--out_dir", "results", "--y"])]
    receipt = (tmp_path / "arena-provider-seam.json").read_text()
    assert "fixture-secret-only" not in receipt
    assert json.loads(receipt)["discarded_metadata"] == ["user"]
    assert driver.os.environ["API_KEY"] == "fixture-secret-only"
    assert driver.os.environ["API_BASE"] == "http://127.0.0.1:8789/v1"


def test_coevo_driver_keeps_native_loop_cache_and_tls_before_import(tmp_path, monkeypatch):
    monkeypatch.setattr(driver.os, "environ", dict(driver.os.environ))
    cache, snapshot, manifest = embedding_cache(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-secret-only")
    events = []
    monkeypatch.setattr(driver, "configure_ca", lambda path: events.append(("tls", path)))
    monkeypatch.setattr(driver.runpy, "run_path", lambda name, **kwargs: events.append(("native", name, list(driver.sys.argv))))
    driver.main(["--engine", "coevo", "--model", "gpt-5.6-sol", "--tls-ca", "public.pem",
                 "--hf-cache", str(cache), "--hf-manifest", str(manifest), "--task", "oscillation_1",
                 "--mode", "coevo", "--max_gen", "2", "--pop_size", "2"])
    assert events[0] == ("tls", Path("public.pem"))
    assert events[1][1] == str(tmp_path / "main_run.py")
    assert events[1][2][1:] == ["--task", "oscillation_1", "--mode", "coevo", "--max_gen", "2", "--pop_size", "2"]
    assert driver.os.environ["HF_HUB_OFFLINE"] == "1" and driver.os.environ["TRANSFORMERS_OFFLINE"] == "1"
    assert driver.os.environ["API_URL"] == "https://127.0.0.1:8790/v1/chat/completions"
    assert driver.os.environ["MODEL"] == "gpt-5.6-sol"
    (tmp_path / "model_config.json").write_text("{}")
    with pytest.raises(ValueError, match="credential template"):
        driver.main(["--engine", "coevo", "--model", "gpt-5.6-sol", "--tls-ca", "public.pem",
                     "--hf-cache", str(cache), "--hf-manifest", str(manifest)])
