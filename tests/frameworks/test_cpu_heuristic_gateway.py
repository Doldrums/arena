"""Inert provider transport/config fixtures; no native search or network calls."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

from arena.frameworks.drivers import base_gateway, cpu_heuristic_gateway


def gateway_module(monkeypatch, client):
    native = ModuleType("utils.llm_client.openai")
    class NativeClient:
        def __init__(self, model, temperature, base_url, api_key):
            self.model, self.client = model, client
    native.OpenAIClient = NativeClient
    monkeypatch.setitem(sys.modules, "utils.llm_client.openai", native)
    path = Path(base_gateway.__file__).with_name("reevo_gateway.py")
    spec = importlib.util.spec_from_file_location("gateway_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reevo_batch_preserves_exact_model_order_and_choices_with_n_one(monkeypatch):
    calls, options = [], []
    class Choice:
        def __init__(self, text, index=0):
            self.message, self.index = SimpleNamespace(content=text), index
        def model_copy(self, update):
            return Choice(self.message.content, update["index"])
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[Choice(f"draw {len(calls)}")])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    client.with_options = lambda **kw: (options.append(kw), client)[1]
    module = gateway_module(monkeypatch, client)
    transport = module.GatewayClient("codex-auto-review", base_url="http://127.0.0.1:8789/v1", api_key="fixture")
    messages = [{"role": "user", "content": "fixture"}]
    choices = transport._chat_completion_api(messages, 1.3, n=3)
    assert [c.message.content for c in choices] == ["draw 1", "draw 2", "draw 3"]
    assert [c.index for c in choices] == [0, 1, 2]
    assert all(c == dict(model="codex-auto-review", messages=messages, temperature=1.3, n=1, stream=False) for c in calls)
    assert options == [{"timeout": 180.0, "max_retries": 0}]
    for invalid in (0, 9, True, 2.5):
        with pytest.raises(ValueError): transport._chat_completion_api(messages, 1, invalid)
    assert len(calls) == 3


def test_base_transport_does_not_substitute_models_and_unknown_cost_is_not_zero():
    calls = []
    transport = base_gateway.omit_unsupported_seed(lambda **kw: calls.append(kw), "gpt-6-astra")
    transport(model="gpt-6-astra", seed=42, temperature=.4, messages=[])
    assert calls == [{"model": "gpt-6-astra", "temperature": .4, "messages": []}]
    with pytest.raises(ValueError): transport(model="Qwen/Qwen3-8B", seed=42)
    with pytest.raises(ValueError): transport(model="gpt-6-astra", extra_body={})
    result = base_gateway.erase_unmeasured_flops({"total_flops": 0, "flops_per_round": [0], "cumulative_flops": [0], "final_best_fitness": 1.25, "rewards": [1.2, 1.25]})
    assert result["final_best_fitness"] == 1.25 and result["rewards"] == [1.2, 1.25]
    assert all(result[name] is None for name in ("total_flops", "flops_per_round", "cumulative_flops", "params_active"))


def test_hsevo_wrapper_only_routes_endpoint_then_invokes_native_entrypoint(monkeypatch, tmp_path):
    import json
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-only")
    monkeypatch.setenv("OPENAI_API_BASE", "https://wrong.invalid")
    observed = []
    monkeypatch.setattr(cpu_heuristic_gateway.runpy, "run_path", lambda path, run_name: observed.append((path, run_name, list(sys.argv))))
    monkeypatch.setattr(sys, "argv", ["fixture"])
    cpu_heuristic_gateway.main(["--engine", "hsevo", "--", "algorithm=hsevo", "problem=bpp_online"])
    assert observed == [(str(tmp_path / "main.py"), "__main__", [str(tmp_path / "main.py"), "algorithm=hsevo", "problem=bpp_online"])]
    import os
    assert os.environ["OPENAI_API_BASE"] == "http://127.0.0.1:8789/v1"
    proof = json.loads((tmp_path / "arena-provider-seam.json").read_text())
    assert proof["native_loop_modified"] is False and proof["canonical_evaluation"] is False
    assert "fixture-only" not in (tmp_path / "arena-provider-seam.json").read_text()


def test_native_configuration_keeps_exact_alias_and_gateway_key_reference(tmp_path):
    import json
    path = Path(__file__).resolve().parents[2] / "scripts/deployment/prepare_cpu_heuristics.py"
    spec = importlib.util.spec_from_file_location("pilot_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "cfg").mkdir()
    source = "defaults: [{problem: bpp_online}]\nnative_option: preserved\n" + "".join(key+": 10\n" for key in ("max_fe", "pop_size", "init_pop_size", "timeout", "model", "max_tokens", "enable_thinking", "n_parallel", "hm_size", "max_iter", "mutation_rate"))
    (tmp_path / "cfg/config.yaml").write_text(source)
    for model in module.MODELS:
        for engine in ("reevo", "hsevo", "mcts-ahd"):
            overlays = module.configured(tmp_path, engine, model)
            config = overlays["cfg/config.yaml"]
            assert "native_option: preserved\n" in config
            assert "pop_size: 2\n" in config and "init_pop_size: 2\n" in config
            if engine == "hsevo":
                assert 'model: "openai/' + model + '"' in config
                assert "enable_thinking: false\n" in config
                assert "hm_size: 2\n" in config and "max_iter: 1\n" in config
            else:
                client = json.loads(overlays["cfg/llm_client/openai.yaml"])
                assert client["model"] == model
                assert client["api_key"] == "${oc.env:OPENAI_API_KEY}"
                assert client["base_url"] == "http://127.0.0.1:8789/v1"
    with pytest.raises(ValueError): module.configured(tmp_path, "base", "invented-alias")
    (tmp_path / "cfg/config.yaml").write_text(source+"max_fe: 500\n")
    with pytest.raises(ValueError, match="ambiguous"):
        module.configured(tmp_path, "reevo", "gpt-5.6-sol")
