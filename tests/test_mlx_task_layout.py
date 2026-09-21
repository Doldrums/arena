"""MLX task module wiring and score semantics without MLX or GPU execution."""
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest

TASK = Path(__file__).resolve().parents[1] / "tasks/suite/sciel-bench-mlx-qwen3-gqa-kernel"


@pytest.fixture
def modules(monkeypatch):
    def no_process(*args, **kwargs):
        raise AssertionError("Metadata and scoring checks must not run a model")
    monkeypatch.setattr(subprocess, "Popen", no_process)
    monkeypatch.syspath_prepend(str(TASK))
    mlx, core, nn = (ModuleType(name) for name in ("mlx", "mlx.core", "mlx.nn"))
    core.array = object
    core.__version__ = "fixture"
    nn.Module = object
    mlx.core, mlx.nn = core, nn
    for module in (mlx, core, nn):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    before = set(sys.modules)
    loaded = {}
    try:
        for name in ("evaluator", "run_benchmarks", "initial_program"):
            spec = importlib.util.spec_from_file_location("fixture_mlx_" + name, TASK / (name + ".py"))
            module = importlib.util.module_from_spec(spec)
            monkeypatch.setitem(sys.modules, spec.name, module)
            spec.loader.exec_module(module)
            loaded[name] = module
        yield loaded
    finally:
        for name in set(sys.modules) - before:
            module = sys.modules[name]
            if getattr(module, "__file__", None) and Path(module.__file__).parent == TASK:
                sys.modules.pop(name, None)


def test_benchmark_configs_and_summary_preserve_public_api(modules):
    api = modules["evaluator"]
    suite = api.Qwen3BenchmarkSuite("fixture-model")
    configs = suite.create_benchmark_configs()
    assert len(configs) >= 15
    assert len({row.name for row in configs}) == len(configs)
    assert configs[0].name == "short_context_quick"
    assert all(isinstance(row, api.BenchmarkConfig) and row.prompt and row.max_tokens > 0 for row in configs)
    rows = [api.BenchmarkResult("short_context_quick", 10, 20, 100, 40, 60, 2, 1, "prompt", "output"),
            api.BenchmarkResult("code_generation_test", 10, 20, 200, 60, 80, 4, 1, "prompt", "output")]
    summary = suite.generate_summary(rows)
    assert summary["avg_decode_speed"] == 50
    assert summary["avg_prefill_speed"] == 150
    assert summary["avg_memory_usage"] == 3
    assert summary["context_length_count"] == 1
    assert summary["use_cases_count"] == 1
    assert suite._result_to_dict(rows[0])["name"] == rows[0].name


def test_evaluator_score_and_error_counters_span_mixins(modules):
    evaluator = modules["evaluator"].BulletproofMetalEvaluator()
    comparison = {"avg_decode_improvement_pct": 10, "memory_change_gb": -0.5,
                  "num_benchmarks_improved": 1, "total_benchmarks": 2, "safety_score": 100}
    assert evaluator._calculate_safety_adjusted_score({"comparison_summary": comparison}, 1.0) == 50
    assert evaluator._calculate_safety_adjusted_score({}, 0.8) == -1000
    evaluator.total_metal_errors = 2
    evaluator.metal_command_buffer_errors = 2
    assert evaluator._calculate_safety_score() == pytest.approx(100 * (1 - 2 / 12))
    evaluator._reset_error_counters()
    assert evaluator._calculate_safety_score() == 100
    assert evaluator._safe_calculate_improvement(12, 10) == 20
    assert evaluator._safe_calculate_improvement(12, 0) == 0


def test_cli_and_seed_exports_survive_modularization(modules):
    cli, seed = modules["run_benchmarks"], modules["initial_program"]
    for name in ("analyze_comparison_results", "save_comparison_results", "print_comparison_summary", "main"):
        assert callable(getattr(cli, name))
    assert callable(seed.qwen3_custom_gqa_attention)
    assert callable(seed.CustomGQAAttention)
    import _metal_seed_demo
    called = []
    _metal_seed_demo.run(lambda: called.append("correctness"), lambda: called.append("benchmark"))
    assert called == ["correctness", "benchmark"]
