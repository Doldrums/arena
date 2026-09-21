import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

from arena.frameworks.recipes import validate_recipe, RecipeAdapter
from arena.frameworks.drivers import avo_community

ROOT = Path(__file__).resolve().parents[2]
RECIPES = json.loads((ROOT / "registry/framework-recipes/community.json").read_text())["recipes"]


def test_community_identity_is_explicit_and_distinct_from_original_authors():
    for recipe in RECIPES:
        validate_recipe(recipe)
        assert recipe["status"] == "source_verified"
        assert "community" in recipe["name"] or "independent" in recipe["name"]
        assert any("not" in s for s in recipe["profiles"][0]["limitations"])
    assert RECIPES[0]["repository"]["url"] == "https://github.com/austin1997/AVO"
    assert RECIPES[1]["repository"]["url"] == "https://github.com/algorithmicsuperintelligence/openevolve"


@pytest.mark.parametrize("recipe", RECIPES, ids=lambda r: r["id"])
def test_source_only_prepare_is_inert_with_native_module_and_driver(tmp_path, recipe):
    recipe = json.loads(json.dumps(recipe))
    source = tmp_path / "source"
    for name in recipe["evidence"]:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("raise RuntimeError('No native imports during planning')")
        recipe["evidence"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    command = RecipeAdapter(recipe).prepare(source, {"python": sys.executable}, tmp_path / "out")
    assert command["argv"][-2:] == ["--output", str(tmp_path / "out/native")]
    assert not (tmp_path / "out").exists()
    if recipe["id"] == "openevolve":
        with pytest.raises(ValueError, match="fixes this option"):
            RecipeAdapter(recipe).prepare(source, {"python": sys.executable, "arguments": ["-o", "elsewhere"]}, tmp_path / "out")


def test_avo_driver_delegates_to_native_loop_and_retains_native_metrics(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text("reviewed fixture")
    calls = []
    config = SimpleNamespace(llm=SimpleNamespace(api_key=""))
    config_module, core_module = ModuleType("avo.config"), ModuleType("avo.core.evolution")
    config_module.EvolutionConfig = SimpleNamespace(from_yaml=lambda path: config)
    class Runner:
        def __init__(self, native_config):
            assert native_config is config
            calls.append("init")
        def run(self):
            calls.append("native loop")
        def get_results(self):
            return {"best_geomean": 2.25, "total_versions": 2}
    core_module.EvolutionRunner = Runner
    monkeypatch.setitem(sys.modules, "avo.config", config_module)
    monkeypatch.setitem(sys.modules, "avo.core.evolution", core_module)
    args = ["--config", "config.yaml", "--max-versions", "2", "--hours", "0.1", "--max-agent-steps", "5", "--output", str(tmp_path / "native")]
    assert avo_community.main(args) == 0
    assert calls == ["init", "native loop"]
    assert config.max_versions == 2 and config.max_agent_steps_per_variation == 5
    result = json.loads((tmp_path / "native/native-summary.json").read_text())
    assert result["native"]["best_geomean"] == 2.25 and result["canonical_evaluation"] is False
    config.llm.api_key = "no-literal-key"
    with pytest.raises(SystemExit):
        avo_community.main(args)
    assert calls == ["init", "native loop"]


@pytest.mark.parametrize("hours", ["nan", "inf", "-1", "169"])
def test_avo_rejects_unbounded_budget_before_native_import(hours, tmp_path):
    with pytest.raises(SystemExit):
        avo_community.main(["--config", "missing.yaml", "--max-versions", "2", "--hours", hours,
                            "--max-agent-steps", "5", "--output", str(tmp_path / "native")])
