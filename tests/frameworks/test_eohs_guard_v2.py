import json
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

from arena.frameworks.drivers import eohs_gateway_v2 as driver
from arena.frameworks.recipes import load_recipes


class Population:
    def __init__(self, count=1):
        self.population = [SimpleNamespace(score=[0.1, 0.2], code=str(i)) for i in range(count)]
        self.generation = 2

    def select_complementary_pair(self):
        if len(self.population) < 2:
            raise ValueError(driver.PAIR_ERROR)
        return tuple(self.population[:2])


class Method:
    def __init__(self, population):
        self._population = population
        self._tot_sample_nums = 2
        self.shutdown = []
        self._evaluation_executor = SimpleNamespace(shutdown=lambda **k: self.shutdown.append(k))
        self.native_attempts = 0

    def _iteratively_use_eoh_operator(self):
        for _ in range(10):
            self.native_attempts += 1
            try:
                self._population.select_complementary_pair()
                return
            except Exception:
                continue
        raise AssertionError("Fixture native retry loop was not interrupted")

    def run(self):
        errors = []
        def run_thread():
            try:
                self._iteratively_use_eoh_operator()
            except BaseException as error:
                errors.append(error)
        thread = threading.Thread(target=run_thread)
        thread.start()
        thread.join(timeout=2)
        assert not thread.is_alive()
        if errors:
            raise errors[0]


def test_insufficient_population_escapes_native_retry_and_thread_reports_partial(tmp_path):
    method = Method(Population())
    record = driver.GuardRecord(tmp_path / "guard.json")
    pair, loop = Population.select_complementary_pair, Method._iteratively_use_eoh_operator
    assert driver.execute_native(method, Population, Method, record) == 75
    value = json.loads(record.path.read_text())
    assert method.native_attempts == 1 and method._tot_sample_nums == 2
    assert method.shutdown == [{"cancel_futures": True}]
    assert value["status"] == "partial_insufficient_population"
    assert value["native_completed"] is False and value["canonical_evaluation"] is False
    assert value["event"]["valid_population_size"] == 1
    assert value["event"]["registered_samples"] == 2
    assert value["event"]["population"][0]["native_score"] == [0.1, 0.2]
    assert Population.select_complementary_pair is pair
    assert Method._iteratively_use_eoh_operator is loop


def test_healthy_native_selection_is_not_replaced_or_modified(tmp_path):
    population = Population(2)
    original = tuple(population.population)
    record = driver.GuardRecord(tmp_path / "guard.json")
    with driver.guard_native_selection(Population, Method, record):
        selected = population.select_complementary_pair()
    assert all(a is b for a, b in zip(selected, original))
    assert record.event is None
    assert driver.execute_native(Method(population), Population, Method, record) == 0
    assert json.loads(record.path.read_text())["native_completed"] is True


def test_unrelated_native_error_is_not_relabelled(tmp_path):
    class OtherPopulation(Population):
        def select_complementary_pair(self):
            raise ValueError("unrelated native failure")
    record = driver.GuardRecord(tmp_path / "guard.json")
    with driver.guard_native_selection(OtherPopulation, Method, record):
        with pytest.raises(ValueError, match="unrelated"):
            OtherPopulation().select_complementary_pair()
    assert record.event is None and not record.path.exists()


def test_unexpected_native_run_failure_is_not_completion(tmp_path):
    class BrokenMethod(Method):
        def run(self):
            raise RuntimeError("fixture")
    record = driver.GuardRecord(tmp_path / "guard.json")
    with pytest.raises(RuntimeError, match="fixture"):
        driver.execute_native(BrokenMethod(Population()), Population, BrokenMethod, record)
    assert json.loads(record.path.read_text())["status"] == "native_error"
    assert not json.loads(record.path.read_text())["native_completed"]


def test_source_guard_fails_without_importing_native_code(tmp_path):
    with pytest.raises(ValueError, match="source mismatch"):
        driver.verify_source(tmp_path)


def test_versioned_recipe_preserves_original_identity_and_task_protocol():
    recipes = load_recipes()
    old, new = recipes["eoh-s"], recipes["eoh-s-gateway-v2"]
    assert old["repository"] == new["repository"]
    assert old["participant_ids"] == new["participant_ids"]
    original = next(p for p in old["profiles"] if p["id"] == "gateway-obp-set-pilot")
    guarded = new["profiles"][0]
    assert guarded["id"] == "gateway-obp-set-pilot-v2"
    assert original["invocation"]["target"].endswith(".eohs_gateway")
    assert guarded["invocation"]["target"].endswith(".eohs_gateway_v2")
    for key in ("required_files", "evaluation", "python_paths", "config_files", "output"):
        assert original[key] == guarded[key]


def test_seven_pure_templates_keep_budget_concurrency_and_exact_models():
    import importlib.util
    path = Path(__file__).resolve().parents[2] / "scripts/deployment/prepare_eohs_guard_v2_pilots.py"
    spec = importlib.util.spec_from_file_location("prepare_eohs_v2_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = [module.template(Path("/srv/arena"), model, Path("/trust.pem")) for model in driver.MODELS]
    assert len({row["id"] for row in rows}) == 7
    for row in rows:
        request = row["spec"]["request"]
        assert request["arguments"][:4] == ["--model", row["model"], "--samples", "8"]
        assert row["spec"]["timeout_seconds"] == 2400
        assert row["resources"]["evaluation_slots"] == 1
        assert row["framework"] == "eoh-s-gateway-v2"


@pytest.mark.parametrize("value,expected", [(None, False), ([1.0, float("inf")], False), ([0.1, 0.2], True), (float("-inf"), False)])
def test_native_eligibility_is_preserved(value, expected):
    assert driver.valid_score(value) is expected
