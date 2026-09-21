"""Provider identity and inert entrypoint tests; no native search or model calls."""
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from arena.frameworks.drivers import darwinian_gateway as driver


def test_import_is_inert():
    subprocess.run([sys.executable, "-c", "import sys; from arena.frameworks.drivers import darwinian_gateway; assert 'anthropic' not in sys.modules and 'darwinian_evolver' not in sys.modules"], check=True)


@pytest.mark.parametrize("model", driver.MODELS)
def test_exact_model_and_fixed_endpoint_override_inherited_provider(monkeypatch, model):
    calls = []
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-local-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://wrong.invalid")
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=lambda **kw: calls.append(kw)))
    problem = SimpleNamespace(ANTHROPIC_MODEL="claude", Anthropic=lambda: None)
    driver.bind_provider(problem, model)
    assert problem.ANTHROPIC_MODEL == model
    problem.Anthropic()
    assert calls == [{"api_key": "fixture-local-key", "base_url": driver.ENDPOINT, "timeout": 180, "max_retries": 0}]


def test_bad_model_and_missing_key_fail_before_sdk_import(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="exact reviewed"):
        driver.bind_provider(SimpleNamespace(), "claude")
    with pytest.raises(ValueError, match="scoped"):
        driver.bind_provider(SimpleNamespace(), driver.MODELS[0])


def test_native_cli_disables_external_upload_resume_and_parallel_evaluations(tmp_path):
    args = driver.native_arguments(4, tmp_path)
    assert args[0] == "circle_packing"
    assert args[args.index("--num_parents_per_iteration") + 1] == "1"
    assert args[args.index("--evaluator_concurrency") + 1] == "1"
    assert args[args.index("--mutator_concurrency") + 1] == "1"
    assert args[args.index("--learning_log") + 1] == "ancestors"
    assert not {"--s3_dir", "--resume_from_snapshot", "--fixed_children_per_generation"}.intersection(args)
    for bad in (0, 9, True):
        with pytest.raises(ValueError): driver.native_arguments(bad, tmp_path)


def test_source_drift_fails_without_importing_native_code(tmp_path):
    p = tmp_path / driver.PROBLEM_FILE
    p.parent.mkdir(parents=True)
    p.write_text("raise RuntimeError('must not run')")
    with pytest.raises(ValueError, match="hash mismatch"):
        driver.verify_source(tmp_path)


def test_seven_templates_use_separate_recipe_and_original_pinned_source():
    path = Path(__file__).resolve().parents[2] / "scripts/deployment/prepare_darwinian_pilots.py"
    spec = importlib.util.spec_from_file_location("darwinian_templates", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    values = [module.template(Path("/srv/arena"), model) for model in driver.MODELS]
    assert len({v["id"] for v in values}) == 7
    for item in values:
        assert item["framework"] == "darwinian-evolver-gateway"
        assert item["spec"]["source_dir"] == "/srv/arena/sources/darwinian-evolver"
        assert item["spec"]["environment_names"] == ["OPENAI_API_KEY"]
        assert item["model"] in item["spec"]["request"]["arguments"]
