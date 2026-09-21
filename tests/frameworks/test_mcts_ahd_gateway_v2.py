"""Bound the existing native retries without replacing their search decisions."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest

from arena.frameworks.drivers import mcts_ahd_gateway_v2 as driver
from arena.frameworks.recipes import load_recipes


def test_retry_guard_escapes_native_style_exception_loop_and_restores_methods(tmp_path):
    class Native:
        def _get_alg(self, pop, operator, father=None):
            raise ValueError("inert parser failure")
        def get_algorithm(self, evaluations, pop, operator):
            while True:
                try:
                    self._get_alg(pop, operator)
                except Exception:
                    continue
    original = (Native._get_alg, Native.get_algorithm)
    budget = driver.AttemptBudget(8, 3, tmp_path / "attempts.json")
    with pytest.raises(driver.ProposalBudgetExhausted):
        with driver.bounded_native_attempts(Native, budget):
            Native().get_algorithm(0, [], "i1")
    assert (Native._get_alg, Native.get_algorithm) == original
    report = json.loads((tmp_path / "attempts.json").read_text())
    assert report["status"] == "budget_exhausted"
    assert report["attempt_count"] == report["initialization_attempt_count"] == 3
    assert report["exhausted"] == "initialization"
    assert budget.depth == 0


def test_guard_passes_native_results_and_parent_identity_then_limits_search(tmp_path):
    native_calls = []
    result = object()
    class Native:
        def _get_alg(self, pop, operator, father=None):
            native_calls.append((pop, operator, father))
            return result
        def get_algorithm(self, evaluations, pop, operator):
            return self._get_alg(pop, operator)
    parent, population = object(), []
    budget = driver.AttemptBudget(8, 3, tmp_path / "attempts.json")
    with driver.bounded_native_attempts(Native, budget):
        native = Native()
        assert native.get_algorithm(0, population, "i1") is result
        assert native.get_algorithm(1, population, "e1") is result
        for _ in range(6):
            assert native._get_alg(population, "m1", father=parent) is result
        with pytest.raises(driver.ProposalBudgetExhausted):
            native._get_alg(population, "m2", father=parent)
    assert len(native_calls) == 8
    assert all(p is population and f is parent for p, _, f in native_calls[2:])
    assert [e["phase"] for e in budget.events] == ["initialization"] * 2 + ["search"] * 6
    assert budget.exhausted == "total"


@pytest.mark.parametrize("total,initial", [(True, 1), (0, 1), (65, 2), (8, True), (8, 0), (8, 9)])
def test_invalid_budgets_rejected(total, initial, tmp_path):
    with pytest.raises(ValueError):
        driver.AttemptBudget(total, initial, tmp_path / "unused.json")
    assert not list(tmp_path.iterdir())


def test_driver_budget_exhaustion_is_nonzero_and_does_not_claim_completion(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-credential-never-serialize")
    monkeypatch.setattr(driver, "verify_workspace", lambda root: None)
    class Native:
        def _get_alg(self, pop, operator, father=None):
            return object()
        def get_algorithm(self, count, pop, operator):
            while True:
                self._get_alg(pop, operator)
    module = ModuleType("source.evolution_interface")
    module.InterfaceEC = Native
    monkeypatch.setitem(sys.modules, "source.evolution_interface", module)
    observed = []
    def run(path, run_name):
        observed.append(list(sys.argv))
        Native().get_algorithm(0, [], "i1")
    monkeypatch.setattr(driver.runpy, "run_path", run)
    assert driver.main([]) == 75
    assert observed[0][1:] == ["algorithm=mcts_ahd", "problem=bpp_online", "max_fe=4", "init_pop_size=2", "pop_size=2", "timeout=60"]
    report = json.loads((tmp_path / "arena-attempt-budget-v2.json").read_text())
    assert report["status"] == "budget_exhausted" and report["attempt_count"] == 3
    assert "fixture-credential-never-serialize" not in "".join(p.read_text() for p in tmp_path.iterdir())
    with pytest.raises(SystemExit):
        driver.main(["max_fe=500"])


def load_preparer():
    path = Path(__file__).resolve().parents[2] / "scripts/deployment/prepare_mcts_ahd_v2_pilots.py"
    spec = importlib.util.spec_from_file_location("mcts_v2_preparation_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_separate_variant_preserves_old_profile_and_records_exact_models(tmp_path):
    recipes = load_recipes()
    old = next(p for p in recipes["mcts-ahd"]["profiles"] if p["id"] == "gateway-cpu-pilot")
    assert old["invocation"]["target"] == "arena.frameworks.drivers.cpu_heuristic_gateway"
    assert not any(p["id"] == "gateway-cpu-pilot-v2" for p in recipes["mcts-ahd"]["profiles"])
    recipe = recipes["mcts-ahd-gateway-v2"]
    assert recipe["participant_ids"] == ["mcts-ahd"]
    assert recipe["repository"] == recipes["mcts-ahd"]["repository"]
    profile = recipe["profiles"][0]
    assert "prompts/bpp_online/func_signature.txt" in profile["config_files"]
    assert set(driver.SOURCE_HASHES).issubset(recipe["evidence"])
    assert recipe["evidence"] | driver.SOURCE_HASHES == recipe["evidence"]
    module = load_preparer()
    (tmp_path / "cfg").mkdir()
    (tmp_path / "prompts/bpp_online").mkdir(parents=True)
    (tmp_path / "cfg/config.yaml").write_text("max_fe: 1000\npop_size: 10\ninit_pop_size: 4\ntimeout: 60\nunrelated_native_option: retained\n")
    (tmp_path / "prompts/bpp_online/func_signature.txt").write_text("def priority(item: float, bins_remain_cap: np.ndarray) -> np.ndarray:")
    for model in module.MODELS:
        overlays = module.configured(tmp_path, model)
        assert overlays["prompts/bpp_online/func_signature.txt"].format(version=2).startswith("def priority_v2(")
        client = json.loads(overlays["cfg/llm_client/openai.yaml"])
        assert client["model"] == model and client["api_key"] == "${oc.env:OPENAI_API_KEY}"
        assert "unrelated_native_option: retained" in overlays["cfg/config.yaml"]
    with pytest.raises(ValueError):
        module.configured(tmp_path, "invented-alias")
    (tmp_path / "prompts/bpp_online/func_signature.txt").write_text("changed")
    with pytest.raises(ValueError, match="signature changed"):
        module.configured(tmp_path, module.MODELS[0])


def test_workspace_rejects_changed_native_evaluator(tmp_path):
    for relative in driver.SOURCE_HASHES:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("changed source")
    with pytest.raises(ValueError, match="source seam changed"):
        driver.verify_workspace(tmp_path)
