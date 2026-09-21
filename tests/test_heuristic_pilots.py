import importlib.util
from pathlib import Path

import pytest


def load_generator():
    path = Path(__file__).resolve().parents[1] / "scripts/deployment/prepare_heuristic_pilots.py"
    spec = importlib.util.spec_from_file_location("heuristic_pilot_generator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("engine", ["eoh", "meoh"])
def test_pilot_matrix_has_explicit_budget_and_hashable_ca_input(engine, tmp_path):
    generator = load_generator()
    templates = [generator.template(tmp_path, engine, model, tmp_path / "public-ca.pem", {"name": engine})
                 for model in generator.MODELS]
    assert len(templates) == 7 and len({t["id"] for t in templates}) == 7
    for item in templates:
        spec = item["spec"]
        arguments = spec["request"]["arguments"]
        options = dict(zip(arguments[::2], arguments[1::2]))
        assert options["--model"] == item["model"]
        assert options["--generations"] == "2"
        assert options["--samplers"] == options["--evaluators"] == options["--numeric-threads"] == "1"
        assert item["resources"]["evaluation_slots"] == 1 and item["evaluation_concurrency_verified"]
        assert spec["timeout_seconds"] == 2400
        assert spec["environment_names"] == ["OPENAI_API_KEY"]
        assert "api_key" not in str(spec).lower().replace("openai_api_key", "")
        native_cwd = Path("examples/bp_online") if engine == "eoh" else Path(".")
        assert str(native_cwd / options["--tls-ca"]) in spec["request"]["inputs"]
        if engine == "eoh":
            # The real pinned EoH initializes 2*population before its additional
            # max_sample_nums evolution budget. It must not silently become16.
            assert 2 * int(options["--population"]) + int(options["--samples"]) == 8
        else:
            assert int(options["--samples"]) == 8


def test_pilot_generator_rejects_unreviewed_engine_model(tmp_path):
    generator = load_generator()
    for engine, model in [("other", generator.MODELS[0]), ("eoh", "unreviewed")]:
        with pytest.raises(ValueError):
            generator.template(tmp_path, engine, model, tmp_path / "ca", {"name": "fixture"})
